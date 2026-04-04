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


def test_resistance_greater_than_support_validation():
    """Test that resistance_level must be greater than support_level."""
    # Valid case: resistance > support
    config = StrategyConfig(
        name="test_range",
        symbol="BTCUSDT",
        timeframes=["4h"],
        indicators={"rsi": IndicatorConfig(type="rsi", timeframe="4h", period=14)},
        entry_conditions=[EntryCondition(type="less_than", indicator="rsi", value=30)],
        exit_conditions=[ExitCondition(type="take_profit", percent=2.0)],
        position_size=0.01,
        max_position_size=0.05,
        support_level=68000.0,
        resistance_level=72000.0
    )
    assert config.support_level == 68000.0
    assert config.resistance_level == 72000.0
    
    # Invalid case: resistance <= support
    with pytest.raises(ValueError, match="resistance_level.*must be greater than.*support_level"):
        StrategyConfig(
            name="test_range",
            symbol="BTCUSDT",
            timeframes=["4h"],
            indicators={"rsi": IndicatorConfig(type="rsi", timeframe="4h", period=14)},
            entry_conditions=[EntryCondition(type="less_than", indicator="rsi", value=30)],
            exit_conditions=[ExitCondition(type="take_profit", percent=2.0)],
            position_size=0.01,
            max_position_size=0.05,
            support_level=72000.0,
            resistance_level=68000.0
        )
    
    # Invalid case: resistance == support
    with pytest.raises(ValueError, match="resistance_level.*must be greater than.*support_level"):
        StrategyConfig(
            name="test_range",
            symbol="BTCUSDT",
            timeframes=["4h"],
            indicators={"rsi": IndicatorConfig(type="rsi", timeframe="4h", period=14)},
            entry_conditions=[EntryCondition(type="less_than", indicator="rsi", value=30)],
            exit_conditions=[ExitCondition(type="take_profit", percent=2.0)],
            position_size=0.01,
            max_position_size=0.05,
            support_level=70000.0,
            resistance_level=70000.0
        )


def test_support_resistance_must_be_positive():
    """Test that support_level and resistance_level must be positive."""
    # Invalid case: negative support_level
    with pytest.raises(ValueError, match="support_level must be positive"):
        StrategyConfig(
            name="test_range",
            symbol="BTCUSDT",
            timeframes=["4h"],
            indicators={"rsi": IndicatorConfig(type="rsi", timeframe="4h", period=14)},
            entry_conditions=[EntryCondition(type="less_than", indicator="rsi", value=30)],
            exit_conditions=[ExitCondition(type="take_profit", percent=2.0)],
            position_size=0.01,
            max_position_size=0.05,
            support_level=-68000.0,
            resistance_level=72000.0
        )
    
    # Invalid case: negative resistance_level
    with pytest.raises(ValueError, match="resistance_level must be positive"):
        StrategyConfig(
            name="test_range",
            symbol="BTCUSDT",
            timeframes=["4h"],
            indicators={"rsi": IndicatorConfig(type="rsi", timeframe="4h", period=14)},
            entry_conditions=[EntryCondition(type="less_than", indicator="rsi", value=30)],
            exit_conditions=[ExitCondition(type="take_profit", percent=2.0)],
            position_size=0.01,
            max_position_size=0.05,
            support_level=68000.0,
            resistance_level=-72000.0
        )
    
    # Invalid case: zero support_level
    with pytest.raises(ValueError, match="support_level must be positive"):
        StrategyConfig(
            name="test_range",
            symbol="BTCUSDT",
            timeframes=["4h"],
            indicators={"rsi": IndicatorConfig(type="rsi", timeframe="4h", period=14)},
            entry_conditions=[EntryCondition(type="less_than", indicator="rsi", value=30)],
            exit_conditions=[ExitCondition(type="take_profit", percent=2.0)],
            position_size=0.01,
            max_position_size=0.05,
            support_level=0.0,
            resistance_level=72000.0
        )
    
    # Invalid case: zero resistance_level
    with pytest.raises(ValueError, match="resistance_level must be positive"):
        StrategyConfig(
            name="test_range",
            symbol="BTCUSDT",
            timeframes=["4h"],
            indicators={"rsi": IndicatorConfig(type="rsi", timeframe="4h", period=14)},
            entry_conditions=[EntryCondition(type="less_than", indicator="rsi", value=30)],
            exit_conditions=[ExitCondition(type="take_profit", percent=2.0)],
            position_size=0.01,
            max_position_size=0.05,
            support_level=68000.0,
            resistance_level=0.0
        )


def test_range_width_percentage_calculation(caplog):
    """Test that range width percentage is calculated and logged correctly."""
    import logging
    caplog.set_level(logging.INFO)
    
    # Create config with support and resistance levels
    config = StrategyConfig(
        name="test_range",
        symbol="BTCUSDT",
        timeframes=["4h"],
        indicators={"rsi": IndicatorConfig(type="rsi", timeframe="4h", period=14)},
        entry_conditions=[EntryCondition(type="less_than", indicator="rsi", value=30)],
        exit_conditions=[ExitCondition(type="take_profit", percent=2.0)],
        position_size=0.01,
        max_position_size=0.05,
        support_level=68000.0,
        resistance_level=72000.0
    )
    
    # Calculate expected range width percentage
    expected_range_width = ((72000.0 - 68000.0) / 68000.0) * 100
    
    # Verify the calculation is correct (approximately 5.88%)
    assert abs(expected_range_width - 5.88) < 0.01
    
    # Verify that range width percentage is logged
    log_messages = [record.message for record in caplog.records]
    range_config_logs = [msg for msg in log_messages if "range_levels_configured" in msg]
    
    assert len(range_config_logs) > 0, "range_levels_configured log not found"
    
    # Verify the log contains the range width percentage
    log_msg = range_config_logs[0]
    assert "range_width_percent=5.88" in log_msg
    assert "support=68000.0" in log_msg
    assert "resistance=72000.0" in log_msg
    assert "mid_range=70000.0" in log_msg


def test_proximity_percent_validation():
    """Test that level_proximity_percent must be between 0.1 and 5.0."""
    # Valid case: proximity_percent = 0.5 (default)
    config = StrategyConfig(
        name="test_range",
        symbol="BTCUSDT",
        timeframes=["4h"],
        indicators={"rsi": IndicatorConfig(type="rsi", timeframe="4h", period=14)},
        entry_conditions=[EntryCondition(type="less_than", indicator="rsi", value=30)],
        exit_conditions=[ExitCondition(type="take_profit", percent=2.0)],
        position_size=0.01,
        max_position_size=0.05,
        support_level=68000.0,
        resistance_level=72000.0
    )
    assert config.level_proximity_percent == 0.5
    
    # Valid case: proximity_percent = 0.1 (minimum)
    config = StrategyConfig(
        name="test_range",
        symbol="BTCUSDT",
        timeframes=["4h"],
        indicators={"rsi": IndicatorConfig(type="rsi", timeframe="4h", period=14)},
        entry_conditions=[EntryCondition(type="less_than", indicator="rsi", value=30)],
        exit_conditions=[ExitCondition(type="take_profit", percent=2.0)],
        position_size=0.01,
        max_position_size=0.05,
        support_level=68000.0,
        resistance_level=72000.0,
        level_proximity_percent=0.1
    )
    assert config.level_proximity_percent == 0.1
    
    # Valid case: proximity_percent = 5.0 (maximum)
    config = StrategyConfig(
        name="test_range",
        symbol="BTCUSDT",
        timeframes=["4h"],
        indicators={"rsi": IndicatorConfig(type="rsi", timeframe="4h", period=14)},
        entry_conditions=[EntryCondition(type="less_than", indicator="rsi", value=30)],
        exit_conditions=[ExitCondition(type="take_profit", percent=2.0)],
        position_size=0.01,
        max_position_size=0.05,
        support_level=68000.0,
        resistance_level=72000.0,
        level_proximity_percent=5.0
    )
    assert config.level_proximity_percent == 5.0
    
    # Invalid case: proximity_percent < 0.1
    with pytest.raises(ValueError, match="level_proximity_percent must be between 0.1 and 5.0"):
        StrategyConfig(
            name="test_range",
            symbol="BTCUSDT",
            timeframes=["4h"],
            indicators={"rsi": IndicatorConfig(type="rsi", timeframe="4h", period=14)},
            entry_conditions=[EntryCondition(type="less_than", indicator="rsi", value=30)],
            exit_conditions=[ExitCondition(type="take_profit", percent=2.0)],
            position_size=0.01,
            max_position_size=0.05,
            support_level=68000.0,
            resistance_level=72000.0,
            level_proximity_percent=0.05
        )
    
    # Invalid case: proximity_percent > 5.0
    with pytest.raises(ValueError, match="level_proximity_percent must be between 0.1 and 5.0"):
        StrategyConfig(
            name="test_range",
            symbol="BTCUSDT",
            timeframes=["4h"],
            indicators={"rsi": IndicatorConfig(type="rsi", timeframe="4h", period=14)},
            entry_conditions=[EntryCondition(type="less_than", indicator="rsi", value=30)],
            exit_conditions=[ExitCondition(type="take_profit", percent=2.0)],
            position_size=0.01,
            max_position_size=0.05,
            support_level=68000.0,
            resistance_level=72000.0,
            level_proximity_percent=5.5
        )
    
    # Invalid case: proximity_percent = 0
    with pytest.raises(ValueError, match="level_proximity_percent must be between 0.1 and 5.0"):
        StrategyConfig(
            name="test_range",
            symbol="BTCUSDT",
            timeframes=["4h"],
            indicators={"rsi": IndicatorConfig(type="rsi", timeframe="4h", period=14)},
            entry_conditions=[EntryCondition(type="less_than", indicator="rsi", value=30)],
            exit_conditions=[ExitCondition(type="take_profit", percent=2.0)],
            position_size=0.01,
            max_position_size=0.05,
            support_level=68000.0,
            resistance_level=72000.0,
            level_proximity_percent=0.0
        )


def test_price_near_level_condition_creation():
    """Test creating PriceNearLevelCondition with valid parameters."""
    from src.strategy.config import PriceNearLevelCondition
    
    # Valid condition for support
    condition = PriceNearLevelCondition(
        type="price_near_level",
        level="support",
        description="Price near support level"
    )
    assert condition.type == "price_near_level"
    assert condition.level == "support"
    assert condition.description == "Price near support level"
    
    # Valid condition for resistance
    condition = PriceNearLevelCondition(
        type="price_near_level",
        level="resistance"
    )
    assert condition.type == "price_near_level"
    assert condition.level == "resistance"
    assert condition.description is None


def test_price_near_level_condition_invalid_type():
    """Test that PriceNearLevelCondition rejects invalid type."""
    from src.strategy.config import PriceNearLevelCondition
    
    with pytest.raises(ValueError, match="Invalid type for PriceNearLevelCondition"):
        PriceNearLevelCondition(
            type="invalid_type",
            level="support"
        )


def test_price_near_level_condition_invalid_level():
    """Test that PriceNearLevelCondition rejects invalid level values."""
    from src.strategy.config import PriceNearLevelCondition
    
    # Invalid level value
    with pytest.raises(ValueError, match="level must be 'support' or 'resistance'"):
        PriceNearLevelCondition(
            type="price_near_level",
            level="invalid"
        )
    
    # Empty level
    with pytest.raises(ValueError, match="level must be 'support' or 'resistance'"):
        PriceNearLevelCondition(
            type="price_near_level",
            level=""
        )


def test_strategy_with_price_near_level_condition():
    """Test creating a strategy with price_near_level condition."""
    from src.strategy.config import PriceNearLevelCondition
    
    config = StrategyConfig(
        name="test_range",
        symbol="BTCUSDT",
        timeframes=["4h"],
        indicators={"rsi": IndicatorConfig(type="rsi", timeframe="4h", period=14)},
        entry_conditions=[
            EntryCondition(type="less_than", indicator="rsi", value=30),
            PriceNearLevelCondition(type="price_near_level", level="support")
        ],
        exit_conditions=[ExitCondition(type="take_profit", percent=2.0)],
        position_size=0.01,
        max_position_size=0.05,
        support_level=68000.0,
        resistance_level=72000.0
    )
    
    assert len(config.entry_conditions) == 2
    assert isinstance(config.entry_conditions[0], EntryCondition)
    assert isinstance(config.entry_conditions[1], PriceNearLevelCondition)
    assert config.entry_conditions[1].level == "support"


def test_price_near_level_condition_requires_level_defined():
    """Test that price_near_level condition requires corresponding level to be defined."""
    from src.strategy.config import PriceNearLevelCondition
    
    # Missing support_level when condition requires it
    with pytest.raises(ValueError, match="requires support_level to be defined"):
        StrategyConfig(
            name="test_range",
            symbol="BTCUSDT",
            timeframes=["4h"],
            indicators={"rsi": IndicatorConfig(type="rsi", timeframe="4h", period=14)},
            entry_conditions=[
                PriceNearLevelCondition(type="price_near_level", level="support")
            ],
            exit_conditions=[ExitCondition(type="take_profit", percent=2.0)],
            position_size=0.01,
            max_position_size=0.05,
            resistance_level=72000.0  # Only resistance defined, not support
        )
    
    # Missing resistance_level when condition requires it
    with pytest.raises(ValueError, match="requires resistance_level to be defined"):
        StrategyConfig(
            name="test_range",
            symbol="BTCUSDT",
            timeframes=["4h"],
            indicators={"rsi": IndicatorConfig(type="rsi", timeframe="4h", period=14)},
            entry_conditions=[
                PriceNearLevelCondition(type="price_near_level", level="resistance")
            ],
            exit_conditions=[ExitCondition(type="take_profit", percent=2.0)],
            position_size=0.01,
            max_position_size=0.05,
            support_level=68000.0  # Only support defined, not resistance
        )


def test_load_strategy_with_price_near_level_from_yaml(tmp_path):
    """Test loading a strategy with price_near_level condition from YAML."""
    # Create a temporary YAML file
    yaml_content = """
name: test_range_strategy
symbol: BTCUSDT
timeframes:
  - 4h
position_size: 0.01
max_position_size: 0.05
support_level: 68000.0
resistance_level: 72000.0
level_proximity_percent: 0.5

indicators:
  rsi_4h:
    type: rsi
    timeframe: 4h
    period: 14
    oversold: 30
    overbought: 70

entry_conditions:
  - type: less_than
    indicator: rsi_4h
    value: 30
    description: RSI oversold
  
  - type: price_near_level
    level: support
    description: Price near support

exit_conditions:
  - type: take_profit
    percent: 2.0
  - type: stop_loss
    percent: 1.0
"""
    
    yaml_file = tmp_path / "test_range.yaml"
    yaml_file.write_text(yaml_content)
    
    # Load the strategy
    strategy = load_strategy_from_yaml(yaml_file)
    
    # Verify basic fields
    assert strategy.name == "test_range_strategy"
    assert strategy.symbol == "BTCUSDT"
    assert strategy.support_level == 68000.0
    assert strategy.resistance_level == 72000.0
    assert strategy.level_proximity_percent == 0.5
    
    # Verify entry conditions
    assert len(strategy.entry_conditions) == 2
    
    # First condition should be EntryCondition
    assert isinstance(strategy.entry_conditions[0], EntryCondition)
    assert strategy.entry_conditions[0].type == "less_than"
    assert strategy.entry_conditions[0].indicator == "rsi_4h"
    assert strategy.entry_conditions[0].value == 30
    
    # Second condition should be PriceNearLevelCondition
    from src.strategy.config import PriceNearLevelCondition
    assert isinstance(strategy.entry_conditions[1], PriceNearLevelCondition)
    assert strategy.entry_conditions[1].type == "price_near_level"
    assert strategy.entry_conditions[1].level == "support"
    assert strategy.entry_conditions[1].description == "Price near support"
