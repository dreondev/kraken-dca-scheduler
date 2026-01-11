"""Tests for DCA scheduler logic."""

import pytest
from unittest.mock import Mock, patch
from src.scheduler import DCAScheduler, DCAResult
from src.config import Config, GeneralConfig, KrakenConfig, TradeConfig
from src.kraken.models import Ticker, OrderResult


@pytest.fixture
def config():
    """Create test configuration."""
    return Config(
        general=GeneralConfig(timezone="Europe/Berlin", log_level="INFO"),
        kraken=KrakenConfig(api_key="test_key", api_secret="test_secret", pair="XXBTZEUR"),
        trade=TradeConfig(
            amount_eur=20.0,
            discount_percent=0.5,
            validate_order=True,
            min_free_balance=0.0
        ),
    )


@pytest.fixture
def mock_kraken():
    """Create mock Kraken client."""
    return Mock()


@pytest.fixture
def mock_notifier():
    """Create mock notifier."""
    return Mock()


@pytest.fixture
def scheduler(config, mock_kraken, mock_notifier):
    """Create DCA scheduler with mocks."""
    return DCAScheduler(config, mock_kraken, mock_notifier)


@pytest.fixture
def sample_ticker():
    """Create sample ticker."""
    return Ticker(
        ask_price=77920.40,
        ask_volume=1.0,
        bid_price=77919.30,
        bid_volume=1.0,
        last_price=77920.00,
        volume_24h=123.45,
        pair="XXBTZEUR",
    )


class TestDCASchedulerInit:
    """Tests for DCAScheduler initialization."""
    
    def test_init(self, config, mock_kraken, mock_notifier):
        """Test scheduler initialization."""
        scheduler = DCAScheduler(config, mock_kraken, mock_notifier)
        
        assert scheduler._config == config
        assert scheduler._kraken == mock_kraken
        assert scheduler._notifier == mock_notifier


class TestExecuteWithSufficientFunds:
    """Tests for execute() with sufficient funds."""
    
    def test_execute_success(self, scheduler, mock_kraken, mock_notifier, sample_ticker):
        """Test successful execution with order placement."""
        # Setup mocks
        mock_kraken.get_ticker.return_value = sample_ticker
        mock_kraken.get_balance_by_currency.return_value = 1000.0
        mock_kraken.calculate_free_balance.return_value = 100.0
        mock_kraken.place_limit_order.return_value = OrderResult(
            order_ids=[],
            description="buy 0.00025641 XXBTZEUR @ limit 77531.5",
            is_validated=True,
        )
        
        # Execute
        result = scheduler.execute()
        
        # Verify
        assert result.success is True
        assert result.order_placed is False  # validate_order=True
        assert result.insufficient_funds is False
        assert result.balance_eur == 1000.0
        assert result.free_balance_eur == 100.0
        assert result.limit_price is not None
        assert result.btc_volume is not None
        
        # Verify Kraken client calls
        mock_kraken.get_ticker.assert_called_once()
        mock_kraken.get_balance_by_currency.assert_called_once()
        mock_kraken.calculate_free_balance.assert_called_once()
        mock_kraken.place_limit_order.assert_called_once()
        
        # Verify notification
        mock_notifier.send_success.assert_called_once()
    
    def test_execute_actual_order(self, scheduler, mock_kraken, mock_notifier, sample_ticker, config):
        """Test execution with actual order placement (validate=False)."""
        # Change config to place actual orders
        scheduler._config.trade.validate_order = False
        
        # Setup mocks
        mock_kraken.get_ticker.return_value = sample_ticker
        mock_kraken.get_balance_by_currency.return_value = 1000.0
        mock_kraken.calculate_free_balance.return_value = 100.0
        mock_kraken.place_limit_order.return_value = OrderResult(
            order_ids=["ORDER123"],
            description="buy 0.00025641 XXBTZEUR @ limit 77531.5",
            is_validated=False,
        )
        
        # Execute
        result = scheduler.execute()
        
        # Verify order was placed
        assert result.order_placed is True
        
        # Verify the call was made (with approximate values for floating point)
        call_args = mock_kraken.place_limit_order.call_args
        assert call_args[1]["pair"] == "XXBTZEUR"
        assert call_args[1]["volume"] == pytest.approx(0.000258, abs=0.00001)
        assert call_args[1]["price"] == pytest.approx(77531.5, abs=1.0)
        assert call_args[1]["validate"] is False


class TestExecuteWithInsufficientFunds:
    """Tests for execute() with insufficient funds."""
    
    def test_execute_insufficient_funds(self, scheduler, mock_kraken, mock_notifier, sample_ticker):
        """Test execution when insufficient funds."""
        # Setup mocks - free balance less than amount_eur
        mock_kraken.get_ticker.return_value = sample_ticker
        mock_kraken.get_balance_by_currency.return_value = 50.0
        mock_kraken.calculate_free_balance.return_value = 10.0  # Less than 20.0 needed
        
        # Execute
        result = scheduler.execute()
        
        # Verify
        assert result.success is True  # Not an error, just info
        assert result.insufficient_funds is True
        assert result.order_placed is False
        assert result.free_balance_eur == 10.0
        assert result.limit_price is not None  # Calculated but not used
        assert result.btc_volume is not None
        
        # Verify no order placed
        mock_kraken.place_limit_order.assert_not_called()
        
        # Verify info notification
        mock_notifier.send_info.assert_called_once()


class TestExecuteWithErrors:
    """Tests for execute() with various errors."""
    
    def test_execute_ticker_error(self, scheduler, mock_kraken, mock_notifier):
        """Test execution when ticker fetch fails."""
        mock_kraken.get_ticker.side_effect = Exception("API error")
        
        # Execute
        result = scheduler.execute()
        
        # Verify
        assert result.success is False
        assert "API error" in result.message
        
        # Verify error notification
        mock_notifier.send_error.assert_called_once()
    
    def test_execute_order_placement_error(self, scheduler, mock_kraken, mock_notifier, sample_ticker):
        """Test execution when order placement fails."""
        # Setup mocks
        mock_kraken.get_ticker.return_value = sample_ticker
        mock_kraken.get_balance_by_currency.return_value = 1000.0
        mock_kraken.calculate_free_balance.return_value = 100.0
        mock_kraken.place_limit_order.side_effect = Exception("Order failed")
        
        # Execute
        result = scheduler.execute()
        
        # Verify
        assert result.success is False
        assert "Order failed" in result.message
        assert result.order_placed is False
        
        # Verify error notification
        mock_notifier.send_error.assert_called_once()


class TestCalculations:
    """Tests for calculation methods."""
    
    def test_calculate_limit_price(self, scheduler):
        """Test limit price calculation."""
        # 0.5% discount: 77920.40 * (1 - 0.005) = 77531.498
        # Python round() to 1 decimal: 77530.8 (banker's rounding)
        limit_price = scheduler._calculate_limit_price(77920.40)
        
        assert limit_price == pytest.approx(77531.5, abs=1.0)  # Allow 1 EUR tolerance
    
    def test_calculate_btc_volume(self, scheduler):
        """Test BTC volume calculation."""
        # 20 EUR / 77531.5 = 0.000258...
        btc_volume = scheduler._calculate_btc_volume(77531.5)
        
        assert btc_volume == pytest.approx(0.000258, abs=0.0001)
    
    def test_calculate_with_different_discount(self, scheduler):
        """Test calculation with different discount."""
        scheduler._config.trade.discount_percent = 1.0
        
        # 1% discount: 77920.40 * (1 - 0.01) = 77141.196
        # Rounded: 77141.2
        limit_price = scheduler._calculate_limit_price(77920.40)
        
        assert limit_price == 77141.2


class TestNotifications:
    """Tests for notification handling."""
    
    def test_no_notifier(self, config, mock_kraken):
        """Test execution without notifier."""
        scheduler = DCAScheduler(config, mock_kraken, notifier=None)
        
        # Setup mocks
        sample_ticker = Ticker(
            ask_price=77920.40,
            ask_volume=1.0,
            bid_price=77919.30,
            bid_volume=1.0,
            last_price=77920.00,
            volume_24h=123.45,
            pair="XXBTZEUR",
        )
        mock_kraken.get_ticker.return_value = sample_ticker
        mock_kraken.get_balance_by_currency.return_value = 1000.0
        mock_kraken.calculate_free_balance.return_value = 100.0
        mock_kraken.place_limit_order.return_value = OrderResult(
            order_ids=[],
            description="test order",
            is_validated=True,
        )
        
        # Execute - should not fail without notifier
        result = scheduler.execute()
        
        assert result.success is True
    
    def test_notification_failure(self, scheduler, mock_kraken, mock_notifier, sample_ticker):
        """Test that notification failure doesn't break execution."""
        from src.notifications.ntfy import NotificationError
        
        # Setup mocks
        mock_kraken.get_ticker.return_value = sample_ticker
        mock_kraken.get_balance_by_currency.return_value = 1000.0
        mock_kraken.calculate_free_balance.return_value = 100.0
        mock_kraken.place_limit_order.return_value = OrderResult(
            order_ids=[],
            description="test order",
            is_validated=True,
        )
        mock_notifier.send_success.side_effect = NotificationError("Network error")
        
        # Execute - should complete despite notification failure
        result = scheduler.execute()
        
        assert result.success is True  # Execution succeeded
        mock_notifier.send_success.assert_called_once()


class TestMessageBuilding:
    """Tests for message building methods."""
    
    def test_build_success_message(self, scheduler, sample_ticker):
        """Test success message building."""
        message = scheduler._build_success_message(
            ticker=sample_ticker,
            balance_eur=1000.0,
            free_balance=100.0,
            limit_price=77531.5,
            btc_volume=0.000258,
        )
        
        assert "Order validated" in message
        assert "20,00 EUR" in message
        assert "77.531,5 EUR" in message
        assert "0,00025800 BTC" in message
        assert "0,50%" in message
        assert "1.000,00 EUR" in message
        assert "100,00 EUR" in message
    
    def test_build_error_message(self, scheduler, sample_ticker):
        """Test error message building."""
        message = scheduler._build_error_message(
            ticker=sample_ticker,
            balance_eur=1000.0,
            free_balance=100.0,
            limit_price=77531.5,
            btc_volume=0.000258,
            error="Test error",
        )
        
        assert "❌ Error: Test error" in message
        assert "20,00 EUR" in message
    
    def test_build_insufficient_funds_message(self, scheduler, sample_ticker):
        """Test insufficient funds message building."""
        message = scheduler._build_insufficient_funds_message(
            ticker=sample_ticker,
            balance_eur=50.0,
            free_balance=10.0,
            limit_price=77531.5,
            btc_volume=0.000258,
        )
        
        assert "⚠️ Insufficient funds" in message
        assert "Planned order" in message
        assert "50,00 EUR" in message
        assert "10,00 EUR" in message


class TestDCAResult:
    """Tests for DCAResult dataclass."""
    
    def test_dca_result_creation(self, sample_ticker):
        """Test creating DCAResult."""
        result = DCAResult(
            success=True,
            message="Test message",
            ticker=sample_ticker,
            balance_eur=1000.0,
            free_balance_eur=100.0,
            limit_price=77531.5,
            btc_volume=0.000258,
            order_placed=True,
            insufficient_funds=False,
        )
        
        assert result.success is True
        assert result.message == "Test message"
        assert result.ticker == sample_ticker
        assert result.balance_eur == 1000.0
        assert result.order_placed is True