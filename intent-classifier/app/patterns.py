"""Regex patterns for intent matching."""

import re
from typing import List, Dict, Optional
from .intents import IntentType


class IntentPattern:
    """A pattern for matching an intent with regex."""

    def __init__(self, intent: IntentType, patterns: List[str], priority: int = 0):
        """Initialize an intent pattern.

        Args:
            intent: The IntentType this pattern matches
            patterns: List of regex patterns (will be compiled with re.IGNORECASE)
            priority: Priority level (higher = checked first). Default 0.
        """
        self.intent = intent
        self.patterns = [re.compile(p, re.IGNORECASE) for p in patterns]
        self.priority = priority

    def match(self, text: str) -> Optional[re.Match]:
        """Check if any pattern matches the text.

        Args:
            text: Input text to match against

        Returns:
            Match object if any pattern matches, None otherwise
        """
        for pattern in self.patterns:
            match = pattern.search(text)
            if match:
                return match
        return None


# Application Control Patterns
APP_CONTROL_PATTERNS = [
    IntentPattern(
        IntentType.OPEN_APP,
        [
            r"\b(open|launch|start|run)\s+(\w+)",
            r"\b(open|launch|start|run)\s+(the\s+)?(\w+\s+)?(app|application|program)",
        ],
        priority=1,
    ),
    IntentPattern(
        IntentType.CLOSE_APP,
        [
            r"\b(close|quit|exit|kill|stop)\s+(\w+)",
            r"\b(close|quit|exit|kill|stop)\s+(the\s+)?(\w+\s+)?(app|application|program)",
        ],
        priority=1,
    ),
    IntentPattern(
        IntentType.SWITCH_APP,
        [
            r"\b(switch|change)\s+to\s+(\w+)",
            r"\balt\s+tab",
        ],
    ),
    IntentPattern(
        IntentType.MINIMIZE_APP,
        [
            r"\bminimize\s+(the\s+)?(\w+\s+)?(window|app)?",
        ],
    ),
    IntentPattern(
        IntentType.MAXIMIZE_APP,
        [
            r"\bmaximize\s+(the\s+)?(\w+\s+)?(window|app)?",
            r"\bfull\s*screen",
        ],
    ),
]

# System Control Patterns
SYSTEM_CONTROL_PATTERNS = [
    IntentPattern(
        IntentType.SHUTDOWN,
        [
            r"\b(shut\s*down|power\s+off|turn\s+off)\s+(the\s+)?(computer|pc|system)?",
        ],
        priority=2,  # High priority for safety
    ),
    IntentPattern(
        IntentType.RESTART_SYSTEM,
        [
            r"\b(restart|reboot)\s+(the\s+)?(computer|pc|system)?",
        ],
        priority=2,
    ),
    IntentPattern(
        IntentType.LOCK_SCREEN,
        [
            r"\block\s+(the\s+)?(screen|computer|pc)",
        ],
        priority=1,
    ),
    IntentPattern(
        IntentType.INCREASE_VOLUME,
        [
            r"\b(increase|raise|turn\s+up|volume\s+up)\s+(the\s+)?volume",
            r"\blouder",
        ],
    ),
    IntentPattern(
        IntentType.DECREASE_VOLUME,
        [
            r"\b(decrease|lower|turn\s+down|volume\s+down)\s+(the\s+)?volume",
            r"\bquieter",
        ],
    ),
    IntentPattern(
        IntentType.MUTE_VOLUME,
        [
            r"\bmute(\s+the\s+volume)?",
            r"\bsilence",
        ],
    ),
    IntentPattern(
        IntentType.UNMUTE_VOLUME,
        [
            r"\bunmute(\s+the\s+volume)?",
        ],
    ),
    IntentPattern(
        IntentType.INCREASE_BRIGHTNESS,
        [
            r"\b(increase|raise|turn\s+up)\s+(the\s+)?brightness",
            r"\bbrighter",
        ],
    ),
    IntentPattern(
        IntentType.DECREASE_BRIGHTNESS,
        [
            r"\b(decrease|lower|turn\s+down)\s+(the\s+)?brightness",
            r"\bdimmer",
        ],
    ),
    IntentPattern(
        IntentType.TAKE_SCREENSHOT,
        [
            r"\btake\s+(a\s+)?screenshot",
            r"\bscreen\s*shot",
            r"\bprint\s+screen",
        ],
    ),
    IntentPattern(
        IntentType.OPEN_SETTINGS,
        [
            r"\bopen\s+(the\s+)?settings",
            r"\bsettings",
        ],
    ),
]

# Information Retrieval Patterns
INFO_PATTERNS = [
    IntentPattern(
        IntentType.GET_WEATHER,
        [
            r"\b(what\'?s|how\'?s)\s+the\s+weather",
            r"\bweather\s+(in|at|for)",
            r"\btemperature\s+(in|at|for)",
        ],
    ),
    IntentPattern(
        IntentType.GET_NEWS,
        [
            r"\b(what\'?s|tell\s+me)\s+(the\s+)?(latest\s+)?news",
            r"\bnews\s+(about|on|for)",
        ],
    ),
    IntentPattern(
        IntentType.GET_TIME,
        [
            r"\b(what\'?s|what\s+is)\s+(the\s+)?(current\s+)?time",
            r"\bwhat\s+time\s+is\s+it",
        ],
    ),
    IntentPattern(
        IntentType.GET_DATE,
        [
            r"\b(what\'?s|what\s+is)\s+(the\s+)?(current\s+)?date",
            r"\bwhat\s+day\s+is\s+it",
            r"\btoday\'?s\s+date",
        ],
    ),
    IntentPattern(
        IntentType.SEARCH_WEB,
        [
            r"\b(search|google|look\s+up)\s+(for\s+)?(.+)",
            r"\bfind\s+(.+)\s+(on\s+the\s+)?(web|internet)",
        ],
        priority=0,  # Lower priority - very broad
    ),
    IntentPattern(
        IntentType.SEARCH_FILES,
        [
            r"\b(search|find|locate)\s+(for\s+)?(files?|documents?)\s+(.+)",
            r"\b(where\s+is|find)\s+(my\s+)?(.+)\s+file",
        ],
    ),
    IntentPattern(
        IntentType.GET_DEFINITION,
        [
            r"\b(what\'?s|what\s+is|define)\s+(the\s+)?(definition\s+of\s+)?(\w+)",
            r"\bdefine\s+(\w+)",
        ],
    ),
    IntentPattern(
        IntentType.GET_TRANSLATION,
        [
            r"\b(translate|how\s+do\s+you\s+say)\s+(.+)\s+(to|in)\s+(\w+)",
        ],
    ),
    IntentPattern(
        IntentType.CALCULATE,
        [
            r"\b(calculate|compute|what\'?s)\s+(.+)",
            r"\bhow\s+much\s+is\s+(.+)",
            r"\d+\s*[\+\-\*\/×÷]\s*\d+",  # Math expressions
        ],
    ),
]

# Communication Patterns
COMMUNICATION_PATTERNS = [
    IntentPattern(
        IntentType.SEND_EMAIL,
        [
            r"\bsend\s+(an\s+)?email\s+(to\s+)?(.+)",
            r"\bemail\s+(.+)",
        ],
    ),
    IntentPattern(
        IntentType.READ_EMAIL,
        [
            r"\bread\s+(my\s+)?(emails?|inbox)",
            r"\bcheck\s+(my\s+)?email",
        ],
    ),
    IntentPattern(
        IntentType.MAKE_CALL,
        [
            r"\bcall\s+(.+)",
            r"\b(make\s+a\s+)?phone\s+call\s+(to\s+)?(.+)",
        ],
    ),
    IntentPattern(
        IntentType.SEND_MESSAGE,
        [
            r"\b(send|text)\s+(a\s+)?message\s+(to\s+)?(.+)",
            r"\b(send|text)\s+(.+)\s+to\s+(.+)",
        ],
    ),
    IntentPattern(
        IntentType.READ_MESSAGE,
        [
            r"\bread\s+(my\s+)?messages?",
            r"\bcheck\s+(my\s+)?messages?",
        ],
    ),
]

# Media & Entertainment Patterns
MEDIA_PATTERNS = [
    IntentPattern(
        IntentType.PLAY_MUSIC,
        [
            r"\bplay\s+(some\s+)?music",
            r"\bplay\s+(.+)\s+by\s+(.+)",  # "play Shape of You by Ed Sheeran"
            r"\bplay\s+(.+)",  # Generic play (lower priority)
        ],
    ),
    IntentPattern(
        IntentType.PLAY_VIDEO,
        [
            r"\bplay\s+(the\s+)?video\s+(.+)",
            r"\bwatch\s+(.+)",
        ],
    ),
    IntentPattern(
        IntentType.PAUSE_MEDIA,
        [
            r"\bpause(\s+the\s+)?(music|video|playback)?",
        ],
    ),
    IntentPattern(
        IntentType.RESUME_MEDIA,
        [
            r"\bresume(\s+the\s+)?(music|video|playback)?",
            r"\bcontinue\s+playing",
        ],
    ),
    IntentPattern(
        IntentType.NEXT_TRACK,
        [
            r"\b(next|skip)\s+(track|song)",
            r"\bskip(\s+this)?",
        ],
    ),
    IntentPattern(
        IntentType.PREVIOUS_TRACK,
        [
            r"\b(previous|last|go\s+back)\s+(track|song)",
        ],
    ),
    IntentPattern(
        IntentType.STOP_MEDIA,
        [
            r"\bstop\s+(the\s+)?(music|video|playback)",
        ],
    ),
]

# Smart Home Patterns
SMART_HOME_PATTERNS = [
    IntentPattern(
        IntentType.TURN_ON_LIGHTS,
        [
            r"\bturn\s+on\s+(the\s+)?lights?",
            r"\blights?\s+on",
        ],
    ),
    IntentPattern(
        IntentType.TURN_OFF_LIGHTS,
        [
            r"\bturn\s+off\s+(the\s+)?lights?",
            r"\blights?\s+off",
        ],
    ),
    IntentPattern(
        IntentType.DIM_LIGHTS,
        [
            r"\bdim\s+(the\s+)?lights?",
            r"\b(decrease|lower)\s+light(s|ing)?",
        ],
    ),
    IntentPattern(
        IntentType.SET_TEMPERATURE,
        [
            r"\bset\s+(the\s+)?temperature\s+to\s+(\d+)",
            r"\bmake\s+it\s+(warmer|cooler|hotter|colder)",
        ],
    ),
    IntentPattern(
        IntentType.LOCK_DOOR,
        [
            r"\block\s+(the\s+)?(front\s+|back\s+)?door",
        ],
    ),
    IntentPattern(
        IntentType.UNLOCK_DOOR,
        [
            r"\bunlock\s+(the\s+)?(front\s+|back\s+)?door",
        ],
    ),
]

# Navigation Patterns
NAVIGATION_PATTERNS = [
    IntentPattern(
        IntentType.GET_DIRECTIONS,
        [
            r"\b(get|give\s+me)\s+directions\s+to\s+(.+)",
            r"\bhow\s+do\s+I\s+get\s+to\s+(.+)",
            r"\bnavigate\s+to\s+(.+)",
        ],
    ),
    IntentPattern(
        IntentType.FIND_LOCATION,
        [
            r"\b(where\s+is|find|locate)\s+(.+)",
        ],
    ),
    IntentPattern(
        IntentType.FIND_NEARBY,
        [
            r"\bfind\s+(nearby|near\s+me)\s+(.+)",
            r"\b(.+)\s+near\s+me",
        ],
    ),
]

# Productivity Patterns
PRODUCTIVITY_PATTERNS = [
    IntentPattern(
        IntentType.CREATE_REMINDER,
        [
            r"\b(remind|set\s+a\s+reminder)\s+(me\s+)?(to\s+)?(.+)",
        ],
    ),
    IntentPattern(
        IntentType.LIST_REMINDERS,
        [
            r"\b(list|show|what\s+are)\s+(my\s+)?reminders?",
        ],
    ),
    IntentPattern(
        IntentType.SCHEDULE_MEETING,
        [
            r"\bschedule\s+(a\s+)?meeting\s+(.+)",
            r"\bset\s+up\s+(a\s+)?meeting\s+(.+)",
        ],
    ),
    IntentPattern(
        IntentType.CHECK_CALENDAR,
        [
            r"\b(check|show|what\'?s\s+on)\s+(my\s+)?calendar",
            r"\bwhat\'?s\s+(my\s+)?schedule",
        ],
    ),
    IntentPattern(
        IntentType.TAKE_NOTE,
        [
            r"\b(take|make|create)\s+(a\s+)?note\s+(.+)",
            r"\bwrite\s+down\s+(.+)",
        ],
    ),
]

# Utility Patterns
UTILITY_PATTERNS = [
    IntentPattern(
        IntentType.SET_TIMER,
        [
            r"\bset\s+(a\s+)?timer\s+for\s+(\d+)\s+(minutes?|seconds?|hours?)",
            r"\btimer\s+(\d+)\s+(minutes?|seconds?|hours?)",
        ],
    ),
    IntentPattern(
        IntentType.SET_ALARM,
        [
            r"\bset\s+(an\s+)?alarm\s+for\s+(.+)",
            r"\balarm\s+(at\s+)?(.+)",
        ],
    ),
    IntentPattern(
        IntentType.CONVERT_UNITS,
        [
            r"\bconvert\s+(\d+)\s+(\w+)\s+to\s+(\w+)",
            r"\bhow\s+many\s+(\w+)\s+in\s+(\d+)\s+(\w+)",
        ],
    ),
]

# Meta Patterns
META_PATTERNS = [
    IntentPattern(
        IntentType.HELP,
        [
            r"\bhelp",
            r"\bwhat\s+can\s+you\s+do",
            r"\bhow\s+do\s+I\s+use",
        ],
        priority=1,
    ),
    IntentPattern(
        IntentType.CANCEL,
        [
            r"\bcancel",
            r"\bnever\s+mind",
            r"\bstop",
        ],
        priority=2,
    ),
    IntentPattern(
        IntentType.REPEAT,
        [
            r"\brepeat",
            r"\bsay\s+that\s+again",
            r"\bwhat\s+did\s+you\s+say",
        ],
        priority=1,
    ),
]


# Combined pattern list (sorted by priority)
ALL_PATTERNS: List[IntentPattern] = sorted(
    APP_CONTROL_PATTERNS
    + SYSTEM_CONTROL_PATTERNS
    + INFO_PATTERNS
    + COMMUNICATION_PATTERNS
    + MEDIA_PATTERNS
    + SMART_HOME_PATTERNS
    + NAVIGATION_PATTERNS
    + PRODUCTIVITY_PATTERNS
    + UTILITY_PATTERNS
    + META_PATTERNS,
    key=lambda p: p.priority,
    reverse=True,  # Higher priority first
)


def match_pattern(text: str) -> Optional[Dict]:
    """Attempt to match text against all patterns.

    Args:
        text: Input text to classify

    Returns:
        Dict with 'intent' and 'match' if found, None otherwise
    """
    for pattern in ALL_PATTERNS:
        match = pattern.match(text)
        if match:
            return {"intent": pattern.intent, "match": match}
    return None
