"""
Streamlit UI for Calendar Agent with Google Gemini and Google Calendar
"""
import streamlit as st
import json
from datetime import datetime, timedelta
from typing import Optional

from agent.calendar_agent import get_agent
from config.mcp_config import INTEGRATION_CONFIG
from integrations.google_calendar_service import get_google_calendar_service
import json


# Page configuration
st.set_page_config(
    page_title="📅 Calendar Agent (Gemini + Google Calendar)",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        text-align: center;
        color: #666;
        font-size: 0.9rem;
        margin-bottom: 1rem;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .user-message {
        background-color: #000000;
        border-left: 5px solid #1976d2;
    }
    .agent-message {
        background-color: #000000;
        border-left: 5px solid #4caf50;
    }
    .example-box {
        background-color: #000000;
        padding: 0.8rem;
        border-radius: 0.5rem;
        border-left: 5px solid #ff9800;
        margin: 0.5rem 0;
        font-size: 0.85rem;
    }
    .mcp-badge {
        background-color: #7c4dff;
        color: white;
        padding: 0.2rem 0.6rem;
        border-radius: 1rem;
        font-size: 0.75rem;
        font-weight: bold;
    }
    .metric-container {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """Initialize Streamlit session state."""
    if "agent" not in st.session_state:
        st.session_state.agent = get_agent()
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "input_key" not in st.session_state:
        st.session_state.input_key = 0
    
    # Settings session state
    if "google_calendar_id" not in st.session_state:
        st.session_state.google_calendar_id = "primary"
    
    if "google_credentials_json" not in st.session_state:
        st.session_state.google_credentials_json = ""
    
    if "google_auth_code" not in st.session_state:
        st.session_state.google_auth_code = ""
    
    if "google_auth_url" not in st.session_state:
        st.session_state.google_auth_url = ""
    
    if "google_token_json" not in st.session_state:
        st.session_state.google_token_json = None
    
    if "google_calendar_authenticated" not in st.session_state:
        st.session_state.google_calendar_authenticated = False


def display_chat_history():
    """Display chat message history."""
    for message in st.session_state.messages:
        role = message["role"]
        content = message["content"]
        
        if role == "user":
            st.markdown(f"""
            <div class="chat-message user-message">
                <strong>🧑 You:</strong><br>{content}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="chat-message agent-message">
                <strong>🤖 CalendarBot:</strong><br>{content}
            </div>
            """, unsafe_allow_html=True)


def display_sidebar():
    """Display sidebar with information and controls."""
    with st.sidebar:
        st.markdown("## 📅 Calendar Agent")
        st.markdown('<span class="mcp-badge">GOOGLE CALENDAR</span>', unsafe_allow_html=True)
        st.markdown("---")
        
        # Google Calendar Status
        st.markdown("### 🔌 Google Calendar Status")
        try:
            # Only try to get service if we have credentials or token, otherwise skip to avoid auto-auth
            if st.session_state.google_token_json or st.session_state.google_credentials_json:
                # Use skip_auth=True if we have a token to prevent re-authentication
                google_service = get_google_calendar_service(
                    credentials_json=st.session_state.google_credentials_json if st.session_state.google_credentials_json else None,
                    token_json=st.session_state.google_token_json,
                    calendar_id=st.session_state.google_calendar_id,
                    force_reinit=False,
                    skip_auth=True if st.session_state.google_token_json else False
                )
                if google_service.is_enabled():
                    st.success("✅ Connected to Google Calendar")
                    st.caption("Using Google Calendar as primary storage")
                else:
                    st.error("❌ Not Connected")
                    st.caption("Please configure Google Calendar in Settings")
            else:
                # No credentials yet, don't try to authenticate
                st.error("❌ Not Connected")
                st.caption("Please configure Google Calendar in Settings")
            if google_service.is_enabled():
                st.success("✅ Connected to Google Calendar")
                st.caption("Using Google Calendar as primary storage")
            else:
                st.error("❌ Not Connected")
                st.caption("Please configure Google Calendar in Settings")
        except Exception as e:
            st.error("❌ Connection Error")
            st.caption(f"Error: {str(e)}")
        
        st.markdown("---")
        
        # Statistics
        st.markdown("### 📊 Statistics")
        try:
            # Only get statistics if we have credentials/token
            if st.session_state.google_token_json or st.session_state.google_credentials_json:
                # Use skip_auth=True if we have a token to prevent re-authentication
                google_service = get_google_calendar_service(
                    credentials_json=st.session_state.google_credentials_json if st.session_state.google_credentials_json else None,
                    token_json=st.session_state.google_token_json,
                    calendar_id=st.session_state.google_calendar_id,
                    force_reinit=False,
                    skip_auth=True if st.session_state.google_token_json else False
                )
                # Get upcoming meetings (next 30 days)
                time_min = datetime.now()
                time_max = time_min + timedelta(days=30)
                meetings = google_service.get_events(time_min=time_min, time_max=time_max)
            else:
                meetings = []
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total", len(meetings))
            
            # Upcoming meetings count (future only)
            upcoming = sum(
                1 for m in meetings 
                if datetime.strptime(f"{m['date']} {m['time']}", "%Y-%m-%d %H:%M") > datetime.now()
            )
            with col2:
                st.metric("Upcoming", upcoming)
        except Exception:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total", "N/A")
            with col2:
                st.metric("Upcoming", "N/A")
        
        st.markdown("---")
        
        # Quick Actions
        st.markdown("### ⚡ Quick Actions")
        
        if st.button("📋 List All Meetings", use_container_width=True):
            st.session_state.quick_action = "List all my meetings"
        
        if st.button("📅 Today's Meetings", use_container_width=True):
            today = datetime.now().strftime("%Y-%m-%d")
            st.session_state.quick_action = f"Show me meetings on {today}"
        
        if st.button("🔄 Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.agent.reset_history()
            st.rerun()
        
        st.markdown("---")
        
        # Examples
        st.markdown("### 💡 Example Queries")
        
        examples = [
            "Schedule meeting with John tomorrow at 3 PM about project review",
            "Show meetings on 2024-12-25",
            "List all my meetings",
            "What meetings do I have with Sarah?",
            "Update meeting abc123 time to 5 PM",
            "Delete meeting xyz789"
        ]
        
        for example in examples:
            st.markdown(f"""
            <div class="example-box">
                {example}
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Google Integration Info
        with st.expander("ℹ️ About This App"):
            st.markdown("""
            **Google Gemini + Google Calendar Integration**
            
            This calendar assistant uses:
            - **Google Gemini 2.0 Flash** for natural language understanding
            - **Google Calendar API** as the primary data storage
            
            **Benefits:**
            - Real-time sync with your Google Calendar
            - Access meetings from any device
            - Automatic conflict detection
            - Email notifications
            - Google Meet integration
            
            All meetings are stored directly in your Google Calendar,
            ensuring seamless integration with your existing workflow.
            """)
        
        # Instructions
        with st.expander("📖 How to Use"):
            st.markdown("""
            **Schedule a Meeting:**
            ```
            Schedule meeting with John on 2024-12-25 at 10:00 AM
            ```
            
            **Query Meetings:**
            ```
            Show meetings on 2024-12-20
            Meetings with John
            Find project review meeting
            ```
            
            **Update Meeting:**
            ```
            Update meeting abc123 to 4 PM
            ```
            
            **Delete Meeting:**
            ```
            Delete meeting abc123
            ```
            """)


def validate_credentials_json(credentials_json: str) -> tuple[bool, Optional[dict], Optional[str]]:
    """Validate Google credentials JSON structure.
    
    Returns:
        (is_valid, parsed_dict, error_message)
    """
    if not credentials_json.strip():
        return False, None, "Credentials JSON cannot be empty"
    
    try:
        creds_dict = json.loads(credentials_json)
        
        # Check for required structure (either "installed" or "web")
        if "installed" not in creds_dict and "web" not in creds_dict:
            return False, None, "Invalid credentials format. Must contain 'installed' or 'web' key."
        
        # Check for client_id and client_secret
        creds = creds_dict.get("installed") or creds_dict.get("web")
        if not creds:
            return False, None, "Invalid credentials format."
        
        if not creds.get("client_id") or not creds.get("client_secret"):
            return False, None, "Missing client_id or client_secret in credentials."
        
        return True, creds_dict, None
        
    except json.JSONDecodeError as e:
        return False, None, f"Invalid JSON format: {str(e)}"
    except Exception as e:
        return False, None, f"Error validating credentials: {str(e)}"


def display_settings_tab():
    """Display the Settings tab UI."""
    st.markdown("## ⚙️ Google Calendar Settings")
    st.markdown("Configure your Google Calendar credentials to connect the Calendar Agent.")
    
    st.markdown("---")
    
    # Google Calendar ID
    st.markdown("### 📅 Calendar ID")
    calendar_id = st.text_input(
        "Calendar ID",
        value=st.session_state.google_calendar_id,
        placeholder="primary",
        help="Use 'primary' for your main calendar, or enter a specific calendar ID"
    )
    st.session_state.google_calendar_id = calendar_id or "primary"
    
    st.markdown("---")
    
    # Google API Credentials
    st.markdown("### 🔑 Google API Credentials")
    st.markdown("Paste your Google OAuth credentials JSON here. You can get this from [Google Cloud Console](https://console.cloud.google.com/).")
    
    credentials_json = st.text_area(
        "Credentials JSON",
        value=st.session_state.google_credentials_json,
        height=200,
        placeholder='{\n  "installed": {\n    "client_id": "...",\n    "client_secret": "...",\n    ...\n  }\n}',
        help="Paste the entire JSON content from your Google OAuth credentials file"
    )
    
    # Validate credentials on input
    if credentials_json:
        is_valid, creds_dict, error_msg = validate_credentials_json(credentials_json)
        if is_valid:
            st.success("✅ Valid credentials format")
            st.session_state.google_credentials_json = credentials_json
        else:
            st.error(f"❌ {error_msg}")
    else:
        st.session_state.google_credentials_json = ""
    
    st.markdown("---")
    
    # OAuth Authorization Flow
    st.markdown("### 🔐 OAuth Authorization")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔗 Generate Authorization URL", use_container_width=True):
            if not st.session_state.google_credentials_json:
                st.error("❌ Please enter credentials JSON first")
            else:
                try:
                    from integrations.google_calendar_service import GoogleCalendarService
                    service = GoogleCalendarService(skip_auth=True)
                    auth_url = service.generate_authorization_url(st.session_state.google_credentials_json)
                    st.session_state.google_auth_url = auth_url
                    st.success("✅ Authorization URL generated!")
                except Exception as e:
                    st.error(f"❌ Failed to generate URL: {str(e)}")
    
    with col2:
        if st.button("🔄 Clear URL", use_container_width=True):
            st.session_state.google_auth_url = ""
            st.rerun()
    
    # Display authorization URL
    if st.session_state.google_auth_url:
        st.markdown("**Authorization URL:**")
        st.code(st.session_state.google_auth_url, language=None)
        st.markdown("""
        **Instructions:**
        1. Click the URL above to open it in your browser
        2. Sign in with your Google account and authorize the app
        3. **IMPORTANT:** You might be redirected to a page that says "This site can't be reached" (localhost)
        4. Look at the **URL bar** of that page. It will look like: 
           `http://localhost:8080/?code=4/0Aean...&scope=...`
        5. Copy the value of the `code` parameter (everything between `code=` and `&scope`)
        6. Paste it below and click "Authenticate"
        """)
    
    st.markdown("---")
    
    # Authorization Code Input
    auth_code = st.text_input(
        "Authorization Code",
        value=st.session_state.google_auth_code,
        placeholder="4/0AeanS...",
        help="Paste the authorization code from the OAuth redirect page"
    )
    st.session_state.google_auth_code = auth_code
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("✅ Authenticate with Code", use_container_width=True, type="primary"):
            if not st.session_state.google_credentials_json:
                st.error("❌ Please enter credentials JSON first")
            elif not auth_code:
                st.error("❌ Please enter authorization code")
            else:
                try:
                    from integrations.google_calendar_service import GoogleCalendarService
                    service = GoogleCalendarService(skip_auth=True)
                    token = service.exchange_code_for_token(
                        st.session_state.google_credentials_json,
                        auth_code
                    )
                    st.session_state.google_token_json = json.loads(token.to_json())
                    
                    # Re-initialize service with new credentials (skip auth since we already have token)
                    get_google_calendar_service(
                        credentials_json=st.session_state.google_credentials_json,
                        token_json=st.session_state.google_token_json,
                        calendar_id=st.session_state.google_calendar_id,
                        force_reinit=True,
                        skip_auth=True  # Prevent auto-authentication that opens browser tabs
                    )
                    
                    # Mark as authenticated
                    st.session_state.google_calendar_authenticated = True
                    
                    st.success("✅ Authentication successful! Your calendar is now connected.")
                    st.info("💡 You can now use the Chat tab to interact with your calendar.")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Authentication failed: {str(e)}")
    
    with col2:
        if st.button("💾 Save Settings", use_container_width=True):
            st.success("✅ Settings saved to session")
    
    st.markdown("---")
    
    # Connection Status
    st.markdown("### 📊 Connection Status")
    try:
        # Try to get service with session credentials
        # Use skip_auth=True if we have a token to prevent re-authentication
        service = get_google_calendar_service(
            credentials_json=st.session_state.google_credentials_json if st.session_state.google_credentials_json else None,
            token_json=st.session_state.google_token_json,
            calendar_id=st.session_state.google_calendar_id,
            force_reinit=False,
            skip_auth=True if st.session_state.google_token_json else False
        )
        
        if service.is_enabled():
            st.success("✅ Connected to Google Calendar")
            st.caption(f"Using calendar: {st.session_state.google_calendar_id}")
        else:
            st.warning("⚠️ Not connected. Please configure credentials and authenticate.")
    except Exception as e:
        st.error(f"❌ Connection error: {str(e)}")
    
    st.markdown("---")
    
    # Instructions
    with st.expander("📖 Setup Instructions"):
        st.markdown("""
        **Step 1: Get Google OAuth Credentials**
        
        1. Go to [Google Cloud Console](https://console.cloud.google.com/)
        2. Create a new project or select an existing one
        3. Enable the "Google Calendar API"
        4. Go to "Credentials" → "Create Credentials" → "OAuth client ID"
        5. Choose "Desktop app" as the application type
        6. Download the JSON file
        7. Copy the entire JSON content and paste it in the "Credentials JSON" field above
        
        **Step 2: Generate Authorization URL**
        
        1. Click "Generate Authorization URL"
        2. Copy the generated URL
        
        **Step 3: Authorize**
        
        1. Open the authorization URL in your browser
        2. Sign in with your Google account
        3. Click "Allow" to grant permissions
        4. Copy the authorization code from the redirect page
        5. Paste it in the "Authorization Code" field
        6. Click "Authenticate with Code"
        
        **Step 4: Verify**
        
        Check the "Connection Status" section above to confirm you're connected.
        """)
    
    with st.expander("🔒 Security Notes"):
        st.markdown("""
        - Credentials are stored in session state (ephemeral, cleared on restart)
        - For production deployment, use Streamlit Secrets
        - Never share your credentials or authorization codes
        - Tokens are automatically refreshed when expired
        """)


def main():
    """Main application function."""
    initialize_session_state()
    
    # Header
    st.markdown('<h1 class="main-header">📅 Calendar Agent</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">AI-powered meeting assistant with Google Gemini & Google Calendar</p>',
        unsafe_allow_html=True
    )
    
    # Sidebar
    display_sidebar()
    
    # Tabs for Chat and Settings
    tab1, tab2 = st.tabs(["💬 Chat", "⚙️ Settings"])
    
    with tab1:
        # Main chat area
        st.markdown("---")
        
        # Chat container
        chat_container = st.container()
        
        with chat_container:
            display_chat_history()
    
        # Handle quick action from sidebar
        if hasattr(st.session_state, 'quick_action'):
            user_input = st.session_state.quick_action
            delattr(st.session_state, 'quick_action')
            
            # Add user message
            st.session_state.messages.append({"role": "user", "content": user_input})
            
            # Get agent response
            with st.spinner("🤔 Processing with Google Gemini..."):
                response = st.session_state.agent.run(user_input)
            
            # Add agent response
            st.session_state.messages.append({"role": "agent", "content": response})
            st.rerun()
        
        # Input area (fixed at bottom)
        st.markdown("---")
        
        col1, col2 = st.columns([6, 1])
        
        with col1:
            user_input = st.text_input(
                "Type your message here...",
                key=f"user_input_{st.session_state.input_key}",
                placeholder="e.g., Schedule a meeting with John tomorrow at 3 PM",
                label_visibility="collapsed"
            )
        
        with col2:
            send_button = st.button("Send 📤", use_container_width=True)
        
        # Handle message submission
        if send_button and user_input.strip():
            # Add user message
            st.session_state.messages.append({"role": "user", "content": user_input})
            
            # Get agent response
            with st.spinner("🤔 Processing with Google Gemini..."):
                response = st.session_state.agent.run(user_input)
            
            # Add agent response
            st.session_state.messages.append({"role": "agent", "content": response})
            
            # Increment input key to clear the input field
            st.session_state.input_key += 1
            
            # Rerun to update the UI
            st.rerun()
        
        # Welcome message for first-time users
        if not st.session_state.messages:
            st.info("""
            👋 **Welcome to Calendar Agent!**
            
            I'm your AI-powered calendar assistant using Google Gemini and Google Calendar.
            
            Try asking me to:
            - Schedule a new meeting in your Google Calendar
            - Check your upcoming meetings
            - Update or delete meetings
            
            Just type naturally, and I'll handle the rest! 🚀
            """)
    
    with tab2:
        display_settings_tab()


if __name__ == "__main__":
    main()