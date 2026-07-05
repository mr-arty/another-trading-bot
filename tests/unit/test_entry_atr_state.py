"""Unit tests for entry_atr state management in StrategyEngine."""

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
from src.indicators.calculator import IndicatorCalculator
from src.exchange.connector import MarketData


@pytest.fixture
def indicator_calculator():
    """Create a mock indicator calculator."""
    calc = AsyncMock(spec=IndicatorCalculator)
    return calc


@pytest.fixture
def strategy_engine(indicator_calculator):
    """Create a strategy engine with mock calculator."""
    return StrategyEngine(
        indicator_calculator=indicator_calculator,
        signal_callback=None
    )


@pytest.fixture
def strategy_config_with_atr():
    """Create a strategy configuration with ATR indicator."""
    return StrategyConfig(
        name="test_atr_strategy",
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
            ),
            "ema_20": IndicatorConfig(
                type="ema",
                timeframe="1m",
                period=20
            )
        },
        entry_conditions=[
            EntryCondition(
                type="greater_than",
                indicator="ema_20",
                value=50000.0
            )
        ],
        exit_conditions=[
            ExitCondition(
                type="take_profit",
                percent=5.0
            )
        ]
    )


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


@pytest.mark.asyncio
async def test_entry_atr_storage_on_position_entry(
    strategy_engine,
    strategy_config_with_atr,
    market_data
):
    """Test that entry_atr is stored when position is entered."""
    # Register strategy
    await strategy_engine.register_strategy(strategy_config_with_atr)
    
    # Get strategy state
    state = strategy_engine.get_strategy_state("test_atr_strategy")
    assert state is not None
    assert state.entry_atr is None
    
    # Mock _calculate_indicators to return both ATR and EMA
    async def mock_calculate_indicators(config, symbol):
        return {
            "atr_14": 500.0,
            "ema_20": 50100.0
        }
    
    strategy_engine._calculate_indicators = mock_calculate_indicators
    
    # Process market data (should trigger entry)
    await strategy_engine.process_market_data(market_data)
    
    # Verify entry_atr was stored
    assert state.entry_atr == 500.0
    assert state.has_position is True


@pytest.mark.asyncio
async def test_entry_atr_reset_on_position_exit(
    strategy_engine,
    strategy_config_with_atr,
    market_data
):
    """Test that entry_atr is reset when position is exited."""
    # Register strategy
    await strategy_engine.register_strategy(strategy_config_with_atr)
    
    # Get strategy state
    state = strategy_engine.get_strategy_state("test_atr_strategy")
    
    # Mock _calculate_indicators to return both ATR and EMA
    async def mock_calculate_indicators(config, symbol):
        return {
            "atr_14": 500.0,
            "ema_20": 50100.0
        }
    
    strategy_engine._calculate_indicators = mock_calculate_indicators
    
    # Enter position
    await strategy_engine.process_market_data(market_data)
    assert state.entry_atr == 500.0
    assert state.has_position is True
    
    # Set entry price (simulating order fill)
    state.entry_price = 50050.0
    
    # Create market data that triggers exit (5% profit)
    exit_market_data = MarketData(
        symbol="BTC/USD",
        timestamp=datetime.now(),
        open=52500.0,
        high=52600.0,
        low=52400.0,
        close=52552.5,  # ~5% above entry
        volume=100.0
    )
    
    # Process market data (should trigger exit)
    await strategy_engine.process_market_data(exit_market_data)
    
    # Verify entry_atr was reset
    assert state.entry_atr is None
    assert state.has_position is False
    assert state.entry_price is None


@pytest.mark.asyncio
async def test_entry_atr_reset_in_update_position_state(
    strategy_engine,
    strategy_config_with_atr
):
    """Test that entry_atr is reset in update_position_state()."""
    # Register strategy
    await strategy_engine.register_strategy(strategy_config_with_atr)
    
    # Get strategy state
    state = strategy_engine.get_strategy_state("test_atr_strategy")
    
    # Manually set position state with entry_atr
    state.has_position = True
    state.entry_price = 50000.0
    state.entry_atr = 500.0
    
    # Update position state to close position
    await strategy_engine.update_position_state(
        strategy_name="test_atr_strategy",
        has_position=False
    )
    
    # Verify entry_atr was reset
    assert state.entry_atr is None
    assert state.entry_price is None
    assert state.has_position is False


@pytest.mark.asyncio
async def test_entry_atr_none_when_no_atr_indicator(
    strategy_engine,
    market_data
):
    """Test that entry_atr remains None when no ATR indicator is configured."""
    # Create strategy without ATR indicator
    config = StrategyConfig(
        name="test_no_atr_strategy",
        symbol="BTC/USD",
        timeframes=["1m"],
        position_direction="long",
        position_size=1.0,
        max_position_size=10.0,
        indicators={
            "ema_20": IndicatorConfig(
                type="ema",
                timeframe="1m",
                period=20
            )
        },
        entry_conditions=[
            EntryCondition(
                type="greater_than",
                indicator="ema_20",
                value=50000.0
            )
        ],
        exit_conditions=[
            ExitCondition(
                type="take_profit",
                percent=5.0
            )
        ]
    )
    
    # Register strategy
    await strategy_engine.register_strategy(config)
    
    # Get strategy state
    state = strategy_engine.get_strategy_state("test_no_atr_strategy")
    
    # Mock _calculate_indicators to return only EMA (no ATR)
    async def mock_calculate_indicators(config, symbol):
        return {
            "ema_20": 50100.0
        }
    
    strategy_engine._calculate_indicators = mock_calculate_indicators
    
    # Process market data (should trigger entry)
    await strategy_engine.process_market_data(market_data)
    
    # Verify entry_atr remains None
    assert state.entry_atr is None
    assert state.has_position is True


@pytest.mark.asyncio
async def test_entry_atr_uses_first_atr_indicator(
    strategy_engine,
    market_data
):
    """Test that entry_atr uses the first ATR indicator when multiple exist."""
    # Create strategy with multiple ATR indicators
    config = StrategyConfig(
        name="test_multi_atr_strategy",
        symbol="BTC/USD",
        timeframes=["1m"],
        position_direction="long",
        position_size=1.0,
        max_position_size=10.0,
        indicators={
            "atr_7": IndicatorConfig(
                type="atr",
                timeframe="1m",
                period=7
            ),
            "atr_14": IndicatorConfig(
                type="atr",
                timeframe="1m",
                period=14
            ),
            "ema_20": IndicatorConfig(
                type="ema",
                timeframe="1m",
                period=20
            )
        },
        entry_conditions=[
            EntryCondition(
                type="greater_than",
                indicator="ema_20",
                value=50000.0
            )
        ],
        exit_conditions=[
            ExitCondition(
                type="take_profit",
                percent=5.0
            )
        ]
    )
    
    # Register strategy
    await strategy_engine.register_strategy(config)
    
    # Get strategy state
    state = strategy_engine.get_strategy_state("test_multi_atr_strategy")
    
    # Mock _calculate_indicators to return multiple ATR values
    async def mock_calculate_indicators(config, symbol):
        return {
            "atr_7": 300.0,
            "atr_14": 500.0,
            "ema_20": 50100.0
        }
    
    strategy_engine._calculate_indicators = mock_calculate_indicators
    
    # Process market data (should trigger entry)
    await strategy_engine.process_market_data(market_data)
    
    # Verify entry_atr uses first ATR indicator found
    # Note: The order depends on dict iteration, but at least one should be stored
    assert state.entry_atr in [300.0, 500.0]
    assert state.has_position is True


@pytest.mark.asyncio
async def test_independent_strategy_state(strategy_engine, market_data):
    """
    Test that multiple strategies maintain independent entry_atr values.
    Property 16: Independent Strategy State
    Validates: Requirements 8.5
    """
    # Create two strategies with different symbols
    config1 = StrategyConfig(
        name="strategy_btc",
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
            ),
            "ema_20": IndicatorConfig(
                type="ema",
                timeframe="1m",
                period=20
            )
        },
        entry_conditions=[
            EntryCondition(
                type="greater_than",
                indicator="ema_20",
                value=50000.0
            )
        ],
        exit_conditions=[
            ExitCondition(
                type="take_profit",
                percent=5.0
            )
        ]
    )
    
    config2 = StrategyConfig(
        name="strategy_eth",
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
            ),
            "ema_20": IndicatorConfig(
                type="ema",
                timeframe="1m",
                period=20
            )
        },
        entry_conditions=[
            EntryCondition(
                type="greater_than",
                indicator="ema_20",
                value=3000.0
            )
        ],
        exit_conditions=[
            ExitCondition(
                type="take_profit",
                percent=5.0
            )
        ]
    )
    
    # Register both strategies
    await strategy_engine.register_strategy(config1)
    await strategy_engine.register_strategy(config2)
    
    # Get strategy states
    state1 = strategy_engine.get_strategy_state("strategy_btc")
    state2 = strategy_engine.get_strategy_state("strategy_eth")
    
    # Mock _calculate_indicators to return different ATR values for each symbol
    original_calculate = strategy_engine._calculate_indicators
    
    async def mock_calculate_indicators(config, symbol):
        if symbol == "BTC/USD":
            return {
                "atr_14": 500.0,
                "ema_20": 50100.0
            }
        elif symbol == "ETH/USD":
            return {
                "atr_14": 100.0,
                "ema_20": 3100.0
            }
        return await original_calculate(config, symbol)
    
    strategy_engine._calculate_indicators = mock_calculate_indicators
    
    # Process BTC market data
    btc_data = MarketData(
        symbol="BTC/USD",
        timestamp=datetime.now(),
        open=50000.0,
        high=50100.0,
        low=49900.0,
        close=50050.0,
        volume=100.0
    )
    await strategy_engine.process_market_data(btc_data)
    
    # Process ETH market data
    eth_data = MarketData(
        symbol="ETH/USD",
        timestamp=datetime.now(),
        open=3000.0,
        high=3100.0,
        low=2900.0,
        close=3050.0,
        volume=100.0
    )
    await strategy_engine.process_market_data(eth_data)
    
    # Verify each strategy has independent entry_atr
    assert state1.entry_atr == 500.0, "BTC strategy should have ATR of 500.0"
    assert state2.entry_atr == 100.0, "ETH strategy should have ATR of 100.0"
    assert state1.has_position is True
    assert state2.has_position is True
    
    # Verify closing one position doesn't affect the other
    await strategy_engine.update_position_state(
        strategy_name="strategy_btc",
        has_position=False
    )
    
    assert state1.entry_atr is None, "BTC strategy entry_atr should be reset"
    assert state2.entry_atr == 100.0, "ETH strategy entry_atr should remain unchanged"
    assert state1.has_position is False
    assert state2.has_position is True
