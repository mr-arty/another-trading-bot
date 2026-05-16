"""
Demo script for Kill-Switch Handler functionality.

This script demonstrates:
1. Setting up the kill-switch handler
2. Triggering emergency shutdown
3. Order prevention during shutdown
4. Summary logging
"""

import asyncio
import logging
from datetime import datetime

from src.killswitch.handler import KillSwitchHandler
from src.execution.executor import OrderExecutor
from src.position.tracker import PositionTracker, Position, OrderFill
from src.exchange.connector import ExchangeConnector, OrderResult, OrderSide, OrderType
from src.strategy.engine import StrategyEngine
from src.database.db import Database


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockExchange:
    """Mock exchange for demo purposes."""
    
    async def close_position(self, symbol: str, side: str = "Buy") -> OrderResult:
        """Mock position closure."""
        logger.info(f"Mock: Closing position {symbol} ({side})")
        return OrderResult(
            success=True,
            order_id=f"close_{symbol}_{datetime.utcnow().timestamp()}",
            message="Position closed successfully"
        )
    
    async def get_positions(self):
        """Mock get positions."""
        return []
    
    async def disconnect(self):
        """Mock disconnect."""
        logger.info("Mock: Disconnected from exchange")


class MockOrderExecutor:
    """Mock order executor for demo purposes."""
    
    def __init__(self):
        self.active_orders = {
            "order1": ("BTCUSDT", "strategy1"),
            "order2": ("ETHUSDT", "strategy2"),
            "order3": ("SOLUSDT", "strategy1")
        }
    
    async def cancel_all_orders(self):
        """Mock cancel all orders."""
        logger.info(f"Mock: Cancelling {len(self.active_orders)} orders")
        cancelled = list(self.active_orders.keys())
        self.active_orders.clear()
        return cancelled


class MockPositionTracker:
    """Mock position tracker for demo purposes."""
    
    def __init__(self):
        self.positions = [
            Position(
                symbol="BTCUSDT",
                strategy_name="strategy1",
                quantity=0.1,
                entry_price=50000.0,
                current_price=51000.0,
                unrealized_pnl=100.0,
                side="Buy"
            ),
            Position(
                symbol="ETHUSDT",
                strategy_name="strategy2",
                quantity=1.0,
                entry_price=3000.0,
                current_price=3100.0,
                unrealized_pnl=100.0,
                side="Buy"
            )
        ]
    
    async def get_all_positions(self):
        """Mock get all positions."""
        return self.positions.copy()
    
    async def close_position(self, symbol: str, strategy_name: str, exit_price: float, exit_reason: str):
        """Mock close position."""
        logger.info(f"Mock: Closing position {symbol} for {strategy_name} at {exit_price}")
        # Calculate mock P&L
        position = next((p for p in self.positions if p.symbol == symbol), None)
        if position:
            pnl = (exit_price - position.entry_price) * position.quantity
            self.positions.remove(position)
            return pnl
        return 0.0


class MockStrategyEngine:
    """Mock strategy engine for demo purposes."""
    
    def __init__(self):
        self.strategies = {
            "strategy1": "Running",
            "strategy2": "Running"
        }
    
    def get_all_strategies(self):
        """Mock get all strategies."""
        return self.strategies.copy()
    
    async def unregister_strategy(self, strategy_name: str):
        """Mock unregister strategy."""
        logger.info(f"Mock: Stopping strategy {strategy_name}")
        if strategy_name in self.strategies:
            del self.strategies[strategy_name]


async def demo_kill_switch():
    """Demonstrate kill-switch functionality."""
    
    logger.info("=" * 80)
    logger.info("KILL-SWITCH HANDLER DEMO")
    logger.info("=" * 80)
    logger.info("")
    
    # Create mock components
    logger.info("1. Setting up mock components...")
    order_executor = MockOrderExecutor()
    position_tracker = MockPositionTracker()
    exchange = MockExchange()
    strategy_engine = MockStrategyEngine()
    
    # Create kill-switch handler
    logger.info("2. Creating kill-switch handler...")
    kill_switch = KillSwitchHandler(
        order_executor=order_executor,
        position_tracker=position_tracker,
        exchange=exchange,
        strategy_engine=strategy_engine
    )
    
    logger.info(f"   Kill-switch active: {kill_switch.is_active}")
    logger.info("")
    
    # Simulate some trading activity
    logger.info("3. Simulating active trading...")
    logger.info(f"   Active orders: {len(order_executor.active_orders)}")
    logger.info(f"   Open positions: {len(position_tracker.positions)}")
    logger.info(f"   Running strategies: {len(strategy_engine.strategies)}")
    logger.info("")
    
    # Wait a moment
    await asyncio.sleep(1)
    
    # Trigger kill-switch
    logger.info("4. TRIGGERING KILL-SWITCH...")
    logger.info("")
    
    summary = await kill_switch.trigger()
    
    logger.info("")
    logger.info("5. Kill-switch execution completed!")
    logger.info(f"   Execution time: {summary.execution_time_seconds:.2f} seconds")
    logger.info(f"   Cancelled orders: {len(summary.cancelled_orders)}")
    logger.info(f"   Closed positions: {len(summary.closed_positions)}")
    logger.info(f"   Kill-switch active: {kill_switch.is_active}")
    logger.info("")
    
    # Verify state after kill-switch
    logger.info("6. Verifying final state...")
    logger.info(f"   Active orders: {len(order_executor.active_orders)}")
    logger.info(f"   Open positions: {len(position_tracker.positions)}")
    logger.info(f"   Running strategies: {len(strategy_engine.strategies)}")
    logger.info("")
    
    # Try to trigger again (should be idempotent)
    logger.info("7. Testing idempotency (triggering again)...")
    summary2 = await kill_switch.trigger()
    logger.info(f"   Same summary returned: {summary == summary2}")
    logger.info("")
    
    # Test order blocking
    logger.info("8. Testing order prevention...")
    should_block = kill_switch.should_block_orders()
    logger.info(f"   Should block new orders: {should_block}")
    logger.info("")
    
    logger.info("=" * 80)
    logger.info("DEMO COMPLETED")
    logger.info("=" * 80)


async def demo_signal_handler():
    """Demonstrate signal handler setup."""
    
    logger.info("")
    logger.info("=" * 80)
    logger.info("SIGNAL HANDLER DEMO")
    logger.info("=" * 80)
    logger.info("")
    
    # Create minimal kill-switch
    order_executor = MockOrderExecutor()
    position_tracker = MockPositionTracker()
    exchange = MockExchange()
    
    kill_switch = KillSwitchHandler(
        order_executor=order_executor,
        position_tracker=position_tracker,
        exchange=exchange
    )
    
    # Setup signal handlers
    logger.info("Setting up signal handlers (SIGINT, SIGTERM)...")
    kill_switch.setup_signal_handler()
    logger.info("Signal handlers registered!")
    logger.info("")
    logger.info("In a real application, pressing Ctrl+C would trigger the kill-switch.")
    logger.info("For this demo, we'll skip actual signal testing.")
    logger.info("")
    logger.info("=" * 80)


if __name__ == "__main__":
    # Run demos
    asyncio.run(demo_kill_switch())
    asyncio.run(demo_signal_handler())
