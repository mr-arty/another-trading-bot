"""Unit tests for Risk Manager."""

import pytest
from datetime import datetime
from src.risk.manager import RiskManager, RiskCheckResult
from src.strategy.engine import Signal
from src.config.config import Config


@pytest.fixture
def config():
    """Create test configuration."""
    return Config(
        exchange_api_key="test_key",
        exchange_api_secret="test_secret",
        exchange_testnet=True,
        strategies_dir="./strategies",
        max_total_exposure=1000.0,
        max_position_size=100.0,
        log_level="INFO",
        log_file="./logs/test.log"
    )


@pytest.fixture
def risk_manager(config):
    """Create risk manager instance."""
    return RiskManager(config=config)


@pytest.mark.asyncio
async def test_buy_signal_within_limits(risk_manager):
    """Test that buy signal within limits is approved."""
    signal = Signal(
        strategy_name="test_strategy",
        symbol="BTCUSDT",
        side="buy",
        quantity=50.0,
        price=None,
        timestamp=datetime.now(),
        reason="Test buy"
    )
    
    result = await risk_manager.validate_signal(signal)
    
    assert result.approved is True
    assert "approved" in result.reason.lower()


@pytest.mark.asyncio
async def test_buy_signal_exceeds_position_size(risk_manager):
    """Test that buy signal exceeding position size is rejected."""
    signal = Signal(
        strategy_name="test_strategy",
        symbol="BTCUSDT",
        side="buy",
        quantity=150.0,  # Exceeds max_position_size of 100
        price=None,
        timestamp=datetime.now(),
        reason="Test buy"
    )
    
    result = await risk_manager.validate_signal(signal)
    
    assert result.approved is False
    assert "position size" in result.reason.lower()


@pytest.mark.asyncio
async def test_buy_signal_exceeds_total_exposure(risk_manager):
    """Test that buy signal exceeding total exposure is rejected."""
    # Add existing positions
    await risk_manager.update_position("strategy1", "BTCUSDT", 500.0)
    await risk_manager.update_position("strategy2", "ETHUSDT", 450.0)
    
    # Try to add more that would exceed total exposure of 1000
    # Use 60 to stay within position size limit (60 < 100) but exceed total exposure (950 + 60 = 1010 > 1000)
    signal = Signal(
        strategy_name="strategy3",
        symbol="SOLUSDT",
        side="buy",
        quantity=60.0,  # Would make total 1010, exceeding 1000 limit
        price=None,
        timestamp=datetime.now(),
        reason="Test buy"
    )
    
    result = await risk_manager.validate_signal(signal)
    
    assert result.approved is False
    assert "exposure" in result.reason.lower()


@pytest.mark.asyncio
async def test_sell_signal_no_position(risk_manager):
    """Test that sell signal without position is approved (opens short position)."""
    signal = Signal(
        strategy_name="test_strategy",
        symbol="BTCUSDT",
        side="sell",
        quantity=50.0,
        price=None,
        timestamp=datetime.now(),
        reason="Test sell"
    )
    
    result = await risk_manager.validate_signal(signal)
    
    # With short position support, sell without position opens a short
    assert result.approved is True
    assert "approved" in result.reason.lower()


@pytest.mark.asyncio
async def test_sell_signal_exceeds_holding(risk_manager):
    """Test that sell signal exceeding holding is rejected."""
    # Set up position
    await risk_manager.update_position("test_strategy", "BTCUSDT", 30.0)
    
    # Try to sell more than we have
    signal = Signal(
        strategy_name="test_strategy",
        symbol="BTCUSDT",
        side="sell",
        quantity=50.0,  # More than the 30 we have
        price=None,
        timestamp=datetime.now(),
        reason="Test sell"
    )
    
    result = await risk_manager.validate_signal(signal)
    
    assert result.approved is False
    assert "exceeds" in result.reason.lower()


@pytest.mark.asyncio
async def test_sell_signal_within_holding(risk_manager):
    """Test that sell signal within holding is approved."""
    # Set up position
    await risk_manager.update_position("test_strategy", "BTCUSDT", 50.0)
    
    # Sell within holding
    signal = Signal(
        strategy_name="test_strategy",
        symbol="BTCUSDT",
        side="sell",
        quantity=30.0,
        price=None,
        timestamp=datetime.now(),
        reason="Test sell"
    )
    
    result = await risk_manager.validate_signal(signal)
    
    assert result.approved is True
    assert "approved" in result.reason.lower()


@pytest.mark.asyncio
async def test_position_tracking(risk_manager):
    """Test position tracking functionality."""
    # Initially no positions
    total_exposure = await risk_manager.get_total_exposure()
    assert total_exposure == 0.0
    
    # Add position
    await risk_manager.update_position("strategy1", "BTCUSDT", 100.0)
    position = await risk_manager.get_position("strategy1", "BTCUSDT")
    assert position == 100.0
    
    total_exposure = await risk_manager.get_total_exposure()
    assert total_exposure == 100.0
    
    # Add another position
    await risk_manager.update_position("strategy2", "ETHUSDT", 50.0)
    total_exposure = await risk_manager.get_total_exposure()
    assert total_exposure == 150.0
    
    # Close first position
    await risk_manager.update_position("strategy1", "BTCUSDT", 0.0)
    position = await risk_manager.get_position("strategy1", "BTCUSDT")
    assert position == 0.0
    
    total_exposure = await risk_manager.get_total_exposure()
    assert total_exposure == 50.0


@pytest.mark.asyncio
async def test_check_position_limit(risk_manager):
    """Test position limit checking."""
    assert await risk_manager.check_position_limit("BTCUSDT", 50.0) is True
    assert await risk_manager.check_position_limit("BTCUSDT", 100.0) is True
    assert await risk_manager.check_position_limit("BTCUSDT", 150.0) is False


@pytest.mark.asyncio
async def test_check_total_exposure(risk_manager):
    """Test total exposure checking."""
    # Initially within limits
    assert await risk_manager.check_total_exposure() is True
    
    # Add positions up to limit
    await risk_manager.update_position("strategy1", "BTCUSDT", 1000.0)
    assert await risk_manager.check_total_exposure() is True
    
    # Exceed limit
    await risk_manager.update_position("strategy2", "ETHUSDT", 1.0)
    assert await risk_manager.check_total_exposure() is False


@pytest.mark.asyncio
async def test_process_signal_approved(risk_manager):
    """Test signal processing with approved signal."""
    forwarded_signals = []
    
    async def signal_callback(signal: Signal):
        forwarded_signals.append(signal)
    
    risk_manager.signal_callback = signal_callback
    
    signal = Signal(
        strategy_name="test_strategy",
        symbol="BTCUSDT",
        side="buy",
        quantity=50.0,
        price=None,
        timestamp=datetime.now(),
        reason="Test buy"
    )
    
    await risk_manager.process_signal(signal)
    
    # Signal should be forwarded
    assert len(forwarded_signals) == 1
    assert forwarded_signals[0] == signal


@pytest.mark.asyncio
async def test_process_signal_rejected(risk_manager):
    """Test signal processing with rejected signal."""
    forwarded_signals = []
    
    async def signal_callback(signal: Signal):
        forwarded_signals.append(signal)
    
    risk_manager.signal_callback = signal_callback
    
    # Signal that exceeds position size
    signal = Signal(
        strategy_name="test_strategy",
        symbol="BTCUSDT",
        side="buy",
        quantity=150.0,
        price=None,
        timestamp=datetime.now(),
        reason="Test buy"
    )
    
    await risk_manager.process_signal(signal)
    
    # Signal should NOT be forwarded
    assert len(forwarded_signals) == 0
