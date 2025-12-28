"""
MCP Server Implementation for Calendar Tools
"""
import json
import sys
from typing import Any, Sequence
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from mcp_server.handlers import CalendarHandlers
from config.mcp_config import MCP_SERVER_CONFIG, CALENDAR_CONFIG


class CalendarMCPServer:
    """MCP Server for Calendar operations."""
    
    def __init__(self):
        self.server = Server(MCP_SERVER_CONFIG["server_name"])
        self.handlers = CalendarHandlers()
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Set up MCP tool handlers."""
        
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available calendar tools."""
            return [
                Tool(
                    name="schedule_meeting",
                    description="Schedule a new meeting with participants",
                    inputSchema={
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
                                "description": "Meeting time in HH:MM format (24-hour)"
                            },
                            "participants": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of participant names"
                            },
                            "description": {
                                "type": "string",
                                "description": "Optional meeting description"
                            }
                        },
                        "required": ["title", "date", "time", "participants"]
                    }
                ),
                Tool(
                    name="get_meeting_details",
                    description="Get meeting details with optional filters",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "date": {
                                "type": "string",
                                "description": "Filter by date (YYYY-MM-DD)"
                            },
                            "participant": {
                                "type": "string",
                                "description": "Filter by participant name"
                            },
                            "title": {
                                "type": "string",
                                "description": "Filter by meeting title"
                            },
                            "meeting_id": {
                                "type": "string",
                                "description": "Get specific meeting by ID"
                            }
                        }
                    }
                ),
                Tool(
                    name="list_all_meetings",
                    description="List all scheduled meetings sorted by date and time",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="update_meeting",
                    description="Update an existing meeting by ID",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "meeting_id": {
                                "type": "string",
                                "description": "ID of the meeting to update"
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
                ),
                Tool(
                    name="delete_meeting",
                    description="Delete a meeting by ID",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "meeting_id": {
                                "type": "string",
                                "description": "ID of the meeting to delete"
                            }
                        },
                        "required": ["meeting_id"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> Sequence[TextContent]:
            """Execute a calendar tool."""
            try:
                # Route to appropriate handler
                if name == "schedule_meeting":
                    result = self.handlers.schedule_meeting(
                        title=arguments.get("title"),
                        date=arguments.get("date"),
                        time=arguments.get("time"),
                        participants=arguments.get("participants"),
                        description=arguments.get("description", "")
                    )
                
                elif name == "get_meeting_details":
                    result = self.handlers.get_meeting_details(
                        date=arguments.get("date"),
                        participant=arguments.get("participant"),
                        title=arguments.get("title"),
                        meeting_id=arguments.get("meeting_id")
                    )
                
                elif name == "list_all_meetings":
                    result = self.handlers.list_all_meetings()
                
                elif name == "update_meeting":
                    result = self.handlers.update_meeting(
                        meeting_id=arguments.get("meeting_id"),
                        title=arguments.get("title"),
                        date=arguments.get("date"),
                        time=arguments.get("time"),
                        participants=arguments.get("participants"),
                        description=arguments.get("description")
                    )
                
                elif name == "delete_meeting":
                    result = self.handlers.delete_meeting(
                        meeting_id=arguments.get("meeting_id")
                    )
                
                else:
                    result = {
                        "success": False,
                        "error": f"Unknown tool: {name}"
                    }
                
                # Format response
                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
                
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": f"Tool execution error: {str(e)}"
                    }, indent=2)
                )]
    
    async def run(self):
        """Run the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def main():
    """Main entry point for MCP server."""
    server = CalendarMCPServer()
    await server.run()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())