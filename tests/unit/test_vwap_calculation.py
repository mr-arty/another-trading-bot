"""Unit tests for VWAP calculation - Task 2.1."""

import pytest
from datetime import datetime, timedelta
from src.indicators.calculator import IndicatorCalculator
from src.exchange.connector import MarketData


@pytest.fixture
def calculator():
    """Create indicator calculator instance."""
    return IndicatorCalculator(cache_ttl_seconds=60)


@pytest.mark.asyncio
async def test_vwap_calculation_with_known_data():
    """Test VWAP calculation with 3 known data points."""
    calculator = IndicatorCalculator(cache_ttl_seconds=60)
    
    # Create 3 data points with known values
    # Data point 1: high=102, low=98, hl2=100, volume=1000
    # Data point 2: high=106, low=94, hl2=100, volume=2000
    # Data point 3: high=114, low=86, hl2=100, volume=3000
    
    base_time = datetime.now()
    
    data_points = [
        MarketData(
            symbol="BTCUSDT",
            timestamp=base_time,
            open=100.0,
            high=102.0,
            low=98.0,
            close=100.0,
            volume=1000.0
        ),
        MarketData(
            symbol="BTCUSDT",
            timestamp=base_time + timedelta(minutes=1),
            open=100.0,
            high=106.0,
            low=94.0,
            close=100.0,
            volume=2000.0
        ),
        MarketData(
            symbol="BTCUSDT",
            timestamp=base_time + timedelta(minutes=2),
            open=100.0,
            high=114.0,
            low=86.0,
            close=100.0,
            volume=3000.0
        ),
    ]
    
    # Add data points
    for data in data_points:
        await calculator.add_market_data(data, "1h")
    
    # Calculate VWAP
    vwap = await calculator.calculate_vwap("BTCUSDT", "1h", use_cache=False)
    
    # Expected VWAP calculation:
    # hl2_1 = (102 + 98) / 2 = 100
    # hl2_2 = (106 + 94) / 2 = 100
    # hl2_3 = (114 + 86) / 2 = 100
    # vwapsum = (100 * 1000) + (100 * 2000) + (100 * 3000) = 600000
    # volumesum = 1000 + 2000 + 3000 = 6000
    # VWAP = 600000 / 6000 = 100.0
    
    assert vwap is not None
    assert abs(vwap - 100.0) < 0.01  # Allow small floating point error


@pytest.mark.asyncio
async def test_vwap_with_varying_prices():
    """Test VWAP calculation with varying prices."""
    calculator = IndicatorCalculator(cache_ttl_seconds=60)
    
    base_time = datetime.now()
    
    # Data point 1: high=52, low=48, hl2=50, volume=100
    # Data point 2: high=62, low=58, hl2=60, volume=200
    # Data point 3: high=72, low=68, hl2=70, volume=300
    
    data_points = [
        MarketData(
            symbol="BTCUSDT",
            timestamp=base_time,
            open=50.0,
            high=52.0,
            low=48.0,
            close=50.0,
            volume=100.0
        ),
        MarketData(
            symbol="BTCUSDT",
            timestamp=base_time + timedelta(minutes=1),
            open=60.0,
            high=62.0,
            low=58.0,
            close=60.0,
            volume=200.0
        ),
        MarketData(
            symbol="BTCUSDT",
            timestamp=base_time + timedelta(minutes=2),
            open=70.0,
            high=72.0,
            low=68.0,
            close=70.0,
            volume=300.0
        ),
    ]
    
    # Add data points
    for data in data_points:
        await calculator.add_market_data(data, "1h")
    
    # Calculate VWAP
    vwap = await calculator.calculate_vwap("BTCUSDT", "1h", use_cache=False)
    
    # Expected VWAP calculation:
    # hl2_1 = 50, hl2_2 = 60, hl2_3 = 70
    # vwapsum = (50 * 100) + (60 * 200) + (70 * 300) = 5000 + 12000 + 21000 = 38000
    # volumesum = 100 + 200 + 300 = 600
    # VWAP = 38000 / 600 = 63.333...
    
    assert vwap is not None
    assert abs(vwap - 63.333333) < 0.01


@pytest.mark.asyncio
async def test_vwap_insufficient_data():
    """Test VWAP returns None with no data."""
    calculator = IndicatorCalculator(cache_ttl_seconds=60)
    
    # Try to calculate VWAP without adding any data
    vwap = await calculator.calculate_vwap("BTCUSDT", "1h", use_cache=False)
    
    assert vwap is None


@pytest.mark.asyncio
async def test_vwap_caching():
    """Test that VWAP caching works correctly."""
    calculator = IndicatorCalculator(cache_ttl_seconds=60)
    
    base_time = datetime.now()
    
    data = MarketData(
        symbol="BTCUSDT",
        timestamp=base_time,
        open=100.0,
        high=102.0,
        low=98.0,
        close=100.0,
        volume=1000.0
    )
    
    await calculator.add_market_data(data, "1h")
    
    # Calculate VWAP first time (no cache)
    vwap1 = await calculator.calculate_vwap("BTCUSDT", "1h", use_cache=False)
    
    # Calculate VWAP second time (should use cache)
    vwap2 = await calculator.calculate_vwap("BTCUSDT", "1h", use_cache=True)
    
    # Values should be identical
    assert vwap1 == vwap2
    assert vwap1 is not None


@pytest.mark.asyncio
async def test_vwap_state_persistence():
    """Test that VWAP state persists across multiple data additions."""
    calculator = IndicatorCalculator(cache_ttl_seconds=60)
    
    base_time = datetime.now()
    
    # Add first data point
    data1 = MarketData(
        symbol="BTCUSDT",
        timestamp=base_time,
        open=100.0,
        high=102.0,
        low=98.0,
        close=100.0,
        volume=1000.0
    )
    await calculator.add_market_data(data1, "1h")
    vwap1 = await calculator.calculate_vwap("BTCUSDT", "1h", use_cache=False)
    
    # Add second data point
    data2 = MarketData(
        symbol="BTCUSDT",
        timestamp=base_time + timedelta(minutes=1),
        open=100.0,
        high=106.0,
        low=94.0,
        close=100.0,
        volume=2000.0
    )
    await calculator.add_market_data(data2, "1h")
    vwap2 = await calculator.calculate_vwap("BTCUSDT", "1h", use_cache=False)
    
    # VWAP should change as cumulative sums update
    assert vwap1 is not None
    assert vwap2 is not None
    # Both should be 100 in this case since hl2 is always 100
    assert abs(vwap1 - 100.0) < 0.01
    assert abs(vwap2 - 100.0) < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
