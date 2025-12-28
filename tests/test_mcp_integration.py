"""
MCP Integration Test Script
Test all MCP calendar tools
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.handlers import CalendarHandlers
from utils.helpers import load_meetings
from config.mcp_config import MEETINGS_FILE


def print_header(text):
    """Print test section header."""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)


def print_result(test_name, result):
    """Print test result."""
    status = "✅ PASS" if result.get("success", False) else "❌ FAIL"
    print(f"\n{status} - {test_name}")
    print(f"Result: {result}")


def test_schedule_meeting():
    """Test scheduling a meeting."""
    print_header("TEST 1: Schedule Meeting")
    
    handlers = CalendarHandlers()
    
    # Test with future date
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    result = handlers.schedule_meeting(
        title="Team Standup",
        date=tomorrow,
        time="10:00",
        participants=["Alice", "Bob", "Charlie"],
        description="Daily team standup meeting"
    )
    
    print_result("Schedule future meeting", result)
    
    if result.get("success"):
        meeting_id = result["meeting"]["id"]
        print(f"✓ Created meeting with ID: {meeting_id}")
        return meeting_id
    
    return None


def test_get_meeting_details(meeting_id=None):
    """Test retrieving meeting details."""
    print_header("TEST 2: Get Meeting Details")
    
    handlers = CalendarHandlers()
    
    # Test 1: Get all meetings
    result = handlers.get_meeting_details()
    print_result("Get all meetings", result)
    
    # Test 2: Filter by participant
    if result.get("success") and result.get("meetings"):
        result = handlers.get_meeting_details(participant="Alice")
        print_result("Filter by participant", result)
    
    # Test 3: Get specific meeting by ID
    if meeting_id:
        result = handlers.get_meeting_details(meeting_id=meeting_id)
        print_result("Get meeting by ID", result)


def test_list_all_meetings():
    """Test listing all meetings."""
    print_header("TEST 3: List All Meetings")
    
    handlers = CalendarHandlers()
    result = handlers.list_all_meetings()
    
    print_result("List all meetings", result)
    
    if result.get("success"):
        print(f"✓ Total meetings: {result.get('count', 0)}")


def test_update_meeting(meeting_id):
    """Test updating a meeting."""
    print_header("TEST 4: Update Meeting")
    
    if not meeting_id:
        print("⚠️  Skipping update test - no meeting ID available")
        return
    
    handlers = CalendarHandlers()
    
    # Update time
    result = handlers.update_meeting(
        meeting_id=meeting_id,
        time="11:00",
        title="Updated Team Standup"
    )
    
    print_result("Update meeting time and title", result)


def test_delete_meeting(meeting_id):
    """Test deleting a meeting."""
    print_header("TEST 5: Delete Meeting")
    
    if not meeting_id:
        print("⚠️  Skipping delete test - no meeting ID available")
        return
    
    handlers = CalendarHandlers()
    result = handlers.delete_meeting(meeting_id=meeting_id)
    
    print_result("Delete meeting", result)


def test_validation():
    """Test input validation."""
    print_header("TEST 6: Input Validation")
    
    handlers = CalendarHandlers()
    
    # Test 1: Invalid date format
    result = handlers.schedule_meeting(
        title="Invalid Date Meeting",
        date="25-12-2024",  # Wrong format
        time="10:00",
        participants=["Alice"]
    )
    print_result("Invalid date format (should fail)", result)
    
    # Test 2: Past date
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    result = handlers.schedule_meeting(
        title="Past Meeting",
        date=yesterday,
        time="10:00",
        participants=["Alice"]
    )
    print_result("Past date (should fail)", result)
    
    # Test 3: Invalid time format
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    result = handlers.schedule_meeting(
        title="Invalid Time Meeting",
        date=tomorrow,
        time="25:00",  # Invalid time
        participants=["Alice"]
    )
    print_result("Invalid time format (should fail)", result)


def test_conflict_detection():
    """Test meeting conflict detection."""
    print_header("TEST 7: Conflict Detection")
    
    handlers = CalendarHandlers()
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Schedule first meeting
    result1 = handlers.schedule_meeting(
        title="Conflict Test Meeting 1",
        date=tomorrow,
        time="14:00",
        participants=["Alice"]
    )
    print_result("Schedule first meeting", result1)
    
    # Try to schedule conflicting meeting
    result2 = handlers.schedule_meeting(
        title="Conflict Test Meeting 2",
        date=tomorrow,
        time="14:30",  # Overlaps with first meeting
        participants=["Bob"]
    )
    print_result("Schedule conflicting meeting (should fail)", result2)
    
    # Clean up
    if result1.get("success"):
        handlers.delete_meeting(result1["meeting"]["id"])


def run_all_tests():
    """Run all tests."""
    print("\n" + "🧪"*30)
    print("  MCP CALENDAR TOOLS - INTEGRATION TESTS")
    print("🧪"*30)
    
    try:
        # Run tests in sequence
        meeting_id = test_schedule_meeting()
        test_get_meeting_details(meeting_id)
        test_list_all_meetings()
        test_update_meeting(meeting_id)
        test_validation()
        test_conflict_detection()
        test_delete_meeting(meeting_id)
        
        # Summary
        print_header("TEST SUMMARY")
        meetings = load_meetings(MEETINGS_FILE)
        print(f"\n📊 Final state: {len(meetings)} meeting(s) in database")
        print("\n✅ All tests completed!")
        print("\n💡 Note: Some tests are expected to fail (validation tests)")
        
    except Exception as e:
        print(f"\n❌ Test suite error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()