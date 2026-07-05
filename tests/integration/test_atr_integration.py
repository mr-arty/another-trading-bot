"""Integration tests for ATR exit conditions in StrategyEngine."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock
import asyncio

from src.strategy.engine import StrategyEngine, Signal
from src.strategy.config import (
    StrategyConfig,
    IndicatorConfig,
    EntryCondition,
    AtrThresholdCondition,
    AtrStopLossCondition,
    AtrPercentChangeCondition
)
from src.indicators.calculator import IndicatorCalculator
from src.exchange.connector import MarketData


@pytest.fixture
def indicator_calculator():
    """Create a mock indicator calculator."""
    return AsyncMock(spec=IndicatorCalculator)


@pytest.fixture
def captured_signals():
    """Create a list to capture emitted signals."""
    signals = []
    
    async def signal_callback(signal: Signal):
        signals.append(signal)
    
    return signals, signal_callback


@pytest.fixture
def strategy_engine_with_callback(indicator_calculator, captured_signals):
    """Create a strategy engine with signal callback."""
    signals, callback = captured_signals
    engine = StrategyEngine(
        indicator_calculator=indicator_calculator,
        signal_callback=callback
    )
    return engine, signals


def create_market_data(close_price: float, timestamp: datetime = None) -> MarketData:
    """Helper to create market data."""
    if timestamp is None:
        timestamp = datetime.now()
    
    return MarketData(
        symbol="BTC/USD",
        timestamp=timestamp,
        open=close_price,
        high=close_price + 100,
        low=close_price - 100,
        close=close_price,
        volume=100.0
    )


@pytest.mark.asyncio
async def test_atr_threshold_exit_integration(strategy_engine_with_callback, indicator_calculator):
    """
    Integration test: ATR threshold condition triggers exit signal.
    
    Tests end-to-end flow:
    1. Register strategy with ATR threshold exit condition
    2. Enter position
    3. Feed data with ATR above threshold
    4. Verify exit signal generated with correct reason
    """
    engine, signals = strategy_engine_with_callback
    
    # Create strategy with ATR threshold exit condition
    config = StrategyConfig(
        name="atr_threshold_strategy",
        symbol="BTC/USD",
        timeframes=["1m"],
        position_direction="long",
        position_size=1.0,
        max_position_size=10.0,
        indicators={
            "atr_14": IndicatorConfig(
                type="atr",
                timeframe="1m",
                period=14
            )
        },
        entry_conditions=[
            EntryCondition(
                type="greater_than",
                indicator="atr_14",
                value=100.0
            )
        ],
        exit_conditions=[
            AtrThresholdCondition(
                type="atr_threshold",
                atr_indicator="atr_14",
                threshold=600.0,
                direction="above"
            )
        ]
    )
    
    # Register strategy
    await engine.register_strategy(config)
    
    # Mock indicator calculator
    indicator_calculator.add_market_data = AsyncMock()
    
    # Mock _calculate_indicators to return ATR values
    async def mock_calculate_indicators(config, symbol):
        return {"atr_14": 400.0}
    
    engine._calculate_indicators = mock_calculate_indicators
    
    # Feed market data to trigger entry
    await engine.process_market_data(create_market_data(50000.0))
    
    # Verify entry signal
    assert len(signals) == 1
    assert signals[0].side == "buy"
    assert signals[0].strategy_name == "atr_threshold_strategy"
    
    # Set entry price (simulating order fill)
    state = engine.get_strategy_state("atr_threshold_strategy")
    state.entry_price = 50000.0
    
    # Mock ATR to be above threshold
    async def mock_calculate_indicators_high_atr(config, symbol):
        return {"atr_14": 700.0}
    
    engine._calculate_indicators = mock_calculate_indicators_high_atr
    
    # Feed market data to trigger exit
    await engine.process_market_data(create_market_data(50500.0))
    
    # Verify exit signal
    assert len(signals) == 2
    exit_signal = signals[1]
    assert exit_signal.side == "sell"
    assert exit_signal.strategy_name == "atr_threshold_strategy"
    assert "ATR" in exit_signal.reason
    assert "700.00" in exit_signal.reason
    assert "600.00" in exit_signal.reason


@pytest.mark.asyncio
async def test_atr_stop_loss_exit_integration(strategy_engine_with_callback, indicator_calculator):
    """
    Integration test: ATR stop loss condition triggers exit signal for long position.
    
    Tests:
    1. Register strategy with ATR stop loss
    2. Enter position and store entry_atr
    3. Price drops below ATR-based stop loss
    4. Verify exit signal with correct calculation
    """
    engine, signals = strategy_engine_with_callback
    
    # Create strategy with ATR stop loss
    config = StrategyConfig(
        name="atr_stop_loss_strategy",
        symbol="BTC/USD",
        timeframes=["1m"],
        position_direction="long",
        position_size=1.0,
        max_position_size=10.0,
        indicators={
            "atr_14": IndicatorConfig(
                type="atr",
                timeframe="1m",
                period=14
            )
        },
        entry_conditions=[
            EntryCondition(
                type="greater_than",
                indicator="atr_14",
                value=100.0
            )
        ],
        exit_conditions=[
            AtrStopLossCondition(
                type="atr_stop_loss",
                atr_indicator="atr_14",
                multiplier=2.0
            )
        ]
    )
    
    # Register strategy
    await engine.register_strategy(config)
    
    # Mock indicator calculator
    indicator_calculator.add_market_data = AsyncMock()
    
    # Mock ATR = 400
    async def mock_calculate_indicators(config, symbol):
        return {"atr_14": 400.0}
    
    engine._calculate_indicators = mock_calculate_indicators
    
    # Feed market data to trigger entry at 50000
    await engine.process_market_data(create_market_data(50000.0))
    
    # Verify entry signal and entry_atr stored
    assert len(signals) == 1
    state = engine.get_strategy_state("atr_stop_loss_strategy")
    assert state.entry_atr == 400.0
    
    # Set entry price
    state.entry_price = 50000.0
    
    # Calculate expected stop loss: 50000 - (400 * 2) = 49200
    # Feed market data with price at 49000 (below stop loss)
    await engine.process_market_data(create_market_data(49000.0))
    
    # Verify exit signal
    assert len(signals) == 2
    exit_signal = signals[1]
    assert exit_signal.side == "sell"
    assert "stop loss" in exit_signal.reason.lower()
    assert "49000.00" in exit_signal.reason
    assert "49200.00" in exit_signal.reason


@pytest.mark.asyncio
async def test_atr_percent_change_exit_integration(strategy_engine_with_callback, indicator_calculator):
    """
    Integration test: ATR percent change condition triggers exit on volatility spike.
    
    Tests:
    1. Register strategy with ATR percent change exit
    2. Enter position and store entry_atr
    3. ATR increases by more than threshold
    4. Verify exit signal with correct percentage calculation
    """
    engine, signals = strategy_engine_with_callback
    
    # Create strategy with ATR percent change exit
    config = StrategyConfig(
        name="atr_percent_change_strategy",
        symbol="BTC/USD",
        timeframes=["1m"],
        position_direction="long",
        position_size=1.0,
        max_position_size=10.0,
        indicators={
            "atr_14": IndicatorConfig(
                type="atr",
                timeframe="1m",
                period=14
            )
        },
        entry_conditions=[
            EntryCondition(
                type="greater_than",
                indicator="atr_14",
                value=100.0
            )
        ],
        exit_conditions=[
            AtrPercentChangeCondition(
                type="atr_percent_change",
                atr_indicator="atr_14",
                percent_change=50.0,
                direction="increase"
            )
        ]
    )
    
    # Register strategy
    await engine.register_strategy(config)
    
    # Mock indicator calculator
    indicator_calculator.add_market_data = AsyncMock()
    
    # Mock entry ATR = 400
    async def mock_calculate_indicators_entry(config, symbol):
        return {"atr_14": 400.0}
    
    engine._calculate_indicators = mock_calculate_indicators_entry
    
    # Feed market data to trigger entry
    await engine.process_market_data(create_market_data(50000.0))
    
    # Verify entry signal and entry_atr stored
    assert len(signals) == 1
    state = engine.get_strategy_state("atr_percent_change_strategy")
    assert state.entry_atr == 400.0
    
    # Set entry price
    state.entry_price = 50000.0
    
    # Mock ATR increased to 650 (62.5% increase from 400)
    async def mock_calculate_indicators_high_atr(config, symbol):
        return {"atr_14": 650.0}
    
    engine._calculate_indicators = mock_calculate_indicators_high_atr
    
    # Feed market data to trigger exit
    await engine.process_market_data(create_market_data(50500.0))
    
    # Verify exit signal
    assert len(signals) == 2
    exit_signal = signals[1]
    assert exit_signal.side == "sell"
    assert "increased" in exit_signal.reason.lower()
    assert "400.00" in exit_signal.reason  # entry_atr
    assert "650.00" in exit_signal.reason  # current_atr
    assert "62.5" in exit_signal.reason or "62.50" in exit_signal.reason  # percent change


@pytest.mark.asyncio
async def test_multiple_atr_conditions_first_triggers(strategy_engine_with_callback, indicator_calculator):
    """
    Integration test: Multiple ATR exit conditions, first one to trigger wins.
    
    Tests that when multiple ATR conditions are configured, the first one
    to be met triggers the exit signal.
    """
    engine, signals = strategy_engine_with_callback
    
    # Create strategy with multiple ATR exit conditions
    config = StrategyConfig(
        name="multi_atr_strategy",
        symbol="BTC/USD",
        timeframes=["1m"],
        position_direction="long",
        position_size=1.0,
        max_position_size=10.0,
        indicators={
            "atr_14": IndicatorConfig(
                type="atr",
                timeframe="1m",
                period=14
            )
        },
        entry_conditions=[
            EntryCondition(
                type="greater_than",
                indicator="atr_14",
                value=100.0
            )
        ],
        exit_conditions=[
            AtrThresholdCondition(
                type="atr_threshold",
                atr_indicator="atr_14",
                threshold=600.0,
                direction="above"
            ),
            AtrStopLossCondition(
                type="atr_stop_loss",
                atr_indicator="atr_14",
                multiplier=2.0
            ),
            AtrPercentChangeCondition(
                type="atr_percent_change",
                atr_indicator="atr_14",
                percent_change=50.0,
                direction="increase"
            )
        ]
    )
    
    # Register strategy
    await engine.register_strategy(config)
    
    # Mock indicator calculator
    indicator_calculator.add_market_data = AsyncMock()
    
    # Entry with ATR = 400
    async def mock_calculate_indicators_entry(config, symbol):
        return {"atr_14": 400.0}
    
    engine._calculate_indicators = mock_calculate_indicators_entry
    
    # Trigger entry
    await engine.process_market_data(create_market_data(50000.0))
    
    state = engine.get_strategy_state("multi_atr_strategy")
    state.entry_price = 50000.0
    
    # Set ATR = 700 (triggers threshold condition)
    async def mock_calculate_indicators_high_atr(config, symbol):
        return {"atr_14": 700.0}
    
    engine._calculate_indicators = mock_calculate_indicators_high_atr
    
    # Feed market data
    await engine.process_market_data(create_market_data(50500.0))
    
    # Verify exit triggered by threshold condition (first in list)
    assert len(signals) == 2
    exit_signal = signals[1]
    assert exit_signal.side == "sell"
    assert "threshold" in exit_signal.reason.lower()


@pytest.mark.asyncio
async def test_error_isolation_in_atr_evaluation(strategy_engine_with_callback, indicator_calculator):
    """
    Integration test: Error in ATR condition evaluation doesn't crash engine.
    Property 15: Error Isolation
    
    Tests that errors in one ATR condition don't prevent other conditions
    from being evaluated.
    """
    engine, signals = strategy_engine_with_callback
    
    # Create strategy with ATR conditions
    config = StrategyConfig(
        name="error_isolation_strategy",
        symbol="BTC/USD",
        timeframes=["1m"],
        position_direction="long",
        position_size=1.0,
        max_position_size=10.0,
        indicators={
            "atr_14": IndicatorConfig(
                type="atr",
                timeframe="1m",
                period=14
            )
        },
        entry_conditions=[
            EntryCondition(
                type="greater_than",
                indicator="atr_14",
                value=100.0
            )
        ],
        exit_conditions=[
            AtrPercentChangeCondition(
                type="atr_percent_change",
                atr_indicator="atr_14",
                percent_change=50.0,
                direction="increase"
            )
        ]
    )
    
    # Register strategy
    await engine.register_strategy(config)
    
    # Mock indicator calculator
    indicator_calculator.add_market_data = AsyncMock()
    
    # Entry
    async def mock_calculate_indicators_entry(config, symbol):
        return {"atr_14": 400.0}
    
    engine._calculate_indicators = mock_calculate_indicators_entry
    
    await engine.process_market_data(create_market_data(50000.0))
    
    state = engine.get_strategy_state("error_isolation_strategy")
    state.entry_price = 50000.0
    
    # Mock _calculate_indicators to raise an exception
    async def mock_calculate_indicators_error(config, symbol):
        raise RuntimeError("Simulated indicator calculation error")
    
    engine._calculate_indicators = mock_calculate_indicators_error
    
    # Feed market data - should not crash, error should be isolated
    await engine.process_market_data(create_market_data(50500.0))
    
    # Verify engine didn't crash and error was logged
    assert state.error_count > 0
    assert "Simulated indicator calculation error" in state.last_error


@pytest.mark.asyncio
async def test_atr_conditions_short_position(strategy_engine_with_callback, indicator_calculator):
    """
    Integration test: ATR stop loss works correctly for short positions.
    
    Tests that ATR-based stop loss calculation is correct for short positions
    where stop loss is above entry price.
    """
    engine, signals = strategy_engine_with_callback
    
    # Create SHORT strategy with ATR stop loss
    config = StrategyConfig(
        name="short_atr_strategy",
        symbol="BTC/USD",
        timeframes=["1m"],
        position_direction="short",  # SHORT position
        position_size=1.0,
        max_position_size=10.0,
        indicators={
            "atr_14": IndicatorConfig(
                type="atr",
                timeframe="1m",
                period=14
            )
        },
        entry_conditions=[
            EntryCondition(
                type="greater_than",
                indicator="atr_14",
                value=100.0
            )
        ],
        exit_conditions=[
            AtrStopLossCondition(
                type="atr_stop_loss",
                atr_indicator="atr_14",
                multiplier=2.0
            )
        ]
    )
    
    # Register strategy
    await engine.register_strategy(config)
    
    # Mock indicator calculator
    indicator_calculator.add_market_data = AsyncMock()
    
    # Entry with ATR = 400
    async def mock_calculate_indicators(config, symbol):
        return {"atr_14": 400.0}
    
    engine._calculate_indicators = mock_calculate_indicators
    
    # Trigger entry at 50000 (for short position, entry signal is 'sell')
    await engine.process_market_data(create_market_data(50000.0))
    
    # Verify entry signal is 'sell' for short position
    assert len(signals) == 1
    assert signals[0].side == "sell"
    
    state = engine.get_strategy_state("short_atr_strategy")
    state.entry_price = 50000.0
    
    # For short position: stop loss = 50000 + (400 * 2) = 50800
    # Price rises to 51000 (above stop loss)
    await engine.process_market_data(create_market_data(51000.0))
    
    # Verify exit signal (for short position, exit signal is 'buy')
    assert len(signals) == 2
    exit_signal = signals[1]
    assert exit_signal.side == "buy"  # Buy to close short
    assert "stop loss" in exit_signal.reason.lower()
    assert "51000.00" in exit_signal.reason
    assert "50800.00" in exit_signal.reason


@pytest.mark.asyncio
async def test_entry_atr_independent_across_strategies(strategy_engine_with_callback, indicator_calculator):
    """
    Integration test: Multiple strategies maintain independent entry_atr values.
    
    Tests that when multiple strategies are running, each maintains its own
    entry_atr value independently.
    """
    engine, signals = strategy_engine_with_callback
    
    # Create two strategies with different symbols
    config1 = StrategyConfig(
        name="btc_strategy",
        symbol="BTC/USD",
        timeframes=["1m"],
        position_direction="long",
        position_size=1.0,
        max_position_size=10.0,
        indicators={
            "atr_14": IndicatorConfig(
                type="atr",
                timeframe="1m",
                period=14
            )
        },
        entry_conditions=[
            EntryCondition(
                type="greater_than",
                indicator="atr_14",
                value=100.0
            )
        ],
        exit_conditions=[
            AtrPercentChangeCondition(
                type="atr_percent_change",
                atr_indicator="atr_14",
                percent_change=50.0,
                direction="increase"
            )
        ]
    )
    
    config2 = StrategyConfig(
        name="eth_strategy",
        symbol="ETH/USD",
        timeframes=["1m"],
        position_direction="long",
        position_size=1.0,
        max_position_size=10.0,
        indicators={
            "atr_14": IndicatorConfig(
                type="atr",
                timeframe="1m",
                period=14
            )
        },
        entry_conditions=[
            EntryCondition(
                type="greater_than",
                indicator="atr_14",
                value=50.0
            )
        ],
        exit_conditions=[
            AtrPercentChangeCondition(
                type="atr_percent_change",
                atr_indicator="atr_14",
                percent_change=50.0,
                direction="increase"
            )
        ]
    )
    
    # Register both strategies
    await engine.register_strategy(config1)
    await engine.register_strategy(config2)
    
    # Mock indicator calculator
    indicator_calculator.add_market_data = AsyncMock()
    
    # Mock different ATR values for each symbol
    async def mock_calculate_indicators(config, symbol):
        if symbol == "BTC/USD":
            return {"atr_14": 500.0}
        elif symbol == "ETH/USD":
            return {"atr_14": 100.0}
        return {}
    
    engine._calculate_indicators = mock_calculate_indicators
    
    # Trigger entries for both strategies
    btc_data = MarketData(
        symbol="BTC/USD",
        timestamp=datetime.now(),
        open=50000.0,
        high=50100.0,
        low=49900.0,
        close=50000.0,
        volume=100.0
    )
    
    eth_data = MarketData(
        symbol="ETH/USD",
        timestamp=datetime.now(),
        open=3000.0,
        high=3100.0,
        low=2900.0,
        close=3000.0,
        volume=100.0
    )
    
    await engine.process_market_data(btc_data)
    await engine.process_market_data(eth_data)
    
    # Verify both entered with independent entry_atr values
    btc_state = engine.get_strategy_state("btc_strategy")
    eth_state = engine.get_strategy_state("eth_strategy")
    
    assert btc_state.entry_atr == 500.0
    assert eth_state.entry_atr == 100.0
    assert btc_state.entry_atr != eth_state.entry_atr
