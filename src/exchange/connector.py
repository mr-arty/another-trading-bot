"""Exchange connector for Bybit API integration."""

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable, Awaitable
from enum import Enum
import structlog
from pybit.unified_trading import HTTP, WebSocket


logger = structlog.get_logger(__name__)


class OrderSide(Enum):
    """Order side enumeration."""
    BUY = "Buy"
    SELL = "Sell"


class OrderType(Enum):
    """Order type enumeration."""
    MARKET = "Market"
    LIMIT = "Limit"


class OrderStatus(Enum):
    """Order status enumeration."""
    PENDING = "Pending"
    FILLED = "Filled"
    PARTIALLY_FILLED = "PartiallyFilled"
    CANCELLED = "Cancelled"
    REJECTED = "Rejected"


@dataclass
class MarketData:
    """Market data structure."""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class Order:
    """Order structure."""
    order_id: str
    strategy_name: str
    symbol: str
    side: str  # 'Buy' or 'Sell'
    order_type: str  # 'Market' or 'Limit'
    quantity: float
    price: Optional[float]
    status: str
    timestamp: datetime


@dataclass
class OrderResult:
    """Result of order submission."""
    success: bool
    order_id: Optional[str]
    message: str
    data: Optional[Dict[str, Any]] = None


@dataclass
class Position:
    """Position structure."""
    symbol: str
    quantity: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float = 0.0
    side: str = "Buy"  # 'Buy' for long, 'Sell' for short


class TokenBucket:
    """Token bucket algorithm for rate limiting."""
    
    def __init__(self, rate: int, capacity: int = None):
        """
        Initialize token bucket.
        
        Args:
            rate: Tokens added per second
            capacity: Maximum tokens (defaults to rate)
        """
        self.rate = rate
        self.capacity = capacity or rate
        self.tokens = float(self.capacity)
        self.last_update = time.time()
        self._lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1) -> None:
        """
        Acquire tokens, waiting if necessary.
        
        Args:
            tokens: Number of tokens to acquire
        """
        async with self._lock:
            while True:
                now = time.time()
                elapsed = now - self.last_update
                self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
                self.last_update = now
                
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return
                
                # Wait for enough tokens to accumulate
                wait_time = (tokens - self.tokens) / self.rate
                await asyncio.sleep(wait_time)


class ExchangeConnector:
    """
    Exchange connector for Bybit API.
    
    Manages authenticated connections, WebSocket streams, and REST API calls.
    """
    
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        testnet: bool = True,
        rate_limit_per_second: int = 10,
        max_reconnect_delay: int = 60
    ):
        """
        Initialize exchange connector.
        
        Args:
            api_key: Bybit API key
            api_secret: Bybit API secret
            testnet: Use testnet if True, mainnet if False
            rate_limit_per_second: Maximum API requests per second
            max_reconnect_delay: Maximum delay between reconnection attempts
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.max_reconnect_delay = max_reconnect_delay
        
        # Rate limiting
        self.rate_limiter = TokenBucket(rate=rate_limit_per_second)
        
        # Connection state
        self._connected = False
        self._reconnecting = False
        self._should_reconnect = True
        
        # HTTP client for REST API
        self.http_client: Optional[HTTP] = None
        
        # WebSocket client for market data
        self.ws_client: Optional[WebSocket] = None
        
        # Market data subscriptions
        self._subscriptions: Dict[str, List[Callable[[MarketData], Awaitable[None]]]] = {}
        
        # Error callbacks for strategies
        self._error_callbacks: List[Callable[[str, Exception], Awaitable[None]]] = []
        
        logger.info(
            "exchange_connector_initialized",
            testnet=testnet,
            rate_limit=rate_limit_per_second
        )
    
    async def connect(self) -> None:
        """
        Establish connection to Bybit exchange.
        
        Creates both HTTP and WebSocket clients with authentication.
        """
        try:
            # Initialize HTTP client for REST API
            self.http_client = HTTP(
                testnet=self.testnet,
                api_key=self.api_key,
                api_secret=self.api_secret
            )
            
            # Initialize WebSocket client for market data
            self.ws_client = WebSocket(
                testnet=self.testnet,
                channel_type="linear",
                api_key=self.api_key,
                api_secret=self.api_secret
            )
            
            self._connected = True
            self._should_reconnect = True
            
            logger.info("exchange_connected", testnet=self.testnet)
            
        except Exception as e:
            logger.error("exchange_connection_failed", error=str(e), exc_info=True)
            await self._notify_error("connection", e)
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from exchange and clean up resources."""
        self._should_reconnect = False
        self._connected = False
        
        # Close WebSocket connection
        if self.ws_client:
            try:
                # pybit WebSocket doesn't have an async close method
                # Just set to None and let garbage collection handle it
                self.ws_client = None
            except Exception as e:
                logger.warning("websocket_close_error", error=str(e))
        
        logger.info("exchange_disconnected")
    
    async def _reconnect_with_backoff(self) -> None:
        """
        Reconnect to exchange with exponential backoff.
        
        Implements exponential backoff: 1s, 2s, 4s, 8s, 16s, max 60s
        """
        if self._reconnecting:
            return
        
        self._reconnecting = True
        delay = 1
        
        while self._should_reconnect and not self._connected:
            try:
                logger.info("attempting_reconnection", delay=delay)
                await self.connect()
                self._reconnecting = False
                logger.info("reconnection_successful")
                return
                
            except Exception as e:
                logger.warning(
                    "reconnection_failed",
                    error=str(e),
                    next_attempt_in=delay
                )
                
                await asyncio.sleep(delay)
                
                # Exponential backoff with max delay
                delay = min(delay * 2, self.max_reconnect_delay)
        
        self._reconnecting = False
    
    def _check_connection(self) -> None:
        """Check if connected, attempt reconnection if not."""
        if not self._connected and self._should_reconnect:
            asyncio.create_task(self._reconnect_with_backoff())
            raise ConnectionError("Not connected to exchange, reconnection in progress")
    
    async def subscribe_market_data(
        self,
        symbols: List[str],
        callback: Callable[[MarketData], Awaitable[None]]
    ) -> None:
        """
        Subscribe to market data streams for specified symbols.
        
        Args:
            symbols: List of trading symbols (e.g., ['BTCUSDT', 'ETHUSDT'])
            callback: Async callback function to receive market data
        """
        self._check_connection()
        
        for symbol in symbols:
            if symbol not in self._subscriptions:
                self._subscriptions[symbol] = []
            
            self._subscriptions[symbol].append(callback)
            
            # Subscribe to kline (candlestick) data via WebSocket
            try:
                # Subscribe to 1-minute klines for real-time data
                self.ws_client.kline_stream(
                    interval=1,
                    symbol=symbol,
                    callback=lambda msg: asyncio.create_task(
                        self._handle_market_data(symbol, msg, callback)
                    )
                )
                
                logger.info("market_data_subscribed", symbol=symbol)
                
            except Exception as e:
                logger.error(
                    "market_data_subscription_failed",
                    symbol=symbol,
                    error=str(e),
                    exc_info=True
                )
                await self._notify_error(f"subscribe_{symbol}", e)
                raise
    
    async def _handle_market_data(
        self,
        symbol: str,
        message: Dict[str, Any],
        callback: Callable[[MarketData], Awaitable[None]]
    ) -> None:
        """
        Parse and validate market data from WebSocket.
        
        Args:
            symbol: Trading symbol
            message: Raw message from WebSocket
            callback: Callback to invoke with parsed data
        """
        try:
            # Validate message structure
            if not message or 'data' not in message:
                logger.warning("invalid_market_data", symbol=symbol, message=message)
                return
            
            data = message['data']
            
            # Parse kline data
            if isinstance(data, list) and len(data) > 0:
                kline = data[0]
            else:
                kline = data
            
            # Create MarketData instance
            market_data = MarketData(
                symbol=symbol,
                timestamp=datetime.fromtimestamp(int(kline['start']) / 1000),
                open=float(kline['open']),
                high=float(kline['high']),
                low=float(kline['low']),
                close=float(kline['close']),
                volume=float(kline['volume'])
            )
            
            # Invoke callback
            await callback(market_data)
            
        except Exception as e:
            logger.error(
                "market_data_parsing_failed",
                symbol=symbol,
                error=str(e),
                message=message,
                exc_info=True
            )
            await self._notify_error(f"parse_{symbol}", e)
    
    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: Optional[float] = None,
        strategy_name: str = ""
    ) -> OrderResult:
        """
        Place an order on the exchange.
        
        Args:
            symbol: Trading symbol
            side: Order side (Buy/Sell)
            order_type: Order type (Market/Limit)
            quantity: Order quantity
            price: Limit price (required for limit orders)
            strategy_name: Name of strategy placing order
            
        Returns:
            OrderResult with success status and order details
        """
        self._check_connection()
        
        # Apply rate limiting
        await self.rate_limiter.acquire()
        
        try:
            # Prepare order parameters
            params = {
                "category": "linear",
                "symbol": symbol,
                "side": side.value,
                "orderType": order_type.value,
                "qty": str(quantity),
            }
            
            if order_type == OrderType.LIMIT:
                if price is None:
                    raise ValueError("Price required for limit orders")
                params["price"] = str(price)
            
            # Submit order via REST API
            response = self.http_client.place_order(**params)
            
            # Parse response
            if response.get("retCode") == 0:
                result = response.get("result", {})
                order_id = result.get("orderId", "")
                
                logger.info(
                    "order_placed",
                    order_id=order_id,
                    symbol=symbol,
                    side=side.value,
                    quantity=quantity,
                    strategy=strategy_name
                )
                
                return OrderResult(
                    success=True,
                    order_id=order_id,
                    message="Order placed successfully",
                    data=result
                )
            else:
                error_msg = response.get("retMsg", "Unknown error")
                logger.error(
                    "order_placement_failed",
                    symbol=symbol,
                    error=error_msg,
                    response=response
                )
                
                await self._notify_error(f"place_order_{symbol}", Exception(error_msg))
                
                return OrderResult(
                    success=False,
                    order_id=None,
                    message=error_msg,
                    data=response
                )
                
        except Exception as e:
            logger.error(
                "order_placement_exception",
                symbol=symbol,
                error=str(e),
                exc_info=True
            )
            await self._notify_error(f"place_order_{symbol}", e)
            
            return OrderResult(
                success=False,
                order_id=None,
                message=str(e)
            )
    
    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """
        Cancel a pending order.
        
        Args:
            symbol: Trading symbol
            order_id: Order ID to cancel
            
        Returns:
            True if cancellation successful, False otherwise
        """
        self._check_connection()
        
        # Apply rate limiting
        await self.rate_limiter.acquire()
        
        try:
            response = self.http_client.cancel_order(
                category="linear",
                symbol=symbol,
                orderId=order_id
            )
            
            if response.get("retCode") == 0:
                logger.info("order_cancelled", order_id=order_id, symbol=symbol)
                return True
            else:
                error_msg = response.get("retMsg", "Unknown error")
                logger.error(
                    "order_cancellation_failed",
                    order_id=order_id,
                    error=error_msg
                )
                await self._notify_error(f"cancel_order_{order_id}", Exception(error_msg))
                return False
                
        except Exception as e:
            logger.error(
                "order_cancellation_exception",
                order_id=order_id,
                error=str(e),
                exc_info=True
            )
            await self._notify_error(f"cancel_order_{order_id}", e)
            return False
    
    async def get_positions(self) -> List[Position]:
        """
        Fetch current positions from exchange.
        
        Returns:
            List of Position objects
        """
        self._check_connection()
        
        # Apply rate limiting
        await self.rate_limiter.acquire()
        
        try:
            response = self.http_client.get_positions(
                category="linear",
                settleCoin="USDT"
            )
            
            if response.get("retCode") != 0:
                error_msg = response.get("retMsg", "Unknown error")
                logger.error("get_positions_failed", error=error_msg)
                await self._notify_error("get_positions", Exception(error_msg))
                return []
            
            positions = []
            result = response.get("result", {})
            position_list = result.get("list", [])
            
            for pos_data in position_list:
                size = float(pos_data.get("size", 0))
                if size > 0:  # Only include open positions
                    position = Position(
                        symbol=pos_data.get("symbol", ""),
                        quantity=size,
                        entry_price=float(pos_data.get("avgPrice", 0)),
                        current_price=float(pos_data.get("markPrice", 0)),
                        unrealized_pnl=float(pos_data.get("unrealisedPnl", 0)),
                        realized_pnl=float(pos_data.get("cumRealisedPnl", 0)),
                        side=pos_data.get("side", "Buy")
                    )
                    positions.append(position)
            
            logger.info("positions_fetched", count=len(positions))
            return positions
            
        except Exception as e:
            logger.error(
                "get_positions_exception",
                error=str(e),
                exc_info=True
            )
            await self._notify_error("get_positions", e)
            return []
    
    async def close_position(self, symbol: str, side: str = "Buy") -> OrderResult:
        """
        Close a position at market price.
        
        Args:
            symbol: Trading symbol
            side: Position side ('Buy' for long, 'Sell' for short)
            
        Returns:
            OrderResult with closure details
        """
        self._check_connection()
        
        # Get current position to determine quantity
        positions = await self.get_positions()
        position = next((p for p in positions if p.symbol == symbol and p.side == side), None)
        
        if not position:
            return OrderResult(
                success=False,
                order_id=None,
                message=f"No open position found for {symbol}"
            )
        
        # Close position by placing opposite market order
        close_side = OrderSide.SELL if side == "Buy" else OrderSide.BUY
        
        return await self.place_order(
            symbol=symbol,
            side=close_side,
            order_type=OrderType.MARKET,
            quantity=position.quantity,
            strategy_name="close_position"
        )
    
    def register_error_callback(
        self,
        callback: Callable[[str, Exception], Awaitable[None]]
    ) -> None:
        """
        Register a callback to be notified of API errors.
        
        Args:
            callback: Async function to call on errors (operation_name, exception)
        """
        self._error_callbacks.append(callback)
    
    async def _notify_error(self, operation: str, error: Exception) -> None:
        """
        Notify all registered error callbacks.
        
        Args:
            operation: Name of operation that failed
            error: Exception that occurred
        """
        for callback in self._error_callbacks:
            try:
                await callback(operation, error)
            except Exception as e:
                logger.error(
                    "error_callback_failed",
                    operation=operation,
                    error=str(e),
                    exc_info=True
                )
