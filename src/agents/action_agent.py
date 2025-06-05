import io
import json
import base64
import inspect
import PIL.Image as Image

from .base_agent import BaseAgent
from core.state import State
from utils import input_functions
from utils.function_definitions import function_declarations
from config import settings

class ActionAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            model_name=settings.ACTION_MODEL_NAME,
            system_prompt_path=settings.ACTION_PROMPT_PATH,
            tools=[{"function_declarations" : function_declarations}]
        )
        self.log_file_name = "action_agent_log.txt"

    def call_function(self, function_call_name: str, function_call_args: dict) -> any:
        """Call the function with the given name and arguments, filtering for valid parameters."""
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
        output_updates = {"action_agent_tool_call_name": None, "action_result": None}
        try:
            task_list = state.get("task_list")
            current_task_idx = state.get("current_task_index")

            if not task_list or current_task_idx is None or not (0 <= current_task_idx < len(task_list)):
                msg = "ActionAgent: Task list or current task index is invalid or missing."
                print(msg)
                output_updates["action_result"] = msg
                return output_updates
            
            current_task = task_list[current_task_idx]
            if not current_task or not isinstance(current_task, dict):
                msg = f"ActionAgent: Current task at index {current_task_idx} is invalid."
                print(msg)
                output_updates["action_result"] = msg
                return output_updates

            action_prompt_context = {
                "subtask_request": current_task.get("request"),
                "subtask_expected_output": current_task.get("expected_output"),
                "image_agent_output": state.get("image_agent_output"),
                "current_elements": state.get("current_elements")
            }
            
            prompt_text = f"Task context:\n{json.dumps(action_prompt_context, indent=2)}\n\nPlease analyze the provided current screenshot, the image agent's output, the list of current elements, and the subtask details to determine the function call to execute the subtask using available tools."
            
            current_screenshot_pil = state.get("current_screenshot")

            if not isinstance(current_screenshot_pil, Image.Image):
                msg = "ActionAgent: Screenshot is not a valid PIL Image or not found in state."
                print(msg)
                output_updates["action_result"] = msg
                # Log error if needed here
                return output_updates

            if self.gemini_model:
                message_parts_action = []
                try:
                    img_byte_arr = io.BytesIO()
                    current_screenshot_pil.save(img_byte_arr, format='PNG')
                    base64_image = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
                    
                    image_part = {
                        "inline_data": {
                            "mime_type": "image/png",
                            "data": base64_image
                        }
                    }
                    message_parts_action.append(image_part)
                    message_parts_action.append({"text": "The image is the current screenshot. Use it along with the textual context to decide the action."})
                except Exception as e_img:
                    print(f"ActionAgent: Error processing screenshot for Gemini: {e_img}")
                    # Potentially skip sending image if processing fails, or return error
                    # For now, we'll let it proceed without image if this part fails, but log it.
                    pass # Or handle more gracefully

                message_parts_action.append({"text": prompt_text})
                
                print(f"ActionAgent Input (Text):\n---\n{prompt_text}\n---")
                if any(part.get("inline_data") for part in message_parts_action):
                    print("ActionAgent Input: Includes screenshot.")
                else:
                    print("ActionAgent Input: No screenshot included (or failed to process). It will rely on image_agent_output and current_elements.")
                
                action_response = self.gemini_model.generate_content(contents=message_parts_action)
                function_call = None
                if action_response.candidates and action_response.candidates[0].content and action_response.candidates[0].content.parts:
                    for part in action_response.candidates[0].content.parts:
                        if part.function_call:
                            function_call = part.function_call
                            break
                
                print(f"ActionAgent: Function call:\n```\n{function_call}\n```")
                if function_call is not None:
                    function_call_name = function_call.name
                    function_call_args = dict(function_call.args) if function_call.args else {}
                    
                    action_output = self.call_function(function_call_name, function_call_args)
                    print(f"ActionAgent Output (Function Result): {action_output}")
                    
                    try:
                        with open(self.log_file_name, "a", encoding='utf-8') as f:
                            f.write(f"Action Called: {function_call_name}\n")
                            f.write(f"Arguments: {json.dumps(function_call_args, indent=2)}\n")
                            f.write(f"Output: {str(action_output)}\n---\n")
                    except Exception as e:
                        print(f"Error writing to {self.log_file_name}: {e}")

                    output_updates["action_agent_tool_call_name"] = function_call_name
                    output_updates["action_result"] = str(action_output)
                    return output_updates
                else:
                    output_updates["action_result"] = "No function call found in response."
                    return output_updates
            else:
                output_updates["action_result"] = f"{self.__class__.__name__}: Gemini model not available."
                return output_updates
        
        except Exception as e:
            error_msg = f"Error in ActionAgent: {str(e)}"
            print(error_msg)
            output_updates["action_result"] = error_msg
            return output_updates 