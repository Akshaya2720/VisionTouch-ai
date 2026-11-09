"""Coordinate Mapping and Spatial Projection for VisionTouch AI.

Converts normalized camera coordinates into absolute Windows desktop screen coordinates,
applying active interaction margins (deadzones) and sensitivity scaling.
"""

from dataclasses import dataclass
from typing import Tuple
import numpy as np
import pyautogui


@dataclass
class ScreenBounds:
    """Dimensions of the target display."""
    width: int
    height: int


class CoordinateMapper:
    """Projects camera normalized coordinates [0.0, 1.0] onto the Windows screen resolution.

    Solves the 'Screen Edge Reachability' problem:
    If we map 100% of the camera FOV to the screen, a user would have to reach
    so far to the edges that their hand would exit the camera view.
    By defining an 'Active Control Box' (e.g. 15% margin on X, 20% margin on Y),
    moving your hand within the comfortable center 70% of the camera view
    traverses 100% of the laptop display.
    """

    def __init__(
        self,
        margin_x: float = 0.15,
        margin_y: float = 0.20,
        sensitivity: float = 1.0,
    ) -> None:
        """Initializes the coordinate mapper.

        Args:
            margin_x: Horizontal camera margin fraction ignored at each edge.
            margin_y: Vertical camera margin fraction ignored at each edge.
            sensitivity: Global cursor speed multiplier.
        """
        self.margin_x = margin_x
        self.margin_y = margin_y
        self.sensitivity = max(0.2, min(sensitivity, 3.0))

        # Query primary monitor screen resolution via PyAutoGUI
        screen_w, screen_h = pyautogui.size()
        self.screen = ScreenBounds(width=screen_w, height=screen_h)

    def set_margins(self, margin_x: float, margin_y: float) -> None:
        """Updates active interaction box margins."""
        self.margin_x = max(0.0, min(margin_x, 0.40))
        self.margin_y = max(0.0, min(margin_y, 0.40))

    def set_sensitivity(self, sensitivity: float) -> None:
        """Updates cursor sensitivity multiplier."""
        self.sensitivity = max(0.2, min(sensitivity, 3.0))

    def map_to_screen(self, norm_x: float, norm_y: float) -> Tuple[int, int]:
        """Translates normalized camera coordinates into pixel screen coordinates.

        Args:
            norm_x: Normalized horizontal coordinate in camera space [0.0, 1.0].
            norm_y: Normalized vertical coordinate in camera space [0.0, 1.0].

        Returns:
            Tuple of integer (screen_x, screen_y) clamped to monitor bounds.
        """
        # Active control box boundaries in camera space
        x_min = self.margin_x
        x_max = 1.0 - self.margin_x
        y_min = self.margin_y
        y_max = 1.0 - self.margin_y

        # Linear interpolation with clamping:
        # Maps [x_min, x_max] -> [0, screen_width]
        screen_x = np.interp(norm_x, [x_min, x_max], [0, self.screen.width])
        screen_y = np.interp(norm_y, [y_min, y_max], [0, self.screen.height])

        # Apply sensitivity scaling relative to screen center
        if self.sensitivity != 1.0:
            center_x = self.screen.width / 2.0
            center_y = self.screen.height / 2.0
            screen_x = center_x + (screen_x - center_x) * self.sensitivity
            screen_y = center_y + (screen_y - center_y) * self.sensitivity

        # Clamp strictly within physical display boundaries
        clamped_x = int(np.clip(screen_x, 0, self.screen.width - 1))
        clamped_y = int(np.clip(screen_y, 0, self.screen.height - 1))

        return clamped_x, clamped_y

