"""Centralized logging configuration for the AI Receptionist system."""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path


def setup_logging(log_dir: str = "logs", level: str = "INFO") -> logging.Logger:
    """
    Configure logging with both file and console handlers.

    Creates daily rotating log files with 30-day retention and
    colorized console output for development.

    Args:
        log_dir: Directory for log files (default: "logs")
        level: Logging level (default: "INFO")

    Returns:
        Configured root logger instance
    """
    # Create log directory
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, level.upper()))

    # Clear existing handlers
    logger.handlers = []

    # Log format
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler with daily rotation and 30-day retention
    log_file = log_path / "receptionist.log"
    file_handler = logging.handlers.TimedRotatingFileHandler(
        str(log_file),
        when="midnight",
        interval=1,
        backupCount=30,  # Keep 30 days of logs
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(getattr(logging, level.upper()))
    logger.addHandler(file_handler)

    # Console handler for development/debugging
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(getattr(logging, level.upper()))
    logger.addHandler(console_handler)

    logger.info(f"Logging configured - level: {level}, log_dir: {log_dir}")

    return logger
