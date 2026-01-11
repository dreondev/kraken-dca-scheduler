"""Tests for timezone utilities."""

import pytest
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from src.utils.timezone import (
    get_timezone,
    get_current_time,
    format_timestamp,
    get_timestamp_string,
)


class TestGetTimezone:
    """Tests for get_timezone function."""
    
    def test_get_timezone_berlin(self):
        """Test getting Europe/Berlin timezone."""
        tz = get_timezone("Europe/Berlin")
        assert tz.key == "Europe/Berlin"
    
    def test_get_timezone_utc(self):
        """Test getting UTC timezone."""
        tz = get_timezone("UTC")
        assert tz.key == "UTC"
    
    def test_get_timezone_invalid(self):
        """Test invalid timezone name raises error."""
        with pytest.raises(ZoneInfoNotFoundError):
            get_timezone("Invalid/Timezone")


class TestGetCurrentTime:
    """Tests for get_current_time function."""
    
    def test_get_current_time_with_timezone(self):
        """Test getting current time in specific timezone."""
        tz = get_timezone("Europe/Berlin")
        now = get_current_time(tz)
        
        assert now.tzinfo is not None
        assert now.tzinfo.key == "Europe/Berlin"
    
    def test_get_current_time_utc(self):
        """Test getting current time in UTC (None parameter)."""
        now = get_current_time(None)
        
        assert now.tzinfo is not None
        assert now.tzinfo.key == "UTC"
    
    def test_get_current_time_is_recent(self):
        """Test that returned time is actually current."""
        now = get_current_time()
        
        # Should be in 2025-2027 range (current time when tests run)
        assert 2025 <= now.year <= 2027


class TestFormatTimestamp:
    """Tests for format_timestamp function."""
    
    def test_format_timestamp_default(self):
        """Test default timestamp formatting."""
        dt = datetime(2026, 1, 11, 10, 51, 6, tzinfo=ZoneInfo("Europe/Berlin"))
        result = format_timestamp(dt)
        
        assert "11.01.2026" in result
        assert "10:51:06" in result
        assert "CET" in result or "CEST" in result  # Depends on DST
    
    def test_format_timestamp_current_time(self):
        """Test formatting current time (None parameter)."""
        tz = get_timezone("Europe/Berlin")
        result = format_timestamp(timezone=tz)
        
        # Should contain year and timezone
        assert "202" in result  # 2025-2029
        assert "CET" in result or "CEST" in result
    
    def test_format_timestamp_custom_format(self):
        """Test custom format string."""
        dt = datetime(2026, 1, 11, 10, 51, 6, tzinfo=ZoneInfo("UTC"))
        result = format_timestamp(dt, fmt="%Y-%m-%d")
        
        assert result == "2026-01-11"
    
    def test_format_timestamp_naive_datetime(self):
        """Test formatting naive datetime with timezone."""
        dt = datetime(2026, 1, 11, 10, 51, 6)  # Naive datetime
        tz = get_timezone("Europe/Berlin")
        result = format_timestamp(dt, timezone=tz)
        
        assert "11.01.2026" in result
        assert "10:51:06" in result


class TestGetTimestampString:
    """Tests for get_timestamp_string function."""
    
    def test_get_timestamp_string_with_timezone(self):
        """Test getting timestamp string with timezone."""
        result = get_timestamp_string("Europe/Berlin")
        
        # Should contain current year
        assert "202" in result
        # Should contain timezone
        assert "CET" in result or "CEST" in result
    
    def test_get_timestamp_string_utc(self):
        """Test getting timestamp string in UTC."""
        result = get_timestamp_string(None)
        
        # Should contain current year
        assert "202" in result
        # Should contain UTC
        assert "UTC" in result
    
    def test_get_timestamp_string_format(self):
        """Test that timestamp string has expected format."""
        result = get_timestamp_string("Europe/Berlin")
        
        # Format should be: DD.MM.YYYY HH:MM:SS TZ
        parts = result.split()
        assert len(parts) >= 3  # Date, Time, Timezone
        
        # Date part should have dots
        assert "." in parts[0]
        # Time part should have colons
        assert ":" in parts[1]