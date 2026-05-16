"""
Demo script for Order Executor
"""
import asyncio
import logging
from datetime import datetime

from src.database.db import Database
from src.execution.executor import OrderExecutor
from src.exchange.connector import ExchangeConnector, OrderResult, OrderSide, OrderType
from src.position.tracker import PositionTracker


# Mock signal class
class MockSignal:
    def __init__(self, strategy_name, symbol, side, quantity, price=None):
        self.strategy_name = strategy_name
        self.symbol = symbol
        self.side = side
        self.quantity = quantity
        self.price = price
        self.timestamp = datetime.utcnow()


async def main():
    """Demo Order Executor functionality"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    logger.info("=== Order Executor Demo ===")
    
    # Initialize database
    db = Database(":memory:")
    await db.initialize()
    logger.info("Database initialized")
    
    # Create mock exchange connector
    class MockExchange:
        def __init__(self):
            self.order_counter = 0
        
        async def place_order(self, symbol, side, order_type, quantity, price=None):
            self.order_counter += 1
            order_id = f"ORDER_{symbol}_{self.order_counter}"
            logger.info(f"Mock exchange: Placing order {order_id}")
            return OrderResult(
                success=True,
                order_id=order_id,
                message="Order placed successfully"
            )
        
        async def cancel_order(self, symbol, order_id):
            logger.info(f"Mock exchange: Cancelling order {order_id}")
            return True
    
    exchange = MockExchange()
    
    # Create position tracker
    position_tracker = PositionTracker(database=db)
    await position_tracker.load_state()
    logger.info("Position tracker initialized")
    
    # Create order executor
    executor = OrderExecutor(
        exchange=exchange,
        position_tracker=position_tracker,
        database=db,
        max_retries=3,
        retry_base_delay=0.1
    )
    logger.info("Order executor initialized")
    
    # Test 1: Execute a buy signal
    logger.info("\n--- Test 1: Execute buy signal ---")
    buy_signal = MockSignal(
        strategy_name="test_strategy",
        symbol="BTCUSDT",
        side="buy",
        quantity=0.01,
        price=None  # Market order
    )
    
    order_id = await executor.execute_signal(buy_signal)
    logger.info(f"Buy order submitted: {order_id}")
    
    # Test 2: Execute a sell signal with limit price
    logger.info("\n--- Test 2: Execute sell signal with limit price ---")
    sell_signal = MockSignal(
        strategy_name="test_strategy",
        symbol="BTCUSDT",
        side="sell",
        quantity=0.01,
        price=50000.0  # Limit order
    )
    
    order_id2 = await executor.execute_signal(sell_signal)
    logger.info(f"Sell order submitted: {order_id2}")
    
    # Test 3: Get order history
    logger.info("\n--- Test 3: Get order history ---")
    history = await executor.get_order_history(limit=10)
    logger.info(f"Order history: {len(history)} orders")
    for order in history:
        logger.info(
            f"  - {order['order_id']}: {order['side']} {order['quantity']} "
            f"{order['symbol']} @ {order['price']} ({order['status']})"
        )
    
    # Test 4: Cancel all orders
    logger.info("\n--- Test 4: Cancel all orders ---")
    cancelled = await executor.cancel_all_orders()
    logger.info(f"Cancelled {len(cancelled)} orders: {cancelled}")
    
    # Cleanup
    await db.close()
    logger.info("\n=== Demo Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
