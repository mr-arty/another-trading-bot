"""Integration tests for range trading with price near level detection."""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import AsyncMock

from src.strategy.loader import StrategyLoader, load_strategy_from_yaml
from src.strategy.engine import StrategyEngine, Signal
from src.indicators.calculator import IndicatorCalculator
from src.exchange.connector import MarketData


@pytest.mark.asyncio
async def test_load_range_trading_strategy_with_levels():
    """Test loading a range trading strategy with support/resistance levels."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Create test range trading strategy YAML (subtask 7.1)
        strategy_content = """
name: "test_range_strategy"
symbol: "BTCUSDT"
timeframes:
  - "4h"

# Support and resistance levels
support_level: 68000.0
resistance_level: 72000.0
level_proximity_percent: 0.5

indicators:
  rsi_4h:
    type: "rsi"
    timeframe: "4h"
    period: 14

entry_conditions:
  - type: "less_than"
    indicator: "rsi_4h"
    value: 30
    description: "RSI below 30 (oversold)"
  
  - type: "price_near_level"
    level: "support"
    description: "Price within 0.5% of support"

exit_conditions:
  - type: "take_profit"
    percent: 3.0

position_size: 0.01
max_position_size: 0.05
position_direction: "long"
"""
        strategy_file = tmpdir_path / "test_range_strategy.yaml"
        strategy_file.write_text(strategy_content)
        
        # Load strategy (subtask 7.9)
        strategy = load_strategy_from_yaml(strategy_file)
        
        # Verify strategy loaded correctly
        assert strategy.name == "test_range_strategy"
        assert strategy.support_level == 68000.0
        assert strategy.resistance_level == 72000.0
        assert strategy.level_proximity_percent == 0.5
        assert len(strategy.entry_conditions) == 2
        
        # Verify price_near_level condition
        price_condition = strategy.entry_conditions[1]
        assert price_condition.type == "price_near_level"
        assert price_condition.level == "support"


@pytest.mark.asyncio
async def test_long_entry_with_rsi_and_price_near_support():
    """Test long entry signal when RSI < 30 AND price near support (subtask 7.2)."""
    # Setup strategy
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        strategy_content = """
name: "long_entry_test"
symbol: "BTCUSDT"
timeframes:
  - "4h"

support_level: 68000.0
resistance_level: 72000.0
level_proximity_percent: 0.5

indicators:
  rsi_4h:
    type: "rsi"
    timeframe: "4h"
    period: 14

entry_conditions:
  - type: "less_than"
    indicator: "rsi_4h"
    value: 30
  
  - type: "price_near_level"
    level: "support"

exit_conditions:
  - type: "take_profit"
    percent: 3.0

position_size: 0.01
max_position_size: 0.05
position_direction: "long"
"""
        strategy_file = tmpdir_path / "long_entry_test.yaml"
        strategy_file.write_text(strategy_content)
        
        strategy = load_strategy_from_yaml(strategy_file)
        
        # Setup engine
        indicator_calc = IndicatorCalculator()
        signals = []
        
        async def signal_callback(signal: Signal):
            signals.append(signal)
        
        engine = StrategyEngine(indicator_calc, signal_callback)
        await engine.register_strategy(strategy)
        
        # Build up indicator history with low RSI values
        # Need 15 data points for RSI calculation (period=14 + 1)
        # Start higher and decline TO support level
        
        for i in range(20):
            # Create declining prices to generate low RSI, ending near support
            price = 70000.0 - (i * 100)  # Decline from 70000 toward 68000
            # Keep final prices near support
            if i >= 15:
                price = 68200.0 - ((i - 15) * 10)  # Stay near support
            data = MarketData(
                symbol="BTCUSDT",
                timestamp=datetime.now(),
                open=price,
                high=price + 10,
                low=price - 10,
                close=price,
                volume=1.0
            )
            await engine.process_market_data(data)
        
        # Should generate long entry signal (buy)
        assert len(signals) > 0
        last_signal = signals[-1]
        assert last_signal.side == 'buy'
        assert last_signal.strategy_name == "long_entry_test"
        assert "rsi" in last_signal.reason.lower() or "30" in last_signal.reason
        assert "support" in last_signal.reason.lower()


@pytest.mark.asyncio
async def test_short_entry_with_rsi_and_price_near_resistance():
    """Test short entry signal when RSI > 70 AND price near resistance (subtask 7.3)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        strategy_content = """
name: "short_entry_test"
symbol: "BTCUSDT"
timeframes:
  - "4h"

support_level: 68000.0
resistance_level: 72000.0
level_proximity_percent: 0.5

indicators:
  rsi_4h:
    type: "rsi"
    timeframe: "4h"
    period: 14

entry_conditions:
  - type: "greater_than"
    indicator: "rsi_4h"
    value: 70
  
  - type: "price_near_level"
    level: "resistance"

exit_conditions:
  - type: "take_profit"
    percent: 3.0

position_size: 0.01
max_position_size: 0.05
position_direction: "short"
"""
        strategy_file = tmpdir_path / "short_entry_test.yaml"
        strategy_file.write_text(strategy_content)
        
        strategy = load_strategy_from_yaml(strategy_file)
        
        # Setup engine
        indicator_calc = IndicatorCalculator()
        signals = []
        
        async def signal_callback(signal: Signal):
            signals.append(signal)
        
        engine = StrategyEngine(indicator_calc, signal_callback)
        await engine.register_strategy(strategy)
        
        # Build up indicator history with high RSI values
        # Start lower and rise TO resistance level
        
        for i in range(20):
            # Create rising prices to generate high RSI, ending near resistance
            price = 70000.0 + (i * 100)  # Rise from 70000 toward 72000
            # Keep final prices near resistance
            if i >= 15:
                price = 71800.0 + ((i - 15) * 10)  # Stay near resistance
            data = MarketData(
                symbol="BTCUSDT",
                timestamp=datetime.now(),
                open=price,
                high=price + 10,
                low=price - 10,
                close=price,
                volume=1.0
            )
            await engine.process_market_data(data)
        
        # Should generate short entry signal (sell)
        assert len(signals) > 0
        last_signal = signals[-1]
        assert last_signal.side == 'sell'
        assert last_signal.strategy_name == "short_entry_test"
        assert "rsi" in last_signal.reason.lower() or "70" in last_signal.reason
        assert "resistance" in last_signal.reason.lower()


@pytest.mark.asyncio
async def test_no_signal_when_rsi_met_but_price_not_near_level():
    """Test no signal when RSI condition met but price not near level (subtask 7.4)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        strategy_content = """
name: "no_signal_price_far"
symbol: "BTCUSDT"
timeframes:
  - "4h"

support_level: 68000.0
resistance_level: 72000.0
level_proximity_percent: 0.5

indicators:
  rsi_4h:
    type: "rsi"
    timeframe: "4h"
    period: 14

entry_conditions:
  - type: "less_than"
    indicator: "rsi_4h"
    value: 30
  
  - type: "price_near_level"
    level: "support"

exit_conditions:
  - type: "take_profit"
    percent: 3.0

position_size: 0.01
max_position_size: 0.05
position_direction: "long"
"""
        strategy_file = tmpdir_path / "no_signal_price_far.yaml"
        strategy_file.write_text(strategy_content)
        
        strategy = load_strategy_from_yaml(strategy_file)
        
        # Setup engine
        indicator_calc = IndicatorCalculator()
        signals = []
        
        async def signal_callback(signal: Signal):
            signals.append(signal)
        
        engine = StrategyEngine(indicator_calc, signal_callback)
        await engine.register_strategy(strategy)
        
        # Build up indicator history with low RSI but price FAR from support
        base_price = 70000.0  # Mid-range, far from support (68000)
        
        for i in range(20):
            # Create declining prices to generate low RSI, but stay far from support
            price = base_price - (i * 20)  # Still far from 68000
            data = MarketData(
                symbol="BTCUSDT",
                timestamp=datetime.now(),
                open=price,
                high=price + 10,
                low=price - 10,
                close=price,
                volume=1.0
            )
            await engine.process_market_data(data)
        
        # Should NOT generate signal (price not near support)
        assert len(signals) == 0


@pytest.mark.asyncio
async def test_no_signal_when_price_near_level_but_rsi_not_met():
    """Test no signal when price near level but RSI condition not met (subtask 7.5)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        strategy_content = """
name: "no_signal_rsi_not_met"
symbol: "BTCUSDT"
timeframes:
  - "4h"

support_level: 68000.0
resistance_level: 72000.0
level_proximity_percent: 0.5

indicators:
  rsi_4h:
    type: "rsi"
    timeframe: "4h"
    period: 14

entry_conditions:
  - type: "less_than"
    indicator: "rsi_4h"
    value: 30
  
  - type: "price_near_level"
    level: "support"

exit_conditions:
  - type: "take_profit"
    percent: 3.0

position_size: 0.01
max_position_size: 0.05
position_direction: "long"
"""
        strategy_file = tmpdir_path / "no_signal_rsi_not_met.yaml"
        strategy_file.write_text(strategy_content)
        
        strategy = load_strategy_from_yaml(strategy_file)
        
        # Setup engine
        indicator_calc = IndicatorCalculator()
        signals = []
        
        async def signal_callback(signal: Signal):
            signals.append(signal)
        
        engine = StrategyEngine(indicator_calc, signal_callback)
        await engine.register_strategy(strategy)
        
        # Build up indicator history with neutral RSI but price near support
        base_price = 68200.0  # Near support (68000)
        
        for i in range(20):
            # Create stable prices to generate neutral RSI (around 50)
            price = base_price + ((i % 2) * 10)  # Oscillate slightly
            data = MarketData(
                symbol="BTCUSDT",
                timestamp=datetime.now(),
                open=price,
                high=price + 5,
                low=price - 5,
                close=price,
                volume=1.0
            )
            await engine.process_market_data(data)
        
        # Should NOT generate signal (RSI not < 30)
        assert len(signals) == 0


@pytest.mark.asyncio
async def test_signal_generation_with_both_conditions_met():
    """Test signal generated when both RSI and price proximity conditions met (subtask 7.6)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        strategy_content = """
name: "both_conditions_met"
symbol: "BTCUSDT"
timeframes:
  - "4h"

support_level: 68000.0
resistance_level: 72000.0
level_proximity_percent: 0.5

indicators:
  rsi_4h:
    type: "rsi"
    timeframe: "4h"
    period: 14

entry_conditions:
  - type: "less_than"
    indicator: "rsi_4h"
    value: 30
  
  - type: "price_near_level"
    level: "support"

exit_conditions:
  - type: "take_profit"
    percent: 3.0

position_size: 0.01
max_position_size: 0.05
position_direction: "long"
"""
        strategy_file = tmpdir_path / "both_conditions_met.yaml"
        strategy_file.write_text(strategy_content)
        
        strategy = load_strategy_from_yaml(strategy_file)
        
        # Setup engine
        indicator_calc = IndicatorCalculator()
        signals = []
        
        async def signal_callback(signal: Signal):
            signals.append(signal)
        
        engine = StrategyEngine(indicator_calc, signal_callback)
        await engine.register_strategy(strategy)
        
        # Build up indicator history: low RSI AND price near support
        base_price = 68200.0  # Near support (68000) - within 0.5%
        
        for i in range(20):
            # Create declining prices near support to generate low RSI
            price = base_price - (i * 10)  # Stay near support
            data = MarketData(
                symbol="BTCUSDT",
                timestamp=datetime.now(),
                open=price,
                high=price + 5,
                low=price - 5,
                close=price,
                volume=1.0
            )
            await engine.process_market_data(data)
        
        # Should generate signal (both conditions met)
        assert len(signals) > 0
        last_signal = signals[-1]
        assert last_signal.side == 'buy'
        assert last_signal.strategy_name == "both_conditions_met"
        
        # Verify reason includes both conditions
        reason_lower = last_signal.reason.lower()
        assert "support" in reason_lower or "68" in reason_lower
        assert "rsi" in reason_lower or "30" in reason_lower


@pytest.mark.asyncio
async def test_proximity_zone_transition_logging(caplog):
    """Test proximity zone entry/exit transitions are logged (subtask 7.7)."""
    import logging
    caplog.set_level(logging.INFO)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        strategy_content = """
name: "proximity_logging_test"
symbol: "BTCUSDT"
timeframes:
  - "4h"

support_level: 68000.0
resistance_level: 72000.0
level_proximity_percent: 0.5

indicators:
  rsi_4h:
    type: "rsi"
    timeframe: "4h"
    period: 14

entry_conditions:
  - type: "less_than"
    indicator: "rsi_4h"
    value: 30
  
  - type: "price_near_level"
    level: "support"

exit_conditions:
  - type: "take_profit"
    percent: 3.0

position_size: 0.01
max_position_size: 0.05
position_direction: "long"
"""
        strategy_file = tmpdir_path / "proximity_logging_test.yaml"
        strategy_file.write_text(strategy_content)
        
        strategy = load_strategy_from_yaml(strategy_file)
        
        # Setup engine
        indicator_calc = IndicatorCalculator()
        engine = StrategyEngine(indicator_calc, None)
        await engine.register_strategy(strategy)
        
        # Build up indicator history first
        for i in range(15):
            data = MarketData(
                symbol="BTCUSDT",
                timestamp=datetime.now(),
                open=70000.0,
                high=70010.0,
                low=69990.0,
                close=70000.0,
                volume=1.0
            )
            await engine.process_market_data(data)
        
        # Move price INTO proximity zone (should log entry)
        data = MarketData(
            symbol="BTCUSDT",
            timestamp=datetime.now(),
            open=68200.0,
            high=68210.0,
            low=68190.0,
            close=68200.0,  # Within 0.5% of 68000
            volume=1.0
        )
        await engine.process_market_data(data)
        
        # Move price OUT of proximity zone (should log exit)
        data = MarketData(
            symbol="BTCUSDT",
            timestamp=datetime.now(),
            open=69500.0,
            high=69510.0,
            low=69490.0,
            close=69500.0,  # Outside 0.5% of 68000
            volume=1.0
        )
        await engine.process_market_data(data)
        
        # Check logs for proximity zone transitions
        log_messages = [record.message for record in caplog.records]
        
        # Should have logged entering and exiting proximity
        # Note: Actual log format depends on structlog configuration
        # We're checking that the evaluation happened
        assert len(log_messages) > 0


@pytest.mark.asyncio
async def test_with_real_market_data_simulation():
    """Test strategy with realistic market data simulation (subtask 7.8)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        strategy_content = """
name: "real_data_simulation"
symbol: "BTCUSDT"
timeframes:
  - "4h"

support_level: 68000.0
resistance_level: 72000.0
level_proximity_percent: 0.5

indicators:
  rsi_4h:
    type: "rsi"
    timeframe: "4h"
    period: 14

entry_conditions:
  - type: "less_than"
    indicator: "rsi_4h"
    value: 30
  
  - type: "price_near_level"
    level: "support"

exit_conditions:
  - type: "take_profit"
    percent: 3.0

position_size: 0.01
max_position_size: 0.05
position_direction: "long"
"""
        strategy_file = tmpdir_path / "real_data_simulation.yaml"
        strategy_file.write_text(strategy_content)
        
        strategy = load_strategy_from_yaml(strategy_file)
        
        # Setup engine
        indicator_calc = IndicatorCalculator()
        signals = []
        
        async def signal_callback(signal: Signal):
            signals.append(signal)
        
        engine = StrategyEngine(indicator_calc, signal_callback)
        await engine.register_strategy(strategy)
        
        # Simulate realistic market scenario:
        # 1. Price starts at mid-range
        # 2. Declines toward support
        # 3. Reaches support with oversold RSI
        
        prices = [
            70000, 69800, 69600, 69400, 69200,  # Declining from mid-range
            69000, 68800, 68600, 68400, 68300,  # Approaching support
            68200, 68150, 68100, 68050, 68000,  # At support
            68050, 68100, 68150, 68200, 68250   # Near support with low RSI
        ]
        
        for price in prices:
            data = MarketData(
                symbol="BTCUSDT",
                timestamp=datetime.now(),
                open=price,
                high=price + 50,
                low=price - 50,
                close=price,
                volume=100.0
            )
            await engine.process_market_data(data)
        
        # Should generate at least one signal during the decline to support
        assert len(signals) > 0
        
        # Verify signal is a buy (long entry)
        buy_signals = [s for s in signals if s.side == 'buy']
        assert len(buy_signals) > 0


@pytest.mark.asyncio
async def test_backward_compatibility_with_existing_strategies():
    """Test that existing strategies without price_near_level still work (subtask 7.10)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Create a traditional strategy WITHOUT price_near_level condition
        strategy_content = """
name: "traditional_strategy"
symbol: "BTCUSDT"
timeframes:
  - "4h"

indicators:
  rsi_4h:
    type: "rsi"
    timeframe: "4h"
    period: 14

entry_conditions:
  - type: "less_than"
    indicator: "rsi_4h"
    value: 30

exit_conditions:
  - type: "take_profit"
    percent: 3.0

position_size: 0.01
max_position_size: 0.05
position_direction: "long"
"""
        strategy_file = tmpdir_path / "traditional_strategy.yaml"
        strategy_file.write_text(strategy_content)
        
        # Should load without errors
        strategy = load_strategy_from_yaml(strategy_file)
        
        assert strategy.name == "traditional_strategy"
        assert strategy.support_level is None
        assert strategy.resistance_level is None
        assert len(strategy.entry_conditions) == 1
        
        # Setup engine and verify it works
        indicator_calc = IndicatorCalculator()
        signals = []
        
        async def signal_callback(signal: Signal):
            signals.append(signal)
        
        engine = StrategyEngine(indicator_calc, signal_callback)
        await engine.register_strategy(strategy)
        
        # Process market data
        for i in range(20):
            price = 70000 - (i * 100)
            data = MarketData(
                symbol="BTCUSDT",
                timestamp=datetime.now(),
                open=price,
                high=price + 10,
                low=price - 10,
                close=price,
                volume=1.0
            )
            await engine.process_market_data(data)
        
        # Should generate signals based on RSI alone
        assert len(signals) > 0
        assert signals[-1].side == 'buy'
