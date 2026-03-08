"""Integration tests for main application orchestration."""

import pytest
import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

# Set up test environment
os.environ["BYBIT_API_KEY"] = "test_key"
os.environ["BYBIT_API_SECRET"] = "test_secret"
os.environ["BYBIT_TESTNET"] = "true"
os.environ["STRATEGIES_DIR"] = "./strategies"


@pytest.mark.asyncio
async def test_main_initialization_sequence():
    """Test that main application initializes all components in correct order."""
    from src.config.config import load_config
    from src.database.db import Database
    from src.exchange.connector import ExchangeConnector
    from src.indicators.calculator import IndicatorCalculator
    from src.market_data.manager import MarketDataManager
    from src.position.tracker import PositionTracker
    from src.execution.executor import OrderExecutor
    from src.risk.manager import RiskManager
    from src.strategy.engine import StrategyEngine
    from src.monitoring.volatility import VolatilityMonitor
    from src.killswitch.handler import KillSwitchHandler
    
    # Create strategies directory if it doesn't exist
    Path("./strategies").mkdir(exist_ok=True)
    
    # 1. Load configuration
    config = await load_config()
    assert config is not None
    assert config.exchange_api_key == "test_key"
    
    # 2. Initialize database
    db = Database()
    await db.initialize()
    assert db is not None
    
    try:
        # 3. Initialize exchange connector (mock the connection)
        with patch.object(ExchangeConnector, 'connect', new_callable=AsyncMock):
            exchange = ExchangeConnector(
                api_key=config.exchange_api_key,
                api_secret=config.exchange_api_secret,
                testnet=config.exchange_testnet,
                rate_limit_per_second=config.api_rate_limit_per_second,
                max_reconnect_delay=config.reconnect_max_delay_seconds
            )
            await exchange.connect()
            assert exchange is not None
        
        # 4. Initialize indicator calculator
        indicator_calculator = IndicatorCalculator(cache_ttl_seconds=60)
        assert indicator_calculator is not None
        
        # 5. Initialize market data manager
        market_data_manager = MarketDataManager(
            exchange_connector=exchange,
            interruption_threshold_seconds=30
        )
        assert market_data_manager is not None
        
        # 6. Initialize position tracker
        position_tracker = PositionTracker(database=db)
        await position_tracker.load_state()
        assert position_tracker is not None
        
        # 7. Initialize order executor
        order_executor = OrderExecutor(
            exchange=exchange,
            position_tracker=position_tracker,
            database=db,
            max_retries=config.order_retry_attempts,
            retry_base_delay=1.0
        )
        assert order_executor is not None
        
        # 8. Initialize risk manager
        risk_manager = RiskManager(
            config=config,
            signal_callback=order_executor.execute_signal
        )
        assert risk_manager is not None
        
        # 9. Initialize strategy engine
        strategy_engine = StrategyEngine(
            indicator_calculator=indicator_calculator,
            signal_callback=risk_manager.process_signal
        )
        assert strategy_engine is not None
        
        # 10. Initialize volatility monitor
        volatility_monitor = VolatilityMonitor(
            database=db,
            market_data_manager=market_data_manager,
            atr_threshold=config.volatility_threshold,
            atr_period=14
        )
        assert volatility_monitor is not None
        
        # 11. Initialize kill-switch handler
        kill_switch = KillSwitchHandler(
            order_executor=order_executor,
            position_tracker=position_tracker,
            exchange=exchange,
            strategy_engine=strategy_engine
        )
        assert kill_switch is not None
        assert not kill_switch.is_active
        
        # Verify component wiring
        assert order_executor.exchange == exchange
        assert order_executor.position_tracker == position_tracker
        assert risk_manager.signal_callback == order_executor.execute_signal
        assert strategy_engine.signal_callback == risk_manager.process_signal
        
    finally:
        # Cleanup
        await db.close()


@pytest.mark.asyncio
async def test_graceful_shutdown():
    """Test that application shuts down gracefully."""
    from src.database.db import Database
    from src.exchange.connector import ExchangeConnector
    from src.market_data.manager import MarketDataManager
    
    db = Database()
    await db.initialize()
    
    with patch.object(ExchangeConnector, 'connect', new_callable=AsyncMock):
        with patch.object(ExchangeConnector, 'disconnect', new_callable=AsyncMock) as mock_disconnect:
            exchange = ExchangeConnector(
                api_key="test_key",
                api_secret="test_secret",
                testnet=True
            )
            await exchange.connect()
            
            market_data_manager = MarketDataManager(
                exchange_connector=exchange,
                interruption_threshold_seconds=30
            )
            await market_data_manager.start_monitoring()
            
            # Simulate shutdown
            await market_data_manager.stop_monitoring()
            await exchange.disconnect()
            await db.close()
            
            # Verify disconnect was called
            mock_disconnect.assert_called_once()


@pytest.mark.asyncio
async def test_component_dependencies():
    """Test that components have correct dependencies wired."""
    from src.config.config import load_config
    from src.database.db import Database
    from src.exchange.connector import ExchangeConnector
    from src.indicators.calculator import IndicatorCalculator
    from src.position.tracker import PositionTracker
    from src.execution.executor import OrderExecutor
    from src.risk.manager import RiskManager
    from src.strategy.engine import StrategyEngine
    
    config = await load_config()
    db = Database()
    await db.initialize()
    
    try:
        with patch.object(ExchangeConnector, 'connect', new_callable=AsyncMock):
            exchange = ExchangeConnector(
                api_key=config.exchange_api_key,
                api_secret=config.exchange_api_secret,
                testnet=True
            )
            await exchange.connect()
            
            indicator_calculator = IndicatorCalculator()
            position_tracker = PositionTracker(database=db)
            await position_tracker.load_state()
            
            order_executor = OrderExecutor(
                exchange=exchange,
                position_tracker=position_tracker,
                database=db
            )
            
            risk_manager = RiskManager(
                config=config,
                signal_callback=order_executor.execute_signal
            )
            
            strategy_engine = StrategyEngine(
                indicator_calculator=indicator_calculator,
                signal_callback=risk_manager.process_signal
            )
            
            # Verify dependency chain
            # Strategy Engine -> Risk Manager -> Order Executor -> Exchange
            assert strategy_engine.signal_callback == risk_manager.process_signal
            assert risk_manager.signal_callback == order_executor.execute_signal
            assert order_executor.exchange == exchange
            
    finally:
        await db.close()
