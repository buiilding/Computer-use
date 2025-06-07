import os
import google.generativeai as generativeai
from config.settings import GEMINI_API_KEY

class BaseAgent:
    def __init__(self, model_name: str, system_prompt_path: str, tools: list = None, temperature: float = 0.7):
        self.gemini_model = None
        self.model_name = model_name
        self.system_prompt_path = system_prompt_path
        self.tools = tools
        self.temperature = temperature # ADDED: Store temperature
        
        if GEMINI_API_KEY:
            self.setup_google_gemini(GEMINI_API_KEY)
        else:
            print(f"Warning: GEMINI_API_KEY not provided. {self.__class__.__name__} will not be initialized.")

    def setup_google_gemini(self, gemini_api: str):
        generativeai.configure(api_key=gemini_api)
        system_instruction = self.load_system_prompt()
        
        # ADDED: Create the generation configuration for temperature
        generation_config = {
            "temperature": self.temperature,
        }

        model_kwargs = {
            "model_name": self.model_name,
            "system_instruction": system_instruction,
            "generation_config": generation_config 
        }

        if self.tools:
            model_kwargs["tools"] = self.tools
            
        try:
            self.gemini_model = generativeai.GenerativeModel(**model_kwargs)
            # Added temperature to the success message for clarity
            print(f"{self.__class__.__name__} ({self.model_name}): Gemini model initialized successfully with temperature={self.temperature}.")
        except Exception as e:
            print(f"Error initializing Gemini model for {self.__class__.__name__} ({self.model_name}): {e}")
            self.gemini_model = None


    def load_system_prompt(self):
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        full_prompt_path = os.path.join(project_root, self.system_prompt_path)

        try:
            with open(full_prompt_path, "r", encoding='utf-8') as f:
                prompt_content = f.read()
            return prompt_content
        except FileNotFoundError:
            print(f"Error: System prompt file not found at {self.system_prompt_path} (resolved to {full_prompt_path}). Please check the path.")
            return "" 
        except Exception as e:
            print(f"Error loading system prompt for {self.__class__.__name__} from {self.system_prompt_path}: {str(e)}")
            return ""

    def __call__(self, state: dict) -> dict:
        raise NotImplementedError("Each agent must implement its own __call__ method.")