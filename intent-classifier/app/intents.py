"""Intent type definitions for voice agent classification."""

from enum import Enum


class IntentType(str, Enum):
    """Enumeration of all supported intent types for the voice agent.

    Categories:
    - Application Control: Managing apps and programs
    - System Control: OS-level operations
    - Information Retrieval: Queries for data
    - Communication: Messaging and calls
    - Media & Entertainment: Music, video, podcasts
    - Smart Home: IoT device control
    - Navigation: Maps and directions
    - Productivity: Calendar, reminders, notes
    - Shopping: E-commerce operations
    - Utility: Calculations, conversions, etc.
    - Meta: System-level intents
    """

    # Application Control (8)
    OPEN_APP = "open_app"
    CLOSE_APP = "close_app"
    SWITCH_APP = "switch_app"
    MINIMIZE_APP = "minimize_app"
    MAXIMIZE_APP = "maximize_app"
    RESTART_APP = "restart_app"
    INSTALL_APP = "install_app"
    UNINSTALL_APP = "uninstall_app"

    # System Control (12)
    SHUTDOWN = "shutdown"
    RESTART_SYSTEM = "restart_system"
    LOCK_SCREEN = "lock_screen"
    UNLOCK_SCREEN = "unlock_screen"
    INCREASE_VOLUME = "increase_volume"
    DECREASE_VOLUME = "decrease_volume"
    MUTE_VOLUME = "mute_volume"
    UNMUTE_VOLUME = "unmute_volume"
    INCREASE_BRIGHTNESS = "increase_brightness"
    DECREASE_BRIGHTNESS = "decrease_brightness"
    TAKE_SCREENSHOT = "take_screenshot"
    OPEN_SETTINGS = "open_settings"

    # Information Retrieval (10)
    GET_WEATHER = "get_weather"
    GET_NEWS = "get_news"
    GET_TIME = "get_time"
    GET_DATE = "get_date"
    SEARCH_WEB = "search_web"
    SEARCH_FILES = "search_files"
    GET_DEFINITION = "get_definition"
    GET_TRANSLATION = "get_translation"
    GET_FACTS = "get_facts"
    CALCULATE = "calculate"

    # Communication (6)
    SEND_EMAIL = "send_email"
    READ_EMAIL = "read_email"
    MAKE_CALL = "make_call"
    SEND_MESSAGE = "send_message"
    READ_MESSAGE = "read_message"
    CHECK_NOTIFICATIONS = "check_notifications"

    # Media & Entertainment (8)
    PLAY_MUSIC = "play_music"
    PLAY_VIDEO = "play_video"
    PAUSE_MEDIA = "pause_media"
    RESUME_MEDIA = "resume_media"
    NEXT_TRACK = "next_track"
    PREVIOUS_TRACK = "previous_track"
    STOP_MEDIA = "stop_media"
    SHUFFLE_PLAYLIST = "shuffle_playlist"

    # Smart Home (8)
    TURN_ON_LIGHTS = "turn_on_lights"
    TURN_OFF_LIGHTS = "turn_off_lights"
    DIM_LIGHTS = "dim_lights"
    SET_TEMPERATURE = "set_temperature"
    LOCK_DOOR = "lock_door"
    UNLOCK_DOOR = "unlock_door"
    START_VACUUM = "start_vacuum"
    CHECK_SECURITY = "check_security"

    # Navigation (4)
    GET_DIRECTIONS = "get_directions"
    FIND_LOCATION = "find_location"
    FIND_NEARBY = "find_nearby"
    CHECK_TRAFFIC = "check_traffic"

    # Productivity (7)
    CREATE_REMINDER = "create_reminder"
    LIST_REMINDERS = "list_reminders"
    DELETE_REMINDER = "delete_reminder"
    SCHEDULE_MEETING = "schedule_meeting"
    CHECK_CALENDAR = "check_calendar"
    TAKE_NOTE = "take_note"
    READ_NOTE = "read_note"

    # Shopping (5)
    ADD_TO_CART = "add_to_cart"
    CHECK_PRICE = "check_price"
    TRACK_ORDER = "track_order"
    FIND_PRODUCT = "find_product"
    CREATE_SHOPPING_LIST = "create_shopping_list"

    # Utility (5)
    SET_TIMER = "set_timer"
    SET_ALARM = "set_alarm"
    CONVERT_UNITS = "convert_units"
    FLIP_COIN = "flip_coin"
    ROLL_DICE = "roll_dice"

    # Meta/System (5)
    HELP = "help"
    CANCEL = "cancel"
    REPEAT = "repeat"
    UNKNOWN = "unknown"
    REQUIRES_CLARIFICATION = "requires_clarification"


# Intent category mapping for debugging/analysis
INTENT_CATEGORIES = {
    "Application Control": [
        IntentType.OPEN_APP,
        IntentType.CLOSE_APP,
        IntentType.SWITCH_APP,
        IntentType.MINIMIZE_APP,
        IntentType.MAXIMIZE_APP,
        IntentType.RESTART_APP,
        IntentType.INSTALL_APP,
        IntentType.UNINSTALL_APP,
    ],
    "System Control": [
        IntentType.SHUTDOWN,
        IntentType.RESTART_SYSTEM,
        IntentType.LOCK_SCREEN,
        IntentType.UNLOCK_SCREEN,
        IntentType.INCREASE_VOLUME,
        IntentType.DECREASE_VOLUME,
        IntentType.MUTE_VOLUME,
        IntentType.UNMUTE_VOLUME,
        IntentType.INCREASE_BRIGHTNESS,
        IntentType.DECREASE_BRIGHTNESS,
        IntentType.TAKE_SCREENSHOT,
        IntentType.OPEN_SETTINGS,
    ],
    "Information Retrieval": [
        IntentType.GET_WEATHER,
        IntentType.GET_NEWS,
        IntentType.GET_TIME,
        IntentType.GET_DATE,
        IntentType.SEARCH_WEB,
        IntentType.SEARCH_FILES,
        IntentType.GET_DEFINITION,
        IntentType.GET_TRANSLATION,
        IntentType.GET_FACTS,
        IntentType.CALCULATE,
    ],
    "Communication": [
        IntentType.SEND_EMAIL,
        IntentType.READ_EMAIL,
        IntentType.MAKE_CALL,
        IntentType.SEND_MESSAGE,
        IntentType.READ_MESSAGE,
        IntentType.CHECK_NOTIFICATIONS,
    ],
    "Media & Entertainment": [
        IntentType.PLAY_MUSIC,
        IntentType.PLAY_VIDEO,
        IntentType.PAUSE_MEDIA,
        IntentType.RESUME_MEDIA,
        IntentType.NEXT_TRACK,
        IntentType.PREVIOUS_TRACK,
        IntentType.STOP_MEDIA,
        IntentType.SHUFFLE_PLAYLIST,
    ],
    "Smart Home": [
        IntentType.TURN_ON_LIGHTS,
        IntentType.TURN_OFF_LIGHTS,
        IntentType.DIM_LIGHTS,
        IntentType.SET_TEMPERATURE,
        IntentType.LOCK_DOOR,
        IntentType.UNLOCK_DOOR,
        IntentType.START_VACUUM,
        IntentType.CHECK_SECURITY,
    ],
    "Navigation": [
        IntentType.GET_DIRECTIONS,
        IntentType.FIND_LOCATION,
        IntentType.FIND_NEARBY,
        IntentType.CHECK_TRAFFIC,
    ],
    "Productivity": [
        IntentType.CREATE_REMINDER,
        IntentType.LIST_REMINDERS,
        IntentType.DELETE_REMINDER,
        IntentType.SCHEDULE_MEETING,
        IntentType.CHECK_CALENDAR,
        IntentType.TAKE_NOTE,
        IntentType.READ_NOTE,
    ],
    "Shopping": [
        IntentType.ADD_TO_CART,
        IntentType.CHECK_PRICE,
        IntentType.TRACK_ORDER,
        IntentType.FIND_PRODUCT,
        IntentType.CREATE_SHOPPING_LIST,
    ],
    "Utility": [
        IntentType.SET_TIMER,
        IntentType.SET_ALARM,
        IntentType.CONVERT_UNITS,
        IntentType.FLIP_COIN,
        IntentType.ROLL_DICE,
    ],
    "Meta": [
        IntentType.HELP,
        IntentType.CANCEL,
        IntentType.REPEAT,
        IntentType.UNKNOWN,
        IntentType.REQUIRES_CLARIFICATION,
    ],
}


def get_category(intent: IntentType) -> str:
    """Get the category name for a given intent.

    Args:
        intent: The IntentType to categorize

    Returns:
        The category name as a string, or "Unknown" if not found
    """
    for category, intents in INTENT_CATEGORIES.items():
        if intent in intents:
            return category
    return "Unknown"
