"""Tests for logging setup."""

import logging
import pytest
from pathlib import Path
from src.logger import (
    setup_logger,
    get_logger,
    _parse_log_level,
    _create_formatter,
)


class TestSetupLogger:
    """Tests for setup_logger function."""
    
    def test_setup_logger_basic(self):
        """Test basic logger setup."""
        logger = setup_logger(name="test-logger", level="INFO")
        
        assert logger.name == "test-logger"
        assert logger.level == logging.INFO
        assert len(logger.handlers) == 1  # Console handler only
    
    def test_setup_logger_with_file(self, tmp_path):
        """Test logger setup with file output."""
        log_file = tmp_path / "test.log"
        
        logger = setup_logger(
            name="test-logger-file",
            level="DEBUG",
            log_file=str(log_file)
        )
        
        assert logger.level == logging.DEBUG
        assert len(logger.handlers) == 2  # Console + File
        assert log_file.exists()
    
    def test_setup_logger_creates_directory(self, tmp_path):
        """Test that logger creates log directory if needed."""
        log_file = tmp_path / "logs" / "nested" / "test.log"
        
        logger = setup_logger(
            name="test-logger-nested",
            log_file=str(log_file)
        )
        
        assert log_file.parent.exists()
        assert log_file.exists()
    
    def test_setup_logger_writes_to_file(self, tmp_path):
        """Test that logger actually writes to file."""
        log_file = tmp_path / "test.log"
        
        logger = setup_logger(
            name="test-logger-write",
            log_file=str(log_file)
        )
        
        logger.info("Test message")
        
        # Force flush
        for handler in logger.handlers:
            handler.flush()
        
        content = log_file.read_text()
        assert "Test message" in content
        assert "[INFO]" in content
    
    def test_setup_logger_no_propagation(self):
        """Test that logger doesn't propagate to root."""
        logger = setup_logger(name="test-no-prop")
        
        assert logger.propagate is False
    
    def test_setup_logger_removes_old_handlers(self):
        """Test that setup_logger removes existing handlers."""
        logger = setup_logger(name="test-handlers")
        initial_count = len(logger.handlers)
        
        # Setup again
        logger = setup_logger(name="test-handlers")
        
        # Should have same number of handlers, not doubled
        assert len(logger.handlers) == initial_count


class TestGetLogger:
    """Tests for get_logger function."""
    
    def test_get_logger_after_setup(self):
        """Test getting logger after setup."""
        setup_logger(name="test-get", level="INFO")
        
        logger = get_logger(name="test-get")
        
        assert logger.name == "test-get"
        assert logger.level == logging.INFO
    
    def test_get_logger_same_instance(self):
        """Test that get_logger returns same instance."""
        logger1 = setup_logger(name="test-same")
        logger2 = get_logger(name="test-same")
        
        assert logger1 is logger2


class TestParseLogLevel:
    """Tests for _parse_log_level function."""
    
    def test_parse_log_level_valid(self):
        """Test parsing valid log levels."""
        assert _parse_log_level("DEBUG") == logging.DEBUG
        assert _parse_log_level("INFO") == logging.INFO
        assert _parse_log_level("WARNING") == logging.WARNING
        assert _parse_log_level("ERROR") == logging.ERROR
        assert _parse_log_level("CRITICAL") == logging.CRITICAL
    
    def test_parse_log_level_case_insensitive(self):
        """Test that log level parsing is case-insensitive."""
        assert _parse_log_level("info") == logging.INFO
        assert _parse_log_level("Info") == logging.INFO
        assert _parse_log_level("INFO") == logging.INFO
    
    def test_parse_log_level_invalid(self):
        """Test that invalid log level raises error."""
        with pytest.raises(ValueError, match="Invalid log level"):
            _parse_log_level("INVALID")


class TestCreateFormatter:
    """Tests for _create_formatter function."""
    
    def test_create_formatter(self):
        """Test formatter creation."""
        formatter = _create_formatter()
        
        assert isinstance(formatter, logging.Formatter)
        assert "%(asctime)s" in formatter._fmt
        assert "%(levelname)s" in formatter._fmt
        assert "%(message)s" in formatter._fmt


class TestLogLevels:
    """Tests for different log levels."""
    
    def test_debug_level(self, tmp_path):
        """Test DEBUG level logging."""
        log_file = tmp_path / "debug.log"
        logger = setup_logger(name="test-debug", level="DEBUG", log_file=str(log_file))
        
        logger.debug("Debug message")
        logger.info("Info message")
        
        for handler in logger.handlers:
            handler.flush()
        
        content = log_file.read_text()
        assert "Debug message" in content
        assert "Info message" in content
    
    def test_info_level_filters_debug(self, tmp_path):
        """Test that INFO level filters out DEBUG messages."""
        log_file = tmp_path / "info.log"
        logger = setup_logger(name="test-info", level="INFO", log_file=str(log_file))
        
        logger.debug("Debug message")
        logger.info("Info message")
        
        for handler in logger.handlers:
            handler.flush()
        
        content = log_file.read_text()
        assert "Debug message" not in content
        assert "Info message" in content
    
    def test_warning_level(self, tmp_path):
        """Test WARNING level logging."""
        log_file = tmp_path / "warning.log"
        logger = setup_logger(name="test-warn", level="WARNING", log_file=str(log_file))
        
        logger.info("Info message")
        logger.warning("Warning message")
        
        for handler in logger.handlers:
            handler.flush()
        
        content = log_file.read_text()
        assert "Info message" not in content
        assert "Warning message" in content