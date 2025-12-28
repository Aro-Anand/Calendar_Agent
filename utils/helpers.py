"""
Helper functions for Calendar Agent
"""
from datetime import datetime
from typing import Optional
import re


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse date string to datetime object."""
    formats = ["%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def parse_time(time_str: str) -> Optional[str]:
    """Parse time string to HH:MM format."""
    # Remove spaces
    time_str = time_str.strip()
    
    # Handle 24-hour format (HH:MM)
    if re.match(r'^\d{1,2}:\d{2}$', time_str):
        parts = time_str.split(':')
        hour = int(parts[0])
        minute = int(parts[1])
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return f"{hour:02d}:{minute:02d}"
    
    # Handle 12-hour format with AM/PM
    match = re.match(r'^(\d{1,2}):?(\d{2})?\s*(AM|PM|am|pm)$', time_str)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        period = match.group(3).upper()
        
        if period == 'PM' and hour != 12:
            hour += 12
        elif period == 'AM' and hour == 12:
            hour = 0
        
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return f"{hour:02d}:{minute:02d}"
    
    return None


def is_future_datetime(date_str: str, time_str: str) -> bool:
    """Check if datetime is in the future."""
    try:
        dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        return dt > datetime.now()
    except:
        return False


def generate_meeting_id() -> str:
    """Generate a unique meeting ID."""
    import uuid
    return str(uuid.uuid4())[:8]
