"""VisionTouch AI: Master Application Entrypoint.

By default, launches the minimal, zero-clutter Floating Companion:
- A small draggable camera on the right side of the screen with a digital clock.
- A glowing cursor reticle following your finger over real apps (Instagram, YouTube, etc.).
- Zero complex UI taking up your screen.

To launch the full configuration dashboard instead:
    python app/main.py --dashboard
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication
from app.utils.logger import setup_logger

logger = setup_logger("Main")


def main() -> None:
    app = QApplication(sys.argv)

    # Check command-line arguments
    if "--dashboard" in sys.argv:
        logger.info("Launching Full Configuration Dashboard...")
        from app.ui.dashboard import MainWindow
        window = MainWindow()
        window.show()
    else:
        logger.info("Launching Minimal Floating Camera Companion...")
        from app.ui.mini_app import VisionTouchMiniApp
        mini_app = VisionTouchMiniApp()
        mini_app.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
