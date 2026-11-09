"""Interactive Real-Time Gesture Recognition Diagnostic for Phase 3.

Demonstrates:
- Real-time classification of the 10 core gestures.
- Visual feedback on gesture status (Hysteresis, temporal smoothing).
- Pinch and scroll feedback overlays.
- Emergency pause / Safe mode indicator on Closed Fist.

Usage:
    python tests/run_gesture_demo.py
Press 'q' or 'ESC' to quit.
"""

import sys
from pathlib import Path
import time

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import cv2
from app.camera.camera_manager import CameraManager
from app.config import config
from app.gestures.gesture_recognizer import GestureRecognizer
from app.gestures.gesture_types import GestureType
from app.utils.logger import setup_logger
from app.vision.hand_detector import HandDetector
from app.vision.landmark_processor import LandmarkIndex, LandmarkProcessor

logger = setup_logger("GestureDemo")

GESTURE_COLORS = {
    GestureType.NONE: (180, 180, 180),
    GestureType.CURSOR_MOVE: (0, 255, 0),         # Green
    GestureType.LEFT_CLICK_PINCH: (0, 0, 255),     # Red
    GestureType.RIGHT_CLICK_PINCH: (255, 0, 255),  # Magenta
    GestureType.SCROLL_MODE: (255, 200, 0),       # Cyan/Blue
    GestureType.SCROLL_UP: (0, 255, 255),         # Yellow
    GestureType.SCROLL_DOWN: (0, 165, 255),       # Orange
    GestureType.CLOSED_FIST: (0, 0, 180),         # Dark Red (Paused)
    GestureType.OPEN_PALM: (200, 255, 200),       # Light Green (Active)
    GestureType.SWIPE_LEFT: (255, 100, 0),        # Blue
    GestureType.SWIPE_RIGHT: (0, 100, 255),       # Orange
    GestureType.ZOOM_IN: (255, 255, 0),           # Cyan
    GestureType.ZOOM_OUT: (128, 255, 0),          # Lime
}


def main() -> None:
    logger.info("Starting Phase 3 Gesture Recognition Diagnostic...")

    camera = CameraManager(config.camera)
    detector = HandDetector(config.vision)
    recognizer = GestureRecognizer()
    processor = LandmarkProcessor()

    if not camera.start():
        logger.error("Failed to start camera. Exiting.")
        return

    window_name = "VisionTouch AI - Phase 3 Gesture Recognition"
    cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)

    logger.info("Gesture engine active! Perform gestures in front of the camera. Press 'q' to quit.")

    try:
        while camera.is_running:
            success, frame = camera.read_frame()
            if not success or frame is None:
                break

            # Mirror frame horizontally for intuitive mirror interaction
            frame = cv2.flip(frame, 1)

            # Detect hands and landmarks
            hands, annotated_frame = detector.process_frame(frame, draw=True)

            # Classify gestures
            now = time.perf_counter()
            recognized_gestures = recognizer.recognize(hands, now)
            smoothed_gesture = recognizer.get_smoothed_gesture()

            # Primary gesture display
            primary_gesture = recognized_gestures[0] if recognized_gestures else None
            active_type = primary_gesture.gesture if primary_gesture else GestureType.NONE
            color = GESTURE_COLORS.get(active_type, (200, 200, 200))

            # HUD Display Banner
            cv2.rectangle(annotated_frame, (10, 10), (450, 160), (20, 20, 20), -1)
            cv2.rectangle(annotated_frame, (10, 10), (450, 160), color, 2)

            fps_text = f"FPS: {camera.fps:.1f}"
            gesture_text = f"GESTURE: {active_type.name}"
            smooth_text = f"Smoothed: {smoothed_gesture.name}"

            cv2.putText(annotated_frame, fps_text, (20, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2, cv2.LINE_AA)
            cv2.putText(annotated_frame, gesture_text, (20, 70),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.80, color, 2, cv2.LINE_AA)
            cv2.putText(annotated_frame, smooth_text, (20, 105),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.60, (220, 220, 220), 1, cv2.LINE_AA)

            # Detailed gesture feedback
            if active_type == GestureType.CURSOR_MOVE and primary_gesture.cursor_position:
                cx = int(primary_gesture.cursor_position[0] * frame.shape[1])
                cy = int(primary_gesture.cursor_position[1] * frame.shape[0])
                cv2.circle(annotated_frame, (cx, cy), 12, (0, 255, 0), 2)
                cv2.putText(annotated_frame, "CURSOR TARGET", (cx + 15, cy),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 255, 0), 1)

            elif active_type in (GestureType.SCROLL_UP, GestureType.SCROLL_DOWN):
                delta_text = f"Scroll Velocity: {primary_gesture.scroll_delta:+.2f}"
                cv2.putText(annotated_frame, delta_text, (20, 138),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.60, (0, 255, 255), 2, cv2.LINE_AA)

            elif active_type == GestureType.CLOSED_FIST:
                cv2.putText(annotated_frame, "[SYSTEM PAUSED / SAFE MODE]", (20, 138),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.60, (0, 0, 255), 2, cv2.LINE_AA)

            elif active_type == GestureType.LEFT_CLICK_PINCH:
                cv2.putText(annotated_frame, "LEFT CLICK (LATCHED)", (20, 138),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.60, (0, 0, 255), 2, cv2.LINE_AA)

            elif active_type == GestureType.RIGHT_CLICK_PINCH:
                cv2.putText(annotated_frame, "RIGHT CLICK (LATCHED)", (20, 138),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.60, (255, 0, 255), 2, cv2.LINE_AA)

            cv2.imshow(window_name, annotated_frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord('q'), ord('Q')):
                break

    except KeyboardInterrupt:
        pass
    finally:
        camera.stop()
        detector.close()
        cv2.destroyAllWindows()
        logger.info("Gesture diagnostic closed cleanly.")


if __name__ == "__main__":
    main()

