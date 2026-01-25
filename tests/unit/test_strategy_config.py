"""Unit tests for strategy configuration loading."""

import pytest
from pathlib import Path
from src.strategy.config import (
    StrategyConfig,
    IndicatorConfig,
    EntryCondition,
    ExitCondition,
    load_strategy_from_yaml
)


def test_load_example_strategy():
    """Test loading the example strategy file."""
    strategy_path = Path("example_strategy.yaml")
    
    if not strategy_path.exists():
        pytest.skip("example_strategy.yaml not found")
    
    strategy = load_strategy_from_yaml(strategy_path)
    
    # Verify basic fields
    assert strategy.name == "btc_multi_timeframe_momentum"
    assert strategy.symbol == "BTCUSDT"
    assert strategy.position_size == 0.01
    assert strategy.max_position_size == 0.05
    
    # Verify timeframes
    assert "5m" in strategy.timeframes
    assert "30m" in strategy.timeframes
    
    # Verify indicators
    assert "rsi_5m" in strategy.indicators
    assert "rsi_30m" in strategy.indicators
    assert "ema_fast_30m" in strategy.indicators
    assert "ema_slow_30m" in strategy.indicators
    
    # Verify RSI indicator
    rsi_5m = strategy.indicators["rsi_5m"]
    assert rsi_5m.type == "rsi"
    assert rsi_5m.timeframe == "5m"
    assert rsi_5m.period == 14
    assert rsi_5m.oversold == 30
    assert rsi_5m.overbought == 70
    
    # Verify EMA indicator
    ema_fast = strategy.indicators["ema_fast_30m"]
    assert ema_fast.type == "ema"
    assert ema_fast.timeframe == "30m"
    assert ema_fast.period == 17
    
    # Verify entry conditions
    assert len(strategy.entry_conditions) == 3
    
    # Check less_than condition
    less_than_conditions = [c for c in strategy.entry_conditions if c.type == "less_than"]
    assert len(less_than_conditions) == 2
    
    # Check cross_above condition
    cross_conditions = [c for c in strategy.entry_conditions if c.type == "cross_above"]
    assert len(cross_conditions) == 1
    assert cross_conditions[0].indicator1 == "ema_fast_30m"
    assert cross_conditions[0].indicator2 == "ema_slow_30m"
    
    # Verify exit conditions
    assert len(strategy.exit_conditions) == 5
    
    # Check take_profit
    take_profit = [c for c in strategy.exit_conditions if c.type == "take_profit"]
    assert len(take_profit) == 1
    assert take_profit[0].percent == 4.0
    
    # Check stop_loss
    stop_loss = [c for c in strategy.exit_conditions if c.type == "stop_loss"]
    assert len(stop_loss) == 1
    assert stop_loss[0].percent == 1.0
    
    # Check time_exceeds
    time_exceeds = [c for c in strategy.exit_conditions if c.type == "time_exceeds"]
    assert len(time_exceeds) == 1
    assert time_exceeds[0].seconds == 7200
    
    # Check support_resistance
    support = [c for c in strategy.exit_conditions if c.type == "support_resistance"]
    assert len(support) == 1
    assert support[0].price == 42000.0
    assert support[0].direction == "below"
    
    # Check end_of_day
    eod = [c for c in strategy.exit_conditions if c.type == "end_of_day"]
    assert len(eod) == 1
    assert eod[0].time_utc == "00:00"
    
    # Verify risk parameters
    assert strategy.risk_parameters is not None
    assert strategy.risk_parameters.max_trades_per_day == 5
    assert strategy.risk_parameters.cooldown_after_loss == 3600


def test_invalid_yaml_file():
    """Test that invalid YAML files raise appropriate errors."""
    invalid_path = Path("nonexistent_strategy.yaml")
    
    with pytest.raises(FileNotFoundError):
        load_strategy_from_yaml(invalid_path)


def test_strategy_validation_missing_name():
    """Test that strategies without names fail validation."""
    with pytest.raises(ValueError, match="Strategy name is required"):
        StrategyConfig(
            name="",
            symbol="BTCUSDT",
            timeframes=["5m"],
            indicators={"rsi": IndicatorConfig(type="rsi", timeframe="5m", period=14)},
            entry_conditions=[EntryCondition(type="less_than", indicator="rsi", value=30)],
            exit_conditions=[ExitCondition(type="take_profit", percent=2.0)],
            position_size=0.01,
            max_position_size=0.05
        )


def test_strategy_validation_invalid_timeframe():
    """Test that invalid timeframes fail validation."""
    with pytest.raises(ValueError, match="Invalid timeframe"):
        StrategyConfig(
            name="test",
            symbol="BTCUSDT",
            timeframes=["invalid"],
            indicators={"rsi": IndicatorConfig(type="rsi", timeframe="5m", period=14)},
            entry_conditions=[EntryCondition(type="less_than", indicator="rsi", value=30)],
            exit_conditions=[ExitCondition(type="take_profit", percent=2.0)],
            position_size=0.01,
            max_position_size=0.05
        )


def test_strategy_validation_invalid_position_size():
    """Test that invalid position sizes fail validation."""
    with pytest.raises(ValueError, match="position_size must be positive"):
        StrategyConfig(
            name="test",
            symbol="BTCUSDT",
            timeframes=["5m"],
            indicators={"rsi": IndicatorConfig(type="rsi", timeframe="5m", period=14)},
            entry_conditions=[EntryCondition(type="less_than", indicator="rsi", value=30)],
            exit_conditions=[ExitCondition(type="take_profit", percent=2.0)],
            position_size=-0.01,
            max_position_size=0.05
        )


def test_entry_condition_validation_missing_indicator():
    """Test that entry conditions without required fields fail validation."""
    with pytest.raises(ValueError, match="indicator.*required"):
        StrategyConfig(
            name="test",
            symbol="BTCUSDT",
            timeframes=["5m"],
            indicators={"rsi": IndicatorConfig(type="rsi", timeframe="5m", period=14)},
            entry_conditions=[EntryCondition(type="less_than", value=30)],  # Missing indicator
            exit_conditions=[ExitCondition(type="take_profit", percent=2.0)],
            position_size=0.01,
            max_position_size=0.05
        )


def test_exit_condition_validation_missing_percent():
    """Test that exit conditions without required fields fail validation."""
    with pytest.raises(ValueError, match="percent.*required"):
        StrategyConfig(
            name="test",
            symbol="BTCUSDT",
            timeframes=["5m"],
            indicators={"rsi": IndicatorConfig(type="rsi", timeframe="5m", period=14)},
            entry_conditions=[EntryCondition(type="less_than", indicator="rsi", value=30)],
            exit_conditions=[ExitCondition(type="take_profit")],  # Missing percent
            position_size=0.01,
            max_position_size=0.05
        )


def test_indicator_validation_invalid_type():
    """Test that indicators with invalid types fail validation."""
    with pytest.raises(ValueError, match="type must be one of"):
        StrategyConfig(
            name="test",
            symbol="BTCUSDT",
            timeframes=["5m"],
            indicators={"invalid": IndicatorConfig(type="invalid", timeframe="5m", period=14)},
            entry_conditions=[EntryCondition(type="less_than", indicator="invalid", value=30)],
            exit_conditions=[ExitCondition(type="take_profit", percent=2.0)],
            position_size=0.01,
            max_position_size=0.05
        )
