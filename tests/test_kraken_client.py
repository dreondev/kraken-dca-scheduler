"""Tests for Kraken API client."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.kraken.client import KrakenClient, KrakenAPIError
from src.kraken.models import Ticker, OpenOrder, OrderResult


@pytest.fixture
def mock_kraken_api():
    """Create a mock krakenex.API instance."""
    with patch('src.kraken.client.krakenex.API') as mock_api_class:
        mock_instance = Mock()
        mock_api_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def client(mock_kraken_api):
    """Create KrakenClient with mocked API."""
    return KrakenClient(
        api_key="test_key",
        api_secret="test_secret",
        max_retries=3,
        retry_delay=0.1  # Short delay for tests
    )


class TestKrakenClientInit:
    """Tests for KrakenClient initialization."""
    
    def test_init(self, mock_kraken_api):
        """Test client initialization."""
        client = KrakenClient(
            api_key="test_key",
            api_secret="test_secret"
        )
        
        assert client._max_retries == 3
        assert client._retry_delay == 1.0


class TestGetTicker:
    """Tests for get_ticker method."""
    
    def test_get_ticker_success(self, client, mock_kraken_api):
        """Test successful ticker fetch."""
        mock_kraken_api.query_public.return_value = {
            "error": [],
            "result": {
                "XXBTZEUR": {
                    "a": ["77920.40000", "1", "1.000"],
                    "b": ["77919.30000", "1", "1.000"],
                    "c": ["77920.00000", "0.00100000"],
                    "v": ["123.45", "234.56"]
                }
            }
        }
        
        ticker = client.get_ticker("XXBTZEUR")
        
        assert isinstance(ticker, Ticker)
        assert ticker.ask_price == 77920.40
        assert ticker.bid_price == 77919.30
        assert ticker.pair == "XXBTZEUR"
    
    def test_get_ticker_api_error(self, client, mock_kraken_api):
        """Test ticker fetch with API error."""
        mock_kraken_api.query_public.return_value = {
            "error": ["Invalid pair"]
        }
        
        with pytest.raises(KrakenAPIError, match="Invalid pair"):
            client.get_ticker("INVALID")
    
    def test_get_ticker_missing_pair(self, client, mock_kraken_api):
        """Test ticker fetch with missing pair in response."""
        mock_kraken_api.query_public.return_value = {
            "error": [],
            "result": {}
        }
        
        with pytest.raises(KrakenAPIError, match="Ticker data not found"):
            client.get_ticker("XXBTZEUR")


class TestGetBalance:
    """Tests for get_balance method."""
    
    def test_get_balance_success(self, client, mock_kraken_api):
        """Test successful balance fetch."""
        mock_kraken_api.query_private.return_value = {
            "error": [],
            "result": {
                "ZEUR": "1234.5678",
                "XXBT": "0.12345678"
            }
        }
        
        balances = client.get_balance()
        
        assert balances["ZEUR"] == 1234.5678
        assert balances["XXBT"] == 0.12345678
    
    def test_get_balance_by_currency(self, client, mock_kraken_api):
        """Test getting balance for specific currency."""
        mock_kraken_api.query_private.return_value = {
            "error": [],
            "result": {
                "ZEUR": "1234.5678",
                "XXBT": "0.12345678"
            }
        }
        
        eur_balance = client.get_balance_by_currency("ZEUR")
        
        assert eur_balance == 1234.5678
    
    def test_get_balance_by_currency_missing(self, client, mock_kraken_api):
        """Test getting balance for non-existent currency."""
        mock_kraken_api.query_private.return_value = {
            "error": [],
            "result": {
                "ZEUR": "1234.5678"
            }
        }
        
        balance = client.get_balance_by_currency("XUSD")
        
        assert balance == 0.0


class TestGetOpenOrders:
    """Tests for get_open_orders method."""
    
    def test_get_open_orders_success(self, client, mock_kraken_api):
        """Test successful open orders fetch."""
        mock_kraken_api.query_private.return_value = {
            "error": [],
            "result": {
                "open": {
                    "ORDER1": {
                        "descr": {
                            "pair": "XXBTZEUR",
                            "type": "buy",
                            "price": "77000.0",
                            "order": "buy 0.0001 XXBTZEUR @ limit 77000.0"
                        },
                        "vol": "0.0001"
                    }
                }
            }
        }
        
        orders = client.get_open_orders()
        
        assert len(orders) == 1
        assert orders[0].order_id == "ORDER1"
        assert orders[0].pair == "XXBTZEUR"
    
    def test_get_open_orders_empty(self, client, mock_kraken_api):
        """Test fetching when no open orders."""
        mock_kraken_api.query_private.return_value = {
            "error": [],
            "result": {
                "open": {}
            }
        }
        
        orders = client.get_open_orders()
        
        assert orders == []


class TestCalculateFreeBalance:
    """Tests for calculate_free_balance method."""
    
    def test_calculate_free_balance_no_orders(self, client, mock_kraken_api):
        """Test free balance calculation with no open orders."""
        mock_kraken_api.query_private.side_effect = [
            # First call: Balance
            {
                "error": [],
                "result": {"ZEUR": "1000.0"}
            },
            # Second call: OpenOrders
            {
                "error": [],
                "result": {"open": {}}
            }
        ]
        
        free_balance = client.calculate_free_balance("ZEUR")
        
        assert free_balance == 1000.0
    
    def test_calculate_free_balance_with_orders(self, client, mock_kraken_api):
        """Test free balance calculation with open orders."""
        mock_kraken_api.query_private.side_effect = [
            # First call: Balance
            {
                "error": [],
                "result": {"ZEUR": "1000.0"}
            },
            # Second call: OpenOrders
            {
                "error": [],
                "result": {
                    "open": {
                        "ORDER1": {
                            "descr": {
                                "type": "buy",
                                "price": "100.0",
                                "order": "buy 2.0 @ limit 100.0"
                            },
                            "vol": "2.0"
                        }
                    }
                }
            }
        ]
        
        # Reserved: 2.0 * 100.0 * 1.005 = 201.0
        # Free: 1000.0 - 201.0 = 799.0
        free_balance = client.calculate_free_balance("ZEUR", fee_buffer=1.005)
        
        assert free_balance == 799.0


class TestPlaceLimitOrder:
    """Tests for place_limit_order method."""
    
    def test_place_limit_order_validate(self, client, mock_kraken_api):
        """Test placing order in validation mode."""
        mock_kraken_api.query_private.return_value = {
            "error": [],
            "result": {
                "descr": {
                    "order": "buy 0.0001 XXBTZEUR @ limit 77000.0"
                }
            }
        }
        
        result = client.place_limit_order(
            pair="XXBTZEUR",
            volume=0.0001,
            price=77000.0,
            validate=True
        )
        
        assert isinstance(result, OrderResult)
        assert result.is_validated is True
        assert result.order_ids == []
    
    def test_place_limit_order_actual(self, client, mock_kraken_api):
        """Test placing actual order."""
        mock_kraken_api.query_private.return_value = {
            "error": [],
            "result": {
                "descr": {
                    "order": "buy 0.0001 XXBTZEUR @ limit 77000.0"
                },
                "txid": ["ORDER123"]
            }
        }
        
        result = client.place_limit_order(
            pair="XXBTZEUR",
            volume=0.0001,
            price=77000.0,
            validate=False
        )
        
        assert isinstance(result, OrderResult)
        assert result.is_validated is False
        assert result.order_ids == ["ORDER123"]


class TestRetryLogic:
    """Tests for retry logic."""
    
    def test_retry_on_transient_error(self, client, mock_kraken_api):
        """Test that client retries on transient errors."""
        # First two calls fail, third succeeds
        mock_kraken_api.query_public.side_effect = [
            Exception("Connection timeout"),
            Exception("Connection timeout"),
            {
                "error": [],
                "result": {
                    "XXBTZEUR": {
                        "a": ["77920.40000", "1", "1.000"],
                        "b": ["77919.30000", "1", "1.000"],
                        "c": ["77920.00000", "0.00100000"],
                        "v": ["123.45", "234.56"]
                    }
                }
            }
        ]
        
        ticker = client.get_ticker("XXBTZEUR")
        
        assert ticker.ask_price == 77920.40
        assert mock_kraken_api.query_public.call_count == 3
    
    def test_no_retry_on_api_error(self, client, mock_kraken_api):
        """Test that client doesn't retry on API errors."""
        mock_kraken_api.query_public.return_value = {
            "error": ["Invalid pair"]
        }
        
        with pytest.raises(KrakenAPIError, match="Invalid pair"):
            client.get_ticker("INVALID")
        
        # Should only be called once (no retries for API errors)
        assert mock_kraken_api.query_public.call_count == 1
    
    def test_all_retries_fail(self, client, mock_kraken_api):
        """Test that exception is raised after all retries fail."""
        mock_kraken_api.query_public.side_effect = Exception("Connection timeout")
        
        with pytest.raises(KrakenAPIError, match="failed after 3 retries"):
            client.get_ticker("XXBTZEUR")
        
        assert mock_kraken_api.query_public.call_count == 3