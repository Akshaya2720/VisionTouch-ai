"""Hand Detection and Tracking Subsystem using MediaPipe.

Provides:
- Two-stage pipeline (BlazePalm detector + Hand Landmark model).
- Memory-efficient inference with read-only frame buffers.
- Multi-hand tracking with handedness classification (Left vs Right).
- Clean visualization and annotation utilities.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import cv2
import mediapipe as mp
import numpy as np

from app.config import VisionConfig
from app.utils.logger import setup_logger

logger = setup_logger("HandDetector")


@dataclass
class DetectedHand:
    """Represents a single detected hand with landmarks and metadata."""
    hand_id: int
    handedness: str  # 'Left' or 'Right'
    confidence: float
    # List of 21 (x, y, z) normalized coordinates (range [0.0, 1.0])
    normalized_landmarks: List[Tuple[float, float, float]]
    # List of 21 (x, y) pixel coordinates
    pixel_landmarks: List[Tuple[int, int]]


class HandDetector:
    """Encapsulates MediaPipe Hands perception graph with performance optimizations."""

    def __init__(self, config: Optional[VisionConfig] = None) -> None:
        """Initializes the MediaPipe Hands graph.

        Args:
            config: VisionConfig dataclass with confidence thresholds and hand limits.
        """
        self.config = config or VisionConfig()
        self._mp_hands = mp.solutions.hands
        self._mp_draw = mp.solutions.drawing_utils
        self._mp_draw_styles = mp.solutions.drawing_styles

        logger.info(
            f"Initializing MediaPipe Hands (max_hands={self.config.max_num_hands}, "
            f"detect_conf={self.config.min_detection_confidence:.2f}, "
            f"track_conf={self.config.min_tracking_confidence:.2f})"
        )

        self._hands = self._mp_hands.Hands(
            static_image_mode=False,  # Video streaming mode enables temporal tracking
            max_num_hands=self.config.max_num_hands,
            model_complexity=self.config.model_complexity,
            min_detection_confidence=self.config.min_detection_confidence,
            min_tracking_confidence=self.config.min_tracking_confidence,
        )

    def process_frame(
        self, frame: np.ndarray, draw: bool = False
    ) -> Tuple[List[DetectedHand], np.ndarray]:
        """Runs hand detection and landmark extraction on a raw BGR frame.

        Args:
            frame: Raw BGR input frame (NumPy array of shape [H, W, 3]).
            draw: If True, draws landmarks and skeleton connections on the frame.

        Returns:
            Tuple of (detected_hands_list, annotated_frame).
        """
        h, w, _ = frame.shape
        output_frame = frame.copy() if draw else frame

        # Performance Optimization:
        # Mark frame as non-writeable to pass by reference to underlying C++ graph
        # and convert from BGR to RGB (MediaPipe expects RGB color channel order).
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb_frame.flags.writeable = False

        results = self._hands.process(rgb_frame)

        detected_hands: List[DetectedHand] = []

        if not results.multi_hand_landmarks:
            return detected_hands, output_frame

        # Extract handedness metadata (Left vs Right)
        handedness_list: List[Tuple[str, float]] = []
        if results.multi_handedness:
            for hand_meta in results.multi_handedness:
                label = hand_meta.classification[0].label
                score = hand_meta.classification[0].score
                handedness_list.append((label, score))

        for idx, hand_lms in enumerate(results.multi_hand_landmarks):
            norm_landmarks: List[Tuple[float, float, float]] = []
            pixel_landmarks: List[Tuple[int, int]] = []

            for lm in hand_lms.landmark:
                norm_landmarks.append((lm.x, lm.y, lm.z))
                px = int(np.clip(lm.x * w, 0, w - 1))
                py = int(np.clip(lm.y * h, 0, h - 1))
                pixel_landmarks.append((px, py))

            label, score = (
                handedness_list[idx] if idx < len(handedness_list) else ("Unknown", 0.0)
            )

            detected_hands.append(
                DetectedHand(
                    hand_id=idx,
                    handedness=label,
                    confidence=score,
                    normalized_landmarks=norm_landmarks,
                    pixel_landmarks=pixel_landmarks,
                )
            )

            if draw:
                self._draw_landmarks(output_frame, hand_lms)

        return detected_hands, output_frame

    def _draw_landmarks(self, frame: np.ndarray, hand_lms) -> None:
        """Renders hand landmarks and skeletal links onto the frame."""
        self._mp_draw.draw_landmarks(
            frame,
            hand_lms,
            self._mp_hands.HAND_CONNECTIONS,
            self._mp_draw_styles.get_default_hand_landmarks_style(),
            self._mp_draw_styles.get_default_hand_connections_style(),
        )

    def close(self) -> None:
        """Frees the underlying C++ graph and GPU/CPU inference engines."""
        if hasattr(self, "_hands") and self._hands is not None:
            self._hands.close()
            self._hands = None
            logger.info("MediaPipe Hands graph closed successfully.")

    def __del__(self) -> None:
        self.close()

