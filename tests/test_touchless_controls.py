"""Unit tests for Touchless Scrolling, Media Controls, and Keyboard Navigation (Phase 5)."""

import time
import pytest

from app.controllers.keyboard_controller import KeyboardController
from app.controllers.media_controller import MediaController
from app.controllers.scroll_controller import ScrollController


def test_scroll_controller_zero_delta():
    """Verify scroll controller rejects zero or infinitesimal displacement."""
    scroller = ScrollController()
    assert scroller.scroll(0.0) is False
    assert scroller.scroll(1e-6) is False


def test_scroll_controller_cooldown_throttling():
    """Verify rapid scroll calls are throttled to prevent event queue flooding."""
    scroller = ScrollController(cooldown=0.05)
    first = scroller.scroll(1.0)
    assert first is True

    # Immediate second call within cooldown must be throttled
    second = scroller.scroll(1.0)
    assert second is False


def test_media_controller_cooldown():
    """Verify media controller blocks rapid repeated executions."""
    media = MediaController(action_cooldown=0.25)
    assert media.play_pause() is True
    # Immediate repeat must be blocked
    assert media.play_pause() is False


def test_keyboard_controller_safety_blacklist():
    """Verify dangerous hotkeys like Alt+F4 are actively intercepted and blocked."""
    kb = KeyboardController(action_cooldown=0.1)
    # Block Alt+F4
    blocked_f4 = kb.execute_hotkey("alt", "f4")
    assert blocked_f4 is False

    # Block Windows Lock
    blocked_lock = kb.execute_hotkey("win", "l")
    assert blocked_lock is False


def test_keyboard_controller_cooldown():
    """Verify keyboard actions obey debounce cooldowns."""
    kb = KeyboardController(action_cooldown=0.30)
    first = kb.refresh_page()
    assert first is True

    # Immediate repeat should be blocked
    second = kb.refresh_page()
    assert second is False

