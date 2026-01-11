"""Tests for formatting utilities."""

import pytest
from src.utils.formatting import (
    format_currency,
    format_number,
    format_percentage,
    format_btc,
    format_price,
)


class TestFormatCurrency:
    """Tests for format_currency function."""
    
    def test_format_currency_basic(self):
        """Test basic currency formatting."""
        result = format_currency(1234.56)
        assert result == "1.234,56 EUR"
    
    def test_format_currency_with_thousands(self):
        """Test formatting with thousands separator."""
        result = format_currency(1234567.89)
        assert result == "1.234.567,89 EUR"
    
    def test_format_currency_small_amount(self):
        """Test formatting small amounts."""
        result = format_currency(0.01)
        assert result == "0,01 EUR"
    
    def test_format_currency_zero(self):
        """Test formatting zero."""
        result = format_currency(0.0)
        assert result == "0,00 EUR"
    
    def test_format_currency_custom_decimals(self):
        """Test custom decimal places."""
        result = format_currency(1234.567, decimals=3)
        assert result == "1.234,567 EUR"
    
    def test_format_currency_custom_currency(self):
        """Test custom currency code."""
        result = format_currency(100.0, currency="USD")
        assert result == "100,00 USD"


class TestFormatNumber:
    """Tests for format_number function."""
    
    def test_format_number_basic(self):
        """Test basic number formatting."""
        result = format_number(1234.56)
        assert result == "1.234,56"
    
    def test_format_number_large(self):
        """Test formatting large numbers."""
        result = format_number(77920.40)
        assert result == "77.920,40"
    
    def test_format_number_custom_decimals(self):
        """Test custom decimal places."""
        result = format_number(123.456, decimals=1)
        assert result == "123,5"


class TestFormatPercentage:
    """Tests for format_percentage function."""
    
    def test_format_percentage_basic(self):
        """Test basic percentage formatting."""
        result = format_percentage(0.005)
        assert result == "0,50%"
    
    def test_format_percentage_larger(self):
        """Test larger percentage."""
        result = format_percentage(0.1234)
        assert result == "12,34%"
    
    def test_format_percentage_custom_decimals(self):
        """Test custom decimal places."""
        result = format_percentage(0.123456, decimals=4)
        assert result == "12,3456%"


class TestFormatBTC:
    """Tests for format_btc function."""
    
    def test_format_btc_small_amount(self):
        """Test formatting small BTC amounts."""
        result = format_btc(0.00012345)
        assert result == "0,00012345 BTC"
    
    def test_format_btc_larger_amount(self):
        """Test formatting larger BTC amounts."""
        result = format_btc(1.23456789)
        assert result == "1,23456789 BTC"
    
    def test_format_btc_custom_decimals(self):
        """Test custom decimal places."""
        result = format_btc(0.123, decimals=4)
        assert result == "0,1230 BTC"


class TestFormatPrice:
    """Tests for format_price function."""
    
    def test_format_price_basic(self):
        """Test basic price formatting."""
        result = format_price(77920.40)
        assert result == "77.920,40"
    
    def test_format_price_from_log(self):
        """Test price formatting matching your log output."""
        # From your log: Ask=77.920,40
        result = format_price(77920.40)
        assert result == "77.920,40"