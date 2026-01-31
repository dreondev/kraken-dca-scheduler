"""Professional logging setup for Kraken DCA Scheduler.

This module provides a centralized logging configuration with
support for console and file output, structured formatting,
and log rotation.

Note: Configures both root logger and named logger to ensure
child loggers (src.daemon, src.scheduler) work correctly in
APScheduler threads.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str = "src",
    level: str = "INFO",
    log_file: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> logging.Logger:
    """Set up and configure application logger.
    
    Creates a logger with console output and optional file output.
    Configures both root logger and named logger to ensure proper
    logging from child modules (src.daemon, src.scheduler) even
    when running in APScheduler threads.
    
    Args:
        name: Logger name (default: "src" for module inheritance)
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
    log_level = _parse_log_level(level)
    formatter = _create_formatter()
    
    # Create handlers
    console_handler = _create_console_handler(formatter)
    console_handler.setLevel(log_level)
    
    file_handler = None
    if log_file:
        file_handler = _create_file_handler(
            log_file, formatter, max_bytes, backup_count
        )
        file_handler.setLevel(log_level)
    
    # Configure root logger as fallback for all child loggers
    # This ensures src.daemon, src.scheduler etc. always have handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    if file_handler:
        root_logger.addHandler(file_handler)
    
    # Configure named logger
    logger = logging.getLogger(name)
    logger.handlers.clear()
    logger.setLevel(log_level)
    
    # Propagate to root logger (which has the handlers)
    logger.propagate = True
    
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
        fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
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


def get_logger(name: str = "src") -> logging.Logger:
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