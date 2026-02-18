"""
Unit tests for Order Executor
"""
import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.execution.executor import OrderExecutor
from src.exchange.connector import (
    ExchangeConnector, OrderResult, OrderSide, 
    OrderType, OrderStatus
)
from src.position.tracker import PositionTracker, OrderFill
from src.database.db import Database


@pytest.fixture
async def database():
    """Create test database"""
    db = Database(":memory:")
    await db.initialize()
    yield db
    await db.close()


@pytest.fixture
def mock_exchange():
    """Create mock exchange connector"""
    exchange = AsyncMock(spec=ExchangeConnector)
    return exchange


@pytest.fixture
def mock_position_tracker():
    """Create mock position tracker"""
    tracker = AsyncMock(spec=PositionTracker)
    return tracker


@pytest.fixture
async def executor(mock_exchange, mock_position_tracker, database):
    """Create order executor"""
    return OrderExecutor(
        exchange=mock_exchange,
        position_tracker=mock_position_tracker,
        database=database,
        max_retries=3,
        retry_base_delay=0.1  # Short delay for tests
    )


class MockSignal:
    """Mock signal for testing"""
    def __init__(
        self,
        strategy_name: str = "test_strategy",
        symbol: str = "BTCUSDT",
        side: str = "buy",
        quantity: float = 0.01,
        price: float = None,
        timestamp: datetime = None
    ):
        self.strategy_name = strategy_name
        self.symbol = symbol
        self.side = side
        self.quantity = quantity
        self.price = price
        self.timestamp = timestamp or datetime.utcnow()


@pytest.mark.asyncio
async def test_create_order_from_signal_market_order(executor):
    """Test creating market order from signal"""
    signal = MockSignal(side="buy", price=None)
    
    order = executor._create_order_from_signal(signal)
    
    assert order.strategy_name == "test_strategy"
    assert order.symbol == "BTCUSDT"
    assert order.side == OrderSide.BUY
    assert order.order_type == OrderType.MARKET
    assert order.quantity == 0.01
    assert order.price is None


@pytest.mark.asyncio
async def test_create_order_from_signal_limit_order(executor):
    """Test creating limit order from signal"""
    signal = MockSignal(side="sell", price=50000.0)
    
    order = executor._create_order_from_signal(signal)
    
    assert order.strategy_name == "test_strategy"
    assert order.symbol == "BTCUSDT"
    assert order.side == OrderSide.SELL
    assert order.order_type == OrderType.LIMIT
    assert order.quantity == 0.01
    assert order.price == 50000.0


@pytest.mark.asyncio
async def test_execute_signal_success(executor, mock_exchange):
    """Test successful signal execution"""
    signal = MockSignal()
    
    # Mock successful order placement
    mock_exchange.place_order.return_value = OrderResult(
        success=True,
        order_id="order123",
        message="Order placed successfully"
    )
    
    order_id = await executor.execute_signal(signal)
    
    assert order_id == "order123"
    assert order_id in executor.active_orders
    assert order_id in executor.monitoring_tasks
    mock_exchange.place_order.assert_called_once()


@pytest.mark.asyncio
async def test_execute_signal_with_retry(executor, mock_exchange):
    """Test signal execution with retry on failure"""
    signal = MockSignal()
    
    # First attempt fails, second succeeds
    mock_exchange.place_order.side_effect = [
        OrderResult(success=False, order_id=None, message="Rate limit"),
        OrderResult(success=True, order_id="order123", message="Success")
    ]
    
    order_id = await executor.execute_signal(signal)
    
    assert order_id == "order123"
    assert mock_exchange.place_order.call_count == 2


@pytest.mark.asyncio
async def test_execute_signal_all_retries_fail(executor, mock_exchange):
    """Test signal execution when all retries fail"""
    signal = MockSignal()
    
    # All attempts fail
    mock_exchange.place_order.return_value = OrderResult(
        success=False,
        order_id=None,
        message="Connection error"
    )
    
    order_id = await executor.execute_signal(signal)
    
    assert order_id is None
    assert mock_exchange.place_order.call_count == 3


@pytest.mark.asyncio
async def test_handle_order_fill(executor, mock_position_tracker, database):
    """Test handling order fill"""
    from src.exchange.connector import Order
    
    order = Order(
        order_id="order123",
        strategy_name="test_strategy",
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=0.01,
        price=None,
        status=OrderStatus.PENDING,
        timestamp=datetime.utcnow()
    )
    
    # Store order first
    await executor._store_order_history("order123", order, OrderStatus.PENDING)
    
    await executor._handle_order_fill(
        order_id="order123",
        order=order,
        fill_quantity=0.01,
        fill_price=50000.0,
        fee=0.5
    )
    
    # Verify position tracker was updated
    mock_position_tracker.update_position.assert_called_once()
    
    # Verify order status was updated in database
    conn = await database.get_connection()
    async with conn.execute(
        "SELECT status, filled_quantity FROM order_history WHERE order_id = ?",
        ("order123",)
    ) as cursor:
        row = await cursor.fetchone()
    
    assert row is not None
    assert row[0] == OrderStatus.FILLED.value


@pytest.mark.asyncio
async def test_handle_partial_fill(executor, mock_position_tracker, database):
    """Test handling partial order fill"""
    from src.exchange.connector import Order
    
    order = Order(
        order_id="order123",
        strategy_name="test_strategy",
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=0.1,
        price=50000.0,
        status=OrderStatus.PENDING,
        timestamp=datetime.utcnow()
    )
    
    # Store order first
    await executor._store_order_history("order123", order, OrderStatus.PENDING)
    
    await executor._handle_partial_fill(
        order_id="order123",
        order=order,
        fill_quantity=0.05,
        fill_price=50000.0,
        remaining_quantity=0.05,
        fee=0.25
    )
    
    # Verify position tracker was updated
    mock_position_tracker.update_position.assert_called_once()
    
    # Verify order status was updated in database
    conn = await database.get_connection()
    async with conn.execute(
        "SELECT status, filled_quantity FROM order_history WHERE order_id = ?",
        ("order123",)
    ) as cursor:
        row = await cursor.fetchone()
    
    assert row is not None
    assert row[0] == OrderStatus.PARTIALLY_FILLED.value
    assert row[1] == 0.05


@pytest.mark.asyncio
async def test_strategy_notification(executor):
    """Test strategy notification on order fill"""
    callback_called = False
    callback_args = None
    
    async def mock_callback(order_id, status, fill_info):
        nonlocal callback_called, callback_args
        callback_called = True
        callback_args = (order_id, status, fill_info)
    
    executor.register_strategy_callback("test_strategy", mock_callback)
    
    from src.exchange.connector import Order
    
    order = Order(
        order_id="order123",
        strategy_name="test_strategy",
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=0.01,
        price=None,
        status=OrderStatus.PENDING,
        timestamp=datetime.utcnow()
    )
    
    fill = OrderFill(
        order_id="order123",
        symbol="BTCUSDT",
        side="buy",
        quantity=0.01,
        price=50000.0,
        fee=0.5,
        timestamp=datetime.utcnow()
    )
    
    await executor._notify_strategy(
        order_id="order123",
        order=order,
        status=OrderStatus.FILLED,
        fill_info=fill
    )
    
    assert callback_called
    assert callback_args[0] == "order123"
    assert callback_args[1] == OrderStatus.FILLED
    assert callback_args[2] == fill


@pytest.mark.asyncio
async def test_cancel_all_orders(executor, mock_exchange, database):
    """Test cancelling all orders"""
    from src.exchange.connector import Order
    
    # Add some active orders
    order1 = Order(
        order_id="order1",
        strategy_name="strategy1",
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=0.01,
        price=50000.0,
        status=OrderStatus.PENDING,
        timestamp=datetime.utcnow()
    )
    
    order2 = Order(
        order_id="order2",
        strategy_name="strategy2",
        symbol="ETHUSDT",
        side=OrderSide.SELL,
        order_type=OrderType.LIMIT,
        quantity=0.1,
        price=3000.0,
        status=OrderStatus.PENDING,
        timestamp=datetime.utcnow()
    )
    
    executor.active_orders["order1"] = (order1, None)
    executor.active_orders["order2"] = (order2, None)
    
    # Create mock tasks
    executor.monitoring_tasks["order1"] = AsyncMock()
    executor.monitoring_tasks["order2"] = AsyncMock()
    
    # Mock successful cancellation
    mock_exchange.cancel_order.return_value = True
    
    # Store orders in database first
    await executor._store_order_history("order1", order1, OrderStatus.PENDING)
    await executor._store_order_history("order2", order2, OrderStatus.PENDING)
    
    cancelled = await executor.cancel_all_orders()
    
    assert len(cancelled) == 2
    assert "order1" in cancelled
    assert "order2" in cancelled
    assert mock_exchange.cancel_order.call_count == 2


@pytest.mark.asyncio
async def test_get_order_history(executor, database):
    """Test retrieving order history"""
    from src.exchange.connector import Order
    
    # Store some orders
    order1 = Order(
        order_id="order1",
        strategy_name="strategy1",
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=0.01,
        price=None,
        status=OrderStatus.FILLED,
        timestamp=datetime.utcnow()
    )
    
    order2 = Order(
        order_id="order2",
        strategy_name="strategy2",
        symbol="ETHUSDT",
        side=OrderSide.SELL,
        order_type=OrderType.LIMIT,
        quantity=0.1,
        price=3000.0,
        status=OrderStatus.PENDING,
        timestamp=datetime.utcnow()
    )
    
    await executor._store_order_history("order1", order1, OrderStatus.FILLED)
    await executor._store_order_history("order2", order2, OrderStatus.PENDING)
    
    # Get all orders
    history = await executor.get_order_history()
    assert len(history) == 2
    
    # Filter by strategy
    history = await executor.get_order_history(strategy_name="strategy1")
    assert len(history) == 1
    assert history[0]["order_id"] == "order1"
    
    # Filter by symbol
    history = await executor.get_order_history(symbol="ETHUSDT")
    assert len(history) == 1
    assert history[0]["order_id"] == "order2"


@pytest.mark.asyncio
async def test_exponential_backoff_timing(executor, mock_exchange):
    """Test that retry delays follow exponential backoff"""
    signal = MockSignal()
    
    # All attempts fail
    mock_exchange.place_order.return_value = OrderResult(
        success=False,
        order_id=None,
        message="Error"
    )
    
    start_time = asyncio.get_event_loop().time()
    await executor.execute_signal(signal)
    end_time = asyncio.get_event_loop().time()
    
    # Expected delays: 0.1, 0.2 (total ~0.3 seconds)
    # Allow some tolerance for execution time
    elapsed = end_time - start_time
    assert elapsed >= 0.3
    assert elapsed < 0.5
