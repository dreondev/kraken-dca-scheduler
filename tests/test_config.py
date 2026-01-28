"""Tests for configuration management."""

import pytest
from pathlib import Path
from src.config import (
    Config,
    KrakenConfig,
    TradeConfig,
    NtfyConfig,
    NotificationConfig,
    GeneralConfig,
    ScheduleConfig,
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
    
    def test_negative_min_balance(self):
        """Test that negative min_free_balance raises error."""
        with pytest.raises(ValueError, match="cannot be negative"):
            TradeConfig(
                amount_eur=20.0,
                discount_percent=0.5,
                validate_order=True,
                min_free_balance=-10.0
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
    
    def test_all_valid_priorities(self):
        """Test all valid priority levels."""
        for priority in ["min", "low", "default", "high", "max"]:
            config = NtfyConfig(
                server="https://ntfy.sh",
                topic="test",
                priority=priority
            )
            assert config.priority == priority


class TestNotificationConfig:
    """Tests for NotificationConfig dataclass."""
    
    def test_valid_ntfy_config(self):
        """Test creating valid notification config with ntfy."""
        ntfy = NtfyConfig(
            server="https://ntfy.sh",
            topic="test-topic",
            priority="default"
        )
        config = NotificationConfig(
            enabled=True,
            provider="ntfy",
            ntfy=ntfy
        )
        assert config.enabled is True
        assert config.provider == "ntfy"
        assert config.ntfy is not None
    
    def test_disabled_config_skips_validation(self):
        """Test that disabled notification skips provider validation."""
        config = NotificationConfig(
            enabled=False,
            provider="invalid",
            ntfy=None
        )
        assert config.enabled is False
    
    def test_invalid_provider(self):
        """Test that invalid provider raises error."""
        with pytest.raises(ValueError, match="Provider must be one of"):
            NotificationConfig(
                enabled=True,
                provider="telegram",  # No longer supported
                ntfy=None
            )
    
    def test_missing_ntfy_config(self):
        """Test that missing ntfy config raises error when provider is ntfy."""
        with pytest.raises(ValueError, match="ntfy config required"):
            NotificationConfig(
                enabled=True,
                provider="ntfy",
                ntfy=None
            )


class TestScheduleConfig:
    """Tests for ScheduleConfig dataclass."""

    def test_valid_cron_expression(self):
        """Test that valid cron expression is accepted."""
        config = ScheduleConfig(enabled=True, cron="0 8 * * *")
        assert config.enabled is True
        assert config.cron == "0 8 * * *"

    def test_disabled_schedule_skips_validation(self):
        """Test that disabled schedule skips cron validation."""
        config = ScheduleConfig(enabled=False, cron="")
        assert config.enabled is False

    def test_empty_cron_when_enabled_raises_error(self):
        """Test that empty cron raises error when enabled."""
        with pytest.raises(ValueError, match="Cron expression is required"):
            ScheduleConfig(enabled=True, cron="")

    def test_invalid_cron_parts_raises_error(self):
        """Test that cron with wrong number of parts raises error."""
        with pytest.raises(ValueError, match="must have 5 parts"):
            ScheduleConfig(enabled=True, cron="0 8 *")

    def test_cron_with_six_parts_raises_error(self):
        """Test that cron with 6 parts raises error."""
        with pytest.raises(ValueError, match="must have 5 parts"):
            ScheduleConfig(enabled=True, cron="0 0 8 * * *")
    
    def test_various_valid_cron_expressions(self):
        """Test various valid cron expressions."""
        valid_crons = [
            "0 8 * * *",      # Daily at 8am
            "0 8 * * 1-5",    # Weekdays at 8am
            "0 */6 * * *",    # Every 6 hours
            "30 9 1,15 * *",  # 1st and 15th at 9:30
            "*/15 * * * *",   # Every 15 minutes
        ]
        for cron in valid_crons:
            config = ScheduleConfig(enabled=True, cron=cron)
            assert config.cron == cron


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
  min_free_balance: 5.0

notifications:
  enabled: true
  provider: "ntfy"
  ntfy:
    server: "https://ntfy.sh"
    topic: "test-topic"
    priority: "default"
""")
        
        config = Config.load(str(config_file))
        
        assert config.general.timezone == "Europe/Berlin"
        assert config.kraken.api_key == "test_key"
        assert config.trade.amount_eur == 20.0
        assert config.trade.min_free_balance == 5.0
        assert config.notifications.provider == "ntfy"
        assert config.notifications.ntfy.topic == "test-topic"
    
    def test_load_with_schedule(self, tmp_path):
        """Test loading config with schedule section."""
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

schedule:
  enabled: true
  cron: "0 8 * * *"
""")
        
        config = Config.load(str(config_file))
        
        assert config.schedule is not None
        assert config.schedule.enabled is True
        assert config.schedule.cron == "0 8 * * *"
    
    def test_load_without_schedule(self, tmp_path):
        """Test loading config without schedule section."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
general:
  timezone: "Europe/Berlin"

kraken:
  api_key: "test_key"
  api_secret: "test_secret"

trade:
  amount_eur: 20.0
  discount_percent: 0.5
""")
        
        config = Config.load(str(config_file))
        
        assert config.schedule is None
    
    def test_load_without_notifications(self, tmp_path):
        """Test loading config without notifications section."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
general:
  timezone: "Europe/Berlin"

kraken:
  api_key: "test_key"
  api_secret: "test_secret"

trade:
  amount_eur: 20.0
  discount_percent: 0.5
""")
        
        config = Config.load(str(config_file))
        
        assert config.notifications is None
    
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
        
        with pytest.raises(Exception):
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
    
    def test_load_with_defaults(self, tmp_path):
        """Test that defaults are applied for optional fields."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
kraken:
  api_key: "test_key"
  api_secret: "test_secret"

trade:
  amount_eur: 20.0
  discount_percent: 0.5
""")
        
        config = Config.load(str(config_file))
        
        # Check defaults
        assert config.general.timezone == "Europe/Berlin"
        assert config.general.log_level == "INFO"
        assert config.trade.validate_order is True
        assert config.trade.min_free_balance == 0.0


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
    
    def test_resolve_none_value(self):
        """Test that None is handled gracefully."""
        result = _resolve_env_var(None)
        assert result is None
    
    def test_resolve_non_string_value(self):
        """Test that non-string values are returned as-is."""
        result = _resolve_env_var(123)
        assert result == 123


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
    
    def test_parse_invalid_string(self):
        """Test that invalid string raises error."""
        with pytest.raises(ValueError):
            _parse_string_to_float("not_a_number")