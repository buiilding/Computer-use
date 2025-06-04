from typing import TypedDict, List, Optional, Literal
import PIL.Image as Image # Added for type hint

# ---- LangGraph State Definition ----
class State(TypedDict):
    # --- Overall problem definition ---
    original_request: str
    original_expected_output: str

    # --- Current context for PlanningAgent ---
    request: str  # Current request for the planner (original, or sub-task description)
    expected_output: str # Expected output for the current planner request

    plan_mode: Literal["initial", "decompose_task", "replan_full"]
    task_to_decompose_index: Optional[int] # Index of task in task_list being decomposed

    # --- Task execution state ---
    task_list: List[dict]               # The master list of tasks
    task_index: int                     # Current index in task_list
    cur_task: Optional[dict]            # task_list[task_index] if task_list is not empty

    # --- Action Agent inputs & outputs ---
    cur_screenshot: Optional[Image.Image] # Ho.py uses PIL.Image or io.BytesIO
    cur_elements: Optional[List[dict]]
    cur_action: Optional[str]
    cur_action_output: Optional[str]
    prev_action: Optional[str]             # The action that was just evaluated
    prev_action_output: Optional[str]      # Its output

    # --- Evaluation & Retry/Replan Counters ---
    status: Optional[bool]  # Result of evaluation of cur_task's action
    prev_failed_reason: Optional[str] # Reason from evaluation, becomes prev_failed_reason for next step

    action_attempts_on_cur_task: int         # Action retries for cur_task
    decomposition_attempts_on_cur_task: int  # Decomposition attempts for cur_task

    full_replan_attempts_on_original: int   # Replans for original_request

    error_message: Optional[str]

    # --- Output from PlanningAgent ---
    # This field will be populated by the PlanningAgent node
    # and consumed by update_task_list_node
    new_tasklist: Optional[List[dict]]

    # Additional fields for update_task_list_node (populated by PlanningAgent)
    cur_screenshot_from_planner: Optional[Image.Image] # Ho.py uses PIL.Image or io.BytesIO
    cur_elements_from_planner: Optional[List[dict]]

def pick(state: State, *keys) -> dict:
    """Utility function to pick specified keys from the state."""
    return {k: state[k] for k in keys if k in state} # Added check 'if k in state' for robustness 