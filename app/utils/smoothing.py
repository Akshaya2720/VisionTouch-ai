"""Adaptive Cursor Smoothing and Tremor Filtration for VisionTouch AI.

Implements:
- Standard Exponential Moving Average (EMA).
- Dynamic Adaptive Low-Pass Filter (One-Euro Filter inspired):
  Adapts smoothing coefficient alpha based on cursor velocity:
  * Slow motion (precision targeting) -> High smoothing (alpha -> 0.15), rock-solid stability.
  * Fast motion (ballistic sweeps)     -> Low smoothing (alpha -> 0.85), near-zero lag.
"""

import math
import time
from typing import Optional, Tuple


class AdaptiveTremorFilter:
    """Dynamically adjusts cutoff frequency and smoothing based on instantaneous velocity."""

    def __init__(
        self,
        min_alpha: float = 0.20,
        max_alpha: float = 0.85,
        speed_threshold: float = 1200.0,
    ) -> None:
        """Initializes the adaptive filter.

        Args:
            min_alpha: Smoothing weight when velocity is zero (maximum tremor suppression).
            max_alpha: Smoothing weight during fast ballistic movements (minimal latency).
            speed_threshold: Velocity (pixels/sec) at which filter reaches max_alpha.
        """
        self.min_alpha = min_alpha
        self.max_alpha = max_alpha
        self.speed_threshold = speed_threshold

        self._prev_x: Optional[float] = None
        self._prev_y: Optional[float] = None
        self._prev_time: Optional[float] = None

    def filter(
        self, target_x: float, target_y: float, timestamp: Optional[float] = None
    ) -> Tuple[int, int]:
        """Applies adaptive velocity-dependent smoothing to an input 2D coordinate.

        Args:
            target_x: Raw target screen X coordinate.
            target_y: Raw target screen Y coordinate.
            timestamp: High-resolution timestamp.

        Returns:
            Tuple of smoothed integer coordinates (smooth_x, smooth_y).
        """
        now = timestamp or time.perf_counter()

        if self._prev_x is None or self._prev_y is None or self._prev_time is None:
            self._prev_x = float(target_x)
            self._prev_y = float(target_y)
            self._prev_time = now
            return int(target_x), int(target_y)

        dt = now - self._prev_time
        if dt <= 0:
            return int(self._prev_x), int(self._prev_y)

        # Calculate instantaneous velocity (pixels per second)
        distance = math.hypot(target_x - self._prev_x, target_y - self._prev_y)
        speed = distance / dt

        # Dynamically scale alpha:
        # speed = 0 -> alpha = min_alpha
        # speed >= speed_threshold -> alpha = max_alpha
        speed_ratio = min(speed / self.speed_threshold, 1.0)
        alpha = self.min_alpha + (self.max_alpha - self.min_alpha) * speed_ratio

        # Exponential Moving Average update
        smooth_x = alpha * target_x + (1.0 - alpha) * self._prev_x
        smooth_y = alpha * target_y + (1.0 - alpha) * self._prev_y

        self._prev_x = smooth_x
        self._prev_y = smooth_y
        self._prev_time = now

        return int(round(smooth_x)), int(round(smooth_y))

    def reset(self) -> None:
        """Clears filter state (useful when hand tracking is lost and re-acquired)."""
        self._prev_x = None
        self._prev_y = None
        self._prev_time = None

