"""Timezone utilities for consistent timestamp handling.

This module provides timezone-aware datetime utilities for logging
and message formatting.
"""

from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo


def get_timezone(timezone_name: str) -> ZoneInfo:
    """Get timezone object from name.
    
    Args:
        timezone_name: Timezone name (e.g., "Europe/Berlin")
    
    Returns:
        ZoneInfo object for the timezone
    
    Raises:
        ZoneInfoNotFoundError: If timezone name is invalid
    
    Examples:
        >>> tz = get_timezone("Europe/Berlin")
        >>> tz.key
        'Europe/Berlin'
    """
    return ZoneInfo(timezone_name)


def get_current_time(timezone: Optional[ZoneInfo] = None) -> datetime:
    """Get current time in specified timezone.
    
    Args:
        timezone: ZoneInfo object. If None, returns UTC time.
    
    Returns:
        Current datetime in specified timezone
    
    Examples:
        >>> tz = get_timezone("Europe/Berlin")
        >>> now = get_current_time(tz)
        >>> now.tzinfo.key
        'Europe/Berlin'
    """
    if timezone is None:
        return datetime.now(ZoneInfo("UTC"))
    return datetime.now(timezone)


def format_timestamp(
    dt: Optional[datetime] = None,
    timezone: Optional[ZoneInfo] = None,
    fmt: str = "%d.%m.%Y %H:%M:%S %Z"
) -> str:
    """Format datetime as string in specified timezone.
    
    Args:
        dt: Datetime to format. If None, uses current time.
        timezone: Timezone for formatting. If None, uses UTC.
        fmt: strftime format string (default: German format with timezone)
    
    Returns:
        Formatted timestamp string
    
    Examples:
        >>> tz = get_timezone("Europe/Berlin")
        >>> ts = format_timestamp(timezone=tz)
        >>> "CET" in ts or "CEST" in ts  # Summer/Winter time
        True
    """
    if dt is None:
        dt = get_current_time(timezone)
    elif timezone is not None and dt.tzinfo is None:
        # If dt is naive, localize it to the specified timezone
        dt = dt.replace(tzinfo=timezone)
    
    return dt.strftime(fmt)


def get_timestamp_string(timezone_name: Optional[str] = None) -> str:
    """Get current timestamp as formatted string.
    
    Convenience function that combines timezone lookup and formatting.
    
    Args:
        timezone_name: Timezone name (e.g., "Europe/Berlin"). If None, uses UTC.
    
    Returns:
        Formatted timestamp string like "11.01.2026 10:51:06 CET"
    
    Examples:
        >>> ts = get_timestamp_string("Europe/Berlin")
        >>> len(ts) > 0
        True
        >>> "2026" in ts or "2025" in ts or "2027" in ts
        True
    """
    timezone = get_timezone(timezone_name) if timezone_name else None
    return format_timestamp(timezone=timezone)