"""Input sanitization to prevent injection attacks."""

import re
from typing import Dict, Any, List, Tuple
from pathlib import Path
import yaml


class SanitizationError(Exception):
    """Raised when input fails sanitization."""

    pass


class InputSanitizer:
    """Sanitize inputs to prevent injection attacks."""

    def __init__(self, config_path: str = "config/policies.yaml"):
        """Initialize input sanitizer.

        Args:
            config_path: Path to policies configuration
        """
        self.config_path = Path(config_path)
        self.policies = self._load_policies()
        self.param_rules = self.policies.get("parameter_rules", {})

    def _load_policies(self) -> Dict[str, Any]:
        """Load policies from YAML file."""
        try:
            if self.config_path.exists():
                with open(self.config_path, "r") as f:
                    return yaml.safe_load(f)

            module_dir = Path(__file__).parent.parent
            config_file = module_dir / self.config_path

            if config_file.exists():
                with open(config_file, "r") as f:
                    return yaml.safe_load(f)

            return {}

        except Exception as e:
            print(f"Warning: Failed to load policies: {e}")
            return {}

    def sanitize_parameters(
        self, tool: str, parameters: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], List[str]]:
        """Sanitize all parameters for a tool.

        Args:
            tool: Tool name
            parameters: Raw parameters

        Returns:
            Tuple of (sanitized_params, warnings)

        Raises:
            SanitizationError: If sanitization fails
        """
        sanitized = {}
        warnings = []

        for key, value in parameters.items():
            try:
                if isinstance(value, str):
                    sanitized_value, param_warnings = self._sanitize_string(key, value)
                    sanitized[key] = sanitized_value
                    warnings.extend(param_warnings)
                elif isinstance(value, (int, float)):
                    sanitized[key] = self._sanitize_number(key, value)
                elif isinstance(value, dict):
                    # Recursively sanitize nested dicts
                    nested_sanitized, nested_warnings = self.sanitize_parameters(tool, value)
                    sanitized[key] = nested_sanitized
                    warnings.extend(nested_warnings)
                elif isinstance(value, list):
                    # Sanitize list items
                    sanitized[key] = [
                        self._sanitize_string(key, item)[0] if isinstance(item, str) else item
                        for item in value
                    ]
                else:
                    sanitized[key] = value

            except SanitizationError:
                raise
            except Exception as e:
                warnings.append(f"Failed to sanitize parameter '{key}': {e}")
                sanitized[key] = value

        return sanitized, warnings

    def _sanitize_string(self, key: str, value: str) -> Tuple[str, List[str]]:
        """Sanitize a string parameter.

        Args:
            key: Parameter name
            value: String value

        Returns:
            Tuple of (sanitized_value, warnings)

        Raises:
            SanitizationError: If value is unsafe
        """
        warnings = []
        sanitized = value

        # Check for SQL injection
        if key.lower() in ["query", "sql", "statement"]:
            sanitized, sql_warnings = self._sanitize_sql(value)
            warnings.extend(sql_warnings)

        # Check for command injection
        elif key.lower() in ["command", "cmd", "script", "shell"]:
            sanitized, cmd_warnings = self._sanitize_command(value)
            warnings.extend(cmd_warnings)

        # Check for path traversal
        elif key.lower() in ["path", "file_path", "directory", "filename"]:
            sanitized, path_warnings = self._sanitize_path(value)
            warnings.extend(path_warnings)

        # Check for URL injection
        elif key.lower() in ["url", "link", "website", "uri"]:
            sanitized, url_warnings = self._sanitize_url(value)
            warnings.extend(url_warnings)

        # General XSS protection
        sanitized = self._sanitize_xss(sanitized)

        return sanitized, warnings

    def _sanitize_sql(self, value: str) -> Tuple[str, List[str]]:
        """Sanitize SQL query.

        Args:
            value: SQL query string

        Returns:
            Tuple of (sanitized_value, warnings)

        Raises:
            SanitizationError: If query contains dangerous patterns
        """
        warnings = []
        rules = self.param_rules.get("database_queries", {})

        # Check length
        max_length = rules.get("max_length", 500)
        if len(value) > max_length:
            raise SanitizationError(f"SQL query exceeds max length ({max_length})")

        # Check for dangerous patterns
        blocked_patterns = rules.get("blocked_patterns", [])
        value_upper = value.upper()

        for pattern in blocked_patterns:
            if pattern.upper() in value_upper:
                raise SanitizationError(f"SQL query contains blocked pattern: {pattern}")

        # Escape single quotes
        sanitized = value.replace("'", "''")

        return sanitized, warnings

    def _sanitize_command(self, value: str) -> Tuple[str, List[str]]:
        """Sanitize system command.

        Args:
            value: Command string

        Returns:
            Tuple of (sanitized_value, warnings)

        Raises:
            SanitizationError: If command contains dangerous patterns
        """
        warnings = []
        rules = self.param_rules.get("system_commands", {})

        # Check length
        max_length = rules.get("max_length", 200)
        if len(value) > max_length:
            raise SanitizationError(f"Command exceeds max length ({max_length})")

        # Check for dangerous patterns
        blocked_patterns = rules.get("blocked_patterns", [])

        for pattern in blocked_patterns:
            if pattern in value:
                raise SanitizationError(f"Command contains blocked pattern: {pattern}")

        return value, warnings

    def _sanitize_path(self, value: str) -> Tuple[str, List[str]]:
        """Sanitize file path.

        Args:
            value: File path

        Returns:
            Tuple of (sanitized_value, warnings)

        Raises:
            SanitizationError: If path contains dangerous patterns
        """
        warnings = []
        rules = self.param_rules.get("file_paths", {})

        # Check length
        max_length = rules.get("max_length", 260)
        if len(value) > max_length:
            raise SanitizationError(f"Path exceeds max length ({max_length})")

        # Check for path traversal
        blocked_patterns = rules.get("blocked_patterns", [])
        value_lower = value.lower()

        for pattern in blocked_patterns:
            if pattern.lower() in value_lower:
                raise SanitizationError(f"Path contains blocked pattern: {pattern}")

        # Normalize path
        try:
            normalized = str(Path(value).resolve())

            # Additional check on normalized path
            normalized_lower = normalized.lower()
            for pattern in blocked_patterns:
                if pattern.lower() in normalized_lower:
                    raise SanitizationError(f"Normalized path contains blocked pattern: {pattern}")

            return normalized, warnings

        except Exception as e:
            warnings.append(f"Failed to normalize path: {e}")
            return value, warnings

    def _sanitize_url(self, value: str) -> Tuple[str, List[str]]:
        """Sanitize URL.

        Args:
            value: URL string

        Returns:
            Tuple of (sanitized_value, warnings)

        Raises:
            SanitizationError: If URL is invalid or dangerous
        """
        warnings = []
        rules = self.param_rules.get("urls", {})

        # Check length
        max_length = rules.get("max_length", 2000)
        if len(value) > max_length:
            raise SanitizationError(f"URL exceeds max length ({max_length})")

        # Check scheme
        allowed_schemes = rules.get("allowed_schemes", ["http", "https"])
        if not any(value.lower().startswith(f"{scheme}://") for scheme in allowed_schemes):
            raise SanitizationError(f"URL scheme not allowed. Allowed: {allowed_schemes}")

        # Check for blocked domains
        blocked_domains = rules.get("blocked_domains", [])
        value_lower = value.lower()

        for domain in blocked_domains:
            if domain in value_lower:
                raise SanitizationError(f"URL contains blocked domain: {domain}")

        return value, warnings

    def _sanitize_xss(self, value: str) -> str:
        """Sanitize against XSS attacks.

        Args:
            value: String value

        Returns:
            Sanitized string
        """
        # Remove <script> tags
        value = re.sub(r"<script[^>]*>.*?</script>", "", value, flags=re.IGNORECASE | re.DOTALL)

        # Remove javascript: protocol
        value = re.sub(r"javascript:", "", value, flags=re.IGNORECASE)

        # Remove on* event handlers
        value = re.sub(r"\bon\w+\s*=", "", value, flags=re.IGNORECASE)

        return value

    def _sanitize_number(self, key: str, value: float) -> float:
        """Sanitize numeric parameter.

        Args:
            key: Parameter name
            value: Numeric value

        Returns:
            Sanitized value

        Raises:
            SanitizationError: If value is invalid
        """
        # Check for reasonable bounds
        if abs(value) > 1e15:
            raise SanitizationError(f"Number too large: {value}")

        # Check for NaN or infinity
        if not isinstance(value, (int, float)) or value != value:  # NaN check
            raise SanitizationError(f"Invalid number: {value}")

        return value

    def detect_pii(self, text: str) -> List[Tuple[str, str]]:
        """Detect PII (Personally Identifiable Information) in text.

        Args:
            text: Text to scan

        Returns:
            List of (pii_type, matched_value) tuples
        """
        pii_found = []
        pii_patterns = self.policies.get("pii_patterns", {})

        for pii_type, config in pii_patterns.items():
            pattern = config.get("pattern")
            if pattern:
                matches = re.findall(pattern, text)
                for match in matches:
                    pii_found.append((pii_type, match))

        return pii_found

    def mask_pii(self, text: str) -> str:
        """Mask PII in text.

        Args:
            text: Text containing PII

        Returns:
            Text with PII masked
        """
        masked = text
        pii_patterns = self.policies.get("pii_patterns", {})

        for pii_type, config in pii_patterns.items():
            pattern = config.get("pattern")
            mask = config.get("mask", "***")

            if pattern:
                masked = re.sub(pattern, mask, masked)

        return masked
