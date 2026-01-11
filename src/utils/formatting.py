"""Formatting utilities for numbers and currencies.

This module provides locale-independent formatting functions for
displaying numbers, currencies, and percentages in a consistent way.
"""

from typing import Optional


def format_currency(amount: float, currency: str = "EUR", decimals: int = 2) -> str:
    """Format amount as currency with thousands separator.
    
    Args:
        amount: The amount to format
        currency: Currency code (default: EUR)
        decimals: Number of decimal places (default: 2)
    
    Returns:
        Formatted string like "1.234,56 EUR"
    
    Examples:
        >>> format_currency(1234.56)
        '1.234,56 EUR'
        >>> format_currency(1234.567, decimals=3)
        '1.234,567 EUR'
    """
    # Format with thousands separator (German style: . for thousands, , for decimals)
    formatted = f"{amount:,.{decimals}f}"
    # Replace . and , for German locale
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{formatted} {currency}"


def format_number(number: float, decimals: int = 2) -> str:
    """Format number with thousands separator.
    
    Args:
        number: The number to format
        decimals: Number of decimal places (default: 2)
    
    Returns:
        Formatted string like "1.234,56"
    
    Examples:
        >>> format_number(1234.56)
        '1.234,56'
        >>> format_number(1234567.89)
        '1.234.567,89'
    """
    formatted = f"{number:,.{decimals}f}"
    # Replace . and , for German locale
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return formatted


def format_percentage(value: float, decimals: int = 2) -> str:
    """Format value as percentage.
    
    Args:
        value: The value to format (e.g., 0.005 for 0.5%)
        decimals: Number of decimal places (default: 2)
    
    Returns:
        Formatted string like "0,50%"
    
    Examples:
        >>> format_percentage(0.005)
        '0,50%'
        >>> format_percentage(0.1234, decimals=4)
        '12,3400%'
    """
    percent = value * 100
    formatted = format_number(percent, decimals)
    return f"{formatted}%"


def format_btc(amount: float, decimals: int = 8) -> str:
    """Format Bitcoin amount with proper precision.
    
    Args:
        amount: BTC amount to format
        decimals: Number of decimal places (default: 8)
    
    Returns:
        Formatted string like "0.00012345 BTC"
    
    Examples:
        >>> format_btc(0.00012345)
        '0,00012345 BTC'
        >>> format_btc(1.23456789)
        '1,23456789 BTC'
    """
    formatted = f"{amount:.{decimals}f}"
    # Replace . with , for German locale
    formatted = formatted.replace(".", ",")
    return f"{formatted} BTC"


def format_price(price: float, decimals: int = 2) -> str:
    """Format price with thousands separator (no currency).
    
    This is a convenience function for formatting prices in messages.
    
    Args:
        price: The price to format
        decimals: Number of decimal places (default: 2)
    
    Returns:
        Formatted string like "77.920,40"
    
    Examples:
        >>> format_price(77920.40)
        '77.920,40'
    """
    return format_number(price, decimals)