"""Configuration management for Kraken DCA Scheduler.

This module handles loading and validating configuration from YAML files
and environment variables, following strict Clean Code principles.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


# ============================================================================
# Configuration Dataclasses
# ============================================================================


@dataclass
class GeneralConfig:
    """General application configuration."""
    
    timezone: str
    log_level: str
    
    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        self._validate_log_level()
        self.log_level = self.log_level.upper()
    
    def _validate_log_level(self) -> None:
        """Validate that log level is one of the allowed values."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level.upper() not in valid_levels:
            raise ValueError(
                f"Log level must be one of {valid_levels}, got '{self.log_level}'"
            )


@dataclass
class KrakenConfig:
    """Kraken API configuration."""
    
    api_key: str
    api_secret: str
    pair: str
    
    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        self._validate_credentials()
        self._validate_pair()
    
    def _validate_credentials(self) -> None:
        """Validate that API credentials are present."""
        if not self.api_key or not self.api_secret:
            raise ValueError("Kraken API key and secret are required")
    
    def _validate_pair(self) -> None:
        """Validate that trading pair is present."""
        if not self.pair:
            raise ValueError("Trading pair is required")


@dataclass
class TradeConfig:
    """Trading configuration."""
    
    amount_eur: float
    discount_percent: float
    validate_order: bool
    min_free_balance: float
    
    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        self._validate_amount()
        self._validate_discount()
        self._validate_min_balance()
    
    def _validate_amount(self) -> None:
        """Validate that trade amount is positive."""
        if self.amount_eur <= 0:
            raise ValueError(
                f"Trade amount must be positive, got {self.amount_eur}"
            )
    
    def _validate_discount(self) -> None:
        """Validate that discount percentage is in valid range."""
        if not 0 <= self.discount_percent <= 100:
            raise ValueError(
                f"Discount percent must be between 0 and 100, "
                f"got {self.discount_percent}"
            )
    
    def _validate_min_balance(self) -> None:
        """Validate that minimum balance is non-negative."""
        if self.min_free_balance < 0:
            raise ValueError(
                f"Minimum free balance cannot be negative, "
                f"got {self.min_free_balance}"
            )


@dataclass
class TelegramConfig:
    """Telegram notification configuration."""
    
    bot_token: str
    chat_id: str
    
    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        self._validate_credentials()
    
    def _validate_credentials(self) -> None:
        """Validate that bot token and chat ID are present."""
        if not self.bot_token or not self.chat_id:
            raise ValueError("Telegram bot token and chat ID are required")


@dataclass
class NtfyConfig:
    """ntfy.sh notification configuration."""
    
    server: str
    topic: str
    priority: str
    
    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        self._validate_topic()
        self._validate_priority()
    
    def _validate_topic(self) -> None:
        """Validate that topic is present."""
        if not self.topic:
            raise ValueError("ntfy topic is required")
    
    def _validate_priority(self) -> None:
        """Validate that priority is one of the allowed values."""
        valid_priorities = ["min", "low", "default", "high", "max"]
        if self.priority not in valid_priorities:
            raise ValueError(
                f"Priority must be one of {valid_priorities}, got '{self.priority}'"
            )


@dataclass
class NotificationConfig:
    """Notification configuration."""
    
    enabled: bool
    provider: str
    telegram: Optional[TelegramConfig]
    ntfy: Optional[NtfyConfig]
    
    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if self.enabled:
            self._validate_provider()
            self._validate_provider_config()
    
    def _validate_provider(self) -> None:
        """Validate that provider is one of the allowed values."""
        valid_providers = ["telegram", "ntfy"]
        if self.provider not in valid_providers:
            raise ValueError(
                f"Provider must be one of {valid_providers}, got '{self.provider}'"
            )
    
    def _validate_provider_config(self) -> None:
        """Validate that provider-specific config is present."""
        if self.provider == "telegram" and self.telegram is None:
            raise ValueError("Telegram config required when provider is 'telegram'")
        if self.provider == "ntfy" and self.ntfy is None:
            raise ValueError("ntfy config required when provider is 'ntfy'")


@dataclass
class Config:
    """Main configuration container."""
    
    general: GeneralConfig
    kraken: KrakenConfig
    trade: TradeConfig
    telegram: Optional[TelegramConfig] = None
    notifications: Optional[NotificationConfig] = None
    
    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "Config":
        """Load configuration from YAML file and environment variables.
        
        Args:
            config_path: Path to config YAML file. If None, uses default locations.
        
        Returns:
            Loaded and validated Config object
            
        Raises:
            FileNotFoundError: If config file not found
            ValueError: If configuration is invalid
        """
        path = _find_config_file(config_path)
        data = _load_yaml_file(path)
        
        general = _parse_general_config(data)
        kraken = _parse_kraken_config(data)
        trade = _parse_trade_config(data)
        telegram = _parse_telegram_config(data)
        notifications = _parse_notification_config(data)
        
        return cls(
            general=general,
            kraken=kraken,
            trade=trade,
            telegram=telegram,
            notifications=notifications,
        )


# ============================================================================
# Private Helper Functions (Config Loading)
# ============================================================================


def _find_config_file(config_path: Optional[str]) -> str:
    """Find configuration file from given path or default locations.
    
    Args:
        config_path: Optional path to config file
    
    Returns:
        Path to config file
        
    Raises:
        FileNotFoundError: If config file not found in any location
    """
    # Check explicit path first
    if config_path is not None:
        if Path(config_path).exists():
            return config_path
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    # Check environment variable
    env_path = os.getenv("DCA_CONFIG_PATH")
    if env_path and Path(env_path).exists():
        return env_path
    
    # Check default locations
    default_paths = ["config.yaml", "config/config.yaml"]
    for path in default_paths:
        if Path(path).exists():
            return path
    
    raise FileNotFoundError(
        "Config file not found. Tried: DCA_CONFIG_PATH env var, "
        "config.yaml, config/config.yaml"
    )


def _load_yaml_file(path: str) -> Dict[str, Any]:
    """Load and parse YAML configuration file.
    
    Args:
        path: Path to YAML file
    
    Returns:
        Parsed YAML data as dictionary
        
    Raises:
        ValueError: If file is empty or invalid
    """
    with open(path, "r") as f:
        data = yaml.safe_load(f)
    
    if data is None:
        raise ValueError(f"Config file is empty: {path}")
    
    return data


def _resolve_env_var(value: str) -> str:
    """Resolve environment variable references in config values.
    
    Supports formats: ${VAR_NAME} or $VAR_NAME
    
    Args:
        value: Config value that may contain env var reference
    
    Returns:
        Resolved value with env var substituted
    """
    if not value or not isinstance(value, str):
        return value
    
    # Handle ${VAR_NAME} format
    if value.startswith("${") and value.endswith("}"):
        var_name = value[2:-1]
        return os.getenv(var_name, "")
    
    # Handle $VAR_NAME format
    if value.startswith("$"):
        var_name = value[1:]
        return os.getenv(var_name, "")
    
    return value


def _parse_string_to_float(value: Any) -> float:
    """Parse string or numeric value to float, handling German format.
    
    Args:
        value: Value to parse (float, int, or string)
    
    Returns:
        Parsed float value
    """
    if isinstance(value, (int, float)):
        return float(value)
    
    if isinstance(value, str):
        # Handle German number format (comma as decimal separator)
        return float(value.replace(',', '.'))
    
    raise ValueError(f"Cannot parse value to float: {value}")


# ============================================================================
# Private Helper Functions (Config Parsing)
# ============================================================================


def _parse_general_config(data: Dict[str, Any]) -> GeneralConfig:
    """Parse general configuration section.
    
    Args:
        data: Full configuration dictionary
    
    Returns:
        Parsed GeneralConfig object
    """
    general_data = data.get("general", {})
    
    return GeneralConfig(
        timezone=general_data.get("timezone", "Europe/Berlin"),
        log_level=general_data.get("log_level", "INFO"),
    )


def _parse_kraken_config(data: Dict[str, Any]) -> KrakenConfig:
    """Parse Kraken API configuration section.
    
    Args:
        data: Full configuration dictionary
    
    Returns:
        Parsed KrakenConfig object
        
    Raises:
        ValueError: If kraken section is missing
    """
    kraken_data = data.get("kraken")
    if not kraken_data:
        raise ValueError("Missing 'kraken' section in config")
    
    api_key = _resolve_env_var(kraken_data.get("api_key", ""))
    api_secret = _resolve_env_var(kraken_data.get("api_secret", ""))
    pair = kraken_data.get("pair", "XXBTZEUR")
    
    return KrakenConfig(
        api_key=api_key,
        api_secret=api_secret,
        pair=pair,
    )


def _parse_trade_config(data: Dict[str, Any]) -> TradeConfig:
    """Parse trade configuration section.
    
    Args:
        data: Full configuration dictionary
    
    Returns:
        Parsed TradeConfig object
        
    Raises:
        ValueError: If trade section is missing
    """
    trade_data = data.get("trade")
    if not trade_data:
        raise ValueError("Missing 'trade' section in config")
    
    amount_eur = _parse_string_to_float(trade_data.get("amount_eur"))
    discount_percent = _parse_string_to_float(trade_data.get("discount_percent"))
    validate_order = trade_data.get("validate_order", True)
    min_free_balance = trade_data.get("min_free_balance", 0.0)
    
    return TradeConfig(
        amount_eur=amount_eur,
        discount_percent=discount_percent,
        validate_order=validate_order,
        min_free_balance=min_free_balance,
    )


def _parse_telegram_config(data: Dict[str, Any]) -> Optional[TelegramConfig]:
    """Parse legacy Telegram configuration section.
    
    Args:
        data: Full configuration dictionary
    
    Returns:
        Parsed TelegramConfig object or None if not configured
    """
    telegram_data = data.get("telegram", {})
    
    if not telegram_data:
        return None
    
    bot_token = _resolve_env_var(telegram_data.get("bot_token", ""))
    chat_id = _resolve_env_var(telegram_data.get("chat_id", ""))
    
    if not bot_token or not chat_id:
        return None
    
    return TelegramConfig(
        bot_token=bot_token,
        chat_id=chat_id,
    )


def _parse_notification_config(data: Dict[str, Any]) -> Optional[NotificationConfig]:
    """Parse notification configuration section.
    
    Args:
        data: Full configuration dictionary
    
    Returns:
        Parsed NotificationConfig object or None if not configured
    """
    notif_data = data.get("notifications")
    
    if not notif_data:
        return None
    
    enabled = notif_data.get("enabled", True)
    provider = notif_data.get("provider", "telegram")
    
    telegram_config = _parse_telegram_subconfig(notif_data)
    ntfy_config = _parse_ntfy_subconfig(notif_data)
    
    return NotificationConfig(
        enabled=enabled,
        provider=provider,
        telegram=telegram_config,
        ntfy=ntfy_config,
    )


def _parse_telegram_subconfig(notif_data: Dict[str, Any]) -> Optional[TelegramConfig]:
    """Parse Telegram sub-configuration from notifications section.
    
    Args:
        notif_data: Notifications configuration dictionary
    
    Returns:
        Parsed TelegramConfig object or None if not configured
    """
    telegram_data = notif_data.get("telegram")
    
    if not telegram_data:
        return None
    
    bot_token = _resolve_env_var(telegram_data.get("bot_token", ""))
    chat_id = _resolve_env_var(telegram_data.get("chat_id", ""))
    
    if not bot_token or not chat_id:
        return None
    
    return TelegramConfig(
        bot_token=bot_token,
        chat_id=chat_id,
    )


def _parse_ntfy_subconfig(notif_data: Dict[str, Any]) -> Optional[NtfyConfig]:
    """Parse ntfy sub-configuration from notifications section.
    
    Args:
        notif_data: Notifications configuration dictionary
    
    Returns:
        Parsed NtfyConfig object or None if not configured
    """
    ntfy_data = notif_data.get("ntfy")
    
    if not ntfy_data:
        return None
    
    server = ntfy_data.get("server", "https://ntfy.sh")
    topic = ntfy_data.get("topic", "")
    priority = ntfy_data.get("priority", "default")
    
    return NtfyConfig(
        server=server,
        topic=topic,
        priority=priority,
    )