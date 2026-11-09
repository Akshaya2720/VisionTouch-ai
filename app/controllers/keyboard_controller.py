"""Keyboard and Desktop Navigation Controller for VisionTouch AI.

Dispatches browser tab switching, window navigation (Alt+Tab), screenshots,
and custom keyboard shortcuts with safety guards.
"""

import time
from typing import List, Optional
import pyautogui

from app.utils.logger import setup_logger

logger = setup_logger("KeyboardController")


class KeyboardController:
    """Manages touchless keyboard automation and application navigation."""

    def __init__(self, action_cooldown: float = 0.40) -> None:
        self.action_cooldown = action_cooldown
        self._last_action_time: float = 0.0

        # Safety blacklist to prevent accidental system shutdown or window killing
        self._blacklisted_combos = {
            ("alt", "f4"),
            ("ctrl", "alt", "del"),
            ("win", "l"),  # Prevent accidental lock
        }

    def _can_execute(self) -> bool:
        now = time.perf_counter()
        if (now - self._last_action_time) < self.action_cooldown:
            return False
        self._last_action_time = now
        return True

    def next_tab(self) -> bool:
        """Switches to the next browser tab (Ctrl + Tab)."""
        if not self._can_execute():
            return False
        logger.info("Executing NEXT BROWSER TAB (Ctrl+Tab)")
        pyautogui.hotkey("ctrl", "tab")
        return True

    def previous_tab(self) -> bool:
        """Switches to the previous browser tab (Ctrl + Shift + Tab)."""
        if not self._can_execute():
            return False
        logger.info("Executing PREVIOUS BROWSER TAB (Ctrl+Shift+Tab)")
        pyautogui.hotkey("ctrl", "shift", "tab")
        return True

    def switch_window(self) -> bool:
        """Switches active desktop application (Alt + Tab)."""
        if not self._can_execute():
            return False
        logger.info("Executing SWITCH WINDOW (Alt+Tab)")
        pyautogui.hotkey("alt", "tab")
        return True

    def refresh_page(self) -> bool:
        """Refreshes the current web page or explorer view (F5)."""
        if not self._can_execute():
            return False
        logger.info("Executing REFRESH (F5)")
        pyautogui.press("f5")
        return True

    def take_screenshot(self) -> bool:
        """Triggers Windows screenshot shortcut (Win + PrtScn)."""
        if not self._can_execute():
            return False
        logger.info("Executing SCREENSHOT (Win+PrtScn)")
        pyautogui.hotkey("win", "printscreen")
        return True

    def press_key(self, key_name: str) -> bool:
        """Presses an individual keyboard key."""
        if not self._can_execute():
            return False
        logger.info(f"Pressing key: '{key_name}'")
        pyautogui.press(key_name)
        return True

    def execute_hotkey(self, *keys: str) -> bool:
        """Dispatches a custom combination of keys with safety filtering."""
        if not self._can_execute():
            return False

        lower_keys = tuple(k.lower() for k in keys)
        if lower_keys in self._blacklisted_combos:
            logger.warning(f"Blocked dangerous hotkey combination: {lower_keys}")
            return False

        logger.info(f"Executing Hotkey: {'+'.join(keys)}")
        pyautogui.hotkey(*keys)
        return True

