"""Kraken API client with retry logic and error handling.

This module provides a clean interface to the Kraken API with
automatic retry on failures and comprehensive error handling.
"""

import logging
import time
from typing import Dict, List, Optional

import krakenex

from .models import Balance, OpenOrder, OrderResult, Ticker


logger = logging.getLogger(__name__)


class KrakenAPIError(Exception):
    """Base exception for Kraken API errors."""
    
    def __init__(self, message: str, errors: Optional[List[str]] = None):
        """Initialize KrakenAPIError.
        
        Args:
            message: Error message
            errors: List of error messages from API
        """
        super().__init__(message)
        self.errors = errors or []


class KrakenClient:
    """Kraken API client with retry logic.
    
    This client wraps the krakenex library and provides:
    - Automatic retry on transient failures
    - Clean error handling
    - Type-safe response parsing
    - Logging of all API calls
    """
    
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """Initialize Kraken client.
        
        Args:
            api_key: Kraken API key
            api_secret: Kraken API secret
            max_retries: Maximum number of retries for failed requests
            retry_delay: Initial delay between retries in seconds (exponential backoff)
        """
        self._client = krakenex.API(key=api_key, secret=api_secret)
        self._max_retries = max_retries
        self._retry_delay = retry_delay
    
    def get_ticker(self, pair: str = "XXBTZEUR") -> Ticker:
        """Get ticker information for a trading pair.
        
        Args:
            pair: Trading pair (default: XXBTZEUR for BTC/EUR)
        
        Returns:
            Ticker object with current prices
            
        Raises:
            KrakenAPIError: If API request fails
        """
        logger.info(f"Fetching ticker for pair: {pair}")
        
        response = self._query_public("Ticker", {"pair": pair})
        
        if pair not in response:
            raise KrakenAPIError(
                f"Ticker data not found for pair: {pair}",
                [f"Available pairs: {list(response.keys())}"]
            )
        
        ticker = Ticker.from_api_response(pair, response[pair])
        logger.info(
            f"Ticker fetched: Ask={ticker.ask_price:.2f}, Bid={ticker.bid_price:.2f}"
        )
        
        return ticker
    
    def get_balance(self) -> Dict[str, float]:
        """Get account balance for all currencies.
        
        Returns:
            Dictionary mapping currency codes to balances
            
        Raises:
            KrakenAPIError: If API request fails
        """
        logger.info("Fetching account balance")
        
        response = self._query_private("Balance")
        
        # Convert string balances to floats
        balances = {
            currency: float(amount)
            for currency, amount in response.items()
        }
        
        logger.info(f"Balance fetched: {len(balances)} currencies")
        return balances
    
    def get_balance_by_currency(self, currency: str) -> float:
        """Get balance for a specific currency.
        
        Args:
            currency: Currency code (e.g., "ZEUR", "XXBT")
        
        Returns:
            Balance amount
            
        Raises:
            KrakenAPIError: If API request fails
        """
        balances = self.get_balance()
        return balances.get(currency, 0.0)
    
    def get_open_orders(self) -> List[OpenOrder]:
        """Get all open orders.
        
        Returns:
            List of OpenOrder objects
            
        Raises:
            KrakenAPIError: If API request fails
        """
        logger.info("Fetching open orders")
        
        response = self._query_private("OpenOrders")
        open_orders_data = response.get("open", {})
        
        orders = [
            OpenOrder.from_api_response(order_id, data)
            for order_id, data in open_orders_data.items()
        ]
        
        logger.info(f"Found {len(orders)} open orders")
        return orders
    
    def calculate_free_balance(
        self,
        currency: str = "ZEUR",
        fee_buffer: float = 1.005,
    ) -> float:
        """Calculate free balance accounting for open orders.
        
        This calculates how much balance is actually available for new
        orders by subtracting the reserved amounts for open orders.
        
        Args:
            currency: Currency to check (default: ZEUR for EUR)
            fee_buffer: Safety buffer for fees (default: 0.5% = 1.005)
        
        Returns:
            Free balance amount
            
        Raises:
            KrakenAPIError: If API request fails
        """
        logger.info(f"Calculating free {currency} balance")
        
        total_balance = self.get_balance_by_currency(currency)
        open_orders = self.get_open_orders()
        
        reserved = self._calculate_reserved_balance(open_orders, fee_buffer)
        free_balance = total_balance - reserved
        
        logger.info(
            f"Free balance: {free_balance:.4f} {currency} "
            f"(Total: {total_balance:.4f}, Reserved: {reserved:.4f})"
        )
        
        return free_balance
    
    def place_limit_order(
        self,
        pair: str,
        volume: float,
        price: float,
        validate: bool = True,
        post_only: bool = True,
    ) -> OrderResult:
        """Place a limit buy order.
        
        Args:
            pair: Trading pair (e.g., "XXBTZEUR")
            volume: Order volume (amount to buy)
            price: Limit price
            validate: If True, only validate order without placing it
            post_only: If True, use post-only flag (maker only, lower fees)
        
        Returns:
            OrderResult object with order details
            
        Raises:
            KrakenAPIError: If API request fails
        """
        action = "Validating" if validate else "Placing"
        post_only_info = " (post-only)" if post_only else ""
        logger.info(
            f"{action} limit order{post_only_info}: {volume:.8f} {pair} @ {price:.2f}"
        )
        
        order_data = {
            "pair": pair,
            "type": "buy",
            "ordertype": "limit",
            "price": str(price),
            "volume": str(volume),
            "validate": "true" if validate else "false",
        }
        
        # Add post-only flag if enabled (ensures maker fee, never taker)
        if post_only:
            order_data["oflags"] = "post"
        
        response = self._query_private("AddOrder", order_data)
        result = OrderResult.from_api_response(response, is_validated=validate)
        
        if validate:
            logger.info(f"Order validation successful: {result.description}")
        else:
            logger.info(
                f"Order placed successfully: {result.description} "
                f"(IDs: {result.order_ids})"
            )
        
        return result
    
    def _calculate_reserved_balance(
        self,
        open_orders: List[OpenOrder],
        fee_buffer: float,
    ) -> float:
        """Calculate total balance reserved by open orders.
        
        Args:
            open_orders: List of open orders
            fee_buffer: Safety buffer for fees
        
        Returns:
            Total reserved amount
        """
        reserved = 0.0
        
        for order in open_orders:
            if order.order_type == "buy":
                # For buy orders, we reserve: volume * price * fee_buffer
                order_cost = order.volume * order.price * fee_buffer
                reserved += order_cost
                logger.debug(
                    f"Order {order.order_id}: Reserved {order_cost:.4f} "
                    f"({order.volume:.8f} @ {order.price:.2f})"
                )
        
        return reserved
    
    def _query_public(self, method: str, data: Optional[Dict] = None) -> Dict:
        """Query public Kraken API endpoint with retry logic.
        
        Args:
            method: API method name
            data: Request parameters
        
        Returns:
            API response data
            
        Raises:
            KrakenAPIError: If API request fails after all retries
        """
        return self._execute_with_retry(
            lambda: self._client.query_public(method, data or {})
        )
    
    def _query_private(self, method: str, data: Optional[Dict] = None) -> Dict:
        """Query private Kraken API endpoint with retry logic.
        
        Args:
            method: API method name
            data: Request parameters
        
        Returns:
            API response data
            
        Raises:
            KrakenAPIError: If API request fails after all retries
        """
        return self._execute_with_retry(
            lambda: self._client.query_private(method, data or {})
        )
    
    def _execute_with_retry(self, api_call) -> Dict:
        """Execute API call with exponential backoff retry.
        
        Args:
            api_call: Callable that executes the API request
        
        Returns:
            API response data
            
        Raises:
            KrakenAPIError: If all retries fail
        """
        last_exception = None
        
        for attempt in range(self._max_retries):
            try:
                response = api_call()
                
                # Check for API errors
                if response.get("error"):
                    errors = response["error"]
                    if errors:
                        raise KrakenAPIError(
                            f"Kraken API error: {', '.join(errors)}",
                            errors
                        )
                
                return response.get("result", {})
                
            except KrakenAPIError:
                # Don't retry on API errors (invalid params, etc.)
                raise
                
            except Exception as e:
                last_exception = e
                
                if attempt < self._max_retries - 1:
                    delay = self._retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(
                        f"API call failed (attempt {attempt + 1}/{self._max_retries}): {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"API call failed after {self._max_retries} attempts: {e}"
                    )
        
        # All retries exhausted
        raise KrakenAPIError(
            f"API request failed after {self._max_retries} retries",
            [str(last_exception)]
        )