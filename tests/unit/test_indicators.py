"""Unit tests for technical indicators."""

import pytest
from datetime import datetime, timedelta
from src.indicators.calculator import IndicatorCalculator, IndicatorValue
from src.exchange.connector import MarketData


@pytest.fixture
def calculator():
    """Create indicator calculator instance."""
    return IndicatorCalculator(cache_ttl_seconds=60)


@pytest.fixture
def sample_market_data():
    """Create sample market data for testing."""
    # Generate 50 data points with realistic price movements
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
    
    return data_points


@pytest.mark.asyncio
async def test_rsi_calculation_with_sufficient_data(calculator, sample_market_data):
    """Test RSI calculation with sufficient historical data."""
    # Add market data
    for data in sample_market_data:
        await calculator.add_market_data(data, "1h")
    
    # Calculate RSI with period 14
    rsi = await calculator.calculate_rsi("BTCUSDT", "1h", period=14, use_cache=False)
    
    assert rsi is not None
    assert 0 <= rsi <= 100
    assert isinstance(rsi, float)


@pytest.mark.asyncio
async def test_rsi_insufficient_data(calculator):
    """Test RSI returns None with insufficient data."""
    # Add only 10 data points (need 15 for period 14)
    for i in range(10):
        data = MarketData(
            symbol="BTCUSDT",
            timestamp=datetime.now() - timedelta(minutes=10-i),
            open=50000.0,
            high=50100.0,
            low=49900.0,
            close=50000.0 + i,
            volume=1000.0
        )
        await calculator.add_market_data(data, "1h")
    
    rsi = await calculator.calculate_rsi("BTCUSDT", "1h", period=14, use_cache=False)
    
    assert rsi is None


@pytest.mark.asyncio
async def test_ema_calculation_with_sufficient_data(calculator, sample_market_data):
    """Test EMA calculation with sufficient historical data."""
    # Add market data
    for data in sample_market_data:
        await calculator.add_market_data(data, "1h")
    
    # Calculate EMA with period 9
    ema = await calculator.calculate_ema("BTCUSDT", "1h", period=9, use_cache=False)
    
    assert ema is not None
    assert ema > 0
    assert isinstance(ema, float)


@pytest.mark.asyncio
async def test_ema_insufficient_data(calculator):
    """Test EMA returns None with insufficient data."""
    # Add only 5 data points (need 9 for period 9)
    for i in range(5):
        data = MarketData(
            symbol="BTCUSDT",
            timestamp=datetime.now() - timedelta(minutes=5-i),
            open=50000.0,
            high=50100.0,
            low=49900.0,
            close=50000.0 + i,
            volume=1000.0
        )
        await calculator.add_market_data(data, "1h")
    
    ema = await calculator.calculate_ema("BTCUSDT", "1h", period=9, use_cache=False)
    
    assert ema is None


@pytest.mark.asyncio
async def test_caching_works(calculator, sample_market_data):
    """Test that caching works correctly."""
    # Add market data
    for data in sample_market_data:
        await calculator.add_market_data(data, "1h")
    
    # Calculate RSI first time (no cache)
    rsi1 = await calculator.calculate_rsi("BTCUSDT", "1h", period=14, use_cache=False)
    
    # Calculate RSI second time (should use cache)
    rsi2 = await calculator.calculate_rsi("BTCUSDT", "1h", period=14, use_cache=True)
    
    # Values should be identical
    assert rsi1 == rsi2


@pytest.mark.asyncio
async def test_cache_expiration(calculator, sample_market_data):
    """Test that cache expires after TTL."""
    # Create calculator with very short TTL
    short_ttl_calculator = IndicatorCalculator(cache_ttl_seconds=1)
    
    # Add market data
    for data in sample_market_data:
        await short_ttl_calculator.add_market_data(data, "1h")
    
    # Calculate RSI
    rsi1 = await short_ttl_calculator.calculate_rsi("BTCUSDT", "1h", period=14, use_cache=False)
    
    # Wait for cache to expire
    import asyncio
    await asyncio.sleep(1.5)
    
    # Try to get cached value (should be None/recalculated)
    cached = await short_ttl_calculator._get_cached_value("BTCUSDT", "rsi", "1h", 14)
    
    assert cached is None


@pytest.mark.asyncio
async def test_multiple_timeframes(calculator, sample_market_data):
    """Test that different timeframes are handled separately."""
    # Add data for different timeframes
    for data in sample_market_data:
        await calculator.add_market_data(data, "1h")
        await calculator.add_market_data(data, "4h")
    
    # Calculate indicators for different timeframes
    rsi_1h = await calculator.calculate_rsi("BTCUSDT", "1h", period=14, use_cache=False)
    rsi_4h = await calculator.calculate_rsi("BTCUSDT", "4h", period=14, use_cache=False)
    
    assert rsi_1h is not None
    assert rsi_4h is not None
    # They should be the same since we added the same data, but stored separately
    assert rsi_1h == rsi_4h


@pytest.mark.asyncio
async def test_clear_cache(calculator, sample_market_data):
    """Test cache clearing functionality."""
    # Add market data
    for data in sample_market_data:
        await calculator.add_market_data(data, "1h")
    
    # Calculate some indicators to populate cache
    await calculator.calculate_rsi("BTCUSDT", "1h", period=14, use_cache=False)
    await calculator.calculate_ema("BTCUSDT", "1h", period=9, use_cache=False)
    
    # Get stats before clearing
    stats_before = await calculator.get_cache_statistics()
    assert stats_before["total_cached_entries"] > 0
    
    # Clear cache
    await calculator.clear_cache()
    
    # Get stats after clearing
    stats_after = await calculator.get_cache_statistics()
    assert stats_after["total_cached_entries"] == 0


@pytest.mark.asyncio
async def test_supported_timeframes(calculator):
    """Test that all required timeframes are supported."""
    supported = calculator.get_supported_timeframes()
    
    required_timeframes = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
    
    for tf in required_timeframes:
        assert tf in supported


@pytest.mark.asyncio
async def test_get_historical_data_count(calculator, sample_market_data):
    """Test getting historical data count."""
    # Initially should be 0
    count = await calculator.get_historical_data_count("BTCUSDT", "1h")
    assert count == 0
    
    # Add data
    for data in sample_market_data:
        await calculator.add_market_data(data, "1h")
    
    # Should now have data
    count = await calculator.get_historical_data_count("BTCUSDT", "1h")
    assert count == len(sample_market_data)
