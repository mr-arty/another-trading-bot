# Strategy Engine Implementation

## Overview

The Strategy Engine is a core component of the Trading Bot System that executes trading strategies and generates buy/sell signals based on market conditions and configured rules.

## Implementation Summary

### Files Created/Modified

1. **src/strategy/engine.py** - Main Strategy Engine implementation
2. **src/strategy/__init__.py** - Updated to export new classes
3. **tests/unit/test_strategy_engine.py** - Comprehensive unit tests
4. **demo_strategy_engine.py** - Demo script showing usage

### Key Components

#### 1. Signal Dataclass
```python
@dataclass
class Signal:
    strategy_name: str
    symbol: str
    side: str  # 'buy' or 'sell'
    quantity: float
    price: Optional[float]
    timestamp: datetime
    reason: str
```

Represents a trading signal with all required metadata including strategy identifier and timestamp.

#### 2. StrategyState Dataclass
```python
@dataclass
class StrategyState:
    config: StrategyConfig
    is_active: bool
    last_signal: Optional[Signal]
    last_signal_time: Optional[datetime]
    entry_time: Optional[datetime]
    entry_price: Optional[float]
    has_position: bool
    error_count: int
    last_error: Optional[str]
    previous_indicators: Dict[str, float]
```

Maintains state for each running strategy including position status and error tracking.

#### 3. StrategyEngine Class

Main engine class with the following capabilities:

**Strategy Management:**
- `register_strategy(config)` - Register a new strategy
- `unregister_strategy(name)` - Remove a strategy
- `get_strategy_state(name)` - Get current state
- `get_all_strategies()` - Get all registered strategies

**Market Data Processing:**
- `process_market_data(data)` - Process market data and evaluate strategies
- Concurrent execution of multiple strategies
- State isolation per trading pair

**Condition Evaluation:**
- Entry conditions: `less_than`, `greater_than`, `cross_above`, `cross_below`
- Exit conditions: `take_profit`, `stop_loss`, `time_exceeds`, `support_resistance`, `end_of_day`

**Signal Generation:**
- Generates buy signals when all entry conditions are met
- Generates sell signals when any exit condition is met
- Routes signals to Risk Manager via callback

**Error Handling:**
- Error isolation per strategy
- Errors in one strategy don't affect others
- Error counting and logging

## Features Implemented

### ✅ Task 7.1: Signal Generation
- Created Signal dataclass with validation
- Implemented buy signal generation for entry conditions
- Implemented sell signal generation for exit conditions
- Included strategy identifier and timestamp in all signals

### ✅ Task 7.5: Signal Routing to Risk Manager
- Implemented signal callback mechanism
- Signals are passed to Risk Manager via callback function
- Async callback support for non-blocking operation

### ✅ Task 7.7: Concurrent Strategy Execution
- Uses asyncio.gather() to run strategies concurrently
- Multiple strategies process market data in parallel
- No blocking between strategies

### ✅ Task 7.9: State Isolation per Trading Pair
- Separate state maintained for each (strategy, symbol) pair
- Operations on one pair don't affect others
- Isolated indicator storage per pair

### ✅ Task 7.11: Strategy Error Isolation
- Try-catch blocks wrap strategy execution
- Errors logged without stopping other strategies
- Error count and last error tracked per strategy

## Condition Evaluation Logic

### Entry Conditions

1. **less_than**: `indicator < value`
2. **greater_than**: `indicator > value`
3. **cross_above**: `indicator1` crosses above `indicator2`
   - Previous: ind1 <= ind2
   - Current: ind1 > ind2
4. **cross_below**: `indicator1` crosses below `indicator2`
   - Previous: ind1 >= ind2
   - Current: ind1 < ind2

All entry conditions must be met to generate a buy signal.

### Exit Conditions

1. **take_profit**: Profit percentage >= threshold
2. **stop_loss**: Loss percentage >= threshold
3. **time_exceeds**: Time since entry >= seconds
4. **support_resistance**: Price crosses support/resistance level
5. **end_of_day**: Current time >= configured UTC time

Any exit condition can trigger a sell signal.

## Architecture Highlights

### Concurrent Execution
```python
# Process strategies concurrently
tasks = [
    self._process_strategy(name, state, data)
    for name, state in strategies_to_process
]
await asyncio.gather(*tasks, return_exceptions=True)
```

### State Isolation
```python
# Separate state per (strategy, symbol) pair
self._pair_states: Dict[tuple, Dict[str, Any]] = {}
pair_key = (strategy_name, symbol)
self._pair_states[pair_key] = {
    'last_update': None,
    'market_data': None,
    'indicators': {}
}
```

### Error Isolation
```python
try:
    # Process strategy
    await self._process_strategy(name, state, data)
except Exception as e:
    # Error isolation: log but don't stop others
    state.error_count += 1
    state.last_error = str(e)
    logger.error(...)
```

## Testing

Comprehensive unit tests cover:
- Strategy registration/unregistration
- Buy signal generation
- Sell signal generation
- No signals when conditions unmet
- Concurrent strategy execution
- State isolation per trading pair
- Strategy error isolation
- Position state updates
- Signal metadata completeness

All tests use async/await and mock dependencies appropriately.

## Usage Example

```python
from src.strategy.engine import StrategyEngine, Signal
from src.indicators.calculator import IndicatorCalculator

# Create indicator calculator
indicator_calc = IndicatorCalculator()

# Create signal handler
async def handle_signal(signal: Signal):
    print(f"Signal: {signal.side} {signal.quantity} {signal.symbol}")
    # Pass to Risk Manager...

# Create engine
engine = StrategyEngine(indicator_calc, signal_callback=handle_signal)

# Register strategy
await engine.register_strategy(strategy_config)

# Process market data
await engine.process_market_data(market_data)

# Update position state after order fills
await engine.update_position_state("strategy_name", True, 50000.0)
```

## Integration Points

### Inputs
- **StrategyConfig**: From Strategy Loader
- **MarketData**: From Market Data Manager
- **IndicatorCalculator**: For technical indicators

### Outputs
- **Signal**: To Risk Manager via callback
- **StrategyState**: For monitoring and position tracking

## Requirements Validated

- ✅ **Requirement 2.1**: Concurrent strategy execution
- ✅ **Requirement 2.2**: Non-blocking signal processing
- ✅ **Requirement 2.3**: State isolation per trading pair
- ✅ **Requirement 2.5**: Strategy error isolation
- ✅ **Requirement 5.1**: Buy signal generation
- ✅ **Requirement 5.2**: Sell signal generation
- ✅ **Requirement 5.3**: Signal routing to Risk Manager
- ✅ **Requirement 5.4**: No signals when conditions unmet
- ✅ **Requirement 5.5**: Signal metadata completeness

## Next Steps

The Strategy Engine is now complete and ready for integration with:
1. Risk Manager (Task 8) - To validate signals
2. Order Executor (Task 10) - To execute validated signals
3. Position Tracker (Task 9) - To update position state after fills

Run `python demo_strategy_engine.py` to see the Strategy Engine in action!
