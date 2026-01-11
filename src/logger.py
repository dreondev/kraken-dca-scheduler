"""Professional logging setup for Kraken DCA Scheduler.

This module provides a centralized logging configuration with
support for console and file output, structured formatting,
and log rotation.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str = "kraken-dca",
    level: str = "INFO",
    log_file: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> logging.Logger:
    """Set up and configure application logger.
    
    Creates a logger with console output and optional file output.
    Uses structured formatting for better readability.
    
    Args:
        name: Logger name (default: "kraken-dca")
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file. If None, only console logging.
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup log files to keep
    
    Returns:
        Configured logger instance
        
    Examples:
        >>> logger = setup_logger(level="INFO")
        >>> logger.info("Application started")
        
        >>> logger = setup_logger(level="DEBUG", log_file="app.log")
        >>> logger.debug("Debug information")
    """
    logger = logging.getLogger(name)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Set log level
    log_level = _parse_log_level(level)
    logger.setLevel(log_level)
    
    # Create formatter
    formatter = _create_formatter()
    
    # Add console handler
    console_handler = _create_console_handler(formatter)
    logger.addHandler(console_handler)
    
    # Add file handler if log file specified
    if log_file:
        file_handler = _create_file_handler(
            log_file,
            formatter,
            max_bytes,
            backup_count
        )
        logger.addHandler(file_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


def _parse_log_level(level: str) -> int:
    """Parse log level string to logging constant.
    
    Args:
        level: Log level string (case-insensitive)
    
    Returns:
        Logging level constant
        
    Raises:
        ValueError: If level is invalid
    """
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    
    level_upper = level.upper()
    if level_upper not in level_map:
        raise ValueError(
            f"Invalid log level: {level}. "
            f"Valid levels: {list(level_map.keys())}"
        )
    
    return level_map[level_upper]


def _create_formatter() -> logging.Formatter:
    """Create log formatter with consistent format.
    
    Returns:
        Configured formatter
    """
    return logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


def _create_console_handler(formatter: logging.Formatter) -> logging.StreamHandler:
    """Create console handler for stdout.
    
    Args:
        formatter: Log formatter to use
    
    Returns:
        Configured console handler
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    return handler


def _create_file_handler(
    log_file: str,
    formatter: logging.Formatter,
    max_bytes: int,
    backup_count: int,
) -> RotatingFileHandler:
    """Create rotating file handler.
    
    Args:
        log_file: Path to log file
        formatter: Log formatter to use
        max_bytes: Maximum file size before rotation
        backup_count: Number of backup files to keep
    
    Returns:
        Configured rotating file handler
    """
    # Ensure log directory exists
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8"
    )
    handler.setFormatter(formatter)
    
    return handler


def get_logger(name: str = "kraken-dca") -> logging.Logger:
    """Get existing logger instance.
    
    Use this to get the logger in other modules after setup_logger()
    has been called.
    
    Args:
        name: Logger name (must match name used in setup_logger)
    
    Returns:
        Logger instance
        
    Examples:
        >>> # In main.py
        >>> logger = setup_logger(level="INFO")
        
        >>> # In other modules
        >>> from src.logger import get_logger
        >>> logger = get_logger()
        >>> logger.info("Hello from module")
    """
    return logging.getLogger(name)