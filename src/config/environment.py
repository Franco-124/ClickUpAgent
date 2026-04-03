
import os
from dotenv import load_dotenv
load_dotenv()


class config:
    CLICK_UP_API_TOKEN = os.getenv("CLICK_UP_API_TOKEN")
    CLICKUP_LIST_ID = os.getenv("CLICKUP_LIST_ID")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    CLICK_UP_BASE_URL = os.getenv("CLICK_UP_BASE_URL")