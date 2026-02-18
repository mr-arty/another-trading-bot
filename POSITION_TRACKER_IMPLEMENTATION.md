# Position Tracker Implementation

## Overview

Implemented a comprehensive Position Tracker system for the Trading Bot that handles position lifecycle management, P&L calculation, and database persistence.

## Components Implemented

### 1. Position Dataclass (`src/position/tracker.py`)

A comprehensive position data structure with:
- Symbol and strategy tracking
- Quantity and entry price
- Current price and P&L tracking (realized and unrealized)
- Position status (open/closed)
- Timestamps for opened_at and closed_at
- Side tracking (Buy/Sell)

### 2. OrderFill Dataclass (`src/position/tracker.py`)

Represents order execution details:
- Order ID and symbol
- Side (Buy/Sell)
- Quantity and price
- Fee tracking
- Timestamp and strategy name

### 3. PositionTracker Class (`src/position/tracker.py`)

Main position management class with the following capabilities:

#### Position Updates (Task 9.1)
- **Buy fills**: Creates new positions or adds to existing ones
- **Average entry price calculation**: Automatically calculates weighted average when adding to positions
- **Sell fills**: Reduces position quantity and calculates realized P&L
- **Thread-safe operations**: Uses asyncio locks for concurrent access

#### P&L Calculation (Task 9.3)
- **Realized P&L**: Calculated when positions are reduced or closed
  - Formula: `(exit_price - entry_price) * quantity - fees`
- **Unrealized P&L**: Calculated for open positions based on current market price
  - Formula: `(current_price - entry_price) * quantity`
- **Trade logging**: Completed trades stored in `trade_log` table with:
  - Entry/exit prices
  - P&L amount and percentage
  - Exit reason (take_profit, stop_loss, manual_close, etc.)

#### Position Persistence (Task 9.5)
- **Automatic persistence**: Position state saved to SQLite on every update
- **Load on startup**: Positions restored from database
- **CRUD operations**: Full create, read, update, delete support
- **Database schema**: Uses existing `positions` and `trade_log` tables

#### Position Synchronization (Task 9.7)
- **Exchange reconciliation**: Compares local positions with exchange state
- **Mismatch detection**: Identifies and logs discrepancies
- **Automatic correction**: Updates local state to match exchange
- **Missing position handling**: Detects positions that exist locally but not on exchange

## Key Features

### Multi-Strategy Support
- Tracks positions independently per strategy
- Same symbol can have different positions for different strategies
- Position key: `(strategy_name, symbol)`

### Position Lifecycle Management
1. **Open**: Buy fill creates new position
2. **Increase**: Additional buy fills average the entry price
3. **Decrease**: Sell fills reduce quantity and realize P&L
4. **Close**: Position fully closed and logged to trade history

### Database Integration
- Positions persisted to `positions` table
- Completed trades logged to `trade_log` table
- Automatic state recovery on restart
- Async database operations for performance

## Testing

### Unit Tests (`tests/unit/test_position_tracker.py`)
- 12 comprehensive unit tests covering:
  - Position and OrderFill creation
  - Buy fill handling (new and existing positions)
  - Sell fill handling (partial and full close)
  - Unrealized P&L calculation
  - Manual position close
  - Position persistence and loading
  - Trade log verification

### Integration Tests (`tests/integration/test_position_integration.py`)
- Integration with RiskManager
- Multi-strategy position tracking
- Position close coordination

### Demo Script (`demo_position_tracker.py`)
- Complete workflow demonstration
- Shows all major features in action
- Verifies database persistence

## Usage Example

```python
from src.position.tracker import PositionTracker, OrderFill
from src.database.db import Database

# Initialize
db = Database("data/trading_bot.db")
await db.initialize()
tracker = PositionTracker(db)

# Load existing positions
await tracker.load_state()

# Handle buy fill
buy_fill = OrderFill(
    order_id="ORDER_001",
    symbol="BTCUSDT",
    side="Buy",
    quantity=1.0,
    price=50000.0,
    fee=10.0,
    timestamp=datetime.utcnow(),
    strategy_name="momentum_strategy"
)
await tracker.update_position("BTCUSDT", buy_fill)

# Calculate unrealized P&L
unrealized_pnl = await tracker.calculate_unrealized_pnl(
    "BTCUSDT",
    "momentum_strategy",
    52000.0  # current price
)

# Close position
realized_pnl = await tracker.close_position(
    "BTCUSDT",
    "momentum_strategy",
    52000.0,
    "take_profit"
)

# Sync with exchange
exchange_positions = await exchange_connector.get_positions()
await tracker.sync_with_exchange(exchange_positions)
```

## Requirements Satisfied

- **Requirement 7.3**: Position updates on order fills
- **Requirement 8.1**: Position state storage and tracking
- **Requirement 8.2**: P&L calculation (realized and unrealized)
- **Requirement 8.3**: Position synchronization with exchange
- **Requirement 8.4**: Position persistence to database
- **Requirement 8.5**: Position query methods (within 10ms requirement)

## Test Results

All 12 unit tests pass successfully:
```
tests/unit/test_position_tracker.py::test_position_creation PASSED
tests/unit/test_position_tracker.py::test_order_fill_creation PASSED
tests/unit/test_position_tracker.py::test_buy_fill_new_position PASSED
tests/unit/test_position_tracker.py::test_buy_fill_existing_position PASSED
tests/unit/test_position_tracker.py::test_sell_fill_partial_close PASSED
tests/unit/test_position_tracker.py::test_sell_fill_full_close PASSED
tests/unit/test_position_tracker.py::test_unrealized_pnl_calculation PASSED
tests/unit/test_position_tracker.py::test_close_position PASSED
tests/unit/test_position_tracker.py::test_get_all_positions PASSED
tests/unit/test_position_tracker.py::test_position_persistence PASSED
tests/unit/test_position_tracker.py::test_load_state PASSED
tests/unit/test_position_tracker.py::test_trade_log_on_close PASSED
```

## Files Created/Modified

### Created:
- `src/position/tracker.py` - Main PositionTracker implementation
- `tests/unit/test_position_tracker.py` - Unit tests
- `tests/integration/test_position_integration.py` - Integration tests
- `demo_position_tracker.py` - Demo script
- `POSITION_TRACKER_IMPLEMENTATION.md` - This document

### Modified:
- `src/position/__init__.py` - Exports Position, OrderFill, PositionTracker
- `.kiro/specs/trading-bot/tasks.md` - Marked tasks 9, 9.1, 9.3, 9.5, 9.7 as complete

## Next Steps

The Position Tracker is now ready to be integrated with:
1. **Order Executor**: To receive order fills and update positions
2. **Risk Manager**: To provide position data for risk checks
3. **Strategy Engine**: To query position information for decision making
4. **Kill-Switch Handler**: To close all positions in emergency situations
