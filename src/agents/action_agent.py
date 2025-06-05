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
from utils.screenshot import take_screenshot
from utils.Omni_loader import initialize_omni_models

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

if __name__ == '__main__':
    print("--- Testing ActionAgent Independently with Real Screenshot ---")

    # Imports for testing screenshot functionality
    from utils.screenshot import take_screenshot
    from utils.Omni_loader import initialize_omni_models
    # settings, State, Image, json are already imported or handled by ActionAgent itself.

    real_screenshot_action_pil = None
    real_elements_action = []

    print("Initializing Omni models for screenshot...")
    som_model, caption_model_processor = initialize_omni_models(
        settings.OMNI_DEVICE, settings.SOM_MODEL_PATH, settings.CAPTION_MODEL_PATH
    )
    omni_enabled_for_test_action = True
    if som_model is None or caption_model_processor is None:
        print("Warning: Omni models (SOM, Caption) failed to initialize. Screenshot will be basic.")
        omni_enabled_for_test_action = False
    else:
        print("Omni models initialized successfully for ActionAgent screenshot test.")

    print("Attempting to take a real screenshot for ActionAgent test...")
    try:
        screenshot_bytes_io, elements = take_screenshot(
            som_model, caption_model_processor, omni_enabled=omni_enabled_for_test_action
        )
        
        if screenshot_bytes_io:
            screenshot_bytes_io.seek(0)
            real_screenshot_action_pil = Image.open(screenshot_bytes_io)
            print(f"Real screenshot captured for ActionAgent: {real_screenshot_action_pil.size}")
        else:
            print("take_screenshot returned no image data for ActionAgent.")
            
        real_elements_action = elements if elements else []
        print(f"{len(real_elements_action)} elements identified by screenshot function for ActionAgent.")
        
    except Exception as e_screenshot:
        print(f"Could not take real screenshot for ActionAgent: {e_screenshot}")
        real_screenshot_action_pil = None
        real_elements_action = []


    if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "<GEMINI_API_KEY>":
        print("GEMINI_API_KEY not set. ActionAgent test cannot proceed with actual model call.")
    elif real_screenshot_action_pil:
        # Mock State for ActionAgent, now using real screenshot data
        mock_current_task = {
            "request": "Click the most prominent button visible on the screen.",
            "expected_output": "The button should be clicked.",
            "step": 1 
        }
        
        # current_elements will come from the real screenshot
        mock_state_action_real_ss = State(
            task_list=[mock_current_task],
            current_task_index=0,
            image_agent_output="The screen shows several UI elements. Please refer to the screenshot and element list.", # Generic image agent output
            current_elements=real_elements_action, # Using elements from take_screenshot
            current_screenshot=real_screenshot_action_pil, # Using image from take_screenshot
            original_request="Perform a test action based on real screen content.",
            original_expected_output="Action performed.",
            search_agent_guide=None,
            last_action_done=None,
            step=None, 
            plan_mode="replan",
            newly_planned_tasks=None,
            action_result=None,
            error_message=None
        )

        print(f"Initializing ActionAgent with model: {settings.ACTION_MODEL_NAME}")
        try:
            action_agent_test = ActionAgent()
            if action_agent_test.gemini_model:
                print("ActionAgent initialized successfully for testing with real screenshot.")
                print("Calling ActionAgent with real screenshot data...")
                result_action = action_agent_test(mock_state_action_real_ss)
                print("\nActionAgent Test Result (with real screenshot):")
                print(json.dumps(result_action, indent=2))
            else:
                print("ActionAgent's Gemini model not initialized. Check API key and model setup.")
        except Exception as e:
            print(f"An error occurred during ActionAgent test with real screenshot: {e}")
    elif not real_screenshot_action_pil:
        print("Real screenshot was not captured. Cannot run ActionAgent test that requires an image.")
    else:
        print("Some other prerequisite for ActionAgent test (with real screenshot) failed.") 