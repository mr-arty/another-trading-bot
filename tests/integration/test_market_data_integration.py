"""Integration tests for market data management."""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

from src.market_data.manager import MarketDataManager
from src.exchange.connector import MarketData, ExchangeConnector


@pytest.fixture
def mock_exchange():
    """Create a mock exchange connector."""
    exchange = AsyncMock(spec=ExchangeConnector)
    exchange.subscribe_market_data = AsyncMock()
    return exchange


@pytest.fixture
def market_data_manager(mock_exchange):
    """Create a market data manager."""
    return MarketDataManager(
        exchange_connector=mock_exchange,
        interruption_threshold_seconds=3
    )


@pytest.mark.asyncio
async def test_end_to_end_subscription_and_distribution(market_data_manager):
    """Test complete flow from subscription to data distribution."""
    # Track received data
    received_data = []
    
    async def callback(data: MarketData):
        received_data.append(data)
    
    # Subscribe
    await market_data_manager.subscribe("BTCUSDT", callback)
    
    # Create and distribute data
    market_data = MarketData(
        symbol="BTCUSDT",
        timestamp=datetime.now(),
        open=50000.0,
        high=51000.0,
        low=49000.0,
        close=50500.0,
        volume=1000.0
    )
    
    await market_data_manager._distribute_market_data("BTCUSDT", market_data)
    
    # Verify data was received
    assert len(received_data) == 1
    assert received_data[0] == market_data
    
    # Verify state was updated
    latest = await market_data_manager.get_latest_data("BTCUSDT")
    assert latest == market_data


@pytest.mark.asyncio
async def test_multiple_strategies_shared_stream(market_data_manager, mock_exchange):
    """Test that multiple strategies share a single data stream."""
    # Track received data for each strategy
    strategy1_data = []
    strategy2_data = []
    strategy3_data = []
    
    async def callback1(data: MarketData):
        strategy1_data.append(data)
    
    async def callback2(data: MarketData):
        strategy2_data.append(data)
    
    async def callback3(data: MarketData):
        strategy3_data.append(data)
    
    # Subscribe all strategies to same symbol
    await market_data_manager.subscribe("BTCUSDT", callback1)
    await market_data_manager.subscribe("BTCUSDT", callback2)
    await market_data_manager.subscribe("BTCUSDT", callback3)
    
    # Verify only one exchange subscription was created
    assert mock_exchange.subscribe_market_data.call_count == 1
    
    # Distribute data
    market_data = MarketData(
        symbol="BTCUSDT",
        timestamp=datetime.now(),
        open=50000.0,
        high=51000.0,
        low=49000.0,
        close=50500.0,
        volume=1000.0
    )
    
    await market_data_manager._distribute_market_data("BTCUSDT", market_data)
    
    # Verify all strategies received the data
    assert len(strategy1_data) == 1
    assert len(strategy2_data) == 1
    assert len(strategy3_data) == 1
    assert strategy1_data[0] == market_data
    assert strategy2_data[0] == market_data
    assert strategy3_data[0] == market_data


@pytest.mark.asyncio
async def test_stream_interruption_and_recovery_flow(market_data_manager, mock_exchange):
    """Test complete stream interruption detection and recovery flow."""
    # Track notifications
    notifications = []
    
    async def callback(data: MarketData):
        notifications.append(data)
    
    # Subscribe
    await market_data_manager.subscribe("BTCUSDT", callback)
    
    # Simulate old data (interruption)
    state = await market_data_manager.get_market_state("BTCUSDT")
    state.last_update = datetime.now() - timedelta(seconds=10)
    
    # Start monitoring
    await market_data_manager.start_monitoring()
    
    # Wait for interruption detection
    await asyncio.sleep(11)
    
    # Verify interruption was detected
    state = await market_data_manager.get_market_state("BTCUSDT")
    assert state.last_interruption is not None
    
    # Verify data gap notification was sent
    assert len(notifications) > 0
    gap_notification = notifications[-1]
    assert gap_notification.symbol == "BTCUSDT"
    assert gap_notification.open == 0.0  # Gap indicator
    
    # Verify resubscription occurred
    # Initial subscription + resubscription
    assert mock_exchange.subscribe_market_data.call_count >= 2
    
    # Simulate data arrival after recovery
    new_data = MarketData(
        symbol="BTCUSDT",
        timestamp=datetime.now(),
        open=51000.0,
        high=52000.0,
        low=50000.0,
        close=51500.0,
        volume=1500.0
    )
    
    await market_data_manager._distribute_market_data("BTCUSDT", new_data)
    
    # Verify interruption flag was cleared
    state = await market_data_manager.get_market_state("BTCUSDT")
    assert state.last_interruption is None
    
    # Cleanup
    await market_data_manager.stop_monitoring()


@pytest.mark.asyncio
async def test_multiple_symbols_independent_streams(market_data_manager, mock_exchange):
    """Test that different symbols have independent streams."""
    btc_data = []
    eth_data = []
    
    async def btc_callback(data: MarketData):
        btc_data.append(data)
    
    async def eth_callback(data: MarketData):
        eth_data.append(data)
    
    # Subscribe to different symbols
    await market_data_manager.subscribe("BTCUSDT", btc_callback)
    await market_data_manager.subscribe("ETHUSDT", eth_callback)
    
    # Verify separate exchange subscriptions
    assert mock_exchange.subscribe_market_data.call_count == 2
    
    # Distribute data for each symbol
    btc_market_data = MarketData(
        symbol="BTCUSDT",
        timestamp=datetime.now(),
        open=50000.0,
        high=51000.0,
        low=49000.0,
        close=50500.0,
        volume=1000.0
    )
    
    eth_market_data = MarketData(
        symbol="ETHUSDT",
        timestamp=datetime.now(),
        open=3000.0,
        high=3100.0,
        low=2900.0,
        close=3050.0,
        volume=5000.0
    )
    
    await market_data_manager._distribute_market_data("BTCUSDT", btc_market_data)
    await market_data_manager._distribute_market_data("ETHUSDT", eth_market_data)
    
    # Verify each callback only received its symbol's data
    assert len(btc_data) == 1
    assert len(eth_data) == 1
    assert btc_data[0].symbol == "BTCUSDT"
    assert eth_data[0].symbol == "ETHUSDT"


@pytest.mark.asyncio
async def test_unsubscribe_and_resubscribe(market_data_manager):
    """Test unsubscribing and resubscribing to a symbol."""
    received_data = []
    
    async def callback(data: MarketData):
        received_data.append(data)
    
    # Subscribe
    await market_data_manager.subscribe("BTCUSDT", callback)
    
    # Distribute data
    data1 = MarketData(
        symbol="BTCUSDT",
        timestamp=datetime.now(),
        open=50000.0,
        high=51000.0,
        low=49000.0,
        close=50500.0,
        volume=1000.0
    )
    await market_data_manager._distribute_market_data("BTCUSDT", data1)
    
    assert len(received_data) == 1
    
    # Unsubscribe
    await market_data_manager.unsubscribe("BTCUSDT", callback)
    
    # Distribute more data
    data2 = MarketData(
        symbol="BTCUSDT",
        timestamp=datetime.now(),
        open=51000.0,
        high=52000.0,
        low=50000.0,
        close=51500.0,
        volume=1500.0
    )
    await market_data_manager._distribute_market_data("BTCUSDT", data2)
    
    # Should not receive new data
    assert len(received_data) == 1
    
    # Resubscribe
    await market_data_manager.subscribe("BTCUSDT", callback)
    
    # Distribute more data
    data3 = MarketData(
        symbol="BTCUSDT",
        timestamp=datetime.now(),
        open=52000.0,
        high=53000.0,
        low=51000.0,
        close=52500.0,
        volume=2000.0
    )
    await market_data_manager._distribute_market_data("BTCUSDT", data3)
    
    # Should receive new data again
    assert len(received_data) == 2
    assert received_data[1] == data3
