"""Demonstration script for strategy loading functionality."""

import asyncio
import logging
from pathlib import Path
from src.strategy import StrategyLoader, watch_strategies

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def demo_strategy_loading():
    """Demonstrate strategy loading from directory."""
    logger.info("=== Strategy Loading Demo ===")
    
    # Initialize loader
    loader = StrategyLoader()
    
    # Load strategies from the strategies directory
    strategies_dir = "./strategies"
    
    # Check if directory exists, if not use example file
    if not Path(strategies_dir).exists():
        logger.warning(f"Directory {strategies_dir} does not exist, creating it...")
        Path(strategies_dir).mkdir(parents=True, exist_ok=True)
        logger.info("Please add YAML strategy files to the strategies directory")
        return
    
    logger.info(f"Loading strategies from: {strategies_dir}")
    strategies = await loader.load_strategies_from_directory(strategies_dir)
    
    if not strategies:
        logger.info("No valid strategies found in directory")
        logger.info("You can copy example_strategy.yaml to the strategies directory")
        return
    
    # Display loaded strategies
    logger.info(f"\nLoaded {len(strategies)} strategy/strategies:")
    for name, strategy in strategies.items():
        logger.info(f"\n  Strategy: {name}")
        logger.info(f"    Symbol: {strategy.symbol}")
        logger.info(f"    Timeframes: {', '.join(strategy.timeframes)}")
        logger.info(f"    Indicators: {len(strategy.indicators)}")
        logger.info(f"    Entry Conditions: {len(strategy.entry_conditions)}")
        logger.info(f"    Exit Conditions: {len(strategy.exit_conditions)}")
        logger.info(f"    Position Size: {strategy.position_size}")
        logger.info(f"    Max Position Size: {strategy.max_position_size}")
        
        # Display indicators
        logger.info(f"    Indicator Details:")
        for ind_name, indicator in strategy.indicators.items():
            logger.info(f"      - {ind_name}: {indicator.type} ({indicator.timeframe}, period={indicator.period})")
        
        # Display entry conditions
        logger.info(f"    Entry Condition Details:")
        for i, condition in enumerate(strategy.entry_conditions):
            if condition.type in ["less_than", "greater_than"]:
                logger.info(f"      - {condition.type}: {condition.indicator} {condition.type.replace('_', ' ')} {condition.value}")
            elif condition.type in ["cross_above", "cross_below"]:
                logger.info(f"      - {condition.type}: {condition.indicator1} crosses {condition.type.split('_')[1]} {condition.indicator2}")
        
        # Display exit conditions
        logger.info(f"    Exit Condition Details:")
        for condition in strategy.exit_conditions:
            if condition.type == "take_profit":
                logger.info(f"      - Take Profit: {condition.percent}%")
            elif condition.type == "stop_loss":
                logger.info(f"      - Stop Loss: {condition.percent}%")
            elif condition.type == "time_exceeds":
                logger.info(f"      - Time Limit: {condition.seconds} seconds")
            elif condition.type == "support_resistance":
                logger.info(f"      - Support/Resistance: {condition.direction} {condition.price}")
            elif condition.type == "end_of_day":
                logger.info(f"      - End of Day: {condition.time_utc} UTC")


async def demo_file_watching():
    """Demonstrate file watching for strategy reloading."""
    logger.info("\n=== File Watching Demo ===")
    
    strategies_dir = "./strategies"
    
    if not Path(strategies_dir).exists():
        logger.warning(f"Directory {strategies_dir} does not exist")
        return
    
    # Track reload events
    reload_count = [0]
    
    async def reload_callback(file_path: Path, event_type: str):
        """Callback for file changes."""
        reload_count[0] += 1
        logger.info(f"File {event_type}: {file_path.name}")
    
    logger.info(f"Starting file watcher on: {strategies_dir}")
    logger.info("Modify any .yaml file in the strategies directory to see reload events")
    logger.info("Press Ctrl+C to stop watching\n")
    
    # Start watcher
    watcher = await watch_strategies(strategies_dir, reload_callback)
    
    try:
        # Watch for 30 seconds
        await asyncio.sleep(30)
        logger.info(f"\nDetected {reload_count[0]} file change(s)")
    except KeyboardInterrupt:
        logger.info("\nStopping file watcher...")
    finally:
        watcher.stop()


async def main():
    """Main demonstration function."""
    try:
        # Demo 1: Load strategies
        await demo_strategy_loading()
        
        # Demo 2: File watching (optional, commented out by default)
        # Uncomment the line below to test file watching
        # await demo_file_watching()
        
    except Exception as e:
        logger.error(f"Error in demo: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
