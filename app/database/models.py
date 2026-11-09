"""Database Models and Schema Definitions for VisionTouch AI."""

from dataclasses import asdict, dataclass
from typing import Any, Dict


@dataclass
class UserSettings:
    """User preferences and sensitivity configuration."""
    id: int = 1
    cursor_sensitivity: float = 1.0
    scroll_sensitivity: float = 1.0
    margin_x: float = 0.15
    margin_y: float = 0.20
    active_profile: str = "Default"
    camera_index: int = 0
    camera_permission_granted: bool = True
    dark_theme: bool = True


@dataclass
class GestureMapping:
    """Represents a single gesture-to-action binding within an application profile."""
    id: int
    profile_name: str
    gesture_name: str
    action_name: str
    is_enabled: bool = True
    custom_param: str = ""


# Default Profile Mappings seeded upon database initialization
DEFAULT_PROFILES = {
    "Default": {
        "CURSOR_MOVE": "mouse_move",
        "LEFT_CLICK_PINCH": "left_click",
        "RIGHT_CLICK_PINCH": "right_click",
        "SCROLL_UP": "scroll_up",
        "SCROLL_DOWN": "scroll_down",
        "CLOSED_FIST": "emergency_pause",
        "OPEN_PALM": "toggle_mode",
        "SWIPE_LEFT": "previous_tab",
        "SWIPE_RIGHT": "next_tab",
        "ZOOM_IN": "zoom_in",
        "ZOOM_OUT": "zoom_out",
    },
    "YouTube": {
        "CURSOR_MOVE": "mouse_move",
        "LEFT_CLICK_PINCH": "left_click",
        "RIGHT_CLICK_PINCH": "right_click",
        "SCROLL_UP": "volume_up",
        "SCROLL_DOWN": "volume_down",
        "CLOSED_FIST": "emergency_pause",
        "OPEN_PALM": "play_pause",
        "SWIPE_LEFT": "previous_video",
        "SWIPE_RIGHT": "next_video",
    },
    "Instagram": {
        "CURSOR_MOVE": "mouse_move",
        "LEFT_CLICK_PINCH": "double_click",  # Quick like!
        "RIGHT_CLICK_PINCH": "right_click",
        "SCROLL_UP": "scroll_up",
        "SCROLL_DOWN": "scroll_down",
        "CLOSED_FIST": "emergency_pause",
        "OPEN_PALM": "play_pause",
        "SWIPE_LEFT": "previous_post",
        "SWIPE_RIGHT": "next_post",
    },
    "PowerPoint": {
        "CURSOR_MOVE": "mouse_move",
        "LEFT_CLICK_PINCH": "left_click",
        "RIGHT_CLICK_PINCH": "right_click",
        "SCROLL_UP": "previous_slide",
        "SCROLL_DOWN": "next_slide",
        "CLOSED_FIST": "emergency_pause",
        "OPEN_PALM": "toggle_mode",
        "SWIPE_LEFT": "previous_slide",
        "SWIPE_RIGHT": "next_slide",
    },
    "VLC": {
        "CURSOR_MOVE": "mouse_move",
        "LEFT_CLICK_PINCH": "play_pause",
        "RIGHT_CLICK_PINCH": "mute",
        "SCROLL_UP": "volume_up",
        "SCROLL_DOWN": "volume_down",
        "CLOSED_FIST": "emergency_pause",
        "OPEN_PALM": "play_pause",
        "SWIPE_LEFT": "previous_track",
        "SWIPE_RIGHT": "next_track",
    },
}
