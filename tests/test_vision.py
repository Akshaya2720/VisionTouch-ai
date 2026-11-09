"""Unit tests for Computer Vision Hand Detection and Landmark Processing."""

import math
import numpy as np
import pytest

from app.vision.hand_detector import HandDetector, DetectedHand
from app.vision.landmark_processor import LandmarkIndex, LandmarkProcessor


def create_mock_hand(
    fingers_up: bool = True, handedness: str = "Right"
) -> DetectedHand:
    """Helper to synthesize a 21-landmark hand for deterministic testing."""
    norm_lms = []
    pixel_lms = []

    # Wrist at (0.5, 0.8)
    wrist = (0.5, 0.8, 0.0)

    # Generate synthetic coordinates
    for i in range(21):
        if i == 0:
            norm_lms.append(wrist)
        elif i in (4, 8, 12, 16, 20):  # TIPS
            y = 0.2 if fingers_up else 0.7  # If up, tip is near top (small y)
            x = 0.2 + (i / 20.0) * 0.6
            norm_lms.append((x, y, 0.0))
        elif i in (3, 7, 11, 15, 19):  # DIPs / PIPs
            y = 0.5  # middle of hand
            x = 0.2 + (i / 20.0) * 0.6
            norm_lms.append((x, y, 0.0))
        elif i in (2, 6, 10, 14, 18):  # PIPs / MCPs
            y = 0.6
            x = 0.2 + (i / 20.0) * 0.6
            norm_lms.append((x, y, 0.0))
        else:
            norm_lms.append((0.5, 0.65, 0.0))

        pixel_lms.append((int(norm_lms[-1][0] * 640), int(norm_lms[-1][1] * 480)))

    return DetectedHand(
        hand_id=0,
        handedness=handedness,
        confidence=0.95,
        normalized_landmarks=norm_lms,
        pixel_landmarks=pixel_lms,
    )


def test_hand_detector_initialization():
    """Verify HandDetector initializes and cleans up resources cleanly."""
    detector = HandDetector()
    assert detector._hands is not None
    detector.close()
    assert detector._hands is None


def test_euclidean_distance():
    """Verify 2D Euclidean distance calculation."""
    d = LandmarkProcessor.euclidean_distance_2d((0.0, 0.0), (3.0, 4.0))
    assert math.isclose(d, 5.0, rel_tol=1e-5)


def test_palm_scale_invariance():
    """Verify normalized distance divides out hand scale."""
    processor = LandmarkProcessor()
    hand = create_mock_hand(fingers_up=True)

    palm_size = processor.get_palm_size(hand)
    assert palm_size > 0.0

    norm_dist = processor.normalized_distance(
        hand, LandmarkIndex.WRIST, LandmarkIndex.MIDDLE_FINGER_MCP
    )
    # Distance to itself divided by itself should equal 1.0
    assert math.isclose(norm_dist, 1.0, rel_tol=1e-4)


def test_finger_states_open_palm():
    """Verify open palm detects all non-thumb fingers as extended."""
    processor = LandmarkProcessor()
    hand = create_mock_hand(fingers_up=True)
    states = processor.get_finger_states(hand)

    assert states["index"] is True
    assert states["middle"] is True
    assert states["ring"] is True
    assert states["pinky"] is True


def test_finger_states_closed_fist():
    """Verify closed fist detects all non-thumb fingers as curled."""
    processor = LandmarkProcessor()
    hand = create_mock_hand(fingers_up=False)
    states = processor.get_finger_states(hand)

    assert states["index"] is False
    assert states["middle"] is False
    assert states["ring"] is False
    assert states["pinky"] is False


def test_bounding_box_computation():
    """Verify bounding box coordinates stay within valid image boundary."""
    hand = create_mock_hand(fingers_up=True)
    x, y, w, h = LandmarkProcessor.get_bounding_box(hand, padding=10)
    assert x >= 0
    assert y >= 0
    assert w > 0
    assert h > 0

