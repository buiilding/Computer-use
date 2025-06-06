import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(SCRIPT_DIR)
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import io
import PIL.Image as Image
from langgraph.graph import StateGraph, START, END
from typing import Literal

from config import settings
from core.state import State
from agents.planning_agent import PlanningAgent
from agents.action_agent import ActionAgent
from agents.search_agent import SearchAgent
from agents.image_agent import ImageAgent
from utils.Omni_loader import initialize_omni_models
from utils import screenshot as screenshot_util
from utils import input_functions


global_som_model, global_caption_model_processor, global_rapid_ocr_engine = None, None, None
planning_agent_instance: PlanningAgent
action_agent_instance: ActionAgent
search_agent_instance: SearchAgent
image_agent_instance: ImageAgent

def initialize_agents():
    global global_som_model, global_caption_model_processor, global_rapid_ocr_engine
    global planning_agent_instance, action_agent_instance, search_agent_instance, image_agent_instance

    global_som_model, global_caption_model_processor, global_rapid_ocr_engine = initialize_omni_models(
        settings.OMNI_DEVICE, settings.SOM_MODEL_PATH, settings.CAPTION_MODEL_PATH, settings.RAPID_OCR_ENABLED
    )
    if global_som_model is None or global_caption_model_processor is None or global_rapid_ocr_engine is None:
        print("Warning: Omni models (SOM, Caption) or RAPID_OCR failed to initialize. AI-assisted screenshot analysis will be impacted.")
    else:
        print("Omni (SOM/Caption) models initialized successfully.")

    search_agent_instance = SearchAgent(model_name=settings.SEARCH_MODEL_NAME)
    planning_agent_instance = PlanningAgent()
    image_agent_instance = ImageAgent()
    action_agent_instance = ActionAgent()


def search_agent_node(state: State) -> dict:
    print("--- Running Search Agent ---")
    return search_agent_instance(state)

def screenshot_node(state: State) -> dict:
    print("--- Taking Screenshot ---")
    if global_som_model is None or global_caption_model_processor is None:
        print("Screenshot Node: Omni models not available. Cannot take AI-assisted screenshot.")
        return {"current_screenshot": None, "current_elements": None, "error_message": "Omni models unavailable for screenshot."}

    screenshot_bytes_io, elements = screenshot_util.take_screenshot(
        global_som_model, global_caption_model_processor, global_rapid_ocr_engine, omni_enabled=True
    )
    
    pil_image = None
    if isinstance(screenshot_bytes_io, io.BytesIO):
        screenshot_bytes_io.seek(0)
        pil_image = Image.open(screenshot_bytes_io)
    elif isinstance(screenshot_bytes_io, Image.Image):
        pil_image = screenshot_bytes_io
        
    if pil_image:
        print(f"Screenshot Node: Screenshot taken. {len(elements) if elements else 0} elements identified.")
        return {"current_screenshot": pil_image, "current_elements": elements}
    else:
        print("Screenshot Node: Failed to capture or process screenshot.")
        return {"current_screenshot": None, "current_elements": None, "error_message": "Failed to capture/process screenshot."}


def image_agent_node(state: State) -> dict:
    print("--- Running Image Agent ---")
    return image_agent_instance(state)

def planning_agent_node(state: State) -> dict:
    print("--- Running Planning Agent ---")
    return planning_agent_instance(state)

def action_agent_node(state: State) -> dict:
    print("--- Running Action Agent ---")
    return action_agent_instance(state)

def process_planning_output_node(state: State) -> dict:
    print("--- Processing Planning Output ---")
    updates = {}
    planner_output = state.get("newly_planned_tasks")
    current_task_list = list(state.get("task_list", []))
    current_idx = state.get("current_task_index", 0)

    if isinstance(planner_output, list):
        print(f"Planner generated new task list with {len(planner_output)} tasks.")
        updates["task_list"] = planner_output
        updates["current_task_index"] = 0
        updates["plan_mode"] = "replan"
        if not planner_output:
            print("Planner returned an empty list of tasks. Looping back.")
    elif isinstance(planner_output, str) and planner_output.lower() == "continue":
        print("Planner said 'continue'.")
        if current_idx >= len(current_task_list) :
             print("Planner said 'continue' and no more tasks in current list or at end of list. Refreshing agent histories.")
             planning_agent_instance.history = []
             image_agent_instance.history = []
             updates["plan_mode"] = "initial"
             updates["task_list"] = []
             updates["current_task_index"] = 0
    else:
        print(f"Planner returned unexpected output: {planner_output}. Erroring or looping.")
        updates["error_message"] = f"Unexpected planner output: {planner_output}"
    
    updates["newly_planned_tasks"] = None
    return updates

def update_after_action_node(state: State) -> dict:
    print("--- Updating After Action ---")
    updates = {}
    task_list = state.get("task_list", [])
    current_idx = state.get("current_task_index")

    if task_list and current_idx is not None and 0 <= current_idx < len(task_list):
        completed_task = task_list[current_idx]
        updates["last_action_done"] = completed_task.get("request")
        updates["step"] = completed_task.get("step", current_idx + 1)
        updates["current_task_index"] = current_idx + 1
        print(f"Action completed for task {current_idx}. Last action: {updates['last_action_done']}. Next index: {updates['current_task_index']}")
    else:
        print("Error in update_after_action: Invalid task list or index.")
        updates["current_task_index"] = (current_idx + 1) if current_idx is not None else 0

    return updates


def should_action_or_loop(state: State) -> Literal["action_agent_node", "loop_entry", END]:
    print("--- Deciding: Action or Loop? ---")
    if state.get("error_message"):
        print(f"Error detected: {state.get('error_message')}. Ending workflow.")
        return END
        
    task_list = state.get("task_list", [])
    current_idx = state.get("current_task_index")

    if task_list and current_idx is not None and 0 <= current_idx < len(task_list):
        print(f"Proceeding to action for task {current_idx} of {len(task_list)}.")
        return "action_agent_node"
    else:
        print("No actionable task. Looping back to screenshot.")
        return "loop_entry"

def run_workflow(initial_request: str, initial_expected_output: str):
    for log_file in settings.LOG_FILES:
        try:
            with open(log_file, "w", encoding='utf-8') as f: f.write("")
            print(f"Log file {log_file} cleared/created.")
        except Exception as e:
            print(f"Warning: Could not clear/create log file {log_file}: {e}")

    if not settings.GEMINI_API_KEY:
        print("Fatal: GEMINI_API_KEY not set. Workflow cannot proceed.")
        return

    initialize_agents()

    graph_builder = StateGraph(State)

    graph_builder.add_node("search_agent_node", search_agent_node)
    graph_builder.add_node("loop_entry", lambda state: state)
    graph_builder.add_node("screenshot_node", screenshot_node)
    graph_builder.add_node("image_agent_node", image_agent_node)
    graph_builder.add_node("planning_agent_node", planning_agent_node)
    graph_builder.add_node("process_planning_output_node", process_planning_output_node)
    graph_builder.add_node("action_agent_node", action_agent_node)
    graph_builder.add_node("update_after_action_node", update_after_action_node)

    graph_builder.add_edge(START, "search_agent_node")
    graph_builder.add_edge("search_agent_node", "loop_entry")
    graph_builder.add_edge("loop_entry", "screenshot_node")
    graph_builder.add_edge("screenshot_node", "image_agent_node")
    graph_builder.add_edge("image_agent_node", "planning_agent_node")
    graph_builder.add_edge("planning_agent_node", "process_planning_output_node")
    graph_builder.add_conditional_edges(
        "process_planning_output_node",
        should_action_or_loop,
        {
            "action_agent_node": "action_agent_node",
            "loop_entry": "loop_entry",
            END: END
        }
    )
    graph_builder.add_edge("action_agent_node", "update_after_action_node")
    graph_builder.add_edge("update_after_action_node", "loop_entry")

    graph = graph_builder.compile()
    print("LangGraph compiled successfully with new workflow.")

    initial_state_data = State(
        original_request=initial_request,
        original_expected_output=initial_expected_output,
        search_agent_guide=None,
        current_screenshot=None,
        current_elements=None,
        image_agent_output=None,
        last_action_done=None,
        step=None,
        plan_mode="initial",
        task_list=[],
        current_task_index=0,
        newly_planned_tasks=None,
        action_result=None,
        error_message=None
    )

    print("Starting graph stream with new workflow...")
    for event_idx, event in enumerate(graph.stream(initial_state_data, config={"recursion_limit": 200})):
        print(f"\n--- Event {event_idx} ---")
        for node_name, node_output_dict in event.items():
            print(f"{node_name}:")
            if isinstance(node_output_dict, dict):
                element_keys = ["current_elements", "task_list", "newly_planned_tasks"]
                image_keys = ["current_screenshot"]
                
                for k, v in node_output_dict.items():
                    if k in element_keys and isinstance(v, list):
                        print(f"  {k}: <{len(v) if v is not None else 0} elements/tasks omitted>")
                    elif k in image_keys or isinstance(v, Image.Image) or isinstance(v, io.BytesIO):
                        print(f"  {k}: <image_data_omitted>")
                    else:
                        print(f"  {k}: {v}")
            else:
                print(f"  {node_output_dict}")
        print("--- End Event ---")
        if event_idx > 500:
            print("Stopping due to event limit (safety break).")
            break
            
    print("Workflow finished or stopped.")

if __name__ == "__main__":
    print("Running workflow directly via __main__")
    print(f"Current Working Directory: {os.getcwd()}")
    run_workflow(
        initial_request="Go to amazon.com and search for the cheapest laptop.",
        initial_expected_output="Search results for the cheapest laptop are displayed."
    ) 