"""Unit tests for the Camera Management subsystem."""

import pytest
from app.config import CameraConfig
from app.camera.camera_manager import CameraManager


def test_camera_config_defaults():
    """Verify default camera parameters comply with performance budget."""
    cfg = CameraConfig()
    assert cfg.frame_width == 640
    assert cfg.frame_height == 480
    assert cfg.target_fps == 30
    assert cfg.default_camera_index == 0


def test_camera_manager_initial_state():
    """Verify camera manager starts uninitialized and reports zero FPS."""
    manager = CameraManager()
    assert not manager.is_running
    assert manager.fps == 0.0


def test_camera_enumeration():
    """Verify camera enumeration returns a list of integers without crashing."""
    cameras = CameraManager.list_available_cameras(max_probe=2)
    assert isinstance(cameras, list)
    for cam_idx in cameras:
        assert isinstance(cam_idx, int)

