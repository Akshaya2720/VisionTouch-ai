"""Main Desktop Dashboard Application for VisionTouch AI built with PySide6.

Features:
- Modern minimal black/white/subtle-blue dark theme.
- 10 comprehensive pages (Onboarding, Dashboard, Camera, Gestures, Customization, Profiles, Settings, Instructions, Privacy, About).
- Thread-safe non-blocking QThread camera pipeline.
- SQLite-backed settings and profile switching.
"""

import sys
from typing import Dict, Optional
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont, QIcon, QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSlider,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
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
from app.core.state_manager import AppState, StateManager
from app.database.db_manager import DatabaseManager
from app.gestures.gesture_recognizer import GestureRecognizer
from app.ui.camera_worker import CameraWorker
from app.utils.logger import setup_logger
from app.vision.hand_detector import HandDetector

logger = setup_logger("Dashboard")

DARK_STYLE = """
QMainWindow {
    background-color: #121212;
}
QWidget {
    background-color: #121212;
    color: #E0E0E0;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    font-size: 13px;
}
QFrame.card {
    background-color: #1E1E1E;
    border: 1px solid #2D2D2D;
    border-radius: 8px;
    padding: 16px;
}
QPushButton {
    background-color: #2D2D2D;
    color: #FFFFFF;
    border: 1px solid #3D3D3D;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #0078D4;
    border-color: #0078D4;
}
QPushButton.primary {
    background-color: #0078D4;
    border: 1px solid #005A9E;
}
QPushButton.primary:hover {
    background-color: #108CEB;
}
QPushButton.danger {
    background-color: #D13438;
    border: 1px solid #A80000;
}
QPushButton.danger:hover {
    background-color: #E81123;
}
QPushButton.nav-btn {
    text-align: left;
    padding: 10px 14px;
    border-radius: 6px;
    background-color: transparent;
    border: none;
    font-size: 13px;
}
QPushButton.nav-btn:hover {
    background-color: #1F1F1F;
    color: #0078D4;
}
QPushButton.nav-btn:checked {
    background-color: #262626;
    color: #00b4d8;
    font-weight: bold;
    border-left: 3px solid #00b4d8;
}
QSlider::groove:horizontal {
    height: 6px;
    background: #2D2D2D;
    border-radius: 3px;
}
QSlider::sub-page:horizontal {
    background: #0078D4;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #FFFFFF;
    width: 16px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 8px;
}
QComboBox {
    background-color: #1E1E1E;
    border: 1px solid #3D3D3D;
    border-radius: 6px;
    padding: 6px 12px;
    color: #FFFFFF;
}
QTableWidget {
    background-color: #181818;
    border: 1px solid #2D2D2D;
    border-radius: 6px;
    gridline-color: #2D2D2D;
}
QHeaderView::section {
    background-color: #222222;
    color: #FFFFFF;
    padding: 6px;
    border: 1px solid #2D2D2D;
    font-weight: bold;
}
"""


class MainWindow(QMainWindow):
    """Main Application Window housing the 10-page navigation architecture."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("VisionTouch AI - Touchless Laptop Control")
        self.resize(1150, 750)
        self.setStyleSheet(DARK_STYLE)

        # Initialize subsystems
        self.db = DatabaseManager()
        self.settings = self.db.get_settings()
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

        # Setup background worker
        self.worker: Optional[CameraWorker] = None

        self._init_ui()
        self._start_worker()

    def _init_ui(self) -> None:
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Left Sidebar Navigation
        sidebar = QFrame()
        sidebar.setFixedWidth(230)
        sidebar.setStyleSheet("background-color: #161616; border-right: 1px solid #222222;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 16, 12, 16)
        sidebar_layout.setSpacing(4)

        # App Brand Header
        brand_label = QLabel("VisionTouch AI")
        brand_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        brand_label.setStyleSheet("color: #00b4d8; padding-bottom: 4px;")
        sidebar_layout.addWidget(brand_label)

        sub_label = QLabel("Touchless OS Control")
        sub_label.setFont(QFont("Segoe UI", 9))
        sub_label.setStyleSheet("color: #888888; padding-bottom: 16px;")
        sidebar_layout.addWidget(sub_label)

        # Navigation Buttons (10 Pages)
        self.nav_buttons = []
        nav_items = [
            ("🏠 Welcome / Onboarding", 0),
            ("📊 Main Dashboard", 1),
            ("📷 Camera Preview", 2),
            ("🖐️ Gesture Controls", 3),
            ("⚙️ Gesture Customization", 4),
            ("📁 Application Profiles", 5),
            ("🎛️ Sensitivity Settings", 6),
            ("📖 Usage Instructions", 7),
            ("🔒 Privacy & Permissions", 8),
            ("ℹ️ About", 9),
        ]

        self.pages = QStackedWidget()

        for title, index in nav_items:
            btn = QPushButton(title)
            btn.setProperty("class", "nav-btn")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, idx=index: self._switch_page(idx))
            sidebar_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        sidebar_layout.addStretch()

        # Engine Quick-Toggle in Sidebar
        self.sidebar_toggle_btn = QPushButton("Stop Engine")
        self.sidebar_toggle_btn.setProperty("class", "danger")
        self.sidebar_toggle_btn.clicked.connect(self._toggle_engine)
        sidebar_layout.addWidget(self.sidebar_toggle_btn)

        main_layout.addWidget(sidebar)

        # 2. Build 10 Pages into QStackedWidget
        self._build_page_welcome()
        self._build_page_dashboard()
        self._build_page_camera()
        self._build_page_gesture_panel()
        self._build_page_customization()
        self._build_page_profiles()
        self._build_page_settings()
        self._build_page_instructions()
        self._build_page_privacy()
        self._build_page_about()

        main_layout.addWidget(self.pages)

        # Activate Main Dashboard by default
        self._switch_page(1)

    def _switch_page(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

    # ---------------- PAGE BUILDERS ---------------- #

    def _build_page_welcome(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)

        card = QFrame()
        card.setProperty("class", "card")
        card_layout = QVBoxLayout(card)

        title = QLabel("Welcome to VisionTouch AI")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title.setStyleSheet("color: #00b4d8;")
        card_layout.addWidget(title)

        desc = QLabel(
            "Experience next-generation touchless laptop control.\n\n"
            "• Natural 21-point hand tracking with edge-computed machine learning.\n"
            "• Control your entire Windows desktop without touching keyboard, mouse, or screen.\n"
            "• 100% private, offline, and secure — no video ever leaves your machine.\n"
            "• Optimized for smooth real-time performance on Intel Core i3 and higher."
        )
        desc.setFont(QFont("Segoe UI", 12))
        desc.setStyleSheet("color: #CCCCCC; line-height: 1.6;")
        card_layout.addWidget(desc)

        card_layout.addSpacing(20)
        start_btn = QPushButton("Go to Dashboard ➔")
        start_btn.setProperty("class", "primary")
        start_btn.setFixedWidth(200)
        start_btn.clicked.connect(lambda: self._switch_page(1))
        card_layout.addWidget(start_btn)

        layout.addWidget(card)
        layout.addStretch()
        self.pages.addWidget(page)

    def _build_page_dashboard(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Header Banner
        header = QLabel("System Dashboard")
        header.setFont(QFont("Segoe UI", 18, QFont.Bold))
        layout.addWidget(header)

        # Metrics Grid Cards
        metrics_layout = QHBoxLayout()

        # 1. Camera Card
        self.cam_status_card = QFrame()
        self.cam_status_card.setProperty("class", "card")
        c1 = QVBoxLayout(self.cam_status_card)
        c1.addWidget(QLabel("CAMERA STATUS"))
        self.lbl_cam_status = QLabel("ACTIVE")
        self.lbl_cam_status.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.lbl_cam_status.setStyleSheet("color: #00FF00;")
        c1.addWidget(self.lbl_cam_status)
        metrics_layout.addWidget(self.cam_status_card)

        # 2. Mode Card
        self.mode_card = QFrame()
        self.mode_card.setProperty("class", "card")
        c2 = QVBoxLayout(self.mode_card)
        c2.addWidget(QLabel("CONTROL MODE"))
        self.lbl_mode = QLabel("ACTIVE")
        self.lbl_mode.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.lbl_mode.setStyleSheet("color: #00b4d8;")
        c2.addWidget(self.lbl_mode)
        metrics_layout.addWidget(self.mode_card)

        # 3. Gesture Card
        self.gesture_card = QFrame()
        self.gesture_card.setProperty("class", "card")
        c3 = QVBoxLayout(self.gesture_card)
        c3.addWidget(QLabel("CURRENT GESTURE"))
        self.lbl_gesture = QLabel("NONE")
        self.lbl_gesture.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.lbl_gesture.setStyleSheet("color: #FFD700;")
        c3.addWidget(self.lbl_gesture)
        metrics_layout.addWidget(self.gesture_card)

        # 4. FPS Card
        self.fps_card = QFrame()
        self.fps_card.setProperty("class", "card")
        c4 = QVBoxLayout(self.fps_card)
        c4.addWidget(QLabel("PERFORMANCE"))
        self.lbl_fps = QLabel("30.0 FPS")
        self.lbl_fps.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.lbl_fps.setStyleSheet("color: #FFFFFF;")
        c4.addWidget(self.lbl_fps)
        metrics_layout.addWidget(self.fps_card)

        layout.addLayout(metrics_layout)

        # Active Profile & Action Information
        info_card = QFrame()
        info_card.setProperty("class", "card")
        info_layout = QVBoxLayout(info_card)

        profile_row = QHBoxLayout()
        profile_row.addWidget(QLabel("Active Profile:"))
        self.combo_profile_dash = QComboBox()
        self.combo_profile_dash.addItems(self.db.get_profiles())
        self.combo_profile_dash.setCurrentText(self.action_manager.active_profile)
        self.combo_profile_dash.currentTextChanged.connect(self._on_profile_changed)
        profile_row.addWidget(self.combo_profile_dash)
        profile_row.addStretch()
        info_layout.addLayout(profile_row)

        self.lbl_last_action = QLabel("Dispatched OS Action: None")
        self.lbl_last_action.setStyleSheet("color: #AAAAAA; padding-top: 8px;")
        info_layout.addWidget(self.lbl_last_action)

        layout.addWidget(info_card)
        layout.addStretch()
        self.pages.addWidget(page)

    def _build_page_camera(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)

        header = QLabel("Live Camera Preview")
        header.setFont(QFont("Segoe UI", 16, QFont.Bold))
        layout.addWidget(header)

        self.video_display = QLabel("Camera Stream Loading...")
        self.video_display.setAlignment(Qt.AlignCenter)
        self.video_display.setMinimumSize(640, 480)
        self.video_display.setStyleSheet("background-color: #000000; border-radius: 8px; border: 1px solid #333;")
        layout.addWidget(self.video_display)

        self.pages.addWidget(page)

    def _build_page_gesture_panel(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)

        header = QLabel("Gesture Control Panel")
        header.setFont(QFont("Segoe UI", 16, QFont.Bold))
        layout.addWidget(header)

        table = QTableWidget(10, 3)
        table.setHorizontalHeaderLabels(["Gesture Name", "Standard Action", "Status"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        gestures_data = [
            ("Index Extended", "Move Desktop Cursor", "Active"),
            ("Thumb-Index Pinch", "Left Mouse Click", "Active"),
            ("Thumb-Middle Pinch", "Right Mouse Click", "Active"),
            ("Two Fingers Up", "Scroll Mode Activated", "Active"),
            ("Vertical Hand Shift", "Continuous Scroll Up / Down", "Active"),
            ("Closed Fist", "Emergency Pause / Freeze", "Active"),
            ("Open Palm (5 Fingers)", "Toggle Standby / Active", "Active"),
            ("Swipe Left", "Previous Browser Tab / Slide", "Active"),
            ("Swipe Right", "Next Browser Tab / Slide", "Active"),
            ("Two-Hand Pinch", "Zoom In / Zoom Out", "Active"),
        ]

        for row, (g, a, s) in enumerate(gestures_data):
            table.setItem(row, 0, QTableWidgetItem(g))
            table.setItem(row, 1, QTableWidgetItem(a))
            item_s = QTableWidgetItem(s)
            item_s.setForeground(Qt.green)
            table.setItem(row, 2, item_s)

        layout.addWidget(table)
        self.pages.addWidget(page)

    def _build_page_customization(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)

        header = QLabel("Gesture Customization")
        header.setFont(QFont("Segoe UI", 16, QFont.Bold))
        layout.addWidget(header)

        card = QFrame()
        card.setProperty("class", "card")
        cl = QVBoxLayout(card)

        cl.addWidget(QLabel("Customize gesture bindings for current profile and save to local SQLite database:"))

        self.table_custom = QTableWidget(10, 3)
        self.table_custom.setHorizontalHeaderLabels(["Gesture", "Assigned Action", "Enabled"])
        self.table_custom.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._load_custom_mappings()

        cl.addWidget(self.table_custom)

        save_btn = QPushButton("Save Mappings to Database")
        save_btn.setProperty("class", "primary")
        save_btn.clicked.connect(self._save_custom_mappings)
        cl.addWidget(save_btn)

        layout.addWidget(card)
        self.pages.addWidget(page)

    def _build_page_profiles(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)

        header = QLabel("Application Profiles")
        header.setFont(QFont("Segoe UI", 16, QFont.Bold))
        layout.addWidget(header)

        card = QFrame()
        card.setProperty("class", "card")
        cl = QVBoxLayout(card)

        cl.addWidget(QLabel("Select an application profile for tailored gesture interactions:"))

        profiles = ["Default", "YouTube", "Instagram", "PowerPoint", "VLC"]
        for p in profiles:
            btn = QPushButton(f"Switch to '{p}' Profile")
            btn.clicked.connect(lambda checked, name=p: self._on_profile_changed(name))
            cl.addWidget(btn)

        layout.addWidget(card)
        layout.addStretch()
        self.pages.addWidget(page)

    def _build_page_settings(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)

        header = QLabel("Sensitivity & Hardware Calibration")
        header.setFont(QFont("Segoe UI", 16, QFont.Bold))
        layout.addWidget(header)

        card = QFrame()
        card.setProperty("class", "card")
        cl = QVBoxLayout(card)

        # Cursor Sensitivity Slider
        cl.addWidget(QLabel("Cursor Speed Multiplier:"))
        self.slider_cursor = QSlider(Qt.Horizontal)
        self.slider_cursor.setRange(20, 300)
        self.slider_cursor.setValue(int(self.settings.cursor_sensitivity * 100))
        self.slider_cursor.valueChanged.connect(self._on_sensitivity_slider_changed)
        cl.addWidget(self.slider_cursor)

        # Scroll Sensitivity Slider
        cl.addWidget(QLabel("Scroll Speed Multiplier:"))
        self.slider_scroll = QSlider(Qt.Horizontal)
        self.slider_scroll.setRange(5, 50)
        self.slider_scroll.setValue(int(self.scroller.base_speed))
        self.slider_scroll.valueChanged.connect(self._on_scroll_slider_changed)
        cl.addWidget(self.slider_scroll)

        layout.addWidget(card)
        layout.addStretch()
        self.pages.addWidget(page)

    def _build_page_instructions(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)

        header = QLabel("Usage Instructions & Tutorial")
        header.setFont(QFont("Segoe UI", 16, QFont.Bold))
        layout.addWidget(header)

        card = QFrame()
        card.setProperty("class", "card")
        cl = QVBoxLayout(card)

        text = QLabel(
            "1. Positioning: Sit comfortably 40 to 80 cm from the laptop webcam in well-lit conditions.\n\n"
            "2. Moving Cursor: Extend only your Index finger. Move your hand within the center active control zone.\n\n"
            "3. Left Click: Pinch your Thumb tip and Index finger tip together firmly.\n\n"
            "4. Right Click: Pinch your Thumb tip and Middle finger tip together.\n\n"
            "5. Scrolling: Raise both Index and Middle fingers upright. Move hand upward to scroll up, downward to scroll down.\n\n"
            "6. Swipe Navigation: Rapidly wave your hand left or right to switch browser tabs.\n\n"
            "7. Emergency Stop: Make a closed fist to instantly freeze cursor and halt automation."
        )
        text.setFont(QFont("Segoe UI", 11))
        text.setStyleSheet("color: #DDDDDD; line-height: 1.6;")
        cl.addWidget(text)

        layout.addWidget(card)
        layout.addStretch()
        self.pages.addWidget(page)

    def _build_page_privacy(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)

        header = QLabel("Privacy & Security Architecture")
        header.setFont(QFont("Segoe UI", 16, QFont.Bold))
        layout.addWidget(header)

        card = QFrame()
        card.setProperty("class", "card")
        cl = QVBoxLayout(card)

        info = QLabel(
            "🔒 100% On-Device Processing:\n"
            "VisionTouch AI processes all camera frames strictly in local RAM. No frames, landmarks, "
            "or audio are ever saved to disk, recorded, or transmitted across the internet.\n\n"
            "🛡️ Camera Hardware Indicator:\n"
            "Your laptop's physical LED indicator activates only when the camera pipeline is running.\n\n"
            "⛔ Safety Interceptor:\n"
            "Dangerous system shortcuts (Alt+F4, Windows Lock, Ctrl+Alt+Del) are filtered by the safety blacklist."
        )
        info.setFont(QFont("Segoe UI", 11))
        info.setStyleSheet("color: #CCCCCC; line-height: 1.5;")
        cl.addWidget(info)

        layout.addWidget(card)
        layout.addStretch()
        self.pages.addWidget(page)

    def _build_page_about(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)

        header = QLabel("About VisionTouch AI")
        header.setFont(QFont("Segoe UI", 16, QFont.Bold))
        layout.addWidget(header)

        card = QFrame()
        card.setProperty("class", "card")
        cl = QVBoxLayout(card)

        about_text = QLabel(
            "VisionTouch AI: AI-Powered Touchless Laptop Control System\n"
            "Version: 1.0.0 (Production Release)\n\n"
            "Built with:\n"
            "• Python 3.10 & PySide6 (Qt for Python)\n"
            "• MediaPipe 21-Point Hand Perception Graph\n"
            "• OpenCV Computer Vision Engine & DirectShow Capture\n"
            "• SQLite Local Database & Windows user32 Input Subsystem\n\n"
            "GitHub Repository: https://github.com/Akshaya2720/VisionTouch-ai\n"
            "Engineering Architecture: Modular Domain-Driven Design"
        )
        about_text.setFont(QFont("Segoe UI", 11))
        about_text.setStyleSheet("color: #CCCCCC; line-height: 1.6;")
        cl.addWidget(about_text)

        layout.addWidget(card)
        layout.addStretch()
        self.pages.addWidget(page)

    # ---------------- SLOTS & EVENT HANDLERS ---------------- #

    def _start_worker(self) -> None:
        """Launches the asynchronous QThread vision pipeline."""
        self.worker = CameraWorker(
            self.camera, self.detector, self.recognizer, self.action_manager, self.state_manager
        )
        self.worker.frame_ready.connect(self._on_frame_ready)
        self.worker.gesture_detected.connect(self._on_gesture_detected)
        self.worker.state_changed.connect(self._on_state_changed)
        self.worker.start()

    @Slot(QImage)
    def _on_frame_ready(self, q_img: QImage) -> None:
        """Renders live video frame to the Camera Preview tab."""
        pixmap = QPixmap.fromImage(q_img)
        scaled = pixmap.scaled(
            self.video_display.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.video_display.setPixmap(scaled)

    @Slot(str, str, float)
    def _on_gesture_detected(self, gesture_name: str, action_name: str, fps: float) -> None:
        self.lbl_gesture.setText(gesture_name)
        self.lbl_fps.setText(f"{fps:.1f} FPS")
        if action_name != "none":
            self.lbl_last_action.setText(f"Dispatched OS Action: {action_name}")

    @Slot(str)
    def _on_state_changed(self, state_name: str) -> None:
        self.lbl_mode.setText(state_name)
        if state_name == "ACTIVE":
            self.lbl_mode.setStyleSheet("color: #00b4d8;")
        elif state_name == "PAUSED":
            self.lbl_mode.setStyleSheet("color: #FF0000;")
        else:
            self.lbl_mode.setStyleSheet("color: #FFA500;")

    def _toggle_engine(self) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.sidebar_toggle_btn.setText("Start Engine")
            self.sidebar_toggle_btn.setProperty("class", "primary")
            self.sidebar_toggle_btn.setStyle(self.sidebar_toggle_btn.style())
            self.lbl_cam_status.setText("STOPPED")
            self.lbl_cam_status.setStyleSheet("color: #FF0000;")
        else:
            self._start_worker()
            self.sidebar_toggle_btn.setText("Stop Engine")
            self.sidebar_toggle_btn.setProperty("class", "danger")
            self.sidebar_toggle_btn.setStyle(self.sidebar_toggle_btn.style())
            self.lbl_cam_status.setText("ACTIVE")
            self.lbl_cam_status.setStyleSheet("color: #00FF00;")

    def _on_profile_changed(self, profile_name: str) -> None:
        self.action_manager.set_profile(profile_name)
        self.combo_profile_dash.setCurrentText(profile_name)
        self._load_custom_mappings()

    def _load_custom_mappings(self) -> None:
        mappings = self.db.get_mappings(self.action_manager.active_profile)
        self.table_custom.setRowCount(len(mappings))
        for row, (gesture, action) in enumerate(mappings.items()):
            self.table_custom.setItem(row, 0, QTableWidgetItem(gesture))
            self.table_custom.setItem(row, 1, QTableWidgetItem(action))
            self.table_custom.setItem(row, 2, QTableWidgetItem("Yes"))

    def _save_custom_mappings(self) -> None:
        profile = self.action_manager.active_profile
        for row in range(self.table_custom.rowCount()):
            g_item = self.table_custom.item(row, 0)
            a_item = self.table_custom.item(row, 1)
            if g_item and a_item:
                self.db.update_mapping(profile, g_item.text(), a_item.text())
        self.action_manager.set_profile(profile)
        logger.info("Custom mappings saved successfully.")

    def _on_sensitivity_slider_changed(self, value: int) -> None:
        val = value / 100.0
        self.mouse.mapper.set_sensitivity(val)
        self.db.update_settings(cursor_sensitivity=val)

    def _on_scroll_slider_changed(self, value: int) -> None:
        self.scroller.base_speed = float(value)
        self.db.update_settings(scroll_sensitivity=float(value))

    def closeEvent(self, event) -> None:
        """Gracefully release hardware on window close."""
        if self.worker:
            self.worker.stop()
        self.detector.close()
        event.accept()


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
