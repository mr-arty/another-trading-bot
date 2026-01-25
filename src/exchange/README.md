# Exchange Connector Module

This module provides the `ExchangeConnector` class for integrating with the Bybit cryptocurrency exchange API.

## Features

### ✓ Authenticated Connection
- Establishes authenticated connections to Bybit using API credentials
- Supports both testnet and mainnet environments
- Manages both REST API (HTTP) and WebSocket connections

### ✓ Reconnection Logic with Exponential Backoff
- Automatically detects connection losses
- Implements exponential backoff: 1s, 2s, 4s, 8s, 16s, max 60s
- Continues reconnection attempts until successful or manually stopped

### ✓ Market Data Subscription and Parsing
- Subscribes to real-time market data streams via WebSocket
- Parses and validates incoming kline (candlestick) data
- Creates structured `MarketData` objects with OHLCV data
- Supports multiple symbol subscriptions with shared callbacks

### ✓ API Rate Limiting
- Implements token bucket algorithm for rate limit enforcement
- Configurable requests per second limit
- Automatically queues requests when approaching rate limits
- Prevents API throttling and request rejections

### ✓ API Error Handling
- Catches and logs all API error responses
- Notifies registered callbacks of errors
- Includes operation context and error details
- Continues operation after non-fatal errors

### ✓ Order Management
- Place market and limit orders
- Cancel pending orders
- Track order status
- Query current positions
- Close positions at market price

## Usage

### Basic Initialization

```python
from src.exchange import ExchangeConnector, OrderSide, OrderType

connector = ExchangeConnector(
    api_key="your_api_key",
    api_secret="your_api_secret",
    testnet=True,  # Use testnet for testing
    rate_limit_per_second=10,
    max_reconnect_delay=60
)
```

### Connecting to Exchange

```python
await connector.connect()
```

### Subscribing to Market Data

```python
async def handle_market_data(data: MarketData):
    print(f"{data.symbol}: {data.close} @ {data.timestamp}")

await connector.subscribe_market_data(
    symbols=["BTCUSDT", "ETHUSDT"],
    callback=handle_market_data
)
```

### Placing Orders

```python
# Market order
result = await connector.place_order(
    symbol="BTCUSDT",
    side=OrderSide.BUY,
    order_type=OrderType.MARKET,
    quantity=0.001,
    strategy_name="my_strategy"
)

# Limit order
result = await connector.place_order(
    symbol="BTCUSDT",
    side=OrderSide.BUY,
    order_type=OrderType.LIMIT,
    quantity=0.001,
    price=50000.0,
    strategy_name="my_strategy"
)

if result.success:
    print(f"Order placed: {result.order_id}")
else:
    print(f"Order failed: {result.message}")
```

### Querying Positions

```python
positions = await connector.get_positions()
for pos in positions:
    print(f"{pos.symbol}: {pos.quantity} @ {pos.entry_price}")
    print(f"  Unrealized P&L: {pos.unrealized_pnl}")
```

### Closing Positions

```python
result = await connector.close_position(
    symbol="BTCUSDT",
    side="Buy"  # 'Buy' for long positions, 'Sell' for short
)
```

### Error Handling

```python
async def handle_error(operation: str, error: Exception):
    print(f"Error in {operation}: {error}")
    # Notify strategies, log to database, etc.

connector.register_error_callback(handle_error)
```

### Disconnecting

```python
await connector.disconnect()
```

## Data Structures

### MarketData
```python
@dataclass
class MarketData:
    symbol: str          # Trading symbol (e.g., "BTCUSDT")
    timestamp: datetime  # Data timestamp
    open: float         # Opening price
    high: float         # Highest price
    low: float          # Lowest price
    close: float        # Closing price
    volume: float       # Trading volume
```

### Order
```python
@dataclass
class Order:
    order_id: str       # Unique order identifier
    strategy_name: str  # Strategy that placed the order
    symbol: str         # Trading symbol
    side: str          # 'Buy' or 'Sell'
    order_type: str    # 'Market' or 'Limit'
    quantity: float    # Order quantity
    price: Optional[float]  # Limit price (None for market orders)
    status: str        # Order status
    timestamp: datetime # Order creation time
```

### Position
```python
@dataclass
class Position:
    symbol: str         # Trading symbol
    quantity: float     # Position size
    entry_price: float  # Average entry price
    current_price: float # Current market price
    unrealized_pnl: float # Unrealized profit/loss
    realized_pnl: float   # Realized profit/loss
    side: str          # 'Buy' for long, 'Sell' for short
```

### OrderResult
```python
@dataclass
class OrderResult:
    success: bool       # Whether operation succeeded
    order_id: Optional[str]  # Order ID if successful
    message: str        # Success or error message
    data: Optional[Dict[str, Any]]  # Additional response data
```

## Rate Limiting

The connector uses a token bucket algorithm to enforce rate limits:

- Tokens are added at a configurable rate (default: 10/second)
- Each API request consumes one token
- Requests wait if insufficient tokens are available
- Prevents API throttling and ensures smooth operation

## Reconnection Strategy

When connection is lost:

1. Detect connection failure
2. Wait 1 second, attempt reconnection
3. If failed, wait 2 seconds, attempt reconnection
4. If failed, wait 4 seconds, attempt reconnection
5. Continue doubling delay up to maximum (default: 60 seconds)
6. Keep attempting until successful or manually stopped

## Error Handling

The connector handles various error scenarios:

- **Connection errors**: Automatic reconnection with backoff
- **Authentication errors**: Logged and raised (requires manual intervention)
- **Rate limiting**: Automatic request queuing
- **API errors**: Logged and callbacks notified
- **Invalid data**: Logged and skipped
- **Order failures**: Returned in OrderResult with error details

## Requirements Validation

This implementation satisfies the following requirements:

- **Requirement 3.1**: ✓ Authenticated connection to Bybit API
- **Requirement 3.2**: ✓ Reconnection with exponential backoff
- **Requirement 3.3**: ✓ Market data parsing and validation
- **Requirement 3.4**: ✓ API rate limiting
- **Requirement 3.5**: ✓ API error handling and notification
- **Requirement 4.1**: ✓ Market data subscription

## Testing

Unit tests are available in `tests/unit/test_exchange_connector.py`:

```bash
pytest tests/unit/test_exchange_connector.py -v
```

## Dependencies

- `pybit`: Bybit API wrapper
- `structlog`: Structured logging
- `asyncio`: Asynchronous operations

## Notes

- Always use testnet for development and testing
- Never commit API credentials to version control
- Use environment variables for API keys
- Monitor rate limits to avoid throttling
- Handle errors gracefully in production
- Test thoroughly before using with real funds
