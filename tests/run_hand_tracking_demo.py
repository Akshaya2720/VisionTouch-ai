"""Interactive Real-Time Hand Tracking & Landmark Diagnostic for Phase 2.

Demonstrates:
- Live 21-point hand tracking with MediaPipe.
- Finger extension state visualization (UP / DOWN).
- Scale-invariant pinch distance (Thumb TIP to Index TIP).
- Hand bounding box and handedness identification.
- Real-time FPS monitoring.

Usage:
    python tests/run_hand_tracking_demo.py
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
from app.utils.logger import setup_logger
from app.vision.hand_detector import HandDetector
from app.vision.landmark_processor import LandmarkIndex, LandmarkProcessor

logger = setup_logger("HandTrackingDemo")


def main() -> None:
    logger.info("Starting Phase 2 Hand Tracking Diagnostic...")

    camera = CameraManager(config.camera)
    detector = HandDetector(config.vision)
    processor = LandmarkProcessor()

    if not camera.start():
        logger.error("Failed to start camera. Exiting.")
        return

    window_name = "VisionTouch AI - Phase 2 Hand Tracking & Landmarks"
    cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)

    logger.info("Hand tracking active. Show your hand to the camera. Press 'q' to quit.")

    try:
        while camera.is_running:
            success, frame = camera.read_frame()
            if not success or frame is None:
                break

            # Mirror frame horizontally so movements feel natural
            frame = cv2.flip(frame, 1)

            # Process frame with MediaPipe (draw=True renders skeleton connections)
            hands, annotated_frame = detector.process_frame(frame, draw=True)

            # Diagnostics HUD background
            cv2.rectangle(annotated_frame, (10, 10), (320, 150), (20, 20, 20), -1)
            cv2.rectangle(annotated_frame, (10, 10), (320, 150), (0, 255, 200), 1)

            fps_text = f"FPS: {camera.fps:.1f}"
            hands_text = f"Hands Detected: {len(hands)}"

            cv2.putText(annotated_frame, fps_text, (20, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2, cv2.LINE_AA)
            cv2.putText(annotated_frame, hands_text, (20, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.60, (255, 255, 255), 1, cv2.LINE_AA)

            current_time = time.perf_counter()

            for hand in hands:
                # 1. Bounding Box
                bx, by, bw, bh = processor.get_bounding_box(hand, padding=15)
                cv2.rectangle(annotated_frame, (bx, by), (bx + bw, by + bh), (255, 200, 0), 2)
                cv2.putText(
                    annotated_frame, f"{hand.handedness} Hand ({hand.confidence:.2f})",
                    (bx, max(20, by - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 200, 0), 2
                )

                # 2. Finger states
                finger_states = processor.get_finger_states(hand)
                state_str = " | ".join(
                    [f"{f[0].upper()}:{'UP' if s else 'DN'}" for f, s in finger_states.items()]
                )
                cv2.putText(annotated_frame, f"Fingers: {state_str}", (20, 90),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)

                # 3. Normalized Pinch Distance (Thumb Tip to Index Tip)
                pinch_dist = processor.normalized_distance(
                    hand, LandmarkIndex.THUMB_TIP, LandmarkIndex.INDEX_FINGER_TIP
                )
                pinch_text = f"Pinch Ratio: {pinch_dist:.2f}"
                is_pinching = pinch_dist < 0.25
                pinch_color = (0, 0, 255) if is_pinching else (0, 255, 0)
                if is_pinching:
                    pinch_text += " [PINCH ACTIVE]"

                cv2.putText(annotated_frame, pinch_text, (20, 115),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.50, pinch_color, 2, cv2.LINE_AA)

                # 4. Hand velocity
                vx, vy = processor.calculate_velocity(hand, current_time)
                cv2.putText(annotated_frame, f"Velocity: ({vx:.2f}, {vy:.2f})", (20, 138),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1, cv2.LINE_AA)

                # Highlight Index and Thumb tips with visual target rings
                thumb_px = hand.pixel_landmarks[LandmarkIndex.THUMB_TIP]
                index_px = hand.pixel_landmarks[LandmarkIndex.INDEX_FINGER_TIP]
                cv2.circle(annotated_frame, thumb_px, 8, pinch_color, -1)
                cv2.circle(annotated_frame, index_px, 8, pinch_color, -1)
                cv2.line(annotated_frame, thumb_px, index_px, pinch_color, 2)

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
        logger.info("Hand tracking diagnostic finished cleanly.")


if __name__ == "__main__":
    main()

