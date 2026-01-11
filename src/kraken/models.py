"""Data models for Kraken API responses.

This module contains dataclasses representing various Kraken API
data structures for type-safe handling of API responses.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class Ticker:
    """Ticker information for a trading pair.
    
    Attributes:
        ask_price: Current ask (sell) price
        ask_volume: Volume at ask price
        bid_price: Current bid (buy) price
        bid_volume: Volume at bid price
        last_price: Price of last trade
        volume_24h: 24-hour trading volume
        pair: Trading pair (e.g., "XXBTZEUR")
    """
    
    ask_price: float
    ask_volume: float
    bid_price: float
    bid_volume: float
    last_price: float
    volume_24h: float
    pair: str
    
    @classmethod
    def from_api_response(cls, pair: str, data: Dict) -> "Ticker":
        """Create Ticker from Kraken API response.
        
        Args:
            pair: Trading pair name
            data: Ticker data from API
        
        Returns:
            Ticker instance
            
        Example API response:
            {
                "a": ["77920.40000", "1", "1.000"],
                "b": ["77919.30000", "1", "1.000"],
                "c": ["77920.00000", "0.00100000"],
                "v": ["123.45678900", "234.56789000"]
            }
        """
        return cls(
            ask_price=float(data["a"][0]),
            ask_volume=float(data["a"][1]),
            bid_price=float(data["b"][0]),
            bid_volume=float(data["b"][1]),
            last_price=float(data["c"][0]),
            volume_24h=float(data["v"][0]),
            pair=pair,
        )


@dataclass
class Balance:
    """Account balance information.
    
    Attributes:
        currency: Currency code (e.g., "ZEUR", "XXBT")
        amount: Balance amount
    """
    
    currency: str
    amount: float
    
    @classmethod
    def from_api_response(cls, balances: Dict[str, str]) -> List["Balance"]:
        """Create list of Balance objects from Kraken API response.
        
        Args:
            balances: Balance data from API
        
        Returns:
            List of Balance instances
            
        Example API response:
            {
                "ZEUR": "1234.5678",
                "XXBT": "0.12345678"
            }
        """
        return [
            cls(currency=currency, amount=float(amount))
            for currency, amount in balances.items()
        ]


@dataclass
class OpenOrder:
    """Open order information.
    
    Attributes:
        order_id: Unique order identifier
        pair: Trading pair
        order_type: Order type (buy/sell)
        price: Limit price
        volume: Order volume
        description: Order description string
    """
    
    order_id: str
    pair: str
    order_type: str
    price: float
    volume: float
    description: str
    
    @classmethod
    def from_api_response(cls, order_id: str, data: Dict) -> "OpenOrder":
        """Create OpenOrder from Kraken API response.
        
        Args:
            order_id: Order identifier
            data: Order data from API
        
        Returns:
            OpenOrder instance
            
        Example API response:
            {
                "descr": {
                    "pair": "XXBTZEUR",
                    "type": "buy",
                    "ordertype": "limit",
                    "price": "77000.0",
                    "order": "buy 0.00025641 XXBTZEUR @ limit 77000.0"
                },
                "vol": "0.00025641"
            }
        """
        descr = data["descr"]
        return cls(
            order_id=order_id,
            pair=descr.get("pair", ""),
            order_type=descr.get("type", ""),
            price=float(descr.get("price", 0)),
            volume=float(data.get("vol", 0)),
            description=descr.get("order", ""),
        )


@dataclass
class OrderResult:
    """Result of placing an order.
    
    Attributes:
        order_ids: List of order transaction IDs (txid)
        description: Order description
        is_validated: Whether this was a validation-only request
    """
    
    order_ids: List[str]
    description: str
    is_validated: bool
    
    @classmethod
    def from_api_response(cls, data: Dict, is_validated: bool = False) -> "OrderResult":
        """Create OrderResult from Kraken API response.
        
        Args:
            data: Order result data from API
            is_validated: Whether this was a validation request
        
        Returns:
            OrderResult instance
            
        Example API response (validated):
            {
                "descr": {
                    "order": "buy 0.00025641 XXBTZEUR @ limit 77000.0"
                }
            }
            
        Example API response (placed):
            {
                "descr": {
                    "order": "buy 0.00025641 XXBTZEUR @ limit 77000.0"
                },
                "txid": ["OUF4KD-GXYDB-3V6PQI"]
            }
        """
        descr = data.get("descr", {})
        order_description = descr.get("order", "")
        
        # txid is only present for actual orders, not validated ones
        order_ids = data.get("txid", [])
        
        return cls(
            order_ids=order_ids,
            description=order_description,
            is_validated=is_validated,
        )