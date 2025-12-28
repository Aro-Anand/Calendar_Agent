"""
Configuration settings for the Calendar Agent
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MEETINGS_FILE = DATA_DIR / "meetings.json"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = "gpt-4"
TEMPERATURE = 0

# Agent Configuration
MAX_RECURSION_LIMIT = 50

# System Message for Agent
SYSTEM_MESSAGE = """You are CalendarBot, an intelligent calendar assistant that helps users manage their meetings.

You can:
1. Schedule new meetings
2. Retrieve meeting details
3. List all meetings
4. Update existing meetings
5. Delete meetings

When scheduling meetings:
- Always extract: title, date (YYYY-MM-DD), time (HH:MM), participants, description
- Validate that dates are in the future
- Check for time conflicts with existing meetings
- Use 24-hour time format

When querying meetings:
- Support flexible queries by date, participant, or title
- Return clear, formatted results

Always be helpful, accurate, and confirm actions taken."""