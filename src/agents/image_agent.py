import io
import base64
import PIL.Image as Image

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
            
            current_turn_content = [{"role": "user", "parts": [image_part, {"text": "Analyze the provided screenshot based on your instructions and our previous interactions (if any)."}]}]
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
