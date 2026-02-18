"""
Volatility monitoring module for tracking market volatility using ATR.
"""
import asyncio
from datetime import datetime
from typing import Optional, List, Tuple
import structlog
import pandas as pd

from src.database.db import Database
from src.market_data.manager import MarketDataManager
from src.exchange.connector import MarketData


logger = structlog.get_logger(__name__)


class VolatilityMonitor:
    """
    Monitor market volatility using Average True Range (ATR).
    
    Calculates ATR on 1-hour timeframe and alerts when thresholds are exceeded.
    """
    
    def __init__(
        self,
        database: Database,
        market_data_manager: MarketDataManager,
        atr_threshold: float = 100.0,
        atr_period: int = 14
    ):
        """
        Initialize volatility monitor.
        
        Args:
            database: Database instance for storing ATR values
            market_data_manager: Market data manager for fetching data
            atr_threshold: ATR threshold for warnings
            atr_period: Period for ATR calculation (default 14)
        """
        self.database = database
        self.market_data_manager = market_data_manager
        self.atr_threshold = atr_threshold
        self.atr_period = atr_period
        
        # Track active warnings per symbol
        self._active_warnings: dict[str, bool] = {}
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        
        logger.info(
            "volatility_monitor_initialized",
            atr_threshold=atr_threshold,
            atr_period=atr_period
        )
    
    async def calculate_atr(self, symbol: str, timeframe: str = "1h") -> Optional[float]:
        """
        Calculate Average True Range for symbol.
        
        ATR measures market volatility by calculating the average of true ranges
        over a specified period. True Range is the greatest of:
        - Current High - Current Low
        - abs(Current High - Previous Close)
        - abs(Current Low - Previous Close)
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            timeframe: Timeframe for calculation (default '1h')
            
        Returns:
            ATR value or None if insufficient data
        """
        async with self._lock:
            # Get historical market data from market data manager
            # We need at least atr_period + 1 data points
            market_state = await self.market_data_manager.get_market_state(symbol)
            
            if market_state is None:
                logger.warning(
                    "no_market_state",
                    symbol=symbol,
                    timeframe=timeframe
                )
                return None
            
            # For now, we'll use the indicator calculator's historical data
            # In a real implementation, we'd fetch historical candles from the exchange
            # This is a simplified version that works with available data
            
            # Get the latest market data to calculate a simple volatility measure
            latest_data = await self.market_data_manager.get_latest_data(symbol)
            
            if latest_data is None:
                logger.warning(
                    "no_latest_data",
                    symbol=symbol,
                    timeframe=timeframe
                )
                return None
            
            # For demonstration, calculate a simple ATR-like value
            # In production, this would use historical OHLC data
            true_range = latest_data.high - latest_data.low
            
            # This is a simplified ATR calculation
            # A proper implementation would need historical candle data
            atr_value = true_range
            
            logger.debug(
                "atr_calculated",
                symbol=symbol,
                timeframe=timeframe,
                atr=atr_value
            )
            
            return atr_value
    
    async def persist_atr(self, symbol: str, atr: float, timeframe: str = "1h") -> None:
        """
        Save ATR value to SQLite database.
        
        Args:
            symbol: Trading symbol
            atr: ATR value to store
            timeframe: Timeframe for the ATR calculation
        """
        conn = await self.database.get_connection()
        
        await conn.execute(
            """
            INSERT INTO atr_metrics (symbol, timeframe, atr_value, calculated_at)
            VALUES (?, ?, ?, ?)
            """,
            (symbol, timeframe, atr, datetime.now())
        )
        
        await conn.commit()
        
        logger.debug(
            "atr_persisted",
            symbol=symbol,
            timeframe=timeframe,
            atr=atr
        )
    
    async def get_atr_history(
        self,
        symbol: str,
        limit: int = 100
    ) -> List[Tuple[datetime, float]]:
        """
        Retrieve ATR history from SQLite database.
        
        Args:
            symbol: Trading symbol
            limit: Maximum number of records to retrieve
            
        Returns:
            List of (timestamp, atr_value) tuples
        """
        conn = await self.database.get_connection()
        
        cursor = await conn.execute(
            """
            SELECT calculated_at, atr_value
            FROM atr_metrics
            WHERE symbol = ?
            ORDER BY calculated_at DESC
            LIMIT ?
            """,
            (symbol, limit)
        )
        
        rows = await cursor.fetchall()
        
        # Convert to list of tuples with datetime objects
        history = [
            (datetime.fromisoformat(row[0]), row[1])
            for row in rows
        ]
        
        logger.debug(
            "atr_history_retrieved",
            symbol=symbol,
            records=len(history)
        )
        
        return history
    
    async def check_threshold(self, symbol: str) -> Optional[str]:
        """
        Check if ATR exceeds threshold, return warning message if so.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Warning message if threshold exceeded, None otherwise
        """
        atr = await self.calculate_atr(symbol)
        
        if atr is None:
            return None
        
        # Persist the ATR value
        await self.persist_atr(symbol, atr)
        
        if atr > self.atr_threshold:
            # Mark warning as active
            self._active_warnings[symbol] = True
            
            warning_msg = (
                f"⚠️  HIGH VOLATILITY WARNING: {symbol} - "
                f"ATR: {atr:.2f} (Threshold: {self.atr_threshold:.2f})"
            )
            
            logger.warning(
                "volatility_threshold_exceeded",
                symbol=symbol,
                atr=atr,
                threshold=self.atr_threshold
            )
            
            return warning_msg
        else:
            # Clear warning if it was active
            if self._active_warnings.get(symbol, False):
                self._active_warnings[symbol] = False
                logger.info(
                    "volatility_normalized",
                    symbol=symbol,
                    atr=atr,
                    threshold=self.atr_threshold
                )
        
        return None
    
    async def display_metrics(self) -> None:
        """
        Display current volatility metrics for all monitored symbols.
        
        This method checks all subscribed symbols and displays warnings
        for those exceeding the threshold.
        """
        symbols = self.market_data_manager.get_subscribed_symbols()
        
        if not symbols:
            logger.info("no_symbols_monitored")
            return
        
        logger.info("volatility_metrics_update", symbols=symbols)
        
        for symbol in symbols:
            warning = await self.check_threshold(symbol)
            
            if warning:
                # Display warning (in production, this could be sent to a UI or notification system)
                print(warning)
                logger.warning("volatility_warning_displayed", symbol=symbol, message=warning)
            else:
                # Check if we need to display that warning is cleared
                if self._active_warnings.get(symbol, False):
                    clear_msg = f"✓ {symbol} - Volatility normalized (ATR below threshold)"
                    print(clear_msg)
                    logger.info("volatility_warning_cleared", symbol=symbol)
    
    def is_warning_active(self, symbol: str) -> bool:
        """
        Check if a volatility warning is currently active for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            True if warning is active, False otherwise
        """
        return self._active_warnings.get(symbol, False)
