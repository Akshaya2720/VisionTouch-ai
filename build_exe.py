"""Production Build Script for VisionTouch AI.

Packages the entire Python, PySide6, OpenCV, and MediaPipe application
into a standalone Windows desktop executable using PyInstaller.
"""

import os
from pathlib import Path
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parent


def build() -> None:
    print("==================================================")
    print("      VisionTouch AI: Standalone Executable Build ")
    print("==================================================")

    main_script = PROJECT_ROOT / "app" / "main.py"
    dist_dir = PROJECT_ROOT / "dist"
    build_dir = PROJECT_ROOT / "build"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name=VisionTouchAI",
        "--windowed",          # Hide console window in production GUI
        "--onedir",            # Faster startup than --onefile for large ML models
        "--clean",
        "--noconfirm",
        "--collect-all=mediapipe",  # Bundle all offline TFLite models
        f"--distpath={dist_dir}",
        f"--workpath={build_dir}",
        str(main_script),
    ]

    print(f"Executing: {' '.join(cmd)}\n")
    try:
        subprocess.run(cmd, check=True)
        print("\n==================================================")
        print(" BUILD SUCCESSFUL!")
        print(f" Standalone executable available at:")
        print(f" {dist_dir / 'VisionTouchAI' / 'VisionTouchAI.exe'}")
        print("==================================================")
    except subprocess.CalledProcessError as e:
        print(f"\nBUILD FAILED with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    build()
