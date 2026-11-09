"""Unit tests for Coordinate Mapping, Adaptive Smoothing, and Mouse Automation (Phase 4)."""

import math
import time
import pytest

from app.controllers.mouse_controller import MouseController
from app.utils.coordinate_mapper import CoordinateMapper, ScreenBounds
from app.utils.smoothing import AdaptiveTremorFilter


def test_coordinate_mapper_center():
    """Verify camera center (0.5, 0.5) maps to the center of the screen."""
    mapper = CoordinateMapper(margin_x=0.1, margin_y=0.1, sensitivity=1.0)
    mapper.screen = ScreenBounds(width=1920, height=1080)

    sx, sy = mapper.map_to_screen(0.5, 0.5)
    assert sx == 1920 // 2
    assert sy == 1080 // 2


def test_coordinate_mapper_boundary_clamping():
    """Verify coordinates outside the active margin box clamp strictly within display boundaries."""
    mapper = CoordinateMapper(margin_x=0.15, margin_y=0.20)
    mapper.screen = ScreenBounds(width=1920, height=1080)

    # Top-left corner beyond margin
    sx, sy = mapper.map_to_screen(0.05, 0.05)
    assert sx == 0
    assert sy == 0

    # Bottom-right corner beyond margin
    sx, sy = mapper.map_to_screen(0.95, 0.95)
    assert sx == 1920 - 1
    assert sy == 1080 - 1


def test_adaptive_tremor_filter_damping():
    """Verify tiny tremors are smoothed effectively while large steps move rapidly."""
    filter_ = AdaptiveTremorFilter(min_alpha=0.10, max_alpha=0.90)

    # First point initializes filter
    x0, y0 = filter_.filter(100, 100, timestamp=1.0)
    assert x0 == 100
    assert y0 == 100

    # Simulate microscopic tremor (102, 101) after 33ms (small speed)
    x1, y1 = filter_.filter(102, 101, timestamp=1.033)
    # Filter should suppress the displacement heavily (alpha ~ 0.10)
    assert abs(x1 - 100) <= 1
    assert abs(y1 - 100) <= 1


def test_mouse_controller_debouncing():
    """Verify rapid consecutive clicks are debounced by cooldown timer."""
    controller = MouseController(click_cooldown=0.30)

    # First click must succeed
    first = controller.left_click()
    assert first is True

    # Immediate second click (without waiting cooldown) must be blocked
    second = controller.left_click()
    assert second is False


def test_mouse_drag_and_drop_lifecycle():
    """Verify drag and drop state changes correctly."""
    controller = MouseController()
    assert not controller.is_dragging

    # Start drag
    started = controller.start_drag()
    assert started is True
    assert controller.is_dragging is True

    # Starting drag again while already dragging should return False
    duplicate = controller.start_drag()
    assert duplicate is False

    # End drag
    ended = controller.end_drag()
    assert ended is True
    assert controller.is_dragging is False

