"""Floating Desktop Overlays for VisionTouch AI.

Provides:
1. FloatingCursorOverlay: A transparent, click-through full-screen canvas that renders
   a glowing visual reticle following your finger across real Windows apps (Instagram,
   Chrome, YouTube, Desktop) without intercepting or blocking real mouse clicks.
2. FloatingCameraPiP: A compact, draggable, always-on-top Picture-in-Picture webcam view
   pinned to the top of your screen so you can always see your hand landmarks and gestures.
"""

from typing import Optional
from PySide6.QtCore import QPoint, QRect, QRectF, Qt, QTimer, Slot
from PySide6.QtGui import QBrush, QColor, QFont, QImage, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.gestures.gesture_types import GestureType


class FloatingCursorOverlay(QWidget):
    """Full-screen, transparent, click-through overlay showing a glowing cursor follower."""

    def __init__(self) -> None:
        super().__init__()
        # Essential Windows flags:
        # - WindowTransparentForInput: OS clicks pass straight through to Chrome/Instagram!
        # - WindowStaysOnTopHint: Floats above all desktop apps.
        # - FramelessWindowHint: No borders or titlebar.
        # - Tool: Doesn't clutter the Windows taskbar.
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint
            | Qt.FramelessWindowHint
            | Qt.WindowTransparentForInput
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)

        screen = QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())

        self.cursor_x: int = -100
        self.cursor_y: int = -100
        self.active_gesture: str = "NONE"
        self.pulse_radius: float = 14.0
        self._pulse_direction: float = 0.5

        # Animation timer for cursor glow
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._animate_pulse)
        self.anim_timer.start(16)  # ~60 FPS

    def update_position(self, screen_x: int, screen_y: int, gesture: str) -> None:
        """Updates cursor follower position and gesture state."""
        self.cursor_x = screen_x
        self.cursor_y = screen_y
        self.active_gesture = gesture
        self.update()

    def _animate_pulse(self) -> None:
        self.pulse_radius += self._pulse_direction
        if self.pulse_radius > 22.0 or self.pulse_radius < 14.0:
            self._pulse_direction *= -1
        self.update()

    def paintEvent(self, event) -> None:
        """Renders the glowing cursor follower over real desktop apps."""
        if self.cursor_x < 0 or self.cursor_y < 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        cx, cy = self.cursor_x, self.cursor_y

        # Determine visual style based on active gesture
        if self.active_gesture == "LEFT_CLICK_PINCH":
            outer_color = QColor(255, 30, 30, 180)  # Red pulse on left click
            inner_color = QColor(255, 60, 60, 240)
            status_text = "CLICK"
        elif self.active_gesture == "RIGHT_CLICK_PINCH":
            outer_color = QColor(255, 0, 255, 180)  # Magenta pulse on right click
            inner_color = QColor(255, 50, 255, 240)
            status_text = "MENU"
        elif self.active_gesture in ("SCROLL_UP", "SCROLL_DOWN"):
            outer_color = QColor(0, 220, 255, 180)  # Cyan on scroll
            inner_color = QColor(0, 240, 255, 240)
            status_text = "SCROLL"
        elif self.active_gesture == "CLOSED_FIST":
            outer_color = QColor(255, 100, 0, 200)  # Orange on pause
            inner_color = QColor(255, 50, 0, 240)
            status_text = "PAUSED"
        else:
            outer_color = QColor(0, 180, 255, 120)  # Sleek neon blue
            inner_color = QColor(0, 220, 255, 220)
            status_text = ""

        # 1. Outer animated glow ring
        painter.setPen(QPen(outer_color, 2.5))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QPoint(cx, cy), int(self.pulse_radius), int(self.pulse_radius))

        # 2. Inner solid core dot
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(inner_color))
        painter.drawEllipse(QPoint(cx, cy), 5, 5)

        # 3. Action badge text if clicking/scrolling
        if status_text:
            painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
            painter.setPen(QPen(QColor(255, 255, 255, 230)))
            painter.drawText(cx + 18, cy + 5, status_text)


class FloatingCameraPiP(QWidget):
    """Always-on-top, draggable, compact camera Picture-in-Picture window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("VisionTouch PiP")
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(260, 195)

        # Position at top-right of primary screen with margin
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.availableGeometry()
            self.move(geom.right() - 280, geom.top() + 30)

        self._drag_pos: Optional[QPoint] = None

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Container Frame with rounded borders and shadow styling
        self.container = QFrame()
        self.container.setStyleSheet(
            """
            QFrame {
                background-color: #1A1A1A;
                border: 2px solid #00b4d8;
                border-radius: 10px;
            }
            """
        )
        c_layout = QVBoxLayout(self.container)
        c_layout.setContentsMargins(4, 4, 4, 4)
        c_layout.setSpacing(4)

        # Top Drag Bar with Status and Close
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(6, 2, 6, 2)

        self.lbl_pip_title = QLabel("VisionTouch AI (Live)")
        self.lbl_pip_title.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.lbl_pip_title.setStyleSheet("color: #00b4d8; border: none;")
        top_bar.addWidget(self.lbl_pip_title)

        top_bar.addStretch()

        self.lbl_pip_gesture = QLabel("ACTIVE")
        self.lbl_pip_gesture.setFont(QFont("Segoe UI", 8, QFont.Bold))
        self.lbl_pip_gesture.setStyleSheet("color: #00FF00; border: none; padding-right: 6px;")
        top_bar.addWidget(self.lbl_pip_gesture)

        c_layout.addLayout(top_bar)

        # Video Display
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: #000; border-radius: 6px; border: none;")
        self.video_label.setFixedSize(250, 160)
        c_layout.addWidget(self.video_label)

        layout.addWidget(self.container)

    @Slot(QImage)
    def update_frame(self, q_img: QImage) -> None:
        """Renders live camera frames into the compact PiP box."""
        pixmap = QPixmap.fromImage(q_img)
        scaled = pixmap.scaled(
            self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.video_label.setPixmap(scaled)

    def update_gesture_status(self, gesture_name: str, state_name: str) -> None:
        """Updates the status pill in the PiP header."""
        if state_name == "PAUSED":
            self.lbl_pip_gesture.setText("PAUSED")
            self.lbl_pip_gesture.setStyleSheet("color: #FF3333; border: none;")
        elif state_name == "STANDBY":
            self.lbl_pip_gesture.setText("STANDBY")
            self.lbl_pip_gesture.setStyleSheet("color: #FFA500; border: none;")
        else:
            self.lbl_pip_gesture.setText(gesture_name)
            self.lbl_pip_gesture.setStyleSheet("color: #00FF00; border: none;")

    # Enable mouse dragging of PiP window anywhere on screen
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

