"""
Google Calendar Integration Configuration
"""
import os
import json
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent
CREDENTIALS_DIR = BASE_DIR / "credentials"
CREDENTIALS_DIR.mkdir(exist_ok=True)


def get_credentials_from_env() -> Optional[dict]:
    """Get credentials from environment variables (Streamlit Secrets)."""
    credentials_json_str = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if credentials_json_str:
        try:
            return json.loads(credentials_json_str)
        except json.JSONDecodeError:
            return None
    return None


def get_token_from_env() -> Optional[dict]:
    """Get token from environment variables (Streamlit Secrets)."""
    token_json_str = os.getenv("GOOGLE_TOKEN_JSON")
    if token_json_str:
        try:
            return json.loads(token_json_str)
        except json.JSONDecodeError:
            return None
    return None


def detect_credentials_source() -> str:
    """Detect the source of credentials (session, env, or file)."""
    if os.getenv("GOOGLE_CREDENTIALS_JSON"):
        return "env"
    credentials_file = CREDENTIALS_DIR / "google_credentials.json"
    if credentials_file.exists():
        return "file"
    return "none"

# Google Calendar Configuration
GOOGLE_CALENDAR_CONFIG = {
    # Enable/Disable Integration - NOW ENABLED BY DEFAULT
    "enabled": os.getenv("GOOGLE_CALENDAR_ENABLED", "true").lower() == "true",
    
    # Credentials Files
    "credentials_file": CREDENTIALS_DIR / "google_credentials.json",
    "token_file": CREDENTIALS_DIR / "google_token.json",
    
    # Calendar Settings
    "calendar_id": os.getenv("GOOGLE_CALENDAR_ID", "primary"),  # Use "primary" for main calendar or specific calendar ID
    
    # Sync Settings - Google Calendar is now the PRIMARY storage
    "sync_direction": "google_primary",  # Google Calendar is the source of truth
    "auto_sync_on_create": True,         # Auto-sync when creating meetings
    "auto_sync_on_update": True,         # Auto-sync when updating meetings
    "auto_sync_on_delete": True,         # Auto-sync when deleting meetings
    
    # Sync Interval
    "background_sync_enabled": False,    # Enable periodic background sync
    "sync_interval_minutes": 5,          # How often to sync (if background sync enabled)
    
    # Event Settings
    "default_reminder_minutes": 15,      # Default reminder before meeting
    "send_notifications": True,          # Send email notifications via Google
    "add_conference_link": True,         # Auto-add Google Meet link
    
    # Conflict Handling
    "conflict_resolution": "google_wins", # Google Calendar is the source of truth
    
    # OAuth Settings
    "oauth_scopes": [
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/calendar.events'
    ],
    "oauth_redirect_uri": "http://localhost:8080/",
    
    # Credential Source Detection
    "credentials_source": detect_credentials_source(),
    "allow_manual_auth": True,  # Enable manual code flow
}

# Google API Configuration
GOOGLE_API_CONFIG = {
    "api_name": "calendar",
    "api_version": "v3",
    "max_results": 100,
    "timeout_seconds": 30,
}

# Mapping between local and Google Calendar fields
FIELD_MAPPING = {
    "local_to_google": {
        "id": "extendedProperties.private.local_id",
        "title": "summary",
        "description": "description",
        "date": "start.date",
        "time": "start.dateTime",
        "participants": "attendees",
    },
    "google_to_local": {
        "summary": "title",
        "description": "description",
        "start": "datetime",
        "attendees": "participants",
    }
}