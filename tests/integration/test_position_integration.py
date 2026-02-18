"""Integration tests for position tracker with other components."""

import pytest
from datetime import datetime
from src.position.tracker import PositionTracker, OrderFill
from src.database.db import Database
from src.risk.manager import RiskManager
from src.config.config import Config


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


@pytest.fixture
def config():
    """Create test config."""
    return Config(
        exchange_api_key="test_key",
        exchange_api_secret="test_secret",
        exchange_testnet=True,
        strategies_dir="strategies",
        max_total_exposure=10.0,
        max_position_size=5.0,
        log_level="INFO",
        log_file="test.log",
        volatility_threshold=1.0
    )


@pytest.mark.asyncio
async def test_position_tracker_with_risk_manager(tracker, config):
    """Test position tracker integration with risk manager."""
    # Create risk manager
    risk_manager = RiskManager(config)
    
    # Simulate a buy fill
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
    
    # Update position in tracker
    await tracker.update_position("BTCUSDT", buy_fill)
    
    # Update risk manager's position tracking
    await risk_manager.update_position("test_strategy", "BTCUSDT", 2.0)
    
    # Verify position exists in tracker
    position = await tracker.get_position("BTCUSDT", "test_strategy")
    assert position is not None
    assert position.quantity == 2.0
    
    # Verify risk manager has the position
    risk_position = await risk_manager.get_position("test_strategy", "BTCUSDT")
    assert risk_position == 2.0


@pytest.mark.asyncio
async def test_position_close_updates_risk_manager(tracker, config):
    """Test that closing a position can update risk manager."""
    # Create risk manager
    risk_manager = RiskManager(config)
    
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
    await risk_manager.update_position("test_strategy", "BTCUSDT", 1.0)
    
    # Close position
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
    await risk_manager.update_position("test_strategy", "BTCUSDT", 0.0)
    
    # Verify position is closed in tracker
    position = await tracker.get_position("BTCUSDT", "test_strategy")
    assert position is None
    
    # Verify risk manager shows no position
    risk_position = await risk_manager.get_position("test_strategy", "BTCUSDT")
    assert risk_position == 0.0


@pytest.mark.asyncio
async def test_multiple_strategies_position_tracking(tracker):
    """Test tracking positions for multiple strategies."""
    # Strategy 1 opens position
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
    
    # Strategy 2 opens position on same symbol
    fill2 = OrderFill(
        order_id="2",
        symbol="BTCUSDT",
        side="Buy",
        quantity=2.0,
        price=51000.0,
        fee=10.0,
        timestamp=datetime.utcnow(),
        strategy_name="strategy2"
    )
    await tracker.update_position("BTCUSDT", fill2)
    
    # Verify both positions exist independently
    pos1 = await tracker.get_position("BTCUSDT", "strategy1")
    pos2 = await tracker.get_position("BTCUSDT", "strategy2")
    
    assert pos1 is not None
    assert pos1.quantity == 1.0
    assert pos1.entry_price == 50000.0
    
    assert pos2 is not None
    assert pos2.quantity == 2.0
    assert pos2.entry_price == 51000.0
    
    # Verify total positions
    all_positions = await tracker.get_all_positions()
    assert len(all_positions) == 2
