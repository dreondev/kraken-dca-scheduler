"""DCA (Dollar Cost Averaging) scheduler logic.

This module contains the main business logic for executing
DCA Bitcoin purchases on Kraken with limit orders.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from .config import Config
from .kraken.client import KrakenClient
from .kraken.models import Ticker
from .notifications.ntfy import NtfyNotifier, NotificationError
from .utils.formatting import format_currency, format_btc, format_percentage, format_price
from .utils.timezone import get_timestamp_string


logger = logging.getLogger(__name__)


@dataclass
class DCAResult:
    """Result of a DCA execution.
    
    Attributes:
        success: Whether execution was successful
        message: Human-readable result message
        ticker: Current ticker information
        balance_eur: Total EUR balance
        free_balance_eur: Free EUR balance (after open orders)
        limit_price: Calculated limit price (None if insufficient funds)
        btc_volume: Calculated BTC volume (None if insufficient funds)
        order_placed: Whether order was actually placed
        insufficient_funds: Whether execution failed due to insufficient funds
    """
    
    success: bool
    message: str
    ticker: Ticker
    balance_eur: float
    free_balance_eur: float
    limit_price: Optional[float] = None
    btc_volume: Optional[float] = None
    order_placed: bool = False
    insufficient_funds: bool = False


class DCAScheduler:
    """Dollar Cost Averaging scheduler for Kraken.
    
    Executes DCA strategy:
    1. Check current BTC price
    2. Calculate limit order price (discount under Ask)
    3. Check available balance
    4. Place limit order if sufficient funds
    5. Send notification
    """
    
    def __init__(
        self,
        config: Config,
        kraken_client: KrakenClient,
        notifier: Optional[NtfyNotifier] = None,
    ):
        """Initialize DCA scheduler.
        
        Args:
            config: Application configuration
            kraken_client: Kraken API client
            notifier: Optional notification client
        """
        self._config = config
        self._kraken = kraken_client
        self._notifier = notifier
        
        logger.info("DCA Scheduler initialized")
    
    def execute(self) -> DCAResult:
        """Execute DCA strategy.
        
        Returns:
            DCAResult with execution details
        """
        logger.info("=" * 60)
        logger.info("Starting DCA execution")
        logger.info("=" * 60)
        
        try:
            # Step 1: Get current prices
            ticker = self._get_ticker()
            
            # Step 2: Check balance
            balance_eur = self._get_balance()
            free_balance = self._get_free_balance()
            
            # Step 3: Execute strategy
            if free_balance >= self._config.trade.amount_eur:
                result = self._execute_trade(ticker, balance_eur, free_balance)
            else:
                result = self._handle_insufficient_funds(ticker, balance_eur, free_balance)
            
            # Step 4: Send notification
            self._send_notification(result)
            
            logger.info(f"DCA execution completed: {result.success}")
            return result
            
        except Exception as e:
            logger.error(f"DCA execution failed: {e}", exc_info=True)
            error_result = self._create_error_result(str(e))
            self._send_notification(error_result)
            return error_result
    
    def _get_ticker(self) -> Ticker:
        """Get current ticker information.
        
        Returns:
            Ticker with current prices
        """
        logger.info(f"Fetching ticker for {self._config.kraken.pair}")
        ticker = self._kraken.get_ticker(self._config.kraken.pair)
        
        logger.info(
            f"Current prices: Ask={format_price(ticker.ask_price)}, "
            f"Bid={format_price(ticker.bid_price)}"
        )
        
        return ticker
    
    def _get_balance(self) -> float:
        """Get total EUR balance.
        
        Returns:
            Total EUR balance
        """
        balance = self._kraken.get_balance_by_currency("ZEUR")
        logger.info(f"Total EUR balance: {format_currency(balance)}")
        return balance
    
    def _get_free_balance(self) -> float:
        """Get free EUR balance (accounting for open orders).
        
        Returns:
            Free EUR balance
        """
        free_balance = self._kraken.calculate_free_balance("ZEUR")
        logger.info(f"Free EUR balance: {format_currency(free_balance)}")
        return free_balance
    
    def _execute_trade(
        self,
        ticker: Ticker,
        balance_eur: float,
        free_balance: float,
    ) -> DCAResult:
        """Execute trade with sufficient funds.
        
        Args:
            ticker: Current ticker information
            balance_eur: Total EUR balance
            free_balance: Free EUR balance
        
        Returns:
            DCAResult with trade execution details
        """
        logger.info("Sufficient funds available, proceeding with order")
        
        # Calculate order parameters
        limit_price = self._calculate_limit_price(ticker.ask_price)
        btc_volume = self._calculate_btc_volume(limit_price)
        
        logger.info(
            f"Order parameters: {format_btc(btc_volume)} @ "
            f"{format_currency(limit_price, decimals=1)}"
        )
        
        # Place order
        try:
            order_result = self._kraken.place_limit_order(
                pair=self._config.kraken.pair,
                volume=btc_volume,
                price=limit_price,
                validate=self._config.trade.validate_order,
            )
            
            action = "validated" if self._config.trade.validate_order else "placed"
            logger.info(f"Order {action} successfully: {order_result.description}")
            
            message = self._build_success_message(
                ticker, balance_eur, free_balance, limit_price, btc_volume
            )
            
            return DCAResult(
                success=True,
                message=message,
                ticker=ticker,
                balance_eur=balance_eur,
                free_balance_eur=free_balance,
                limit_price=limit_price,
                btc_volume=btc_volume,
                order_placed=not self._config.trade.validate_order,
            )
            
        except Exception as e:
            logger.error(f"Order placement failed: {e}")
            message = self._build_error_message(
                ticker, balance_eur, free_balance, limit_price, btc_volume, str(e)
            )
            
            return DCAResult(
                success=False,
                message=message,
                ticker=ticker,
                balance_eur=balance_eur,
                free_balance_eur=free_balance,
                limit_price=limit_price,
                btc_volume=btc_volume,
                order_placed=False,
            )
    
    def _handle_insufficient_funds(
        self,
        ticker: Ticker,
        balance_eur: float,
        free_balance: float,
    ) -> DCAResult:
        """Handle case of insufficient funds.
        
        Args:
            ticker: Current ticker information
            balance_eur: Total EUR balance
            free_balance: Free EUR balance
        
        Returns:
            DCAResult indicating insufficient funds
        """
        logger.warning(
            f"Insufficient funds: Need {format_currency(self._config.trade.amount_eur)}, "
            f"have {format_currency(free_balance)} available"
        )
        
        # Calculate what the order would have been
        limit_price = self._calculate_limit_price(ticker.ask_price)
        btc_volume = self._calculate_btc_volume(limit_price)
        
        message = self._build_insufficient_funds_message(
            ticker, balance_eur, free_balance, limit_price, btc_volume
        )
        
        return DCAResult(
            success=True,  # Not an error, just insufficient funds
            message=message,
            ticker=ticker,
            balance_eur=balance_eur,
            free_balance_eur=free_balance,
            limit_price=limit_price,
            btc_volume=btc_volume,
            order_placed=False,
            insufficient_funds=True,
        )
    
    def _calculate_limit_price(self, ask_price: float) -> float:
        """Calculate limit price with discount under ask.
        
        Args:
            ask_price: Current ask price
        
        Returns:
            Limit price rounded to 1 decimal
        """
        discount_decimal = self._config.trade.discount_percent / 100
        limit_price = ask_price * (1 - discount_decimal)
        return round(limit_price, 1)
    
    def _calculate_btc_volume(self, limit_price: float) -> float:
        """Calculate BTC volume for given limit price.
        
        Args:
            limit_price: Limit order price
        
        Returns:
            BTC volume to purchase
        """
        return self._config.trade.amount_eur / limit_price
    
    def _build_success_message(
        self,
        ticker: Ticker,
        balance_eur: float,
        free_balance: float,
        limit_price: float,
        btc_volume: float,
    ) -> str:
        """Build success notification message.
        
        Args:
            ticker: Current ticker
            balance_eur: Total balance
            free_balance: Free balance
            limit_price: Order limit price
            btc_volume: Order BTC volume
        
        Returns:
            Formatted message string
        """
        timestamp = get_timestamp_string(self._config.general.timezone)
        validate_mode = self._config.trade.validate_order
        
        action = "Order validated" if validate_mode else "Order placed"
        
        return (
            f"{action} on {timestamp}\n\n"
            f"Amount: {format_currency(self._config.trade.amount_eur)}\n"
            f"Limit Price: {format_currency(limit_price, decimals=1)}\n"
            f"BTC Volume: {format_btc(btc_volume)}\n"
            f"Discount: {format_percentage(self._config.trade.discount_percent / 100)} under Ask\n\n"
            f"Total EUR: {format_currency(balance_eur)}\n"
            f"Available: {format_currency(free_balance)}\n\n"
            f"Ask: {format_currency(ticker.ask_price)} | "
            f"Bid: {format_currency(ticker.bid_price)}"
        )
    
    def _build_error_message(
        self,
        ticker: Ticker,
        balance_eur: float,
        free_balance: float,
        limit_price: float,
        btc_volume: float,
        error: str,
    ) -> str:
        """Build error notification message.
        
        Args:
            ticker: Current ticker
            balance_eur: Total balance
            free_balance: Free balance
            limit_price: Order limit price
            btc_volume: Order BTC volume
            error: Error message
        
        Returns:
            Formatted message string
        """
        base_msg = self._build_success_message(
            ticker, balance_eur, free_balance, limit_price, btc_volume
        )
        return f"{base_msg}\n\n❌ Error: {error}"
    
    def _build_insufficient_funds_message(
        self,
        ticker: Ticker,
        balance_eur: float,
        free_balance: float,
        limit_price: float,
        btc_volume: float,
    ) -> str:
        """Build insufficient funds notification message.
        
        Args:
            ticker: Current ticker
            balance_eur: Total balance
            free_balance: Free balance
            limit_price: Planned limit price
            btc_volume: Planned BTC volume
        
        Returns:
            Formatted message string
        """
        timestamp = get_timestamp_string(self._config.general.timezone)
        
        return (
            f"⚠️ Insufficient funds on {timestamp}\n\n"
            f"Planned order:\n"
            f"Amount: {format_currency(self._config.trade.amount_eur)}\n"
            f"Limit Price: {format_currency(limit_price, decimals=1)}\n"
            f"BTC Volume: {format_btc(btc_volume)}\n"
            f"Discount: {format_percentage(self._config.trade.discount_percent / 100)} under Ask\n\n"
            f"Total EUR: {format_currency(balance_eur)}\n"
            f"Available: {format_currency(free_balance)}\n\n"
            f"Ask: {format_currency(ticker.ask_price)} | "
            f"Bid: {format_currency(ticker.bid_price)}"
        )
    
    def _create_error_result(self, error: str) -> DCAResult:
        """Create error result when execution fails completely.
        
        Args:
            error: Error message
        
        Returns:
            DCAResult indicating failure
        """
        timestamp = get_timestamp_string(self._config.general.timezone)
        message = f"❌ DCA execution failed on {timestamp}\n\nError: {error}"
        
        # Create dummy ticker with zero values
        from .kraken.models import Ticker
        dummy_ticker = Ticker(
            ask_price=0.0,
            ask_volume=0.0,
            bid_price=0.0,
            bid_volume=0.0,
            last_price=0.0,
            volume_24h=0.0,
            pair=self._config.kraken.pair,
        )
        
        return DCAResult(
            success=False,
            message=message,
            ticker=dummy_ticker,
            balance_eur=0.0,
            free_balance_eur=0.0,
        )
    
    def _send_notification(self, result: DCAResult) -> None:
        """Send notification about DCA execution result.
        
        Args:
            result: DCA execution result
        """
        if not self._notifier:
            logger.info("No notifier configured, skipping notification")
            return
        
        try:
            if not result.success:
                self._notifier.send_error(result.message, title="❌ DCA Error")
            elif result.insufficient_funds:
                self._notifier.send_info(result.message, title="⚠️ Insufficient Funds")
            else:
                self._notifier.send_success(result.message, title="✅ DCA Executed")
            
            logger.info("Notification sent successfully")
            
        except NotificationError as e:
            logger.error(f"Failed to send notification: {e}")