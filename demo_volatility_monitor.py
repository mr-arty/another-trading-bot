"""
Demo script for VolatilityMonitor functionality.
"""
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.database.db import Database
from src.exchange.connector import MarketData
from src.monitoring.volatility import VolatilityMonitor


async def main():
    """Demonstrate VolatilityMonitor functionality."""
    
    # Initialize components
    database = Database("data/demo_volatility.db")
    await database.initialize()
    
    # Create a mock market data manager
    market_data_manager = MagicMock()
    market_data_manager.get_subscribed_symbols = MagicMock(return_value=["BTCUSDT"])
    
    # Initialize VolatilityMonitor with a threshold
    volatility_monitor = VolatilityMonitor(
        database=database,
        market_data_manager=market_data_manager,
        atr_threshold=50.0,  # Set threshold to 50 for demo
        atr_period=14
    )
    
    print("=== Volatility Monitor Demo ===\n")
    
    # Simulate market data for BTCUSDT
    symbol = "BTCUSDT"
    
    # Simulate some market data with different volatility levels
    print("1. Simulating LOW volatility market data...")
    low_vol_data = MarketData(
        symbol=symbol,
        timestamp=datetime.now(),
        price=50000.0,
        high=50020.0,
        low=49980.0,
        volume=100.0,
        bid=49995.0,
        ask=50005.0
    )
    
    # Mock the market data manager methods
    market_data_manager.get_market_state = AsyncMock(return_value=MagicMock())
    market_data_manager.get_latest_data = AsyncMock(return_value=low_vol_data)
    
    # Check threshold
    warning = await volatility_monitor.check_threshold(symbol)
    if warning:
        print(f"   {warning}")
    else:
        print(f"   ✓ {symbol} - ATR within normal range")
    
    print()
    
    # Simulate HIGH volatility
    print("2. Simulating HIGH volatility market data...")
    high_vol_data = MarketData(
        symbol=symbol,
        timestamp=datetime.now(),
        price=50000.0,
        high=50100.0,  # Large range = high volatility
        low=49900.0,
        volume=1000.0,
        bid=49995.0,
        ask=50005.0
    )
    
    market_data_manager.get_latest_data = AsyncMock(return_value=high_vol_data)
    
    warning = await volatility_monitor.check_threshold(symbol)
    if warning:
        print(f"   {warning}")
    else:
        print(f"   ✓ {symbol} - ATR within normal range")
    
    print()
    
    # Display all metrics
    print("3. Displaying all volatility metrics...")
    await volatility_monitor.display_metrics()
    
    print()
    
    # Retrieve ATR history
    print("4. Retrieving ATR history from database...")
    history = await volatility_monitor.get_atr_history(symbol, limit=10)
    
    if history:
        print(f"   Found {len(history)} ATR records:")
        for timestamp, atr_value in history:
            print(f"   - {timestamp.strftime('%Y-%m-%d %H:%M:%S')}: ATR = {atr_value:.2f}")
    else:
        print("   No ATR history found")
    
    print()
    
    # Check warning status
    print("5. Checking warning status...")
    is_active = volatility_monitor.is_warning_active(symbol)
    print(f"   Warning active for {symbol}: {is_active}")
    
    print()
    
    # Simulate volatility returning to normal
    print("6. Simulating volatility returning to normal...")
    normal_data = MarketData(
        symbol=symbol,
        timestamp=datetime.now(),
        price=50000.0,
        high=50015.0,
        low=49985.0,
        volume=100.0,
        bid=49995.0,
        ask=50005.0
    )
    
    market_data_manager.get_latest_data = AsyncMock(return_value=normal_data)
    
    warning = await volatility_monitor.check_threshold(symbol)
    if warning:
        print(f"   {warning}")
    else:
        print(f"   ✓ {symbol} - Volatility normalized (ATR below threshold)")
    
    # Display metrics again
    await volatility_monitor.display_metrics()
    
    print("\n=== Demo Complete ===")
    
    # Cleanup
    await database.close()


if __name__ == "__main__":
    asyncio.run(main())
