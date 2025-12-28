"""
Calendar Agent with MCP Integration using Google Gemini API
"""
import json
from typing import List, Dict, Any
import google.generativeai as genai

from config.mcp_config import (
    GOOGLE_API_KEY,
    MODEL_NAME,
    MAX_TOKENS,
    SYSTEM_MESSAGE
)


class CalendarAgent:
    """Calendar Agent with MCP tool support via Google Gemini API."""
    
    def __init__(self):
        """Initialize the calendar agent with Gemini client."""
        genai.configure(api_key=GOOGLE_API_KEY)
        
        # Initialize Gemini model with function calling
        self.model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            tools=self._define_mcp_tools(),
            system_instruction=SYSTEM_MESSAGE
        )
        
        # Disable automatic function calling to handle it manually
        self.chat = self.model.start_chat(enable_automatic_function_calling=False)
        self.conversation_history: List[Dict[str, Any]] = []
    
    def _define_mcp_tools(self) -> List[Any]:
        """Define MCP tools in Gemini format."""
        from mcp_server.handlers import CalendarHandlers
        
        # Create handler instance
        handlers = CalendarHandlers()
        
        # Define function declarations for Gemini
        return [
            {
                "function_declarations": [
                    {
                        "name": "schedule_meeting",
                        "description": "Schedule a new meeting in Google Calendar. Participants are optional - only include if email addresses are provided. Returns success status and meeting details.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "title": {
                                    "type": "string",
                                    "description": "Meeting title or subject"
                                },
                                "date": {
                                    "type": "string",
                                    "description": "Meeting date in YYYY-MM-DD format"
                                },
                                "time": {
                                    "type": "string",
                                    "description": "Meeting time in HH:MM format (24-hour) or 12-hour with AM/PM"
                                },
                                "participants": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Optional list of participant email addresses. Only valid email addresses will be added as attendees."
                                },
                                "description": {
                                    "type": "string",
                                    "description": "Optional meeting description"
                                }
                            },
                            "required": ["title", "date", "time"]
                        }
                    },
                    {
                        "name": "get_meeting_details",
                        "description": "Get meeting details from Google Calendar with optional filters (date, participant, title, or meeting_id)",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "date": {
                                    "type": "string",
                                    "description": "Filter by date (YYYY-MM-DD format)"
                                },
                                "participant": {
                                    "type": "string",
                                    "description": "Filter by participant name"
                                },
                                "title": {
                                    "type": "string",
                                    "description": "Filter by meeting title (partial match)"
                                },
                                "meeting_id": {
                                    "type": "string",
                                    "description": "Get specific meeting by Google event ID"
                                }
                            }
                        }
                    },
                    {
                        "name": "list_all_meetings",
                        "description": "List all upcoming meetings from Google Calendar sorted by date and time",
                        "parameters": {
                            "type": "object",
                            "properties": {}
                        }
                    },
                    {
                        "name": "update_meeting",
                        "description": "Update an existing meeting in Google Calendar by ID. Only provided fields will be updated.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "meeting_id": {
                                    "type": "string",
                                    "description": "Google event ID of the meeting to update"
                                },
                                "title": {
                                    "type": "string",
                                    "description": "New meeting title"
                                },
                                "date": {
                                    "type": "string",
                                    "description": "New date (YYYY-MM-DD)"
                                },
                                "time": {
                                    "type": "string",
                                    "description": "New time (HH:MM)"
                                },
                                "participants": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "New participant list"
                                },
                                "description": {
                                    "type": "string",
                                    "description": "New description"
                                }
                            },
                            "required": ["meeting_id"]
                        }
                    },
                    {
                        "name": "delete_meeting",
                        "description": "Delete a meeting from Google Calendar by its ID",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "meeting_id": {
                                    "type": "string",
                                    "description": "Google event ID of the meeting to delete"
                                }
                            },
                            "required": ["meeting_id"]
                        }
                    }
                ]
            }
        ]
    
    def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool by calling the MCP handlers directly.
        """
        from mcp_server.handlers import CalendarHandlers
        
        handlers = CalendarHandlers()
        
        try:
            if tool_name == "schedule_meeting":
                return handlers.schedule_meeting(**tool_input)
            elif tool_name == "get_meeting_details":
                return handlers.get_meeting_details(**tool_input)
            elif tool_name == "list_all_meetings":
                return handlers.list_all_meetings()
            elif tool_name == "update_meeting":
                return handlers.update_meeting(**tool_input)
            elif tool_name == "delete_meeting":
                return handlers.delete_meeting(**tool_input)
            else:
                return {
                    "success": False,
                    "error": f"Unknown tool: {tool_name}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Tool execution error: {str(e)}"
            }
    
    def run(self, user_input: str) -> str:
        """
        Process user input and return agent response.
        
        Args:
            user_input: User's natural language query
            
        Returns:
            Agent's response as string
        """
        try:
            # Send message to Gemini
            response = self.chat.send_message(user_input)
            
            # Handle function calls manually
            while response.candidates[0].content.parts:
                part = response.candidates[0].content.parts[0]
                
                # Check if this is a function call
                if hasattr(part, 'function_call') and part.function_call:
                    function_call = part.function_call
                    function_name = function_call.name
                    function_args = dict(function_call.args)
                    
                    # Execute the function
                    function_result = self._execute_tool(function_name, function_args)
                    
                    # Send the function result back to Gemini
                    response = self.chat.send_message(
                        genai.protos.Content(
                            parts=[
                                genai.protos.Part(
                                    function_response=genai.protos.FunctionResponse(
                                        name=function_name,
                                        response={"result": function_result}
                                    )
                                )
                            ]
                        )
                    )
                else:
                    # No more function calls, extract text response
                    break
            
            # Extract final text response
            result_text = ""
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'text') and part.text:
                    result_text += part.text
            
            # Return the response
            if result_text.strip():
                return result_text.strip()
            else:
                return "Operation completed successfully."
            
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}\n\nPlease try rephrasing your request."
            return error_msg
    
    def reset_history(self):
        """Clear conversation history."""
        self.chat = self.model.start_chat(enable_automatic_function_calling=False)
        self.conversation_history = []
    
    def get_history(self) -> List[Dict[str, Any]]:
        """Get current conversation history."""
        return self.conversation_history


# Singleton instance
_agent_instance = None


def get_agent() -> CalendarAgent:
    """Get or create the calendar agent singleton instance."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = CalendarAgent()
    return _agent_instance