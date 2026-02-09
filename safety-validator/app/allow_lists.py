"""Allow lists and whitelists for tools and commands."""

import re
from enum import Enum
from typing import Set, List, Dict, Any
import yaml
from pathlib import Path


class ToolCategory(str, Enum):
    """Tool categories for allow list management."""

    # Information retrieval
    GET_WEATHER = "GET_WEATHER"
    GET_TIME = "GET_TIME"
    GET_DATE = "GET_DATE"
    WEB_SEARCH = "WEB_SEARCH"
    GET_NEWS = "GET_NEWS"

    # Media control
    MEDIA_PLAYER = "MEDIA_PLAYER"
    VOLUME_CONTROL = "VOLUME_CONTROL"
    MUSIC_CONTROL = "MUSIC_CONTROL"
    SCREEN_CONTROL = "SCREEN_CONTROL"

    # Application control
    OPEN_APPLICATION = "OPEN_APPLICATION"
    CLOSE_APPLICATION = "CLOSE_APPLICATION"

    # System control
    SYSTEM_CONTROL = "SYSTEM_CONTROL"
    DEVICE_CONTROL = "DEVICE_CONTROL"

    # Productivity
    SET_TIMER = "SET_TIMER"
    SET_ALARM = "SET_ALARM"
    REMINDER = "REMINDER"
    NOTE_TAKING = "NOTE_TAKING"
    LIST_MANAGEMENT = "LIST_MANAGEMENT"
    CALENDAR = "CALENDAR"

    # Communication
    SEND_EMAIL = "SEND_EMAIL"
    SEND_MESSAGE = "SEND_MESSAGE"
    MAKE_CALL = "MAKE_CALL"

    # Smart home
    LIGHT_CONTROL = "LIGHT_CONTROL"
    TEMPERATURE_CONTROL = "TEMPERATURE_CONTROL"
    SMART_HOME_CONTROL = "SMART_HOME_CONTROL"

    # Navigation
    NAVIGATION = "NAVIGATION"

    # File operations
    FILE_OPERATION = "FILE_OPERATION"

    # Financial
    PAYMENT = "PAYMENT"
    PURCHASE = "PURCHASE"
    BOOKING = "BOOKING"
    SUBSCRIPTION = "SUBSCRIPTION"

    # Conversational
    HELP = "HELP"
    GREETING = "GREETING"
    FAREWELL = "FAREWELL"
    JOKE = "JOKE"
    FACT = "FACT"
    QUOTE = "QUOTE"

    # Utilities
    MATH_CALCULATION = "MATH_CALCULATION"
    UNIT_CONVERSION = "UNIT_CONVERSION"
    TRANSLATION = "TRANSLATION"

    # Dangerous - blocked by default
    SYSTEM_SHUTDOWN = "SYSTEM_SHUTDOWN"
    SYSTEM_RESTART = "SYSTEM_RESTART"
    DELETE_FILE = "DELETE_FILE"
    FORMAT_DRIVE = "FORMAT_DRIVE"
    ADMIN_COMMAND = "ADMIN_COMMAND"
    DATABASE_MODIFY = "DATABASE_MODIFY"
    USER_ACCOUNT_MODIFY = "USER_ACCOUNT_MODIFY"


class AllowListManager:
    """Manage allow lists and whitelists for security validation."""

    def __init__(self, config_path: str = "config/policies.yaml"):
        """Initialize allow list manager.

        Args:
            config_path: Path to policies configuration file
        """
        self.config_path = Path(config_path)
        self.policies = self._load_policies()

        self.allowed_tools: Set[str] = set(self.policies.get("allowed_tools", []))
        self.blocked_tools: Set[str] = set(self.policies.get("blocked_tools", []))
        self.allowed_apps: Set[str] = set(
            self.policies.get("parameter_rules", {}).get("applications", {}).get("allowed_apps", [])
        )

    def _load_policies(self) -> Dict[str, Any]:
        """Load policies from YAML file.

        Returns:
            Dictionary of policies
        """
        try:
            # Try absolute path first
            if self.config_path.exists():
                with open(self.config_path, "r") as f:
                    return yaml.safe_load(f)

            # Try relative to module
            module_dir = Path(__file__).parent.parent
            config_file = module_dir / self.config_path

            if config_file.exists():
                with open(config_file, "r") as f:
                    return yaml.safe_load(f)

            # Return empty dict if file not found
            return {}

        except Exception as e:
            print(f"Warning: Failed to load policies from {self.config_path}: {e}")
            return {}

    def is_tool_allowed(self, tool: str) -> bool:
        """Check if a tool is on the allow list.

        Args:
            tool: Tool name to check

        Returns:
            True if allowed, False otherwise
        """
        # Normalize tool name
        tool_upper = tool.upper()

        # Check if explicitly blocked
        if tool_upper in self.blocked_tools:
            return False

        # Check if on allow list
        return tool_upper in self.allowed_tools

    def is_tool_blocked(self, tool: str) -> bool:
        """Check if a tool is explicitly blocked.

        Args:
            tool: Tool name to check

        Returns:
            True if blocked, False otherwise
        """
        return tool.upper() in self.blocked_tools

    def is_application_allowed(self, app_name: str) -> bool:
        """Check if an application is on the allow list.

        Args:
            app_name: Application name to check

        Returns:
            True if allowed, False otherwise
        """
        # Normalize to lowercase for comparison
        app_lower = app_name.lower().strip()

        # Remove common extensions
        app_lower = re.sub(r"\.(exe|app|dmg)$", "", app_lower)

        return app_lower in self.allowed_apps

    def get_allowed_tools(self) -> List[str]:
        """Get list of all allowed tools.

        Returns:
            List of allowed tool names
        """
        return sorted(list(self.allowed_tools))

    def get_blocked_tools(self) -> List[str]:
        """Get list of all blocked tools.

        Returns:
            List of blocked tool names
        """
        return sorted(list(self.blocked_tools))

    def get_allowed_applications(self) -> List[str]:
        """Get list of all allowed applications.

        Returns:
            List of allowed application names
        """
        return sorted(list(self.allowed_apps))

    def validate_url(self, url: str) -> bool:
        """Validate URL against allow list.

        Args:
            url: URL to validate

        Returns:
            True if valid, False otherwise
        """
        url_rules = self.policies.get("parameter_rules", {}).get("urls", {})

        # Check length
        max_length = url_rules.get("max_length", 2000)
        if len(url) > max_length:
            return False

        # Check scheme
        allowed_schemes = url_rules.get("allowed_schemes", ["http", "https"])
        if not any(url.startswith(f"{scheme}://") for scheme in allowed_schemes):
            return False

        # Check blocked domains
        blocked_domains = url_rules.get("blocked_domains", [])
        url_lower = url.lower()
        for domain in blocked_domains:
            if domain in url_lower:
                return False

        return True

    def validate_file_path(self, path: str) -> bool:
        """Validate file path against allow list.

        Args:
            path: File path to validate

        Returns:
            True if valid, False otherwise
        """
        path_rules = self.policies.get("parameter_rules", {}).get("file_paths", {})

        # Check length
        max_length = path_rules.get("max_length", 260)
        if len(path) > max_length:
            return False

        # Check blocked patterns
        blocked_patterns = path_rules.get("blocked_patterns", [])
        path_lower = path.lower()
        for pattern in blocked_patterns:
            if pattern.lower() in path_lower:
                return False

        # Check allowed extensions
        allowed_extensions = path_rules.get("allowed_extensions", [])
        if allowed_extensions:
            if not any(path.lower().endswith(ext) for ext in allowed_extensions):
                return False

        return True

    def get_policy(self, key: str, default: Any = None) -> Any:
        """Get a policy value by key.

        Args:
            key: Policy key (supports nested keys with dots)
            default: Default value if key not found

        Returns:
            Policy value or default
        """
        keys = key.split(".")
        value = self.policies

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value
