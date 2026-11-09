"""Biomechanical Thresholds and Calibration Parameters for Gesture Recognition.

All thresholds are mathematically defined and experimentally calibrated
to account for hand scale invariance, sensor noise, and human tremor.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class GestureThresholds:
    """Threshold constants for gesture classification and state transitions."""

    # Pinch Hysteresis Thresholds (Normalized to palm scale S_palm = dist(WRIST, MIDDLE_MCP))
    # Schmitt-trigger dual thresholds prevent contact bouncing:
    # 1. Distance must drop below ENTER to trigger a pinch.
    # 2. Distance must rise above EXIT to release the pinch.
    pinch_enter_threshold: float = 0.22
    pinch_exit_threshold: float = 0.32

    # Click timing parameters (in seconds)
    click_cooldown_sec: float = 0.30
    double_click_interval_sec: float = 0.35

    # Scrolling thresholds
    # Deadzone filters out microscopic human hand tremors when holding fingers still
    scroll_deadzone: float = 0.025
    scroll_sensitivity: float = 18.0

    # Swipe gesture thresholds
    # Velocity is in normalized screen units per second
    swipe_velocity_threshold: float = 1.10
    swipe_cooldown_sec: float = 0.45
    swipe_min_lateral_ratio: float = 2.0  # |vx| must be at least 2x |vy| to be a true lateral swipe

    # Two-hand Zoom thresholds
    zoom_deadzone: float = 0.03
    zoom_sensitivity: float = 2.5

    # Temporal smoothing
    temporal_history_length: int = 5


# Default calibrated instance
default_thresholds = GestureThresholds()
