"""Configuration management for the Trading Bot System."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv


@dataclass
class Config:
    """System configuration with all parameters."""
    
    # Exchange API credentials
    exchange_api_key: str
    exchange_api_secret: str
    exchange_testnet: bool = True
    
    # Strategy configuration
    strategies_dir: str = "./strategies"
    
    # Risk management
    max_total_exposure: float = 10000.0
    max_position_size: float = 1000.0
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "./logs/trading_bot.log"
    log_max_size_mb: int = 100
    
    # Volatility monitoring
    volatility_threshold: float = 2.0
    volatility_timeframe: str = "1h"
    
    # Database
    database_path: str = "./data/trading_bot.db"
    
    # Exchange settings
    api_rate_limit_per_second: int = 10
    reconnect_max_delay_seconds: int = 60
    order_retry_attempts: int = 3
    
    # Market data
    market_data_timeout_ms: int = 100
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate()
    
    def _validate(self):
        """Validate configuration parameters."""
        errors = []
        
        # Validate required credentials
        if not self.exchange_api_key:
            errors.append("exchange_api_key is required")
        if not self.exchange_api_secret:
            errors.append("exchange_api_secret is required")
        
        # Validate paths exist or can be created
        strategies_path = Path(self.strategies_dir)
        if not strategies_path.exists():
            errors.append(f"strategies_dir does not exist: {self.strategies_dir}")
        
        # Validate numeric parameters
        if self.max_total_exposure <= 0:
            errors.append("max_total_exposure must be positive")
        if self.max_position_size <= 0:
            errors.append("max_position_size must be positive")
        if self.volatility_threshold <= 0:
            errors.append("volatility_threshold must be positive")
        if self.api_rate_limit_per_second <= 0:
            errors.append("api_rate_limit_per_second must be positive")
        if self.reconnect_max_delay_seconds <= 0:
            errors.append("reconnect_max_delay_seconds must be positive")
        if self.order_retry_attempts < 0:
            errors.append("order_retry_attempts must be non-negative")
        if self.market_data_timeout_ms <= 0:
            errors.append("market_data_timeout_ms must be positive")
        if self.log_max_size_mb <= 0:
            errors.append("log_max_size_mb must be positive")
        
        # Validate log level
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level.upper() not in valid_log_levels:
            errors.append(f"log_level must be one of {valid_log_levels}")
        
        # Validate volatility timeframe
        valid_timeframes = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
        if self.volatility_timeframe not in valid_timeframes:
            errors.append(f"volatility_timeframe must be one of {valid_timeframes}")
        
        if errors:
            error_message = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            raise ValueError(error_message)


async def load_config() -> Config:
    """
    Load configuration from environment variables and config files.
    
    Environment variables take precedence over defaults.
    
    Returns:
        Config: Validated configuration object
        
    Raises:
        ValueError: If required parameters are missing or invalid
    """
    # Load environment variables from .env file if it exists
    load_dotenv()
    
    # Read from environment variables with defaults
    config = Config(
        # Required parameters (no defaults)
        exchange_api_key=os.getenv("BYBIT_API_KEY", ""),
        exchange_api_secret=os.getenv("BYBIT_API_SECRET", ""),
        
        # Optional parameters with defaults
        exchange_testnet=os.getenv("BYBIT_TESTNET", "true").lower() in ("true", "1", "yes"),
        strategies_dir=os.getenv("STRATEGIES_DIR", "./strategies"),
        max_total_exposure=float(os.getenv("MAX_TOTAL_EXPOSURE", "10000.0")),
        max_position_size=float(os.getenv("MAX_POSITION_SIZE", "1000.0")),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        log_file=os.getenv("LOG_FILE", "./logs/trading_bot.log"),
        log_max_size_mb=int(os.getenv("LOG_MAX_SIZE_MB", "100")),
        volatility_threshold=float(os.getenv("VOLATILITY_THRESHOLD", "2.0")),
        volatility_timeframe=os.getenv("VOLATILITY_TIMEFRAME", "1h"),
        database_path=os.getenv("DATABASE_PATH", "./data/trading_bot.db"),
        api_rate_limit_per_second=int(os.getenv("API_RATE_LIMIT_PER_SECOND", "10")),
        reconnect_max_delay_seconds=int(os.getenv("RECONNECT_MAX_DELAY_SECONDS", "60")),
        order_retry_attempts=int(os.getenv("ORDER_RETRY_ATTEMPTS", "3")),
        market_data_timeout_ms=int(os.getenv("MARKET_DATA_TIMEOUT_MS", "100")),
    )
    
    # Ensure required directories exist
    _ensure_directories(config)
    
    return config


def _ensure_directories(config: Config) -> None:
    """
    Ensure required directories exist, create them if they don't.
    
    Args:
        config: Configuration object
    """
    # Create log directory if it doesn't exist
    log_path = Path(config.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create database directory if it doesn't exist
    db_path = Path(config.database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
