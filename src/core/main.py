import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(SCRIPT_DIR)
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import time
import PIL.Image as Image
import json

from config import settings
from core.state import State
from agents.search_agent import SearchAgent
from agents.main_agent import MainAgent
from utils.Omni_loader import initialize_omni_models
from utils import screenshot as screenshot_util

def run_workflow(initial_request: str, initial_expected_output: str, simulation_mode: bool = False):
    # Clear logs
    for log_file in settings.LOG_FILES:
        try:
            # Construct the full path to the log file
            log_path = os.path.join(settings.PROJECT_ROOT, log_file)
            # Ensure the directory exists
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "w", encoding='utf-8') as f:
                f.write("")
            print(f"Log file {log_path} cleared.")
        except Exception as e:
            print(f"Warning: Could not clear log file {log_file}: {e}")

    if not settings.GEMINI_API_KEY:
        print("Fatal: GEMINI_API_KEY not set. Workflow cannot proceed.")
        return

    # Initialize models and agents
    som_model, caption_model_processor, rapid_ocr_engine = initialize_omni_models(
        settings.OMNI_DEVICE, settings.SOM_MODEL_PATH, settings.CAPTION_MODEL_PATH, settings.RAPID_OCR_ENABLED
    )
    search_agent = SearchAgent(model_name=settings.SEARCH_MODEL_NAME)
    main_agent = MainAgent()

    # Initial state
    state = State(
        original_request=initial_request,
        original_expected_output=initial_expected_output,
    )

    # Step 1: Run Search Agent to get a guide
    print("--- Running Search Agent ---")
    search_result = search_agent(state)
    state["search_agent_guide"] = search_result.get("search_agent_guide")
    print(f"Search Agent Guide:\n{state['search_agent_guide']}")

    if simulation_mode:
        print("\n--- Running in Simulation Mode ---")
        # Define the sequence of simulated screenshots (JSON files)
        simulation_files = [
            "desktop_elements.json",
            "newtab_elements.json",
            "amazon_homepage.json",
            "laptop_page.json",
            "laptop_page_dropdown.json",
            "cheapest_laptop_page.json",
            "single_cheapest.json"
        ]
        simulation_path = os.path.join(SRC_DIR, "core", "test_json_elements")
        simulation_file_paths = [os.path.join(simulation_path, f) for f in simulation_files]

        # Simulation loop
        for i, json_file_path in enumerate(simulation_file_paths):
            print(f"\n--- Simulation Iteration {i + 1}: Using {os.path.basename(json_file_path)} ---")

            # Load elements from JSON file
            try:
                with open(json_file_path, "r", encoding='utf-8') as f:
                    elements = json.load(f)
                state["current_elements"] = elements
                state["current_screenshot"] = None # No image in simulation mode
                print(f"Loaded {len(elements) if elements else 0} elements from simulation file.")
            except FileNotFoundError:
                print(f"Error: Simulation file not found: {json_file_path}. Ending workflow.")
                break
            except json.JSONDecodeError:
                print(f"Error: Could not decode JSON from {json_file_path}. Ending workflow.")
                break
            
            # Call Main Agent
            agent_output = main_agent(state)

            # Update state with the results of the last action for the next turn
            state["previous_thinking"] = agent_output.get("thoughts")
            state["previous_action_result"] = str(agent_output.get("action_result"))

            if "error" in agent_output:
                print(f"Error from Main Agent: {agent_output['error']}")
                time.sleep(2)
                continue
                
            function_call = agent_output.get("function_call")
            
            # Check for task completion
            is_task_done = False
            if isinstance(function_call, str) and function_call == "task_done":
                is_task_done = True
            elif isinstance(function_call, list) and "task_done" in function_call:
                is_task_done = True

            if is_task_done:
                print("--- Task Complete ---")
                
                reason = "No reason given."
                action_result = agent_output.get("action_result")
                if isinstance(action_result, list):
                    # Find the 'task_done' output in the list of results
                    task_done_output = next((r for r in action_result if r.get("function_name") == "task_done"), None)
                    if task_done_output and isinstance(task_done_output.get("output"), dict):
                        reason = task_done_output["output"].get("message", reason)
                elif isinstance(action_result, dict):
                     reason = action_result.get("message", reason)

                print(f"Reason: {reason}")
                break
            
            time.sleep(1)
    else:
        # Step 2: Main loop
        iteration = 0
        while iteration < 100: # Safety break
            iteration += 1
            print(f"\n--- Iteration {iteration} ---")

            # Take screenshot
            print("--- Taking Screenshot ---")
            screenshot_bytes_io, elements = screenshot_util.take_screenshot(
                som_model, caption_model_processor, rapid_ocr_engine, omni_enabled=True
            )
            if screenshot_bytes_io:
                screenshot_bytes_io.seek(0)
                state["current_screenshot"] = Image.open(screenshot_bytes_io)
                state["current_elements"] = elements
                print(f"Screenshot taken. {len(elements) if elements else 0} elements identified.")
            else:
                print("Error: Failed to take screenshot. Ending workflow.")
                break
            
            # Call Main Agent
            agent_output = main_agent(state)

            # Update state with the results of the last action for the next turn
            state["previous_thinking"] = agent_output.get("thoughts")
            state["previous_action_result"] = str(agent_output.get("action_result"))

            if "error" in agent_output:
                print(f"Error from Main Agent: {agent_output['error']}")
                time.sleep(2)
                continue
                
            function_call = agent_output.get("function_call")
            
            # Check for task completion
            # Can be a single string or a list of strings
            is_task_done = False
            if isinstance(function_call, str) and function_call == "task_done":
                is_task_done = True
            elif isinstance(function_call, list) and "task_done" in function_call:
                is_task_done = True

            if is_task_done:
                print("--- Task Complete ---")
                
                # Extract reason from the potentially nested action_result
                reason = "No reason given."
                action_result = agent_output.get("action_result")
                if isinstance(action_result, list):
                    # Find the 'task_done' output in the list of results
                    task_done_output = next((r for r in action_result if r.get("function_name") == "task_done"), None)
                    if task_done_output and isinstance(task_done_output.get("output"), dict):
                        reason = task_done_output["output"].get("message", reason)
                elif isinstance(action_result, dict):
                     reason = action_result.get("message", reason)

                print(f"Reason: {reason}")
                break
            
            time.sleep(1)

    print("\nWorkflow finished.")


if __name__ == "__main__":
    print("Running simplified workflow...")
    run_workflow(
        initial_request=settings.REQUEST,
        initial_expected_output=settings.EXPECTED_OUTPUT,
        simulation_mode=True
    ) 