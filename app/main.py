"""VisionTouch AI: Master Desktop Application Entrypoint.

Initializes the PySide6 Qt GUI loop, loads SQLite preferences,
and starts the real-time computer vision perception pipeline.
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication
from app.ui.dashboard import MainWindow
from app.utils.logger import setup_logger

logger = setup_logger("Main")


def main() -> None:
    logger.info("Starting VisionTouch AI Application Suite...")
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    logger.info("Main dashboard window opened successfully.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

