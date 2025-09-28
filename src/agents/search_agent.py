import os
import sys

# Add the project root to the Python path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(SCRIPT_DIR)
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from google import genai
from google.genai.types import (
    GenerateContentConfig,
    GoogleSearch,
    Tool,
)

from core.state import State
from typing import Dict, Any
from config.settings import GEMINI_API_KEY, SEARCH_PROMPT_PATH, PROJECT_ROOT

from agents.base_agent import BaseAgent
from config import settings


class SearchAgent(BaseAgent):
    def __init__(self):
        """Initializes the SearchAgent."""
        super().__init__(
            model_name=settings.SEARCH_MODEL_NAME,
            system_prompt_path=settings.SEARCH_PROMPT_PATH,
            tools=[Tool(google_search=GoogleSearch())],
            temperature=0.0
        )
        self.log_file_name = os.path.join(settings.PROJECT_ROOT, "search_agent_log.txt")

    def __call__(self, state: State) -> Dict[str, Any]:
        """
        Performs a web search based on the request and expected output in the state.

        Args:
            state: The current state object, containing 'original_request' and 'original_expected_output'.

        Returns:
            A dictionary containing the search result text or an error message.
        """
        request = state.get("original_request")
        expected_output_context = state.get("original_expected_output")

        if not request:
            print("SearchAgent: 'original_request' is missing from state.")
            return {"error": "'original_request' is missing from state."}

        user_query = f"Request: {request}"
        if expected_output_context:
            user_query += f"\nConsidering expected output context: {expected_output_context}"
        
        if not self.gemini_model:
            return {"error": "SearchAgent: Gemini model not available."}

        try:
            print("--- Calling Search Agent ---")
            response = self.gemini_model.generate_content(
                contents=[user_query]
            )
            
            search_result_text = response.text
            
            # Log the interaction
            with open(self.log_file_name, "a", encoding='utf-8') as f:
                f.write(f"--- Search Entry ---\nQuery: {user_query}\nResponse Text: {search_result_text}\n--- End Search ---\n\n")

            return {"search_agent_guide": search_result_text}

        except Exception as e:
            print(f"SearchAgent: Error during search: {e}")
            with open(self.log_file_name, "a", encoding='utf-8') as f:
                f.write(f"--- Search Error ---\nQuery: {user_query}\nError: {e}\n--- End Search Error ---\n\n")
            return {"error": str(e)}

# Example Usage (for testing purposes, if you run this file directly):
if __name__ == '__main__':

    # Mock State for testing
    mock_state = State(
        original_request="When is the next total solar eclipse in the United States?",
        original_expected_output="The date of the next total solar eclipse.",
        search_agent_guide=None,
        current_screenshot=None,
        current_elements=None,
        image_agent_output=None,
        last_action_done=None,
        step=None,
        plan_mode="initial",
        task_list=[],
        current_task_index=None,
        newly_planned_tasks=None,
        action_result=None,
        error_message=None
    )

    
    print("Attempting to initialize SearchAgent...")
    print(f"GEMINI_API_KEY is set: {'Yes' if os.getenv('GEMINI_API_KEY') else 'No'}")

    try:
        search_agent = SearchAgent() 
        print(f"SearchAgent initialized with model: {search_agent.model_name}.")
        print("Performing search...")
        result = search_agent(mock_state)
        print("\nSearch Result:")
        if "search_agent_guide" in result:
            print(result["search_agent_guide"])
        elif "error" in result:
            print(f"Error: {result['error']}")
    except ValueError as ve:
        print(f"Configuration Error: {ve}")
        print("Please ensure GEMINI_API_KEY environment variable is set.")
    except Exception as e:
        print(f"An unexpected error occurred during testing: {e}") 