"""Unit tests for market data manager."""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.market_data.manager import MarketDataManager, MarketDataState
from src.exchange.connector import MarketData, ExchangeConnector


@pytest.fixture
def mock_exchange():
    """Create a mock exchange connector."""
    exchange = AsyncMock(spec=ExchangeConnector)
    exchange.subscribe_market_data = AsyncMock()
    return exchange


@pytest.fixture
def market_data_manager(mock_exchange):
    """Create a market data manager with mock exchange."""
    return MarketDataManager(
        exchange_connector=mock_exchange,
        interruption_threshold_seconds=5
    )


@pytest.fixture
def sample_market_data():
    """Create sample market data."""
    return MarketData(
        symbol="BTCUSDT",
        timestamp=datetime.now(),
        open=50000.0,
        high=51000.0,
        low=49000.0,
        close=50500.0,
        volume=1000.0
    )


@pytest.mark.asyncio
async def test_subscribe_creates_new_subscription(market_data_manager, mock_exchange):
    """Test that subscribing to a new symbol creates a new exchange subscription."""
    callback = AsyncMock()
    
    await market_data_manager.subscribe("BTCUSDT", callback)
    
    # Verify exchange subscription was created
    mock_exchange.subscribe_market_data.assert_called_once()
    call_args = mock_exchange.subscribe_market_data.call_args
    assert call_args[0][0] == ["BTCUSDT"]
    
    # Verify callback was added
    state = await market_data_manager.get_market_state("BTCUSDT")
    assert state is not None
    assert callback in state.subscribers


@pytest.mark.asyncio
async def test_subscribe_reuses_existing_subscription(market_data_manager, mock_exchange):
    """Test that subscribing to an existing symbol reuses the subscription."""
    callback1 = AsyncMock()
    callback2 = AsyncMock()
    
    # First subscription
    await market_data_manager.subscribe("BTCUSDT", callback1)
    
    # Second subscription to same symbol
    await market_data_manager.subscribe("BTCUSDT", callback2)
    
    # Verify exchange subscription was only called once
    assert mock_exchange.subscribe_market_data.call_count == 1
    
    # Verify both callbacks are registered
    state = await market_data_manager.get_market_state("BTCUSDT")
    assert callback1 in state.subscribers
    assert callback2 in state.subscribers
    assert len(state.subscribers) == 2


@pytest.mark.asyncio
async def test_unsubscribe_removes_callback(market_data_manager):
    """Test that unsubscribing removes the callback."""
    callback = AsyncMock()
    
    await market_data_manager.subscribe("BTCUSDT", callback)
    await market_data_manager.unsubscribe("BTCUSDT", callback)
    
    state = await market_data_manager.get_market_state("BTCUSDT")
    assert callback not in state.subscribers


@pytest.mark.asyncio
async def test_distribute_market_data_to_subscribers(market_data_manager, sample_market_data):
    """Test that market data is distributed to all subscribers."""
    callback1 = AsyncMock()
    callback2 = AsyncMock()
    
    await market_data_manager.subscribe("BTCUSDT", callback1)
    await market_data_manager.subscribe("BTCUSDT", callback2)
    
    # Simulate receiving market data
    await market_data_manager._distribute_market_data("BTCUSDT", sample_market_data)
    
    # Verify both callbacks received the data
    callback1.assert_called_once_with(sample_market_data)
    callback2.assert_called_once_with(sample_market_data)


@pytest.mark.asyncio
async def test_distribute_updates_state(market_data_manager, sample_market_data):
    """Test that distributing data updates the market state."""
    callback = AsyncMock()
    
    await market_data_manager.subscribe("BTCUSDT", callback)
    
    # Get initial state
    state_before = await market_data_manager.get_market_state("BTCUSDT")
    initial_update_time = state_before.last_update
    
    # Wait a bit to ensure time difference
    await asyncio.sleep(0.1)
    
    # Distribute data
    await market_data_manager._distribute_market_data("BTCUSDT", sample_market_data)
    
    # Verify state was updated
    state_after = await market_data_manager.get_market_state("BTCUSDT")
    assert state_after.data == sample_market_data
    assert state_after.last_update > initial_update_time


@pytest.mark.asyncio
async def test_get_latest_data(market_data_manager, sample_market_data):
    """Test retrieving latest market data."""
    callback = AsyncMock()
    
    await market_data_manager.subscribe("BTCUSDT", callback)
    await market_data_manager._distribute_market_data("BTCUSDT", sample_market_data)
    
    latest = await market_data_manager.get_latest_data("BTCUSDT")
    assert latest == sample_market_data


@pytest.mark.asyncio
async def test_get_latest_data_unknown_symbol(market_data_manager):
    """Test retrieving data for unknown symbol returns None."""
    latest = await market_data_manager.get_latest_data("UNKNOWN")
    assert latest is None


@pytest.mark.asyncio
async def test_get_subscribed_symbols(market_data_manager):
    """Test getting list of subscribed symbols."""
    callback = AsyncMock()
    
    await market_data_manager.subscribe("BTCUSDT", callback)
    await market_data_manager.subscribe("ETHUSDT", callback)
    
    symbols = market_data_manager.get_subscribed_symbols()
    assert "BTCUSDT" in symbols
    assert "ETHUSDT" in symbols
    assert len(symbols) == 2


@pytest.mark.asyncio
async def test_subscriber_callback_error_handling(market_data_manager, sample_market_data):
    """Test that errors in subscriber callbacks don't affect other subscribers."""
    callback1 = AsyncMock(side_effect=Exception("Callback error"))
    callback2 = AsyncMock()
    
    await market_data_manager.subscribe("BTCUSDT", callback1)
    await market_data_manager.subscribe("BTCUSDT", callback2)
    
    # Distribute data - should not raise exception
    await market_data_manager._distribute_market_data("BTCUSDT", sample_market_data)
    
    # Verify second callback still received data
    callback2.assert_called_once_with(sample_market_data)


@pytest.mark.asyncio
async def test_stream_interruption_detection(market_data_manager):
    """Test that stream interruptions are detected."""
    callback = AsyncMock()
    
    await market_data_manager.subscribe("BTCUSDT", callback)
    
    # Set last update to old time
    state = await market_data_manager.get_market_state("BTCUSDT")
    state.last_update = datetime.now() - timedelta(seconds=10)
    
    # Start monitoring
    await market_data_manager.start_monitoring()
    
    # Wait for monitoring to detect interruption
    await asyncio.sleep(11)
    
    # Check if interruption was detected
    state = await market_data_manager.get_market_state("BTCUSDT")
    assert state.last_interruption is not None
    
    await market_data_manager.stop_monitoring()


@pytest.mark.asyncio
async def test_stream_recovery_resubscribes(market_data_manager, mock_exchange):
    """Test that stream recovery resubscribes to exchange."""
    callback = AsyncMock()
    
    await market_data_manager.subscribe("BTCUSDT", callback)
    
    # Reset mock to clear initial subscription call
    mock_exchange.subscribe_market_data.reset_mock()
    
    # Trigger recovery
    await market_data_manager._recover_stream("BTCUSDT")
    
    # Verify resubscription occurred
    assert mock_exchange.subscribe_market_data.call_count >= 1


@pytest.mark.asyncio
async def test_stream_recovery_notifies_subscribers(market_data_manager):
    """Test that stream recovery notifies subscribers of data gap."""
    callback = AsyncMock()
    
    await market_data_manager.subscribe("BTCUSDT", callback)
    
    # Trigger recovery
    await market_data_manager._recover_stream("BTCUSDT")
    
    # Verify callback was called (for data gap notification)
    assert callback.called


@pytest.mark.asyncio
async def test_data_gap_notification(market_data_manager):
    """Test that data gap notifications are sent to subscribers."""
    callback = AsyncMock()
    
    await market_data_manager.subscribe("BTCUSDT", callback)
    
    # Notify data gap
    await market_data_manager._notify_data_gap("BTCUSDT", [callback])
    
    # Verify callback received notification
    callback.assert_called_once()
    
    # Verify notification has zero values (gap indicator)
    call_args = callback.call_args[0][0]
    assert isinstance(call_args, MarketData)
    assert call_args.symbol == "BTCUSDT"
    assert call_args.open == 0.0
    assert call_args.close == 0.0


@pytest.mark.asyncio
async def test_stream_recovery_clears_interruption_flag(market_data_manager, sample_market_data):
    """Test that receiving data after interruption clears the flag."""
    callback = AsyncMock()
    
    await market_data_manager.subscribe("BTCUSDT", callback)
    
    # Set interruption flag
    state = await market_data_manager.get_market_state("BTCUSDT")
    state.last_interruption = datetime.now()
    
    # Distribute new data
    await market_data_manager._distribute_market_data("BTCUSDT", sample_market_data)
    
    # Verify interruption flag was cleared
    state = await market_data_manager.get_market_state("BTCUSDT")
    assert state.last_interruption is None


@pytest.mark.asyncio
async def test_get_statistics(market_data_manager, sample_market_data):
    """Test getting subscription statistics."""
    callback1 = AsyncMock()
    callback2 = AsyncMock()
    
    await market_data_manager.subscribe("BTCUSDT", callback1)
    await market_data_manager.subscribe("BTCUSDT", callback2)
    await market_data_manager.subscribe("ETHUSDT", callback1)
    
    # Add some data
    await market_data_manager._distribute_market_data("BTCUSDT", sample_market_data)
    
    stats = await market_data_manager.get_statistics()
    
    assert "BTCUSDT" in stats
    assert "ETHUSDT" in stats
    assert stats["BTCUSDT"]["subscribers"] == 2
    assert stats["ETHUSDT"]["subscribers"] == 1
    assert stats["BTCUSDT"]["has_data"] is True
    assert stats["ETHUSDT"]["has_data"] is False


@pytest.mark.asyncio
async def test_monitoring_start_stop(market_data_manager):
    """Test starting and stopping stream monitoring."""
    await market_data_manager.start_monitoring()
    assert market_data_manager._running is True
    assert market_data_manager._monitor_task is not None
    
    await market_data_manager.stop_monitoring()
    assert market_data_manager._running is False
    assert market_data_manager._monitor_task is None


@pytest.mark.asyncio
async def test_monitoring_already_running(market_data_manager):
    """Test that starting monitoring twice doesn't create duplicate tasks."""
    await market_data_manager.start_monitoring()
    first_task = market_data_manager._monitor_task
    
    await market_data_manager.start_monitoring()
    second_task = market_data_manager._monitor_task
    
    assert first_task == second_task
    
    await market_data_manager.stop_monitoring()
