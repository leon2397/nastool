"""
nastool Logging System

Unified logging with configurable level and format.

Usage:
    from logger import get_logger

    logger = get_logger(__name__)
    logger.info("Starting diagnosis")
    logger.error("Check failed", exc_info=True)
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from .config import Config


def setup_logger(
    name: str = "nastool",
    level: Optional[str] = None,
    log_file: Optional[Path] = None,
) -> logging.Logger:
    """
    Setup logger with console and optional file handler.

    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Clear existing handlers
    logger.handlers.clear()

    # Set level
    log_level = level or Config.LOG_LEVEL
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_formatter = logging.Formatter(Config.LOG_FORMAT, datefmt=Config.LOG_DATE_FORMAT)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(Config.LOG_FORMAT, datefmt=Config.LOG_DATE_FORMAT)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get or create logger for a module.

    Args:
        name: Usually __name__ of the calling module

    Returns:
        Logger instance
    """
    # Ensure root logger is configured
    root_logger = logging.getLogger("nastool")

    if not root_logger.handlers:
        setup_logger("nastool")

    # Return child logger
    if name.startswith("nastool."):
        return logging.getLogger(name)
    else:
        return logging.getLogger(f"nastool.{name}")


class LogContext:
    """Context manager for temporary log level changes."""

    def __init__(self, level: str):
        self.level = level
        self.original_level = None
        self.logger = logging.getLogger("nastool")

    def __enter__(self):
        self.original_level = self.logger.level
        self.logger.setLevel(getattr(logging, self.level.upper()))
        return self

    def __exit__(self, *args):
        if self.original_level is not None:
            self.logger.setLevel(self.original_level)


# Convenience functions
def debug(msg: str, *args, **kwargs):
    """Log debug message."""
    get_logger("nastool").debug(msg, *args, **kwargs)


def info(msg: str, *args, **kwargs):
    """Log info message."""
    get_logger("nastool").info(msg, *args, **kwargs)


def warning(msg: str, *args, **kwargs):
    """Log warning message."""
    get_logger("nastool").warning(msg, *args, **kwargs)


def error(msg: str, *args, **kwargs):
    """Log error message."""
    get_logger("nastool").error(msg, *args, **kwargs)


def critical(msg: str, *args, **kwargs):
    """Log critical message."""
    get_logger("nastool").critical(msg, *args, **kwargs)
