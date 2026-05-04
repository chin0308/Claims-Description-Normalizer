"""
Logging Utility
----------------
Centralized logging setup for the entire pipeline.

Logs to both console (INFO) and a rotating file (DEBUG) for full traceability.
"""

import logging
import logging.handlers
from pathlib import Path


def setup_logging(log_dir: str = "logs", level: int = logging.INFO):
    """
    Configure application-wide logging.

    - Console: INFO level (clean, readable)
    - File: DEBUG level (full detail for debugging)
    - Rotating file handler: max 5MB per file, 3 backups

    Args:
        log_dir: Directory to store log files
        level: Minimum log level for console output
    """
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    formatter = logging.Formatter(log_format, datefmt=date_format)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    # Rotating file handler
    file_handler = logging.handlers.RotatingFileHandler(
        filename=f"{log_dir}/pipeline.log",
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Attach handlers (avoid duplicates on re-import)
    if not root_logger.handlers:
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)
