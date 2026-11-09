"""Core Gesture Recognition Engine for VisionTouch AI.

Processes spatial hand landmark configurations, applies biomechanical
state machine rules, temporal voting, and hysteresis to detect the 10 core gestures.
"""

from collections import deque
import math
import time
from typing import Deque, Dict, List, Optional, Tuple

from app.gestures.gesture_calibration import GestureThresholds, default_thresholds
from app.gestures.gesture_types import GestureType, RecognizedGesture
from app.utils.logger import setup_logger
from app.vision.hand_detector import DetectedHand
from app.vision.landmark_processor import LandmarkIndex, LandmarkProcessor

logger = setup_logger("GestureRecognizer")


class GestureRecognizer:
    """Classifies gestures using biomechanical rules, hysteresis, and temporal filtering."""

    def __init__(self, thresholds: Optional[GestureThresholds] = None) -> None:
        self.thresholds = thresholds or default_thresholds
        self.processor = LandmarkProcessor()

        # State machine variables for Hysteresis
        self._is_left_pinching: Dict[int, bool] = {}   # hand_id -> is_pinched
        self._is_right_pinching: Dict[int, bool] = {}  # hand_id -> is_pinched

        # Cooldown timestamps
        self._last_click_timestamp: float = 0.0
        self._last_swipe_timestamp: float = 0.0

        # Scroll reference anchor (hand_id -> prev_y)
        self._prev_scroll_y: Dict[int, float] = {}

        # Two-hand zoom anchor (prev_inter_hand_distance)
        self._prev_zoom_distance: Optional[float] = None

        # Temporal filter: sliding window of recent gesture types for majority voting
        self._gesture_history: Deque[GestureType] = deque(
            maxlen=self.thresholds.temporal_history_length
        )

    def recognize(
        self, hands: List[DetectedHand], current_time: Optional[float] = None
    ) -> List[RecognizedGesture]:
        """Classifies gestures for one or two hands in the current frame.

        Args:
            hands: List of DetectedHand objects from HandDetector.
            current_time: High-resolution timestamp (defaults to time.perf_counter()).

        Returns:
            List of RecognizedGesture instances.
        """
        now = current_time or time.perf_counter()
        results: List[RecognizedGesture] = []

        if not hands:
            self._reset_transient_state()
            return results

        # 1. Multi-hand gesture: Two-hand Zoom (Gesture 10)
        if len(hands) >= 2:
            zoom_gesture = self._check_two_hand_zoom(hands[0], hands[1])
            if zoom_gesture is not None:
                results.append(zoom_gesture)
                return results

        # 2. Single-hand gestures (evaluated for the primary/first hand)
        primary_hand = hands[0]
        hand_id = primary_hand.hand_id

        # Compute geometric primitives
        finger_states = self.processor.get_finger_states(primary_hand)
        thumb_idx_dist = self.processor.normalized_distance(
            primary_hand, LandmarkIndex.THUMB_TIP, LandmarkIndex.INDEX_FINGER_TIP
        )
        thumb_mid_dist = self.processor.normalized_distance(
            primary_hand, LandmarkIndex.THUMB_TIP, LandmarkIndex.MIDDLE_FINGER_TIP
        )

        vx, vy = self.processor.calculate_velocity(primary_hand, now)

        # Count extended non-thumb fingers
        up_count = sum(1 for f in ("index", "middle", "ring", "pinky") if finger_states[f])

        # Evaluate gestures hierarchically:

        # Gesture 3: Right-Click Pinch (Thumb + Middle tip)
        is_right_pinched = self._eval_hysteresis(
            hand_id, thumb_mid_dist, self._is_right_pinching
        )
        if is_right_pinched:
            raw_gesture = GestureType.RIGHT_CLICK_PINCH
            idx_pos = primary_hand.normalized_landmarks[LandmarkIndex.INDEX_FINGER_TIP]
            results.append(
                RecognizedGesture(
                    raw_gesture, 0.90, hand_id, primary_hand.handedness,
                    cursor_position=(idx_pos[0], idx_pos[1])
                )
            )
            self._apply_temporal_smoothing(raw_gesture)
            return results

        # Gesture 2: Left-Click Pinch (Thumb + Index tip)
        is_left_pinched = self._eval_hysteresis(
            hand_id, thumb_idx_dist, self._is_left_pinching
        )
        if is_left_pinched:
            raw_gesture = GestureType.LEFT_CLICK_PINCH
            idx_pos = primary_hand.normalized_landmarks[LandmarkIndex.INDEX_FINGER_TIP]
            results.append(
                RecognizedGesture(
                    raw_gesture, 0.95, hand_id, primary_hand.handedness,
                    cursor_position=(idx_pos[0], idx_pos[1])
                )
            )
            self._apply_temporal_smoothing(raw_gesture)
            return results

        # Gesture 6: Closed Fist (Emergency Pause / Safe Mode)
        # All fingers curled (including thumb), and neither pinch is active
        if up_count == 0 and not finger_states["thumb"]:
            raw_gesture = GestureType.CLOSED_FIST
            results.append(RecognizedGesture(raw_gesture, 0.95, hand_id, primary_hand.handedness))
            self._apply_temporal_smoothing(raw_gesture)
            self._prev_scroll_y.pop(hand_id, None)
            return results

        # Check for Swipe on hand motion (Gesture 8 & 9)
        swipe = self._check_swipe(vx, vy, now, hand_id, primary_hand.handedness)
        if swipe is not None:
            results.append(swipe)
            return results

        # Gesture 7: Open Palm (Toggle Mode / Standby)
        # All 5 fingers extended upright
        if up_count == 4 and finger_states["thumb"]:
            raw_gesture = GestureType.OPEN_PALM
            results.append(RecognizedGesture(raw_gesture, 0.95, hand_id, primary_hand.handedness))
            self._apply_temporal_smoothing(raw_gesture)
            self._prev_scroll_y.pop(hand_id, None)
            return results

        # Gesture 4 & 5: Two Fingers Extended -> Scroll Mode (Index + Middle UP, Ring + Pinky DOWN)
        if finger_states["index"] and finger_states["middle"] and not finger_states["ring"] and not finger_states["pinky"]:
            scroll_gesture = self._eval_scrolling(primary_hand, hand_id)
            results.append(scroll_gesture)
            self._apply_temporal_smoothing(scroll_gesture.gesture)
            return results
        else:
            self._prev_scroll_y.pop(hand_id, None)

        # Gesture 1: Index Finger Extended -> Cursor Movement
        # Index UP, Middle, Ring, Pinky DOWN
        if finger_states["index"] and not finger_states["middle"] and not finger_states["ring"] and not finger_states["pinky"]:
            raw_gesture = GestureType.CURSOR_MOVE
            idx_pos = primary_hand.normalized_landmarks[LandmarkIndex.INDEX_FINGER_TIP]
            results.append(
                RecognizedGesture(
                    raw_gesture, 0.90, hand_id, primary_hand.handedness,
                    cursor_position=(idx_pos[0], idx_pos[1])
                )
            )
            self._apply_temporal_smoothing(raw_gesture)
            return results

        # Default fallback
        results.append(RecognizedGesture(GestureType.NONE, 0.50, hand_id, primary_hand.handedness))
        self._apply_temporal_smoothing(GestureType.NONE)
        return results

    def _eval_hysteresis(
        self, hand_id: int, distance: float, state_dict: Dict[int, bool]
    ) -> bool:
        """Applies dual-threshold Schmitt Trigger to prevent contact bounce jitter."""
        currently_pinched = state_dict.get(hand_id, False)
        if currently_pinched:
            # Must open beyond exit threshold to unlatch
            if distance > self.thresholds.pinch_exit_threshold:
                state_dict[hand_id] = False
                return False
            return True
        else:
            # Must close tighter than enter threshold to latch
            if distance < self.thresholds.pinch_enter_threshold:
                state_dict[hand_id] = True
                return True
            return False

    def _eval_scrolling(self, hand: DetectedHand, hand_id: int) -> RecognizedGesture:
        """Converts vertical displacement of two fingers into SCROLL_UP / SCROLL_DOWN commands."""
        # Use midpoint of Index TIP and Middle TIP as reference
        idx_tip = hand.normalized_landmarks[LandmarkIndex.INDEX_FINGER_TIP]
        mid_tip = hand.normalized_landmarks[LandmarkIndex.MIDDLE_FINGER_TIP]
        curr_y = (idx_tip[1] + mid_tip[1]) / 2.0

        if hand_id not in self._prev_scroll_y:
            self._prev_scroll_y[hand_id] = curr_y
            return RecognizedGesture(GestureType.SCROLL_MODE, 0.85, hand_id, hand.handedness)

        prev_y = self._prev_scroll_y[hand_id]
        delta_y = curr_y - prev_y  # positive = moving down, negative = moving up

        self._prev_scroll_y[hand_id] = curr_y

        # Deadzone filter
        if abs(delta_y) < self.thresholds.scroll_deadzone:
            return RecognizedGesture(GestureType.SCROLL_MODE, 0.85, hand_id, hand.handedness)

        if delta_y < 0:
            # Fingers moved UP -> Scroll UP (content moves up)
            return RecognizedGesture(
                GestureType.SCROLL_UP, 0.90, hand_id, hand.handedness,
                scroll_delta=-delta_y * self.thresholds.scroll_sensitivity
            )
        else:
            # Fingers moved DOWN -> Scroll DOWN
            return RecognizedGesture(
                GestureType.SCROLL_DOWN, 0.90, hand_id, hand.handedness,
                scroll_delta=delta_y * self.thresholds.scroll_sensitivity
            )

    def _check_swipe(
        self, vx: float, vy: float, now: float, hand_id: int, handedness: str
    ) -> Optional[RecognizedGesture]:
        """Detects rapid lateral hand swipes (Gesture 8 & 9)."""
        if (now - self._last_swipe_timestamp) < self.thresholds.swipe_cooldown_sec:
            return None

        speed_x = abs(vx)
        speed_y = abs(vy)

        # Must exceed velocity threshold and be predominantly horizontal
        if speed_x > self.thresholds.swipe_velocity_threshold and speed_x > (speed_y * self.thresholds.swipe_min_lateral_ratio):
            self._last_swipe_timestamp = now
            if vx > 0:
                logger.info(f"Detected SWIPE_RIGHT (vx={vx:.2f})")
                return RecognizedGesture(GestureType.SWIPE_RIGHT, 0.92, hand_id, handedness)
            else:
                logger.info(f"Detected SWIPE_LEFT (vx={vx:.2f})")
                return RecognizedGesture(GestureType.SWIPE_LEFT, 0.92, hand_id, handedness)
        return None

    def _check_two_hand_zoom(
        self, hand1: DetectedHand, hand2: DetectedHand
    ) -> Optional[RecognizedGesture]:
        """Detects two-hand pinch zoom: hands moving apart (Zoom In) or together (Zoom Out)."""
        # Compute distance between wrists of both hands
        w1 = hand1.normalized_landmarks[LandmarkIndex.WRIST]
        w2 = hand2.normalized_landmarks[LandmarkIndex.WRIST]
        current_distance = math.hypot(w1[0] - w2[0], w1[1] - w2[1])

        if self._prev_zoom_distance is None:
            self._prev_zoom_distance = current_distance
            return None

        delta_dist = current_distance - self._prev_zoom_distance
        self._prev_zoom_distance = current_distance

        if abs(delta_dist) < self.thresholds.zoom_deadzone:
            return None

        if delta_dist > 0:
            scale = 1.0 + (delta_dist * self.thresholds.zoom_sensitivity)
            return RecognizedGesture(
                GestureType.ZOOM_IN, 0.88, hand1.hand_id, "Both", zoom_scale=scale
            )
        else:
            scale = max(0.2, 1.0 + (delta_dist * self.thresholds.zoom_sensitivity))
            return RecognizedGesture(
                GestureType.ZOOM_OUT, 0.88, hand1.hand_id, "Both", zoom_scale=scale
            )

    def _apply_temporal_smoothing(self, current: GestureType) -> None:
        """Appends to sliding history for majority voting."""
        self._gesture_history.append(current)

    def get_smoothed_gesture(self) -> GestureType:
        """Returns the statistically dominant gesture in recent temporal history."""
        if not self._gesture_history:
            return GestureType.NONE
        # Return most frequent gesture in deque (majority vote)
        counts: Dict[GestureType, int] = {}
        for g in self._gesture_history:
            counts[g] = counts.get(g, 0) + 1
        return max(counts, key=counts.get)

    def _reset_transient_state(self) -> None:
        self._is_left_pinching.clear()
        self._is_right_pinching.clear()
        self._prev_scroll_y.clear()
        self._prev_zoom_distance = None
        self._gesture_history.clear()
