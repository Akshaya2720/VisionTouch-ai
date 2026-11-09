"""Enumerations and data structures for gestures recognized by VisionTouch AI."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Tuple


class GestureType(Enum):
    """Categorical enumeration of all supported hand gestures."""
    NONE = auto()
    CURSOR_MOVE = auto()          # Index finger extended, others curled
    LEFT_CLICK_PINCH = auto()     # Thumb and Index tips pinched together
    RIGHT_CLICK_PINCH = auto()    # Thumb and Middle tips pinched together
    SCROLL_MODE = auto()          # Index and Middle fingers extended together
    SCROLL_UP = auto()            # Index + Middle extended with upward movement
    SCROLL_DOWN = auto()          # Index + Middle extended with downward movement
    CLOSED_FIST = auto()          # All fingers curled (Emergency Pause / Safe Mode)
    OPEN_PALM = auto()            # All 5 fingers extended (Mode Toggle / Standby)
    SWIPE_LEFT = auto()           # Rapid lateral leftward hand motion
    SWIPE_RIGHT = auto()          # Rapid lateral rightward hand motion
    ZOOM_IN = auto()              # Two hands moving apart while pinching
    ZOOM_OUT = auto()             # Two hands moving closer while pinching


@dataclass
class RecognizedGesture:
    """Contains classification output and spatial metadata for a detected gesture."""
    gesture: GestureType
    confidence: float
    hand_id: int
    handedness: str
    cursor_position: Optional[Tuple[float, float]] = None  # Normalized (x, y)
    scroll_delta: float = 0.0                              # Vertical displacement
    zoom_scale: float = 1.0                                # Distance ratio for zoom
