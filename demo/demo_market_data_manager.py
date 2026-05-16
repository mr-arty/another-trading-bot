"""
Demo script for Market Data Manager.

This script demonstrates:
1. Creating market data subscriptions
2. Sharing data streams across multiple subscribers
3. Distributing market data to subscribers
4. Stream interruption detection and recovery
"""

import asyncio
from datetime import datetime
from src.market_data.manager import MarketDataManager
from src.exchange.connector import MarketData, ExchangeConnector
from unittest.mock import AsyncMock


async def strategy_callback_1(data: MarketData):
    """Example strategy callback 1."""
    print(f"Strategy 1 received data for {data.symbol}: Close=${data.close:.2f}")


async def strategy_callback_2(data: MarketData):
    """Example strategy callback 2."""
    print(f"Strategy 2 received data for {data.symbol}: Volume={data.volume:.2f}")


async def main():
    """Demonstrate market data manager functionality."""
    print("=" * 60)
    print("Market Data Manager Demo")
    print("=" * 60)
    
    # Create mock exchange connector
    mock_exchange = AsyncMock(spec=ExchangeConnector)
    mock_exchange.subscribe_market_data = AsyncMock()
    
    # Create market data manager
    manager = MarketDataManager(
        exchange_connector=mock_exchange,
        interruption_threshold_seconds=5
    )
    
    print("\n1. Subscribing Strategy 1 to BTCUSDT...")
    await manager.subscribe("BTCUSDT", strategy_callback_1)
    print(f"   Subscribed symbols: {manager.get_subscribed_symbols()}")
    
    print("\n2. Subscribing Strategy 2 to BTCUSDT (shared stream)...")
    await manager.subscribe("BTCUSDT", strategy_callback_2)
    
    # Get statistics
    stats = await manager.get_statistics()
    print(f"   BTCUSDT subscribers: {stats['BTCUSDT']['subscribers']}")
    print(f"   Exchange subscriptions created: {mock_exchange.subscribe_market_data.call_count}")
    
    print("\n3. Subscribing Strategy 1 to ETHUSDT...")
    await manager.subscribe("ETHUSDT", strategy_callback_1)
    print(f"   Subscribed symbols: {manager.get_subscribed_symbols()}")
    
    print("\n4. Simulating market data distribution...")
    
    # Create sample market data
    btc_data = MarketData(
        symbol="BTCUSDT",
        timestamp=datetime.now(),
        open=50000.0,
        high=51000.0,
        low=49000.0,
        close=50500.0,
        volume=1000.0
    )
    
    eth_data = MarketData(
        symbol="ETHUSDT",
        timestamp=datetime.now(),
        open=3000.0,
        high=3100.0,
        low=2900.0,
        close=3050.0,
        volume=5000.0
    )
    
    # Distribute data
    print("\n   Distributing BTCUSDT data to 2 subscribers:")
    await manager._distribute_market_data("BTCUSDT", btc_data)
    
    print("\n   Distributing ETHUSDT data to 1 subscriber:")
    await manager._distribute_market_data("ETHUSDT", eth_data)
    
    print("\n5. Checking latest data...")
    latest_btc = await manager.get_latest_data("BTCUSDT")
    latest_eth = await manager.get_latest_data("ETHUSDT")
    print(f"   Latest BTCUSDT: ${latest_btc.close:.2f}")
    print(f"   Latest ETHUSDT: ${latest_eth.close:.2f}")
    
    print("\n6. Stream interruption recovery demo...")
    print("   Simulating stream interruption for BTCUSDT...")
    
    # Get state and set old update time
    state = await manager.get_market_state("BTCUSDT")
    from datetime import timedelta
    state.last_update = datetime.now() - timedelta(seconds=10)
    
    print("   Starting stream monitoring...")
    await manager.start_monitoring()
    
    print("   Waiting for interruption detection (11 seconds)...")
    await asyncio.sleep(11)
    
    # Check if interruption was detected
    state = await manager.get_market_state("BTCUSDT")
    if state.last_interruption:
        print(f"   ✓ Interruption detected at {state.last_interruption.strftime('%H:%M:%S')}")
    
    print("\n   Triggering recovery...")
    await manager._recover_stream("BTCUSDT")
    print("   ✓ Recovery completed")
    
    print("\n   Simulating data arrival after recovery...")
    await manager._distribute_market_data("BTCUSDT", btc_data)
    
    state = await manager.get_market_state("BTCUSDT")
    if not state.last_interruption:
        print("   ✓ Interruption flag cleared")
    
    print("\n7. Final statistics:")
    stats = await manager.get_statistics()
    for symbol, stat in stats.items():
        print(f"\n   {symbol}:")
        print(f"     Subscribers: {stat['subscribers']}")
        print(f"     Has data: {stat['has_data']}")
        print(f"     Is interrupted: {stat['is_interrupted']}")
    
    print("\n8. Unsubscribing Strategy 2 from BTCUSDT...")
    await manager.unsubscribe("BTCUSDT", strategy_callback_2)
    stats = await manager.get_statistics()
    print(f"   BTCUSDT subscribers: {stats['BTCUSDT']['subscribers']}")
    
    print("\n9. Stopping monitoring...")
    await manager.stop_monitoring()
    print("   ✓ Monitoring stopped")
    
    print("\n" + "=" * 60)
    print("Demo completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
