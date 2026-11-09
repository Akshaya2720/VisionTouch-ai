"""Action Dispatcher and Execution Manager for VisionTouch AI.

Routes recognized gestures to appropriate hardware automation controllers
based on the active application profile and current AppState.
"""

from typing import Dict, Optional
from app.controllers.keyboard_controller import KeyboardController
from app.controllers.media_controller import MediaController
from app.controllers.mouse_controller import MouseController
from app.controllers.scroll_controller import ScrollController
from app.core.state_manager import AppState, StateManager
from app.database.db_manager import DatabaseManager
from app.gestures.gesture_types import GestureType, RecognizedGesture
from app.utils.logger import setup_logger

logger = setup_logger("ActionManager")


class ActionManager:
    """Dispatches gestures to concrete system controllers based on active profile."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        state_manager: StateManager,
        mouse: MouseController,
        scroller: ScrollController,
        media: MediaController,
        keyboard: KeyboardController,
    ) -> None:
        self.db = db_manager
        self.state = state_manager
        self.mouse = mouse
        self.scroller = scroller
        self.media = media
        self.keyboard = keyboard

        settings = self.db.get_settings()
        self.active_profile: str = settings.active_profile
        self._mappings: Dict[str, str] = self.db.get_mappings(self.active_profile)

        # Safety control: when False, gestures will NEVER touch the physical mouse cursor or clicks,
        # ensuring the laptop touchpad works completely normally without any interference!
        self.enable_mouse_cursor: bool = True

    def set_mouse_control(self, enabled: bool) -> None:
        """Enables or disables touchless mouse cursor movement and clicking."""
        self.enable_mouse_cursor = enabled
        logger.info(f"Mouse cursor automation enabled: {enabled}")
        if not enabled:
            self.mouse.reset()

    def set_profile(self, profile_name: str) -> None:
        """Switches active profile and reloads mapping dictionary."""
        self.active_profile = profile_name
        self._mappings = self.db.get_mappings(profile_name)
        self.db.update_settings(active_profile=profile_name)
        logger.info(f"Switched active profile to: '{profile_name}'")

    def dispatch(self, gesture: RecognizedGesture) -> Optional[str]:
        """Dispatches recognized gesture to controller action.

        Returns:
            Dispatched action string identifier or None if ignored.
        """
        g_name = gesture.gesture.name

        # Always process Emergency Pause (Closed Fist) regardless of state
        if gesture.gesture == GestureType.CLOSED_FIST:
            self.state.set_state(AppState.PAUSED)
            self.mouse.reset()
            return "emergency_pause"

        # Always process Open Palm (Toggle Standby/Active)
        if gesture.gesture == GestureType.OPEN_PALM:
            new_state = self.state.toggle_standby()
            self.mouse.reset()
            return f"toggle_standby_{new_state.name.lower()}"

        # If system is not in ACTIVE state, ignore all other actions
        if self.state.state != AppState.ACTIVE:
            return None

        # Look up mapped action for this profile
        action_name = self._mappings.get(g_name)
        if not action_name:
            return None

        # Touchpad safety check: if mouse automation is disabled, ignore cursor/clicks
        if not self.enable_mouse_cursor and action_name in (
            "mouse_move", "left_click", "right_click", "double_click"
        ):
            return None

        # Execute concrete controller actions
        if action_name == "mouse_move" and gesture.cursor_position:
            self.mouse.move_to(gesture.cursor_position[0], gesture.cursor_position[1])

        elif action_name == "left_click":
            self.mouse.left_click()

        elif action_name == "right_click":
            self.mouse.right_click()

        elif action_name == "double_click":
            self.mouse.double_click()

        elif action_name == "scroll_up":
            self.scroller.scroll(gesture.scroll_delta if gesture.scroll_delta != 0 else 3.0)

        elif action_name == "scroll_down":
            self.scroller.scroll(gesture.scroll_delta if gesture.scroll_delta != 0 else -3.0)

        elif action_name == "play_pause":
            self.media.play_pause()

        elif action_name == "next_track" or action_name == "next_video":
            self.media.next_track()

        elif action_name == "previous_track" or action_name == "previous_video":
            self.media.previous_track()

        elif action_name == "volume_up":
            self.media.volume_up()

        elif action_name == "volume_down":
            self.media.volume_down()

        elif action_name == "mute":
            self.media.mute()

        elif action_name == "next_tab":
            self.keyboard.next_tab()

        elif action_name == "previous_tab":
            self.keyboard.previous_tab()

        elif action_name == "next_slide" or action_name == "next_post":
            self.keyboard.press_key("right")

        elif action_name == "previous_slide" or action_name == "previous_post":
            self.keyboard.press_key("left")

        return action_name

