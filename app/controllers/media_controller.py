"""Media and Playback Automation Controller for VisionTouch AI.

Dispatches hardware media keys and web playback hotkeys for YouTube, Spotify,
VLC, and web video players.
"""

import ctypes
import platform
import time
from typing import Optional
import pyautogui

from app.utils.logger import setup_logger

logger = setup_logger("MediaController")

# Windows Virtual-Key (VK) codes for standard multimedia keyboards
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3

KEYEVENTF_KEYUP = 0x0002


class MediaController:
    """Controls OS system volume, media playback, and video player navigation."""

    def __init__(self, action_cooldown: float = 0.35) -> None:
        self.action_cooldown = action_cooldown
        self._last_action_time: float = 0.0

        self._is_windows = platform.system() == "Windows"
        self._user32 = ctypes.windll.user32 if self._is_windows else None

    def _can_execute(self) -> bool:
        now = time.perf_counter()
        if (now - self._last_action_time) < self.action_cooldown:
            return False
        self._last_action_time = now
        return True

    def _send_vk(self, vk_code: int) -> None:
        """Sends a hardware virtual key press and release event on Windows."""
        if self._is_windows and self._user32:
            self._user32.keybd_event(vk_code, 0, 0, 0)
            time.sleep(0.01)
            self._user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)

    def play_pause(self) -> bool:
        """Toggles media play/pause state across system players or active YouTube tab."""
        if not self._can_execute():
            return False
        logger.info("Executing Media PLAY/PAUSE")
        if self._is_windows:
            self._send_vk(VK_MEDIA_PLAY_PAUSE)
        else:
            pyautogui.press("playpause")
        return True

    def next_track(self) -> bool:
        """Skips to the next video or track."""
        if not self._can_execute():
            return False
        logger.info("Executing Media NEXT TRACK")
        if self._is_windows:
            self._send_vk(VK_MEDIA_NEXT_TRACK)
        else:
            pyautogui.press("nexttrack")
        return True

    def previous_track(self) -> bool:
        """Returns to the previous video or track."""
        if not self._can_execute():
            return False
        logger.info("Executing Media PREVIOUS TRACK")
        if self._is_windows:
            self._send_vk(VK_MEDIA_PREV_TRACK)
        else:
            pyautogui.press("prevtrack")
        return True

    def volume_up(self, steps: int = 1) -> bool:
        """Increases system volume."""
        if not self._can_execute():
            return False
        logger.info(f"Executing VOLUME UP ({steps} steps)")
        for _ in range(steps):
            if self._is_windows:
                self._send_vk(VK_VOLUME_UP)
            else:
                pyautogui.press("volumeup")
            time.sleep(0.02)
        return True

    def volume_down(self, steps: int = 1) -> bool:
        """Decreases system volume."""
        if not self._can_execute():
            return False
        logger.info(f"Executing VOLUME DOWN ({steps} steps)")
        for _ in range(steps):
            if self._is_windows:
                self._send_vk(VK_VOLUME_DOWN)
            else:
                pyautogui.press("volumedown")
            time.sleep(0.02)
        return True

    def mute(self) -> bool:
        """Toggles system audio mute."""
        if not self._can_execute():
            return False
        logger.info("Executing VOLUME MUTE")
        if self._is_windows:
            self._send_vk(VK_VOLUME_MUTE)
        else:
            pyautogui.press("volumemute")
        return True

