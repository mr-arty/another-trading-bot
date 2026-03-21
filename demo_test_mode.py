#!/usr/bin/env python3
"""
Demo script showing test mode functionality.

Test mode allows you to verify API connectivity and data reception
without executing any trades. Perfect for:
- Testing API credentials
- Verifying market data flow
- Checking indicator calculations
- Debugging connectivity issues
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import load_config
from src.strategy import StrategyLoader, StrategyEngine
from src.market_data import MarketDataManager
from src.exchange import ExchangeConnector
from src.indicators import IndicatorCalculator
from src.logging import setup_logging, get_logger


async def main():
    """Run test mode demo."""
    # Setup logging
    setup_logging(log_dir="./logs", log_level="INFO")
    logger = get_logger()
    
    logger.info("=== Test Mode Demo ===")
    logger.info("This demo will:")
    logger.info("1. Load the test strategy from strategies/test_data_strategy.yaml")
    logger.info("2. Connect to Bybit API")
    logger.info("3. Subscribe to market data")
    logger.info("4. Calculate indicators")
    logger.info("5. Log data reception (no trading)")
    logger.info("")
    
    try:
        # Load configuration
        logger.info("Loading configuration...")
        config = await load_config()
        
        # Initialize components
        logger.info("Initializing components...")
        
        # Exchange connector (for market data)
        exchange = ExchangeConnector(
            api_key=config.exchange_api_key,
            api_secret=config.exchange_api_secret,
            testnet=config.exchange_testnet
        )
        
        # Connect to exchange
        logger.info("Connecting to exchange...")
        await exchange.connect()
        
        # Market data manager
        market_data_manager = MarketDataManager(exchange)
        
        # Indicator calculator
        indicator_calculator = IndicatorCalculator()
        
        # Strategy engine
        strategy_engine = StrategyEngine(
            indicator_calculator=indicator_calculator,
            signal_callback=None  # No signal callback in test mode
        )
        
        # Load test strategy
        logger.info("Loading test strategy...")
        loader = StrategyLoader()
        
        # Load only test strategies
        strategies = await loader.load_strategies_from_directory(config.strategies_dir)
        
        test_strategies = {
            name: cfg for name, cfg in strategies.items()
            if cfg.strategy_type == "test"
        }
        
        if not test_strategies:
            logger.error("No test strategies found!")
            logger.error("Make sure strategies/test_data_strategy.yaml exists")
            logger.error("and has strategy_type: 'test'")
            return
        
        logger.info(f"Found {len(test_strategies)} test strategy(ies):")
        for name in test_strategies:
            logger.info(f"  - {name}")
        
        # Register test strategies
        for name, config_obj in test_strategies.items():
            await strategy_engine.register_strategy(config_obj)
            logger.info(f"Registered test strategy: {name}")
        
        # Subscribe to market data
        logger.info("Subscribing to market data...")
        for name, config_obj in test_strategies.items():
            
            async def data_callback(data):
                """Forward market data to strategy engine."""
                await strategy_engine.process_market_data(data)
            
            await market_data_manager.subscribe(
                symbol=config_obj.symbol,
                callback=data_callback
            )
            logger.info(f"Subscribed to {config_obj.symbol}")
        
        logger.info("")
        logger.info("=== Test Mode Active ===")
        logger.info("Receiving market data and calculating indicators...")
        logger.info("Watch for 'test_strategy_data_received' log messages")
        logger.info("Press Ctrl+C to stop")
        logger.info("")
        
        # Run for a while to collect data
        try:
            # Keep running until interrupted
            while True:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Stopping test mode...")
    
    except Exception as e:
        logger.error(f"Error in test mode: {e}", exc_info=True)
    
    finally:
        logger.info("Test mode demo completed")


if __name__ == "__main__":
    asyncio.run(main())
