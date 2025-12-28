"""
MCP Server Tool Handlers with Google Calendar as Primary Storage
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from config.google_calendar_config import GOOGLE_CALENDAR_CONFIG
from utils.helpers import (
    parse_date,
    parse_time,
    is_future_datetime,
    generate_meeting_id
)

# Import Google Calendar service
from integrations.google_calendar_service import get_google_calendar_service


class CalendarHandlers:
    """Handler class for calendar MCP tools with Google Calendar as primary storage."""
    
    def __init__(self):
        """Initialize handlers with Google Calendar service."""
        self.google_service = get_google_calendar_service()
        if not self.google_service.is_enabled():
            raise RuntimeError("Google Calendar integration is not enabled or authenticated")
        print("✅ Google Calendar integration active")
    
    def _check_time_conflict(self, date_str: str, time_str: str, exclude_event_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Check for time conflicts in Google Calendar."""
        try:
            # Parse the proposed meeting time
            meeting_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            meeting_end = meeting_datetime + timedelta(minutes=60)  # Default 1 hour duration
            
            # Get events from Google Calendar for that day
            day_start = meeting_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            events = self.google_service.get_events(time_min=day_start, time_max=day_end)
            
            # Check for conflicts
            for event in events:
                # Skip if this is the same event we're updating
                if exclude_event_id and event.get("google_event_id") == exclude_event_id:
                    continue
                
                # Parse event time
                event_datetime = datetime.strptime(f"{event['date']} {event['time']}", "%Y-%m-%d %H:%M")
                event_end = event_datetime + timedelta(minutes=60)
                
                # Check for overlap
                if (meeting_datetime < event_end and meeting_end > event_datetime):
                    return event
            
            return None
        except Exception as e:
            print(f"⚠️ Error checking conflicts: {e}")
            return None
    
    def schedule_meeting(
        self,
        title: str,
        date: str,
        time: str,
        participants: Optional[List[str]] = None,
        description: str = ""
    ) -> Dict[str, Any]:
        """
        Schedule a new meeting in Google Calendar.
        
        Args:
            title: Meeting title
            date: Date in YYYY-MM-DD format
            time: Time in HH:MM format
            participants: Optional list of participant email addresses
            description: Optional description
            
        Returns:
            Result dictionary with success status and message
        """
        try:
            # Default participants to empty list if not provided
            # Participants are completely optional - only valid emails will be added as attendees
            if participants is None:
                participants = []
            # Filter out empty strings and None values
            participants = [p for p in participants if p and str(p).strip()]
            
            # Validate inputs
            if not all([title, date, time]):
                return {
                    "success": False,
                    "error": "Missing required fields (title, date, time)"
                }
            
            # Parse and validate date
            parsed_date = parse_date(date)
            if not parsed_date:
                return {
                    "success": False,
                    "error": f"Invalid date format '{date}'. Use YYYY-MM-DD"
                }
            
            date_formatted = parsed_date.strftime("%Y-%m-%d")
            
            # Parse and validate time
            parsed_time = parse_time(time)
            if not parsed_time:
                return {
                    "success": False,
                    "error": f"Invalid time format '{time}'. Use HH:MM or 12-hour format"
                }
            
            # Check if future
            if not is_future_datetime(date_formatted, parsed_time):
                return {
                    "success": False,
                    "error": "Cannot schedule meetings in the past"
                }
            
            # Check conflicts
            if GOOGLE_CALENDAR_CONFIG.get("enable_conflict_detection", True):
                conflict = self._check_time_conflict(date_formatted, parsed_time)
                if conflict:
                    return {
                        "success": False,
                        "error": f"Time conflict with '{conflict['title']}' at {conflict['date']} {conflict['time']}"
                    }
            
            # Create meeting object
            meeting = {
                "id": generate_meeting_id(),
                "title": title,
                "date": date_formatted,
                "time": parsed_time,
                "participants": participants,
                "description": description,
                "created_at": datetime.now().isoformat()
            }
            
            # Create in Google Calendar
            google_event_id = self.google_service.create_event(meeting)
            
            if google_event_id:
                meeting["google_event_id"] = google_event_id
                meeting["synced_to_google"] = True
                
                return {
                    "success": True,
                    "meeting": meeting,
                    "message": f"Successfully scheduled '{title}' on {date_formatted} at {parsed_time} (Synced to Google Calendar ✓)"
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to create event in Google Calendar"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Error scheduling meeting: {str(e)}"
            }
    
    def get_meeting_details(
        self,
        date: Optional[str] = None,
        participant: Optional[str] = None,
        title: Optional[str] = None,
        meeting_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get meeting details from Google Calendar with optional filters.
        
        Args:
            date: Filter by date
            participant: Filter by participant
            title: Filter by title
            meeting_id: Get specific meeting by ID
            
        Returns:
            Result dictionary with meetings
        """
        try:
            # Determine time range for query
            if date:
                parsed_date = parse_date(date)
                if not parsed_date:
                    return {
                        "success": False,
                        "error": f"Invalid date format '{date}'. Use YYYY-MM-DD"
                    }
                time_min = parsed_date.replace(hour=0, minute=0, second=0)
                time_max = time_min + timedelta(days=1)
            else:
                # Get next 30 days by default
                time_min = datetime.now()
                time_max = time_min + timedelta(days=30)
            
            # Get events from Google Calendar
            meetings = self.google_service.get_events(time_min=time_min, time_max=time_max)
            
            if not meetings:
                return {
                    "success": True,
                    "meetings": [],
                    "message": "No meetings found"
                }
            
            # Apply filters
            filtered = meetings
            
            # Filter by participant
            if participant:
                filtered = [
                    m for m in filtered
                    if any(participant.lower() in p.lower() for p in m.get("participants", []))
                ]
            
            # Filter by title
            if title:
                filtered = [
                    m for m in filtered
                    if title.lower() in m.get("title", "").lower()
                ]
            
            # Filter by meeting ID (Google event ID)
            if meeting_id:
                filtered = [
                    m for m in filtered
                    if m.get("google_event_id") == meeting_id or m.get("id") == meeting_id
                ]
            
            return {
                "success": True,
                "meetings": filtered,
                "count": len(filtered),
                "message": f"Found {len(filtered)} meeting(s) in Google Calendar"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error retrieving meetings: {str(e)}"
            }
    
    def list_all_meetings(self) -> Dict[str, Any]:
        """
        List all upcoming meetings from Google Calendar.
        
        Returns:
            Result dictionary with all meetings
        """
        try:
            # Get events from Google Calendar (next 30 days)
            time_min = datetime.now()
            time_max = time_min + timedelta(days=30)
            
            meetings = self.google_service.get_events(time_min=time_min, time_max=time_max)
            
            if not meetings:
                return {
                    "success": True,
                    "meetings": [],
                    "count": 0,
                    "message": "No upcoming meetings in Google Calendar"
                }
            
            # Sort by date and time
            try:
                sorted_meetings = sorted(
                    meetings,
                    key=lambda m: datetime.strptime(f"{m['date']} {m['time']}", "%Y-%m-%d %H:%M")
                )
            except Exception:
                sorted_meetings = meetings
            
            return {
                "success": True,
                "meetings": sorted_meetings,
                "count": len(sorted_meetings),
                "message": f"Found {len(sorted_meetings)} upcoming meeting(s) in Google Calendar"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error listing meetings: {str(e)}"
            }
    
    def update_meeting(
        self,
        meeting_id: str,
        title: Optional[str] = None,
        date: Optional[str] = None,
        time: Optional[str] = None,
        participants: Optional[List[str]] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update an existing meeting in Google Calendar.
        
        Args:
            meeting_id: Google event ID or local ID
            title: New title
            date: New date
            time: New time
            participants: New participants
            description: New description
            
        Returns:
            Result dictionary
        """
        try:
            # First, find the meeting
            result = self.get_meeting_details(meeting_id=meeting_id)
            
            if not result.get("success") or not result.get("meetings"):
                return {
                    "success": False,
                    "error": f"Meeting with ID '{meeting_id}' not found in Google Calendar"
                }
            
            meeting = result["meetings"][0]
            google_event_id = meeting.get("google_event_id")
            
            if not google_event_id:
                return {
                    "success": False,
                    "error": "Cannot update meeting: Google event ID not found"
                }
            
            # Update fields
            if title:
                meeting["title"] = title
            
            if date:
                parsed_date = parse_date(date)
                if not parsed_date:
                    return {
                        "success": False,
                        "error": f"Invalid date format '{date}'"
                    }
                meeting["date"] = parsed_date.strftime("%Y-%m-%d")
            
            if time:
                parsed_time = parse_time(time)
                if not parsed_time:
                    return {
                        "success": False,
                        "error": f"Invalid time format '{time}'"
                    }
                meeting["time"] = parsed_time
            
            if participants:
                meeting["participants"] = participants
            
            if description is not None:
                meeting["description"] = description
            
            # Check for conflicts if date/time changed
            if date or time:
                conflict = self._check_time_conflict(
                    meeting["date"], 
                    meeting["time"],
                    exclude_event_id=google_event_id
                )
                if conflict:
                    return {
                        "success": False,
                        "error": f"Time conflict with '{conflict['title']}' at {conflict['date']} {conflict['time']}"
                    }
            
            # Update in Google Calendar
            success = self.google_service.update_event(meeting, google_event_id)
            
            if success:
                return {
                    "success": True,
                    "meeting": meeting,
                    "message": f"Successfully updated meeting '{meeting['title']}' in Google Calendar ✓"
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to update event in Google Calendar"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Error updating meeting: {str(e)}"
            }
    
    def delete_meeting(self, meeting_id: str) -> Dict[str, Any]:
        """
        Delete a meeting from Google Calendar.
        
        Args:
            meeting_id: Google event ID or local ID
            
        Returns:
            Result dictionary
        """
        try:
            # First, find the meeting
            result = self.get_meeting_details(meeting_id=meeting_id)
            
            if not result.get("success") or not result.get("meetings"):
                return {
                    "success": False,
                    "error": f"Meeting with ID '{meeting_id}' not found in Google Calendar"
                }
            
            meeting = result["meetings"][0]
            google_event_id = meeting.get("google_event_id")
            
            if not google_event_id:
                return {
                    "success": False,
                    "error": "Cannot delete meeting: Google event ID not found"
                }
            
            # Delete from Google Calendar
            success = self.google_service.delete_event(google_event_id)
            
            if success:
                return {
                    "success": True,
                    "message": f"Successfully deleted meeting '{meeting['title']}' from Google Calendar ✓",
                    "deleted_meeting": meeting
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to delete event from Google Calendar"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Error deleting meeting: {str(e)}"
            }