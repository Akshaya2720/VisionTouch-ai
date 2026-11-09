"""Geometric and Spatial Processing for Hand Landmarks.

Provides:
- Landmark anatomical enumeration (21 MediaPipe joints).
- Scale-invariant Euclidean distance calculations.
- Finger state classification (extended vs curled).
- Hand movement velocity and displacement tracking across frames.
- Hand bounding box calculation.
"""

from enum import IntEnum
import math
from typing import Dict, List, Optional, Tuple
import numpy as np

from app.vision.hand_detector import DetectedHand


class LandmarkIndex(IntEnum):
    """Anatomical MediaPipe Hand Landmark IDs."""
    WRIST = 0
    THUMB_CMC = 1
    THUMB_MCP = 2
    THUMB_IP = 3
    THUMB_TIP = 4
    INDEX_FINGER_MCP = 5
    INDEX_FINGER_PIP = 6
    INDEX_FINGER_DIP = 7
    INDEX_FINGER_TIP = 8
    MIDDLE_FINGER_MCP = 9
    MIDDLE_FINGER_PIP = 10
    MIDDLE_FINGER_DIP = 11
    MIDDLE_FINGER_TIP = 12
    RING_FINGER_MCP = 13
    RING_FINGER_PIP = 14
    RING_FINGER_DIP = 15
    RING_FINGER_TIP = 16
    PINKY_MCP = 17
    PINKY_PIP = 18
    PINKY_DIP = 19
    PINKY_TIP = 20


# Mapping of fingers to their anatomical joints: (TIP, PIP, MCP)
FINGER_JOINTS = {
    "thumb": (LandmarkIndex.THUMB_TIP, LandmarkIndex.THUMB_IP, LandmarkIndex.THUMB_MCP),
    "index": (LandmarkIndex.INDEX_FINGER_TIP, LandmarkIndex.INDEX_FINGER_PIP, LandmarkIndex.INDEX_FINGER_MCP),
    "middle": (LandmarkIndex.MIDDLE_FINGER_TIP, LandmarkIndex.MIDDLE_FINGER_PIP, LandmarkIndex.MIDDLE_FINGER_MCP),
    "ring": (LandmarkIndex.RING_FINGER_TIP, LandmarkIndex.RING_FINGER_PIP, LandmarkIndex.RING_FINGER_MCP),
    "pinky": (LandmarkIndex.PINKY_TIP, LandmarkIndex.PINKY_PIP, LandmarkIndex.PINKY_MCP),
}


class LandmarkProcessor:
    """Performs spatial geometry, distance calculations, and finger state analysis."""

    def __init__(self) -> None:
        # History buffer for velocity and temporal motion tracking
        # Maps hand_id -> (prev_wrist_x, prev_wrist_y, timestamp)
        self._previous_positions: Dict[int, Tuple[float, float, float]] = {}

    @staticmethod
    def euclidean_distance_2d(
        p1: Tuple[float, float], p2: Tuple[float, float]
    ) -> float:
        """Calculates standard Euclidean distance between two 2D points:

        d = sqrt((x2 - x1)^2 + (y2 - y1)^2)
        """
        return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

    @staticmethod
    def get_palm_size(hand: DetectedHand) -> float:
        """Calculates reference palm scale (distance between WRIST and MIDDLE_MCP).

        Used as the scale normalization factor so distances remain invariant
        regardless of whether the user sits 30 cm or 120 cm from the camera.
        """
        wrist = hand.normalized_landmarks[LandmarkIndex.WRIST]
        middle_mcp = hand.normalized_landmarks[LandmarkIndex.MIDDLE_FINGER_MCP]
        size = math.hypot(wrist[0] - middle_mcp[0], wrist[1] - middle_mcp[1])
        return max(size, 1e-4)  # Prevent division by zero

    def normalized_distance(
        self, hand: DetectedHand, idx1: LandmarkIndex, idx2: LandmarkIndex
    ) -> float:
        """Returns the palm-scale-invariant normalized distance between two landmarks.

        A distance of 0.2 means the points are separated by 20% of the palm length.
        """
        p1 = hand.normalized_landmarks[idx1]
        p2 = hand.normalized_landmarks[idx2]
        raw_dist = math.hypot(p1[0] - p2[0], p1[1] - p2[1])
        palm_size = self.get_palm_size(hand)
        return raw_dist / palm_size

    @staticmethod
    def get_finger_states(hand: DetectedHand) -> Dict[str, bool]:
        """Determines which fingers are extended (True) vs curled (False).

        Algorithm:
        - For Index, Middle, Ring, Pinky:
          The finger is extended if its TIP y-coordinate is above (smaller than)
          its PIP joint y-coordinate (remember: y=0 is top of image).
        - For Thumb:
          Checks horizontal extension of THUMB_TIP relative to THUMB_IP
          based on handedness (Left vs Right hand).
        """
        lms = hand.normalized_landmarks
        states: Dict[str, bool] = {}

        # 4 Standard fingers: TIP.y < PIP.y indicates finger is pointing UP
        for finger_name, (tip_idx, pip_idx, _) in FINGER_JOINTS.items():
            if finger_name == "thumb":
                continue
            states[finger_name] = lms[tip_idx][1] < lms[pip_idx][1]

        # Thumb extension check:
        # For right hand facing camera: thumb extends to the left (smaller x)
        # For left hand facing camera: thumb extends to the right (larger x)
        thumb_tip = lms[LandmarkIndex.THUMB_TIP]
        thumb_ip = lms[LandmarkIndex.THUMB_IP]
        thumb_mcp = lms[LandmarkIndex.THUMB_MCP]

        if hand.handedness == "Right":
            states["thumb"] = (thumb_tip[0] < thumb_ip[0]) and (thumb_ip[0] < thumb_mcp[0])
        else:
            states["thumb"] = (thumb_tip[0] > thumb_ip[0]) and (thumb_ip[0] > thumb_mcp[0])

        return states

    @staticmethod
    def get_bounding_box(
        hand: DetectedHand, padding: int = 20
    ) -> Tuple[int, int, int, int]:
        """Calculates pixel bounding box around the hand: (x_min, y_min, width, height)."""
        xs = [pt[0] for pt in hand.pixel_landmarks]
        ys = [pt[1] for pt in hand.pixel_landmarks]
        x_min = max(0, min(xs) - padding)
        y_min = max(0, min(ys) - padding)
        x_max = max(xs) + padding
        y_max = max(ys) + padding
        return x_min, y_min, (x_max - x_min), (y_max - y_min)

    def calculate_velocity(
        self, hand: DetectedHand, current_timestamp: float
    ) -> Tuple[float, float]:
        """Calculates normalized hand displacement velocity (dx/dt, dy/dt) across frames.

        Returns:
            Tuple of (velocity_x, velocity_y) in normalized units per second.
        """
        wrist = hand.normalized_landmarks[LandmarkIndex.WRIST]
        curr_x, curr_y = wrist[0], wrist[1]

        if hand.hand_id not in self._previous_positions:
            self._previous_positions[hand.hand_id] = (curr_x, curr_y, current_timestamp)
            return 0.0, 0.0

        prev_x, prev_y, prev_time = self._previous_positions[hand.hand_id]
        dt = current_timestamp - prev_time

        if dt <= 0:
            return 0.0, 0.0

        vx = (curr_x - prev_x) / dt
        vy = (curr_y - prev_y) / dt

        self._previous_positions[hand.hand_id] = (curr_x, curr_y, current_timestamp)
        return vx, vy

