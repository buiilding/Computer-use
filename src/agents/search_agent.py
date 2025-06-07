import os
from google import genai
from google.genai.types import (
    GenerateContentConfig,
    GoogleSearch,
    Tool,
)

from core.state import State
from typing import Dict, Any
from config.settings import GEMINI_API_KEY, SEARCH_PROMPT_PATH, PROJECT_ROOT


class SearchAgent:
    def __init__(self, model_name: str = "gemini-2.0-flash"):
        """
        Initializes the SearchAgent.

        Args:
            model_name: The name of the Gemini model to use for generation.
                        Defaults to "gemini-2.0-flash".
        """
        api_key = GEMINI_API_KEY

        if not api_key or api_key == "<GEMINI_API_KEY>":
            print("Warning: GEMINI_API_KEY environment variable not set. This is required.")
            raise ValueError("GEMINI_API_KEY environment variable not set.")

        self.client = genai.Client(api_key=api_key)
        self.model_id = model_name
        self.google_search_tool = Tool(google_search=GoogleSearch())
        self.system_prompt = self.load_system_prompt()
        self.log_file_name = os.path.join(PROJECT_ROOT, "search_agent_log.txt")

    def load_system_prompt(self):
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        full_prompt_path = os.path.join(project_root, SEARCH_PROMPT_PATH)
        try:
            with open(full_prompt_path, "r", encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"Error: System prompt file not found at {full_prompt_path}.")
            return ""
        except Exception as e:
            print(f"Error loading system prompt for SearchAgent: {str(e)}")
            return ""

    def __call__(self, state: State) -> Dict[str, Any]:
        """
        Performs a web search based on the request and expected output in the state.

        Args:
            state: The current state object, containing 'original_request' and 'original_expected_output'.

        Returns:
            A dictionary containing the search result text or an error message.
            Example: {"search_result_text": "..."} or {"error": "..."}
        """
        request = state.get("original_request")
        expected_output_context = state.get("original_expected_output")

        if not request:
            print("SearchAgent: 'original_request' is missing from state.")
            return {"error": "'original_request' is missing from state."}

        user_query = f"Request: {request}"
        if expected_output_context:
            user_query += f"\nConsidering expected output context: {expected_output_context}"
        
        prompt_parts = [self.system_prompt, user_query]

        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt_parts,
                config=GenerateContentConfig(
                    tools=[self.google_search_tool],
                    response_modalities=["TEXT"],
                )
            )
            
            # Extract text from response parts
            search_result_text_parts = []
            if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'text'):
                        search_result_text_parts.append(part.text)
            search_result_text = "".join(search_result_text_parts)
            
            if not search_result_text and response.prompt_feedback:
                 print(f"SearchAgent: Search returned no text. Prompt Feedback: {response.prompt_feedback}")


            # Log the interaction
            try:
                with open(self.log_file_name, "a", encoding='utf-8') as f:
                    f.write(f"--- Search Entry ---\n")
                    f.write(f"Query: {user_query}\n")
                    f.write(f"Model ID: {self.model_id}\n")
                    f.write(f"Response Text: {search_result_text}\n")
                    f.write(f"--- End Search ---\n\n")
            except Exception as e:
                print(f"Error writing to {self.log_file_name}: {e}")

            return {"search_agent_guide": search_result_text}

        except Exception as e:
            print(f"SearchAgent: Error during search: {e}")
            # Log the error
            try:
                with open(self.log_file_name, "a", encoding='utf-8') as f:
                    f.write(f"--- Search Error ---\n")
                    f.write(f"Query: {user_query}\n")
                    f.write(f"Model ID: {self.model_id}\n")
                    f.write(f"Error: {e}\n")
                    f.write(f"--- End Search Error ---\n\n")
            except Exception as log_e:
                print(f"Error writing error to {self.log_file_name}: {log_e}")
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
        print(f"SearchAgent initialized with model: {search_agent.model_id}.")
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