"""Background QThread Worker for Computer Vision and Gesture Processing.

Ensures the PySide6 UI remains at a smooth 60 FPS without ever freezing
or blocking during video frame capture or ML inference.
"""

import time
import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

from app.camera.camera_manager import CameraManager
from app.config import config
from app.core.action_manager import ActionManager
from app.core.state_manager import AppState, StateManager
from app.gestures.gesture_recognizer import GestureRecognizer
from app.gestures.gesture_types import GestureType
from app.utils.logger import setup_logger
from app.vision.hand_detector import HandDetector

logger = setup_logger("CameraWorker")


class CameraWorker(QThread):
    """Asynchronous worker executing the perception and automation pipeline."""

    # Qt Signals emitted to UI
    frame_ready = Signal(QImage)
    gesture_detected = Signal(str, str, float)  # gesture_name, action_name, fps
    hand_count_changed = Signal(int)
    state_changed = Signal(str)

    def __init__(
        self,
        camera: CameraManager,
        detector: HandDetector,
        recognizer: GestureRecognizer,
        action_manager: ActionManager,
        state_manager: StateManager,
    ) -> None:
        super().__init__()
        self.camera = camera
        self.detector = detector
        self.recognizer = recognizer
        self.action_manager = action_manager
        self.state_manager = state_manager
        self._running = False

    def run(self) -> None:
        """Main execution loop running inside a dedicated background thread."""
        self._running = True
        logger.info("CameraWorker thread started.")

        if not self.camera.is_running:
            if not self.camera.start():
                logger.error("Failed to start camera in worker thread.")
                self._running = False
                return

        while self._running:
            success, frame = self.camera.read_frame()
            if not success or frame is None:
                time.sleep(0.01)
                continue

            # Mirror frame horizontally for user interaction
            frame = cv2.flip(frame, 1)
            h, w, c = frame.shape

            # Run MediaPipe hand tracking (drawing landmarks on preview)
            hands, annotated = self.detector.process_frame(frame, draw=True)
            self.hand_count_changed.emit(len(hands))

            # Recognize Gestures
            now = time.perf_counter()
            recognized = self.recognizer.recognize(hands, now)

            primary = recognized[0] if recognized else None
            active_gesture_name = primary.gesture.name if primary else "NONE"
            dispatched_action = "none"

            # Dispatch action to OS
            if primary and primary.gesture != GestureType.NONE:
                action = self.action_manager.dispatch(primary)
                dispatched_action = action or "none"

            self.gesture_detected.emit(
                active_gesture_name, dispatched_action, self.camera.fps
            )
            self.state_changed.emit(self.state_manager.state.name)

            # Convert BGR frame to QImage for smooth PySide6 rendering
            rgb_frame = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
            bytes_per_line = c * w
            q_img = QImage(
                rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888
            ).copy()  # Deep copy to ensure thread safety

            self.frame_ready.emit(q_img)

        self.camera.stop()
        logger.info("CameraWorker thread stopped cleanly.")

    def stop(self) -> None:
        """Stops the background execution thread safely."""
        self._running = False
        self.wait(1000)
