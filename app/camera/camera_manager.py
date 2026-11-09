"""Webcam Management Module for VisionTouch AI.

Responsible for:
- Hardware camera enumeration and selection.
- Video stream initialization with DirectShow (Windows-optimized backend).
- Non-blocking frame capture.
- FPS tracking and performance instrumentation.
- Safe resource acquisition and release (RAII pattern).
"""

import time
from typing import List, Optional, Tuple
import cv2
import numpy as np

from app.config import CameraConfig
from app.utils.logger import setup_logger

logger = setup_logger("CameraManager")


class CameraManager:
    """Manages webcam capture lifecycle, settings, and hardware communication."""

    def __init__(self, config: Optional[CameraConfig] = None) -> None:
        """Initializes the camera manager with the given configuration.

        Args:
            config: CameraConfig dataclass containing resolution, FPS, and device index.
        """
        self.config = config or CameraConfig()
        self.camera_index: int = self.config.default_camera_index
        self._cap: Optional[cv2.VideoCapture] = None
        self._is_running: bool = False

        # Real-time performance metrics
        self._prev_frame_time: float = 0.0
        self._fps: float = 0.0
        self._frame_count: int = 0
        self._start_time: float = 0.0

    @property
    def is_running(self) -> bool:
        """Returns True if the camera stream is currently active."""
        return self._is_running and self._cap is not None and self._cap.isOpened()

    @property
    def fps(self) -> float:
        """Returns the current real-time frames per second (FPS)."""
        return self._fps

    @staticmethod
    def list_available_cameras(max_probe: int = 4) -> List[int]:
        """Probes video capture indices to enumerate physically accessible cameras.

        On Windows, cv2.CAP_DSHOW (DirectShow) is used to avoid long timeout delays
        associated with Microsoft Media Foundation (MSMF) probing.

        Args:
            max_probe: Maximum number of device indices to probe.

        Returns:
            List of accessible integer camera indices (e.g. [0, 1]).
        """
        available = []
        for index in range(max_probe):
            cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    available.append(index)
                cap.release()
        logger.info(f"Detected accessible camera indices: {available}")
        return available

    def start(self, camera_index: Optional[int] = None) -> bool:
        """Initializes and opens the camera stream.

        Args:
            camera_index: Optional camera device index. If None, uses default from config.

        Returns:
            True if camera successfully opened and ready, False otherwise.
        """
        if self.is_running:
            logger.warning("Camera is already active. Stop current stream first.")
            return True

        if camera_index is not None:
            self.camera_index = camera_index

        logger.info(
            f"Opening camera index {self.camera_index} "
            f"({self.config.frame_width}x{self.config.frame_height} @ {self.config.target_fps} FPS)..."
        )

        # cv2.CAP_DSHOW is significantly faster on Windows 10/11
        self._cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not self._cap.isOpened():
            logger.info("DirectShow open failed, trying default media backend...")
            self._cap = cv2.VideoCapture(self.camera_index)

        # If primary index fails, automatically fallback to other accessible camera indices
        if not self._cap.isOpened():
            available = self.list_available_cameras(max_probe=self.config.max_cameras_to_probe)
            for idx in available:
                if idx != self.camera_index:
                    logger.info(f"Retrying camera open on detected device index {idx}...")
                    self._cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
                    if self._cap.isOpened():
                        self.camera_index = idx
                        break

        if not self._cap.isOpened():
            logger.error(
                f"Failed to open camera at index {self.camera_index}. "
                "Check camera permissions or verify device connection."
            )
            self._cap = None
            self._is_running = False
            return False

        # Set hardware properties
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.frame_width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.frame_height)
        self._cap.set(cv2.CAP_PROP_FPS, self.config.target_fps)

        # OpenCV may adjust to the closest hardware-supported resolution
        actual_w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = self._cap.get(cv2.CAP_PROP_FPS)
        logger.info(
            f"Camera initialized successfully. Actual stream settings: "
            f"{actual_w}x{actual_h} @ {actual_fps:.1f} FPS"
        )

        self._is_running = True
        self._prev_frame_time = time.perf_counter()
        self._start_time = time.perf_counter()
        self._frame_count = 0
        return True

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Captures a single raw video frame from the active stream.

        Returns:
            Tuple of (success_flag, frame_as_numpy_bgr_array).
            If success_flag is False, frame is None.
        """
        if not self.is_running or self._cap is None:
            return False, None

        ret, frame = self._cap.read()
        if not ret or frame is None:
            logger.warning("Camera dropped a frame or was disconnected.")
            return False, None

        # Calculate instantaneous FPS with moving average smoothing
        current_time = time.perf_counter()
        dt = current_time - self._prev_frame_time
        self._prev_frame_time = current_time

        if dt > 0:
            instant_fps = 1.0 / dt
            # Exponential moving average (alpha=0.2) to smooth jitter
            self._fps = 0.2 * instant_fps + 0.8 * self._fps if self._fps > 0 else instant_fps

        self._frame_count += 1
        return True, frame

    def stop(self) -> None:
        """Gracefully stops camera stream and releases the hardware resource."""
        if self._cap is not None:
            logger.info("Releasing camera hardware handle...")
            self._cap.release()
            self._cap = None

        self._is_running = False
        self._fps = 0.0
        logger.info("Camera stopped successfully.")

    def __enter__(self) -> "CameraManager":
        """Context manager support: starts camera on entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager support: ensures camera is always released on exit."""
        self.stop()

    def __del__(self) -> None:
        """Garbage collection safeguard: ensures underlying OS handle is freed."""
        self.stop()

