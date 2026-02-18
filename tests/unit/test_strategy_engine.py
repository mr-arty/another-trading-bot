"""Unit tests for strategy engine."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.strategy.engine import StrategyEngine, Signal, StrategyState
from src.strategy.config import (
    StrategyConfig,
    IndicatorConfig,
    EntryCondition,
    ExitCondition
)
from src.exchange.connector import MarketData
from src.indicators.calculator import IndicatorCalculator


@pytest.fixture
def indicator_calculator():
    """Create a mock indicator calculator."""
    calc = AsyncMock(spec=IndicatorCalculator)
    return calc


@pytest.fixture
def sample_strategy_config():
    """Create a sample strategy configuration."""
    return StrategyConfig(
        name="test_strategy",
        symbol="BTCUSDT",
        timeframes=["15m"],
        indicators={
            "rsi": IndicatorConfig(
                type="rsi",
                timeframe="15m",
                period=14
            ),
            "ema_fast": IndicatorConfig(
                type="ema",
                timeframe="15m",
                period=9
            ),
            "ema_slow": IndicatorConfig(
                type="ema",
                timeframe="15m",
                period=21
            )
        },
        entry_conditions=[
            EntryCondition(
                type="greater_than",
                indicator="rsi",
                value=50
            ),
            EntryCondition(
                type="cross_above",
                indicator1="ema_fast",
                indicator2="ema_slow"
            )
        ],
        exit_conditions=[
            ExitCondition(
                type="take_profit",
                percent=4.0
            ),
            ExitCondition(
                type="stop_loss",
                percent=1.0
            )
        ],
        position_size=0.01,
        max_position_size=0.05
    )


@pytest.fixture
def sample_market_data():
    """Create sample market data."""
    return MarketData(
        symbol="BTCUSDT",
        timestamp=datetime.now(),
        open=50000.0,
        high=50100.0,
        low=49900.0,
        close=50050.0,
        volume=100.0
    )


@pytest.mark.asyncio
async def test_strategy_registration(indicator_calculator, sample_strategy_config):
    """Test strategy registration."""
    engine = StrategyEngine(indicator_calculator)
    
    await engine.register_strategy(sample_strategy_config)
    
    state = engine.get_strategy_state("test_strategy")
    assert state is not None
    assert state.config.name == "test_strategy"
    assert state.is_active is True
    assert state.has_position is False


@pytest.mark.asyncio
async def test_strategy_unregistration(indicator_calculator, sample_strategy_config):
    """Test strategy unregistration."""
    engine = StrategyEngine(indicator_calculator)
    
    await engine.register_strategy(sample_strategy_config)
    await engine.unregister_strategy("test_strategy")
    
    state = engine.get_strategy_state("test_strategy")
    assert state is None


@pytest.mark.asyncio
async def test_signal_generation_buy(indicator_calculator, sample_strategy_config, sample_market_data):
    """Test buy signal generation when entry conditions are met."""
    signals_received = []
    
    async def signal_callback(signal: Signal):
        signals_received.append(signal)
    
    engine = StrategyEngine(indicator_calculator, signal_callback)
    await engine.register_strategy(sample_strategy_config)
    
    # Mock indicator calculations - first pass
    indicator_calculator.add_market_data = AsyncMock()
    
    # First pass - set up previous indicators
    call_count = [0]
    async def mock_ema(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:  # ema_fast
            return 9.0
        else:  # ema_slow
            return 10.0
    
    indicator_calculator.calculate_rsi = AsyncMock(return_value=55.0)
    indicator_calculator.calculate_ema = mock_ema
    
    # Process market data
    await engine.process_market_data(sample_market_data)
    
    # First pass - no previous indicators for cross detection
    assert len(signals_received) == 0
    
    # Second pass - cross above condition
    call_count[0] = 0
    async def mock_ema_cross(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:  # ema_fast
            return 11.0
        else:  # ema_slow
            return 10.0
    
    indicator_calculator.calculate_rsi = AsyncMock(return_value=55.0)
    indicator_calculator.calculate_ema = mock_ema_cross
    
    # Process again
    await engine.process_market_data(sample_market_data)
    
    # Should generate buy signal
    assert len(signals_received) == 1
    signal = signals_received[0]
    assert signal.strategy_name == "test_strategy"
    assert signal.symbol == "BTCUSDT"
    assert signal.side == "buy"
    assert signal.quantity == 0.01


@pytest.mark.asyncio
async def test_signal_generation_sell(indicator_calculator, sample_strategy_config, sample_market_data):
    """Test sell signal generation when exit conditions are met."""
    signals_received = []
    
    async def signal_callback(signal: Signal):
        signals_received.append(signal)
    
    engine = StrategyEngine(indicator_calculator, signal_callback)
    await engine.register_strategy(sample_strategy_config)
    
    # Set position state
    state = engine.get_strategy_state("test_strategy")
    state.has_position = True
    state.entry_price = 48000.0  # Entry at 48000
    state.entry_time = datetime.now()
    
    # Mock indicator calculations
    indicator_calculator.add_market_data = AsyncMock()
    indicator_calculator.calculate_rsi = AsyncMock(return_value=55.0)
    indicator_calculator.calculate_ema = AsyncMock(side_effect=[10.0, 9.0])
    
    # Market data with price at 50050 (4.27% profit from 48000)
    await engine.process_market_data(sample_market_data)
    
    # Should generate sell signal (take profit)
    assert len(signals_received) == 1
    signal = signals_received[0]
    assert signal.strategy_name == "test_strategy"
    assert signal.symbol == "BTCUSDT"
    assert signal.side == "sell"
    assert "Take profit" in signal.reason


@pytest.mark.asyncio
async def test_no_signal_when_conditions_unmet(indicator_calculator, sample_strategy_config, sample_market_data):
    """Test that no signal is generated when conditions are not met."""
    signals_received = []
    
    async def signal_callback(signal: Signal):
        signals_received.append(signal)
    
    engine = StrategyEngine(indicator_calculator, signal_callback)
    await engine.register_strategy(sample_strategy_config)
    
    # Mock indicator calculations - RSI below threshold
    indicator_calculator.add_market_data = AsyncMock()
    indicator_calculator.calculate_rsi = AsyncMock(return_value=45.0)  # Below 50
    indicator_calculator.calculate_ema = AsyncMock(side_effect=[10.0, 9.0])
    
    # Process market data
    await engine.process_market_data(sample_market_data)
    
    # Should not generate signal
    assert len(signals_received) == 0


@pytest.mark.asyncio
async def test_concurrent_strategy_execution(indicator_calculator, sample_market_data):
    """Test that multiple strategies execute concurrently."""
    engine = StrategyEngine(indicator_calculator)
    
    # Register multiple strategies
    for i in range(3):
        config = StrategyConfig(
            name=f"strategy_{i}",
            symbol="BTCUSDT",
            timeframes=["15m"],
            indicators={
                "rsi": IndicatorConfig(type="rsi", timeframe="15m", period=14)
            },
            entry_conditions=[
                EntryCondition(type="greater_than", indicator="rsi", value=50)
            ],
            exit_conditions=[
                ExitCondition(type="take_profit", percent=4.0)
            ],
            position_size=0.01,
            max_position_size=0.05
        )
        await engine.register_strategy(config)
    
    # Mock indicator calculations
    indicator_calculator.add_market_data = AsyncMock()
    indicator_calculator.calculate_rsi = AsyncMock(return_value=55.0)
    
    # Process market data - should process all strategies
    await engine.process_market_data(sample_market_data)
    
    # Verify all strategies were processed
    stats = await engine.get_statistics()
    assert stats["total_strategies"] == 3
    assert stats["active_strategies"] == 3


@pytest.mark.asyncio
async def test_state_isolation_per_trading_pair(indicator_calculator):
    """Test that state is isolated per trading pair."""
    engine = StrategyEngine(indicator_calculator)
    
    # Register strategies for different symbols
    config1 = StrategyConfig(
        name="btc_strategy",
        symbol="BTCUSDT",
        timeframes=["15m"],
        indicators={"rsi": IndicatorConfig(type="rsi", timeframe="15m", period=14)},
        entry_conditions=[EntryCondition(type="greater_than", indicator="rsi", value=50)],
        exit_conditions=[ExitCondition(type="take_profit", percent=4.0)],
        position_size=0.01,
        max_position_size=0.05
    )
    
    config2 = StrategyConfig(
        name="eth_strategy",
        symbol="ETHUSDT",
        timeframes=["15m"],
        indicators={"rsi": IndicatorConfig(type="rsi", timeframe="15m", period=14)},
        entry_conditions=[EntryCondition(type="greater_than", indicator="rsi", value=50)],
        exit_conditions=[ExitCondition(type="take_profit", percent=4.0)],
        position_size=0.01,
        max_position_size=0.05
    )
    
    await engine.register_strategy(config1)
    await engine.register_strategy(config2)
    
    # Verify separate pair states exist
    assert ("btc_strategy", "BTCUSDT") in engine._pair_states
    assert ("eth_strategy", "ETHUSDT") in engine._pair_states
    # Verify they are different objects (not the same reference)
    assert id(engine._pair_states[("btc_strategy", "BTCUSDT")]) != id(engine._pair_states[("eth_strategy", "ETHUSDT")])


@pytest.mark.asyncio
async def test_strategy_error_isolation(indicator_calculator, sample_market_data):
    """Test that errors in one strategy don't affect others."""
    signals_received = []
    
    async def signal_callback(signal: Signal):
        signals_received.append(signal)
    
    engine = StrategyEngine(indicator_calculator, signal_callback)
    
    # Register two strategies
    config1 = StrategyConfig(
        name="good_strategy",
        symbol="BTCUSDT",
        timeframes=["15m"],
        indicators={"rsi": IndicatorConfig(type="rsi", timeframe="15m", period=14)},
        entry_conditions=[EntryCondition(type="greater_than", indicator="rsi", value=50)],
        exit_conditions=[ExitCondition(type="take_profit", percent=4.0)],
        position_size=0.01,
        max_position_size=0.05
    )
    
    config2 = StrategyConfig(
        name="bad_strategy",
        symbol="BTCUSDT",
        timeframes=["15m"],
        indicators={"rsi": IndicatorConfig(type="rsi", timeframe="15m", period=14)},
        entry_conditions=[EntryCondition(type="greater_than", indicator="rsi", value=50)],
        exit_conditions=[ExitCondition(type="take_profit", percent=4.0)],
        position_size=0.01,
        max_position_size=0.05
    )
    
    await engine.register_strategy(config1)
    await engine.register_strategy(config2)
    
    # Mock indicator calculations - one will fail with exception in processing
    call_count = [0]
    
    async def mock_add_market_data(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 2:  # Second strategy
            raise Exception("Processing error")
    
    indicator_calculator.add_market_data = mock_add_market_data
    indicator_calculator.calculate_rsi = AsyncMock(return_value=55.0)
    
    # Process market data
    await engine.process_market_data(sample_market_data)
    
    # Verify good strategy still works and bad strategy has error
    good_state = engine.get_strategy_state("good_strategy")
    bad_state = engine.get_strategy_state("bad_strategy")
    
    assert good_state.error_count == 0
    assert bad_state.error_count == 1
    assert bad_state.last_error is not None
    
    # Verify good strategy generated signal
    assert len(signals_received) == 1
    assert signals_received[0].strategy_name == "good_strategy"


@pytest.mark.asyncio
async def test_position_state_update(indicator_calculator, sample_strategy_config):
    """Test updating position state after order fills."""
    engine = StrategyEngine(indicator_calculator)
    await engine.register_strategy(sample_strategy_config)
    
    # Update position state
    await engine.update_position_state("test_strategy", True, 50000.0)
    
    state = engine.get_strategy_state("test_strategy")
    assert state.has_position is True
    assert state.entry_price == 50000.0
    
    # Close position
    await engine.update_position_state("test_strategy", False)
    
    state = engine.get_strategy_state("test_strategy")
    assert state.has_position is False
    assert state.entry_price is None


@pytest.mark.asyncio
async def test_signal_metadata_completeness(indicator_calculator, sample_strategy_config, sample_market_data):
    """Test that signals include all required metadata."""
    signals_received = []
    
    async def signal_callback(signal: Signal):
        signals_received.append(signal)
    
    engine = StrategyEngine(indicator_calculator, signal_callback)
    await engine.register_strategy(sample_strategy_config)
    
    # Set up for signal generation
    state = engine.get_strategy_state("test_strategy")
    state.has_position = True
    state.entry_price = 48000.0
    state.entry_time = datetime.now()
    
    indicator_calculator.add_market_data = AsyncMock()
    indicator_calculator.calculate_rsi = AsyncMock(return_value=55.0)
    indicator_calculator.calculate_ema = AsyncMock(side_effect=[10.0, 9.0])
    
    await engine.process_market_data(sample_market_data)
    
    # Verify signal has all metadata
    assert len(signals_received) == 1
    signal = signals_received[0]
    
    assert signal.strategy_name is not None
    assert signal.symbol is not None
    assert signal.side is not None
    assert signal.quantity is not None
    assert signal.timestamp is not None
    assert signal.reason is not None
    assert len(signal.reason) > 0
