# Logging System

Comprehensive logging system for the Trading Bot using structlog with JSON formatting and automatic log rotation.

## Features

- **Structured Logging**: Uses structlog for structured, machine-readable logs
- **JSON Format**: Logs in JSON format for easy parsing and analysis
- **Automatic Rotation**: Rotates log files when size limit is exceeded
- **Timestamp & Severity**: All logs include ISO 8601 timestamps and severity levels
- **Stack Traces**: Errors are logged with full stack traces and context
- **Specialized Loggers**: Dedicated functions for orders, fills, errors, and system events

## Setup

```python
from src.logging import setup_logging

# Initialize logging system
logger = setup_logging(
    log_dir="logs",              # Directory for log files
    log_level="INFO",            # Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    max_bytes=10*1024*1024,      # Max file size before rotation (10 MB)
    backup_count=5,              # Number of backup files to keep
    json_format=True             # Use JSON formatting
)
```

## Usage

### Log Orders

```python
from src.logging import log_order

log_order(
    order_id="ORD-001",
    symbol="BTCUSDT",
    side="BUY",
    quantity=0.1,
    price=50000.0,
    strategy_id="momentum-strategy-1",
    order_type="LIMIT"
)
```

### Log Fills

```python
from src.logging import log_fill

log_fill(
    order_id="ORD-001",
    symbol="BTCUSDT",
    side="BUY",
    quantity=0.1,
    price=49950.0,
    strategy_id="momentum-strategy-1",
    fill_type="FULL"
)
```

### Log Errors

```python
from src.logging import log_error

# Simple error
log_error(
    "api_error",
    "Failed to connect to exchange",
    exchange="Bybit",
    retry_count=3
)

# Error with exception
try:
    # Some operation
    pass
except Exception as e:
    log_error(
        "strategy_error",
        "Strategy execution failed",
        exc_info=e,
        strategy_id="my-strategy"
    )
```

### Log System Events

```python
from src.logging import log_system_event

log_system_event(
    "system_start",
    "Trading Bot System starting",
    version="1.0.0",
    environment="production"
)
```

## Log Rotation

The system automatically rotates logs when the file size exceeds the configured limit. You can also monitor and manually trigger rotation:

```python
from src.logging import LogRotationMonitor

monitor = LogRotationMonitor(
    log_file="logs/trading_bot.log",
    max_bytes=10*1024*1024,
    backup_count=5
)

# Check rotation status
info = monitor.get_rotation_info()
print(f"Current size: {info['current_size']} bytes")
print(f"Should rotate: {info['should_rotate']}")

# Manually trigger rotation
if monitor.should_rotate():
    monitor.rotate_logs()

# Cleanup old logs beyond backup count
removed = monitor.cleanup_old_logs()
```

## Configuration via Environment Variables

```bash
export LOG_DIR="logs"
export LOG_LEVEL="INFO"
export MAX_LOG_SIZE="10485760"  # 10 MB
export LOG_BACKUP_COUNT="5"
```

## Log Format

Logs are written in JSON format with the following structure:

```json
{
  "event": "order_placed",
  "level": "info",
  "timestamp": "2026-03-08T12:00:00.000000Z",
  "order_id": "ORD-001",
  "symbol": "BTCUSDT",
  "side": "BUY",
  "quantity": 0.1,
  "price": 50000.0,
  "strategy_id": "momentum-strategy-1",
  "order_type": "LIMIT"
}
```

## Requirements Satisfied

- **9.1**: Logs all significant actions with timestamps and severity levels
- **9.2**: Logs errors with stack traces and context information
- **9.3**: Logs order placements and fills with complete details
- **9.4**: Logs system start/stop events with configuration
- **9.5**: Implements log rotation when size limit is exceeded
