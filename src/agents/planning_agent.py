import ast
import json

from .base_agent import BaseAgent
from utils import screenshot
from utils import input_functions
from config import settings
from core.state import State

class PlanningAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            model_name=settings.PLANNING_MODEL_NAME,
            system_prompt_path=settings.PLANNING_PROMPT_PATH
        )
        self.history = []
        self.log_file_name = "planning_agent_log.txt"

    def convert_to_list(self, task_list_str: str) -> list | str:
        """Find the first "[" and the last "]" and convert the text between them to a list.
        If the string is "continue", return "continue".
        """
        if task_list_str.strip().lower() == "continue":
            return "continue"
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
        output_payload = {"newly_planned_tasks": None}

        plan_prompt_context = {}
        current_plan_mode = state.get("plan_mode", "replan") # Default to replan if not set

        if current_plan_mode == "initial":
            plan_prompt_context["search_agent_guide"] = state.get("search_agent_guide")
            plan_prompt_context["image_agent_output"] = state.get("image_agent_output")
            # For initial planning, original_request and original_expected_output provide overall goal.
            # The prompt should guide the model to use search_agent_guide and image_agent_output to make the first plan.
            plan_prompt_context["original_request"] = state.get("original_request")
            plan_prompt_context["original_expected_output"] = state.get("original_expected_output")
        else: # "replan" mode
            plan_prompt_context["image_agent_output"] = state.get("image_agent_output")
            plan_prompt_context["last_action_done"] = state.get("last_action_done")
            plan_prompt_context["step"] = state.get("step")
            # The history (self.history) will contain the previous task list implicitly.
            # We also include original request/output for context during replanning if needed.
            plan_prompt_context["original_request"] = state.get("original_request")
            plan_prompt_context["original_expected_output"] = state.get("original_expected_output")
  
        prompt_text = f"{json.dumps(plan_prompt_context, indent=2)}\n"

        gemini_response_text = None
        current_user_message_content = {} # Initialize to handle cases where gemini_model might not run

        if self.gemini_model:
            try:
                current_user_message_content = {"role": "user", "parts": [{"text": prompt_text}]}
                api_contents = self.history + [current_user_message_content]
                
                print(f"PlanningAgent Input (Text to add to history):\n---\n{prompt_text}\n---")
                if self.history:
                    print(f"PlanningAgent: Sending {len(self.history)} previous turns in history.")
                print("PlanningAgent Input: No screenshot.")
                                
                task_list_response = self.gemini_model.generate_content(contents=api_contents)
                
                if hasattr(task_list_response, 'text') and task_list_response.text:
                    gemini_response_text = task_list_response.text
                elif hasattr(task_list_response, 'candidates') and task_list_response.candidates and hasattr(task_list_response.candidates[0], 'content') and hasattr(task_list_response.candidates[0].content, 'parts') and task_list_response.candidates[0].content.parts and hasattr(task_list_response.candidates[0].content.parts[0], 'text'):
                    # Fallback for different response structures if .text is not directly available
                    gemini_response_text = task_list_response.candidates[0].content.parts[0].text
                else:
                    print("PlanningAgent: No text in Gemini response or unexpected response structure.")
                    if hasattr(task_list_response, 'prompt_feedback') and task_list_response.prompt_feedback:
                        print(f"PlanningAgent: Prompt Feedback: {task_list_response.prompt_feedback}")
                    # print(f"DEBUG: Full Gemini Response: {task_list_response}") # Optional: for deeper debugging

            except Exception as e:
                print(f"Error sending message to Gemini in PlanningAgent: {e}")
        else:
            print(f"{self.__class__.__name__}: Gemini model not available.")

        if gemini_response_text:
            print(f"PlanningAgent: Raw Gemini response text:\n```\n{gemini_response_text}\n```")
            # Add successful interaction to history only if current_user_message_content was populated
            if current_user_message_content: 
                self.history.append(current_user_message_content)
                self.history.append({"role": "model", "parts": [{"text": gemini_response_text}]})

            task_list_or_continue = self.convert_to_list(gemini_response_text)
            output_payload["newly_planned_tasks"] = task_list_or_continue
            try:
                with open(self.log_file_name, "a", encoding='utf-8') as f:
                    f.write(f"--- New Plan ({current_plan_mode}) ---\n")
                    if isinstance(task_list_or_continue, list):
                        if task_list_or_continue:
                            for i, task_item in enumerate(task_list_or_continue):
                                f.write(f"Task {i+1}: {task_item.get('request', 'No request')} (Expected: {task_item.get('expected_output', 'N/A')})\n")
                        else:
                            f.write("No tasks generated.\n")
                    elif task_list_or_continue == "continue":
                        f.write("Plan deemed good. Responding with 'continue'.\n")
                    else:
                        f.write("No tasks generated or invalid response.\n")
                    f.write("--- End Plan ---\n\n")
            except Exception as e:
                print(f"Error writing to {self.log_file_name}: {e}")
        else:
            print("PlanningAgent: Failed to get a valid task list string from Gemini.")
            try:
                with open(self.log_file_name, "a", encoding='utf-8') as f:
                    f.write(f"--- New Plan ({current_plan_mode}) ---\n")
                    f.write("Failed to generate tasks from Gemini response.\n")
                    f.write("--- End Plan ---\n\n")
            except Exception as e:
                print(f"Error writing to {self.log_file_name}: {e}")

        return output_payload

if __name__ == '__main__':
    print("--- Testing PlanningAgent Independently ---")

    if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "<GEMINI_API_KEY>":
        print("GEMINI_API_KEY not set. PlanningAgent test cannot proceed with actual model call.")
    else:
        # Test Case 1: Initial Planning
        print("\n--- Test Case 1: Initial Planning ---")
        mock_state_initial_plan = State(
            original_request="Open calculator and calculate 2+2",
            original_expected_output="The calculator shows 4.",
            search_agent_guide="1. Find and open calculator app. 2. Click button '2'. 3. Click button '+'. 4. Click button '2'. 5. Click button '='.",
            image_agent_output="The screen shows a desktop with a calculator icon.",
            plan_mode="initial",
            # Other fields that might be checked or used by the agent, fill with defaults
            current_screenshot=None, # Planning agent doesn't use direct screenshot
            current_elements=None,
            last_action_done=None,
            step=None,
            task_list=[],
            current_task_index=None,
            newly_planned_tasks=None,
            action_result=None,
            error_message=None
        )

        print(f"Initializing PlanningAgent with model: {settings.PLANNING_MODEL_NAME}")
        try:
            planning_agent_test = PlanningAgent()
            if planning_agent_test.gemini_model:
                print("PlanningAgent initialized successfully for testing.")
                print("Calling PlanningAgent (Initial Plan)...")
                result_initial = planning_agent_test(mock_state_initial_plan)
                print("\nPlanningAgent Test Result (Initial Plan):")
                print(json.dumps(result_initial, indent=2))

                # Test Case 2: Replanning (Continue)
                print("\n--- Test Case 2: Replanning (Continue) ---")
                # Simulate a state where an action was done from a previous plan
                planning_agent_test.history = [
                    {"role": "user", "parts": [{"text": "Original plan context..."}]},
                    {"role": "model", "parts": [{"text": '[{"step": 1, "request": "Click calculator icon", "expected_output": "Calculator opens"}, {"step": 2, "request": "Click button 2", "expected_output": "2 is displayed"}]'}]}
                ]
                mock_state_replan_continue = State(
                    original_request="Open calculator and calculate 2+2",
                    original_expected_output="The calculator shows 4.",
                    image_agent_output="Calculator is open, '2' is displayed on the calculator screen.",
                    plan_mode="replan",
                    last_action_done="Click calculator icon",
                    step=1,
                    search_agent_guide=None, 
                    current_screenshot=None,
                    current_elements=None,
                    task_list=planning_agent_test.history[1]["parts"][0]["text"], # Mocking task list from history
                    current_task_index=1, # Implies first task was done
                    newly_planned_tasks=None,
                    action_result=None,
                    error_message=None
                )
                print("Calling PlanningAgent (Replan - expecting continue)...")
                result_replan_continue = planning_agent_test(mock_state_replan_continue)
                print("\nPlanningAgent Test Result (Replan - Continue):")
                print(json.dumps(result_replan_continue, indent=2))
            else:
                print("PlanningAgent's Gemini model not initialized. Check API key and model setup.")
        except Exception as e:
            print(f"An error occurred during PlanningAgent test: {e}") 