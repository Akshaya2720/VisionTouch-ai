"""Interactive Real-Time Webcam Test Script for VisionTouch AI.

Demonstrates:
- OpenCV frame acquisition via CameraManager.
- Real-time overlay of FPS, Resolution, and Camera status.
- Hardware release and clean exit handling.

Usage:
    python tests/run_camera_demo.py
Press 'q' or 'ESC' to exit.
"""

import sys
from pathlib import Path

# Add project root to sys.path so app modules import cleanly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import cv2
from app.camera.camera_manager import CameraManager
from app.config import config
from app.utils.logger import setup_logger

logger = setup_logger("CameraDemo")


def main() -> None:
    logger.info("Starting VisionTouch AI Camera Diagnostic...")
    cameras = CameraManager.list_available_cameras(max_probe=3)
    logger.info(f"Available camera devices found: {cameras}")

    if not cameras:
        logger.warning(
            "No active camera devices detected. Please check webcam connection or Windows privacy permissions."
        )

    camera = CameraManager(config.camera)
    if not camera.start():
        logger.error("Could not start camera. Exiting.")
        return

    window_name = "VisionTouch AI - Phase 1 Camera Feed Diagnostic"
    cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)

    logger.info("Camera stream running. Press 'q' or 'ESC' in the feed window to quit.")

    try:
        while camera.is_running:
            success, frame = camera.read_frame()
            if not success or frame is None:
                logger.warning("Frame read failed. Stream interrupted.")
                break

            # Mirror the frame horizontally so it acts like a natural mirror for user gestures
            display_frame = cv2.flip(frame, 1)

            # Draw HUD: Diagnostics Overlay
            fps_text = f"FPS: {camera.fps:.1f}"
            res_text = f"Res: {frame.shape[1]}x{frame.shape[0]}"
            status_text = "Status: CAMERA ACTIVE"

            # Background banner for text legibility
            cv2.rectangle(display_frame, (10, 10), (280, 100), (20, 20, 20), -1)
            cv2.rectangle(display_frame, (10, 10), (280, 100), (0, 255, 200), 1)

            cv2.putText(
                display_frame, fps_text, (20, 38),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2, cv2.LINE_AA
            )
            cv2.putText(
                display_frame, res_text, (20, 65),
                cv2.FONT_HERSHEY_SIMPLEX, 0.60, (255, 255, 255), 1, cv2.LINE_AA
            )
            cv2.putText(
                display_frame, status_text, (20, 90),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 200, 255), 1, cv2.LINE_AA
            )

            cv2.imshow(window_name, display_frame)

            # Wait 1 ms for key press: 27 is ESC, ord('q') is 'q'
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord('q'), ord('Q')):
                logger.info("User requested exit.")
                break

    except KeyboardInterrupt:
        logger.info("Interrupted by user terminal.")
    finally:
        camera.stop()
        cv2.destroyAllWindows()
        logger.info("Diagnostic completed and all hardware handles released.")


if __name__ == "__main__":
    main()

