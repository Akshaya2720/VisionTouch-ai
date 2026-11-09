"""Unit tests for SQLite Database, State Manager, and Action Dispatcher (Phase 6)."""

from pathlib import Path
import pytest

from app.controllers.keyboard_controller import KeyboardController
from app.controllers.media_controller import MediaController
from app.controllers.mouse_controller import MouseController
from app.controllers.scroll_controller import ScrollController
from app.core.action_manager import ActionManager
from app.core.state_manager import AppState, StateManager
from app.database.db_manager import DatabaseManager
from app.gestures.gesture_types import GestureType, RecognizedGesture


@pytest.fixture
def temp_db(tmp_path: Path) -> DatabaseManager:
    """Provides an isolated SQLite database instance for testing."""
    test_db_path = tmp_path / "test_visiontouch.db"
    return DatabaseManager(db_path=test_db_path)


def test_database_initial_seed(temp_db: DatabaseManager):
    """Verify default settings and all 5 profiles are seeded properly."""
    settings = temp_db.get_settings()
    assert settings.active_profile == "Default"
    assert settings.cursor_sensitivity == 1.0

    profiles = temp_db.get_profiles()
    assert "Default" in profiles
    assert "YouTube" in profiles
    assert "Instagram" in profiles
    assert "PowerPoint" in profiles
    assert "VLC" in profiles


def test_database_settings_update(temp_db: DatabaseManager):
    """Verify settings fields update correctly in SQLite."""
    temp_db.update_settings(cursor_sensitivity=1.5, active_profile="YouTube")
    updated = temp_db.get_settings()
    assert updated.cursor_sensitivity == 1.5
    assert updated.active_profile == "YouTube"


def test_database_mapping_customization(temp_db: DatabaseManager):
    """Verify custom gesture mappings persist and can be reset."""
    # Override Default profile mapping
    temp_db.update_mapping("Default", "SWIPE_LEFT", "custom_action")
    mappings = temp_db.get_mappings("Default")
    assert mappings["SWIPE_LEFT"] == "custom_action"

    # Reset back to default
    temp_db.reset_profile("Default")
    reset_mappings = temp_db.get_mappings("Default")
    assert reset_mappings["SWIPE_LEFT"] == "previous_tab"


def test_state_manager_transitions():
    """Verify StateManager state transitions and notification callbacks."""
    sm = StateManager()
    assert sm.state == AppState.ACTIVE

    states_recorded = []
    sm.add_listener(lambda s: states_recorded.append(s))

    # Toggle to Standby
    sm.toggle_standby()
    assert sm.state == AppState.STANDBY

    # Set to Emergency Pause
    sm.set_state(AppState.PAUSED)
    assert sm.state == AppState.PAUSED

    assert states_recorded == [AppState.STANDBY, AppState.PAUSED]


def test_action_manager_dispatch(temp_db: DatabaseManager):
    """Verify ActionManager routes gestures according to active profile."""
    sm = StateManager()
    mouse = MouseController()
    scroller = ScrollController()
    media = MediaController()
    kb = KeyboardController()

    am = ActionManager(temp_db, sm, mouse, scroller, media, kb)

    # Test Left Click in Default profile
    g_click = RecognizedGesture(GestureType.LEFT_CLICK_PINCH, 0.95, 0, "Right")
    action = am.dispatch(g_click)
    assert action == "left_click"

    # Switch profile to VLC and test Left Click -> play_pause
    am.set_profile("VLC")
    action_vlc = am.dispatch(g_click)
    assert action_vlc == "play_pause"

