import ast
import io
import json
import base64
import PIL.Image as Image

from .base_agent import BaseAgent
from utils import screenshot
from utils import input_functions
from config import settings
from core.state import State

class PlanningAgent(BaseAgent):
    def __init__(self, som_model, caption_model_processor):
        super().__init__(
            model_name=settings.PLANNING_MODEL_NAME,
            system_prompt_path=settings.PLANNING_PROMPT_PATH
        )
        self.som_model = som_model
        self.caption_model_processor = caption_model_processor

    def convert_to_list(self, task_list_str: str) -> list:
        """Find the first "[" and the last "]" and convert the text between them to a list"""
        start = task_list_str.find("[")
        end = task_list_str.rfind("]")
        if start == -1 or end == -1 or end < start:
            return []
        list_str = task_list_str[start:end+1]
        try:
            return ast.literal_eval(list_str)
        except Exception:
            return []

    def __call__(self, state: State) -> dict:
        output_payload = {"new_tasklist": None}
        effective_screenshot_for_gemini = state.get("cur_screenshot")
        elements_for_prompt = state.get("cur_elements")

        if state["plan_mode"] == "initial" or state["plan_mode"] == "replan_full":
            try:
                new_screenshot_bytes_io, new_elements = screenshot.take_screenshot(
                    self.som_model, self.caption_model_processor
                )
                
                output_payload["cur_screenshot_from_planner"] = new_screenshot_bytes_io
                output_payload["cur_elements_from_planner"] = new_elements
                effective_screenshot_for_gemini = new_screenshot_bytes_io 
                elements_for_prompt = new_elements
            except Exception as e:
                print(f"Error taking screenshot in PlanningAgent ({state['plan_mode']}): {e}")
                pass 
        
        plan_prompt_context = {"request": state["request"], "expected_output": state["expected_output"]}
        
        if elements_for_prompt is not None:
            input_functions.update_global_transformed_list(elements_for_prompt)

        if state["plan_mode"] != "initial" and state.get("prev_failed_reason"):
            plan_prompt_context["prev_failed_reason"] = state["prev_failed_reason"]
            if state.get("prev_action"):
                plan_prompt_context["prev_action"] = state["prev_action"]
            if state.get("prev_action_output"):
                plan_prompt_context["prev_action_output"] = state["prev_action_output"]
        
        prompt_text = f"Task context:\n{json.dumps(plan_prompt_context, indent=2)}\n\nPlease generate a list of tasks to complete the request."
        
        gemini_response_text = None
        if self.gemini_model:
            try:
                message_parts = []
                if effective_screenshot_for_gemini:
                    pil_image_to_send = effective_screenshot_for_gemini
                    if isinstance(effective_screenshot_for_gemini, io.BytesIO):
                        effective_screenshot_for_gemini.seek(0)
                        pil_image_to_send = Image.open(effective_screenshot_for_gemini)
                    
                    if isinstance(pil_image_to_send, Image.Image):
                        img_byte_arr = io.BytesIO()
                        pil_image_to_send.save(img_byte_arr, format='PNG')
                        base64_image = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
                        
                        image_part = {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": base64_image
                            }
                        }
                        message_parts.append(image_part)
                        message_parts.append({"text": "The image is the current screenshot."})
                
                print(f"PlanningAgent Input (Text):\n---\n{prompt_text}\n---")
                if effective_screenshot_for_gemini:
                    print("PlanningAgent Input: Includes screenshot.")
                else:
                    print("PlanningAgent Input: No screenshot.")
                message_parts.append({"text": prompt_text})
                                
                task_list_response = self.gemini_model.generate_content(contents=message_parts)
                if task_list_response.candidates and task_list_response.text: # Added check for candidates
                    gemini_response_text = task_list_response.text
                else:
                    print("PlanningAgent: No text in Gemini response.")
                    if task_list_response.prompt_feedback:
                        print(f"PlanningAgent: Prompt Feedback: {task_list_response.prompt_feedback}")

            except Exception as e:
                print(f"Error sending message to Gemini in PlanningAgent: {e}")
        else:
            print(f"{self.__class__.__name__}: Gemini model not available.")

        if gemini_response_text:
            print(f"PlanningAgent: Raw Gemini response text:\n```\n{gemini_response_text}\n```")
            task_list = self.convert_to_list(gemini_response_text)
            output_payload["new_tasklist"] = task_list
            try:
                with open("planning_agent_log.txt", "a", encoding='utf-8') as f:
                    f.write(f"--- New Plan ({state['plan_mode']}) ---\n")
                    if task_list:
                        for i, task_item in enumerate(task_list): # Renamed task to task_item
                            f.write(f"Task {i+1}: {task_item.get('request', 'No request')} (Expected: {task_item.get('expected_output', 'N/A')})\n")
                    else:
                        f.write("No tasks generated.\n")
                    f.write("--- End Plan ---\n\n")
            except Exception as e:
                print(f"Error writing to planning_agent_log.txt: {e}")
        else:
            print("PlanningAgent: Failed to get a valid task list string from Gemini.")
            try:
                with open("planning_agent_log.txt", "a", encoding='utf-8') as f:
                    f.write(f"--- New Plan ({state['plan_mode']}) ---\n")
                    f.write("Failed to generate tasks from Gemini response.\n")
                    f.write("--- End Plan ---\n\n")
            except Exception as e:
                print(f"Error writing to planning_agent_log.txt: {e}")

        return output_payload 