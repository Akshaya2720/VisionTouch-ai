"""Unit tests for the Gesture Recognition Subsystem (Phase 3)."""

import pytest
from app.gestures.gesture_calibration import GestureThresholds
from app.gestures.gesture_recognizer import GestureRecognizer
from app.gestures.gesture_types import GestureType
from app.vision.hand_detector import DetectedHand
from app.vision.landmark_processor import LandmarkIndex


def build_hand_with_fingers(
    index: bool = False,
    middle: bool = False,
    ring: bool = False,
    pinky: bool = False,
    thumb: bool = False,
    thumb_idx_pinch: bool = False,
    thumb_mid_pinch: bool = False,
) -> DetectedHand:
    """Synthesizes a realistic 21-landmark hand configuration for deterministic gesture tests."""
    lms = []
    # Wrist at (0.5, 0.8)
    wrist = (0.5, 0.8, 0.0)

    for i in range(21):
        if i == LandmarkIndex.WRIST:
            lms.append(wrist)
        elif i == LandmarkIndex.MIDDLE_FINGER_MCP:
            # Palm reference: 0.3 units away vertically -> palm size = 0.3
            lms.append((0.5, 0.5, 0.0))
        elif i == LandmarkIndex.INDEX_FINGER_TIP:
            if thumb_idx_pinch:
                lms.append((0.40, 0.60, 0.0))  # Pinched with thumb
            else:
                # Extended points up (y=0.20), curled folds into palm (y=0.55)
                y = 0.20 if index else 0.55
                x = 0.45 if index else 0.48
                lms.append((x, y, 0.0))
        elif i == LandmarkIndex.INDEX_FINGER_PIP:
            lms.append((0.45, 0.45, 0.0))
        elif i == LandmarkIndex.MIDDLE_FINGER_TIP:
            if thumb_mid_pinch:
                lms.append((0.40, 0.60, 0.0))  # Pinched with thumb
            else:
                y = 0.18 if middle else 0.65
                lms.append((0.50, y, 0.0))
        elif i == LandmarkIndex.MIDDLE_FINGER_PIP:
            lms.append((0.50, 0.45, 0.0))
        elif i == LandmarkIndex.RING_FINGER_TIP:
            y = 0.20 if ring else 0.65
            lms.append((0.55, y, 0.0))
        elif i == LandmarkIndex.RING_FINGER_PIP:
            lms.append((0.55, 0.45, 0.0))
        elif i == LandmarkIndex.PINKY_TIP:
            y = 0.22 if pinky else 0.65
            lms.append((0.60, y, 0.0))
        elif i == LandmarkIndex.PINKY_PIP:
            lms.append((0.60, 0.45, 0.0))
        elif i == LandmarkIndex.THUMB_TIP:
            if thumb_idx_pinch or thumb_mid_pinch:
                lms.append((0.41, 0.60, 0.0))  # Near index or middle tip
            else:
                # Extended thumb extends left (x=0.28). Curled thumb tucks right (x=0.45).
                x = 0.28 if thumb else 0.45
                y = 0.55 if thumb else 0.70
                lms.append((x, y, 0.0))
        elif i == LandmarkIndex.THUMB_IP:
            lms.append((0.36, 0.65, 0.0))
        elif i == LandmarkIndex.THUMB_MCP:
            lms.append((0.40, 0.70, 0.0))
        else:
            lms.append((0.5, 0.6, 0.0))

    pixel_lms = [(int(pt[0] * 640), int(pt[1] * 480)) for pt in lms]

    return DetectedHand(
        hand_id=0,
        handedness="Right",
        confidence=0.95,
        normalized_landmarks=lms,
        pixel_landmarks=pixel_lms,
    )


def test_cursor_move_gesture():
    """Index finger extended, others curled -> CURSOR_MOVE."""
    recognizer = GestureRecognizer()
    hand = build_hand_with_fingers(index=True, middle=False, ring=False, pinky=False)
    results = recognizer.recognize([hand])

    assert len(results) == 1
    assert results[0].gesture == GestureType.CURSOR_MOVE
    assert results[0].cursor_position is not None


def test_left_click_pinch_gesture():
    """Thumb and Index pinched together -> LEFT_CLICK_PINCH."""
    recognizer = GestureRecognizer()
    hand = build_hand_with_fingers(thumb_idx_pinch=True)
    results = recognizer.recognize([hand])

    assert len(results) == 1
    assert results[0].gesture == GestureType.LEFT_CLICK_PINCH


def test_closed_fist_gesture():
    """All fingers curled -> CLOSED_FIST."""
    recognizer = GestureRecognizer()
    hand = build_hand_with_fingers(index=False, middle=False, ring=False, pinky=False, thumb=False)
    results = recognizer.recognize([hand])

    assert len(results) == 1
    assert results[0].gesture == GestureType.CLOSED_FIST


def test_open_palm_gesture():
    """All 5 fingers extended -> OPEN_PALM."""
    recognizer = GestureRecognizer()
    hand = build_hand_with_fingers(index=True, middle=True, ring=True, pinky=True, thumb=True)
    results = recognizer.recognize([hand])

    assert len(results) == 1
    assert results[0].gesture == GestureType.OPEN_PALM


def test_scroll_mode_gesture():
    """Index and Middle extended, others curled -> SCROLL_MODE."""
    recognizer = GestureRecognizer()
    hand = build_hand_with_fingers(index=True, middle=True, ring=False, pinky=False)
    results = recognizer.recognize([hand])

    assert len(results) == 1
    assert results[0].gesture in (GestureType.SCROLL_MODE, GestureType.SCROLL_UP, GestureType.SCROLL_DOWN)


def test_pinch_hysteresis():
    """Verify Schmitt-trigger hysteresis latches and unlatches properly."""
    thresholds = GestureThresholds(pinch_enter_threshold=0.20, pinch_exit_threshold=0.30)
    recognizer = GestureRecognizer(thresholds)

    # 1. Start far apart (dist = 0.40) -> Not pinched
    state = recognizer._eval_hysteresis(hand_id=0, distance=0.40, state_dict=recognizer._is_left_pinching)
    assert state is False

    # 2. Move to intermediate distance (0.25) -> Still not pinched (must enter < 0.20)
    state = recognizer._eval_hysteresis(hand_id=0, distance=0.25, state_dict=recognizer._is_left_pinching)
    assert state is False

    # 3. Pinch firmly (0.15) -> Latch to True
    state = recognizer._eval_hysteresis(hand_id=0, distance=0.15, state_dict=recognizer._is_left_pinching)
    assert state is True

    # 4. Open slightly to intermediate distance (0.25) -> Stays latched True due to hysteresis!
    state = recognizer._eval_hysteresis(hand_id=0, distance=0.25, state_dict=recognizer._is_left_pinching)
    assert state is True

    # 5. Open wide (0.35) -> Unlatches to False
    state = recognizer._eval_hysteresis(hand_id=0, distance=0.35, state_dict=recognizer._is_left_pinching)
    assert state is False
