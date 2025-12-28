"""
Google Calendar Authentication Setup Script
Run this once to authenticate with Google Calendar
"""
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from config.google_calendar_config import GOOGLE_CALENDAR_CONFIG, CREDENTIALS_DIR
from integrations.google_calendar_service import GoogleCalendarService


def print_banner():
    """Print setup banner."""
    print("\n" + "="*70)
    print("  📅 Google Calendar Authentication Setup")
    print("="*70)
    print("\nThis wizard will help you connect your Google Calendar.\n")


def check_credentials_file():
    """Check if credentials file exists and is valid."""
    credentials_file = GOOGLE_CALENDAR_CONFIG["credentials_file"]
    
    # Check if credentials file exists
    if not credentials_file.exists():
        print("❌ Google credentials file not found!")
        print(f"\nExpected location: {credentials_file}")
        print("\n📝 To get your credentials:")
        print("   1. Go to: https://console.cloud.google.com/")
        print("   2. Create a new project (or select existing)")
        print("   3. Enable 'Google Calendar API'")
        print("   4. Go to 'Credentials' \u2192 'Create Credentials' \u2192 'OAuth client ID'")
        print("   5. Choose 'Desktop app' as application type")
        print("   6. Download the JSON file")
        print(f"   7. Save it as: {credentials_file}")
        print("\n💡 Detailed instructions: https://developers.google.com/calendar/api/quickstart/python")
        return False

    # Check credential type
    try:
        import json
        with open(credentials_file, 'r') as f:
            data = json.load(f)
            
        if "web" in data:
            print(f"✅ Found credentials file: {credentials_file}")
            print("\n⚠️  WARNING: DETECTED 'WEB APPLICATION' CREDENTIALS!")
            print("   Desktop apps require 'Desktop' credentials.")
            print("   The '400 Malformed' error is likely caused by this.")
            print("\n   Please go to Google Cloud Console:")
            print("   1. Delete the current 'Web' credential")
            print("   2. Create a NEW credential")
            print("   3. Select application type: 'Desktop app' (strictly)")
        if "installed" in data:
            creds = data["installed"]
            client_id = creds.get("client_id", "")
            client_secret = creds.get("client_secret", "")
            
            if not client_id or not client_secret:
                print(f"✅ Found credentials file: {credentials_file}")
                print("\n❌ ERROR: Invalid credentials file!")
                print("   Missing client_id or client_secret.")
                return False
                
            if client_id.strip() != client_id or client_secret.strip() != client_secret:
                print(f"✅ Found credentials file: {credentials_file}")
                print("\n❌ ERROR: Malformed credentials detected!")
                print("   The client_id or client_secret contains extra spaces or newlines.")
                print("   This often happens when copy-pasting.")
                print("   Please download the JSON file again from Google Cloud Console.")
                return False
        
        if "installed" not in data:
            print(f"✅ Found credentials file: {credentials_file}")
            print("\n⚠️  WARNING: UNKNOWN CREDENTIAL TYPE!")
            print("   Expected 'installed' (Desktop) key in JSON.")
    except Exception as e:
        print(f"⚠️  Error reading credentials file: {e}")

    print(f"✅ Found credentials file (Desktop): {credentials_file}")
    return True


def authenticate():
    """Run authentication flow."""
    print("\n🔐 Starting authentication...")
    print("   A browser window will open for you to sign in to Google.")
    print("   Please authorize the Calendar Agent to access your calendar.\n")
    
    try:
        service = GoogleCalendarService()
        
        if service.is_enabled():
            print("\n✅ Authentication successful!")
            print(f"   Token saved to: {GOOGLE_CALENDAR_CONFIG['token_file']}")
            
            # Test by listing calendars
            print("\n🧪 Testing connection...")
            try:
                calendar_list = service.service.calendarList().list().execute()
                calendars = calendar_list.get("items", [])
                
                print(f"\n✅ Found {len(calendars)} calendar(s):")
                for cal in calendars[:5]:  # Show first 5
                    name = cal.get("summary", "Unknown")
                    cal_id = cal.get("id", "")
                    is_primary = " (Primary)" if cal.get("primary") else ""
                    print(f"   • {name}{is_primary}")
                    print(f"     ID: {cal_id}")
                
                return True
            except Exception as e:
                print(f"⚠️  Could not list calendars: {e}")
                return True  # Auth worked, listing failed
        else:
            print("\n❌ Authentication failed!")
            return False
            
    except Exception as e:
        print(f"\n❌ Authentication error: {e}")
        return False


def update_env_file():
    """Update .env file to enable Google Calendar."""
    env_file = Path(".env")
    
    if not env_file.exists():
        print("\n⚠️  .env file not found. Creating one...")
        with open(env_file, "w") as f:
            f.write("# Calendar Agent Configuration\n\n")
    
    # Read existing content
    with open(env_file, "r") as f:
        lines = f.readlines()
    
    # Check if GOOGLE_CALENDAR_ENABLED exists
    has_setting = any("GOOGLE_CALENDAR_ENABLED" in line for line in lines)
    
    if not has_setting:
        with open(env_file, "a") as f:
            f.write("\n# Google Calendar Integration\n")
            f.write("GOOGLE_CALENDAR_ENABLED=true\n")
        print(f"\n✅ Updated .env file: GOOGLE_CALENDAR_ENABLED=true")
    else:
        print("\n✅ .env file already configured")


def print_next_steps():
    """Print next steps."""
    print("\n" + "="*70)
    print("  🎉 Setup Complete!")
    print("="*70)
    print("\n✅ Google Calendar is now connected to your Calendar Agent!")
    print("\n📋 Next Steps:")
    print("   1. Run your Calendar Agent: streamlit run app.py")
    print("   2. Create a meeting using natural language")
    print("   3. Check your Google Calendar - it should appear there!")
    print("\n🔄 Sync Settings:")
    print("   • Auto-sync on create: Enabled")
    print("   • Auto-sync on update: Enabled")
    print("   • Auto-sync on delete: Enabled")
    print("\n⚙️  To configure sync settings, edit: config/google_calendar_config.py")
    print("\n💡 Pro Tip: Participants with email addresses will receive calendar invites!")
    print("="*70 + "\n")


def main():
    """Main setup function."""
    print_banner()
    
    # Ensure credentials directory exists
    CREDENTIALS_DIR.mkdir(exist_ok=True)
    print(f"📁 Credentials directory: {CREDENTIALS_DIR}")
    
    # Check for credentials file
    if not check_credentials_file():
        print("\n⏸️  Setup paused. Please follow the instructions above to get credentials.")
        return
    
    # Run authentication
    print("\n" + "-"*70)
    if authenticate():
        update_env_file()
        print_next_steps()
    else:
        print("\n❌ Setup failed. Please try again or check the error messages above.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Setup cancelled by user.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()