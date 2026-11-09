"""Centralized structured logger for VisionTouch AI."""

import logging
import sys
from typing import Optional


def setup_logger(name: str = "VisionTouchAI", level: int = logging.INFO) -> logging.Logger:
    """Configures and returns a thread-safe standardized console logger.

    Args:
        name: Subsystem or module identifier.
        level: Logging verbosity (default INFO).

    Returns:
        logging.Logger instance.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(level)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
            datefmt="%H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False
    return logger

