"""Technical indicator calculations with caching."""

import asyncio
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional, Deque, Tuple
import pandas as pd
import structlog

from src.exchange.connector import MarketData


logger = structlog.get_logger(__name__)


@dataclass
class IndicatorValue:
    """Cached indicator value with timestamp."""
    value: float
    timestamp: datetime
    symbol: str
    indicator_type: str
    timeframe: str


class IndicatorCalculator:
    """
    Calculate technical indicators (RSI, EMA) with caching.
    
    Supports multiple timeframes: 5m, 15m, 30m, 1h, 4h, 1d
    Caches indicator values for performance.
    """
    
    # Timeframe to minutes mapping
    TIMEFRAME_MINUTES = {
        "1m": 1,
        "5m": 5,
        "15m": 15,
        "30m": 30,
        "1h": 60,
        "4h": 240,
        "1d": 1440
    }
    
    def __init__(self, cache_ttl_seconds: int = 60):
        """
        Initialize indicator calculator.
        
        Args:
            cache_ttl_seconds: Time-to-live for cached values
        """
        self.cache_ttl = timedelta(seconds=cache_ttl_seconds)
        
        # Cache: {(symbol, indicator_type, timeframe, period): IndicatorValue}
        self._cache: Dict[Tuple[str, str, str, int], IndicatorValue] = {}
        
        # Historical data storage for calculations
        # {(symbol, timeframe): deque of MarketData}
        self._historical_data: Dict[Tuple[str, str], Deque[MarketData]] = {}
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        
        logger.info("indicator_calculator_initialized", cache_ttl=cache_ttl_seconds)
    
    async def add_market_data(self, data: MarketData, timeframe: str = "1m") -> None:
        """
        Add market data for indicator calculations.
        
        Args:
            data: Market data to add
            timeframe: Timeframe for this data
        """
        async with self._lock:
            key = (data.symbol, timeframe)
            
            if key not in self._historical_data:
                # Initialize with max size based on longest indicator period we might need
                # RSI typically uses 14 periods, EMA can use up to 200
                # Keep 500 data points to be safe
                self._historical_data[key] = deque(maxlen=500)
            
            self._historical_data[key].append(data)
            
            logger.debug(
                "market_data_added",
                symbol=data.symbol,
                timeframe=timeframe,
                data_points=len(self._historical_data[key])
            )
    
    async def calculate_rsi(
        self,
        symbol: str,
        timeframe: str,
        period: int = 14,
        use_cache: bool = True
    ) -> Optional[float]:
        """
        Calculate Relative Strength Index (RSI).
        
        RSI = 100 - (100 / (1 + RS))
        where RS = Average Gain / Average Loss over period
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe (5m, 15m, 30m, 1h, 4h, 1d)
            period: RSI period (default 14)
            use_cache: Use cached value if available
            
        Returns:
            RSI value (0-100) or None if insufficient data
        """
        # Check cache first
        if use_cache:
            cached = await self._get_cached_value(symbol, "rsi", timeframe, period)
            if cached is not None:
                return cached
        
        async with self._lock:
            # Get historical data
            key = (symbol, timeframe)
            if key not in self._historical_data:
                logger.warning(
                    "no_historical_data",
                    symbol=symbol,
                    timeframe=timeframe,
                    indicator="rsi"
                )
                return None
            
            data_points = list(self._historical_data[key])
            
            # Need at least period + 1 data points
            if len(data_points) < period + 1:
                logger.debug(
                    "insufficient_data_for_rsi",
                    symbol=symbol,
                    timeframe=timeframe,
                    required=period + 1,
                    available=len(data_points)
                )
                return None
            
            # Extract closing prices
            closes = pd.Series([d.close for d in data_points])
            
            # Calculate price changes
            delta = closes.diff()
            
            # Separate gains and losses
            gains = delta.where(delta > 0, 0.0)
            losses = -delta.where(delta < 0, 0.0)
            
            # Calculate average gains and losses using EMA
            avg_gain = gains.ewm(span=period, adjust=False).mean()
            avg_loss = losses.ewm(span=period, adjust=False).mean()
            
            # Calculate RS and RSI
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            # Get the latest RSI value
            rsi_value = float(rsi.iloc[-1])
            
            # Cache the result
            await self._cache_value(
                symbol=symbol,
                indicator_type="rsi",
                timeframe=timeframe,
                period=period,
                value=rsi_value
            )
            
            logger.debug(
                "rsi_calculated",
                symbol=symbol,
                timeframe=timeframe,
                period=period,
                rsi=rsi_value
            )
            
            return rsi_value
    
    async def calculate_ema(
        self,
        symbol: str,
        timeframe: str,
        period: int,
        use_cache: bool = True
    ) -> Optional[float]:
        """
        Calculate Exponential Moving Average (EMA).
        
        EMA = Price(t) * k + EMA(y) * (1 - k)
        where k = 2 / (period + 1)
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe (5m, 15m, 30m, 1h, 4h, 1d)
            period: EMA period
            use_cache: Use cached value if available
            
        Returns:
            EMA value or None if insufficient data
        """
        # Check cache first
        if use_cache:
            cached = await self._get_cached_value(symbol, "ema", timeframe, period)
            if cached is not None:
                return cached
        
        async with self._lock:
            # Get historical data
            key = (symbol, timeframe)
            if key not in self._historical_data:
                logger.warning(
                    "no_historical_data",
                    symbol=symbol,
                    timeframe=timeframe,
                    indicator="ema"
                )
                return None
            
            data_points = list(self._historical_data[key])
            
            # Need at least period data points
            if len(data_points) < period:
                logger.debug(
                    "insufficient_data_for_ema",
                    symbol=symbol,
                    timeframe=timeframe,
                    required=period,
                    available=len(data_points)
                )
                return None
            
            # Extract closing prices
            closes = pd.Series([d.close for d in data_points])
            
            # Calculate EMA using pandas
            ema = closes.ewm(span=period, adjust=False).mean()
            
            # Get the latest EMA value
            ema_value = float(ema.iloc[-1])
            
            # Cache the result
            await self._cache_value(
                symbol=symbol,
                indicator_type="ema",
                timeframe=timeframe,
                period=period,
                value=ema_value
            )
            
            logger.debug(
                "ema_calculated",
                symbol=symbol,
                timeframe=timeframe,
                period=period,
                ema=ema_value
            )
            
            return ema_value
    
    async def _get_cached_value(
        self,
        symbol: str,
        indicator_type: str,
        timeframe: str,
        period: int
    ) -> Optional[float]:
        """
        Get cached indicator value if still valid.
        
        Args:
            symbol: Trading symbol
            indicator_type: Type of indicator (rsi, ema)
            timeframe: Timeframe
            period: Indicator period
            
        Returns:
            Cached value or None if not available or expired
        """
        cache_key = (symbol, indicator_type, timeframe, period)
        
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            age = datetime.now() - cached.timestamp
            
            if age <= self.cache_ttl:
                logger.debug(
                    "cache_hit",
                    symbol=symbol,
                    indicator=indicator_type,
                    timeframe=timeframe,
                    period=period,
                    age_seconds=age.total_seconds()
                )
                return cached.value
            else:
                # Cache expired
                logger.debug(
                    "cache_expired",
                    symbol=symbol,
                    indicator=indicator_type,
                    timeframe=timeframe,
                    period=period,
                    age_seconds=age.total_seconds()
                )
                del self._cache[cache_key]
        
        return None
    
    async def _cache_value(
        self,
        symbol: str,
        indicator_type: str,
        timeframe: str,
        period: int,
        value: float
    ) -> None:
        """
        Cache an indicator value.
        
        Args:
            symbol: Trading symbol
            indicator_type: Type of indicator (rsi, ema)
            timeframe: Timeframe
            period: Indicator period
            value: Calculated value
        """
        cache_key = (symbol, indicator_type, timeframe, period)
        
        self._cache[cache_key] = IndicatorValue(
            value=value,
            timestamp=datetime.now(),
            symbol=symbol,
            indicator_type=indicator_type,
            timeframe=timeframe
        )
        
        logger.debug(
            "value_cached",
            symbol=symbol,
            indicator=indicator_type,
            timeframe=timeframe,
            period=period,
            value=value
        )
    
    async def clear_cache(self, symbol: Optional[str] = None) -> None:
        """
        Clear cached indicator values.
        
        Args:
            symbol: If provided, only clear cache for this symbol
        """
        async with self._lock:
            if symbol is None:
                # Clear all cache
                count = len(self._cache)
                self._cache.clear()
                logger.info("cache_cleared", entries_removed=count)
            else:
                # Clear cache for specific symbol
                keys_to_remove = [
                    key for key in self._cache.keys()
                    if key[0] == symbol
                ]
                for key in keys_to_remove:
                    del self._cache[key]
                logger.info(
                    "cache_cleared_for_symbol",
                    symbol=symbol,
                    entries_removed=len(keys_to_remove)
                )
    
    async def get_cache_statistics(self) -> Dict[str, any]:
        """
        Get statistics about cached values.
        
        Returns:
            Dictionary with cache statistics
        """
        async with self._lock:
            now = datetime.now()
            
            total_entries = len(self._cache)
            expired_entries = sum(
                1 for cached in self._cache.values()
                if (now - cached.timestamp) > self.cache_ttl
            )
            valid_entries = total_entries - expired_entries
            
            # Count by indicator type
            by_type = {}
            for key, cached in self._cache.items():
                indicator_type = key[1]
                by_type[indicator_type] = by_type.get(indicator_type, 0) + 1
            
            # Count historical data points
            historical_stats = {
                f"{symbol}_{tf}": len(data)
                for (symbol, tf), data in self._historical_data.items()
            }
            
            return {
                "total_cached_entries": total_entries,
                "valid_entries": valid_entries,
                "expired_entries": expired_entries,
                "by_indicator_type": by_type,
                "historical_data_points": historical_stats
            }
    
    def get_supported_timeframes(self) -> list[str]:
        """
        Get list of supported timeframes.
        
        Returns:
            List of timeframe strings
        """
        return list(self.TIMEFRAME_MINUTES.keys())
    
    async def get_historical_data_count(self, symbol: str, timeframe: str) -> int:
        """
        Get count of historical data points available.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            
        Returns:
            Number of data points available
        """
        async with self._lock:
            key = (symbol, timeframe)
            if key in self._historical_data:
                return len(self._historical_data[key])
            return 0
