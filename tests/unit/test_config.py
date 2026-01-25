"""Unit tests for configuration management."""

import os
import pytest
from pathlib import Path
from src.config import Config, load_config


class TestConfig:
    """Test Config dataclass validation."""
    
    def test_valid_config(self, tmp_path):
        """Test creating a valid configuration."""
        strategies_dir = tmp_path / "strategies"
        strategies_dir.mkdir()
        
        config = Config(
            exchange_api_key="test_key",
            exchange_api_secret="test_secret",
            strategies_dir=str(strategies_dir)
        )
        
        assert config.exchange_api_key == "test_key"
        assert config.exchange_api_secret == "test_secret"
        assert config.exchange_testnet is True
        assert config.max_total_exposure == 10000.0
        assert config.log_level == "INFO"
    
    def test_missing_api_key(self, tmp_path):
        """Test that missing API key raises validation error."""
        strategies_dir = tmp_path / "strategies"
        strategies_dir.mkdir()
        
        with pytest.raises(ValueError, match="exchange_api_key is required"):
            Config(
                exchange_api_key="",
                exchange_api_secret="test_secret",
                strategies_dir=str(strategies_dir)
            )
    
    def test_missing_api_secret(self, tmp_path):
        """Test that missing API secret raises validation error."""
        strategies_dir = tmp_path / "strategies"
        strategies_dir.mkdir()
        
        with pytest.raises(ValueError, match="exchange_api_secret is required"):
            Config(
                exchange_api_key="test_key",
                exchange_api_secret="",
                strategies_dir=str(strategies_dir)
            )
    
    def test_nonexistent_strategies_dir(self):
        """Test that nonexistent strategies directory raises validation error."""
        with pytest.raises(ValueError, match="strategies_dir does not exist"):
            Config(
                exchange_api_key="test_key",
                exchange_api_secret="test_secret",
                strategies_dir="/nonexistent/path"
            )
    
    def test_negative_max_total_exposure(self, tmp_path):
        """Test that negative max_total_exposure raises validation error."""
        strategies_dir = tmp_path / "strategies"
        strategies_dir.mkdir()
        
        with pytest.raises(ValueError, match="max_total_exposure must be positive"):
            Config(
                exchange_api_key="test_key",
                exchange_api_secret="test_secret",
                strategies_dir=str(strategies_dir),
                max_total_exposure=-100.0
            )
    
    def test_invalid_log_level(self, tmp_path):
        """Test that invalid log level raises validation error."""
        strategies_dir = tmp_path / "strategies"
        strategies_dir.mkdir()
        
        with pytest.raises(ValueError, match="log_level must be one of"):
            Config(
                exchange_api_key="test_key",
                exchange_api_secret="test_secret",
                strategies_dir=str(strategies_dir),
                log_level="INVALID"
            )
    
    def test_invalid_volatility_timeframe(self, tmp_path):
        """Test that invalid volatility timeframe raises validation error."""
        strategies_dir = tmp_path / "strategies"
        strategies_dir.mkdir()
        
        with pytest.raises(ValueError, match="volatility_timeframe must be one of"):
            Config(
                exchange_api_key="test_key",
                exchange_api_secret="test_secret",
                strategies_dir=str(strategies_dir),
                volatility_timeframe="invalid"
            )


class TestLoadConfig:
    """Test config loading from environment variables."""
    
    @pytest.mark.asyncio
    async def test_load_config_from_env(self, tmp_path, monkeypatch):
        """Test loading configuration from environment variables."""
        strategies_dir = tmp_path / "strategies"
        strategies_dir.mkdir()
        
        # Set environment variables
        monkeypatch.setenv("BYBIT_API_KEY", "env_key")
        monkeypatch.setenv("BYBIT_API_SECRET", "env_secret")
        monkeypatch.setenv("BYBIT_TESTNET", "false")
        monkeypatch.setenv("STRATEGIES_DIR", str(strategies_dir))
        monkeypatch.setenv("MAX_TOTAL_EXPOSURE", "5000.0")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        
        config = await load_config()
        
        assert config.exchange_api_key == "env_key"
        assert config.exchange_api_secret == "env_secret"
        assert config.exchange_testnet is False
        assert config.max_total_exposure == 5000.0
        assert config.log_level == "DEBUG"
    
    @pytest.mark.asyncio
    async def test_load_config_with_defaults(self, tmp_path, monkeypatch):
        """Test loading configuration with default values."""
        strategies_dir = tmp_path / "strategies"
        strategies_dir.mkdir()
        
        # Set only required environment variables
        monkeypatch.setenv("BYBIT_API_KEY", "test_key")
        monkeypatch.setenv("BYBIT_API_SECRET", "test_secret")
        monkeypatch.setenv("STRATEGIES_DIR", str(strategies_dir))
        
        config = await load_config()
        
        # Check defaults are applied
        assert config.exchange_testnet is True
        assert config.max_total_exposure == 10000.0
        assert config.log_level == "INFO"
        assert config.volatility_threshold == 2.0
        assert config.api_rate_limit_per_second == 10
    
    @pytest.mark.asyncio
    async def test_load_config_missing_required(self, monkeypatch):
        """Test that missing required parameters raises error."""
        # Don't set API key
        monkeypatch.setenv("BYBIT_API_SECRET", "test_secret")
        
        with pytest.raises(ValueError, match="exchange_api_key is required"):
            await load_config()
    
    @pytest.mark.asyncio
    async def test_load_config_creates_directories(self, tmp_path, monkeypatch):
        """Test that load_config creates required directories."""
        strategies_dir = tmp_path / "strategies"
        strategies_dir.mkdir()
        
        log_dir = tmp_path / "logs"
        db_dir = tmp_path / "data"
        
        monkeypatch.setenv("BYBIT_API_KEY", "test_key")
        monkeypatch.setenv("BYBIT_API_SECRET", "test_secret")
        monkeypatch.setenv("STRATEGIES_DIR", str(strategies_dir))
        monkeypatch.setenv("LOG_FILE", str(log_dir / "test.log"))
        monkeypatch.setenv("DATABASE_PATH", str(db_dir / "test.db"))
        
        config = await load_config()
        
        # Check directories were created
        assert log_dir.exists()
        assert db_dir.exists()
