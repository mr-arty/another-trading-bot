# Quick Start Guide

Get the Trading Bot running in 5 minutes.

## 1. Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and set your Bybit API credentials:

```env
BYBIT_API_KEY=your_api_key_here
BYBIT_API_SECRET=your_api_secret_here
BYBIT_TESTNET=true
```

## 3. Create Directories

```bash
mkdir -p data logs strategies
```

## 4. Add a Strategy

Copy an example strategy to the strategies directory:

```bash
cp example_strategy.yaml strategies/
```

Or create your own (see `strategies/STRATEGY_SCHEMA.md` for reference).

## 5. Run the Bot

```bash
python -m src.main
```

## 6. Monitor Logs

In another terminal:

```bash
tail -f logs/trading_bot.log | jq
```

## Emergency Stop

Press `Ctrl+C` to stop gracefully, or send `SIGTERM` to trigger kill-switch:

```bash
kill -TERM $(pgrep -f "python -m src.main")
```

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Review [strategies/STRATEGY_SCHEMA.md](strategies/STRATEGY_SCHEMA.md) for strategy creation
- Check [RUNNING.md](RUNNING.md) for operational details
- Run tests: `pytest tests/`

## Common Issues

### "Configuration validation failed"
- Check `.env` file exists and has all required variables

### "ModuleNotFoundError"
- Run as module: `python -m src.main` (not `python src/main.py`)
- Ensure virtual environment is activated

### "Database error"
- Ensure `data` directory exists: `mkdir -p data`
- Check permissions: `chmod 755 data`

### "No strategies loaded"
- Ensure `strategies` directory exists
- Check YAML files are valid: `python -c "import yaml; yaml.safe_load(open('strategies/my_strategy.yaml'))"`

## Testing on Testnet

Always test on Bybit testnet first:

1. Create testnet account: https://testnet.bybit.com
2. Generate API keys in testnet account
3. Set `BYBIT_TESTNET=true` in `.env`
4. Run bot and verify behavior
5. Only switch to mainnet after thorough testing

## Support

For detailed documentation, see:
- [README.md](README.md) - Complete documentation
- [strategies/STRATEGY_SCHEMA.md](strategies/STRATEGY_SCHEMA.md) - Strategy reference
- [RUNNING.md](RUNNING.md) - Running instructions
