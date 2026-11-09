"""Virtual Mouse Controller Subsystem for VisionTouch AI.

Converts gesture events and normalized coordinates into low-latency OS mouse events
including cursor movement, clicks, double-clicks, and drag-and-drop operations.
"""

import ctypes
import platform
import time
from typing import Optional, Tuple
import pyautogui

from app.utils.coordinate_mapper import CoordinateMapper
from app.utils.logger import setup_logger
from app.utils.smoothing import AdaptiveTremorFilter

logger = setup_logger("MouseController")

# Optimization: PyAutoGUI defaults to a 0.1-second sleep after EVERY mouse call.
# In a real-time 30-60 FPS CV loop, this 100ms pause destroys performance.
pyautogui.PAUSE = 0.0
pyautogui.FAILSAFE = False  # Avoid crashing when cursor touches (0, 0)


# Windows native user32 mouse event flags for direct high-speed hardware input
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_ABSOLUTE = 0x8000


class MouseController:
    """Manages touchless mouse interaction with adaptive smoothing and debouncing."""

    def __init__(
        self,
        mapper: Optional[CoordinateMapper] = None,
        smoother: Optional[AdaptiveTremorFilter] = None,
        click_cooldown: float = 0.35,
    ) -> None:
        self.mapper = mapper or CoordinateMapper()
        self.smoother = smoother or AdaptiveTremorFilter()
        self.click_cooldown = click_cooldown

        self._is_dragging: bool = False
        self._last_click_time: float = 0.0
        self._last_left_click_time: float = 0.0
        self._double_click_window: float = 0.35

        self.current_x: int = self.mapper.screen.width // 2
        self.current_y: int = self.mapper.screen.height // 2

        self._is_windows = platform.system() == "Windows"
        if self._is_windows:
            self._user32 = ctypes.windll.user32
        else:
            self._user32 = None

    @property
    def is_dragging(self) -> bool:
        return self._is_dragging

    def move_to(self, norm_x: float, norm_y: float) -> Tuple[int, int]:
        """Maps and smoothly moves the cursor to the target camera coordinates.

        Args:
            norm_x: Normalized horizontal coordinate [0.0, 1.0].
            norm_y: Normalized vertical coordinate [0.0, 1.0].

        Returns:
            Tuple of final smoothed screen coordinates (smooth_x, smooth_y).
        """
        # 1. Project normalized coordinate to screen resolution with active margin box
        raw_screen_x, raw_screen_y = self.mapper.map_to_screen(norm_x, norm_y)

        # 2. Filter tremor using adaptive velocity-dependent filter
        smooth_x, smooth_y = self.smoother.filter(raw_screen_x, raw_screen_y)

        self.current_x = smooth_x
        self.current_y = smooth_y

        # 3. Dispatch hardware event
        if self._is_windows and self._user32:
            self._user32.SetCursorPos(smooth_x, smooth_y)
        else:
            pyautogui.moveTo(smooth_x, smooth_y)

        return smooth_x, smooth_y

    def left_click(self) -> bool:
        """Executes a left mouse click with debouncing protection."""
        now = time.perf_counter()
        if (now - self._last_click_time) < self.click_cooldown:
            return False

        logger.info(f"Left Click at ({self.current_x}, {self.current_y})")

        if self._is_windows and self._user32:
            try:
                self._user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                time.sleep(0.015)
            finally:
                self._user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        else:
            pyautogui.click(button="left")

        self._last_click_time = now
        self._last_left_click_time = now
        return True

    def right_click(self) -> bool:
        """Executes a right mouse click with debouncing protection."""
        now = time.perf_counter()
        if (now - self._last_click_time) < self.click_cooldown:
            return False

        logger.info(f"Right Click at ({self.current_x}, {self.current_y})")

        if self._is_windows and self._user32:
            try:
                self._user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
                time.sleep(0.015)
            finally:
                self._user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
        else:
            pyautogui.click(button="right")

        self._last_click_time = now
        return True

    def double_click(self) -> bool:
        """Executes a rapid double-click event."""
        now = time.perf_counter()
        if (now - self._last_click_time) < self.click_cooldown:
            return False

        logger.info(f"Double Click at ({self.current_x}, {self.current_y})")
        if self._is_windows and self._user32:
            try:
                self._user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                time.sleep(0.01)
                self._user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                time.sleep(0.05)
                self._user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                time.sleep(0.01)
            finally:
                self._user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        else:
            pyautogui.doubleClick()

        self._last_click_time = now
        return True

    def start_drag(self) -> bool:
        """Presses and holds the left mouse button to initiate drag mode."""
        if self._is_dragging:
            return False

        logger.info(f"Drag Started at ({self.current_x}, {self.current_y})")
        if self._is_windows and self._user32:
            self._user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        else:
            pyautogui.mouseDown(button="left")

        self._is_dragging = True
        return True

    def end_drag(self) -> bool:
        """Releases the held left mouse button to complete drop mode."""
        if not self._is_dragging:
            return False

        logger.info(f"Drag Ended (Drop) at ({self.current_x}, {self.current_y})")
        if self._is_windows and self._user32:
            self._user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        else:
            pyautogui.mouseUp(button="left")

        self._is_dragging = False
        return True

    def reset(self) -> None:
        """Resets smoother state and guarantees all hardware mouse buttons are released."""
        if self._is_dragging:
            self.end_drag()
        if self._is_windows and self._user32:
            self._user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            self._user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
        self.smoother.reset()

