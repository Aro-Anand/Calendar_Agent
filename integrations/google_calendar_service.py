"""
Google Calendar Service Integration
"""
import os
import json
import tempfile
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pytz
from oauthlib.oauth2.rfc6749.errors import OAuth2Error

from config.google_calendar_config import (
    GOOGLE_CALENDAR_CONFIG,
    GOOGLE_API_CONFIG,
    FIELD_MAPPING,
    get_credentials_from_env,
    get_token_from_env,
)


class GoogleCalendarService:
    """Service for interacting with Google Calendar API."""
    
    def __init__(
        self,
        credentials_json: Optional[Union[str, dict]] = None,
        token_json: Optional[Union[str, dict]] = None,
        auth_code: Optional[str] = None,
        calendar_id: Optional[str] = None,
        skip_auth: bool = False
    ):
        self.config = GOOGLE_CALENDAR_CONFIG.copy()
        self.api_config = GOOGLE_API_CONFIG
        self.service = None
        self.credentials = None
        
        # Override calendar_id if provided
        if calendar_id:
            self.config["calendar_id"] = calendar_id
        
        # Store credentials for manual auth
        self._credentials_json = credentials_json
        self._token_json = token_json
        self._auth_code = auth_code
        
        # If skip_auth is True but we have a token_json, initialize service with token directly
        if self.config["enabled"] and skip_auth and token_json:
            try:
                token_dict = token_json if isinstance(token_json, dict) else json.loads(token_json)
                creds = Credentials.from_authorized_user_info(token_dict, self.config["oauth_scopes"])
                
                # Refresh if expired
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                
                if creds:
                    self.credentials = creds
                    self.service = build(
                        self.api_config["api_name"],
                        self.api_config["api_version"],
                        credentials=creds
                    )
                    print("✅ Google Calendar authenticated successfully (using provided token)")
            except Exception as e:
                print(f"⚠️ Could not initialize service with provided token: {e}")
        elif self.config["enabled"] and not skip_auth:
            self._authenticate()
    
    def _load_credentials_from_json(self, credentials_json: Union[str, dict]) -> dict:
        """Parse JSON string to dict or return dict as-is."""
        if isinstance(credentials_json, str):
            try:
                return json.loads(credentials_json)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON format in credentials")
        return credentials_json
    
    def _authenticate(self) -> bool:
        """Authenticate with Google Calendar API.
        
        Supports multiple credential sources (priority order):
        1. Session state credentials (from UI)
        2. Environment variables (GOOGLE_CREDENTIALS_JSON, GOOGLE_TOKEN_JSON)
        3. File-based credentials (existing behavior)
        """
        try:
            creds = None
            credentials_dict = None
            
            # Priority 1: Session state credentials (from UI)
            if self._credentials_json:
                credentials_dict = self._load_credentials_from_json(self._credentials_json)
                
                # If we have an auth code, use manual flow
                if self._auth_code:
                    return self._authenticate_manual(credentials_dict, self._auth_code)
                
                # If we have a token JSON, load it and use it directly
                if self._token_json:
                    try:
                        token_dict = self._token_json if isinstance(self._token_json, dict) else json.loads(self._token_json)
                        creds = Credentials.from_authorized_user_info(token_dict, self.config["oauth_scopes"])
                        
                        # If credentials are valid, use them immediately and skip further authentication
                        if creds and creds.valid:
                            self.credentials = creds
                            self.service = build(
                                self.api_config["api_name"],
                                self.api_config["api_version"],
                                credentials=creds
                            )
                            print("✅ Google Calendar authenticated successfully (using provided token)")
                            return True
                        # If expired but has refresh token, try to refresh
                        elif creds and creds.expired and creds.refresh_token:
                            creds.refresh(Request())
                            self.credentials = creds
                            self.service = build(
                                self.api_config["api_name"],
                                self.api_config["api_version"],
                                credentials=creds
                            )
                            print("✅ Google Calendar authenticated successfully (token refreshed)")
                            return True
                    except Exception as e:
                        print(f"⚠️ Could not use provided token: {e}")
                        creds = None  # Reset to None so we can try other methods
            
            # Priority 2: Environment variables
            if not creds:
                env_credentials = get_credentials_from_env()
                env_token = get_token_from_env()
                
                if env_credentials:
                    credentials_dict = env_credentials
                    if env_token:
                        creds = Credentials.from_authorized_user_info(env_token, self.config["oauth_scopes"])
            
            # Priority 3: File-based credentials (existing behavior)
            if not credentials_dict:
                token_file = self.config["token_file"]
                credentials_file = self.config["credentials_file"]
                
                # Check if credentials file exists
                if not credentials_file.exists():
                    print(f"❌ Google credentials file not found: {credentials_file}")
                    print("📝 Please follow the setup instructions to get credentials")
                    return False
                
                # Load existing token
                if token_file.exists():
                    creds = Credentials.from_authorized_user_file(
                        str(token_file),
                        self.config["oauth_scopes"]
                    )
            
            # If no valid credentials, authenticate
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    # Need credentials to proceed
                    if not credentials_dict:
                        token_file = self.config["token_file"]
                        credentials_file = self.config["credentials_file"]
                        if not credentials_file.exists():
                            print("❌ No credentials available for authentication")
                            return False
                        flow = InstalledAppFlow.from_client_secrets_file(
                            str(credentials_file),
                            self.config["oauth_scopes"]
                        )
                    else:
                        # Create temporary file for credentials dict
                        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
                            json.dump(credentials_dict, tmp_file)
                            tmp_file_path = tmp_file.name
                        
                        try:
                            flow = InstalledAppFlow.from_client_secrets_file(
                                tmp_file_path,
                                self.config["oauth_scopes"]
                            )
                        finally:
                            # Clean up temporary file
                            if os.path.exists(tmp_file_path):
                                os.unlink(tmp_file_path)
                    
                    # Force 127.0.0.1 to avoid IPv6/localhost resolution issues
                    creds = flow.run_local_server(
                        port=0,
                        host='127.0.0.1',
                        authorization_prompt_message='Please visit this URL: {url}',
                        success_message='The auth flow is complete; you may close this window.',
                        open_browser=True
                    )
                
                # Save credentials for next time (only if using file-based)
                if not self._credentials_json and not get_credentials_from_env():
                    token_file = self.config["token_file"]
                    with open(token_file, 'w') as token:
                        token.write(creds.to_json())
            
            self.credentials = creds
            self.service = build(
                self.api_config["api_name"],
                self.api_config["api_version"],
                credentials=creds
            )
            
            print("✅ Google Calendar authenticated successfully")
            return True
            
        except Exception as e:
            print(f"❌ Google Calendar authentication failed: {e}")
            return False
    
    def _authenticate_manual(self, credentials_dict: dict, auth_code: str) -> bool:
        """Manual OAuth flow implementation using authorization code."""
        tmp_file_path = None
        try:
            # Create temporary file for credentials dict
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
                json.dump(credentials_dict, tmp_file)
                tmp_file_path = tmp_file.name
            
            flow = InstalledAppFlow.from_client_secrets_file(
                tmp_file_path,
                self.config["oauth_scopes"]
            )
            
            # Exchange authorization code for token
            flow.fetch_token(code=auth_code)
            creds = flow.credentials
            
            self.credentials = creds
            self.service = build(
                self.api_config["api_name"],
                self.api_config["api_version"],
                credentials=creds
            )
            
            print("✅ Google Calendar authenticated successfully (manual flow)")
            return True
            
        except OAuth2Error as e:
            print(f"❌ OAuth error during manual authentication: {e}")
            return False
        except Exception as e:
            print(f"❌ Google Calendar manual authentication failed: {e}")
            return False
        finally:
            # Clean up temporary file
            if tmp_file_path and os.path.exists(tmp_file_path):
                try:
                    os.unlink(tmp_file_path)
                except Exception:
                    pass  # Ignore cleanup errors
    
    def generate_authorization_url(self, credentials_json: Union[str, dict]) -> str:
        """Generate OAuth authorization URL for manual code flow.
        
        Args:
            credentials_json: Google OAuth credentials as dict or JSON string
            
        Returns:
            Authorization URL string
        """
        tmp_file_path = None
        try:
            credentials_dict = self._load_credentials_from_json(credentials_json)
            
            # Create temporary file for credentials dict
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
                json.dump(credentials_dict, tmp_file)
                tmp_file_path = tmp_file.name
            
            flow = InstalledAppFlow.from_client_secrets_file(
                tmp_file_path,
                self.config["oauth_scopes"]
            )
            
            # Set redirect URI to fix "Missing required parameter: redirect_uri"
            flow.redirect_uri = self.config["oauth_redirect_uri"]
            
            # Generate authorization URL
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true'
            )
            
            return auth_url
            
        except Exception as e:
            raise ValueError(f"Failed to generate authorization URL: {e}")
        finally:
            # Clean up temporary file
            if tmp_file_path and os.path.exists(tmp_file_path):
                try:
                    os.unlink(tmp_file_path)
                except Exception:
                    pass  # Ignore cleanup errors
    
    def exchange_code_for_token(self, credentials_json: Union[str, dict], auth_code: str) -> Credentials:
        """Exchange authorization code for access token.
        
        Args:
            credentials_json: Google OAuth credentials as dict or JSON string
            auth_code: Authorization code from OAuth flow
            
        Returns:
            Credentials object
        """
        tmp_file_path = None
        try:
            credentials_dict = self._load_credentials_from_json(credentials_json)
            
            # Create temporary file for credentials dict
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
                json.dump(credentials_dict, tmp_file)
                tmp_file_path = tmp_file.name
            
            flow = InstalledAppFlow.from_client_secrets_file(
                tmp_file_path,
                self.config["oauth_scopes"]
            )
            
            # Set redirect URI (must match the one used in authorization step)
            flow.redirect_uri = self.config["oauth_redirect_uri"]
            
            # Exchange code for token
            flow.fetch_token(code=auth_code)
            return flow.credentials
            
        except OAuth2Error as e:
            raise ValueError(f"OAuth error: {e}")
        except Exception as e:
            raise ValueError(f"Failed to exchange code for token: {e}")
        finally:
            # Clean up temporary file
            if tmp_file_path and os.path.exists(tmp_file_path):
                try:
                    os.unlink(tmp_file_path)
                except Exception:
                    pass  # Ignore cleanup errors
    
    def is_enabled(self) -> bool:
        """Check if Google Calendar integration is enabled and authenticated."""
        return self.config["enabled"] and self.service is not None
    
    def _convert_to_google_event(self, meeting: Dict[str, Any]) -> Dict[str, Any]:
        """Convert local meeting format to Google Calendar event format."""
        # Parse date and time
        date_str = meeting.get("date", "")
        time_str = meeting.get("time", "")
        
        # Combine date and time
        start_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        end_datetime = start_datetime + timedelta(minutes=60)  # Default 60 min duration
        
        # Convert to ISO format with timezone
        timezone = pytz.timezone("UTC")
        start_iso = timezone.localize(start_datetime).isoformat()
        end_iso = timezone.localize(end_datetime).isoformat()
        
        # Convert participants to attendees (OPTIONAL - only valid email addresses)
        # Participants are completely optional - only add as attendees if valid emails provided
        attendees = []
        non_email_participants = []
        
        # Handle None or empty participants gracefully
        participants = meeting.get("participants") or []
        
        for participant in participants:
            if participant:  # Skip empty strings/None
                participant_str = str(participant).strip()
                # Only add as attendee if it's a valid email address
                if "@" in participant_str and "." in participant_str:
                    attendees.append({"email": participant_str})
                else:
                    # Store non-email participants in description
                    non_email_participants.append(participant_str)
        
        # Build description with non-email participants
        description = meeting.get("description", "")
        if non_email_participants:
            participants_text = "\n\nParticipants: " + ", ".join(non_email_participants)
            description = description + participants_text if description else participants_text.strip()
        
        # Build Google Calendar event
        event = {
            "summary": meeting.get("title", "Untitled Meeting"),
            "description": description,
            "start": {
                "dateTime": start_iso,
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": end_iso,
                "timeZone": "UTC",
            },
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": self.config["default_reminder_minutes"]},
                    {"method": "popup", "minutes": self.config["default_reminder_minutes"]},
                ],
            },
            "extendedProperties": {
                "private": {
                    "local_id": meeting.get("id", ""),
                    "created_by": "calendar_mcp_agent"
                }
            }
        }
        
        # Only add attendees if we have valid email addresses (completely optional)
        if attendees:
            event["attendees"] = attendees
        
        # Add Google Meet link if requested
        if self.config["add_conference_link"]:
            event["conferenceData"] = {
                "createRequest": {
                    "requestId": f"meet-{meeting.get('id', '')}",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"}
                }
            }
        
        return event
    
    def _convert_from_google_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Google Calendar event to local meeting format."""
        # Extract date and time
        start = event.get("start", {})
        start_datetime_str = start.get("dateTime", start.get("date", ""))
        
        if not start_datetime_str:
            return None
        
        # Parse datetime
        try:
            if "T" in start_datetime_str:
                start_dt = datetime.fromisoformat(start_datetime_str.replace("Z", "+00:00"))
            else:
                start_dt = datetime.strptime(start_datetime_str, "%Y-%m-%d")
        except:
            return None
        
        # Extract participants
        participants = []
        for attendee in event.get("attendees", []):
            name = attendee.get("displayName") or attendee.get("email", "").split("@")[0]
            participants.append(name)
        
        # Get local ID if it exists
        extended_props = event.get("extendedProperties", {}).get("private", {})
        local_id = extended_props.get("local_id")
        
        meeting = {
            "id": local_id or event.get("id"),
            "title": event.get("summary", "Untitled"),
            "date": start_dt.strftime("%Y-%m-%d"),
            "time": start_dt.strftime("%H:%M"),
            "participants": participants,
            "description": event.get("description", ""),
            "google_event_id": event.get("id"),
            "google_link": event.get("htmlLink", ""),
        }
        
        # Add Google Meet link if available
        if event.get("hangoutLink"):
            meeting["meet_link"] = event.get("hangoutLink")
        
        return meeting
    
    def create_event(self, meeting: Dict[str, Any]) -> Optional[str]:
        """Create an event in Google Calendar."""
        if not self.is_enabled():
            return None
        
        try:
            event = self._convert_to_google_event(meeting)
            
            result = self.service.events().insert(
                calendarId=self.config["calendar_id"],
                body=event,
                sendNotifications=self.config["send_notifications"],
                conferenceDataVersion=1 if self.config["add_conference_link"] else 0
            ).execute()
            
            print(f"✅ Created Google Calendar event: {result.get('htmlLink')}")
            return result.get("id")
            
        except HttpError as e:
            if e.resp.status == 404:
                print(f"❌ Calendar '{self.config['calendar_id']}' not found. Please check the Calendar ID in Settings (use 'primary' for main calendar)")
            else:
                print(f"❌ Failed to create Google Calendar event: {e}")
            return None
    
    def update_event(self, meeting: Dict[str, Any], google_event_id: str) -> bool:
        """Update an existing event in Google Calendar."""
        if not self.is_enabled():
            return False
        
        try:
            event = self._convert_to_google_event(meeting)
            
            self.service.events().update(
                calendarId=self.config["calendar_id"],
                eventId=google_event_id,
                body=event,
                sendNotifications=self.config["send_notifications"]
            ).execute()
            
            print(f"✅ Updated Google Calendar event: {google_event_id}")
            return True
            
        except HttpError as e:
            if e.resp.status == 404:
                print(f"❌ Calendar '{self.config['calendar_id']}' not found. Please check the Calendar ID in Settings (use 'primary' for main calendar)")
            else:
                print(f"❌ Failed to update Google Calendar event: {e}")
            return False
    
    def delete_event(self, google_event_id: str) -> bool:
        """Delete an event from Google Calendar."""
        if not self.is_enabled():
            return False
        
        try:
            self.service.events().delete(
                calendarId=self.config["calendar_id"],
                eventId=google_event_id,
                sendNotifications=self.config["send_notifications"]
            ).execute()
            
            print(f"✅ Deleted Google Calendar event: {google_event_id}")
            return True
            
        except HttpError as e:
            print(f"❌ Failed to delete Google Calendar event: {e}")
            return False
    
    def get_events(
        self,
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """Get events from Google Calendar."""
        if not self.is_enabled():
            return []
        
        try:
            # Default to next 30 days
            if not time_min:
                time_min = datetime.utcnow()
            if not time_max:
                time_max = time_min + timedelta(days=30)
            
            # Convert to ISO format
            time_min_iso = time_min.isoformat() + "Z"
            time_max_iso = time_max.isoformat() + "Z"
            
            events_result = self.service.events().list(
                calendarId=self.config["calendar_id"],
                timeMin=time_min_iso,
                timeMax=time_max_iso,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime"
            ).execute()
            
            events = events_result.get("items", [])
            
            # Convert to local format
            meetings = []
            for event in events:
                meeting = self._convert_from_google_event(event)
                if meeting:
                    meetings.append(meeting)
            
            return meetings
            
        except HttpError as e:
            if e.resp.status == 404:
                print(f"❌ Calendar '{self.config['calendar_id']}' not found. Please check the Calendar ID in Settings (use 'primary' for main calendar)")
            else:
                print(f"❌ Failed to get Google Calendar events: {e}")
            return []
    
    def sync_event(self, meeting: Dict[str, Any], action: str = "create") -> Optional[str]:
        """Sync a single event based on action."""
        if not self.is_enabled():
            return None
        
        google_event_id = meeting.get("google_event_id")
        
        if action == "create":
            return self.create_event(meeting)
        elif action == "update" and google_event_id:
            success = self.update_event(meeting, google_event_id)
            return google_event_id if success else None
        elif action == "delete" and google_event_id:
            success = self.delete_event(google_event_id)
            return google_event_id if success else None
        
        return None


# Singleton instance
_google_calendar_service = None


def get_google_calendar_service(
    credentials_json: Optional[Union[str, dict]] = None,
    token_json: Optional[Union[str, dict]] = None,
    auth_code: Optional[str] = None,
    calendar_id: Optional[str] = None,
    force_reinit: bool = False,
    skip_auth: bool = False
) -> GoogleCalendarService:
    """Get or create the Google Calendar service singleton.
    
    Args:
        credentials_json: Optional credentials JSON (dict or string)
        token_json: Optional token JSON (dict or string)
        auth_code: Optional authorization code for manual OAuth
        calendar_id: Optional calendar ID override
        force_reinit: Force re-initialization even if service exists
    
    Returns:
        GoogleCalendarService instance
    """
    global _google_calendar_service
    
    # Only re-initialize if:
    # 1. Explicitly forced
    # 2. Service doesn't exist yet
    # 3. We have credentials/token and service doesn't have them (or they're different)
    # 4. We have an auth_code (manual authentication in progress)
    should_reinit = force_reinit
    
    if _google_calendar_service is None:
        should_reinit = True
    elif auth_code is not None:
        # Always reinit if we have an auth code (manual auth in progress)
        should_reinit = True
    elif token_json is not None:
        # Only reinit if current service doesn't have a token or it's different
        current_token = getattr(_google_calendar_service, '_token_json', None)
        if current_token != token_json:
            should_reinit = True
    elif credentials_json is not None and not hasattr(_google_calendar_service, '_credentials_json'):
        # Only reinit if we're providing credentials but service doesn't have them
        should_reinit = True
    
    if should_reinit:
        _google_calendar_service = GoogleCalendarService(
            credentials_json=credentials_json,
            token_json=token_json,
            auth_code=auth_code,
            calendar_id=calendar_id,
            skip_auth=skip_auth
        )
    elif _google_calendar_service is None:
        _google_calendar_service = GoogleCalendarService()
    
    return _google_calendar_service