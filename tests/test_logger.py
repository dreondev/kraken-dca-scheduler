"""Tests for logging setup.

Tests cover:
- Basic logger setup and configuration
- Root logger configuration (critical for APScheduler threads)
- Child logger propagation (src.daemon, src.scheduler, etc.)
- File handler with rotation
- Log level filtering
"""

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest

from src.logger import (
    setup_logger,
    get_logger,
    _parse_log_level,
    _create_formatter,
    _create_console_handler,
    _create_file_handler,
)


class TestSetupLogger:
    """Tests for setup_logger function."""

    def test_returns_named_logger(self):
        """Test that setup_logger returns logger with correct name."""
        logger = setup_logger(name="test-basic", level="INFO")
        
        assert logger.name == "test-basic"

    def test_sets_log_level(self):
        """Test that logger has correct level."""
        logger = setup_logger(name="test-level", level="DEBUG")
        
        assert logger.level == logging.DEBUG

    def test_configures_root_logger(self):
        """Test that root logger is configured with handlers."""
        setup_logger(name="test-root", level="INFO")
        
        root_logger = logging.getLogger()
        
        assert len(root_logger.handlers) >= 1
        assert root_logger.level == logging.INFO

    def test_root_logger_has_console_handler(self):
        """Test that root logger has StreamHandler for console output."""
        setup_logger(name="test-console", level="INFO")
        
        root_logger = logging.getLogger()
        handler_types = [type(h) for h in root_logger.handlers]
        
        assert logging.StreamHandler in handler_types

    def test_clears_existing_handlers(self):
        """Test that setup_logger removes existing handlers."""
        # Setup twice
        setup_logger(name="test-clear", level="INFO")
        setup_logger(name="test-clear", level="INFO")
        
        root_logger = logging.getLogger()
        
        # Should not have duplicate handlers
        assert len(root_logger.handlers) <= 2  # Console + optional file

    def test_named_logger_propagates(self):
        """Test that named logger propagates to root."""
        logger = setup_logger(name="test-propagate", level="INFO")
        
        assert logger.propagate is True


class TestSetupLoggerWithFile:
    """Tests for setup_logger with file output."""

    def test_creates_log_file(self, tmp_path):
        """Test that log file is created."""
        log_file = tmp_path / "test.log"
        
        setup_logger(name="test-file", level="INFO", log_file=str(log_file))
        
        assert log_file.exists()

    def test_creates_nested_directories(self, tmp_path):
        """Test that nested log directories are created."""
        log_file = tmp_path / "logs" / "nested" / "deep" / "test.log"
        
        setup_logger(name="test-nested", level="INFO", log_file=str(log_file))
        
        assert log_file.parent.exists()
        assert log_file.exists()

    def test_writes_to_file(self, tmp_path):
        """Test that log messages are written to file."""
        log_file = tmp_path / "test.log"
        
        logger = setup_logger(
            name="test-write",
            level="INFO",
            log_file=str(log_file)
        )
        
        logger.info("Test message for file")
        
        # Flush all handlers
        for handler in logging.getLogger().handlers:
            handler.flush()
        
        content = log_file.read_text()
        assert "Test message for file" in content

    def test_root_logger_has_file_handler(self, tmp_path):
        """Test that root logger gets file handler."""
        log_file = tmp_path / "test.log"
        
        setup_logger(name="test-root-file", level="INFO", log_file=str(log_file))
        
        root_logger = logging.getLogger()
        handler_types = [type(h).__name__ for h in root_logger.handlers]
        
        assert "RotatingFileHandler" in handler_types


class TestChildLoggerPropagation:
    """Tests for child logger propagation - critical for APScheduler fix."""

    def test_child_logger_inherits_level(self):
        """Test that child loggers inherit effective level."""
        setup_logger(name="src", level="DEBUG")
        
        child = logging.getLogger("src.daemon")
        
        assert child.getEffectiveLevel() == logging.DEBUG

    def test_child_logger_messages_reach_root(self, tmp_path):
        """Test that child logger messages are handled by root logger."""
        log_file = tmp_path / "test.log"
        
        setup_logger(name="src", level="INFO", log_file=str(log_file))
        
        # Simulate what src.daemon does
        child_logger = logging.getLogger("src.daemon")
        child_logger.info("Message from child logger")
        
        # Flush
        for handler in logging.getLogger().handlers:
            handler.flush()
        
        content = log_file.read_text()
        assert "Message from child logger" in content

    def test_deeply_nested_child_logger(self, tmp_path):
        """Test that deeply nested loggers also work."""
        log_file = tmp_path / "test.log"
        
        setup_logger(name="src", level="INFO", log_file=str(log_file))
        
        # Simulate src.kraken.client
        deep_child = logging.getLogger("src.kraken.client")
        deep_child.info("Message from deep child")
        
        for handler in logging.getLogger().handlers:
            handler.flush()
        
        content = log_file.read_text()
        assert "Message from deep child" in content

    def test_multiple_child_loggers(self, tmp_path):
        """Test multiple child loggers all work correctly."""
        log_file = tmp_path / "test.log"
        
        setup_logger(name="src", level="INFO", log_file=str(log_file))
        
        # Simulate all module loggers
        daemon_logger = logging.getLogger("src.daemon")
        scheduler_logger = logging.getLogger("src.scheduler")
        client_logger = logging.getLogger("src.kraken.client")
        
        daemon_logger.info("Daemon message")
        scheduler_logger.info("Scheduler message")
        client_logger.info("Client message")
        
        for handler in logging.getLogger().handlers:
            handler.flush()
        
        content = log_file.read_text()
        assert "Daemon message" in content
        assert "Scheduler message" in content
        assert "Client message" in content


class TestThreadSafety:
    """Tests for thread safety - simulates APScheduler behavior."""

    def test_child_logger_works_in_thread(self, tmp_path):
        """Test that child logger works when called from a different thread."""
        log_file = tmp_path / "test.log"
        
        setup_logger(name="src", level="INFO", log_file=str(log_file))
        
        def log_from_thread():
            """Simulate APScheduler job execution."""
            thread_logger = logging.getLogger("src.daemon")
            thread_logger.info("Message from APScheduler thread")
        
        # Run in separate thread (like APScheduler does)
        thread = threading.Thread(target=log_from_thread)
        thread.start()
        thread.join()
        
        for handler in logging.getLogger().handlers:
            handler.flush()
        
        content = log_file.read_text()
        assert "Message from APScheduler thread" in content

    def test_concurrent_logging_from_multiple_threads(self, tmp_path):
        """Test concurrent logging from multiple threads."""
        log_file = tmp_path / "test.log"
        
        setup_logger(name="src", level="INFO", log_file=str(log_file))
        
        def log_from_thread(thread_id: int):
            """Log messages from thread."""
            logger = logging.getLogger("src.daemon")
            for i in range(10):
                logger.info(f"Thread-{thread_id}-Message-{i}")
        
        # Run multiple threads concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(log_from_thread, i) for i in range(5)]
            for f in futures:
                f.result()
        
        for handler in logging.getLogger().handlers:
            handler.flush()
        
        content = log_file.read_text()
        
        # Verify all threads logged successfully
        for thread_id in range(5):
            assert f"Thread-{thread_id}-Message-0" in content
            assert f"Thread-{thread_id}-Message-9" in content

    def test_logger_created_before_setup_works_in_thread(self, tmp_path):
        """Test logger created before setup still works in threads.
        
        This simulates the real-world scenario where modules import
        and create loggers at import time, before setup_logger is called.
        """
        log_file = tmp_path / "test.log"
        
        # Create child logger BEFORE setup (like module-level logger = logging.getLogger(__name__))
        early_logger = logging.getLogger("src.early_module")
        
        # Now setup parent
        setup_logger(name="src", level="INFO", log_file=str(log_file))
        
        def log_from_thread():
            early_logger.info("Message from early logger in thread")
        
        thread = threading.Thread(target=log_from_thread)
        thread.start()
        thread.join()
        
        for handler in logging.getLogger().handlers:
            handler.flush()
        
        content = log_file.read_text()
        assert "Message from early logger in thread" in content


class TestGetLogger:
    """Tests for get_logger function."""

    def test_returns_logger_instance(self):
        """Test that get_logger returns a logger."""
        logger = get_logger("test-get")
        
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test-get"

    def test_returns_same_instance(self):
        """Test that get_logger returns same instance as setup_logger."""
        logger1 = setup_logger(name="test-same", level="INFO")
        logger2 = get_logger(name="test-same")
        
        assert logger1 is logger2

    def test_default_name(self):
        """Test default logger name."""
        logger = get_logger()
        
        assert logger.name == "src"


class TestParseLogLevel:
    """Tests for _parse_log_level function."""

    @pytest.mark.parametrize("level_str,expected", [
        ("DEBUG", logging.DEBUG),
        ("INFO", logging.INFO),
        ("WARNING", logging.WARNING),
        ("ERROR", logging.ERROR),
        ("CRITICAL", logging.CRITICAL),
    ])
    def test_valid_levels(self, level_str: str, expected: int):
        """Test parsing valid log levels."""
        assert _parse_log_level(level_str) == expected

    @pytest.mark.parametrize("level_str", ["debug", "Info", "WARNING", "error", "CrItIcAl"])
    def test_case_insensitive(self, level_str: str):
        """Test that parsing is case-insensitive."""
        result = _parse_log_level(level_str)
        
        assert result in (
            logging.DEBUG,
            logging.INFO, 
            logging.WARNING,
            logging.ERROR,
            logging.CRITICAL
        )

    def test_invalid_level_raises_error(self):
        """Test that invalid level raises ValueError."""
        with pytest.raises(ValueError, match="Invalid log level"):
            _parse_log_level("INVALID")

    def test_error_message_lists_valid_levels(self):
        """Test that error message includes valid levels."""
        with pytest.raises(ValueError) as exc_info:
            _parse_log_level("WRONG")
        
        error_msg = str(exc_info.value)
        assert "DEBUG" in error_msg
        assert "INFO" in error_msg


class TestCreateFormatter:
    """Tests for _create_formatter function."""

    def test_returns_formatter(self):
        """Test that function returns a Formatter."""
        formatter = _create_formatter()
        
        assert isinstance(formatter, logging.Formatter)

    def test_format_includes_timestamp(self):
        """Test that format includes timestamp."""
        formatter = _create_formatter()
        
        assert "%(asctime)s" in formatter._fmt

    def test_format_includes_level(self):
        """Test that format includes log level."""
        formatter = _create_formatter()
        
        assert "%(levelname)s" in formatter._fmt

    def test_format_includes_logger_name(self):
        """Test that format includes logger name for debugging."""
        formatter = _create_formatter()
        
        assert "%(name)s" in formatter._fmt

    def test_format_includes_message(self):
        """Test that format includes message."""
        formatter = _create_formatter()
        
        assert "%(message)s" in formatter._fmt


class TestCreateConsoleHandler:
    """Tests for _create_console_handler function."""

    def test_returns_stream_handler(self):
        """Test that function returns StreamHandler."""
        formatter = _create_formatter()
        handler = _create_console_handler(formatter)
        
        assert isinstance(handler, logging.StreamHandler)

    def test_handler_has_formatter(self):
        """Test that handler has formatter set."""
        formatter = _create_formatter()
        handler = _create_console_handler(formatter)
        
        assert handler.formatter is formatter


class TestCreateFileHandler:
    """Tests for _create_file_handler function."""

    def test_returns_rotating_handler(self, tmp_path):
        """Test that function returns RotatingFileHandler."""
        from logging.handlers import RotatingFileHandler
        
        log_file = tmp_path / "test.log"
        formatter = _create_formatter()
        
        handler = _create_file_handler(
            str(log_file), formatter, max_bytes=1024, backup_count=3
        )
        
        assert isinstance(handler, RotatingFileHandler)

    def test_handler_has_correct_settings(self, tmp_path):
        """Test that handler has correct rotation settings."""
        log_file = tmp_path / "test.log"
        formatter = _create_formatter()
        
        handler = _create_file_handler(
            str(log_file), formatter, max_bytes=5000, backup_count=7
        )
        
        assert handler.maxBytes == 5000
        assert handler.backupCount == 7


class TestLogLevelFiltering:
    """Tests for log level filtering."""

    def test_debug_level_logs_all(self, tmp_path):
        """Test that DEBUG level logs all messages."""
        log_file = tmp_path / "test.log"
        logger = setup_logger(name="test-debug", level="DEBUG", log_file=str(log_file))
        
        logger.debug("Debug msg")
        logger.info("Info msg")
        logger.warning("Warning msg")
        
        for handler in logging.getLogger().handlers:
            handler.flush()
        
        content = log_file.read_text()
        assert "Debug msg" in content
        assert "Info msg" in content
        assert "Warning msg" in content

    def test_info_level_filters_debug(self, tmp_path):
        """Test that INFO level filters DEBUG messages."""
        log_file = tmp_path / "test.log"
        logger = setup_logger(name="test-info", level="INFO", log_file=str(log_file))
        
        logger.debug("Debug msg")
        logger.info("Info msg")
        
        for handler in logging.getLogger().handlers:
            handler.flush()
        
        content = log_file.read_text()
        assert "Debug msg" not in content
        assert "Info msg" in content

    def test_warning_level_filters_info(self, tmp_path):
        """Test that WARNING level filters INFO and DEBUG."""
        log_file = tmp_path / "test.log"
        logger = setup_logger(name="test-warn", level="WARNING", log_file=str(log_file))
        
        logger.debug("Debug msg")
        logger.info("Info msg")
        logger.warning("Warning msg")
        
        for handler in logging.getLogger().handlers:
            handler.flush()
        
        content = log_file.read_text()
        assert "Debug msg" not in content
        assert "Info msg" not in content
        assert "Warning msg" in content


class TestLogFormat:
    """Tests for log message format."""

    def test_format_contains_timestamp(self, tmp_path):
        """Test that log output contains timestamp."""
        log_file = tmp_path / "test.log"
        setup_logger(name="test-ts", level="INFO", log_file=str(log_file))
        
        logger = logging.getLogger("test-ts")
        logger.info("Test message")
        
        for handler in logging.getLogger().handlers:
            handler.flush()
        
        content = log_file.read_text()
        # Check for date pattern YYYY-MM-DD
        import re
        assert re.search(r"\d{4}-\d{2}-\d{2}", content)

    def test_format_contains_level(self, tmp_path):
        """Test that log output contains level."""
        log_file = tmp_path / "test.log"
        setup_logger(name="test-lvl", level="INFO", log_file=str(log_file))
        
        logger = logging.getLogger("test-lvl")
        logger.info("Test message")
        
        for handler in logging.getLogger().handlers:
            handler.flush()
        
        content = log_file.read_text()
        assert "[INFO]" in content

    def test_format_contains_logger_name(self, tmp_path):
        """Test that log output contains logger name."""
        log_file = tmp_path / "test.log"
        setup_logger(name="src", level="INFO", log_file=str(log_file))
        
        child_logger = logging.getLogger("src.daemon")
        child_logger.info("Test message")
        
        for handler in logging.getLogger().handlers:
            handler.flush()
        
        content = log_file.read_text()
        assert "src.daemon" in content