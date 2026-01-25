"""Unit tests for strategy directory loader."""

import pytest
import tempfile
import shutil
from pathlib import Path
from src.strategy.loader import StrategyLoader


@pytest.mark.asyncio
async def test_load_strategies_from_directory():
    """Test loading strategies from a directory."""
    # Create a temporary directory with test strategy files
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Create a valid strategy file
        valid_strategy = """
name: "test_strategy"
symbol: "BTCUSDT"
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
        (tmpdir_path / "valid.yaml").write_text(valid_strategy)
        
        # Create an invalid strategy file
        invalid_strategy = """
name: "invalid_strategy"
# Missing required fields
"""
        (tmpdir_path / "invalid.yaml").write_text(invalid_strategy)
        
        # Load strategies
        loader = StrategyLoader()
        strategies = await loader.load_strategies_from_directory(str(tmpdir_path))
        
        # Should load only the valid strategy
        assert len(strategies) == 1
        assert "test_strategy" in strategies
        assert strategies["test_strategy"].symbol == "BTCUSDT"


@pytest.mark.asyncio
async def test_load_from_nonexistent_directory():
    """Test loading from a non-existent directory."""
    loader = StrategyLoader()
    strategies = await loader.load_strategies_from_directory("/nonexistent/path")
    
    # Should return empty dict
    assert len(strategies) == 0


@pytest.mark.asyncio
async def test_duplicate_strategy_names():
    """Test that duplicate strategy names are handled correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Create two files with the same strategy name
        strategy_content = """
name: "duplicate_name"
symbol: "BTCUSDT"
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
        (tmpdir_path / "strategy1.yaml").write_text(strategy_content)
        (tmpdir_path / "strategy2.yaml").write_text(strategy_content)
        
        loader = StrategyLoader()
        strategies = await loader.load_strategies_from_directory(str(tmpdir_path))
        
        # Should only load one strategy (the first one encountered)
        assert len(strategies) == 1
        assert "duplicate_name" in strategies


@pytest.mark.asyncio
async def test_get_strategy():
    """Test getting a strategy by name."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        strategy_content = """
name: "test_strategy"
symbol: "BTCUSDT"
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
        (tmpdir_path / "strategy.yaml").write_text(strategy_content)
        
        loader = StrategyLoader()
        await loader.load_strategies_from_directory(str(tmpdir_path))
        
        # Get the strategy
        strategy = loader.get_strategy("test_strategy")
        assert strategy.name == "test_strategy"
        
        # Try to get non-existent strategy
        with pytest.raises(KeyError):
            loader.get_strategy("nonexistent")


@pytest.mark.asyncio
async def test_has_strategy():
    """Test checking if a strategy exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        strategy_content = """
name: "test_strategy"
symbol: "BTCUSDT"
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
        (tmpdir_path / "strategy.yaml").write_text(strategy_content)
        
        loader = StrategyLoader()
        await loader.load_strategies_from_directory(str(tmpdir_path))
        
        assert loader.has_strategy("test_strategy")
        assert not loader.has_strategy("nonexistent")


@pytest.mark.asyncio
async def test_reload_strategy():
    """Test reloading a single strategy."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        strategy_file = tmpdir_path / "strategy.yaml"
        strategy_content = """
name: "test_strategy"
symbol: "BTCUSDT"
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
        
        loader = StrategyLoader()
        await loader.load_strategies_from_directory(str(tmpdir_path))
        
        # Verify initial load
        strategy = loader.get_strategy("test_strategy")
        assert strategy.position_size == 0.01
        
        # Modify the file
        modified_content = strategy_content.replace("position_size: 0.01", "position_size: 0.02")
        strategy_file.write_text(modified_content)
        
        # Reload
        success = await loader.reload_strategy(strategy_file)
        assert success
        
        # Verify the change
        strategy = loader.get_strategy("test_strategy")
        assert strategy.position_size == 0.02


@pytest.mark.asyncio
async def test_remove_strategy():
    """Test removing a strategy."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        strategy_content = """
name: "test_strategy"
symbol: "BTCUSDT"
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
        (tmpdir_path / "strategy.yaml").write_text(strategy_content)
        
        loader = StrategyLoader()
        await loader.load_strategies_from_directory(str(tmpdir_path))
        
        assert loader.has_strategy("test_strategy")
        
        # Remove the strategy
        success = await loader.remove_strategy("test_strategy")
        assert success
        assert not loader.has_strategy("test_strategy")
        
        # Try to remove non-existent strategy
        success = await loader.remove_strategy("nonexistent")
        assert not success
