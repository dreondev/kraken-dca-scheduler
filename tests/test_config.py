"""Tests for configuration management."""

import pytest
from pathlib import Path
from src.config import (
    Config,
    KrakenConfig,
    TradeConfig,
    TelegramConfig,
    NtfyConfig,
    NotificationConfig,
    GeneralConfig,
    _resolve_env_var,
    _parse_string_to_float,
)


class TestKrakenConfig:
    """Tests for KrakenConfig dataclass."""
    
    def test_valid_config(self):
        """Test creating valid Kraken config."""
        config = KrakenConfig(
            api_key="test_key",
            api_secret="test_secret",
            pair="XXBTZEUR"
        )
        assert config.api_key == "test_key"
        assert config.api_secret == "test_secret"
        assert config.pair == "XXBTZEUR"
    
    def test_missing_api_key(self):
        """Test that missing API key raises error."""
        with pytest.raises(ValueError, match="API key and secret are required"):
            KrakenConfig(api_key="", api_secret="test_secret", pair="XXBTZEUR")
    
    def test_missing_api_secret(self):
        """Test that missing API secret raises error."""
        with pytest.raises(ValueError, match="API key and secret are required"):
            KrakenConfig(api_key="test_key", api_secret="", pair="XXBTZEUR")


class TestTradeConfig:
    """Tests for TradeConfig dataclass."""
    
    def test_valid_config(self):
        """Test creating valid trade config."""
        config = TradeConfig(
            amount_eur=20.0,
            discount_percent=0.5,
            validate_order=True,
            min_free_balance=0.0
        )
        assert config.amount_eur == 20.0
        assert config.discount_percent == 0.5
        assert config.validate_order is True
        assert config.min_free_balance == 0.0
    
    def test_negative_amount(self):
        """Test that negative amount raises error."""
        with pytest.raises(ValueError, match="must be positive"):
            TradeConfig(
                amount_eur=-10.0,
                discount_percent=0.5,
                validate_order=True,
                min_free_balance=0.0
            )
    
    def test_invalid_discount_percent(self):
        """Test that invalid discount percent raises error."""
        with pytest.raises(ValueError, match="must be between 0 and 100"):
            TradeConfig(
                amount_eur=20.0,
                discount_percent=101.0,
                validate_order=True,
                min_free_balance=0.0
            )


class TestGeneralConfig:
    """Tests for GeneralConfig dataclass."""
    
    def test_valid_config(self):
        """Test creating valid general config."""
        config = GeneralConfig(
            timezone="Europe/Berlin",
            log_level="INFO"
        )
        assert config.timezone == "Europe/Berlin"
        assert config.log_level == "INFO"
    
    def test_log_level_normalization(self):
        """Test that log level is normalized to uppercase."""
        config = GeneralConfig(timezone="Europe/Berlin", log_level="info")
        assert config.log_level == "INFO"
    
    def test_invalid_log_level(self):
        """Test that invalid log level raises error."""
        with pytest.raises(ValueError, match="Log level must be one of"):
            GeneralConfig(timezone="Europe/Berlin", log_level="INVALID")


class TestTelegramConfig:
    """Tests for TelegramConfig dataclass."""
    
    def test_valid_config(self):
        """Test creating valid Telegram config."""
        config = TelegramConfig(
            bot_token="123:ABC",
            chat_id="456"
        )
        assert config.bot_token == "123:ABC"
        assert config.chat_id == "456"
    
    def test_missing_token(self):
        """Test that missing token raises error."""
        with pytest.raises(ValueError, match="bot token and chat ID are required"):
            TelegramConfig(bot_token="", chat_id="456")


class TestNtfyConfig:
    """Tests for NtfyConfig dataclass."""
    
    def test_valid_config(self):
        """Test creating valid ntfy config."""
        config = NtfyConfig(
            server="https://ntfy.sh",
            topic="test-topic",
            priority="default"
        )
        assert config.server == "https://ntfy.sh"
        assert config.topic == "test-topic"
        assert config.priority == "default"
    
    def test_missing_topic(self):
        """Test that missing topic raises error."""
        with pytest.raises(ValueError, match="topic is required"):
            NtfyConfig(server="https://ntfy.sh", topic="", priority="default")
    
    def test_invalid_priority(self):
        """Test that invalid priority raises error."""
        with pytest.raises(ValueError, match="Priority must be one of"):
            NtfyConfig(server="https://ntfy.sh", topic="test", priority="invalid")


class TestConfigLoad:
    """Tests for Config.load() method."""
    
    def test_load_valid_config(self, tmp_path):
        """Test loading valid config file."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
general:
  timezone: "Europe/Berlin"
  log_level: "INFO"

kraken:
  api_key: "test_key"
  api_secret: "test_secret"
  pair: "XXBTZEUR"

trade:
  amount_eur: 20.0
  discount_percent: 0.5
  validate_order: true

telegram:
  bot_token: "123:ABC"
  chat_id: "456"
""")
        
        config = Config.load(str(config_file))
        
        assert config.general.timezone == "Europe/Berlin"
        assert config.kraken.api_key == "test_key"
        assert config.trade.amount_eur == 20.0
        assert config.telegram.bot_token == "123:ABC"
    
    def test_load_with_string_numbers(self, tmp_path):
        """Test loading config with string numbers (German format)."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
general:
  timezone: "Europe/Berlin"

kraken:
  api_key: "test_key"
  api_secret: "test_secret"

trade:
  amount_eur: "20,0"
  discount_percent: "0,5"

telegram:
  bot_token: "123:ABC"
  chat_id: "456"
""")
        
        config = Config.load(str(config_file))
        
        assert config.trade.amount_eur == 20.0
        assert config.trade.discount_percent == 0.5
    
    def test_load_with_env_vars(self, tmp_path, monkeypatch):
        """Test loading config with environment variable substitution."""
        monkeypatch.setenv("KRAKEN_KEY", "env_key")
        monkeypatch.setenv("KRAKEN_SECRET", "env_secret")
        
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
general:
  timezone: "Europe/Berlin"

kraken:
  api_key: "${KRAKEN_KEY}"
  api_secret: "${KRAKEN_SECRET}"

trade:
  amount_eur: 20.0
  discount_percent: 0.5

telegram:
  bot_token: "123:ABC"
  chat_id: "456"
""")
        
        config = Config.load(str(config_file))
        
        assert config.kraken.api_key == "env_key"
        assert config.kraken.api_secret == "env_secret"
    
    def test_load_missing_file(self):
        """Test that missing config file raises error."""
        with pytest.raises(FileNotFoundError, match="Config file not found"):
            Config.load("/nonexistent/config.yaml")
    
    def test_load_invalid_yaml(self, tmp_path):
        """Test that invalid YAML raises error."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("invalid: yaml: content:")
        
        with pytest.raises(Exception):  # yaml.YAMLError or similar
            Config.load(str(config_file))
    
    def test_load_missing_required_section(self, tmp_path):
        """Test that missing required section raises error."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
general:
  timezone: "Europe/Berlin"
""")
        
        with pytest.raises(ValueError, match="Missing 'kraken' section"):
            Config.load(str(config_file))


class TestEnvVarResolution:
    """Tests for environment variable resolution."""
    
    def test_resolve_env_var_with_braces(self, monkeypatch):
        """Test resolving ${VAR_NAME} format."""
        monkeypatch.setenv("TEST_VAR", "test_value")
        result = _resolve_env_var("${TEST_VAR}")
        assert result == "test_value"
    
    def test_resolve_env_var_without_braces(self, monkeypatch):
        """Test resolving $VAR_NAME format."""
        monkeypatch.setenv("TEST_VAR", "test_value")
        result = _resolve_env_var("$TEST_VAR")
        assert result == "test_value"
    
    def test_resolve_env_var_not_set(self):
        """Test resolving unset environment variable."""
        result = _resolve_env_var("${NONEXISTENT_VAR}")
        assert result == ""
    
    def test_resolve_plain_value(self):
        """Test that plain values are not resolved."""
        result = _resolve_env_var("plain_value")
        assert result == "plain_value"


class TestParseStringToFloat:
    """Tests for string to float parsing."""
    
    def test_parse_float(self):
        """Test parsing float value."""
        result = _parse_string_to_float(20.5)
        assert result == 20.5
    
    def test_parse_int(self):
        """Test parsing int value."""
        result = _parse_string_to_float(20)
        assert result == 20.0
    
    def test_parse_string_with_dot(self):
        """Test parsing string with dot decimal separator."""
        result = _parse_string_to_float("20.5")
        assert result == 20.5
    
    def test_parse_string_with_comma(self):
        """Test parsing string with comma decimal separator (German format)."""
        result = _parse_string_to_float("20,5")
        assert result == 20.5
    
    def test_parse_invalid_value(self):
        """Test that invalid value raises error."""
        with pytest.raises(ValueError, match="Cannot parse value to float"):
            _parse_string_to_float(None)