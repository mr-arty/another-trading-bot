# Trading Strategy YAML Schema Documentation

This document describes the YAML schema for defining trading strategies in the Trading Bot System.

## Overview

Strategy files are YAML documents that define trading rules, indicators, entry/exit conditions, and risk parameters. The bot loads these files from the configured strategies directory and executes them concurrently.

## Top-Level Fields

### Required Fields

#### `name` (string)
Unique identifier for the strategy.

```yaml
name: "momentum_breakout_strategy"
```

#### `symbol` (string)
Trading pair symbol (e.g., "BTCUSDT", "ETHUSDT").

```yaml
symbol: "BTCUSDT"
```

#### `position_direction` (string, optional)
Position direction for the strategy: "long" or "short". Defaults to "long" if not specified.

- **"long"**: Entry conditions generate buy signals, exit conditions generate sell signals (profit from price increases)
- **"short"**: Entry conditions generate sell signals, exit conditions generate buy signals (profit from price decreases)

```yaml
position_direction: "long"  # Default - buy on entry, sell on exit
```

```yaml
position_direction: "short"  # Short positions - sell on entry, buy on exit
```

**Important**: The entry and exit conditions remain the same regardless of position direction. The system automatically inverts the buy/sell signals based on this setting.

### Optional Fields

#### `strategy_type` (string)
Strategy classification for organizational purposes. Special value "test" enables test mode.

```yaml
strategy_type: "momentum"  # or "mean_reversion", "range_trading", etc.
```

**Test Mode**: When `strategy_type: "test"`, the strategy operates in test mode:
- Connects to exchange API and receives market data
- Calculates all specified indicators
- Logs data reception and indicator values
- Does NOT generate trading signals
- Does NOT place any orders
- Does NOT require entry/exit conditions or position sizes

Test mode is perfect for:
- Verifying API connectivity
- Testing market data flow
- Debugging indicator calculations
- Validating system setup

```yaml
strategy_type: "test"  # Enable test mode
```

#### `timeframes` (list of strings)
Timeframes used for analysis. Valid values: "1m", "5m", "15m", "30m", "1h", "4h", "1d".

```yaml
timeframes:
  - "5m"
  - "15m"
  - "1h"
```

## Indicators Section


The `indicators` section defines technical indicators used by the strategy.

### Indicator Structure

Each indicator has a unique key and configuration:

```yaml
indicators:
  indicator_name:
    type: "indicator_type"
    timeframe: "15m"
    period: 14
    # Additional parameters specific to indicator type
```

### Common Indicator Types

#### RSI (Relative Strength Index)
```yaml
rsi_15m:
  type: "rsi"
  timeframe: "15m"
  period: 14
  oversold: 30
  overbought: 70
  description: "RSI momentum indicator"
```

#### EMA (Exponential Moving Average)
```yaml
ema_fast:
  type: "ema"
  timeframe: "15m"
  period: 9
  description: "Fast EMA for trend"
```

#### SMA (Simple Moving Average)
```yaml
sma_20:
  type: "sma"
  timeframe: "15m"
  period: 20
  description: "20-period simple moving average"
```

#### Bollinger Bands
```yaml
bb_upper:
  type: "bollinger_upper"
  timeframe: "15m"
  period: 20
  std_dev: 2.0
  description: "Upper Bollinger Band"

bb_middle:
  type: "sma"
  timeframe: "15m"
  period: 20
  description: "Bollinger Band middle (SMA)"

bb_lower:
  type: "bollinger_lower"
  timeframe: "15m"
  period: 20
  std_dev: 2.0
  description: "Lower Bollinger Band"
```

#### Volume Indicators
```yaml
volume_avg:
  type: "volume_sma"
  timeframe: "15m"
  period: 20
  description: "Average volume"
```

#### Swing High/Low (Support/Resistance)
```yaml
swing_high:
  type: "swing_high"
  timeframe: "1h"
  lookback: 20
  pivot_bars: 3
  description: "Recent swing high for resistance"

swing_low:
  type: "swing_low"
  timeframe: "1h"
  lookback: 20
  pivot_bars: 3
  description: "Recent swing low for support"
```

#### Point of Control (Volume Profile)
```yaml
poc:
  type: "poc"
  timeframe: "1h"
  lookback: 48
  description: "Point of Control from volume profile"
```

## Entry Conditions Section

Entry conditions define when to enter a trade. All conditions must be true unless using `entry_conditions_long` and `entry_conditions_short` for separate long/short logic.

### Simple Entry Conditions (All Required)

```yaml
entry_conditions:
  - type: "cross_above"
    indicator1: "ema_fast"
    indicator2: "ema_slow"
    description: "Fast EMA crosses above slow EMA"

  - type: "greater_than"
    indicator: "rsi"
    value: 50
    description: "RSI above 50"
```

### Separate Long/Short Entry Conditions

```yaml
entry_conditions_long:
  description: "Long entry conditions"
  all_required:
    - type: "less_than"
      indicator: "rsi"
      value: 30
      description: "RSI oversold"

entry_conditions_short:
  description: "Short entry conditions"
  all_required:
    - type: "greater_than"
      indicator: "rsi"
      value: 70
      description: "RSI overbought"
```

### Entry Condition Types

#### Comparison Conditions

**`greater_than`** - Indicator value greater than threshold
```yaml
- type: "greater_than"
  indicator: "rsi"
  value: 50
```

**`less_than`** - Indicator value less than threshold
```yaml
- type: "less_than"
  indicator: "rsi"
  value: 30
```

**`cross_above`** - Indicator1 crosses above indicator2
```yaml
- type: "cross_above"
  indicator1: "ema_fast"
  indicator2: "ema_slow"
```

**`cross_below`** - Indicator1 crosses below indicator2
```yaml
- type: "cross_below"
  indicator1: "ema_fast"
  indicator2: "ema_slow"
```

#### Price Conditions

**`price_above`** - Price above indicator
```yaml
- type: "price_above"
  indicator: "ema_200"
```

**`price_below`** - Price below indicator
```yaml
- type: "price_below"
  indicator: "ema_200"
```

**`price_in_zone`** - Price within zone around level
```yaml
- type: "price_in_zone"
  zone: "support"
  distance_percent: 0.2
```

#### Volume Conditions

**`volume_above_average`** - Volume above average by multiplier
```yaml
- type: "volume_above_average"
  multiplier: 1.2
  indicator: "volume_avg"
```

## Exit Conditions Section

Exit conditions define when to close a position. ANY condition can trigger an exit.

```yaml
exit_conditions:
  - type: "take_profit"
    percent: 4.0
    description: "Take profit at 4% gain"

  - type: "stop_loss"
    percent: 1.0
    description: "Stop loss at 1% loss"

  - type: "time_exceeds"
    seconds: 3600
    description: "Exit after 1 hour"
```

### Exit Condition Types

#### Profit/Loss Exits

**`take_profit`** - Exit at profit percentage
```yaml
- type: "take_profit"
  percent: 4.0
```

**`stop_loss`** - Exit at loss percentage
```yaml
- type: "stop_loss"
  percent: 1.0
```

**`dynamic_stop_loss`** - Stop loss relative to entry level
```yaml
- type: "dynamic_stop_loss"
  reference: "entry_sr_level"
  offset_percent: 0.5
```

#### Time-Based Exits

**`time_exceeds`** - Exit after time duration
```yaml
- type: "time_exceeds"
  seconds: 3600  # 1 hour
```

**`end_of_day`** - Exit at specific UTC time
```yaml
- type: "end_of_day"
  time_utc: "00:00"
```

#### Indicator-Based Exits

**`cross_below`** - Exit when indicator crosses below
```yaml
- type: "cross_below"
  indicator1: "ema_fast"
  indicator2: "ema_slow"
```

**`rsi_neutral`** - Exit when RSI returns to neutral zone
```yaml
- type: "rsi_neutral"
  indicator: "rsi"
  lower_bound: 45
  upper_bound: 55
```

#### Price Level Exits

**`support_resistance`** - Exit at support/resistance level
```yaml
- type: "support_resistance"
  price: 45000.0
  direction: "below"  # Exit if price goes below
```

**`mid_range_take_profit`** - Exit at mid-range (for range strategies)
```yaml
- type: "mid_range_take_profit"
  calculation: "(support + resistance) / 2"
  use_poc_if_available: true
  indicator: "poc"
```

## Position Sizing and Risk Management

```yaml
position_size: 0.01  # Position size per trade
max_position_size: 0.05  # Maximum total position size

risk_parameters:
  max_trades_per_day: 5
  cooldown_after_loss: 3600  # Seconds to wait after loss
  max_daily_loss_percent: 3.0
  max_risk_per_trade_percent: 1.0
  min_time_between_trades: 300  # Optional: minimum seconds between trades
```

### Risk Parameters

- **`max_trades_per_day`** (integer): Maximum number of trades allowed per day
- **`cooldown_after_loss`** (integer): Seconds to wait after a losing trade before next trade
- **`max_daily_loss_percent`** (float): Maximum daily loss as percentage of capital
- **`max_risk_per_trade_percent`** (float): Maximum risk per trade as percentage of capital
- **`min_time_between_trades`** (integer, optional): Minimum seconds between consecutive trades

## Advanced Features

### State Machine (for Range Trading)

State machines track market conditions and assign probability levels.

```yaml
state_machine:
  enabled: true
  initial_state: "NEUTRAL"

  states:
    NEUTRAL:
      probability: 0
      description: "No active setup"

    AT_LEVEL:
      probability_range: [40, 70]
      description: "Price at support/resistance"
      trigger:
        distance_from_sr_percent: 0.2

  transitions:
    - from: "NEUTRAL"
      to: "AT_LEVEL"
      when: "price_approaches_level"
```

### Support/Resistance Configuration

```yaml
support_resistance:
  support:
    source: "swing_low_1h"
    description: "Support from swing low"

  resistance:
    source: "swing_high_1h"
    description: "Resistance from swing high"

  zone_width_percent: 0.3
  min_range_width_percent: 1.0
  max_range_width_percent: 5.0
```

### Reference Line (Trend Filter)

```yaml
reference_line:
  indicator: "ema_200_4h"
  timeframe: "4h"

  trend_bias:
    bullish: "price > ema_200_4h"
    bearish: "price < ema_200_4h"
    neutral_zone_percent: 0.5
```

### Volume Profile

```yaml
volume_profile:
  enabled: true
  timeframe: "1h"
  lookback_periods: 48

  poc:
    description: "Point of Control"
    use_as: "take_profit_target"
    fallback: "mid_range"
```

## Metadata Section

Optional metadata for documentation and versioning.

```yaml
metadata:
  version: "1.0.0"
  description: |
    Multi-line description of the strategy.
    
    Can include:
    - Strategy rationale
    - Entry/exit logic summary
    - Risk management approach
    - Expected market conditions
```

## Complete Example: Simple Momentum Strategy

```yaml
name: "simple_momentum"
symbol: "BTCUSDT"
strategy_type: "momentum"
position_direction: "long"  # Long position strategy

timeframes:
  - "15m"

indicators:
  rsi:
    type: "rsi"
    timeframe: "15m"
    period: 14
  
  ema_fast:
    type: "ema"
    timeframe: "15m"
    period: 9
  
  ema_slow:
    type: "ema"
    timeframe: "15m"
    period: 21

entry_conditions:
  - type: "cross_above"
    indicator1: "ema_fast"
    indicator2: "ema_slow"
  
  - type: "greater_than"
    indicator: "rsi"
    value: 50

exit_conditions:
  - type: "take_profit"
    percent: 3.0
  
  - type: "stop_loss"
    percent: 1.0
  
  - type: "time_exceeds"
    seconds: 3600

position_size: 0.01
max_position_size: 0.05

risk_parameters:
  max_trades_per_day: 5
  cooldown_after_loss: 1800
  max_daily_loss_percent: 2.0
  max_risk_per_trade_percent: 1.0

metadata:
  version: "1.0.0"
  description: "Simple EMA crossover momentum strategy with RSI filter"
```

## Complete Example: Short Momentum Strategy

```yaml
name: "short_momentum"
symbol: "BTCUSDT"
strategy_type: "momentum"
position_direction: "short"  # Short position strategy

timeframes:
  - "5m"
  - "15m"

indicators:
  rsi_5m:
    type: "rsi"
    timeframe: "5m"
    period: 14
  
  ema_fast:
    type: "ema"
    timeframe: "15m"
    period: 9
  
  ema_slow:
    type: "ema"
    timeframe: "15m"
    period: 21

entry_conditions:
  # Enter short when RSI is overbought and fast EMA crosses below slow EMA
  - type: "greater_than"
    indicator: "rsi_5m"
    value: 70
  
  - type: "cross_below"
    indicator1: "ema_fast"
    indicator2: "ema_slow"

exit_conditions:
  # Exit short on take profit or stop loss
  - type: "take_profit"
    percent: 3.0
  
  - type: "stop_loss"
    percent: 1.5
  
  - type: "time_exceeds"
    seconds: 3600

position_size: 0.01
max_position_size: 0.05

risk_parameters:
  max_trades_per_day: 5
  cooldown_after_loss: 1800
  max_daily_loss_percent: 2.0
  max_risk_per_trade_percent: 1.0

metadata:
  version: "1.0.0"
  description: |
    Short momentum strategy that profits from downward price movements.
    Enters when RSI is overbought and EMAs cross bearish.
    Note: Entry/exit conditions are the same as a long strategy, but
    position_direction: "short" inverts the buy/sell signals automatically.
```

## Complete Example: Test Strategy (Data Reception Only)

```yaml
name: "test_data"
symbol: "BTCUSDT"
strategy_type: "test"  # Test mode - no trading

timeframes:
  - "15m"
  - "1h"

indicators:
  rsi_15m:
    type: "rsi"
    timeframe: "15m"
    period: 14
    oversold: 30
    overbought: 70
    description: "RSI momentum indicator"
  
  ema_fast:
    type: "ema"
    timeframe: "15m"
    period: 9
    description: "Fast EMA"
  
  ema_slow:
    type: "ema"
    timeframe: "15m"
    period: 21
    description: "Slow EMA"

# No entry_conditions, exit_conditions, or position_size required for test strategies
# The bot will:
# 1. Connect to Bybit API
# 2. Subscribe to BTCUSDT market data
# 3. Calculate RSI and EMA indicators
# 4. Log data reception with indicator values
# 5. NOT generate any trading signals
```

## Validation Rules

The Trading Bot System validates strategy files on load:

1. **Required fields**: `name` and `symbol` must be present
2. **Indicator references**: All indicators referenced in conditions must be defined
3. **Numeric values**: Percentages, periods, and thresholds must be positive numbers
4. **Timeframes**: Must be valid timeframe strings
5. **Condition types**: Must be recognized condition types
6. **Risk parameters**: Must be reasonable values (e.g., stop_loss < 100%)

## Best Practices

1. **Use descriptive names**: Make indicator and strategy names clear
2. **Add descriptions**: Document each condition for maintainability
3. **Test incrementally**: Start with simple strategies and add complexity
4. **Set appropriate risk limits**: Always define stop losses and position limits
5. **Use multiple timeframes**: Confirm signals across timeframes for better accuracy
6. **Include cooldowns**: Prevent overtrading with cooldown periods
7. **Version your strategies**: Use metadata.version to track changes
8. **Document your logic**: Use metadata.description to explain strategy rationale

## Common Patterns

### Trend Following
- Use EMA crossovers for entry
- Confirm with RSI > 50 for longs, RSI < 50 for shorts
- Exit on opposite crossover or time-based

### Mean Reversion
- Enter at Bollinger Band extremes
- Confirm with RSI oversold/overbought
- Exit at middle band or RSI neutral

### Range Trading
- Define support/resistance from swing highs/lows
- Enter at extremes with state machine
- Exit at mid-range or on breakout confirmation

### Breakout
- Wait for volume confirmation
- Enter on momentum indicators
- Use tight stops and trailing exits
