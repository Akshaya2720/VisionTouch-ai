"""Direct Launcher for VisionTouch AI Full Laptop Touchless Mode.

Launches directly into Desktop Companion Mode:
- Glowing Cursor Reticle directly on your desktop (following your finger over Instagram, Chrome, etc.).
- Floating Always-on-Top Camera PiP at the top of your screen showing your hand tracking.
- Minimizes dashboard so you have immediate 100% control over your real laptop applications!

Usage:
    python tests/run_desktop_mode.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication
from app.ui.dashboard import MainWindow
from app.utils.logger import setup_logger

logger = setup_logger("DesktopModeLauncher")


def main() -> None:
    logger.info("Launching VisionTouch AI Desktop Companion Mode...")
    app = QApplication(sys.argv)
    window = MainWindow()

    # Automatically activate floating overlays and minimize dashboard
    window._toggle_overlays()
    window.showMinimized()

    logger.info("==================================================================")
    logger.info(" TOUCHLESS DESKTOP MODE ACTIVE!")
    logger.info(" • Your camera is floating at the top-right of your screen.")
    logger.info(" • A glowing dot follows your finger across all real Windows apps.")
    logger.info(" • Open Instagram / YouTube / Chrome and control everything touchlessly!")
    logger.info(" • Press 'Stop Engine' in PiP or restore the dashboard to quit.")
    logger.info("==================================================================")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

