"""Configuration settings for VisionTouch AI.

This module centralizes all configurable parameters including camera settings,
performance budgets, gesture thresholds, and UI theme constants.
"""

from dataclasses import dataclass
from pathlib import Path

# Base paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_DIR = PROJECT_ROOT / "app"
ASSETS_DIR = PROJECT_ROOT / "assets"
DOCS_DIR = PROJECT_ROOT / "docs"
DATABASE_PATH = PROJECT_ROOT / "visiontouch.db"


@dataclass(frozen=True)
class CameraConfig:
    """Camera hardware and capture configuration.

    Default resolution is kept at 640x480 (VGA) rather than 1080p/720p:
    1. MediaPipe works on internal cropped tensors (usually 224x224 or 256x256).
    2. 640x480 reduces memory copy overhead and bus bandwidth on low-end hardware.
    3. Provides steady 30-60 FPS on laptops with integrated Intel HD/Iris GPUs.
    """
    default_camera_index: int = 0
    frame_width: int = 640
    frame_height: int = 480
    target_fps: int = 30
    auto_detect_cameras: bool = True
    max_cameras_to_probe: int = 4


@dataclass(frozen=True)
class VisionConfig:
    """MediaPipe hand tracking hyperparameters."""
    max_num_hands: int = 2
    min_detection_confidence: float = 0.70
    min_tracking_confidence: float = 0.60
    model_complexity: int = 0  # 0: Lite (fastest, ideal for i3), 1: Full


@dataclass(frozen=True)
class AppConfig:
    """Master application configuration."""
    app_name: str = "VisionTouch AI"
    version: str = "1.0.0"
    camera: CameraConfig = CameraConfig()
    vision: VisionConfig = VisionConfig()


# Global config singleton
config = AppConfig()

