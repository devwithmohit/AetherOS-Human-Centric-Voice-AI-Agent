"""Tool selector for choosing appropriate tools based on intent."""

from typing import List, Dict, Any
from enum import Enum


class ToolType(str, Enum):
    """Available tool types for execution."""

    # Application tools
    OPEN_APPLICATION = "open_application"
    CLOSE_APPLICATION = "close_application"
    SWITCH_APPLICATION = "switch_application"

    # System tools
    SYSTEM_CONTROL = "system_control"
    VOLUME_CONTROL = "volume_control"
    BRIGHTNESS_CONTROL = "brightness_control"
    SCREENSHOT = "screenshot"

    # Information tools
    WEB_SEARCH = "web_search"
    FILE_SEARCH = "file_search"
    GET_WEATHER = "get_weather"
    GET_NEWS = "get_news"
    GET_TIME = "get_time"
    CALCULATOR = "calculator"

    # Communication tools
    SEND_EMAIL = "send_email"
    SEND_MESSAGE = "send_message"
    MAKE_CALL = "make_call"

    # Media tools
    MEDIA_PLAYER = "media_player"

    # Smart home tools
    SMART_HOME_CONTROL = "smart_home_control"

    # Navigation tools
    NAVIGATION = "navigation"

    # Productivity tools
    CALENDAR = "calendar"
    REMINDER = "reminder"
    NOTE_TAKING = "note_taking"

    # Shopping tools
    SHOPPING = "shopping"

    # Utility tools
    TIMER = "timer"
    ALARM = "alarm"
    UNIT_CONVERTER = "unit_converter"

    # Meta tools
    HELP = "help"
    CLARIFICATION = "clarification"


# Intent to tool mapping
INTENT_TO_TOOLS = {
    # Application control
    "open_app": [ToolType.OPEN_APPLICATION],
    "close_app": [ToolType.CLOSE_APPLICATION],
    "switch_app": [ToolType.SWITCH_APPLICATION],
    "minimize_app": [ToolType.OPEN_APPLICATION],
    "maximize_app": [ToolType.OPEN_APPLICATION],
    # System control
    "shutdown": [ToolType.SYSTEM_CONTROL],
    "restart_system": [ToolType.SYSTEM_CONTROL],
    "lock_screen": [ToolType.SYSTEM_CONTROL],
    "increase_volume": [ToolType.VOLUME_CONTROL],
    "decrease_volume": [ToolType.VOLUME_CONTROL],
    "mute_volume": [ToolType.VOLUME_CONTROL],
    "unmute_volume": [ToolType.VOLUME_CONTROL],
    "increase_brightness": [ToolType.BRIGHTNESS_CONTROL],
    "decrease_brightness": [ToolType.BRIGHTNESS_CONTROL],
    "take_screenshot": [ToolType.SCREENSHOT],
    # Information retrieval
    "get_weather": [ToolType.GET_WEATHER],
    "get_news": [ToolType.GET_NEWS],
    "get_time": [ToolType.GET_TIME],
    "search_web": [ToolType.WEB_SEARCH],
    "search_files": [ToolType.FILE_SEARCH],
    "calculate": [ToolType.CALCULATOR],
    # Communication
    "send_email": [ToolType.SEND_EMAIL],
    "send_message": [ToolType.SEND_MESSAGE],
    "make_call": [ToolType.MAKE_CALL],
    # Media
    "play_music": [ToolType.MEDIA_PLAYER],
    "play_video": [ToolType.MEDIA_PLAYER],
    "pause_media": [ToolType.MEDIA_PLAYER],
    "resume_media": [ToolType.MEDIA_PLAYER],
    "next_track": [ToolType.MEDIA_PLAYER],
    "previous_track": [ToolType.MEDIA_PLAYER],
    "stop_media": [ToolType.MEDIA_PLAYER],
    # Smart home
    "turn_on_lights": [ToolType.SMART_HOME_CONTROL],
    "turn_off_lights": [ToolType.SMART_HOME_CONTROL],
    "dim_lights": [ToolType.SMART_HOME_CONTROL],
    "set_temperature": [ToolType.SMART_HOME_CONTROL],
    "lock_door": [ToolType.SMART_HOME_CONTROL],
    "unlock_door": [ToolType.SMART_HOME_CONTROL],
    # Navigation
    "get_directions": [ToolType.NAVIGATION],
    "find_location": [ToolType.NAVIGATION],
    "find_nearby": [ToolType.NAVIGATION],
    # Productivity
    "create_reminder": [ToolType.REMINDER],
    "list_reminders": [ToolType.REMINDER],
    "delete_reminder": [ToolType.REMINDER],
    "schedule_meeting": [ToolType.CALENDAR],
    "check_calendar": [ToolType.CALENDAR],
    "take_note": [ToolType.NOTE_TAKING],
    "read_note": [ToolType.NOTE_TAKING],
    # Shopping
    "add_to_cart": [ToolType.SHOPPING],
    "check_price": [ToolType.SHOPPING],
    "track_order": [ToolType.SHOPPING],
    # Utility
    "set_timer": [ToolType.TIMER],
    "set_alarm": [ToolType.ALARM],
    "convert_units": [ToolType.UNIT_CONVERTER],
    # Meta
    "help": [ToolType.HELP],
    "requires_clarification": [ToolType.CLARIFICATION],
}


class ToolSelector:
    """Select appropriate tools based on intent and context."""

    def __init__(self):
        """Initialize tool selector."""
        self.intent_to_tools = INTENT_TO_TOOLS

    def select_tools(self, intent: str, entities: Dict[str, Any]) -> List[ToolType]:
        """Select tools for the given intent.

        Args:
            intent: Intent string from M4
            entities: Extracted entities

        Returns:
            List of ToolType enums
        """
        # Direct mapping
        tools = self.intent_to_tools.get(intent, [])

        # Handle complex scenarios
        if not tools:
            tools = [ToolType.HELP]  # Default to help if unknown

        return tools

    def get_tool_description(self, tool: ToolType) -> str:
        """Get human-readable description of tool.

        Args:
            tool: ToolType enum

        Returns:
            Tool description string
        """
        descriptions = {
            ToolType.OPEN_APPLICATION: "Open or launch applications",
            ToolType.CLOSE_APPLICATION: "Close or quit applications",
            ToolType.SYSTEM_CONTROL: "Control system operations (shutdown, restart, lock)",
            ToolType.VOLUME_CONTROL: "Adjust system volume",
            ToolType.BRIGHTNESS_CONTROL: "Adjust screen brightness",
            ToolType.SCREENSHOT: "Capture screenshots",
            ToolType.WEB_SEARCH: "Search the internet",
            ToolType.FILE_SEARCH: "Search local files",
            ToolType.GET_WEATHER: "Get weather information",
            ToolType.GET_NEWS: "Fetch news articles",
            ToolType.GET_TIME: "Get current time/date",
            ToolType.CALCULATOR: "Perform calculations",
            ToolType.SEND_EMAIL: "Send email messages",
            ToolType.SEND_MESSAGE: "Send text messages",
            ToolType.MAKE_CALL: "Make phone calls",
            ToolType.MEDIA_PLAYER: "Control media playback",
            ToolType.SMART_HOME_CONTROL: "Control smart home devices",
            ToolType.NAVIGATION: "Get directions and navigation",
            ToolType.CALENDAR: "Manage calendar events",
            ToolType.REMINDER: "Manage reminders",
            ToolType.NOTE_TAKING: "Take and manage notes",
            ToolType.SHOPPING: "Shopping-related tasks",
            ToolType.TIMER: "Set and manage timers",
            ToolType.ALARM: "Set and manage alarms",
            ToolType.UNIT_CONVERTER: "Convert units",
            ToolType.HELP: "Provide help and assistance",
            ToolType.CLARIFICATION: "Request clarification from user",
        }
        return descriptions.get(tool, tool.value)

    def get_tool_parameters(self, tool: ToolType, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Extract tool parameters from entities.

        Args:
            tool: ToolType enum
            entities: Extracted entities from M4

        Returns:
            Dictionary of tool parameters
        """
        params = {}

        # Application tools
        if tool == ToolType.OPEN_APPLICATION:
            params["app_name"] = entities.get("app_name", "")

        # Volume control
        elif tool == ToolType.VOLUME_CONTROL:
            params["level"] = entities.get("numbers", [50])[0] if "numbers" in entities else None

        # Weather
        elif tool == ToolType.GET_WEATHER:
            params["location"] = entities.get("location", "")

        # Web search
        elif tool == ToolType.WEB_SEARCH:
            params["query"] = entities.get("search_query", "")

        # Timer
        elif tool == ToolType.TIMER:
            if "relative_time" in entities:
                params["duration"] = entities["relative_time"]

        # Alarm
        elif tool == ToolType.ALARM:
            if "clock_time" in entities:
                params["time"] = entities["clock_time"]

        # Reminder
        elif tool == ToolType.REMINDER:
            if "clock_time" in entities or "relative_time" in entities:
                params["time"] = entities.get("clock_time") or entities.get("relative_time")

        # Media
        elif tool == ToolType.MEDIA_PLAYER:
            params["media_title"] = entities.get("media_title", "")
            params["artist"] = entities.get("artist", "")

        # Smart home
        elif tool == ToolType.SMART_HOME_CONTROL:
            if "temperature" in entities:
                params["temperature"] = entities["temperature"]

        return params

    def format_tools_for_prompt(self, tools: List[ToolType]) -> str:
        """Format tool list for LLM prompt.

        Args:
            tools: List of ToolType enums

        Returns:
            Formatted tool description string
        """
        lines = ["Available Tools:"]
        for tool in tools:
            lines.append(f"  - {tool.value}: {self.get_tool_description(tool)}")
        return "\n".join(lines)
