"""Technical indicator calculations with caching.

This module provides technical indicator calculations including:
- RSI (Relative Strength Index)
- EMA (Exponential Moving Average)
- VWAP (Volume-Weighted Average Price)
- VWAP Standard Deviation Bands

VWAP Calculation:
    VWAP = sum(typical_price × volume) / sum(volume)
    where typical_price = (high + low) / 2

VWAP Standard Deviation:
    variance = (sum(volume × hl2²) / sum(volume)) - VWAP²
    std_dev = sqrt(max(variance, 0))

VWAP Bands:
    upper_band = VWAP + (multiplier × std_dev)
    lower_band = VWAP - (multiplier × std_dev)

Session Management:
    VWAP calculations reset daily at 00:00 UTC to start a new trading session.
    Cumulative sums (vwapsum, volumesum, v2sum) are reset at session boundaries.

All indicator values are cached for performance optimization.
"""

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


@dataclass
class VwapState:
    """State for VWAP calculation per symbol/timeframe."""
    vwapsum: float = 0.0  # Cumulative sum of (hl2 * volume)
    volumesum: float = 0.0  # Cumulative sum of volume
    v2sum: float = 0.0  # Cumulative sum of (volume * hl2 * hl2)
    session_start: Optional[datetime] = None
    last_reset: Optional[datetime] = None


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
        
        # VWAP state tracking: {(symbol, timeframe): VwapState}
        self._vwap_states: Dict[Tuple[str, str], VwapState] = {}
        
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
    
    async def calculate_vwap(
        self,
        symbol: str,
        timeframe: str,
        use_cache: bool = True
    ) -> Optional[float]:
        """
        Calculate Volume-Weighted Average Price (VWAP).
        
        Formula:
            VWAP = sum(typical_price * volume) / sum(volume)
            where typical_price = (high + low) / 2
        
        The VWAP resets daily at 00:00 UTC to start a new trading session.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe (5m, 15m, 30m, 1h, 4h, 1d)
            use_cache: Use cached value if available
            
        Returns:
            VWAP value or None if insufficient data
        """
        # Check cache first (use period=0 for VWAP since it doesn't use period)
        if use_cache:
            cached = await self._get_cached_value(symbol, "vwap", timeframe, 0)
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
                    indicator="vwap"
                )
                return None
            
            data_points = list(self._historical_data[key])
            
            # Need at least 1 data point
            if len(data_points) < 1:
                logger.debug(
                    "insufficient_data_for_vwap",
                    symbol=symbol,
                    timeframe=timeframe,
                    required=1,
                    available=len(data_points)
                )
                return None
            
            # Get or create VWAP state
            state_key = (symbol, timeframe)
            if state_key not in self._vwap_states:
                self._vwap_states[state_key] = VwapState(
                    session_start=data_points[0].timestamp
                )
            
            state = self._vwap_states[state_key]
            
            # Get latest data point
            latest_data = data_points[-1]
            
            # Check if we need to reset for new session (daily at 00:00 UTC)
            if state.last_reset is None:
                state.last_reset = latest_data.timestamp
            
            # Reset if new day - recalculate from scratch for the new session
            if latest_data.timestamp.date() != state.last_reset.date():
                state.vwapsum = 0.0
                state.volumesum = 0.0
                state.v2sum = 0.0
                state.session_start = latest_data.timestamp
                state.last_reset = latest_data.timestamp
                logger.info(
                    "vwap_session_reset",
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=latest_data.timestamp.isoformat()
                )
                
                # Recalculate from all data points in the new session
                for data in data_points:
                    if data.timestamp.date() == latest_data.timestamp.date():
                        hl2 = (data.high + data.low) / 2
                        volume = data.volume
                        state.vwapsum += hl2 * volume
                        state.volumesum += volume
                        state.v2sum += volume * hl2 * hl2
            else:
                # Same session - recalculate from all data points in current session
                # Reset cumulative sums
                state.vwapsum = 0.0
                state.volumesum = 0.0
                state.v2sum = 0.0
                
                # Calculate from all data points in the current session
                for data in data_points:
                    if data.timestamp.date() == state.last_reset.date():
                        hl2 = (data.high + data.low) / 2
                        volume = data.volume
                        state.vwapsum += hl2 * volume
                        state.volumesum += volume
                        state.v2sum += volume * hl2 * hl2
            
            # Calculate VWAP
            if state.volumesum == 0:
                logger.debug(
                    "zero_volume_for_vwap",
                    symbol=symbol,
                    timeframe=timeframe
                )
                return None
            
            vwap = state.vwapsum / state.volumesum
            
            # Cache the result (use period=0 for VWAP)
            await self._cache_value(
                symbol=symbol,
                indicator_type="vwap",
                timeframe=timeframe,
                period=0,
                value=vwap
            )
            
            logger.debug(
                "vwap_calculated",
                symbol=symbol,
                timeframe=timeframe,
                vwap=vwap,
                volumesum=state.volumesum
            )
            
            return vwap
    
    async def calculate_vwap_std_dev(
        self,
        symbol: str,
        timeframe: str,
        use_cache: bool = True
    ) -> Optional[float]:
        """
        Calculate VWAP standard deviation.
        
        Formula:
            variance = (sum(volume * hl2^2) / sum(volume)) - VWAP^2
            std_dev = sqrt(max(variance, 0))
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe (5m, 15m, 30m, 1h, 4h, 1d)
            use_cache: Use cached value if available
            
        Returns:
            Standard deviation value or None if insufficient data
        """
        # Check cache first (use period=0 for VWAP std dev since it doesn't use period)
        if use_cache:
            cached = await self._get_cached_value(symbol, "vwap_std_dev", timeframe, 0)
            if cached is not None:
                return cached
        
        # Get VWAP state
        state_key = (symbol, timeframe)
        if state_key not in self._vwap_states:
            logger.debug(
                "no_vwap_state",
                symbol=symbol,
                timeframe=timeframe,
                indicator="vwap_std_dev"
            )
            return None
        
        state = self._vwap_states[state_key]
        
        if state.volumesum == 0:
            logger.debug(
                "zero_volume_for_vwap_std_dev",
                symbol=symbol,
                timeframe=timeframe
            )
            return None
        
        # Calculate VWAP first
        vwap = await self.calculate_vwap(symbol, timeframe, use_cache=use_cache)
        if vwap is None:
            return None
        
        # Calculate variance
        variance = (state.v2sum / state.volumesum) - (vwap * vwap)
        
        # Handle floating point precision issues - clamp negative variance to 0
        variance = max(variance, 0.0)
        
        # Calculate standard deviation
        std_dev = variance ** 0.5
        
        # Cache the result (use period=0 for VWAP std dev)
        await self._cache_value(
            symbol=symbol,
            indicator_type="vwap_std_dev",
            timeframe=timeframe,
            period=0,
            value=std_dev
        )
        
        logger.debug(
            "vwap_std_dev_calculated",
            symbol=symbol,
            timeframe=timeframe,
            std_dev=std_dev,
            variance=variance
        )
        
        return std_dev
    
    async def calculate_vwap_band(
        self,
        symbol: str,
        timeframe: str,
        std_dev_multiplier: float,
        band_type: str,
        use_cache: bool = True
    ) -> Optional[float]:
        """
        Calculate VWAP band at specified standard deviation level.
        
        Formula:
            upper_band = VWAP + (multiplier * std_dev)
            lower_band = VWAP - (multiplier * std_dev)
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe (5m, 15m, 30m, 1h, 4h, 1d)
            std_dev_multiplier: Standard deviation multiplier (e.g., 2.0, 3.0)
            band_type: "upper" or "lower"
            use_cache: Use cached value if available
            
        Returns:
            Band value or None if insufficient data
            
        Raises:
            ValueError: If band_type is not "upper" or "lower"
        """
        # Validate band_type
        if band_type not in ["upper", "lower"]:
            raise ValueError(f"Invalid band_type: {band_type}. Must be 'upper' or 'lower'")
        
        # Check cache first
        cache_key = f"vwap_band_{band_type}_{std_dev_multiplier}_{symbol}_{timeframe}"
        if use_cache:
            # Use period=0 for VWAP bands since they don't use period
            cached = await self._get_cached_value(symbol, cache_key, timeframe, 0)
            if cached is not None:
                return cached
        
        # Calculate VWAP
        vwap = await self.calculate_vwap(symbol, timeframe, use_cache=use_cache)
        if vwap is None:
            logger.debug(
                "vwap_not_available_for_band",
                symbol=symbol,
                timeframe=timeframe,
                band_type=band_type,
                std_dev_multiplier=std_dev_multiplier
            )
            return None
        
        # Calculate standard deviation
        std_dev = await self.calculate_vwap_std_dev(symbol, timeframe, use_cache=use_cache)
        if std_dev is None:
            logger.debug(
                "vwap_std_dev_not_available_for_band",
                symbol=symbol,
                timeframe=timeframe,
                band_type=band_type,
                std_dev_multiplier=std_dev_multiplier
            )
            return None
        
        # Calculate band
        if band_type == "upper":
            band = vwap + (std_dev_multiplier * std_dev)
        else:  # band_type == "lower"
            band = vwap - (std_dev_multiplier * std_dev)
        
        # Cache the result (use period=0 for VWAP bands)
        await self._cache_value(
            symbol=symbol,
            indicator_type=cache_key,
            timeframe=timeframe,
            period=0,
            value=band
        )
        
        logger.debug(
            "vwap_band_calculated",
            symbol=symbol,
            timeframe=timeframe,
            band_type=band_type,
            std_dev_multiplier=std_dev_multiplier,
            vwap=vwap,
            std_dev=std_dev,
            band=band
        )
        
        return band
    
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
