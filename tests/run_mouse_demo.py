"""Interactive Real-Time Virtual Mouse Demo for Phase 4.

Demonstrates:
- Touchless Windows cursor control using Index Finger tracking.
- Active Control Box visualization (margins).
- Left-click via Thumb-Index pinch.
- Right-click via Thumb-Middle pinch.
- Emergency freeze / Pause when making a Closed Fist.

Usage:
    python tests/run_mouse_demo.py
Press 'q' or 'ESC' to exit.
"""

import sys
from pathlib import Path
import time

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import cv2
from app.camera.camera_manager import CameraManager
from app.config import config
from app.controllers.mouse_controller import MouseController
from app.gestures.gesture_recognizer import GestureRecognizer
from app.gestures.gesture_types import GestureType
from app.utils.coordinate_mapper import CoordinateMapper
from app.utils.logger import setup_logger
from app.vision.hand_detector import HandDetector
from app.vision.landmark_processor import LandmarkIndex

logger = setup_logger("VirtualMouseDemo")


def main() -> None:
    logger.info("Initializing Phase 4 Virtual Mouse System...")

    camera = CameraManager(config.camera)
    detector = HandDetector(config.vision)
    recognizer = GestureRecognizer()

    mapper = CoordinateMapper(margin_x=0.15, margin_y=0.20, sensitivity=1.1)
    mouse = MouseController(mapper=mapper)

    if not camera.start():
        logger.error("Failed to start camera. Exiting.")
        return

    window_name = "VisionTouch AI - Phase 4 Virtual Mouse Control"
    cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)

    logger.info("Virtual Mouse is ACTIVE! Control your laptop cursor with your hand.")
    logger.info("Index Finger: Move cursor | Thumb-Index Pinch: Left Click | Fist: Emergency Pause")

    try:
        while camera.is_running:
            success, frame = camera.read_frame()
            if not success or frame is None:
                break

            # Mirror frame horizontally so left/right matches screen naturally
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape

            # Detect hands and classify gestures
            hands, annotated_frame = detector.process_frame(frame, draw=True)
            now = time.perf_counter()
            recognized = recognizer.recognize(hands, now)

            # Draw the Active Control Box (margins)
            box_x1 = int(mapper.margin_x * w)
            box_y1 = int(mapper.margin_y * h)
            box_x2 = int((1.0 - mapper.margin_x) * w)
            box_y2 = int((1.0 - mapper.margin_y) * h)
            cv2.rectangle(annotated_frame, (box_x1, box_y1), (box_x2, box_y2), (0, 200, 255), 2)
            cv2.putText(annotated_frame, "ACTIVE CONTROL ZONE", (box_x1 + 10, box_y1 + 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 200, 255), 1, cv2.LINE_AA)

            primary_gesture = recognized[0] if recognized else None
            active_type = primary_gesture.gesture if primary_gesture else GestureType.NONE

            # Dispatch mouse actions
            if active_type == GestureType.CURSOR_MOVE and primary_gesture.cursor_position:
                norm_x, norm_y = primary_gesture.cursor_position
                screen_x, screen_y = mouse.move_to(norm_x, norm_y)

                # Visual indicator at index fingertip
                px = int(norm_x * w)
                py = int(norm_y * h)
                cv2.circle(annotated_frame, (px, py), 12, (0, 255, 0), -1)
                cv2.putText(annotated_frame, f"Mouse: ({screen_x}, {screen_y})", (px + 15, py),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 255, 0), 2)

            elif active_type == GestureType.LEFT_CLICK_PINCH:
                mouse.left_click()
                cv2.putText(annotated_frame, "[LEFT CLICK DISPATCHED]", (w // 2 - 120, h - 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.70, (0, 0, 255), 2, cv2.LINE_AA)

            elif active_type == GestureType.RIGHT_CLICK_PINCH:
                mouse.right_click()
                cv2.putText(annotated_frame, "[RIGHT CLICK DISPATCHED]", (w // 2 - 120, h - 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.70, (255, 0, 255), 2, cv2.LINE_AA)

            elif active_type == GestureType.CLOSED_FIST:
                cv2.putText(annotated_frame, "[PAUSED / SAFE MODE]", (w // 2 - 110, h - 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.70, (0, 0, 255), 2, cv2.LINE_AA)

            elif not hands:
                mouse.reset()

            # HUD Display
            fps_text = f"FPS: {camera.fps:.1f} | State: {active_type.name}"
            cv2.rectangle(annotated_frame, (10, 10), (380, 50), (20, 20, 20), -1)
            cv2.putText(annotated_frame, fps_text, (20, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2, cv2.LINE_AA)

            cv2.imshow(window_name, annotated_frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord('q'), ord('Q')):
                break

    except KeyboardInterrupt:
        pass
    finally:
        camera.stop()
        detector.close()
        mouse.reset()
        cv2.destroyAllWindows()
        logger.info("Virtual Mouse session ended.")


if __name__ == "__main__":
    main()

