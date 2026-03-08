"""
Trading Bot System - Main Entry Point
"""
import asyncio
import os
import sys
from pathlib import Path

from src.database.db import Database
from src.config.config import load_config
from src.strategy.loader import StrategyLoader
from src.exchange.connector import ExchangeConnector
from src.indicators.calculator import IndicatorCalculator
from src.market_data.manager import MarketDataManager
from src.strategy.engine import StrategyEngine
from src.risk.manager import RiskManager
from src.execution.executor import OrderExecutor
from src.position.tracker import PositionTracker
from src.monitoring.volatility import VolatilityMonitor
from src.killswitch.handler import KillSwitchHandler

# Import logging functions after other imports to avoid conflicts
import src.logging.logger as bot_logger


async def main():
    """Main entry point for the Trading Bot System"""
    # Set up comprehensive logging system
    log_dir = os.getenv("LOG_DIR", "logs")
    log_level = os.getenv("LOG_LEVEL", "INFO")
    max_log_size = int(os.getenv("MAX_LOG_SIZE", str(10 * 1024 * 1024)))  # 10 MB default
    log_backup_count = int(os.getenv("LOG_BACKUP_COUNT", "5"))
    
    logger = bot_logger.setup_logging(
        log_dir=log_dir,
        log_level=log_level,
        max_bytes=max_log_size,
        backup_count=log_backup_count,
        json_format=True
    )
    
    bot_logger.log_system_event(
        "system_start",
        "Starting Trading Bot System",
        log_dir=log_dir,
        log_level=log_level,
        max_log_size=max_log_size,
        log_backup_count=log_backup_count
    )
    
    # Component references for cleanup
    db = None
    exchange = None
    market_data_manager = None
    kill_switch = None
    
    try:
        # 1. Load configuration
        bot_logger.log_system_event("config_loading", "Loading system configuration")
        config = await load_config()
        bot_logger.log_system_event("config_loaded", "Configuration loaded successfully")
        
        # 2. Initialize database
        bot_logger.log_system_event("database_initializing", "Initializing database")
        db = Database()
        await db.initialize()
        bot_logger.log_system_event("database_initialized", "Database initialized successfully")
        
        # 3. Initialize exchange connector
        bot_logger.log_system_event("exchange_connecting", "Connecting to exchange")
        exchange = ExchangeConnector(
            api_key=config.exchange_api_key,
            api_secret=config.exchange_api_secret,
            testnet=config.exchange_testnet,
            rate_limit_per_second=config.api_rate_limit_per_second,
            max_reconnect_delay=config.reconnect_max_delay_seconds
        )
        await exchange.connect()
        bot_logger.log_system_event("exchange_connected", "Exchange connection established")
        
        # 4. Initialize indicator calculator
        bot_logger.log_system_event("indicators_initializing", "Initializing indicator calculator")
        indicator_calculator = IndicatorCalculator(cache_ttl_seconds=60)
        bot_logger.log_system_event("indicators_initialized", "Indicator calculator initialized")
        
        # 5. Initialize market data manager
        bot_logger.log_system_event("market_data_initializing", "Initializing market data manager")
        market_data_manager = MarketDataManager(
            exchange_connector=exchange,
            interruption_threshold_seconds=30
        )
        await market_data_manager.start_monitoring()
        bot_logger.log_system_event("market_data_initialized", "Market data manager initialized")
        
        # 6. Initialize position tracker
        bot_logger.log_system_event("position_tracker_initializing", "Initializing position tracker")
        position_tracker = PositionTracker(database=db)
        await position_tracker.load_state()
        bot_logger.log_system_event("position_tracker_initialized", "Position tracker initialized")
        
        # 7. Initialize order executor
        bot_logger.log_system_event("order_executor_initializing", "Initializing order executor")
        order_executor = OrderExecutor(
            exchange=exchange,
            position_tracker=position_tracker,
            database=db,
            max_retries=config.order_retry_attempts,
            retry_base_delay=1.0
        )
        bot_logger.log_system_event("order_executor_initialized", "Order executor initialized")
        
        # 8. Initialize risk manager
        bot_logger.log_system_event("risk_manager_initializing", "Initializing risk manager")
        risk_manager = RiskManager(
            config=config,
            signal_callback=order_executor.execute_signal
        )
        bot_logger.log_system_event("risk_manager_initialized", "Risk manager initialized")
        
        # 9. Initialize strategy engine
        bot_logger.log_system_event("strategy_engine_initializing", "Initializing strategy engine")
        strategy_engine = StrategyEngine(
            indicator_calculator=indicator_calculator,
            signal_callback=risk_manager.process_signal
        )
        bot_logger.log_system_event("strategy_engine_initialized", "Strategy engine initialized")
        
        # 10. Initialize volatility monitor
        bot_logger.log_system_event("volatility_monitor_initializing", "Initializing volatility monitor")
        volatility_monitor = VolatilityMonitor(
            database=db,
            market_data_manager=market_data_manager,
            atr_threshold=config.volatility_threshold,
            atr_period=14
        )
        bot_logger.log_system_event("volatility_monitor_initialized", "Volatility monitor initialized")
        
        # 11. Initialize kill-switch handler
        bot_logger.log_system_event("killswitch_initializing", "Initializing kill-switch handler")
        kill_switch = KillSwitchHandler(
            order_executor=order_executor,
            position_tracker=position_tracker,
            exchange=exchange,
            strategy_engine=strategy_engine
        )
        kill_switch.setup_signal_handler()
        
        # Wire kill-switch to order executor
        order_executor.kill_switch_handler = kill_switch
        bot_logger.log_system_event("killswitch_initialized", "Kill-switch handler initialized")
        
        # 12. Load strategies
        bot_logger.log_system_event("strategies_loading", "Loading strategies from directory")
        strategy_loader = StrategyLoader()
        strategies = await strategy_loader.load_strategies_from_directory(config.strategies_dir)
        bot_logger.log_system_event("strategies_loaded", f"Loaded {len(strategies)} strategies")
        
        # 13. Register strategies with strategy engine
        for strategy_name, strategy_config in strategies.items():
            bot_logger.log_system_event("strategy_registering", f"Registering strategy: {strategy_name}")
            await strategy_engine.register_strategy(strategy_config)
            
            # Subscribe to market data for this strategy's symbol
            async def market_data_callback(data):
                await strategy_engine.process_market_data(data)
            
            await market_data_manager.subscribe(
                symbol=strategy_config.symbol,
                callback=market_data_callback
            )
            
            bot_logger.log_system_event("strategy_registered", f"Strategy registered: {strategy_name}")
        
        bot_logger.log_system_event("system_ready", "Trading Bot System started and ready")
        
        # 14. Start strategy execution loop
        bot_logger.log_system_event("execution_loop_starting", "Starting strategy execution loop")
        
        # Keep the bot running
        await asyncio.Event().wait()
        
    except KeyboardInterrupt:
        bot_logger.log_system_event("system_shutdown", "Shutting down Trading Bot System (KeyboardInterrupt)")
    except Exception as e:
        bot_logger.log_error("system_error", "Unexpected error in main loop", exc_info=e)
        raise
    finally:
        # Graceful shutdown
        bot_logger.log_system_event("shutdown_starting", "Starting graceful shutdown")
        
        try:
            # Stop market data monitoring
            if market_data_manager:
                bot_logger.log_system_event("shutdown_market_data", "Stopping market data manager")
                await market_data_manager.stop_monitoring()
            
            # Disconnect from exchange
            if exchange:
                bot_logger.log_system_event("shutdown_exchange", "Disconnecting from exchange")
                await exchange.disconnect()
            
            # Close database
            if db:
                bot_logger.log_system_event("shutdown_database", "Closing database connection")
                await db.close()
            
            bot_logger.log_system_event("system_stopped", "Trading Bot System stopped")
            
        except Exception as e:
            bot_logger.log_error("shutdown_error", "Error during shutdown", exc_info=e)


if __name__ == "__main__":
    asyncio.run(main())
