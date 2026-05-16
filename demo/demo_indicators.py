"""Demo script to test indicator calculations."""

import asyncio
from datetime import datetime, timedelta
from src.indicators.calculator import IndicatorCalculator
from src.exchange.connector import MarketData


async def main():
    """Test indicator calculations."""
    print("Testing Technical Indicators...")
    print("=" * 60)
    
    # Create calculator
    calculator = IndicatorCalculator(cache_ttl_seconds=60)
    
    # Generate sample market data (50 data points)
    print("\n1. Generating sample market data...")
    base_price = 50000.0
    data_points = []
    
    for i in range(50):
        # Simulate price movement
        price = base_price + (i * 10) + ((-1) ** i * 50)
        
        data = MarketData(
            symbol="BTCUSDT",
            timestamp=datetime.now() - timedelta(minutes=50-i),
            open=price - 5,
            high=price + 10,
            low=price - 10,
            close=price,
            volume=1000.0 + i * 10
        )
        data_points.append(data)
    
    print(f"   Generated {len(data_points)} data points")
    print(f"   Price range: {min(d.close for d in data_points):.2f} - {max(d.close for d in data_points):.2f}")
    
    # Add data to calculator
    print("\n2. Adding market data to calculator...")
    for data in data_points:
        await calculator.add_market_data(data, "1h")
    
    count = await calculator.get_historical_data_count("BTCUSDT", "1h")
    print(f"   Historical data points stored: {count}")
    
    # Test RSI calculation
    print("\n3. Testing RSI calculation...")
    rsi = await calculator.calculate_rsi("BTCUSDT", "1h", period=14, use_cache=False)
    if rsi is not None:
        print(f"   ✓ RSI (14): {rsi:.2f}")
        if rsi < 30:
            print("     → Oversold condition")
        elif rsi > 70:
            print("     → Overbought condition")
        else:
            print("     → Neutral condition")
    else:
        print("   ✗ RSI calculation failed (insufficient data)")
    
    # Test EMA calculation
    print("\n4. Testing EMA calculation...")
    ema_9 = await calculator.calculate_ema("BTCUSDT", "1h", period=9, use_cache=False)
    ema_21 = await calculator.calculate_ema("BTCUSDT", "1h", period=21, use_cache=False)
    
    if ema_9 is not None:
        print(f"   ✓ EMA (9): {ema_9:.2f}")
    else:
        print("   ✗ EMA (9) calculation failed")
    
    if ema_21 is not None:
        print(f"   ✓ EMA (21): {ema_21:.2f}")
    else:
        print("   ✗ EMA (21) calculation failed")
    
    if ema_9 and ema_21:
        if ema_9 > ema_21:
            print("     → Bullish crossover (EMA 9 > EMA 21)")
        else:
            print("     → Bearish crossover (EMA 9 < EMA 21)")
    
    # Test caching
    print("\n5. Testing caching...")
    rsi_cached = await calculator.calculate_rsi("BTCUSDT", "1h", period=14, use_cache=True)
    if rsi_cached == rsi:
        print(f"   ✓ Cache working correctly (RSI: {rsi_cached:.2f})")
    else:
        print("   ✗ Cache not working as expected")
    
    # Test multiple timeframes
    print("\n6. Testing multiple timeframes...")
    supported = calculator.get_supported_timeframes()
    print(f"   Supported timeframes: {', '.join(supported)}")
    
    # Add data for different timeframe
    for data in data_points:
        await calculator.add_market_data(data, "4h")
    
    rsi_4h = await calculator.calculate_rsi("BTCUSDT", "4h", period=14, use_cache=False)
    if rsi_4h is not None:
        print(f"   ✓ RSI on 4h timeframe: {rsi_4h:.2f}")
    
    # Get cache statistics
    print("\n7. Cache statistics...")
    stats = await calculator.get_cache_statistics()
    print(f"   Total cached entries: {stats['total_cached_entries']}")
    print(f"   Valid entries: {stats['valid_entries']}")
    print(f"   By indicator type: {stats['by_indicator_type']}")
    
    # Test insufficient data
    print("\n8. Testing insufficient data handling...")
    rsi_insufficient = await calculator.calculate_rsi("ETHUSDT", "1h", period=14, use_cache=False)
    if rsi_insufficient is None:
        print("   ✓ Correctly returns None for insufficient data")
    else:
        print("   ✗ Should return None for insufficient data")
    
    print("\n" + "=" * 60)
    print("All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
