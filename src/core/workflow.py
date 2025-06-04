import os
import sys # Add this import

# Add src/ directory to Python's search path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(SCRIPT_DIR)
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import io
import PIL.Image as Image # For type checking in print loop
from langgraph.graph import StateGraph, START, END

# Project-specific imports (which should now work)
from config import settings # Will look in src/config.py (or src/config/__init__.py)
from state import State # The main state definition
from agents.planning_agent import PlanningAgent # Will look in src/agents/planning_agent.py
from agents.action_agent import ActionAgent
from agents.evaluation_agent import EvaluationAgent
from controller import update_task_list_node, controller_node # Controller logic
from utils.Omni_loader import initialize_omni_models # Will look in src/utils/Omni_loader.py

def run_workflow(initial_request: str, initial_expected_output: str):
    """Sets up and runs the LangGraph workflow."""

    # Clear/Create log files at the start of each run
    for log_file in settings.LOG_FILES:
        try:
            # Ensure the directory for log files exists if they are not in the current dir
            # os.makedirs(os.path.dirname(log_file), exist_ok=True) # If logs are in a sub-directory
            with open(log_file, "w", encoding='utf-8') as f:
                f.write("") # Clear the file
            print(f"Log file {log_file} cleared/created.")
        except Exception as e:
            print(f"Warning: Could not clear/create log file {log_file}: {e}")

    if not settings.GEMINI_API_KEY:
        # This was a ValueError in Ho.py, changed to a print and early exit
        # to align with settings.py allowing GEMINI_API_KEY to be initially None.
        print("Fatal: GEMINI_API_KEY not set. Workflow cannot proceed.")
        return

    # Initialize Omni models (SOM, Caption)
    # These are loaded once and passed to agents that need them.
    print("Attempting to initialize Omni (SOM/Caption) models...")
    global_som_model, global_caption_model_processor = initialize_omni_models(settings.OMNI_DEVICE, settings.SOM_MODEL_PATH, settings.CAPTION_MODEL_PATH)
    if global_som_model is None or global_caption_model_processor is None:
        print("Warning: One or both Omni models (SOM, Caption) failed to initialize. AI-assisted screenshot analysis will be impacted.")
    else:
        print("Omni (SOM/Caption) models initialized successfully.")

    # Initialize agents, passing models if they were loaded
    # The API key is handled by BaseAgent via settings.GEMINI_API_KEY
    planning_agent = PlanningAgent( 
        som_model=global_som_model, 
        caption_model_processor=global_caption_model_processor
    )
    action_agent = ActionAgent(
        som_model=global_som_model, 
        caption_model_processor=global_caption_model_processor
    )
    evaluation_agent = EvaluationAgent()

    # Build LangGraph
    graph_builder = StateGraph(State)
    graph_builder.add_node("plan", planning_agent) # Agent instances are callable
    graph_builder.add_node("update_task_list", update_task_list_node)
    graph_builder.add_node("action", action_agent)
    graph_builder.add_node("evaluate", evaluation_agent)
    graph_builder.add_node("controller", controller_node)

    # Define edges
    graph_builder.add_edge(START, "plan")
    graph_builder.add_edge("plan", "update_task_list")
    graph_builder.add_edge("update_task_list", "controller")
    graph_builder.add_edge("action", "evaluate")
    graph_builder.add_edge("evaluate", "controller")
    graph_builder.add_conditional_edges("controller", controller_node) # Already has END logic

    graph = graph_builder.compile()
    print("LangGraph compiled successfully.")

    # Define initial state for the graph
    initial_state_data = State(
        original_request=initial_request,
        original_expected_output=initial_expected_output, 
        request=initial_request, 
        expected_output=initial_expected_output,
        plan_mode="initial",
        task_to_decompose_index=None,
        task_list=[],
        task_index=0,
        cur_task=None,
        cur_screenshot=None, 
        cur_elements=None,
        cur_action=None,
        cur_action_output=None,
        prev_action=None,
        prev_action_output=None,
        status=None, 
        prev_failed_reason=None,
        action_attempts_on_cur_task=0,
        decomposition_attempts_on_cur_task=0,
        full_replan_attempts_on_original=0,
        error_message=None,
        new_tasklist=None,
        cur_screenshot_from_planner=None,
        cur_elements_from_planner=None
    )

    print("Starting graph stream...")
    # Stream and print events
    for event in graph.stream(initial_state_data, config={"recursion_limit": 200}):
        print("\n--- Event ---")
        for node_name, node_output_dict in event.items():
            print(f"{node_name}:") 
            if isinstance(node_output_dict, dict):
                element_keys = ["cur_elements", "cur_elements_from_planner", "new_elements", "elements_for_prompt", "task_list", "new_tasklist"]
                image_keys = ["cur_screenshot", "cur_screenshot_from_planner", "effective_screenshot_for_gemini"]
                
                for k, v in node_output_dict.items():
                    if k in element_keys:
                        print(f"  {k}: <{len(v) if v is not None else 0} elements_omitted>")
                    elif k in image_keys or isinstance(v, Image.Image) or isinstance(v, io.BytesIO):
                        print(f"  {k}: <image_data_omitted>")
                    elif k == "cur_task" and isinstance(v, dict):
                        task_desc = v.get('request', 'N/A')
                        task_eo = v.get('expected_output', 'N/A')
                        print(f"  {k}: {{ 'request': '{task_desc}', 'expected_output': '{task_eo}', ...other_details_omitted}}")
                    else:
                        print(f"  {k}: {v}") 
            else:
                print(f"  {node_output_dict}")
        print("--- End Event ---")

    # Final state after streaming (optional, as stream events show progression)
    # final_state = graph.invoke(initial_state_data, config={"recursion_limit": 200})
    # print("\n--- Final State ---")
    # for k, v in final_state.items():
    #     if isinstance(v, Image.Image):
    #         print(f"{k}: <PIL.Image.Image object at ...>")
    #     else:
    #         print(f"{k}: {v}")
    print("Workflow finished.")

if __name__ == "__main__":
    # This allows running the workflow directly from this file for testing
    # Ensure that when run this way, Python can find the src modules (e.g., run from omni-agent/)
    # Example: python -m src.core.workflow
    print("Running workflow directly via __main__")
    
    # Check current working directory to ensure prompts can be loaded if paths are relative to project root
    print(f"Current Working Directory: {os.getcwd()}") 
    
    # For direct execution, you might need to adjust Python path if running from within src/core
    # sys.path.append(os.path.join(os.path.dirname(__file__), "..")) # Add src to path if needed
    
    # To run the workflow, you would call it like this:
    # Make sure that the 'test_prompts' directory is at the root of your project as expected by BaseAgent
    run_workflow(
        initial_request="Go to Amazon.com and search for 'laptop'.",
        initial_expected_output="I have found a laptop on Amazon.com."
    ) 