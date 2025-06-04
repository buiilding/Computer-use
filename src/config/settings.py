import os

# Define Project Root
# This goes from src/config/settings.py up two levels to the omni-agent directory.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Device and Model Paths
OMNI_DEVICE = "cuda"  # Or "cpu"
SOM_MODEL_PATH = os.path.join(PROJECT_ROOT, "weights", "icon_detect", "model.pt")
CAPTION_MODEL_PATH = os.path.join(PROJECT_ROOT, "weights", "icon_caption")

# Workflow Constants
MAX_ACTION_ATTEMPTS_PER_TASK = 1
MAX_DECOMPOSITION_ATTEMPTS_PER_TASK = 3
MAX_FULL_REPLAN_ATTEMPTS = 2

# Log files
LOG_FILES = ["planning_agent_log.txt", "action_agent_log.txt", "evaluation_agent_log.txt"]

# Gemini API Key
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("Warning: GEMINI_API_KEY not set in environment variables. Agents requiring it may not function.")

# Model Names
PLANNING_MODEL_NAME = "gemini-2.0-flash"
ACTION_MODEL_NAME = "gemini-2.0-flash"
EVALUATION_MODEL_NAME = "gemini-2.0-flash" 