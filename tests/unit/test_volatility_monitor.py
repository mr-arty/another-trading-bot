"""
Unit tests for VolatilityMonitor.
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.monitoring.volatility import VolatilityMonitor
from src.database.db import Database
from src.exchange.connector import MarketData


@pytest.fixture
async def database():
    """Create test database."""
    db = Database(":memory:")
    await db.initialize()
    yield db
    await db.close()


@pytest.fixture
def mock_market_data_manager():
    """Create mock market data manager."""
    manager = MagicMock()
    manager.get_subscribed_symbols = MagicMock(return_value=["BTCUSDT"])
    manager.get_market_state = AsyncMock(return_value=MagicMock())
    return manager


@pytest.fixture
async def volatility_monitor(database, mock_market_data_manager):
    """Create VolatilityMonitor instance."""
    return VolatilityMonitor(
        database=database,
        market_data_manager=mock_market_data_manager,
        atr_threshold=100.0,
        atr_period=14
    )


@pytest.mark.asyncio
async def test_calculate_atr_with_valid_data(volatility_monitor, mock_market_data_manager):
    """Test ATR calculation with valid market data."""
    # Arrange
    market_data = MarketData(
        symbol="BTCUSDT",
        timestamp=datetime.now(),
        open=50000.0,
        high=50100.0,
        low=49900.0,
        close=50050.0,
        volume=1000.0
    )
    mock_market_data_manager.get_latest_data = AsyncMock(return_value=market_data)
    
    # Act
    atr = await volatility_monitor.calculate_atr("BTCUSDT")
    
    # Assert
    assert atr is not None
    assert atr == 200.0  # high - low


@pytest.mark.asyncio
async def test_calculate_atr_with_no_data(volatility_monitor, mock_market_data_manager):
    """Test ATR calculation when no market data is available."""
    # Arrange
    mock_market_data_manager.get_latest_data = AsyncMock(return_value=None)
    
    # Act
    atr = await volatility_monitor.calculate_atr("BTCUSDT")
    
    # Assert
    assert atr is None


@pytest.mark.asyncio
async def test_persist_atr(volatility_monitor, database):
    """Test persisting ATR value to database."""
    # Arrange
    symbol = "BTCUSDT"
    atr_value = 150.0
    
    # Act
    await volatility_monitor.persist_atr(symbol, atr_value)
    
    # Assert
    conn = await database.get_connection()
    cursor = await conn.execute(
        "SELECT symbol, atr_value FROM atr_metrics WHERE symbol = ?",
        (symbol,)
    )
    row = await cursor.fetchone()
    
    assert row is not None
    assert row[0] == symbol
    assert row[1] == atr_value


@pytest.mark.asyncio
async def test_get_atr_history(volatility_monitor, database):
    """Test retrieving ATR history from database."""
    # Arrange
    symbol = "BTCUSDT"
    await volatility_monitor.persist_atr(symbol, 100.0)
    await volatility_monitor.persist_atr(symbol, 150.0)
    await volatility_monitor.persist_atr(symbol, 200.0)
    
    # Act
    history = await volatility_monitor.get_atr_history(symbol, limit=10)
    
    # Assert
    assert len(history) == 3
    # History is returned in descending order (most recent first)
    assert history[0][1] == 200.0
    assert history[1][1] == 150.0
    assert history[2][1] == 100.0


@pytest.mark.asyncio
async def test_get_atr_history_with_limit(volatility_monitor, database):
    """Test retrieving ATR history with limit."""
    # Arrange
    symbol = "BTCUSDT"
    for i in range(10):
        await volatility_monitor.persist_atr(symbol, float(i * 10))
    
    # Act
    history = await volatility_monitor.get_atr_history(symbol, limit=5)
    
    # Assert
    assert len(history) == 5


@pytest.mark.asyncio
async def test_check_threshold_below_threshold(volatility_monitor, mock_market_data_manager):
    """Test threshold check when ATR is below threshold."""
    # Arrange
    market_data = MarketData(
        symbol="BTCUSDT",
        timestamp=datetime.now(),
        open=50000.0,
        high=50050.0,
        low=49950.0,
        close=50000.0,
        volume=100.0
    )
    mock_market_data_manager.get_latest_data = AsyncMock(return_value=market_data)
    
    # Act
    warning = await volatility_monitor.check_threshold("BTCUSDT")
    
    # Assert
    assert warning is None
    assert not volatility_monitor.is_warning_active("BTCUSDT")


@pytest.mark.asyncio
async def test_check_threshold_above_threshold(volatility_monitor, mock_market_data_manager):
    """Test threshold check when ATR exceeds threshold."""
    # Arrange
    market_data = MarketData(
        symbol="BTCUSDT",
        timestamp=datetime.now(),
        open=50000.0,
        high=50200.0,
        low=49800.0,
        close=50000.0,
        volume=1000.0
    )
    mock_market_data_manager.get_latest_data = AsyncMock(return_value=market_data)
    
    # Act
    warning = await volatility_monitor.check_threshold("BTCUSDT")
    
    # Assert
    assert warning is not None
    assert "HIGH VOLATILITY WARNING" in warning
    assert "BTCUSDT" in warning
    assert "400.00" in warning  # ATR value
    assert volatility_monitor.is_warning_active("BTCUSDT")


@pytest.mark.asyncio
async def test_check_threshold_persists_atr(volatility_monitor, mock_market_data_manager, database):
    """Test that check_threshold persists ATR values."""
    # Arrange
    market_data = MarketData(
        symbol="BTCUSDT",
        timestamp=datetime.now(),
        open=50000.0,
        high=50100.0,
        low=49900.0,
        close=50000.0,
        volume=100.0
    )
    mock_market_data_manager.get_latest_data = AsyncMock(return_value=market_data)
    
    # Act
    await volatility_monitor.check_threshold("BTCUSDT")
    
    # Assert
    history = await volatility_monitor.get_atr_history("BTCUSDT")
    assert len(history) > 0


@pytest.mark.asyncio
async def test_warning_clears_when_below_threshold(volatility_monitor, mock_market_data_manager):
    """Test that warning clears when ATR falls below threshold."""
    # Arrange - First trigger warning
    high_vol_data = MarketData(
        symbol="BTCUSDT",
        timestamp=datetime.now(),
        open=50000.0,
        high=50200.0,
        low=49800.0,
        close=50000.0,
        volume=1000.0
    )
    mock_market_data_manager.get_latest_data = AsyncMock(return_value=high_vol_data)
    
    warning = await volatility_monitor.check_threshold("BTCUSDT")
    assert warning is not None
    assert volatility_monitor.is_warning_active("BTCUSDT")
    
    # Act - Now return to normal volatility
    normal_data = MarketData(
        symbol="BTCUSDT",
        timestamp=datetime.now(),
        open=50000.0,
        high=50030.0,
        low=49970.0,
        close=50000.0,
        volume=100.0
    )
    mock_market_data_manager.get_latest_data = AsyncMock(return_value=normal_data)
    
    warning = await volatility_monitor.check_threshold("BTCUSDT")
    
    # Assert
    assert warning is None
    assert not volatility_monitor.is_warning_active("BTCUSDT")


@pytest.mark.asyncio
async def test_display_metrics(volatility_monitor, mock_market_data_manager, capsys):
    """Test displaying volatility metrics."""
    # Arrange
    market_data = MarketData(
        symbol="BTCUSDT",
        timestamp=datetime.now(),
        open=50000.0,
        high=50200.0,
        low=49800.0,
        close=50000.0,
        volume=1000.0
    )
    mock_market_data_manager.get_latest_data = AsyncMock(return_value=market_data)
    
    # Act
    await volatility_monitor.display_metrics()
    
    # Assert
    captured = capsys.readouterr()
    assert "HIGH VOLATILITY WARNING" in captured.out
    assert "BTCUSDT" in captured.out


@pytest.mark.asyncio
async def test_display_metrics_no_symbols(volatility_monitor, mock_market_data_manager):
    """Test displaying metrics when no symbols are monitored."""
    # Arrange
    mock_market_data_manager.get_subscribed_symbols = MagicMock(return_value=[])
    
    # Act & Assert - Should not raise an error
    await volatility_monitor.display_metrics()


@pytest.mark.asyncio
async def test_is_warning_active(volatility_monitor):
    """Test checking if warning is active."""
    # Arrange
    symbol = "BTCUSDT"
    
    # Act & Assert - Initially no warning
    assert not volatility_monitor.is_warning_active(symbol)
    
    # Manually set warning
    volatility_monitor._active_warnings[symbol] = True
    assert volatility_monitor.is_warning_active(symbol)
    
    # Clear warning
    volatility_monitor._active_warnings[symbol] = False
    assert not volatility_monitor.is_warning_active(symbol)
