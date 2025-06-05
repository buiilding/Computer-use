import io
import base64
import PIL.Image as Image
import json

from .base_agent import BaseAgent
from core.state import State
from config import settings

class ImageAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            model_name=settings.IMAGE_AGENT_MODEL_NAME,
            system_prompt_path=settings.IMAGE_AGENT_PROMPT_PATH
        )
        self.history = []
        self.log_file_name = "image_agent_log.txt"

    def __call__(self, state: State) -> dict:
        print(f"ImageAgent: Received call. Plan mode: {state.get('plan_mode')}")
        output_payload = {"image_agent_output": None}
        current_screenshot_pil = state.get("current_screenshot")

        if not isinstance(current_screenshot_pil, Image.Image):
            msg = "ImageAgent: Screenshot is not a valid PIL Image or not found."
            print(msg)
            output_payload["image_agent_output"] = msg
            try:
                with open(self.log_file_name, "a", encoding='utf-8') as f:
                    f.write(f"--- ImageAgent Error ---\nState Screenshot: {current_screenshot_pil}\nError: {msg}\n--- End Error ---\n\n")
            except Exception as e_log:
                print(f"Error writing to {self.log_file_name}: {e_log}")
            return output_payload

        if not self.gemini_model:
            msg = f"{self.__class__.__name__}: Gemini model not available."
            print(msg)
            output_payload["image_agent_output"] = msg
            return output_payload

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
            
            current_turn_content = [{"role": "user", "parts": [image_part]}]
            api_contents = self.history + current_turn_content
            
            print(f"ImageAgent: Sending image to Gemini. History length: {len(self.history)}")
            response = self.gemini_model.generate_content(contents=api_contents)
            
            gemini_response_text = None
            if hasattr(response, 'text') and response.text:
                gemini_response_text = response.text
            elif hasattr(response, 'candidates') and response.candidates and hasattr(response.candidates[0], 'content') and hasattr(response.candidates[0].content, 'parts') and response.candidates[0].content.parts and hasattr(response.candidates[0].content.parts[0], 'text'):
                gemini_response_text = response.candidates[0].content.parts[0].text
            else:
                print("ImageAgent: No text in Gemini response or unexpected response structure.")
                if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                    print(f"ImageAgent: Prompt Feedback: {response.prompt_feedback}")

            if gemini_response_text:
                print(f"ImageAgent: Raw Gemini response text:\n```\n{gemini_response_text}\n```")
                output_payload["image_agent_output"] = gemini_response_text
                
                self.history.append(current_turn_content[0])
                self.history.append({"role": "model", "parts": [{"text": gemini_response_text}]})
                
                try:
                    with open(self.log_file_name, "a", encoding='utf-8') as f:
                        f.write(f"--- ImageAgent Entry ---\nResponse: {gemini_response_text}\n--- End Entry ---\n\n")
                except Exception as e_log:
                    print(f"Error writing to {self.log_file_name}: {e_log}")
            else:
                msg = "ImageAgent: Failed to get a valid text response from Gemini."
                print(msg)
                output_payload["image_agent_output"] = msg
                try:
                    with open(self.log_file_name, "a", encoding='utf-8') as f:
                        f.write(f"--- ImageAgent Error ---\nError: {msg}\nFull Response: {response}\n--- End Error ---\n\n")
                except Exception as e_log:
                    print(f"Error writing to {self.log_file_name}: {e_log}")

        except Exception as e:
            error_msg = f"Error in ImageAgent call: {str(e)}"
            print(error_msg)
            output_payload["image_agent_output"] = error_msg
            try:
                with open(self.log_file_name, "a", encoding='utf-8') as f:
                    f.write(f"--- ImageAgent Exception ---\nError: {error_msg}\n--- End Exception ---\n\n")
            except Exception as e_log:
                print(f"Error writing to {self.log_file_name}: {e_log}")
                
        return output_payload

if __name__ == '__main__':
    print("--- Testing ImageAgent Independently with Real Screenshot ---")

    # Imports for testing screenshot functionality
    from utils.screenshot import take_screenshot
    from utils.Omni_loader import initialize_omni_models
    # settings is already imported in the main part of the file for ImageAgent
    # core.state.State is already imported
    # PIL.Image is already imported
    # json is already imported

    real_screenshot_pil = None
    real_elements = []
    
    print("Initializing Omni models for screenshot...")
    som_model, caption_model_processor = initialize_omni_models(
        settings.OMNI_DEVICE, settings.SOM_MODEL_PATH, settings.CAPTION_MODEL_PATH
    )
    omni_enabled_for_test = True
    if som_model is None or caption_model_processor is None:
        print("Warning: Omni models (SOM, Caption) failed to initialize. Screenshot will be basic.")
        omni_enabled_for_test = False
    else:
        print("Omni models initialized successfully for screenshot test.")

    print("Attempting to take a real screenshot...")
    try:
        # Pass the initialized models to take_screenshot
        screenshot_bytes_io, elements = take_screenshot(
            som_model, caption_model_processor, omni_enabled=omni_enabled_for_test
        )
        
        if screenshot_bytes_io:
            screenshot_bytes_io.seek(0)
            real_screenshot_pil = Image.open(screenshot_bytes_io)
            print(f"Real screenshot captured: {real_screenshot_pil.size}")
        else:
            print("take_screenshot returned no image data.")
            
        real_elements = elements if elements else []
        print(f"{len(real_elements)} elements identified by screenshot function.")
        
    except Exception as e_screenshot:
        print(f"Could not take real screenshot: {e_screenshot}")
        real_screenshot_pil = None
        real_elements = []

    if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "<GEMINI_API_KEY>":
        print("GEMINI_API_KEY not set. ImageAgent test cannot proceed with actual model call.")
    elif real_screenshot_pil:
        mock_state_image_real = State(
            current_screenshot=real_screenshot_pil,
            current_elements=real_elements, # Pass elements from screenshot
            original_request="Test request with real screenshot",
            original_expected_output="Test output",
            search_agent_guide=None,
            image_agent_output=None, 
            last_action_done=None,
            step=None,
            plan_mode="initial",
            task_list=[],
            current_task_index=None,
            newly_planned_tasks=None,
            action_result=None,
            error_message=None
        )

        print(f"Initializing ImageAgent with model: {settings.IMAGE_AGENT_MODEL_NAME}")
        try:
            image_agent_test = ImageAgent()
            if image_agent_test.gemini_model:
                print("ImageAgent initialized successfully for testing.")
                print("Calling ImageAgent with real screenshot data...")
                result = image_agent_test(mock_state_image_real)
                print("\nImageAgent Test Result (with real screenshot):")
                print(json.dumps(result, indent=2))
            else:
                print("ImageAgent's Gemini model not initialized. Check API key and model setup.")
        except Exception as e:
            print(f"An error occurred during ImageAgent test with real screenshot: {e}")
    elif not real_screenshot_pil:
        print("Real screenshot was not captured. Cannot run ImageAgent test that requires an image.")
    else:
        print("Some other prerequisite for ImageAgent test failed.")
