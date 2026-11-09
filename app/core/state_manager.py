"""Application State Machine for VisionTouch AI."""

from enum import Enum, auto
from typing import Callable, List


class AppState(Enum):
    """Operational states of VisionTouch AI."""
    ACTIVE = auto()   # Full touchless automation running
    STANDBY = auto()  # Camera running, but mouse/keyboard actions paused
    PAUSED = auto()   # Emergency Freeze (Closed Fist triggered)


class StateManager:
    """Thread-safe state manager for application control flow."""

    def __init__(self, initial_state: AppState = AppState.ACTIVE) -> None:
        self._state = initial_state
        self._listeners: List[Callable[[AppState], None]] = []

    @property
    def state(self) -> AppState:
        return self._state

    def set_state(self, new_state: AppState) -> None:
        if self._state != new_state:
            self._state = new_state
            for callback in self._listeners:
                callback(new_state)

    def toggle_standby(self) -> AppState:
        """Toggles between ACTIVE and STANDBY mode."""
        new_state = AppState.STANDBY if self._state == AppState.ACTIVE else AppState.ACTIVE
        self.set_state(new_state)
        return new_state

    def add_listener(self, callback: Callable[[AppState], None]) -> None:
        self._listeners.append(callback)
