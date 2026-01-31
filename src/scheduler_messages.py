"""Message building for DCA notifications.

This module contains functions for building notification messages
for different DCA execution outcomes.
"""

from .config import Config
from .kraken.models import Ticker
from .utils.formatting import format_currency, format_btc, format_percentage
from .utils.timezone import get_timestamp_string


def build_success_message(
    config: Config,
    ticker: Ticker,
    balance_eur: float,
    free_balance: float,
    limit_price: float,
    btc_volume: float,
) -> str:
    """Build success notification message.
    
    Args:
        config: Application configuration
        ticker: Current ticker
        balance_eur: Total balance
        free_balance: Free balance
        limit_price: Order limit price
        btc_volume: Order BTC volume
    
    Returns:
        Formatted message string
    """
    timestamp = get_timestamp_string(config.general.timezone)
    validate_mode = config.trade.validate_order
    post_only = config.trade.post_only
    
    action = "Order validated" if validate_mode else "Order placed"
    post_only_info = " (post-only)" if post_only else ""
    
    return (
        f"{action}{post_only_info} on {timestamp}\n\n"
        f"Amount: {format_currency(config.trade.amount_eur)}\n"
        f"Limit Price: {format_currency(limit_price, decimals=1)}\n"
        f"BTC Volume: {format_btc(btc_volume)}\n"
        f"Discount: {format_percentage(config.trade.discount_percent / 100)} under Ask\n\n"
        f"Total EUR: {format_currency(balance_eur)}\n"
        f"Available: {format_currency(free_balance)}\n\n"
        f"Ask: {format_currency(ticker.ask_price)} | "
        f"Bid: {format_currency(ticker.bid_price)}"
    )


def build_error_message(
    config: Config,
    ticker: Ticker,
    balance_eur: float,
    free_balance: float,
    limit_price: float,
    btc_volume: float,
    error: str,
) -> str:
    """Build error notification message.
    
    Args:
        config: Application configuration
        ticker: Current ticker
        balance_eur: Total balance
        free_balance: Free balance
        limit_price: Order limit price
        btc_volume: Order BTC volume
        error: Error message
    
    Returns:
        Formatted message string
    """
    base_msg = build_success_message(
        config, ticker, balance_eur, free_balance, limit_price, btc_volume
    )
    return f"{base_msg}\n\n❌ Error: {error}"


def build_insufficient_funds_message(
    config: Config,
    ticker: Ticker,
    balance_eur: float,
    free_balance: float,
    limit_price: float,
    btc_volume: float,
) -> str:
    """Build insufficient funds notification message.
    
    Args:
        config: Application configuration
        ticker: Current ticker
        balance_eur: Total balance
        free_balance: Free balance
        limit_price: Planned limit price
        btc_volume: Planned BTC volume
    
    Returns:
        Formatted message string
    """
    timestamp = get_timestamp_string(config.general.timezone)
    min_balance = config.trade.min_free_balance
    
    buffer_info = ""
    if min_balance > 0:
        buffer_info = f"Buffer: {format_currency(min_balance)}\n"
    
    return (
        f"⚠️ Insufficient funds on {timestamp}\n\n"
        f"Required:\n"
        f"Trade Amount: {format_currency(config.trade.amount_eur)}\n"
        f"{buffer_info}"
        f"Limit Price: {format_currency(limit_price, decimals=1)}\n"
        f"BTC Volume: {format_btc(btc_volume)}\n"
        f"Discount: {format_percentage(config.trade.discount_percent / 100)} under Ask\n\n"
        f"Total EUR: {format_currency(balance_eur)}\n"
        f"Available: {format_currency(free_balance)}\n\n"
        f"Ask: {format_currency(ticker.ask_price)} | "
        f"Bid: {format_currency(ticker.bid_price)}"
    )


def build_fatal_error_message(config: Config, error: str) -> str:
    """Build message for fatal execution errors.
    
    Args:
        config: Application configuration
        error: Error message
    
    Returns:
        Formatted message string
    """
    timestamp = get_timestamp_string(config.general.timezone)
    return f"❌ DCA execution failed on {timestamp}\n\nError: {error}"