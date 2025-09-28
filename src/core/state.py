from typing import TypedDict, List, Optional
import PIL.Image as Image

class State(TypedDict, total=False):
    """
    Defines the structured state passed between components of the workflow.
    `total=False` means keys are optional.
    """
    original_request: str
    original_expected_output: str
    search_agent_guide: Optional[str]
    current_screenshot: Optional[Image.Image]
    nodes: Optional[List[dict]]
    edges: Optional[List[dict]]
    previous_thinking: Optional[str]
    previous_action_result: Optional[str]

def pick(state: State, *keys) -> dict:
    return {k: state[k] for k in keys if k in state} 