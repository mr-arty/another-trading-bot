"""Unit tests for position tracker."""

import pytest
from datetime import datetime
from src.position.tracker import Position, OrderFill, PositionTracker
from src.database.db import Database


@pytest.fixture
async def database():
    """Create test database."""
    db = Database(":memory:")
    await db.initialize()
    yield db
    await db.close()


@pytest.fixture
async def tracker(database):
    """Create position tracker."""
    tracker = PositionTracker(database)
    return tracker


@pytest.mark.asyncio
async def test_position_creation():
    """Test Position dataclass creation."""
    position = Position(
        symbol="BTCUSDT",
        strategy_name="test_strategy",
        quantity=1.0,
        entry_price=50000.0
    )
    
    assert position.symbol == "BTCUSDT"
    assert position.strategy_name == "test_strategy"
    assert position.quantity == 1.0
    assert position.entry_price == 50000.0
    assert position.status == "open"
    assert position.realized_pnl == 0.0


@pytest.mark.asyncio
async def test_order_fill_creation():
    """Test OrderFill dataclass creation."""
    fill = OrderFill(
        order_id="12345",
        symbol="BTCUSDT",
        side="Buy",
        quantity=1.0,
        price=50000.0,
        fee=10.0,
        timestamp=datetime.utcnow(),
        strategy_name="test_strategy"
    )
    
    assert fill.order_id == "12345"
    assert fill.symbol == "BTCUSDT"
    assert fill.side == "Buy"
    assert fill.quantity == 1.0
    assert fill.price == 50000.0


@pytest.mark.asyncio
async def test_buy_fill_new_position(tracker):
    """Test handling buy fill for new position."""
    fill = OrderFill(
        order_id="1",
        symbol="BTCUSDT",
        side="Buy",
        quantity=1.0,
        price=50000.0,
        fee=10.0,
        timestamp=datetime.utcnow(),
        strategy_name="test_strategy"
    )
    
    await tracker.update_position("BTCUSDT", fill)
    
    position = await tracker.get_position("BTCUSDT", "test_strategy")
    assert position is not None
    assert position.quantity == 1.0
    assert position.entry_price == 50000.0
    assert position.status == "open"


@pytest.mark.asyncio
async def test_buy_fill_existing_position(tracker):
    """Test handling buy fill for existing position - average entry price."""
    # First buy
    fill1 = OrderFill(
        order_id="1",
        symbol="BTCUSDT",
        side="Buy",
        quantity=1.0,
        price=50000.0,
        fee=10.0,
        timestamp=datetime.utcnow(),
        strategy_name="test_strategy"
    )
    await tracker.update_position("BTCUSDT", fill1)
    
    # Second buy at different price
    fill2 = OrderFill(
        order_id="2",
        symbol="BTCUSDT",
        side="Buy",
        quantity=1.0,
        price=52000.0,
        fee=10.0,
        timestamp=datetime.utcnow(),
        strategy_name="test_strategy"
    )
    await tracker.update_position("BTCUSDT", fill2)
    
    position = await tracker.get_position("BTCUSDT", "test_strategy")
    assert position is not None
    assert position.quantity == 2.0
    # Average entry price: (1*50000 + 1*52000) / 2 = 51000
    assert position.entry_price == 51000.0


@pytest.mark.asyncio
async def test_sell_fill_partial_close(tracker):
    """Test handling sell fill that partially closes position."""
    # Open position
    buy_fill = OrderFill(
        order_id="1",
        symbol="BTCUSDT",
        side="Buy",
        quantity=2.0,
        price=50000.0,
        fee=10.0,
        timestamp=datetime.utcnow(),
        strategy_name="test_strategy"
    )
    await tracker.update_position("BTCUSDT", buy_fill)
    
    # Partial sell
    sell_fill = OrderFill(
        order_id="2",
        symbol="BTCUSDT",
        side="Sell",
        quantity=1.0,
        price=52000.0,
        fee=10.0,
        timestamp=datetime.utcnow(),
        strategy_name="test_strategy"
    )
    await tracker.update_position("BTCUSDT", sell_fill)
    
    position = await tracker.get_position("BTCUSDT", "test_strategy")
    assert position is not None
    assert position.quantity == 1.0
    assert position.status == "open"
    # Realized P&L: (52000 - 50000) * 1.0 - 10 = 1990
    assert position.realized_pnl == 1990.0


@pytest.mark.asyncio
async def test_sell_fill_full_close(tracker):
    """Test handling sell fill that fully closes position."""
    # Open position
    buy_fill = OrderFill(
        order_id="1",
        symbol="BTCUSDT",
        side="Buy",
        quantity=1.0,
        price=50000.0,
        fee=10.0,
        timestamp=datetime.utcnow(),
        strategy_name="test_strategy"
    )
    await tracker.update_position("BTCUSDT", buy_fill)
    
    # Full sell
    sell_fill = OrderFill(
        order_id="2",
        symbol="BTCUSDT",
        side="Sell",
        quantity=1.0,
        price=52000.0,
        fee=10.0,
        timestamp=datetime.utcnow(),
        strategy_name="test_strategy"
    )
    await tracker.update_position("BTCUSDT", sell_fill)
    
    # Position should be removed from active positions
    position = await tracker.get_position("BTCUSDT", "test_strategy")
    assert position is None


@pytest.mark.asyncio
async def test_unrealized_pnl_calculation(tracker):
    """Test unrealized P&L calculation."""
    # Open position
    fill = OrderFill(
        order_id="1",
        symbol="BTCUSDT",
        side="Buy",
        quantity=1.0,
        price=50000.0,
        fee=10.0,
        timestamp=datetime.utcnow(),
        strategy_name="test_strategy"
    )
    await tracker.update_position("BTCUSDT", fill)
    
    # Calculate unrealized P&L at higher price
    unrealized_pnl = await tracker.calculate_unrealized_pnl(
        "BTCUSDT",
        "test_strategy",
        52000.0
    )
    
    # Unrealized P&L: (52000 - 50000) * 1.0 = 2000
    assert unrealized_pnl == 2000.0
    
    position = await tracker.get_position("BTCUSDT", "test_strategy")
    assert position.current_price == 52000.0
    assert position.unrealized_pnl == 2000.0


@pytest.mark.asyncio
async def test_close_position(tracker):
    """Test manual position close."""
    # Open position
    fill = OrderFill(
        order_id="1",
        symbol="BTCUSDT",
        side="Buy",
        quantity=1.0,
        price=50000.0,
        fee=10.0,
        timestamp=datetime.utcnow(),
        strategy_name="test_strategy"
    )
    await tracker.update_position("BTCUSDT", fill)
    
    # Close position
    realized_pnl = await tracker.close_position(
        "BTCUSDT",
        "test_strategy",
        52000.0,
        "take_profit"
    )
    
    # Realized P&L: (52000 - 50000) * 1.0 = 2000
    assert realized_pnl == 2000.0
    
    # Position should be removed
    position = await tracker.get_position("BTCUSDT", "test_strategy")
    assert position is None


@pytest.mark.asyncio
async def test_get_all_positions(tracker):
    """Test getting all positions."""
    # Create multiple positions
    fill1 = OrderFill(
        order_id="1",
        symbol="BTCUSDT",
        side="Buy",
        quantity=1.0,
        price=50000.0,
        fee=10.0,
        timestamp=datetime.utcnow(),
        strategy_name="strategy1"
    )
    await tracker.update_position("BTCUSDT", fill1)
    
    fill2 = OrderFill(
        order_id="2",
        symbol="ETHUSDT",
        side="Buy",
        quantity=10.0,
        price=3000.0,
        fee=5.0,
        timestamp=datetime.utcnow(),
        strategy_name="strategy2"
    )
    await tracker.update_position("ETHUSDT", fill2)
    
    positions = await tracker.get_all_positions()
    assert len(positions) == 2


@pytest.mark.asyncio
async def test_position_persistence(tracker):
    """Test position persistence to database."""
    # Create position
    fill = OrderFill(
        order_id="1",
        symbol="BTCUSDT",
        side="Buy",
        quantity=1.0,
        price=50000.0,
        fee=10.0,
        timestamp=datetime.utcnow(),
        strategy_name="test_strategy"
    )
    await tracker.update_position("BTCUSDT", fill)
    
    # Verify position was persisted
    conn = await tracker.database.get_connection()
    cursor = await conn.execute(
        "SELECT symbol, quantity, entry_price FROM positions WHERE status = 'open'"
    )
    row = await cursor.fetchone()
    
    assert row is not None
    assert row[0] == "BTCUSDT"
    assert row[1] == 1.0
    assert row[2] == 50000.0


@pytest.mark.asyncio
async def test_load_state(tracker):
    """Test loading position state from database."""
    # Insert position directly into database
    conn = await tracker.database.get_connection()
    await conn.execute(
        """
        INSERT INTO positions
        (symbol, quantity, entry_price, current_price, unrealized_pnl,
         realized_pnl, status, opened_at, strategy_name)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("BTCUSDT", 1.0, 50000.0, 50000.0, 0.0, 0.0, "open", datetime.utcnow().isoformat(), "test_strategy")
    )
    await conn.commit()
    
    # Load state
    await tracker.load_state()
    
    # Verify position was loaded
    position = await tracker.get_position("BTCUSDT", "test_strategy")
    assert position is not None
    assert position.quantity == 1.0
    assert position.entry_price == 50000.0


@pytest.mark.asyncio
async def test_trade_log_on_close(tracker):
    """Test that closed positions are logged to trade_log."""
    # Open and close position
    buy_fill = OrderFill(
        order_id="1",
        symbol="BTCUSDT",
        side="Buy",
        quantity=1.0,
        price=50000.0,
        fee=10.0,
        timestamp=datetime.utcnow(),
        strategy_name="test_strategy"
    )
    await tracker.update_position("BTCUSDT", buy_fill)
    
    sell_fill = OrderFill(
        order_id="2",
        symbol="BTCUSDT",
        side="Sell",
        quantity=1.0,
        price=52000.0,
        fee=10.0,
        timestamp=datetime.utcnow(),
        strategy_name="test_strategy"
    )
    await tracker.update_position("BTCUSDT", sell_fill)
    
    # Verify trade was logged
    conn = await tracker.database.get_connection()
    cursor = await conn.execute(
        "SELECT symbol, entry_price, exit_price, pnl FROM trade_log"
    )
    row = await cursor.fetchone()
    
    assert row is not None
    assert row[0] == "BTCUSDT"
    assert row[1] == 50000.0
    assert row[2] == 52000.0
    assert row[3] == 1990.0  # (52000 - 50000) * 1.0 - 10
