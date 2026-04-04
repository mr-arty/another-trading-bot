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


# ============================================================================
# Price Near Level Condition Tests (Task 6)
# ============================================================================

@pytest.mark.asyncio
async def test_price_within_proximity_threshold(indicator_calculator):
    """Test 6.1: Price within proximity threshold should return True."""
    from src.strategy.config import PriceNearLevelCondition
    
    config = StrategyConfig(
        name="test_range",
        symbol="BTCUSDT",
        timeframes=["4h"],
        indicators={"rsi": IndicatorConfig(type="rsi", timeframe="4h", period=14)},
        entry_conditions=[
            EntryCondition(type="less_than", indicator="rsi", value=30)
        ],
        exit_conditions=[
            ExitCondition(type="take_profit", percent=2.0)
        ],
        position_size=0.01,
        max_position_size=0.05,
        support_level=68000.0,
        resistance_level=72000.0,
        level_proximity_percent=0.5
    )
    
    state = StrategyState(config=config)
    engine = StrategyEngine(indicator_calculator)
    
    condition = PriceNearLevelCondition(
        type="price_near_level",
        level="support"
    )
    
    # Price at 68200 is 0.29% from support (68000)
    # Distance: abs(68200 - 68000) / 68000 * 100 = 0.294%
    met, reason = await engine._evaluate_price_near_level_condition(
        condition, state, 68200.0
    )
    
    assert met is True
    assert "within" in reason.lower()
    assert "68200" in reason
    assert "support" in reason.lower()


@pytest.mark.asyncio
async def test_price_outside_proximity_threshold(indicator_calculator):
    """Test 6.2: Price outside proximity threshold should return False."""
    from src.strategy.config import PriceNearLevelCondition
    
    config = StrategyConfig(
        name="test_range",
        symbol="BTCUSDT",
        timeframes=["4h"],
        indicators={"rsi": IndicatorConfig(type="rsi", timeframe="4h", period=14)},
        entry_conditions=[
            EntryCondition(type="less_than", indicator="rsi", value=30)
        ],
        exit_conditions=[
            ExitCondition(type="take_profit", percent=2.0)
        ],
        position_size=0.01,
        max_position_size=0.05,
        support_level=68000.0,
        resistance_level=72000.0,
        level_proximity_percent=0.5
    )
    
    state = StrategyState(config=config)
    engine = StrategyEngine(indicator_calculator)
    
    condition = PriceNearLevelCondition(
        type="price_near_level",
        level="support"
    )
    
    # Price at 69000 is 1.47% from support (68000)
    # Distance: abs(69000 - 68000) / 68000 * 100 = 1.47%
    met, reason = await engine._evaluate_price_near_level_condition(
        condition, state, 69000.0
    )
    
    assert met is False
    assert "from" in reason.lower()
    assert "69000" in reason
    assert "threshold" in reason.lower()


@pytest.mark.asyncio
async def test_price_exactly_at_level(indicator_calculator):
    """Test 6.3: Price exactly at level should return True."""
    from src.strategy.config import PriceNearLevelCondition
    
    config = StrategyConfig(
        name="test_range",
        symbol="BTCUSDT",
        timeframes=["4h"],
        indicators={"rsi": IndicatorConfig(type="rsi", timeframe="4h", period=14)},
        entry_conditions=[
            EntryCondition(type="less_than", indicator="rsi", value=30)
        ],
        exit_conditions=[
            ExitCondition(type="take_profit", percent=2.0)
        ],
        position_size=0.01,
        max_position_size=0.05,
        support_level=68000.0,
        resistance_level=72000.0,
        level_proximity_percent=0.5
    )
    
    state = StrategyState(config=config)
    engine = StrategyEngine(indicator_calculator)
    
    condition = PriceNearLevelCondition(
        type="price_near_level",
        level="support"
    )
    
    # Price exactly at support level (distance = 0%)
    met, reason = await engine._evaluate_price_near_level_condition(
        condition, state, 68000.0
    )
    
    assert met is True
    assert "within" in reason.lower()
    assert "0.00%" in reason


@pytest.mark.asyncio
async def test_support_level_evaluation(indicator_calculator):
    """Test 6.4: Support level evaluation."""
    from src.strategy.config import PriceNearLevelCondition
    
    config = StrategyConfig(
        name="test_range",
        symbol="BTCUSDT",
        timeframes=["4h"],
        indicators={"rsi": IndicatorConfig(type="rsi", timeframe="4h", period=14)},
        entry_conditions=[
            EntryCondition(type="less_than", indicator="rsi", value=30)
        ],
        exit_conditions=[
            ExitCondition(type="take_profit", percent=2.0)
        ],
        position_size=0.01,
        max_position_size=0.05,
        support_level=68000.0,
        resistance_level=72000.0,
        level_proximity_percent=0.5
    )
    
    state = StrategyState(config=config)
    engine = StrategyEngine(indicator_calculator)
    
    condition = PriceNearLevelCondition(
        type="price_near_level",
        level="support"
    )
    
    # Test price near support
    met, reason = await engine._evaluate_price_near_level_condition(
        condition, state, 68100.0
    )
    
    assert met is True
    assert "support" in reason.lower()
    assert "68000" in reason  # Support level mentioned


@pytest.mark.asyncio
async def test_resistance_level_evaluation(indicator_calculator):
    """Test 6.5: Resistance level evaluation."""
    from src.strategy.config import PriceNearLevelCondition
    
    config = StrategyConfig(
        name="test_range",
        symbol="BTCUSDT",
        timeframes=["4h"],
        indicators={"rsi": IndicatorConfig(type="rsi", timeframe="4h", period=14)},
        entry_conditions=[
            EntryCondition(type="less_than", indicator="rsi", value=30)
        ],
        exit_conditions=[
            ExitCondition(type="take_profit", percent=2.0)
        ],
        position_size=0.01,
        max_position_size=0.05,
        support_level=68000.0,
        resistance_level=72000.0,
        level_proximity_percent=0.5
    )
    
    state = StrategyState(config=config)
    engine = StrategyEngine(indicator_calculator)
    
    condition = PriceNearLevelCondition(
        type="price_near_level",
        level="resistance"
    )
    
    # Test price near resistance
    met, reason = await engine._evaluate_price_near_level_condition(
        condition, state, 71900.0
    )
    
    assert met is True
    assert "resistance" in reason.lower()
    assert "72000" in reason  # Resistance level mentioned


@pytest.mark.asyncio
async def test_proximity_zone_entry_logging(indicator_calculator, capsys):
    """Test 6.6: Proximity zone entry logging."""
    from src.strategy.config import PriceNearLevelCondition
    
    config = StrategyConfig(
        name="test_range",
        symbol="BTCUSDT",
        timeframes=["4h"],
        indicators={"rsi": IndicatorConfig(type="rsi", timeframe="4h", period=14)},
        entry_conditions=[
            EntryCondition(type="less_than", indicator="rsi", value=30)
        ],
        exit_conditions=[
            ExitCondition(type="take_profit", percent=2.0)
        ],
        position_size=0.01,
        max_position_size=0.05,
        support_level=68000.0,
        resistance_level=72000.0,
        level_proximity_percent=0.5
    )
    
    state = StrategyState(config=config)
    engine = StrategyEngine(indicator_calculator)
    
    condition = PriceNearLevelCondition(
        type="price_near_level",
        level="support"
    )
    
    # First call - price far from support (not in zone)
    await engine._evaluate_price_near_level_condition(
        condition, state, 70000.0
    )
    
    # Second call - price enters proximity zone
    await engine._evaluate_price_near_level_condition(
        condition, state, 68200.0
    )
    
    # Check that entering_level_proximity was logged
    captured = capsys.readouterr()
    assert "entering_level_proximity" in captured.out


@pytest.mark.asyncio
async def test_proximity_zone_exit_logging(indicator_calculator, capsys):
    """Test 6.7: Proximity zone exit logging."""
    from src.strategy.config import PriceNearLevelCondition
    
    config = StrategyConfig(
        name="test_range",
        symbol="BTCUSDT",
        timeframes=["4h"],
        indicators={"rsi": IndicatorConfig(type="rsi", timeframe="4h", period=14)},
        entry_conditions=[
            EntryCondition(type="less_than", indicator="rsi", value=30)
        ],
        exit_conditions=[
            ExitCondition(type="take_profit", percent=2.0)
        ],
        position_size=0.01,
        max_position_size=0.05,
        support_level=68000.0,
        resistance_level=72000.0,
        level_proximity_percent=0.5
    )
    
    state = StrategyState(config=config)
    engine = StrategyEngine(indicator_calculator)
    
    condition = PriceNearLevelCondition(
        type="price_near_level",
        level="support"
    )
    
    # First call - price in proximity zone
    await engine._evaluate_price_near_level_condition(
        condition, state, 68200.0
    )
    
    # Second call - price exits proximity zone
    await engine._evaluate_price_near_level_condition(
        condition, state, 70000.0
    )
    
    # Check that exiting_level_proximity was logged
    captured = capsys.readouterr()
    assert "exiting_level_proximity" in captured.out


@pytest.mark.asyncio
async def test_reason_string_format(indicator_calculator):
    """Test 6.8: Reason string format."""
    from src.strategy.config import PriceNearLevelCondition
    
    config = StrategyConfig(
        name="test_range",
        symbol="BTCUSDT",
        timeframes=["4h"],
        indicators={"rsi": IndicatorConfig(type="rsi", timeframe="4h", period=14)},
        entry_conditions=[
            EntryCondition(type="less_than", indicator="rsi", value=30)
        ],
        exit_conditions=[
            ExitCondition(type="take_profit", percent=2.0)
        ],
        position_size=0.01,
        max_position_size=0.05,
        support_level=68000.0,
        resistance_level=72000.0,
        level_proximity_percent=0.5
    )
    
    state = StrategyState(config=config)
    engine = StrategyEngine(indicator_calculator)
    
    condition = PriceNearLevelCondition(
        type="price_near_level",
        level="support"
    )
    
    # Test reason when condition is met
    met, reason = await engine._evaluate_price_near_level_condition(
        condition, state, 68200.0
    )
    
    assert met is True
    # Reason should include: current price, distance %, level type, level price
    assert "68200.00" in reason
    assert "%" in reason
    assert "support" in reason.lower()
    assert "68000.00" in reason
    assert "within" in reason.lower()
    
    # Test reason when condition is not met
    met, reason = await engine._evaluate_price_near_level_condition(
        condition, state, 70000.0
    )
    
    assert met is False
    assert "70000.00" in reason
    assert "%" in reason
    assert "support" in reason.lower()
    assert "68000.00" in reason
    assert "from" in reason.lower()
    assert "threshold" in reason.lower()


@pytest.mark.asyncio
async def test_missing_support_level_handling(indicator_calculator, capsys):
    """Test 6.9: Missing level handling."""
    from src.strategy.config import PriceNearLevelCondition
    
    # Config without support_level defined
    config = StrategyConfig(
        name="test_range",
        symbol="BTCUSDT",
        timeframes=["4h"],
        indicators={"rsi": IndicatorConfig(type="rsi", timeframe="4h", period=14)},
        entry_conditions=[
            EntryCondition(type="less_than", indicator="rsi", value=30)
        ],
        exit_conditions=[
            ExitCondition(type="take_profit", percent=2.0)
        ],
        position_size=0.01,
        max_position_size=0.05,
        support_level=None,  # Not defined
        resistance_level=72000.0,
        level_proximity_percent=0.5
    )
    
    state = StrategyState(config=config)
    engine = StrategyEngine(indicator_calculator)
    
    condition = PriceNearLevelCondition(
        type="price_near_level",
        level="support"
    )
    
    # Should return False and log error
    met, reason = await engine._evaluate_price_near_level_condition(
        condition, state, 68200.0
    )
    
    assert met is False
    assert "not defined" in reason.lower()
    
    # Check error was logged
    captured = capsys.readouterr()
    assert "missing_support_level" in captured.out


@pytest.mark.asyncio
async def test_missing_resistance_level_handling(indicator_calculator, capsys):
    """Test 6.9: Missing resistance level handling."""
    from src.strategy.config import PriceNearLevelCondition
    
    # Config without resistance_level defined
    config = StrategyConfig(
        name="test_range",
        symbol="BTCUSDT",
        timeframes=["4h"],
        indicators={"rsi": IndicatorConfig(type="rsi", timeframe="4h", period=14)},
        entry_conditions=[
            EntryCondition(type="less_than", indicator="rsi", value=30)
        ],
        exit_conditions=[
            ExitCondition(type="take_profit", percent=2.0)
        ],
        position_size=0.01,
        max_position_size=0.05,
        support_level=68000.0,
        resistance_level=None,  # Not defined
        level_proximity_percent=0.5
    )
    
    state = StrategyState(config=config)
    engine = StrategyEngine(indicator_calculator)
    
    condition = PriceNearLevelCondition(
        type="price_near_level",
        level="resistance"
    )
    
    # Should return False and log error
    met, reason = await engine._evaluate_price_near_level_condition(
        condition, state, 71900.0
    )
    
    assert met is False
    assert "not defined" in reason.lower()
    
    # Check error was logged
    captured = capsys.readouterr()
    assert "missing_resistance_level" in captured.out


@pytest.mark.asyncio
async def test_distance_calculation_accuracy(indicator_calculator):
    """Test 6.10: Distance calculation accuracy to 0.01%."""
    from src.strategy.config import PriceNearLevelCondition
    
    config = StrategyConfig(
        name="test_range",
        symbol="BTCUSDT",
        timeframes=["4h"],
        indicators={"rsi": IndicatorConfig(type="rsi", timeframe="4h", period=14)},
        entry_conditions=[
            EntryCondition(type="less_than", indicator="rsi", value=30)
        ],
        exit_conditions=[
            ExitCondition(type="take_profit", percent=2.0)
        ],
        position_size=0.01,
        max_position_size=0.05,
        support_level=68000.0,
        resistance_level=72000.0,
        level_proximity_percent=0.5
    )
    
    state = StrategyState(config=config)
    engine = StrategyEngine(indicator_calculator)
    
    condition = PriceNearLevelCondition(
        type="price_near_level",
        level="support"
    )
    
    # Test various prices and verify distance calculation
    test_cases = [
        # (current_price, expected_distance_percent, should_be_near)
        (68000.0, 0.00, True),      # Exactly at level
        (68100.0, 0.147, True),     # 100 above: 100/68000*100 = 0.147%
        (68340.0, 0.50, True),      # Exactly at threshold: 340/68000*100 = 0.50%
        (68341.0, 0.501, False),    # Just above threshold
        (67660.0, 0.50, True),      # 340 below: 340/68000*100 = 0.50%
        (67659.0, 0.501, False),    # Just below threshold
    ]
    
    for current_price, expected_distance, should_be_near in test_cases:
        met, reason = await engine._evaluate_price_near_level_condition(
            condition, state, current_price
        )
        
        # Extract distance from reason string
        # Format: "Price X within/is Y% of/from support Z"
        import re
        match = re.search(r'(\d+\.\d+)%', reason)
        assert match is not None, f"Could not find distance in reason: {reason}"
        
        actual_distance = float(match.group(1))
        
        # Verify accuracy to 0.01%
        assert abs(actual_distance - expected_distance) < 0.01, \
            f"Distance calculation inaccurate for price {current_price}: " \
            f"expected {expected_distance}%, got {actual_distance}%"
        
        # Verify condition result
        assert met == should_be_near, \
            f"Condition result incorrect for price {current_price}: " \
            f"expected {should_be_near}, got {met}"


@pytest.mark.asyncio
async def test_price_near_level_integration_with_entry_conditions(indicator_calculator):
    """Test price near level condition integrated with other entry conditions."""
    from src.strategy.config import PriceNearLevelCondition
    
    signals_received = []
    
    async def signal_callback(signal: Signal):
        signals_received.append(signal)
    
    engine = StrategyEngine(indicator_calculator, signal_callback)
    
    # Create strategy with both RSI and price near level conditions
    config = StrategyConfig(
        name="range_strategy",
        symbol="BTCUSDT",
        timeframes=["4h"],
        indicators={
            "rsi_4h": IndicatorConfig(type="rsi", timeframe="4h", period=14)
        },
        entry_conditions=[
            EntryCondition(type="less_than", indicator="rsi_4h", value=30),
            PriceNearLevelCondition(type="price_near_level", level="support")
        ],
        exit_conditions=[
            ExitCondition(type="take_profit", percent=2.0)
        ],
        position_size=0.01,
        max_position_size=0.05,
        support_level=68000.0,
        resistance_level=72000.0,
        level_proximity_percent=0.5
    )
    
    await engine.register_strategy(config)
    
    # Mock indicator calculations
    indicator_calculator.add_market_data = AsyncMock()
    indicator_calculator.calculate_rsi = AsyncMock(return_value=25.0)  # RSI < 30
    
    # Market data with price near support
    market_data = MarketData(
        symbol="BTCUSDT",
        timestamp=datetime.now(),
        open=68100.0,
        high=68200.0,
        low=68000.0,
        close=68150.0,  # Within 0.5% of support
        volume=100.0
    )
    
    await engine.process_market_data(market_data)
    
    # Should generate buy signal (both conditions met)
    assert len(signals_received) == 1
    signal = signals_received[0]
    assert signal.side == "buy"
    assert "rsi" in signal.reason.lower()
    assert "support" in signal.reason.lower()
