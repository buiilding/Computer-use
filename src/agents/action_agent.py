import io
import json
import base64
import inspect
import PIL.Image as Image

from .base_agent import BaseAgent
from core.state import State, pick
from utils import screenshot
from utils import input_functions
from utils.function_definitions import function_declarations
from config import settings

class ActionAgent(BaseAgent):
    def __init__(self, som_model, caption_model_processor):
        super().__init__(
            model_name=settings.ACTION_MODEL_NAME,
            system_prompt_path="test_prompts/Action_Agent.txt",
            tools=[{"function_declarations" : function_declarations}]
        )
        self.som_model = som_model
        self.caption_model_processor = caption_model_processor

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
        try:
            if state["cur_task"] is not None and state["task_list"] is not None:
                action_prompt_parts = ["expected_output", "cur_elements", "cur_task"]
                if state.get("prev_failed_reason") is not None: # Check .get for safety
                    action_prompt_parts.extend(["prev_failed_reason", "prev_action", "prev_action_output"])
                
                action_prompt = pick(state, *action_prompt_parts)
                prompt_text = f"Task context:\n{json.dumps(action_prompt, indent=2)}\n\nPlease determine the next action based on the task context."
                
                current_image_from_state = state.get("cur_screenshot")

                if current_image_from_state is None: 
                    print("Warning: No screenshot available for action")
                    return {"cur_action": None, "cur_action_output": "No screenshot available"}
                
                pil_image_to_send_action = current_image_from_state
                if isinstance(current_image_from_state, io.BytesIO):
                    current_image_from_state.seek(0)
                    pil_image_to_send_action = Image.open(current_image_from_state)

                if not isinstance(pil_image_to_send_action, Image.Image):
                    print("ActionAgent: Screenshot is not a valid PIL Image after conversion.")
                    return {"cur_action": None, "cur_action_output": "Failed to process screenshot for action."}

                if self.gemini_model:
                    message_parts_action = []
                    img_byte_arr_action = io.BytesIO()
                    pil_image_to_send_action.save(img_byte_arr_action, format='PNG')
                    base64_image_action = base64.b64encode(img_byte_arr_action.getvalue()).decode('utf-8')
                    
                    image_part_action = {
                        "inline_data": {
                            "mime_type": "image/png",
                            "data": base64_image_action
                        }
                    }
                    message_parts_action.append(image_part_action)
                    message_parts_action.append({"text": "The image is the current screenshot."})
                    message_parts_action.append({"text": prompt_text})
                    
                    print(f"ActionAgent Input (Text):\n---\n{prompt_text}\n---")
                    if pil_image_to_send_action:
                        print("ActionAgent Input: Includes screenshot.")
                    else:
                        print("ActionAgent Input: No screenshot.")
                    
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
                            with open("action_agent_log.txt", "a", encoding='utf-8') as f:
                                f.write(f"Action Called: {function_call_name}\n")
                                f.write(f"Arguments: {json.dumps(function_call_args, indent=2)}\n")
                                f.write(f"Output: {str(action_output)}\n---\n")
                        except Exception as e:
                            print(f"Error writing to action_agent_log.txt: {e}")

                        # Take screenshot AFTER action
                        screenshot_bytes_io_action, elements_action = screenshot.take_screenshot(
                            self.som_model, self.caption_model_processor, omni_enabled=True
                        )
                        if elements_action is not None:
                            input_functions.update_global_transformed_list(elements_action)
                        
                        return {
                            "cur_action": function_call_name, 
                            "cur_action_output": action_output, 
                            "cur_screenshot": screenshot_bytes_io_action, 
                            "cur_elements": elements_action, 
                        }
                    else:
                        return {"cur_action": None, "cur_action_output": "No function call found in response."}
                else:
                    return {"cur_action": None, "cur_action_output": f"{self.__class__.__name__}: Gemini model not available."}
            
            return {"cur_action": None, "cur_action_output": "Current task or task list is missing, or other prerequisite failed."}
        
        except Exception as e:
            print(f"Error in ActionAgent: {str(e)}")
            # (logging handled as in original)
            return {"cur_action": None, "cur_action_output": f"Failed to process action due to an unexpected error: {str(e)}"} 