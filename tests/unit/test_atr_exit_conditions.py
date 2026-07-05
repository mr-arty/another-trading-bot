"""Unit tests for ATR exit condition evaluation in StrategyEngine."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock

from src.strategy.engine import StrategyEngine, StrategyState
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
def strategy_engine(indicator_calculator):
    """Create a strategy engine with mock calculator."""
    return StrategyEngine(
        indicator_calculator=indicator_calculator,
        signal_callback=None
    )


@pytest.fixture
def base_strategy_config():
    """Create a base strategy configuration."""
    return StrategyConfig(
        name="test_strategy",
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
                threshold=1000.0,
                direction="above"
            )
        ]
    )


@pytest.fixture
def strategy_state(base_strategy_config):
    """Create a strategy state with entry values."""
    state = StrategyState(config=base_strategy_config)
    state.has_position = True
    state.entry_price = 50000.0
    state.entry_atr = 400.0
    state.entry_time = datetime.now()
    return state


@pytest.fixture
def market_data():
    """Create sample market data."""
    return MarketData(
        symbol="BTC/USD",
        timestamp=datetime.now(),
        open=50000.0,
        high=50100.0,
        low=49900.0,
        close=50050.0,
        volume=100.0
    )


# ATR Threshold Tests

@pytest.mark.asyncio
async def test_atr_threshold_above_met(strategy_engine):
    """Test ATR threshold above condition when met."""
    condition = AtrThresholdCondition(
        type="atr_threshold",
        atr_indicator="atr_14",
        threshold=500.0,
        direction="above"
    )
    
    indicators = {"atr_14": 600.0}
    
    met, reason = await strategy_engine._evaluate_atr_threshold(condition, indicators)
    
    assert met is True
    assert "600.00" in reason
    assert ">" in reason
    assert "500.00" in reason


@pytest.mark.asyncio
async def test_atr_threshold_above_not_met(strategy_engine):
    """Test ATR threshold above condition when not met."""
    condition = AtrThresholdCondition(
        type="atr_threshold",
        atr_indicator="atr_14",
        threshold=500.0,
        direction="above"
    )
    
    indicators = {"atr_14": 400.0}
    
    met, reason = await strategy_engine._evaluate_atr_threshold(condition, indicators)
    
    assert met is False
    assert "400.00" in reason
    assert "500.00" in reason


@pytest.mark.asyncio
async def test_atr_threshold_below_met(strategy_engine):
    """Test ATR threshold below condition when met."""
    condition = AtrThresholdCondition(
        type="atr_threshold",
        atr_indicator="atr_14",
        threshold=500.0,
        direction="below"
    )
    
    indicators = {"atr_14": 400.0}
    
    met, reason = await strategy_engine._evaluate_atr_threshold(condition, indicators)
    
    assert met is True
    assert "400.00" in reason
    assert "<" in reason
    assert "500.00" in reason


@pytest.mark.asyncio
async def test_atr_threshold_below_not_met(strategy_engine):
    """Test ATR threshold below condition when not met."""
    condition = AtrThresholdCondition(
        type="atr_threshold",
        atr_indicator="atr_14",
        threshold=500.0,
        direction="below"
    )
    
    indicators = {"atr_14": 600.0}
    
    met, reason = await strategy_engine._evaluate_atr_threshold(condition, indicators)
    
    assert met is False
    assert "600.00" in reason
    assert "500.00" in reason


@pytest.mark.asyncio
async def test_atr_threshold_missing_atr(strategy_engine):
    """Test ATR threshold condition with missing ATR value."""
    condition = AtrThresholdCondition(
        type="atr_threshold",
        atr_indicator="atr_14",
        threshold=500.0,
        direction="above"
    )
    
    indicators = {}  # No ATR value
    
    met, reason = await strategy_engine._evaluate_atr_threshold(condition, indicators)
    
    assert met is False
    assert reason == ""


# ATR Stop Loss Tests

@pytest.mark.asyncio
async def test_atr_stop_loss_long_position_triggered(strategy_engine, strategy_state, market_data):
    """Test ATR stop loss for long position when triggered."""
    condition = AtrStopLossCondition(
        type="atr_stop_loss",
        atr_indicator="atr_14",
        multiplier=2.0
    )
    
    # Current ATR = 400, multiplier = 2.0
    # Stop loss = 50000 - (400 * 2) = 49200
    # Current price = 49000 (below stop loss)
    indicators = {"atr_14": 400.0}
    market_data.close = 49000.0
    
    met, reason = await strategy_engine._evaluate_atr_stop_loss(
        condition, strategy_state, market_data.close, indicators
    )
    
    assert met is True
    assert "49000.00" in reason
    assert "49200.00" in reason
    assert "stop loss" in reason.lower()


@pytest.mark.asyncio
async def test_atr_stop_loss_long_position_not_triggered(strategy_engine, strategy_state, market_data):
    """Test ATR stop loss for long position when not triggered."""
    condition = AtrStopLossCondition(
        type="atr_stop_loss",
        atr_indicator="atr_14",
        multiplier=2.0
    )
    
    # Current ATR = 400, multiplier = 2.0
    # Stop loss = 50000 - (400 * 2) = 49200
    # Current price = 49500 (above stop loss)
    indicators = {"atr_14": 400.0}
    market_data.close = 49500.0
    
    met, reason = await strategy_engine._evaluate_atr_stop_loss(
        condition, strategy_state, market_data.close, indicators
    )
    
    assert met is False
    assert "49500.00" in reason
    assert "49200.00" in reason


@pytest.mark.asyncio
async def test_atr_stop_loss_short_position_triggered(strategy_engine, strategy_state, market_data):
    """Test ATR stop loss for short position when triggered."""
    # Change to short position
    strategy_state.config.position_direction = "short"
    
    condition = AtrStopLossCondition(
        type="atr_stop_loss",
        atr_indicator="atr_14",
        multiplier=2.0
    )
    
    # Current ATR = 400, multiplier = 2.0
    # Stop loss = 50000 + (400 * 2) = 50800
    # Current price = 51000 (above stop loss)
    indicators = {"atr_14": 400.0}
    market_data.close = 51000.0
    
    met, reason = await strategy_engine._evaluate_atr_stop_loss(
        condition, strategy_state, market_data.close, indicators
    )
    
    assert met is True
    assert "51000.00" in reason
    assert "50800.00" in reason


@pytest.mark.asyncio
async def test_atr_stop_loss_short_position_not_triggered(strategy_engine, strategy_state, market_data):
    """Test ATR stop loss for short position when not triggered."""
    # Change to short position
    strategy_state.config.position_direction = "short"
    
    condition = AtrStopLossCondition(
        type="atr_stop_loss",
        atr_indicator="atr_14",
        multiplier=2.0
    )
    
    # Current ATR = 400, multiplier = 2.0
    # Stop loss = 50000 + (400 * 2) = 50800
    # Current price = 50500 (below stop loss)
    indicators = {"atr_14": 400.0}
    market_data.close = 50500.0
    
    met, reason = await strategy_engine._evaluate_atr_stop_loss(
        condition, strategy_state, market_data.close, indicators
    )
    
    assert met is False
    assert "50500.00" in reason
    assert "50800.00" in reason


@pytest.mark.asyncio
async def test_atr_stop_loss_no_entry_price(strategy_engine, strategy_state, market_data):
    """Test ATR stop loss with no entry price."""
    strategy_state.entry_price = None
    
    condition = AtrStopLossCondition(
        type="atr_stop_loss",
        atr_indicator="atr_14",
        multiplier=2.0
    )
    
    indicators = {"atr_14": 400.0}
    
    met, reason = await strategy_engine._evaluate_atr_stop_loss(
        condition, strategy_state, market_data.close, indicators
    )
    
    assert met is False
    assert reason == ""


@pytest.mark.asyncio
async def test_atr_stop_loss_missing_atr(strategy_engine, strategy_state, market_data):
    """Test ATR stop loss with missing ATR value."""
    condition = AtrStopLossCondition(
        type="atr_stop_loss",
        atr_indicator="atr_14",
        multiplier=2.0
    )
    
    indicators = {}  # No ATR value
    
    met, reason = await strategy_engine._evaluate_atr_stop_loss(
        condition, strategy_state, market_data.close, indicators
    )
    
    assert met is False
    assert reason == ""


# ATR Percent Change Tests

@pytest.mark.asyncio
async def test_atr_percent_increase_met(strategy_engine, strategy_state):
    """Test ATR percent increase condition when met."""
    condition = AtrPercentChangeCondition(
        type="atr_percent_change",
        atr_indicator="atr_14",
        percent_change=50.0,
        direction="increase"
    )
    
    # Entry ATR = 400, Current ATR = 650
    # Increase = (650 - 400) / 400 * 100 = 62.5%
    indicators = {"atr_14": 650.0}
    
    met, reason = await strategy_engine._evaluate_atr_percent_change(
        condition, strategy_state, indicators
    )
    
    assert met is True
    assert "62.5" in reason or "62.50" in reason
    assert "400.00" in reason
    assert "650.00" in reason


@pytest.mark.asyncio
async def test_atr_percent_increase_not_met(strategy_engine, strategy_state):
    """Test ATR percent increase condition when not met."""
    condition = AtrPercentChangeCondition(
        type="atr_percent_change",
        atr_indicator="atr_14",
        percent_change=50.0,
        direction="increase"
    )
    
    # Entry ATR = 400, Current ATR = 500
    # Increase = (500 - 400) / 400 * 100 = 25%
    indicators = {"atr_14": 500.0}
    
    met, reason = await strategy_engine._evaluate_atr_percent_change(
        condition, strategy_state, indicators
    )
    
    assert met is False
    assert "25" in reason
    assert "400.00" in reason
    assert "500.00" in reason


@pytest.mark.asyncio
async def test_atr_percent_decrease_met(strategy_engine, strategy_state):
    """Test ATR percent decrease condition when met."""
    condition = AtrPercentChangeCondition(
        type="atr_percent_change",
        atr_indicator="atr_14",
        percent_change=50.0,
        direction="decrease"
    )
    
    # Entry ATR = 400, Current ATR = 150
    # Decrease = (400 - 150) / 400 * 100 = 62.5%
    indicators = {"atr_14": 150.0}
    
    met, reason = await strategy_engine._evaluate_atr_percent_change(
        condition, strategy_state, indicators
    )
    
    assert met is True
    assert "62.5" in reason or "62.50" in reason
    assert "400.00" in reason
    assert "150.00" in reason


@pytest.mark.asyncio
async def test_atr_percent_decrease_not_met(strategy_engine, strategy_state):
    """Test ATR percent decrease condition when not met."""
    condition = AtrPercentChangeCondition(
        type="atr_percent_change",
        atr_indicator="atr_14",
        percent_change=50.0,
        direction="decrease"
    )
    
    # Entry ATR = 400, Current ATR = 300
    # Decrease = (400 - 300) / 400 * 100 = 25%
    indicators = {"atr_14": 300.0}
    
    met, reason = await strategy_engine._evaluate_atr_percent_change(
        condition, strategy_state, indicators
    )
    
    assert met is False
    assert "25" in reason
    assert "400.00" in reason
    assert "300.00" in reason


@pytest.mark.asyncio
async def test_atr_percent_change_no_entry_atr(strategy_engine, strategy_state):
    """Test ATR percent change with no entry_atr."""
    strategy_state.entry_atr = None
    
    condition = AtrPercentChangeCondition(
        type="atr_percent_change",
        atr_indicator="atr_14",
        percent_change=50.0,
        direction="increase"
    )
    
    indicators = {"atr_14": 500.0}
    
    met, reason = await strategy_engine._evaluate_atr_percent_change(
        condition, strategy_state, indicators
    )
    
    assert met is False
    assert reason == ""


@pytest.mark.asyncio
async def test_atr_percent_change_zero_entry_atr(strategy_engine, strategy_state):
    """Test ATR percent change with zero entry_atr."""
    strategy_state.entry_atr = 0.0
    
    condition = AtrPercentChangeCondition(
        type="atr_percent_change",
        atr_indicator="atr_14",
        percent_change=50.0,
        direction="increase"
    )
    
    indicators = {"atr_14": 500.0}
    
    met, reason = await strategy_engine._evaluate_atr_percent_change(
        condition, strategy_state, indicators
    )
    
    assert met is False
    assert reason == ""


@pytest.mark.asyncio
async def test_atr_percent_change_missing_atr(strategy_engine, strategy_state):
    """Test ATR percent change with missing ATR value."""
    condition = AtrPercentChangeCondition(
        type="atr_percent_change",
        atr_indicator="atr_14",
        percent_change=50.0,
        direction="increase"
    )
    
    indicators = {}  # No ATR value
    
    met, reason = await strategy_engine._evaluate_atr_percent_change(
        condition, strategy_state, indicators
    )
    
    assert met is False
    assert reason == ""


# Integration Tests with _evaluate_exit_condition

@pytest.mark.asyncio
async def test_evaluate_exit_condition_atr_threshold(strategy_engine, strategy_state, market_data):
    """Test _evaluate_exit_condition with AtrThresholdCondition."""
    condition = AtrThresholdCondition(
        type="atr_threshold",
        atr_indicator="atr_14",
        threshold=500.0,
        direction="above"
    )
    
    indicators = {"atr_14": 600.0}
    
    met, reason = await strategy_engine._evaluate_exit_condition(
        condition, strategy_state, market_data, indicators
    )
    
    assert met is True
    assert "600.00" in reason


@pytest.mark.asyncio
async def test_evaluate_exit_condition_atr_stop_loss(strategy_engine, strategy_state, market_data):
    """Test _evaluate_exit_condition with AtrStopLossCondition."""
    condition = AtrStopLossCondition(
        type="atr_stop_loss",
        atr_indicator="atr_14",
        multiplier=2.0
    )
    
    indicators = {"atr_14": 400.0}
    market_data.close = 49000.0
    
    met, reason = await strategy_engine._evaluate_exit_condition(
        condition, strategy_state, market_data, indicators
    )
    
    assert met is True
    assert "stop loss" in reason.lower()


@pytest.mark.asyncio
async def test_evaluate_exit_condition_atr_percent_change(strategy_engine, strategy_state, market_data):
    """Test _evaluate_exit_condition with AtrPercentChangeCondition."""
    condition = AtrPercentChangeCondition(
        type="atr_percent_change",
        atr_indicator="atr_14",
        percent_change=50.0,
        direction="increase"
    )
    
    indicators = {"atr_14": 650.0}
    
    met, reason = await strategy_engine._evaluate_exit_condition(
        condition, strategy_state, market_data, indicators
    )
    
    assert met is True
    assert "increased" in reason.lower()
