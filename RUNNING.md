# Running the Trading Bot

## Prerequisites

1. Python 3.12+ installed
2. Virtual environment activated
3. Dependencies installed: `pip install -r requirements.txt`
4. Environment variables configured (see Configuration below)

## Configuration

Create a `.env` file in the project root based on `.env.example`:

```bash
cp .env.example .env
```

Edit `.env` and set your Bybit API credentials:

```env
BYBIT_API_KEY=your_actual_api_key
BYBIT_API_SECRET=your_actual_api_secret
BYBIT_TESTNET=true  # Set to false for mainnet
```

## Running the Application

### Using Python Module

```bash
python -m src.main
```

### Using Virtual Environment

```bash
venv/bin/python3 -m src.main
```

## Application Startup Sequence

The application initializes components in the following order:

1. **Logging System** - Sets up structured JSON logging
2. **Configuration** - Loads settings from environment variables
3. **Database** - Initializes SQLite database for persistence
4. **Exchange Connector** - Connects to Bybit exchange API
5. **Indicator Calculator** - Initializes technical indicator calculations
6. **Market Data Manager** - Sets up market data streaming and distribution
7. **Position Tracker** - Loads existing positions from database
8. **Order Executor** - Initializes order submission and tracking
9. **Risk Manager** - Sets up risk validation for trading signals
10. **Strategy Engine** - Initializes strategy execution engine
11. **Volatility Monitor** - Sets up ATR-based volatility monitoring
12. **Kill-Switch Handler** - Initializes emergency shutdown system
13. **Strategy Loading** - Loads strategies from `./strategies` directory
14. **Strategy Registration** - Registers strategies and subscribes to market data
15. **Execution Loop** - Starts processing market data and generating signals

## Graceful Shutdown

The application handles shutdown gracefully:

- Press `Ctrl+C` to trigger shutdown
- The kill-switch can be triggered for emergency shutdown
- All components are cleaned up in reverse order:
  1. Stop market data monitoring
  2. Disconnect from exchange
  3. Close database connections

## Logs

Logs are written to `./logs/trading_bot.log` in JSON format.

View logs in real-time:

```bash
tail -f logs/trading_bot.log | jq
```

## Testing

Run all tests:

```bash
pytest tests/
```

Run integration tests only:

```bash
pytest tests/integration/
```

Run main orchestration tests:

```bash
pytest tests/integration/test_main_orchestration.py -v
```

## Troubleshooting

### Configuration Errors

If you see "Configuration validation failed", ensure:
- `.env` file exists
- `BYBIT_API_KEY` and `BYBIT_API_SECRET` are set
- `./strategies` directory exists

### Import Errors

If you see import errors, ensure:
- Virtual environment is activated
- All dependencies are installed: `pip install -r requirements.txt`
- Running as a module: `python -m src.main` (not `python src/main.py`)

### Database Errors

If you see database errors:
- Ensure `./data` directory exists (created automatically)
- Check file permissions on `./data/trading_bot.db`
- Delete database file to reset: `rm ./data/trading_bot.db`
