"""Tests for Kraken data models."""

import pytest
from src.kraken.models import Ticker, Balance, OpenOrder, OrderResult


class TestTicker:
    """Tests for Ticker dataclass."""
    
    def test_from_api_response(self):
        """Test creating Ticker from API response."""
        api_data = {
            "a": ["77920.40000", "1", "1.000"],
            "b": ["77919.30000", "1", "1.000"],
            "c": ["77920.00000", "0.00100000"],
            "v": ["123.45678900", "234.56789000"]
        }
        
        ticker = Ticker.from_api_response("XXBTZEUR", api_data)
        
        assert ticker.pair == "XXBTZEUR"
        assert ticker.ask_price == 77920.40
        assert ticker.ask_volume == 1.0
        assert ticker.bid_price == 77919.30
        assert ticker.bid_volume == 1.0
        assert ticker.last_price == 77920.00
        assert ticker.volume_24h == 123.45678900


class TestBalance:
    """Tests for Balance dataclass."""
    
    def test_from_api_response(self):
        """Test creating Balance list from API response."""
        api_data = {
            "ZEUR": "1234.5678",
            "XXBT": "0.12345678"
        }
        
        balances = Balance.from_api_response(api_data)
        
        assert len(balances) == 2
        
        eur_balance = next(b for b in balances if b.currency == "ZEUR")
        assert eur_balance.amount == 1234.5678
        
        btc_balance = next(b for b in balances if b.currency == "XXBT")
        assert btc_balance.amount == 0.12345678
    
    def test_from_empty_response(self):
        """Test creating Balance list from empty response."""
        balances = Balance.from_api_response({})
        assert balances == []


class TestOpenOrder:
    """Tests for OpenOrder dataclass."""
    
    def test_from_api_response(self):
        """Test creating OpenOrder from API response."""
        api_data = {
            "descr": {
                "pair": "XXBTZEUR",
                "type": "buy",
                "ordertype": "limit",
                "price": "77000.0",
                "order": "buy 0.00025641 XXBTZEUR @ limit 77000.0"
            },
            "vol": "0.00025641"
        }
        
        order = OpenOrder.from_api_response("ORDER123", api_data)
        
        assert order.order_id == "ORDER123"
        assert order.pair == "XXBTZEUR"
        assert order.order_type == "buy"
        assert order.price == 77000.0
        assert order.volume == 0.00025641
        assert "buy 0.00025641" in order.description


class TestOrderResult:
    """Tests for OrderResult dataclass."""
    
    def test_from_validated_order(self):
        """Test creating OrderResult from validated order response."""
        api_data = {
            "descr": {
                "order": "buy 0.00025641 XXBTZEUR @ limit 77000.0"
            }
        }
        
        result = OrderResult.from_api_response(api_data, is_validated=True)
        
        assert result.is_validated is True
        assert result.order_ids == []
        assert "buy 0.00025641" in result.description
    
    def test_from_placed_order(self):
        """Test creating OrderResult from placed order response."""
        api_data = {
            "descr": {
                "order": "buy 0.00025641 XXBTZEUR @ limit 77000.0"
            },
            "txid": ["OUF4KD-GXYDB-3V6PQI"]
        }
        
        result = OrderResult.from_api_response(api_data, is_validated=False)
        
        assert result.is_validated is False
        assert result.order_ids == ["OUF4KD-GXYDB-3V6PQI"]
        assert "buy 0.00025641" in result.description