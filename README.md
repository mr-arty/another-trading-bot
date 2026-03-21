# Trading Bot System

A professional, production-ready cryptocurrency trading bot for Bybit exchange with support for multiple concurrent strategies, comprehensive risk management, and real-time market data processing.

## Features

- **Multi-Strategy Execution**: Run multiple trading strategies concurrently with isolated state
- **Real-Time Market Data**: WebSocket-based market data streaming with automatic reconnection
- **Technical Indicators**: Built-in support for RSI, EMA, SMA, Bollinger Bands, and more
- **Risk Management**: Position sizing, exposure limits, and daily loss protection
- **Position Tracking**: Automatic P&L calculation and position synchronization with exchange
- **Order Management**: Retry logic, partial fill handling, and order status tracking
- **Volatility Monitoring**: ATR-based volatility alerts with configurable thresholds
- **Kill-Switch**: Emergency shutdown system to close all positions and cancel orders
- **Comprehensive Logging**: Structured JSON logging with automatic rotation
- **Database Persistence**: SQLite-based storage for positions, orders, and trade history
- **Strategy Hot-Reload**: Automatic detection and reload of strategy file changes

## Table of Contents

- [Installation](#installation)
- [Configuration](#configuration)
- [Creating Strategy Files](#creating-strategy-files)
- [Running the Bot](#running-the-bot)
- [Kill-Switch Usage](#kill-switch-usage)
- [Monitoring and Logs](#monitoring-and-logs)
- [Testing](#testing)
- [Architecture](#architecture)
- [Troubleshooting](#troubleshooting)

## Installation

### Prerequisites

- Python 3.12 or higher
- pip package manager
- Bybit account with API credentials

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd trading-bot
```

### Step 2: Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Set Up Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and configure your settings (see [Configuration](#configuration) section).

### Step 5: Create Required Directories

```bash
mkdir -p data logs strategies
```

## Configuration

### Environment Variables

Edit the `.env` file to configure the bot:

#### Exchange Configuration

```env
# Bybit API credentials
BYBIT_API_KEY=your_api_key_here
BYBIT_API_SECRET=your_api_secret_here
BYBIT_TESTNET=true  # Set to false for mainnet trading
```

**Important**: 
- Use testnet for testing and development
- Never commit your API credentials to version control
- Keep your API secret secure

#### Strategy Configuration

```env
# Directory containing strategy YAML files
STRATEGIES_DIR=./strategies
```

#### Risk Management

```env
# Maximum total exposure across all strategies (in USDT)
MAX_TOTAL_EXPOSURE=10000.0

# Maximum position size per strategy (in USDT)
MAX_POSITION_SIZE=1000.0
```

#### Logging

```env
# Log level: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL=INFO

# Log file location
LOG_FILE=./logs/trading_bot.log

# Maximum log file size before rotation (in MB)
LOG_MAX_SIZE_MB=100
```

#### Volatility Monitoring

```env
# ATR threshold for volatility warnings
VOLATILITY_THRESHOLD=2.0

# Timeframe for ATR calculation
VOLATILITY_TIMEFRAME=1h
```

#### Database

```env
# SQLite database file location
DATABASE_PATH=./data/trading_bot.db
```

#### Exchange Settings

```env
# API rate limit (requests per second)
API_RATE_LIMIT_PER_SECOND=10

# Maximum reconnection delay (seconds)
RECONNECT_MAX_DELAY_SECONDS=60

# Number of retry attempts for failed orders
ORDER_RETRY_ATTEMPTS=3

# Market data timeout (milliseconds)
MARKET_DATA_TIMEOUT_MS=100
```

### Configuration Validation

The bot validates all configuration on startup and will exit with clear error messages if:
- Required environment variables are missing
- Values are out of valid ranges
- Directories don't exist or aren't accessible

## Creating Strategy Files

Strategies are defined in YAML files placed in the `strategies` directory. The bot automatically loads all `.yaml` files from this directory.

### Basic Strategy Structure

```yaml
name: "my_strategy"
symbol: "BTCUSDT"

indicators:
  # Define technical indicators here
  
entry_conditions:
  # Define when to enter trades
  
exit_conditions:
  # Define when to exit trades
  
position_size: 0.01
max_position_size: 0.05

risk_parameters:
  max_trades_per_day: 5
  cooldown_after_loss: 3600
```

### Example: Simple Momentum Strategy

```yaml
name: "simple_momentum"
symbol: "BTCUSDT"

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

# ALL entry conditions must be true
entry_conditions:
  - type: "cross_above"
    indicator1: "ema_fast"
    indicator2: "ema_slow"
    description: "Fast EMA crosses above slow EMA"
  
  - type: "greater_than"
    indicator: "rsi"
    value: 50
    description: "RSI above 50 (bullish momentum)"

# ANY exit condition can trigger
exit_conditions:
  - type: "take_profit"
    percent: 3.0
    description: "Take profit at 3% gain"
  
  - type: "stop_loss"
    percent: 1.0
    description: "Stop loss at 1% loss"
  
  - type: "time_exceeds"
    seconds: 3600
    description: "Exit after 1 hour"

position_size: 0.01
max_position_size: 0.05

risk_parameters:
  max_trades_per_day: 5
  cooldown_after_loss: 1800
  max_daily_loss_percent: 2.0
```

### Supported Indicators

| Indicator | Type | Parameters |
|-----------|------|------------|
| RSI | `rsi` | `period`, `oversold`, `overbought` |
| EMA | `ema` | `period` |
| SMA | `sma` | `period` |
| Bollinger Bands | `bollinger_upper`, `bollinger_lower` | `period`, `std_dev` |
| Volume Average | `volume_sma` | `period` |
| Swing High/Low | `swing_high`, `swing_low` | `lookback`, `pivot_bars` |

### Entry Condition Types

- `greater_than`: Indicator value > threshold
- `less_than`: Indicator value < threshold
- `cross_above`: Indicator1 crosses above Indicator2
- `cross_below`: Indicator1 crosses below Indicator2
- `price_above`: Price above indicator
- `price_below`: Price below indicator

### Exit Condition Types

- `take_profit`: Exit at profit percentage
- `stop_loss`: Exit at loss percentage
- `time_exceeds`: Exit after time duration
- `end_of_day`: Exit at specific UTC time
- `support_resistance`: Exit at price level
- `cross_below`: Exit when indicator crosses below

### Complete Schema Documentation

For complete strategy schema documentation with all available options, see:
- `strategies/STRATEGY_SCHEMA.md` - Full schema reference
- `example_strategy.yaml` - Multi-timeframe example
- `strategies/momentum_strategy.yaml` - Momentum strategy example
- `strategies/mean_reversion_strategy.yaml` - Mean reversion example

## Running the Bot

### Start the Bot

```bash
python -m src.main
```

Or using the virtual environment directly:

```bash
venv/bin/python3 -m src.main
```

### Startup Sequence

The bot initializes components in this order:

1. **Logging System** - Sets up structured JSON logging
2. **Configuration** - Loads and validates settings
3. **Database** - Initializes SQLite database
4. **Exchange Connector** - Connects to Bybit API
5. **Indicator Calculator** - Initializes technical indicators
6. **Market Data Manager** - Sets up market data streaming
7. **Position Tracker** - Loads existing positions
8. **Order Executor** - Initializes order management
9. **Risk Manager** - Sets up risk validation
10. **Strategy Engine** - Initializes strategy execution
11. **Volatility Monitor** - Sets up ATR monitoring
12. **Kill-Switch Handler** - Initializes emergency shutdown
13. **Strategy Loading** - Loads strategies from directory
14. **Strategy Registration** - Registers strategies and subscribes to data
15. **Execution Loop** - Starts processing market data

### Expected Output

```
{"event": "system_start", "message": "Starting Trading Bot System", "timestamp": "2026-03-15T10:00:00Z"}
{"event": "config_loaded", "message": "Configuration loaded successfully"}
{"event": "database_initialized", "message": "Database initialized successfully"}
{"event": "exchange_connected", "message": "Exchange connection established"}
...
{"event": "system_ready", "message": "Trading Bot System started and ready"}
```

### Graceful Shutdown

Press `Ctrl+C` to trigger graceful shutdown:

```bash
^C
{"event": "system_shutdown", "message": "Shutting down Trading Bot System"}
{"event": "shutdown_market_data", "message": "Stopping market data manager"}
{"event": "shutdown_exchange", "message": "Disconnecting from exchange"}
{"event": "shutdown_database", "message": "Closing database connection"}
{"event": "system_stopped", "message": "Trading Bot System stopped"}
```

## Kill-Switch Usage

The kill-switch is an emergency shutdown system that immediately:
1. Cancels all pending orders
2. Closes all open positions at market price
3. Blocks new orders from being placed
4. Stops all strategy execution
5. Logs final account state

### Triggering the Kill-Switch

#### Method 1: Signal Handler (Recommended)

Send `SIGTERM` signal to the process:

```bash
# Find the process ID
ps aux | grep "python -m src.main"

# Send SIGTERM signal
kill -TERM <process_id>
```

#### Method 2: Keyboard Interrupt

Press `Ctrl+C` twice rapidly (first press triggers graceful shutdown, second triggers kill-switch).

### Kill-Switch Output

```json
{"event": "killswitch_triggered", "message": "Kill-switch activated"}
{"event": "killswitch_cancelling_orders", "message": "Cancelling all pending orders"}
{"event": "killswitch_closing_positions", "message": "Closing all open positions"}
{"event": "killswitch_order_prevention", "message": "Blocking new orders"}
{"event": "killswitch_cleanup", "message": "Stopping strategy execution"}
{"event": "killswitch_summary", "positions_closed": 3, "final_balance": 10250.50}
```

### When to Use Kill-Switch

- Market conditions become extremely volatile
- Exchange API issues detected
- Unexpected bot behavior observed
- Emergency need to exit all positions
- System maintenance required

### After Kill-Switch Activation

1. Review logs to understand what triggered the need for kill-switch
2. Check exchange account to verify all positions are closed
3. Review trade history in database
4. Fix any issues before restarting the bot
5. Restart the bot when ready

## Monitoring and Logs

### Log Files

Logs are written to `./logs/trading_bot.log` in JSON format.

### View Logs in Real-Time

```bash
# View raw logs
tail -f logs/trading_bot.log

# View formatted logs (requires jq)
tail -f logs/trading_bot.log | jq
```

### Log Rotation

Logs automatically rotate when they reach the configured size:
- Default: 100 MB per file
- Keeps 5 backup files
- Old logs are compressed

### Key Log Events

| Event | Description |
|-------|-------------|
| `system_start` | Bot starting up |
| `strategy_registered` | Strategy loaded and registered |
| `signal_generated` | Trading signal created |
| `order_placed` | Order submitted to exchange |
| `order_filled` | Order execution completed |
| `position_opened` | New position created |
| `position_closed` | Position closed with P&L |
| `risk_limit_exceeded` | Signal rejected by risk manager |
| `volatility_warning` | ATR threshold exceeded |
| `killswitch_triggered` | Emergency shutdown activated |
| `system_error` | Error occurred |

### Database Queries

Query the database for trade history:

```bash
sqlite3 data/trading_bot.db
```

```sql
-- View all trades
SELECT * FROM trade_log ORDER BY closed_at DESC LIMIT 10;

-- View open positions
SELECT * FROM positions WHERE status = 'open';

-- View order history
SELECT * FROM order_history ORDER BY timestamp DESC LIMIT 20;

-- View ATR metrics
SELECT * FROM atr_metrics ORDER BY timestamp DESC LIMIT 10;
```

## Testing

### Run All Tests

```bash
pytest tests/
```

### Run Unit Tests Only

```bash
pytest tests/unit/
```

### Run Integration Tests Only

```bash
pytest tests/integration/
```

### Run Specific Test File

```bash
pytest tests/unit/test_strategy_engine.py -v
```

### Run with Coverage

```bash
pytest --cov=src tests/
```

### Test Categories

- **Unit Tests** (`tests/unit/`): Test individual components in isolation
- **Integration Tests** (`tests/integration/`): Test component interactions
- **Property Tests** (`tests/property/`): Property-based tests for correctness

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         Main Application                     │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────▼────────┐   ┌────────▼────────┐   ┌──────▼──────┐
│ Strategy Engine│   │ Market Data Mgr │   │ Kill-Switch │
└───────┬────────┘   └────────┬────────┘   └──────┬──────┘
        │                     │                     │
        │            ┌────────▼────────┐            │
        │            │ Exchange Conn.  │            │
        │            └────────┬────────┘            │
        │                     │                     │
┌───────▼────────┐   ┌────────▼────────┐   ┌──────▼──────┐
│  Risk Manager  │   │ Indicator Calc. │   │  Database   │
└───────┬────────┘   └─────────────────┘   └─────────────┘
        │
┌───────▼────────┐
│ Order Executor │
└───────┬────────┘
        │
┌───────▼────────┐
│Position Tracker│
└────────────────┘
```

### Key Components

- **Strategy Engine**: Evaluates conditions and generates signals
- **Market Data Manager**: Streams and distributes market data
- **Risk Manager**: Validates signals against risk limits
- **Order Executor**: Submits and tracks orders
- **Position Tracker**: Manages positions and calculates P&L
- **Exchange Connector**: Interfaces with Bybit API
- **Indicator Calculator**: Computes technical indicators
- **Volatility Monitor**: Tracks ATR and generates warnings
- **Kill-Switch Handler**: Emergency shutdown system
- **Database**: Persists positions, orders, and metrics

### Data Flow

1. Market data arrives via WebSocket
2. Market Data Manager distributes to strategies
3. Strategy Engine evaluates conditions
4. Signals generated and sent to Risk Manager
5. Risk Manager validates against limits
6. Approved signals sent to Order Executor
7. Orders submitted to exchange
8. Order fills update Position Tracker
9. P&L calculated and persisted to database

## Troubleshooting

### Configuration Errors

**Error**: `Configuration validation failed`

**Solution**: Ensure `.env` file exists and all required variables are set:
```bash
cat .env
```

### Import Errors

**Error**: `ModuleNotFoundError: No module named 'src'`

**Solution**: Run as a module from project root:
```bash
python -m src.main  # Correct
# NOT: python src/main.py
```

### Database Errors

**Error**: `sqlite3.OperationalError: unable to open database file`

**Solution**: Ensure data directory exists and has write permissions:
```bash
mkdir -p data
chmod 755 data
```

To reset database:
```bash
rm data/trading_bot.db
# Bot will recreate on next startup
```

### Exchange Connection Errors

**Error**: `Exchange connection failed`

**Solutions**:
1. Verify API credentials in `.env`
2. Check if using correct testnet/mainnet setting
3. Verify API key has required permissions
4. Check network connectivity

### Strategy Loading Errors

**Error**: `Failed to load strategy: <strategy_name>`

**Solutions**:
1. Validate YAML syntax:
```bash
python -c "import yaml; yaml.safe_load(open('strategies/my_strategy.yaml'))"
```
2. Check all referenced indicators are defined
3. Verify condition types are valid
4. Ensure numeric values are positive

### No Signals Generated

**Possible causes**:
1. Entry conditions not met
2. Risk limits preventing signal approval
3. Strategy not registered properly
4. Market data not flowing

**Debug steps**:
```bash
# Check logs for strategy registration
grep "strategy_registered" logs/trading_bot.log

# Check for signal generation
grep "signal_generated" logs/trading_bot.log

# Check for risk rejections
grep "risk_limit_exceeded" logs/trading_bot.log
```

### High Memory Usage

**Solutions**:
1. Reduce indicator cache TTL
2. Limit number of concurrent strategies
3. Reduce log retention
4. Clear old database records

### Performance Issues

**Solutions**:
1. Increase `MARKET_DATA_TIMEOUT_MS`
2. Reduce number of timeframes per strategy
3. Optimize indicator calculations
4. Use database indexes

## Additional Documentation

- `RUNNING.md` - Detailed running instructions
- `POSITION_TRACKER_IMPLEMENTATION.md` - Position tracking details
- `STRATEGY_ENGINE_IMPLEMENTATION.md` - Strategy engine details
- `strategies/STRATEGY_SCHEMA.md` - Complete strategy schema reference
- `range_strategy_readme.md` - Range trading strategy guide
- `src/exchange/README.md` - Exchange connector documentation
- `src/indicators/README.md` - Indicator calculator documentation
- `src/market_data/README.md` - Market data manager documentation
- `src/logging/README.md` - Logging system documentation

## Support and Contributing

For issues, questions, or contributions, please refer to the project repository.

## License

[Add your license information here]

## Disclaimer

This trading bot is provided for educational and research purposes. Trading cryptocurrencies carries significant risk. Always test thoroughly on testnet before using real funds. The authors are not responsible for any financial losses incurred through use of this software.
