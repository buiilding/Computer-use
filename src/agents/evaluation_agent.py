import io
import json
import base64
import PIL.Image as Image
from typing import Optional # Added for type hint

from .base_agent import BaseAgent
from core.state import State, pick
from config import settings

class EvaluationAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            model_name=settings.EVALUATION_MODEL_NAME,
            system_prompt_path="test_prompts/Evaluation_Agent.txt" # Relative to project root
        )

    def convert_text_to_dict(self, text_data: str) -> Optional[dict]:
        """Find the first '{' and the last '}' and convert the text between them to a dict."""
        start = text_data.find("{")
        end = text_data.rfind("}")
        if start == -1 or end == -1 or end < start:
            print("Could not find JSON object in text.")
            return None
        json_str = text_data[start:end+1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            print(f"Problematic JSON string: {json_str}")
            return None

    def __call__(self, state: State) -> dict:
        if state.get("cur_action") is not None and state.get("cur_action_output") is not None:
            evaluation_prompt_parts = ["expected_output", "cur_task", "cur_action", "cur_action_output"]
            if state.get("prev_failed_reason") is not None:
                evaluation_prompt_parts.extend(["prev_failed_reason", "prev_action", "prev_action_output"])
            
            evaluation_prompt = pick(state, *evaluation_prompt_parts)
            prompt_text = f"Task context:\n{json.dumps(evaluation_prompt, indent=2)}\n\nPlease evaluate the outcome of the last action based on the task context."
            
            current_image_from_state_eval = state.get("cur_screenshot") 

            if current_image_from_state_eval is None:
                print("EvaluationAgent: Screenshot is None before processing.")
                return {"status": False, "prev_failed_reason": "Missing screenshot for evaluation."}

            pil_image_to_send_eval = current_image_from_state_eval
            if isinstance(current_image_from_state_eval, io.BytesIO):
                current_image_from_state_eval.seek(0)
                pil_image_to_send_eval = Image.open(current_image_from_state_eval)
            
            if not isinstance(pil_image_to_send_eval, Image.Image):
                print("EvaluationAgent: Screenshot is not a valid PIL Image after conversion.")
                return {"status": False, "prev_failed_reason": "Failed to process screenshot for evaluation."}

            if self.gemini_model:
                message_parts_eval = []
                img_byte_arr_eval = io.BytesIO()
                pil_image_to_send_eval.save(img_byte_arr_eval, format='PNG')
                base64_image_eval = base64.b64encode(img_byte_arr_eval.getvalue()).decode('utf-8')
                
                image_part_eval = {
                    "inline_data": {
                        "mime_type": "image/png",
                        "data": base64_image_eval
                    }
                }
                message_parts_eval.append(image_part_eval)
                message_parts_eval.append({"text": "The image is the current screenshot."})
                message_parts_eval.append({"text": prompt_text})

                print(f"EvaluationAgent Input (Text):\n---\n{prompt_text}\n---")
                if pil_image_to_send_eval:
                    print("EvaluationAgent Input: Includes screenshot.")
                else:
                    print("EvaluationAgent Input: No screenshot.")
                
                evaluation_response = self.gemini_model.generate_content(contents=message_parts_eval)
                if evaluation_response.candidates and evaluation_response.text: # Added candidates check
                    print(f"EvaluationAgent Output (Raw Text):\n---\n{evaluation_response.text}\n---")
                    evaluation_data = self.convert_text_to_dict(evaluation_response.text)
                    if evaluation_data:
                        status = bool(evaluation_data.get("status"))
                        reason = evaluation_data.get("reason")
                        # Log the evaluation
                        try:
                            with open("evaluation_agent_log.txt", "a", encoding='utf-8') as f:
                                f.write(f"--- Evaluation Entry ---\n")
                                f.write(f"Action Task: {state.get('cur_task', {}).get('request', 'N/A')}\n")
                                f.write(f"Action Taken: {state.get('cur_action', 'N/A')}\n")
                                f.write(f"Action Output: {str(state.get('cur_action_output', 'N/A'))}\n")
                                f.write(f"Evaluation Status: {status}\n")
                                f.write(f"Evaluation Reason: {reason}\n")
                                f.write(f"--- End Evaluation ---\n\n")
                        except Exception as e:
                            print(f"Error writing to evaluation_agent_log.txt: {e}")
                        return {"status": status, "prev_failed_reason": reason}
                    else:
                        try:
                            with open("evaluation_agent_log.txt", "a", encoding='utf-8') as f:
                                f.write(f"--- Evaluation Entry ---\n")
                                f.write(f"Action Task: {state.get('cur_task', {}).get('request', 'N/A')}\n")
                                f.write(f"Action Taken: {state.get('cur_action', 'N/A')}\n")
                                f.write(f"Action Output: {str(state.get('cur_action_output', 'N/A'))}\n")
                                f.write(f"Evaluation Status: False (Parse Error)\n")
                                f.write(f"Evaluation Reason: Could not parse evaluation output from model: {evaluation_response.text[:200]}...\n")
                                f.write(f"--- End Evaluation ---\n\n")
                        except Exception as e:
                            print(f"Error writing to evaluation_agent_log.txt: {e}")
                        return {"status": False, "prev_failed_reason": "Could not parse evaluation output."}
                else: 
                    print("No evaluation text found")
                    if evaluation_response.prompt_feedback:
                         print(f"EvaluationAgent: Prompt Feedback: {evaluation_response.prompt_feedback}")
                    try:
                        with open("evaluation_agent_log.txt", "a", encoding='utf-8') as f:
                            f.write(f"--- Evaluation Entry ---\n")
                            f.write(f"Action Task: {state.get('cur_task', {}).get('request', 'N/A')}\n")
                            f.write(f"Action Taken: {state.get('cur_action', 'N/A')}\n")
                            f.write(f"Action Output: {str(state.get('cur_action_output', 'N/A'))}\n")
                            f.write(f"Evaluation Status: False (No Text)\n")
                            f.write(f"Evaluation Reason: No evaluation text received from model.\n")
                            f.write(f"--- End Evaluation ---\n\n")
                    except Exception as e:
                        print(f"Error writing to evaluation_agent_log.txt: {e}")
                    return {"status": False, "prev_failed_reason": "No evaluation text received from model."}
            else: 
                print(f"{self.__class__.__name__}: Gemini model not available.")
                try:
                    with open("evaluation_agent_log.txt", "a", encoding='utf-8') as f:
                        f.write(f"--- Evaluation Entry ---\n")
                        f.write(f"Action Task: {state.get('cur_task', {}).get('request', 'N/A')}\n")
                        f.write(f"Action Taken: {state.get('cur_action', 'N/A')}\n")
                        f.write(f"Action Output: {str(state.get('cur_action_output', 'N/A'))}\n")
                        f.write(f"Evaluation Status: False (Model Unavailable)\n")
                        f.write(f"Evaluation Reason: {self.__class__.__name__} model not available.\n")
                        f.write(f"--- End Evaluation ---\n\n")
                except Exception as e:
                    print(f"Error writing to evaluation_agent_log.txt: {e}")
                return {"status": False, "prev_failed_reason": f"{self.__class__.__name__} model not available."}
        else:
            print("EvaluationAgent: Missing current action or action output for evaluation.")
            try:
                with open("evaluation_agent_log.txt", "a", encoding='utf-8') as f:
                    f.write(f"--- Evaluation Entry ---\n")
                    f.write(f"Action Task: {state.get('cur_task', {}).get('request', 'N/A')}\n")
                    f.write(f"Evaluation Status: False (Missing Info)\n")
                    f.write(f"Evaluation Reason: Missing current action or action output for evaluation.\n")
                    f.write(f"--- End Evaluation ---\n\n")
            except Exception as e:
                print(f"Error writing to evaluation_agent_log.txt: {e}")
            return {"status": False, "prev_failed_reason": "Missing action/output for evaluation."} 