"""Market data management and distribution."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Callable, Awaitable, Optional, Set
import structlog

from src.exchange.connector import MarketData, ExchangeConnector


logger = structlog.get_logger(__name__)


@dataclass
class MarketDataState:
    """State of market data for a symbol."""
    symbol: str
    last_update: datetime
    data: MarketData
    subscribers: List[Callable[[MarketData], Awaitable[None]]] = field(default_factory=list)
    is_subscribed: bool = False
    last_interruption: Optional[datetime] = None


class MarketDataManager:
    """
    Manages market data subscriptions and distribution.
    
    Implements shared data streams to avoid duplicate subscriptions
    and distributes market data to all subscribed strategies.
    """
    
    def __init__(
        self,
        exchange_connector: ExchangeConnector,
        interruption_threshold_seconds: int = 30
    ):
        """
        Initialize market data manager.
        
        Args:
            exchange_connector: Exchange connector for market data
            interruption_threshold_seconds: Time without data before considering stream interrupted
        """
        self.exchange = exchange_connector
        self.interruption_threshold = timedelta(seconds=interruption_threshold_seconds)
        
        # Market data state storage
        self._market_states: Dict[str, MarketDataState] = {}
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        
        # Monitoring task
        self._monitor_task: Optional[asyncio.Task] = None
        self._running = False
        
        logger.info(
            "market_data_manager_initialized",
            interruption_threshold=interruption_threshold_seconds
        )
    
    async def subscribe(
        self,
        symbol: str,
        callback: Callable[[MarketData], Awaitable[None]]
    ) -> None:
        """
        Subscribe to market data for a symbol.
        
        If this is the first subscription for the symbol, creates a new
        subscription to the exchange. Otherwise, adds the callback to the
        existing subscription (shared data stream).
        
        Args:
            symbol: Trading symbol to subscribe to
            callback: Async callback to receive market data updates
        """
        async with self._lock:
            # Check if we already have a subscription for this symbol
            if symbol not in self._market_states:
                # Create new market data state
                self._market_states[symbol] = MarketDataState(
                    symbol=symbol,
                    last_update=datetime.now(),
                    data=None,
                    subscribers=[],
                    is_subscribed=False
                )
                
                logger.info(
                    "creating_new_subscription",
                    symbol=symbol
                )
                
                # Subscribe to exchange data stream
                await self._subscribe_to_exchange(symbol)
            else:
                logger.info(
                    "reusing_existing_subscription",
                    symbol=symbol,
                    existing_subscribers=len(self._market_states[symbol].subscribers)
                )
            
            # Add callback to subscribers
            self._market_states[symbol].subscribers.append(callback)
            
            logger.info(
                "subscription_added",
                symbol=symbol,
                total_subscribers=len(self._market_states[symbol].subscribers)
            )
    
    async def unsubscribe(
        self,
        symbol: str,
        callback: Callable[[MarketData], Awaitable[None]]
    ) -> None:
        """
        Unsubscribe from market data for a symbol.
        
        Removes the callback from the subscription. If this was the last
        subscriber, the exchange subscription is maintained but marked
        for potential cleanup.
        
        Args:
            symbol: Trading symbol
            callback: Callback to remove
        """
        async with self._lock:
            if symbol not in self._market_states:
                logger.warning("unsubscribe_unknown_symbol", symbol=symbol)
                return
            
            state = self._market_states[symbol]
            
            if callback in state.subscribers:
                state.subscribers.remove(callback)
                logger.info(
                    "subscription_removed",
                    symbol=symbol,
                    remaining_subscribers=len(state.subscribers)
                )
    
    async def _subscribe_to_exchange(self, symbol: str) -> None:
        """
        Subscribe to exchange market data stream.
        
        Args:
            symbol: Trading symbol
        """
        try:
            # Create a callback that distributes data to all subscribers
            async def distribution_callback(data: MarketData) -> None:
                await self._distribute_market_data(symbol, data)
            
            # Subscribe to exchange
            await self.exchange.subscribe_market_data([symbol], distribution_callback)
            
            # Mark as subscribed
            self._market_states[symbol].is_subscribed = True
            
            logger.info("exchange_subscription_created", symbol=symbol)
            
        except Exception as e:
            logger.error(
                "exchange_subscription_failed",
                symbol=symbol,
                error=str(e),
                exc_info=True
            )
            raise
    
    async def _distribute_market_data(self, symbol: str, data: MarketData) -> None:
        """
        Distribute market data to all subscribers for a symbol.
        
        Args:
            symbol: Trading symbol
            data: Market data to distribute
        """
        async with self._lock:
            if symbol not in self._market_states:
                logger.warning("received_data_for_unknown_symbol", symbol=symbol)
                return
            
            state = self._market_states[symbol]
            
            # Update state
            state.last_update = datetime.now()
            state.data = data
            
            # Clear interruption flag if it was set
            if state.last_interruption:
                logger.info(
                    "stream_recovered",
                    symbol=symbol,
                    interruption_duration=(datetime.now() - state.last_interruption).total_seconds()
                )
                state.last_interruption = None
            
            logger.debug(
                "distributing_market_data",
                symbol=symbol,
                subscribers=len(state.subscribers),
                timestamp=data.timestamp
            )
        
        # Distribute to subscribers outside the lock to avoid blocking
        subscribers = state.subscribers.copy()
        
        for callback in subscribers:
            try:
                await callback(data)
            except Exception as e:
                logger.error(
                    "subscriber_callback_failed",
                    symbol=symbol,
                    error=str(e),
                    exc_info=True
                )
    
    async def get_latest_data(self, symbol: str) -> Optional[MarketData]:
        """
        Get the latest market data for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Latest MarketData or None if not available
        """
        async with self._lock:
            if symbol in self._market_states:
                return self._market_states[symbol].data
            return None
    
    async def get_market_state(self, symbol: str) -> Optional[MarketDataState]:
        """
        Get the complete market data state for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            MarketDataState or None if not available
        """
        async with self._lock:
            if symbol in self._market_states:
                return self._market_states[symbol]
            return None
    
    def get_subscribed_symbols(self) -> List[str]:
        """
        Get list of all subscribed symbols.
        
        Returns:
            List of symbol strings
        """
        return list(self._market_states.keys())
    
    async def start_monitoring(self) -> None:
        """
        Start monitoring for stream interruptions.
        
        Periodically checks if market data streams have been interrupted
        and attempts recovery.
        """
        if self._running:
            logger.warning("monitoring_already_running")
            return
        
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_streams())
        
        logger.info("stream_monitoring_started")
    
    async def stop_monitoring(self) -> None:
        """Stop monitoring for stream interruptions."""
        self._running = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
        
        logger.info("stream_monitoring_stopped")
    
    async def _monitor_streams(self) -> None:
        """
        Monitor market data streams for interruptions.
        
        Checks periodically if any streams have stopped receiving data
        and attempts to recover them.
        """
        while self._running:
            try:
                await asyncio.sleep(10)  # Check every 10 seconds
                
                now = datetime.now()
                
                async with self._lock:
                    for symbol, state in self._market_states.items():
                        # Check if stream is interrupted
                        time_since_update = now - state.last_update
                        
                        if time_since_update > self.interruption_threshold:
                            if not state.last_interruption:
                                # First detection of interruption
                                state.last_interruption = now
                                
                                logger.warning(
                                    "stream_interruption_detected",
                                    symbol=symbol,
                                    time_since_update=time_since_update.total_seconds()
                                )
                                
                                # Attempt recovery
                                asyncio.create_task(self._recover_stream(symbol))
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    "stream_monitoring_error",
                    error=str(e),
                    exc_info=True
                )
    
    async def _recover_stream(self, symbol: str) -> None:
        """
        Recover an interrupted market data stream.
        
        Attempts to resubscribe to the exchange and notifies all
        subscribers of the data gap.
        
        Args:
            symbol: Trading symbol with interrupted stream
        """
        try:
            logger.info("attempting_stream_recovery", symbol=symbol)
            
            # Get current state
            async with self._lock:
                if symbol not in self._market_states:
                    return
                
                state = self._market_states[symbol]
                subscribers = state.subscribers.copy()
            
            # Notify subscribers of data gap
            await self._notify_data_gap(symbol, subscribers)
            
            # Resubscribe to exchange
            await self._resubscribe_to_exchange(symbol)
            
            logger.info("stream_recovery_completed", symbol=symbol)
            
        except Exception as e:
            logger.error(
                "stream_recovery_failed",
                symbol=symbol,
                error=str(e),
                exc_info=True
            )
    
    async def _resubscribe_to_exchange(self, symbol: str) -> None:
        """
        Resubscribe to exchange market data stream.
        
        Args:
            symbol: Trading symbol
        """
        try:
            # Mark as not subscribed
            async with self._lock:
                if symbol in self._market_states:
                    self._market_states[symbol].is_subscribed = False
            
            # Resubscribe
            await self._subscribe_to_exchange(symbol)
            
            logger.info("resubscription_successful", symbol=symbol)
            
        except Exception as e:
            logger.error(
                "resubscription_failed",
                symbol=symbol,
                error=str(e),
                exc_info=True
            )
            raise
    
    async def _notify_data_gap(
        self,
        symbol: str,
        subscribers: List[Callable[[MarketData], Awaitable[None]]]
    ) -> None:
        """
        Notify subscribers of a data gap.
        
        Creates a special MarketData instance with None values to signal
        the gap to subscribers.
        
        Args:
            symbol: Trading symbol
            subscribers: List of subscriber callbacks
        """
        # Create a data gap notification
        gap_notification = MarketData(
            symbol=symbol,
            timestamp=datetime.now(),
            open=0.0,
            high=0.0,
            low=0.0,
            close=0.0,
            volume=0.0
        )
        
        logger.info(
            "notifying_data_gap",
            symbol=symbol,
            subscribers=len(subscribers)
        )
        
        # Notify all subscribers
        for callback in subscribers:
            try:
                await callback(gap_notification)
            except Exception as e:
                logger.error(
                    "data_gap_notification_failed",
                    symbol=symbol,
                    error=str(e),
                    exc_info=True
                )
    
    async def get_statistics(self) -> Dict[str, Dict[str, any]]:
        """
        Get statistics about market data subscriptions.
        
        Returns:
            Dict mapping symbols to their statistics
        """
        async with self._lock:
            stats = {}
            
            for symbol, state in self._market_states.items():
                stats[symbol] = {
                    "subscribers": len(state.subscribers),
                    "is_subscribed": state.is_subscribed,
                    "last_update": state.last_update.isoformat() if state.last_update else None,
                    "has_data": state.data is not None,
                    "is_interrupted": state.last_interruption is not None,
                    "interruption_time": state.last_interruption.isoformat() if state.last_interruption else None
                }
            
            return stats
