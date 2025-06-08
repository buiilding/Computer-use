import os
import sys

# Add the project root to the Python path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(SCRIPT_DIR)
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import io
import json
import base64
import inspect
import PIL.Image as Image

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

    def call_function(self, function_call_name: str, function_call_args: dict, elements: list = None) -> any:
        if hasattr(input_functions, function_call_name):
            function_to_call = getattr(input_functions, function_call_name)
            
            sig = inspect.signature(function_to_call)
            valid_params = {p.name for p in sig.parameters.values()}
            
            filtered_args = {k: v for k, v in function_call_args.items() if k in valid_params}
            
            # If the function requires the elements list, pass it in.
            if "elements" in sig.parameters:
                filtered_args['elements'] = elements

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
        current_elements = state.get("current_elements", [])
        
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
            function_calls = []
            thoughts = ""
            if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'text') and part.text:
                        thoughts += part.text + "\n"
                    if part.function_call:
                        function_calls.append(part.function_call)
            
            if function_calls:
                action_outputs = []
                for function_call in function_calls:
                    function_call_name = function_call.name
                    function_call_args = _convert_proto_to_py(function_call.args) if function_call.args else {}
                    
                    # Execute the function
                    print(f"Executing: {function_call_name} with args {function_call_args}")
                    action_output = self.call_function(function_call_name, function_call_args, elements=current_elements)
                    action_outputs.append({
                        "function_name": function_call_name,
                        "function_args": function_call_args,
                        "output": action_output
                    })
                
                # Log the action
                try:
                    with open(self.log_file_name, "a", encoding='utf-8') as f:
                        f.write(f"Actions Called: {[o['function_name'] for o in action_outputs]}\n")
                        f.write(f"Arguments: {json.dumps([o['function_args'] for o in action_outputs], indent=2)}\n")
                        f.write(f"Outputs: {json.dumps([o['output'] for o in action_outputs], indent=2)}\n---\n")
                    self._log_turn_to_history(prompt_context, response.candidates[0].content, action_outputs)
                except Exception as e:
                    print(f"Error writing to {self.log_file_name}: {e}")

                # Check if the last function call was task_done
                final_function_name = action_outputs[-1]["function_name"] if action_outputs else None
                if final_function_name == "task_done":
                    return {
                        "function_call": "task_done",
                        "action_result": action_outputs[-1]['output'],
                        "thoughts": thoughts.strip()
                    }

                return {
                    "function_call": [o['function_name'] for o in action_outputs], 
                    "action_result": action_outputs,
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

def test_batch_function_calling():
    """A test function to verify how the model handles batch function calls."""
    print("--- Testing Batch Function Calling ---")
    
    # 1. Initialize the agent
    agent = MainAgent()
    if not agent.gemini_model:
        print("Agent could not be initialized. Check API keys.")
        return

    # 2. Load the simulated UI elements
    json_file_path = os.path.join(settings.PROJECT_ROOT, "src", "core", "test_json_elements", "newtab_elements.json")
    try:
        with open(json_file_path, "r", encoding='utf-8') as f:
            elements = json.load(f)
        print(f"Successfully loaded {len(elements)} elements from {os.path.basename(json_file_path)}")
    except Exception as e:
        print(f"Failed to load simulation file: {e}")
        return
        
    # 3. Create a mock state with a specific request for batch execution
    mock_state = State(
        original_request="Click the address bar, type amazon.com, and press enter.",
        current_elements=elements,
        current_screenshot=None, # No image needed for this test
        search_agent_guide="1. Click Address Bar. 2. Type amazon.com. 3. Press Enter."
    )

    # 4. Call the agent. The raw API response will be printed from within the __call__ method.
    print("\n--- Calling Main Agent with test prompt ---")
    agent_output = agent(mock_state)

    # 5. Print the final processed output for inspection
    print("\n--- Agent Processed Output ---")
    print(json.dumps(agent_output, indent=2, default=str))

if __name__ == "__main__":
    test_batch_function_calling()