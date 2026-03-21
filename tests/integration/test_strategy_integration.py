"""Integration tests for strategy loading system."""

import pytest
import tempfile
import asyncio
from pathlib import Path
from src.strategy import StrategyLoader, watch_strategies


@pytest.mark.asyncio
async def test_full_strategy_loading_workflow():
    """Test the complete workflow of loading and watching strategies."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Create initial strategy file
        strategy_content = """
name: "integration_test_strategy"
symbol: "BTCUSDT"
timeframes:
  - "5m"
  - "15m"
indicators:
  rsi_5m:
    type: "rsi"
    timeframe: "5m"
    period: 14
  ema_fast:
    type: "ema"
    timeframe: "15m"
    period: 9
  ema_slow:
    type: "ema"
    timeframe: "15m"
    period: 21
entry_conditions:
  - type: "less_than"
    indicator: "rsi_5m"
    value: 30
  - type: "cross_above"
    indicator1: "ema_fast"
    indicator2: "ema_slow"
exit_conditions:
  - type: "take_profit"
    percent: 3.0
  - type: "stop_loss"
    percent: 1.5
  - type: "time_exceeds"
    seconds: 3600
position_size: 0.01
max_position_size: 0.05
"""
        strategy_file = tmpdir_path / "test_strategy.yaml"
        strategy_file.write_text(strategy_content)
        
        # Initialize loader
        loader = StrategyLoader()
        
        # Load strategies from directory
        strategies = await loader.load_strategies_from_directory(str(tmpdir_path))
        
        # Verify strategy was loaded
        assert len(strategies) == 1
        assert "integration_test_strategy" in strategies
        
        strategy = strategies["integration_test_strategy"]
        assert strategy.symbol == "BTCUSDT"
        assert len(strategy.timeframes) == 2
        assert len(strategy.indicators) == 3
        assert len(strategy.entry_conditions) == 2
        assert len(strategy.exit_conditions) == 3
        
        # Verify indicator types
        assert strategy.indicators["rsi_5m"].type == "rsi"
        assert strategy.indicators["ema_fast"].type == "ema"
        assert strategy.indicators["ema_slow"].type == "ema"
        
        # Verify entry condition types
        condition_types = [c.type for c in strategy.entry_conditions]
        assert "less_than" in condition_types
        assert "cross_above" in condition_types
        
        # Verify exit condition types
        exit_types = [c.type for c in strategy.exit_conditions]
        assert "take_profit" in exit_types
        assert "stop_loss" in exit_types
        assert "time_exceeds" in exit_types


@pytest.mark.asyncio
async def test_strategy_watcher_integration():
    """Test file watcher integration with strategy loader."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Track reload events
        reload_events = []
        
        async def reload_callback(file_path: Path, event_type: str):
            """Callback for file changes."""
            reload_events.append((file_path.name, event_type))
        
        # Start watcher
        watcher = await watch_strategies(str(tmpdir_path), reload_callback)
        
        try:
            # Create a strategy file
            strategy_file = tmpdir_path / "watched_strategy.yaml"
            strategy_content = """
name: "watched_strategy"
symbol: "ETHUSDT"
timeframes:
  - "5m"
indicators:
  rsi:
    type: "rsi"
    timeframe: "5m"
    period: 14
entry_conditions:
  - type: "less_than"
    indicator: "rsi"
    value: 30
exit_conditions:
  - type: "take_profit"
    percent: 2.0
position_size: 0.01
max_position_size: 0.05
"""
            strategy_file.write_text(strategy_content)
            
            # Wait for file system event to be processed
            await asyncio.sleep(0.5)
            
            # Verify creation was detected
            assert len(reload_events) > 0
            assert any(event[0] == "watched_strategy.yaml" for event in reload_events)
            
        finally:
            # Stop watcher
            watcher.stop()


@pytest.mark.asyncio
async def test_multiple_strategies_loading():
    """Test loading multiple strategies with different configurations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Create multiple strategy files
        strategies_data = [
            {
                "name": "momentum_strategy",
                "symbol": "BTCUSDT",
                "indicator_type": "rsi",
                "condition_type": "less_than"
            },
            {
                "name": "trend_strategy",
                "symbol": "ETHUSDT",
                "indicator_type": "ema",
                "condition_type": "greater_than"
            },
            {
                "name": "reversal_strategy",
                "symbol": "SOLUSDT",
                "indicator_type": "rsi",
                "condition_type": "cross_below"
            }
        ]
        
        for i, data in enumerate(strategies_data):
            if data["indicator_type"] == "rsi":
                indicator_config = """
  indicator:
    type: "rsi"
    timeframe: "5m"
    period: 14"""
                indicator_name = "indicator"
                # For RSI, use simple conditions
                if data["condition_type"] == "cross_below":
                    entry_condition = """
  - type: "less_than"
    indicator: "indicator"
    value: 30"""
                else:
                    entry_condition = f"""
  - type: "{data['condition_type']}"
    indicator: "{indicator_name}"
    value: 50"""
            else:
                indicator_config = """
  ema_fast:
    type: "ema"
    timeframe: "5m"
    period: 9
  ema_slow:
    type: "ema"
    timeframe: "5m"
    period: 21"""
                indicator_name = "ema_fast"
                # For EMA, can use cross conditions
                if data["condition_type"] == "cross_below":
                    entry_condition = """
  - type: "cross_below"
    indicator1: "ema_fast"
    indicator2: "ema_slow" """
                else:
                    entry_condition = f"""
  - type: "{data['condition_type']}"
    indicator: "{indicator_name}"
    value: 50"""
            
            strategy_content = f"""
name: "{data['name']}"
symbol: "{data['symbol']}"
timeframes:
  - "5m"
indicators:{indicator_config}
entry_conditions:{entry_condition}
exit_conditions:
  - type: "take_profit"
    percent: 2.0
position_size: 0.01
max_position_size: 0.05
"""
            (tmpdir_path / f"strategy_{i}.yaml").write_text(strategy_content)
        
        # Load all strategies
        loader = StrategyLoader()
        strategies = await loader.load_strategies_from_directory(str(tmpdir_path))
        
        # Verify all strategies were loaded
        assert len(strategies) == 3
        assert "momentum_strategy" in strategies
        assert "trend_strategy" in strategies
        assert "reversal_strategy" in strategies
        
        # Verify each strategy has correct symbol
        assert strategies["momentum_strategy"].symbol == "BTCUSDT"
        assert strategies["trend_strategy"].symbol == "ETHUSDT"
        assert strategies["reversal_strategy"].symbol == "SOLUSDT"
