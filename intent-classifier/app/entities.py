"""Entity extraction from user utterances."""

import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dateutil import parser as date_parser


class EntityExtractor:
    """Extract structured entities from text."""

    # Common patterns
    EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
    PHONE_PATTERN = re.compile(r"\b(\+?1[-.]?)?\(?\d{3}\)?[-.]?\d{3}[-.]?\d{4}\b")
    NUMBER_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\b")
    URL_PATTERN = re.compile(
        r"https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b"
        r"(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)"
    )

    # Time-related patterns
    TIME_PATTERNS = {
        "relative_time": re.compile(
            r"\b(in|after)\s+(\d+)\s+(second|minute|hour|day|week|month|year)s?\b", re.IGNORECASE
        ),
        "clock_time": re.compile(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm|AM|PM)?\b"),
        "relative_day": re.compile(r"\b(today|tomorrow|yesterday|tonight)\b", re.IGNORECASE),
        "day_of_week": re.compile(
            r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.IGNORECASE
        ),
    }

    # Unit patterns for conversion
    UNIT_PATTERN = re.compile(
        r"\b(\d+(?:\.\d+)?)\s*(km|m|cm|mm|mile|yard|foot|feet|inch|"
        r"kg|g|mg|lb|oz|"
        r"l|ml|gal|cup|"
        r"celsius|fahrenheit|kelvin|"
        r"second|minute|hour|day|week|month|year)\b",
        re.IGNORECASE,
    )

    def extract(self, text: str, intent: Optional[str] = None) -> Dict[str, Any]:
        """Extract all entities from text.

        Args:
            text: Input text
            intent: Optional intent to guide extraction

        Returns:
            Dictionary of extracted entities
        """
        entities = {}

        # Always extract basic entities
        entities.update(self._extract_contacts(text))
        entities.update(self._extract_numbers(text))
        entities.update(self._extract_urls(text))

        # Intent-specific extraction
        if intent:
            if (
                "time" in intent.lower()
                or "reminder" in intent.lower()
                or "alarm" in intent.lower()
            ):
                entities.update(self._extract_temporal(text))

            if "convert" in intent.lower():
                entities.update(self._extract_units(text))

            if "app" in intent.lower():
                entities.update(self._extract_app_name(text))

            if "music" in intent.lower() or "video" in intent.lower():
                entities.update(self._extract_media_info(text))

            if "temperature" in intent.lower():
                entities.update(self._extract_temperature(text))

        return entities

    def _extract_contacts(self, text: str) -> Dict[str, Any]:
        """Extract email addresses and phone numbers."""
        entities = {}

        emails = self.EMAIL_PATTERN.findall(text)
        if emails:
            entities["emails"] = emails

        phones = self.PHONE_PATTERN.findall(text)
        if phones:
            entities["phone_numbers"] = phones

        return entities

    def _extract_numbers(self, text: str) -> Dict[str, Any]:
        """Extract numeric values."""
        entities = {}

        numbers = [float(n) for n in self.NUMBER_PATTERN.findall(text)]
        if numbers:
            entities["numbers"] = numbers

        return entities

    def _extract_urls(self, text: str) -> Dict[str, Any]:
        """Extract URLs."""
        entities = {}

        urls = self.URL_PATTERN.findall(text)
        if urls:
            entities["urls"] = urls

        return entities

    def _extract_temporal(self, text: str) -> Dict[str, Any]:
        """Extract time and date information."""
        entities = {}

        # Relative time (in 5 minutes, after 2 hours)
        relative_match = self.TIME_PATTERNS["relative_time"].search(text)
        if relative_match:
            _, amount, unit = relative_match.groups()
            amount = int(amount)

            # Calculate absolute time
            unit_map = {
                "second": timedelta(seconds=amount),
                "minute": timedelta(minutes=amount),
                "hour": timedelta(hours=amount),
                "day": timedelta(days=amount),
                "week": timedelta(weeks=amount),
                "month": timedelta(days=amount * 30),  # Approximate
                "year": timedelta(days=amount * 365),  # Approximate
            }

            delta = unit_map.get(unit, timedelta())
            target_time = datetime.now() + delta

            entities["relative_time"] = {
                "amount": amount,
                "unit": unit,
                "target_datetime": target_time.isoformat(),
            }

        # Clock time (3pm, 14:30)
        clock_match = self.TIME_PATTERNS["clock_time"].search(text)
        if clock_match:
            hour, minute, meridiem = clock_match.groups()
            hour = int(hour)
            minute = int(minute) if minute else 0

            if meridiem:
                if meridiem.lower() == "pm" and hour < 12:
                    hour += 12
                elif meridiem.lower() == "am" and hour == 12:
                    hour = 0

            entities["clock_time"] = {
                "hour": hour,
                "minute": minute,
                "meridiem": meridiem,
            }

        # Relative day
        relative_day_match = self.TIME_PATTERNS["relative_day"].search(text)
        if relative_day_match:
            day = relative_day_match.group(1).lower()
            entities["relative_day"] = day

            # Calculate date
            today = datetime.now()
            if day == "today" or day == "tonight":
                target_date = today
            elif day == "tomorrow":
                target_date = today + timedelta(days=1)
            elif day == "yesterday":
                target_date = today - timedelta(days=1)
            else:
                target_date = today

            entities["target_date"] = target_date.date().isoformat()

        # Day of week
        dow_match = self.TIME_PATTERNS["day_of_week"].search(text)
        if dow_match:
            entities["day_of_week"] = dow_match.group(1).lower()

        # Try parsing with dateutil (handles complex formats)
        try:
            parsed_date = date_parser.parse(text, fuzzy=True)
            entities["parsed_datetime"] = parsed_date.isoformat()
        except (ValueError, OverflowError):
            pass

        return entities

    def _extract_units(self, text: str) -> Dict[str, Any]:
        """Extract units and measurements."""
        entities = {}

        matches = self.UNIT_PATTERN.findall(text)
        if matches:
            measurements = [
                {"value": float(value), "unit": unit.lower()} for value, unit in matches
            ]
            entities["measurements"] = measurements

        return entities

    def _extract_app_name(self, text: str) -> Dict[str, Any]:
        """Extract application name from text."""
        entities = {}

        # Common patterns for app names
        patterns = [
            r"\b(open|launch|start|close|quit)\s+(\w+(?:\s+\w+)?)",
            r"\bapp(?:lication)?\s+(?:called\s+)?(\w+(?:\s+\w+)?)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Get the last group (app name)
                app_name = match.group(match.lastindex)
                entities["app_name"] = app_name
                break

        return entities

    def _extract_media_info(self, text: str) -> Dict[str, Any]:
        """Extract media-related information (song, artist, etc.)."""
        entities = {}

        # "play X by Y" pattern
        by_pattern = re.search(r"play\s+(.+?)\s+by\s+(.+)", text, re.IGNORECASE)
        if by_pattern:
            entities["media_title"] = by_pattern.group(1).strip()
            entities["artist"] = by_pattern.group(2).strip()
        else:
            # Generic "play X" pattern
            play_pattern = re.search(r"play\s+(.+)", text, re.IGNORECASE)
            if play_pattern:
                entities["media_title"] = play_pattern.group(1).strip()

        return entities

    def _extract_temperature(self, text: str) -> Dict[str, Any]:
        """Extract temperature values."""
        entities = {}

        # Temperature with unit
        temp_pattern = re.search(
            r"(\d+)\s*(degree[s]?)?\s*(celsius|fahrenheit|c|f)\b", text, re.IGNORECASE
        )

        if temp_pattern:
            value = int(temp_pattern.group(1))
            unit = temp_pattern.group(3).lower()

            # Normalize unit
            if unit in ("c", "celsius"):
                unit = "celsius"
            elif unit in ("f", "fahrenheit"):
                unit = "fahrenheit"

            entities["temperature"] = {
                "value": value,
                "unit": unit,
            }
        else:
            # Just a number (assume context from intent)
            num_match = re.search(r"\b(\d+)\b", text)
            if num_match:
                entities["temperature"] = {
                    "value": int(num_match.group(1)),
                    "unit": "unknown",  # Context-dependent
                }

        return entities
