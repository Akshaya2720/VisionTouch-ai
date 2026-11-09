"""Interactive Real-Time Touchless Controls Demo for Phase 5.

Demonstrates:
- Touchless Scrolling with Index + Middle fingers (up/down).
- Swipe Left / Swipe Right for Browser Tab switching or Media Track skip.
- Open Palm for Play/Pause.
- Emergency freeze on Closed Fist.

Usage:
    python tests/run_touchless_controls_demo.py
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
from app.controllers.keyboard_controller import KeyboardController
from app.controllers.media_controller import MediaController
from app.controllers.scroll_controller import ScrollController
from app.gestures.gesture_recognizer import GestureRecognizer
from app.gestures.gesture_types import GestureType
from app.utils.logger import setup_logger
from app.vision.hand_detector import HandDetector

logger = setup_logger("TouchlessControlsDemo")


def main() -> None:
    logger.info("Starting Phase 5 Touchless Controls System...")

    camera = CameraManager(config.camera)
    detector = HandDetector(config.vision)
    recognizer = GestureRecognizer()

    scroller = ScrollController()
    media = MediaController()
    keyboard = KeyboardController()

    if not camera.start():
        logger.error("Failed to start camera. Exiting.")
        return

    window_name = "VisionTouch AI - Phase 5 Touchless Controls"
    cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)

    logger.info("Touchless Controls ACTIVE:")
    logger.info("Two Fingers Up/Down: Scroll Web/Feeds | Swipe Left/Right: Browser Tabs | Open Palm: Play/Pause")

    action_banner_text = "READY"
    action_banner_time = 0.0

    try:
        while camera.is_running:
            success, frame = camera.read_frame()
            if not success or frame is None:
                break

            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape

            hands, annotated_frame = detector.process_frame(frame, draw=True)
            now = time.perf_counter()
            recognized = recognizer.recognize(hands, now)

            primary = recognized[0] if recognized else None
            active_type = primary.gesture if primary else GestureType.NONE

            # Dispatch Actions
            if active_type in (GestureType.SCROLL_UP, GestureType.SCROLL_DOWN):
                delta = primary.scroll_delta
                # Invert delta so moving fingers up scrolls page up (positive)
                scroller.scroll(delta)
                action_banner_text = f"SCROLLING: {active_type.name} ({delta:+.1f})"
                action_banner_time = now

            elif active_type == GestureType.SWIPE_LEFT:
                keyboard.previous_tab()
                action_banner_text = "SWIPE LEFT: PREVIOUS TAB"
                action_banner_time = now

            elif active_type == GestureType.SWIPE_RIGHT:
                keyboard.next_tab()
                action_banner_text = "SWIPE RIGHT: NEXT TAB"
                action_banner_time = now

            elif active_type == GestureType.OPEN_PALM:
                if media.play_pause():
                    action_banner_text = "OPEN PALM: MEDIA PLAY/PAUSE"
                    action_banner_time = now

            # Render Action Notification Banner
            if (now - action_banner_time) < 1.2:
                cv2.rectangle(annotated_frame, (w // 2 - 200, h - 60), (w // 2 + 200, h - 15), (0, 140, 255), -1)
                cv2.putText(annotated_frame, action_banner_text, (w // 2 - 185, h - 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.60, (255, 255, 255), 2, cv2.LINE_AA)

            # HUD Display
            hud_text = f"FPS: {camera.fps:.1f} | Gesture: {active_type.name}"
            cv2.rectangle(annotated_frame, (10, 10), (420, 50), (20, 20, 20), -1)
            cv2.putText(annotated_frame, hud_text, (20, 35),
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
        cv2.destroyAllWindows()
        logger.info("Touchless Controls demo finished.")


if __name__ == "__main__":
    main()

