# Market Data Management

This module provides market data subscription management and distribution for the Trading Bot System.

## Overview

The `MarketDataManager` implements efficient market data handling with the following features:

- **Shared Data Streams**: Multiple strategies can subscribe to the same symbol without creating duplicate exchange subscriptions
- **State Management**: Maintains current market data state with timestamps for each symbol
- **Stream Interruption Recovery**: Automatically detects and recovers from data stream interruptions
- **Data Distribution**: Efficiently distributes market data to all subscribed strategies

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  MarketDataManager                       │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────────────────────────────────────────┐  │
│  │         Market Data State Storage                 │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐ │  │
│  │  │  BTCUSDT   │  │  ETHUSDT   │  │  SOLUSDT   │ │  │
│  │  │  - Data    │  │  - Data    │  │  - Data    │ │  │
│  │  │  - Time    │  │  - Time    │  │  - Time    │ │  │
│  │  │  - Subs    │  │  - Subs    │  │  - Subs    │ │  │
│  │  └────────────┘  └────────────┘  └────────────┘ │  │
│  └──────────────────────────────────────────────────┘  │
│                                                           │
│  ┌──────────────────────────────────────────────────┐  │
│  │         Stream Interruption Monitor               │  │
│  │  - Detects data gaps                              │  │
│  │  - Triggers recovery                              │  │
│  │  - Notifies subscribers                           │  │
│  └──────────────────────────────────────────────────┘  │
│                                                           │
│  ┌──────────────────────────────────────────────────┐  │
│  │         Data Distribution Engine                  │  │
│  │  - Receives data from exchange                    │  │
│  │  - Updates state                                  │  │
│  │  - Distributes to all subscribers                 │  │
│  └──────────────────────────────────────────────────┘  │
│                                                           │
└─────────────────────────────────────────────────────────┘
         │                                    │
         ▼                                    ▼
┌──────────────────┐              ┌──────────────────┐
│ Exchange         │              │ Strategy         │
│ Connector        │              │ Callbacks        │
└──────────────────┘              └──────────────────┘
```

## Usage

### Basic Subscription

```python
from src.market_data.manager import MarketDataManager
from src.exchange.connector import ExchangeConnector, MarketData

# Create exchange connector
exchange = ExchangeConnector(api_key="...", api_secret="...")
await exchange.connect()

# Create market data manager
manager = MarketDataManager(
    exchange_connector=exchange,
    interruption_threshold_seconds=30
)

# Define callback for receiving data
async def strategy_callback(data: MarketData):
    print(f"Received {data.symbol}: ${data.close}")

# Subscribe to market data
await manager.subscribe("BTCUSDT", strategy_callback)
```

### Shared Data Streams

Multiple strategies can subscribe to the same symbol. The manager automatically shares a single exchange subscription:

```python
# Strategy 1 subscribes
await manager.subscribe("BTCUSDT", strategy1_callback)

# Strategy 2 subscribes to same symbol
# No duplicate exchange subscription is created
await manager.subscribe("BTCUSDT", strategy2_callback)

# Both strategies receive the same data
```

### Stream Interruption Recovery

The manager automatically monitors for stream interruptions and recovers:

```python
# Start monitoring
await manager.start_monitoring()

# If a stream stops sending data for longer than the threshold:
# 1. Interruption is detected
# 2. Subscribers are notified of the data gap
# 3. Stream is resubscribed to the exchange
# 4. Normal operation resumes
```

### Getting Latest Data

```python
# Get the most recent market data for a symbol
latest = await manager.get_latest_data("BTCUSDT")
if latest:
    print(f"Latest price: ${latest.close}")
```

### Statistics

```python
# Get subscription statistics
stats = await manager.get_statistics()

for symbol, stat in stats.items():
    print(f"{symbol}:")
    print(f"  Subscribers: {stat['subscribers']}")
    print(f"  Has data: {stat['has_data']}")
    print(f"  Is interrupted: {stat['is_interrupted']}")
```

## Components

### MarketDataState

Represents the state of market data for a single symbol:

- `symbol`: Trading symbol (e.g., "BTCUSDT")
- `last_update`: Timestamp of last data update
- `data`: Most recent MarketData instance
- `subscribers`: List of callback functions
- `is_subscribed`: Whether subscribed to exchange
- `last_interruption`: Timestamp of last detected interruption

### MarketDataManager

Main class for managing market data:

#### Methods

- `subscribe(symbol, callback)`: Subscribe to market data for a symbol
- `unsubscribe(symbol, callback)`: Unsubscribe from market data
- `get_latest_data(symbol)`: Get most recent data for a symbol
- `get_market_state(symbol)`: Get complete state for a symbol
- `get_subscribed_symbols()`: Get list of all subscribed symbols
- `start_monitoring()`: Start stream interruption monitoring
- `stop_monitoring()`: Stop stream interruption monitoring
- `get_statistics()`: Get subscription statistics

## Stream Interruption Recovery

The manager implements automatic recovery from stream interruptions:

### Detection

- Monitors time since last data update for each symbol
- If time exceeds `interruption_threshold_seconds`, marks as interrupted
- Logs warning with symbol and time since last update

### Recovery Process

1. **Detect Interruption**: Monitor task detects data gap
2. **Notify Subscribers**: Send data gap notification (MarketData with zero values)
3. **Resubscribe**: Create new exchange subscription
4. **Resume**: Normal data flow resumes
5. **Clear Flag**: Interruption flag cleared on first new data

### Data Gap Notification

When a stream is interrupted, subscribers receive a special notification:

```python
MarketData(
    symbol="BTCUSDT",
    timestamp=<current_time>,
    open=0.0,
    high=0.0,
    low=0.0,
    close=0.0,
    volume=0.0
)
```

Strategies can detect this by checking for zero values and handle accordingly.

## Error Handling

### Subscriber Callback Errors

If a subscriber callback raises an exception:
- Error is logged with context
- Other subscribers continue to receive data
- Stream remains active

### Exchange Subscription Errors

If exchange subscription fails:
- Error is logged
- Exception is raised to caller
- State is marked as not subscribed

### Recovery Errors

If stream recovery fails:
- Error is logged
- Recovery is retried on next monitoring cycle
- Subscribers remain registered

## Performance Considerations

### Shared Streams

- Single exchange subscription per symbol regardless of subscriber count
- Reduces API calls and bandwidth usage
- Improves scalability for multiple strategies

### Async Distribution

- Data distribution uses async/await
- Non-blocking operations
- Callbacks executed concurrently

### Lock Management

- Minimal lock contention
- State updates protected by async lock
- Distribution happens outside lock

## Testing

### Unit Tests

Located in `tests/unit/test_market_data_manager.py`:
- Subscription management
- Data distribution
- State updates
- Error handling
- Monitoring lifecycle

### Integration Tests

Located in `tests/integration/test_market_data_integration.py`:
- End-to-end subscription flow
- Multiple strategies with shared streams
- Stream interruption and recovery
- Multiple symbols with independent streams

### Demo Script

Run `demo_market_data_manager.py` to see the manager in action:

```bash
python demo_market_data_manager.py
```

## Requirements Validation

This implementation satisfies the following requirements:

- **Requirement 4.2**: Market data state storage with timestamps ✓
- **Requirement 4.3**: Shared data streams to avoid duplicate subscriptions ✓
- **Requirement 4.4**: Market data distribution within 100ms (async distribution) ✓
- **Requirement 4.5**: Stream interruption recovery with subscriber notification ✓

## Design Properties

This implementation validates the following correctness properties:

- **Property 11**: Market state updates - State is updated with timestamp on each data receipt ✓
- **Property 12**: Shared data streams - Single subscription per symbol regardless of subscriber count ✓
- **Property 13**: Stream interruption recovery - Detects interruptions, resubscribes, and notifies strategies ✓
