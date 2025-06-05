# Omni-Agent: Internal Architecture and Workflow

This document outlines the internal architecture and operational flow of the Omni-Agent, an autonomous system designed for UI interaction and task automation.

## Core Philosophy

The agent operates on a graph-based workflow, managing state and transitioning between specialized AI agents to understand user requests, perceive UI elements, plan actions, and execute them in a continuous loop.

## Key Components

### 1. State Management (`src/core/state.py`)
At the heart of the system is a **State** object. This object tracks all relevant information throughout the lifecycle of a user request, including:
- The original user request and expected outcome.
- The current plan (list of tasks) and the index of the current task.
- Outputs from various agents (Search Agent guide, Image Agent description, Planning Agent's new tasks, Action Agent's result).
- The current screenshot, detected UI elements, and last action performed.
- Agent histories (for Image and Planning agents).
- Error messages.

All agents and graph nodes read from and write to this state, ensuring a consistent view of the ongoing process.

### 2. Workflow Orchestration (`src/core/main.py`)
`main.py` is responsible for setting up and running the main operational loop defined using a state graph (e.g., LangGraph). It initializes agents and defines the sequence of operations:

1.  **Search (Once)**: A `SearchAgent` first processes the initial request to generate a high-level guide.
2.  **Main Loop**: The workflow then enters a continuous loop:
    a.  **Screenshot**: Captures the current screen and identifies UI elements.
    b.  **Image Analysis**: An `ImageAgent` analyzes the screenshot to provide a textual description and identify interactable elements, maintaining a history to note changes.
    c.  **Planning**: A `PlanningAgent` uses the search guide (initially), the image analysis, and its own conversational history (of previous plans and actions) to decide on the next steps. It either generates a new list of sub-tasks or outputs "continue" if the previous plan is still valid and has pending steps.
    d.  **Action**: If there's a sub-task to perform, an `ActionAgent` takes the sub-task details, the image analysis, detected UI elements, and the direct screenshot to execute a specific UI interaction (e.g., click, type) using low-level input functions.
    e.  The loop then repeats from the Screenshot step.

### 3. Specialized Agents (`src/agents/`)

The system employs several AI-driven agents:

#### a. Search Agent (`src/agents/search_agent.py`)
- **Responsibility**: To perform an initial web search based on the user's request and expected output.
- **Inputs**: `original_request`, `original_expected_output`.
- **Process**: Uses a generative AI model with search capabilities.
- **Outputs**: `search_agent_guide` (a brief textual guide for completing the task).

#### b. Image Agent (`src/agents/image_agent.py`)
- **Responsibility**: To analyze the current screenshot of the UI.
- **Inputs**: The current screenshot image.
- **Process**: Uses a generative AI model to: 
    1. Provide a concise description of the GUI shown.
    2. List visible, interactable UI elements.
    It maintains a history to notice changes from previous screenshots.
- **Outputs**: `image_agent_output` (textual description and element list).

#### c. Planning Agent (`src/agents/planning_agent.py`)
- **Responsibility**: To devise a sequence of actionable sub-tasks or decide to continue with an existing plan.
- **Inputs** (varies by `plan_mode`):
    - Initial: `original_request`, `original_expected_output`, `search_agent_guide`, `image_agent_output`.
    - Replan: `original_request`, `original_expected_output`, `image_agent_output`, `last_action_done`, `step`.
    - Crucially, it uses its own **conversational history** to recall the previously generated plan.
- **Process**: Uses a generative AI model. Based on the inputs and its history, it either:
    - Generates a new list of sub-tasks (each with a request and expected output).
    - Outputs the string "continue" if it deems the prior plan (from its history) is still viable and has pending steps.
- **Outputs**: `newly_planned_tasks` (either the list of sub-tasks or the string "continue").

#### d. Action Agent (`src/agents/action_agent.py`)
- **Responsibility**: To execute the current sub-task identified from the `task_list`.
- **Inputs**: The current sub-task's request and expected output, `image_agent_output`, `current_elements` (from screenshot node), and the **current screenshot image** directly.
- **Process**:
    - Uses a generative AI model (with function calling) to determine the specific UI interaction needed (e.g., click, type).
    - The model's decision is informed by the sub-task, the textual UI description, the structured list of UI elements, and the direct visual context from the screenshot.
    - Calls low-level functions (from `src/utils/input_functions.py`) for actual UI interaction.
- **Outputs**: `action_agent_tool_call_name` and `action_result` (the outcome of the function call).

### 4. Graph Nodes in `main.py` (beyond agents)
- **`screenshot_node`**: Takes the screenshot, performs Omni processing (if models available) to identify elements, and updates the state with `current_screenshot` and `current_elements`.
- **`process_planning_output_node`**: Handles the `PlanningAgent`'s output. If new tasks are provided, it updates the main `task_list`. If "continue" is received and the current `task_list` is exhausted, it triggers a history refresh for the `PlanningAgent` and `ImageAgent` and resets `plan_mode` to "initial".
- **`update_after_action_node`**: Updates state with `last_action_done` and `step` after an action is completed and advances `current_task_index`.
- **`should_action_or_loop` (Conditional Edge Logic)**: Directs flow to `action_agent_node` if there's an actionable task, or back to `loop_entry` (effectively to `screenshot_node`) if no task is pending (e.g., after "continue" on an exhausted list or an empty plan from planner).

### 5. Utilities (`src/utils/`)

-   **`Omni_loader.py`**: Loads AI models for screen understanding (SOM for object detection, captioning models).
-   **`screenshot.py`**: Captures screenshots and uses Omni models (via `model_helpers.py`) to detect UI elements, their content, coordinates, and types.
-   **`model_helpers.py`**: (Assumed to contain functions for running object detection and image captioning models – not directly modified in this refactor but used by `screenshot.py`).
-   **`input_functions.py`**: Provides low-level UI interaction functions like `click(x, y)`, `type(text)`, etc., callable by the `ActionAgent`.
-   **`function_definitions.py`**: Contains JSON schemas for the functions available to the `ActionAgent`'s model.
-   **`config/settings.py`**: Stores configurations like API keys, model paths, and prompt paths.

## Operational Flow Summary

1.  **Initialization**: `main.py` loads settings and initializes all agents and the LangGraph structure.
2.  **Search (Once)**: The `SearchAgent` processes the `original_request` and `original_expected_output` to produce a `search_agent_guide`.
3.  **Main Interaction Loop**: The graph transitions to a loop starting with `loop_entry`:
    a.  **Screenshot (`screenshot_node`)**: Captures the screen, processes it (potentially with Omni models) to get `current_screenshot` (image) and `current_elements` (list of UI element data like coordinates, content, type).
    b.  **Image Analysis (`image_agent_node`)**: The `ImageAgent` receives `current_screenshot`, analyzes it using its history, and produces `image_agent_output` (textual description of the UI and interactable elements).
    c.  **Planning (`planning_agent_node`)**: The `PlanningAgent` takes current context (`image_agent_output`, `search_agent_guide` if initial, `last_action_done` etc. if replan) and its conversational history to produce `newly_planned_tasks` (a list of sub-tasks or the string "continue").
    d.  **Process Planning Output (`process_planning_output_node`)**: 
        - If new tasks: `task_list` in state is updated, `current_task_index` reset.
        - If "continue" and `task_list` is complete/empty: Histories of `ImageAgent` and `PlanningAgent` are cleared, `plan_mode` becomes "initial".
    e.  **Decision (`should_action_or_loop`)**: 
        - If `task_list` has a pending task at `current_task_index`: Proceed to Action.
        - Else (no task, or error): Loop back to `loop_entry` (for a new screenshot and cycle).
    f.  **Action (`action_agent_node`)**: If a task is pending, the `ActionAgent` receives the sub-task details, `image_agent_output`, `current_elements`, and the `current_screenshot`. It determines and executes a UI function call. Produces `action_result`.
    g.  **Update After Action (`update_after_action_node`)**: `last_action_done` and `step` are updated in the state. `current_task_index` is incremented.
    h.  The flow returns to `loop_entry`.
4.  **Workflow End**: The loop can be ended by an error condition in `should_action_or_loop` or if a maximum iteration count (safety break) is hit.
5.  **Logging**: Agents log their inputs, outputs, and significant decisions to respective log files.

This revised flow emphasizes continuous perception and adaptation, with planning decisions closely tied to the latest visual and textual understanding of the UI. It is acknowledged that this iterative process can be slow.
