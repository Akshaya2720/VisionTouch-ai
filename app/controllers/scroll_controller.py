"""Touchless Scrolling Controller for VisionTouch AI.

Converts vertical hand landmark displacements into smooth, momentum-aware
mouse wheel scroll events for web pages, Instagram feeds, and YouTube.
"""

import ctypes
import platform
import time
from typing import Optional
import pyautogui

from app.utils.logger import setup_logger

logger = setup_logger("ScrollController")

# Windows API constants for mouse wheel
MOUSEEVENTF_WHEEL = 0x0800
WHEEL_DELTA = 120  # Standard Windows mouse wheel detent increment


class ScrollController:
    """Manages touchless scrolling with deadzone filtering, momentum, and speed throttling."""

    def __init__(
        self,
        base_speed: float = 12.0,
        acceleration: float = 1.8,
        cooldown: float = 0.04,  # Cap scroll rate to ~25 events/sec
    ) -> None:
        """Initializes the scroll controller.

        Args:
            base_speed: Base scroll step multiplier.
            acceleration: Non-linear speed multiplier for faster hand movements.
            cooldown: Minimum interval between scroll events (in seconds).
        """
        self.base_speed = base_speed
        self.acceleration = acceleration
        self.cooldown = cooldown

        self._last_scroll_time: float = 0.0
        self._is_windows = platform.system() == "Windows"
        self._user32 = ctypes.windll.user32 if self._is_windows else None

    def scroll(self, scroll_delta: float) -> bool:
        """Executes a vertical scroll event based on displacement delta.

        Args:
            scroll_delta: Signed vertical displacement.
                          Positive = Scroll Up, Negative = Scroll Down.

        Returns:
            True if scroll event was dispatched, False if throttled.
        """
        now = time.perf_counter()
        if (now - self._last_scroll_time) < self.cooldown:
            return False

        if abs(scroll_delta) < 1e-4:
            return False

        # Apply non-linear power curve for acceleration:
        # Small finger adjustments produce gentle reading scroll;
        # Fast hand motions produce rapid page traversal.
        magnitude = abs(scroll_delta)
        direction = 1 if scroll_delta > 0 else -1

        scaled_steps = int(
            direction * (self.base_speed * (magnitude ** self.acceleration))
        )
        if scaled_steps == 0:
            scaled_steps = direction * 1

        if self._is_windows and self._user32:
            # On Windows, mouse_event expects WHEEL_DELTA multiples
            # Note: positive WHEEL_DELTA scrolls forward (up), negative scrolls back (down)
            native_delta = int(scaled_steps * (WHEEL_DELTA // 4))
            self._user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, native_delta, 0)
        else:
            pyautogui.scroll(scaled_steps)

        self._last_scroll_time = now
        return True

    def scroll_up(self, amount: int = 3) -> bool:
        """Dispatches an explicit discrete upward scroll event."""
        return self.scroll(float(amount))

    def scroll_down(self, amount: int = 3) -> bool:
        """Dispatches an explicit discrete downward scroll event."""
        return self.scroll(float(-amount))

