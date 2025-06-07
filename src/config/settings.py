import os
from dotenv import load_dotenv


# Define Project Root
# This goes from src/config/settings.py up two levels to the omni-agent directory.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

# Device and Model Paths
OMNI_DEVICE = "cuda"  # Or "cpu"
SOM_MODEL_PATH = os.path.join(PROJECT_ROOT, "weights", "icon_detect", "model.pt")
CAPTION_MODEL_PATH = os.path.join(PROJECT_ROOT, "weights", "icon_caption")
RAPID_OCR_ENABLED = True

# Log files
LOG_FILES = ["main_agent_log.txt", "search_agent_log.txt"]

# Gemini API Key
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("Warning: GEMINI_API_KEY not set in environment variables. Agents requiring it may not function.")

# Model Names
SEARCH_MODEL_NAME = "gemini-2.5-pro-preview-06-05"
MAIN_MODEL_NAME = "gemini-2.5-pro-preview-06-05"

# Prompt Paths
SEARCH_PROMPT_PATH = os.path.join(PROJECT_ROOT, "prompts", "Search_Agent.txt")
MAIN_PROMPT_PATH = os.path.join(PROJECT_ROOT, "prompts", "Main_Agent.txt")

REQUEST = "go to amazon, search for a laptop, and display the cheapest one"
EXPECTED_OUTPUT = "Successfully displayed the cheapest laptop"