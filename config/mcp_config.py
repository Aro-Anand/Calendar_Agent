"""
MCP (Model Context Protocol) Configuration
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent

# Google Gemini Configuration (for MCP support)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL_NAME = "gemini-2.5-flash"  # Gemini 2.0 Flash
MAX_TOKENS = 8192

# MCP Server Configuration
MCP_SERVER_CONFIG = {
    "server_name": "calendar-mcp-server",
    "server_version": "1.0.0",
    "host": "localhost",
    "port": 3000,
    "protocol_version": "2024-11-05",
}


# Calendar Configuration
CALENDAR_CONFIG = {
    # Storage - Now using Google Calendar as primary source
    "storage_type": "google_calendar",
    
    # Meeting Settings
    "default_duration_minutes": 60,
    "min_duration_minutes": 15,
    "max_duration_minutes": 480,
    "timezone": "UTC",
    
    # Business Rules
    "business_hours_start": "09:00",
    "business_hours_end": "18:00",
    "working_days": [0, 1, 2, 3, 4],  # Monday=0 to Friday=4
    "allow_weekend_meetings": True,
    "buffer_between_meetings_minutes": 0,
    
    # Features
    "enable_conflict_detection": True,
    "enable_reminders": True,
    "email_notifications": True,
}


# MCP Protocol Configuration
MCP_PROTOCOL_CONFIG = {
    "protocol_version": "2024-11-05",
    "capabilities": {
        "tools": True,
        "resources": False,
        "prompts": False,
        "logging": True,
    },
    "transport": "stdio",
    "max_connections": 10,
    "tool_timeout_seconds": 30,
}

# Integration Configuration
INTEGRATION_CONFIG = {
    # MCP Server Connection
    "mcp_server_url": f"http://{MCP_SERVER_CONFIG['host']}:{MCP_SERVER_CONFIG['port']}",
    "mcp_connection_timeout": 10,
    "auto_reconnect": True,
    "use_mcp": True,  # Set to False to use direct tools
    
    # Agent Behavior
    "enable_mcp_tools": True,
    "fallback_to_direct_tools": True,
    "cache_tool_results": False,
}

# Agent System Message
SYSTEM_MESSAGE = """You are CalendarBot, an intelligent calendar assistant powered by Google Gemini.

You can:
1. Schedule new meetings (stored in Google Calendar)
2. Retrieve meeting details from Google Calendar
3. List all meetings
4. Update existing meetings in Google Calendar
5. Delete meetings from Google Calendar

When scheduling meetings:
- Extract: title, date (YYYY-MM-DD), time (HH:MM), participants, description
- Validate dates are in the future
- Check for time conflicts with existing Google Calendar events
- Use 24-hour time format

When querying:
- Support flexible queries by date, participant, or title
- Return clear, formatted results from Google Calendar

All meetings are synchronized with Google Calendar in real-time.
Always be helpful, accurate, and confirm actions taken."""