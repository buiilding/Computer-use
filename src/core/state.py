from typing import TypedDict, List, Optional, Literal, Union
import PIL.Image as Image

class State(TypedDict):
    original_request: str
    original_expected_output: str
    search_agent_guide: Optional[str]
    current_screenshot: Optional[Image.Image]
    current_elements: Optional[List[dict]]
    image_agent_output: Optional[str]
    last_action_done: Optional[str]
    step: Optional[int]
    plan_mode: Optional[Literal["initial", "replan"]]
    task_list: List[dict]
    current_task_index: Optional[int]
    newly_planned_tasks: Optional[Union[List[dict], str]]
    action_result: Optional[str]
    error_message: Optional[str]

def pick(state: State, *keys) -> dict:
    return {k: state[k] for k in keys if k in state} 