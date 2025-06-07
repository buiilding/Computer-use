import io
import json
import base64
import inspect
import PIL.Image as Image
import os

from proto.marshal.collections.repeated import RepeatedComposite
from proto.marshal.collections.maps import MapComposite

from agents.base_agent import BaseAgent
from core.state import State
from utils import input_functions
from utils.function_definitions import function_declarations
from config import settings

def _convert_proto_to_py(value):
    """Recursively converts Proto-plus composite types to native Python types."""
    if isinstance(value, MapComposite):
        return {k: _convert_proto_to_py(v) for k, v in value.items()}
    if isinstance(value, RepeatedComposite):
        return [_convert_proto_to_py(v) for v in value]
    return value

class MainAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            model_name=settings.MAIN_MODEL_NAME,
            system_prompt_path=settings.MAIN_PROMPT_PATH,
            tools=[{"function_declarations" : function_declarations}],
            temperature=0.0
        )
        self.log_file_name = "main_agent_log.txt"
        self.history_log_file = os.path.join(settings.PROJECT_ROOT, "main_agent_history.json")
        self._initialize_history_log()

    def _initialize_history_log(self):
        # Create an empty JSON array in the log file
        try:
            with open(self.history_log_file, "w", encoding='utf-8') as f:
                json.dump([], f)
        except Exception as e:
            print(f"Error initializing history log: {e}")

    def call_function(self, function_call_name: str, function_call_args: dict) -> any:
        if hasattr(input_functions, function_call_name):
            function_to_call = getattr(input_functions, function_call_name)
            
            sig = inspect.signature(function_to_call)
            valid_params = {p.name for p in sig.parameters.values()}
            
            filtered_args = {k: v for k, v in function_call_args.items() if k in valid_params}
            
            missing_required_params = []
            for param_name, param_obj in sig.parameters.items():
                if param_obj.default == inspect.Parameter.empty and param_name not in filtered_args:
                    missing_required_params.append(param_name)
            
            if missing_required_params:
                return f"Error: Missing required arguments for {function_call_name}: { ', '.join(missing_required_params)}"

            try:
                return function_to_call(**filtered_args)
            except Exception as e:
                return f"Error calling function {function_call_name} with args {filtered_args}: {str(e)}"
        else:
            return f"Function {function_call_name} not found in input_functions module."

    def __call__(self, state: State) -> dict:
        # Prepare the prompt components
        prompt_context = {
            "original_request": state.get("original_request"),
            "original_expected_output": state.get("original_expected_output"),
            "search_agent_guide": state.get("search_agent_guide"),
            "current_elements": state.get("current_elements"),
            "previous_thinking": state.get("previous_thinking"),
            "previous_action_result": state.get("previous_action_result"),
        }
        # Filter out None values for a cleaner prompt
        prompt_context = {k: v for k, v in prompt_context.items() if v is not None}
        
        prompt_text = f"Analyze the following context and decide the next action.\n{json.dumps(prompt_context, indent=2)}"

        current_screenshot_pil = state.get("current_screenshot")
        
        # Prepare Parts for Gemini
        message_parts = []
        # Image part
        if isinstance(current_screenshot_pil, Image.Image):
            try:
                img_byte_arr = io.BytesIO()
                current_screenshot_pil.save(img_byte_arr, format='PNG')
                base64_image = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
                image_part = {"inline_data": {"mime_type": "image/png", "data": base64_image}}
                message_parts.append(image_part)
            except Exception as e:
                print(f"Error processing image for MainAgent: {e}")

        # Text part
        message_parts.append({"text": prompt_text})

        # Call Gemini model
        if not self.gemini_model:
            return {"error": "MainAgent: Gemini model not available."}
            
        api_contents = [{"role": "user", "parts": message_parts}]
        
        try:
            print("--- Calling Main Agent ---")
            response = self.gemini_model.generate_content(
                contents=api_contents,
            )
            print(response)
            # Extract the first valid function call and any thoughts
            function_call = None
            thoughts = ""
            if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'text') and part.text:
                        thoughts += part.text + "\n"
                    if part.function_call:
                        function_call = part.function_call
                        break 
            
            if function_call:
                function_call_name = function_call.name
                function_call_args = _convert_proto_to_py(function_call.args) if function_call.args else {}
                
                # Execute the function
                print(function_call_name)
                print(function_call_args)
                action_output = self.call_function(function_call_name, function_call_args)
                
                # Log the action
                try:
                    with open(self.log_file_name, "a", encoding='utf-8') as f:
                        f.write(f"Action Called: {function_call_name}\n")
                        f.write(f"Arguments: {json.dumps(function_call_args, indent=2)}\n")
                        f.write(f"Output: {str(action_output)}\n---\n")
                    self._log_turn_to_history(prompt_context, response.candidates[0].content, action_output)
                except Exception as e:
                    print(f"Error writing to {self.log_file_name}: {e}")

                return {
                    "function_call": function_call_name, 
                    "action_result": action_output,
                    "thoughts": thoughts.strip()
                }
            else:
                # Handle cases where no function call was returned
                no_call_reason = response.text if hasattr(response, 'text') and response.text else "Unknown"
                print(f"MainAgent: No function call returned. Reason: {no_call_reason}")
                return {"error": f"No function call from model. Reason: {no_call_reason}"}

        except Exception as e:
            print(f"Error in MainAgent call: {e}")
            return {"error": str(e)}

    def _log_turn_to_history(self, prompt_context, model_content, action_result):
        """Logs the details of a single agent turn to a JSON file."""
        loggable_context = {k: v for k, v in prompt_context.items() if k != 'current_screenshot'}

        logged_parts = []
        if hasattr(model_content, 'parts'):
            for part in model_content.parts:
                part_repr = {}
                if hasattr(part, 'text') and part.text:
                    part_repr['text'] = part.text
                if hasattr(part, 'function_call'):
                    fc = part.function_call
                    part_repr['function_call'] = {"name": fc.name, "args": _convert_proto_to_py(fc.args) if fc.args else {}}
                if part_repr:
                    logged_parts.append(part_repr)

        # Ensure action_result is JSON serializable
        serializable_action_result = {}
        if isinstance(action_result, dict):
            serializable_action_result = {k: str(v) for k, v in action_result.items()}
        else:
            serializable_action_result = str(action_result)

        log_entry = {
            "prompt_context": loggable_context,
            "model_response": {"role": model_content.role, "parts": logged_parts},
            "action_result": serializable_action_result
        }
        
        try:
            with open(self.history_log_file, "r+", encoding='utf-8') as f:
                history = json.load(f)
                history.append(log_entry)
                f.seek(0)
                f.truncate()
                json.dump(history, f, indent=2)
        except (FileNotFoundError, json.JSONDecodeError):
            with open(self.history_log_file, "w", encoding='utf-8') as f:
                json.dump([log_entry], f, indent=2)
        except Exception as e:
            print(f"Error updating history log: {e}")