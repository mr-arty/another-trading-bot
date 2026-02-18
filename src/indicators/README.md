# Technical Indicators Module

This module provides technical indicator calculations for the trading bot system.

## Features

- **RSI (Relative Strength Index)**: Momentum oscillator measuring speed and magnitude of price changes
- **EMA (Exponential Moving Average)**: Weighted moving average giving more weight to recent prices
- **Multiple Timeframes**: Support for 1m, 5m, 15m, 30m, 1h, 4h, 1d
- **Caching**: Automatic caching of calculated values for performance
- **Async Operations**: Fully asynchronous for concurrent strategy execution

## Usage

### Basic Example

```python
from src.indicators.calculator import IndicatorCalculator
from src.exchange.connector import MarketData

# Create calculator
calculator = IndicatorCalculator(cache_ttl_seconds=60)

# Add market data
await calculator.add_market_data(market_data, timeframe="1h")

# Calculate RSI
rsi = await calculator.calculate_rsi("BTCUSDT", "1h", period=14)
if rsi is not None:
    if rsi < 30:
        print("Oversold")
    elif rsi > 70:
        print("Overbought")

# Calculate EMA
ema_fast = await calculator.calculate_ema("BTCUSDT", "1h", period=9)
ema_slow = await calculator.calculate_ema("BTCUSDT", "1h", period=21)

if ema_fast and ema_slow:
    if ema_fast > ema_slow:
        print("Bullish crossover")
```

### Caching

Indicator values are automatically cached with a configurable TTL:

```python
# First call calculates and caches
rsi1 = await calculator.calculate_rsi("BTCUSDT", "1h", period=14, use_cache=True)

# Second call uses cached value (if within TTL)
rsi2 = await calculator.calculate_rsi("BTCUSDT", "1h", period=14, use_cache=True)

# Force recalculation
rsi3 = await calculator.calculate_rsi("BTCUSDT", "1h", period=14, use_cache=False)
```

### Multiple Timeframes

```python
# Add data for different timeframes
await calculator.add_market_data(data, "1h")
await calculator.add_market_data(data, "4h")

# Calculate indicators on different timeframes
rsi_1h = await calculator.calculate_rsi("BTCUSDT", "1h", period=14)
rsi_4h = await calculator.calculate_rsi("BTCUSDT", "4h", period=14)
```

### Cache Management

```python
# Get cache statistics
stats = await calculator.get_cache_statistics()
print(f"Cached entries: {stats['total_cached_entries']}")

# Clear cache for specific symbol
await calculator.clear_cache(symbol="BTCUSDT")

# Clear all cache
await calculator.clear_cache()
```

## Supported Timeframes

- `1m` - 1 minute
- `5m` - 5 minutes
- `15m` - 15 minutes
- `30m` - 30 minutes
- `1h` - 1 hour
- `4h` - 4 hours
- `1d` - 1 day

## Technical Details

### RSI Calculation

RSI is calculated using the standard formula:

```
RSI = 100 - (100 / (1 + RS))
where RS = Average Gain / Average Loss over period
```

The implementation uses pandas EMA for smoothing gains and losses.

### EMA Calculation

EMA is calculated using pandas with the standard formula:

```
EMA = Price(t) * k + EMA(y) * (1 - k)
where k = 2 / (period + 1)
```

### Data Requirements

- **RSI**: Requires at least `period + 1` data points
- **EMA**: Requires at least `period` data points

If insufficient data is available, the calculation methods return `None`.

### Performance

- Calculations use pandas for efficient vectorized operations
- Results are cached with configurable TTL
- Historical data is stored in deques with automatic size management
- Thread-safe operations using asyncio locks

## Integration with Strategy Engine

The indicator calculator is designed to integrate with the Strategy Engine:

1. Market data manager feeds data to the calculator
2. Strategy engine queries indicators for condition evaluation
3. Cached values minimize recalculation overhead
4. Multiple strategies can share the same calculator instance
