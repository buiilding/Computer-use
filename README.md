# Omni-Agent: Internal Architecture and Workflow

This document outlines the internal architecture and operational flow of the Omni-Agent, an autonomous system designed for UI interaction and task automation.

## Core Philosophy

The agent operates on a graph-based workflow, managing state and transitioning between specialized AI agents to understand user requests, perceive UI elements, plan actions, execute them, and evaluate outcomes.

## Key Components

### 1. State Management (`src/core/state.py`)
At the heart of the system is a comprehensive **State** object. This object tracks all relevant information throughout the lifecycle of a user request, including:
- The original user request and expected outcome.
- The current plan (list of tasks).
- The current task being executed.
- Screenshots and detected UI elements.
- History of actions, outcomes, and errors.
- Retry counts and operational modes (e.g., initial planning, replanning, task decomposition).

All agents and a central controller read from and write to this state, ensuring a consistent view of the ongoing process.

### 2. Workflow Orchestration (`src/core/main.py`)
The **Workflow** component is responsible for setting up and running the main operational loop. It initializes the agents and compiles a state graph (likely using a library like LangGraph) that defines the possible transitions between different processing nodes (agents and controller logic). It streams the initial state into this graph to kick off the process.

### 3. Central Controller (`src/core/controller.py`)
The **Controller** acts as the central decision-making node in the graph. After each agent performs its function, the controller evaluates the current state and decides the next step. Its responsibilities include:
- Determining if a task was successful or failed based on the EvaluationAgent's output.
- Advancing to the next task in the plan if the current one is successful.
- Triggering retries for the current task if it failed and retry limits haven't been met.
- Initiating replanning (either decomposing the current failed task or generating a new plan from scratch) if a task repeatedly fails.
- Ending the workflow if all tasks are complete or if maximum retry/replan limits are exceeded.

### 4. Specialized Agents (`src/agents/`)

The system employs three primary AI-driven agents:

#### a. Planning Agent (`src/agents/planning_agent.py`)
- **Responsibility**: To understand the overall user request and break it down into a sequence of smaller, actionable sub-tasks.
- **Inputs**: The user's request, expected output, the current screenshot (if applicable, especially for replanning), and any previous failure reasons.
- **Process**: It uses a generative AI model (e.g., Gemini) to analyze the inputs and generate a structured list of tasks. Each task typically includes a specific instruction and an expected outcome. It can operate in different modes: initial planning, full replanning, or decomposing a single complex task.
- **Outputs**: A new task list, and potentially an updated screenshot and element list if it captured one for planning.

#### b. Action Agent (`src/agents/action_agent.py`)
- **Responsibility**: To execute the current task identified by the Controller. This involves interacting with the UI.
- **Inputs**: The current task, the current screenshot, detected UI elements, and history of previous (failed) actions for context.
- **Process**:
    - It uses a generative AI model (e.g., Gemini with function calling capabilities) to determine the specific UI interaction needed (e.g., click, type).
    - The model's decision is informed by the task description and the visual context from the screenshot and detected UI elements.
    - It calls low-level functions (from `src/utils/input_functions.py`) to perform the actual mouse clicks, keyboard typing, etc.
    - After performing an action, it captures a new screenshot.
- **Outputs**: The name of the action performed, the output/result of that action, and the new screenshot and detected UI elements post-action.

#### c. Evaluation Agent (`src/agents/evaluation_agent.py`)
- **Responsibility**: To assess whether the action performed by the ActionAgent successfully completed the current task.
- **Inputs**: The expected outcome of the task, the current task description, the action that was taken, the output of that action, and the latest screenshot.
- **Process**: It uses a generative AI model to compare the actual outcome (inferred from the action output and the new screenshot) against the expected outcome of the task.
- **Outputs**: A status (e.g., True for success, False for failure) and a reason for the evaluation.

### 5. Utilities (`src/utils/`)

A collection of helper modules support the core components and agents:

-   **`Omni_loader.py`**: Responsible for loading and initializing the AI models used for screen understanding (e.g., SOM/YOLO for object detection, Florence2/BLIP for captioning). These models are loaded once and passed to the agents that need them.
-   **`screenshot.py`**:
    -   Handles capturing screenshots of the current screen.
    -   Orchestrates "Omni processing" on the screenshot if models are available. This involves:
        -   Performing OCR (`detect_text_and_draw_boxes`) to find text elements.
        -   Using a Scene Object Model (SOM) or YOLO model (`get_som_labeled_img` via `model_helpers.py`) to detect UI icons and elements.
        -   Generating captions for detected elements.
    -   Returns the screenshot image and a list of detected UI elements with their properties (content, coordinates, type).
-   **`model_helpers.py`**: Contains functions for running the object detection (YOLO/SOM) and image captioning models, processing their outputs, and removing overlapping detections.
-   **`input_functions.py`**: Provides the low-level functions that the ActionAgent calls to perform actual UI interactions like `click(x, y)`, `type(text, coordinates)`, etc.
-   **`config/settings.py`**: Stores configuration values such as API keys, model paths, and workflow constants (e.g., max retry attempts).

## Operational Flow Summary

1.  **Initialization**: The `workflow.py` script sets up the environment (e.g., `sys.path` modifications for imports), loads settings, and initializes the `StateGraph`.
2.  **Request Input**: A user request (e.g., "Go to Amazon.com and search for 'laptop'") and the expected output (e.g., "The cheapest laptop is displayed on the screen") are provided as the initial input to the workflow.
3.  **Planning**:
    -   The `PlanningAgent` receives the request.
    -   It takes an initial screenshot (via `screenshot.py` which uses `Omni_loader.py` and `model_helpers.py`).
    -   It generates a list of tasks.
4.  **Task Execution Loop (managed by `Controller`)**:
    a.  The `Controller` selects the current task.
    b.  **Action**: The `ActionAgent` takes the current task and the latest screenshot (which includes elements detected by `screenshot.py`). It decides on a UI action (e.g., click button X, type 'laptop' into search bar Y) and executes it using `input_functions.py`. After the action, it captures a new screenshot.
    c.  **Evaluation**: The `EvaluationAgent` examines the result of the action (and the new screenshot) to determine if the task's expected outcome was achieved.
    d.  **Control Logic**: The `Controller` checks the evaluation:
        -   **Success**: If the task is complete, it moves to the next task in the list. If all tasks are done, the workflow ends.
        -   **Failure**:
            -   If action attempts are below a threshold, it retries the `ActionAgent` on the same task.
            -   If action attempts are exhausted, it may trigger the `PlanningAgent` to "decompose" the failed task into simpler sub-tasks.
            -   If decomposition also fails or isn't applicable, it might trigger a full "replan" by the `PlanningAgent` for the original request.
            -   If all retry and replan limits are exhausted, the workflow ends with an error.
5.  **Logging**: Throughout the process, agents log their inputs, outputs, and significant decisions to respective log files (e.g., `planning_agent_log.txt`).

This cycle of planning, acting, evaluating, and controlling allows the agent to attempt complex multi-step tasks, with mechanisms for error handling and replanning. It is super slow though.
