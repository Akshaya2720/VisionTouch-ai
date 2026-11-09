"""VisionTouch AI: Lightweight Floating Camera & Gesture Companion.

A zero-clutter, distraction-free desktop companion:
- Floats as a sleek, draggable mini camera widget on the right side of your screen.
- Displays live hand tracking, digital clock time, active gesture, and FPS.
- 100% Touchpad Safe: Zero full-screen overlays, completely prevents touchpad interference.
- By default, runs in 'Touchpad Safe: Scroll Mode' so you can freely use your touchpad
  to click and navigate, while using hand gestures to scroll Instagram/YouTube and control media.
"""

from datetime import datetime
import sys
import time
from typing import Optional

from PySide6.QtCore import QPoint, Qt, QTimer, Slot
from PySide6.QtGui import QFont, QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.camera.camera_manager import CameraManager
from app.config import config
from app.controllers.keyboard_controller import KeyboardController
from app.controllers.media_controller import MediaController
from app.controllers.mouse_controller import MouseController
from app.controllers.scroll_controller import ScrollController
from app.core.action_manager import ActionManager
from app.core.state_manager import StateManager
from app.database.db_manager import DatabaseManager
from app.gestures.gesture_recognizer import GestureRecognizer
from app.ui.camera_worker import CameraWorker
from app.utils.logger import setup_logger
from app.vision.hand_detector import HandDetector

logger = setup_logger("MiniApp")


class DraggableMiniCamera(QWidget):
    """Sleek, draggable, always-on-top mini camera window on the right side of the screen."""

    def __init__(
        self,
        on_mode_toggle_callback=None,
        on_close_callback=None,
    ) -> None:
        super().__init__()
        self.on_mode_toggle_callback = on_mode_toggle_callback
        self.on_close_callback = on_close_callback
        self.setWindowTitle("VisionTouch Mini")

        # Always-on-top, frameless floating tool window (only covers its own 260x235 footprint)
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(260, 235)

        # Position on the right side of the screen
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.availableGeometry()
            self.move(geom.right() - 280, geom.top() + (geom.height() // 4))

        self._drag_pos: Optional[QPoint] = None
        self._mouse_control_enabled: bool = False

        self._init_ui()

        # Digital Clock timer
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start(1000)

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Card container
        self.container = QFrame()
        self.container.setStyleSheet(
            """
            QFrame {
                background-color: #141414;
                border: 2px solid #00b4d8;
                border-radius: 12px;
            }
            """
        )
        c_layout = QVBoxLayout(self.container)
        c_layout.setContentsMargins(8, 8, 8, 8)
        c_layout.setSpacing(6)

        # Top Bar: Digital Clock, Gesture Badge, Close Button
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(4, 0, 4, 0)

        # Digital Clock
        self.lbl_clock = QLabel(datetime.now().strftime("%I:%M %p"))
        self.lbl_clock.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.lbl_clock.setStyleSheet("color: #FFFFFF; border: none;")
        top_bar.addWidget(self.lbl_clock)

        top_bar.addStretch()

        # Gesture Badge
        self.lbl_gesture = QLabel("READY")
        self.lbl_gesture.setFont(QFont("Segoe UI", 8, QFont.Bold))
        self.lbl_gesture.setStyleSheet(
            "background-color: #0078D4; color: #FFFFFF; border: none; border-radius: 4px; padding: 2px 6px;"
        )
        top_bar.addWidget(self.lbl_gesture)

        # Close button
        btn_close = QPushButton("✕")
        btn_close.setFixedSize(20, 20)
        btn_close.setFont(QFont("Segoe UI", 9, QFont.Bold))
        btn_close.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                color: #888888;
                border: none;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #FF4444;
            }
            """
        )
        btn_close.clicked.connect(self._on_close_clicked)
        top_bar.addWidget(btn_close)

        c_layout.addLayout(top_bar)

        # Live Camera Display
        self.video_display = QLabel()
        self.video_display.setAlignment(Qt.AlignCenter)
        self.video_display.setFixedSize(240, 150)
        self.video_display.setStyleSheet(
            "background-color: #000000; border-radius: 8px; border: 1px solid #222;"
        )
        c_layout.addWidget(self.video_display)

        # Mode Button (Touchpad Safe vs Full Mouse)
        self.btn_mode = QPushButton("🛡️ Touchpad Safe: Scroll Mode")
        self.btn_mode.setFixedHeight(24)
        self.btn_mode.setFont(QFont("Segoe UI", 8, QFont.Bold))
        self.btn_mode.setStyleSheet(
            """
            QPushButton {
                background-color: #1A3026;
                color: #00FF88;
                border: 1px solid #00AA55;
                border-radius: 4px;
                padding: 2px 6px;
            }
            QPushButton:hover {
                background-color: #224433;
            }
            """
        )
        self.btn_mode.clicked.connect(self._toggle_mode)
        c_layout.addWidget(self.btn_mode)

        main_layout.addWidget(self.container)

    def _toggle_mode(self) -> None:
        self._mouse_control_enabled = not self._mouse_control_enabled
        if self._mouse_control_enabled:
            self.btn_mode.setText("🖱️ Hand Mouse Mode (Active)")
            self.btn_mode.setStyleSheet(
                """
                QPushButton {
                    background-color: #1A2840;
                    color: #00AAFF;
                    border: 1px solid #0078D4;
                    border-radius: 4px;
                    padding: 2px 6px;
                }
                QPushButton:hover {
                    background-color: #223555;
                }
                """
            )
        else:
            self.btn_mode.setText("🛡️ Touchpad Safe: Scroll Mode")
            self.btn_mode.setStyleSheet(
                """
                QPushButton {
                    background-color: #1A3026;
                    color: #00FF88;
                    border: 1px solid #00AA55;
                    border-radius: 4px;
                    padding: 2px 6px;
                }
                QPushButton:hover {
                    background-color: #224433;
                }
                """
            )
        if self.on_mode_toggle_callback:
            self.on_mode_toggle_callback(self._mouse_control_enabled)

    def _update_clock(self) -> None:
        self.lbl_clock.setText(datetime.now().strftime("%I:%M %p"))

    @Slot(QImage)
    def update_frame(self, q_img: QImage) -> None:
        """Renders the live webcam stream."""
        pixmap = QPixmap.fromImage(q_img)
        scaled = pixmap.scaled(
            self.video_display.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.video_display.setPixmap(scaled)

    def update_gesture_status(self, gesture_name: str, state_name: str) -> None:
        """Updates gesture badge color and text."""
        if state_name == "PAUSED":
            self.lbl_gesture.setText("PAUSED")
            self.lbl_gesture.setStyleSheet(
                "background-color: #CC0000; color: #FFF; border: none; border-radius: 4px; padding: 2px 6px;"
            )
        elif state_name == "STANDBY":
            self.lbl_gesture.setText("STANDBY")
            self.lbl_gesture.setStyleSheet(
                "background-color: #DD8800; color: #FFF; border: none; border-radius: 4px; padding: 2px 6px;"
            )
        else:
            clean_name = gesture_name.replace("_PINCH", "").replace("_MOVE", "")
            self.lbl_gesture.setText(clean_name if clean_name != "NONE" else "ACTIVE")
            self.lbl_gesture.setStyleSheet(
                "background-color: #008855; color: #FFF; border: none; border-radius: 4px; padding: 2px 6px;"
            )

    # Enable smooth dragging anywhere on the screen
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def _on_close_clicked(self) -> None:
        if self.on_close_callback:
            self.on_close_callback()
        self.close()


class VisionTouchMiniApp:
    """Master controller for the minimal, touchpad-safe touchless companion."""

    def __init__(self) -> None:
        self.db = DatabaseManager()
        self.state_manager = StateManager()

        self.camera = CameraManager(config.camera)
        self.detector = HandDetector(config.vision)
        self.recognizer = GestureRecognizer()

        self.mouse = MouseController()
        self.scroller = ScrollController()
        self.media = MediaController()
        self.keyboard = KeyboardController()

        self.action_manager = ActionManager(
            self.db, self.state_manager, self.mouse, self.scroller, self.media, self.keyboard
        )

        # By default, keep mouse cursor automation disabled so touchpad is 100% untouched!
        self.action_manager.set_mouse_control(False)

        # UI Component: ONLY the small draggable camera (zero full-screen overlays)
        self.mini_camera = DraggableMiniCamera(
            on_mode_toggle_callback=self._on_mode_toggled,
            on_close_callback=self.stop,
        )

        # Worker thread
        self.worker = CameraWorker(
            self.camera, self.detector, self.recognizer, self.action_manager, self.state_manager
        )

        # Connect signals
        self.worker.frame_ready.connect(self.mini_camera.update_frame)
        self.worker.gesture_detected.connect(self._on_gesture)

    def _on_mode_toggled(self, enable_mouse: bool) -> None:
        """Toggles between Touchpad-Safe Scroll mode and Full Mouse mode."""
        self.action_manager.set_mouse_control(enable_mouse)

    def _on_gesture(self, gesture_name: str, action_name: str, fps: float) -> None:
        self.mini_camera.update_gesture_status(gesture_name, self.state_manager.state.name)

    def start(self) -> None:
        """Starts the minimal floating companion."""
        logger.info("Starting VisionTouch AI Touchpad-Safe Companion...")
        self.mouse.reset()
        self.mini_camera.show()
        self.worker.start()

    def stop(self) -> None:
        """Stops worker and releases all hardware buttons."""
        logger.info("Stopping VisionTouch AI Mini Companion...")
        if self.worker:
            self.worker.stop()
        self.mouse.reset()
        self.detector.close()
        QApplication.quit()
