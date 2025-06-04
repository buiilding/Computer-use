from typing import Literal
from langgraph.types import Command
from langgraph.graph import END

from state import State
from utils.input_functions import update_global_transformed_list
from config import settings

def update_task_list_node(state: State) -> dict:
    """Processes the output of PlanningAgent to update the main task list."""
    updates = {}
    new_tasklist = state.get("new_tasklist")

    if state.get("cur_screenshot_from_planner") is not None:
        updates["cur_screenshot"] = state["cur_screenshot_from_planner"]
    if state.get("cur_elements_from_planner") is not None:
        updates["cur_elements"] = state["cur_elements_from_planner"]
        if updates["cur_elements"] is not None:
            update_global_transformed_list(updates["cur_elements"])

    current_task_list = list(state.get("task_list", []))
    new_task_index = state.get("task_index", 0)

    if new_tasklist:
        if state["plan_mode"] == "initial" or state["plan_mode"] == "replan_full":
            print(f"update_task_list_node: New plan created (mode: {state['plan_mode']}). Task count: {len(new_tasklist)}")
            updates["task_list"] = new_tasklist
            new_task_index = 0
        elif state["plan_mode"] == "decompose_task":
            task_to_decompose_idx = state.get("task_to_decompose_index")
            if task_to_decompose_idx is not None and 0 <= task_to_decompose_idx < len(current_task_list):
                print(f"update_task_list_node: Decomposing task {task_to_decompose_idx}. Inserting {len(new_tasklist)} sub-tasks.")
                current_task_list = (
                    current_task_list[:task_to_decompose_idx] +
                    new_tasklist +
                    current_task_list[task_to_decompose_idx+1:]
                )
                updates["task_list"] = current_task_list
                new_task_index = task_to_decompose_idx
            else:
                print(f"update_task_list_node: Error - Invalid task_to_decompose_index: {task_to_decompose_idx}. Retaining old task list.")
                updates["task_list"] = current_task_list 
    else: 
        print(f"update_task_list_node: PlanningAgent returned no new tasks (mode: {state['plan_mode']}).")
        if state["plan_mode"] == "initial" or state["plan_mode"] == "replan_full":
            updates["task_list"] = [] 
            new_task_index = 0

    updates["task_index"] = new_task_index
    if updates.get("task_list") and 0 <= new_task_index < len(updates.get("task_list", [])):
        updates["cur_task"] = updates["task_list"][new_task_index]
    elif current_task_list and 0 <= new_task_index < len(current_task_list) and "task_list" not in updates:
        updates["cur_task"] = current_task_list[new_task_index]
    else:
        updates["cur_task"] = None

    updates["new_tasklist"] = None
    updates["cur_screenshot_from_planner"] = None
    updates["cur_elements_from_planner"] = None
    updates["prev_failed_reason"] = None
    updates["prev_action"] = None
    updates["prev_action_output"] = None
    updates["action_attempts_on_cur_task"] = 0
    updates["decomposition_attempts_on_cur_task"] = 0
    updates["status"] = None 
    
    if "task_list" not in updates:
        updates["task_list"] = current_task_list
    
    return updates

def controller_node(state: State) -> Command[Literal["action", "plan", END]]:
    """Central logic for workflow progression, retries, and replanning."""
    updates = {}
    current_task_list = state.get("task_list", [])
    current_task_index = state.get("task_index", 0)
    current_task = state.get("cur_task")

    if state.get("status") is None: # Coming from update_task_list
        if current_task:
            print(f"Controller: Planning successful. Proceeding to action for task: {current_task.get('request')}")
            updates["action_attempts_on_cur_task"] = 0
            updates["decomposition_attempts_on_cur_task"] = 0
            updates["expected_output"] = current_task.get("expected_output", state.get("original_expected_output"))
            return Command(update=updates, goto="action")
        else: 
            print("Controller: No current task after planning.")
            replan_attempts = state.get("full_replan_attempts_on_original", 0)
            if replan_attempts < settings.MAX_FULL_REPLAN_ATTEMPTS:
                print(f"Controller: Triggering full replan (attempt {replan_attempts + 1}).")
                updates["full_replan_attempts_on_original"] = replan_attempts + 1
                updates["request"] = state["original_request"]
                updates["expected_output"] = state["original_expected_output"]
                updates["plan_mode"] = "replan_full"
                updates["prev_failed_reason"] = state.get("prev_failed_reason", "Planner failed to produce tasks.")
                return Command(update=updates, goto="plan")
            else:
                print("Controller: Max full replans reached. Ending workflow.")
                updates["error_message"] = "Exceeded max full replans after planner returned no tasks."
                return Command(update=updates, goto=END)

    if state["status"] is True:
        print(f"Controller: Task {current_task_index} ({current_task.get('request') if current_task else 'N/A'}) successful.")
        next_task_index = current_task_index + 1
        if next_task_index < len(current_task_list):
            updates["task_index"] = next_task_index
            updates["cur_task"] = current_task_list[next_task_index]
            updates["expected_output"] = updates["cur_task"].get("expected_output", state.get("original_expected_output"))
            updates["action_attempts_on_cur_task"] = 0
            updates["decomposition_attempts_on_cur_task"] = 0
            updates["prev_failed_reason"] = None
            updates["prev_action"] = None
            updates["prev_action_output"] = None
            print(f"Controller (task success): Moving to next task {next_task_index}: {updates['cur_task'].get('request')}")
            return Command(update=updates, goto="action")
        else:
            print("Controller: All tasks completed successfully. Ending workflow.")
            return Command(goto=END)
    else: # status is False
        print(f"Controller: Task {current_task_index} ({current_task.get('request') if current_task else 'N/A'}) failed. Reason: {state.get('prev_failed_reason')}")
        action_attempts = state.get("action_attempts_on_cur_task", 0) + 1
        updates["action_attempts_on_cur_task"] = action_attempts

        if action_attempts < settings.MAX_ACTION_ATTEMPTS_PER_TASK:
            print(f"Controller: Retrying action for task {current_task_index} (attempt {action_attempts}).")
            if current_task:
                 updates["expected_output"] = current_task.get("expected_output", state.get("original_expected_output"))
            return Command(update=updates, goto="action")
        else:
            updates["action_attempts_on_cur_task"] = 0
            decomposition_attempts = state.get("decomposition_attempts_on_cur_task", 0) + 1
            updates["decomposition_attempts_on_cur_task"] = decomposition_attempts

            if decomposition_attempts < settings.MAX_DECOMPOSITION_ATTEMPTS_PER_TASK:
                print(f"Controller: Triggering task decomposition for task {current_task_index} (attempt {decomposition_attempts}).")
                updates["request"] = current_task.get("request", state["original_request"])
                updates["expected_output"] = current_task.get("expected_output", state["original_expected_output"])
                updates["plan_mode"] = "decompose_task"
                updates["task_to_decompose_index"] = current_task_index
                return Command(update=updates, goto="plan")
            else:
                updates["decomposition_attempts_on_cur_task"] = 0
                full_replan_att = state.get("full_replan_attempts_on_original", 0) + 1
                updates["full_replan_attempts_on_original"] = full_replan_att

                if full_replan_att < settings.MAX_FULL_REPLAN_ATTEMPTS:
                    print(f"Controller: Triggering full replan (attempt {full_replan_att}).")
                    updates["request"] = state["original_request"]
                    updates["expected_output"] = state["original_expected_output"]
                    updates["plan_mode"] = "replan_full"
                    return Command(update=updates, goto="plan")
                else:
                    print("Controller: Max full replans reached after task failures. Ending workflow.")
                    updates["error_message"] = f"Exceeded max replans after task {current_task_index} failed repeatedly."
                    return Command(update=updates, goto=END) 