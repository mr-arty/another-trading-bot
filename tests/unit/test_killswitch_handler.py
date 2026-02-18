"""Unit tests for Kill-Switch Handler."""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch
from dataclasses import dataclass

from src.killswitch.handler import KillSwitchHandler, KillSwitchSummary
from src.execution.executor import OrderExecutor
from src.position.tracker import PositionTracker, Position
from src.exchange.connector import ExchangeConnector, OrderResult
from src.strategy.engine import StrategyEngine


@pytest.fixture
def mock_order_executor():
    """Create mock order executor."""
    executor = Mock(spec=OrderExecutor)
    executor.cancel_all_orders = AsyncMock(return_value=["order1", "order2", "order3"])
    return executor


@pytest.fixture
def mock_position_tracker():
    """Create mock position tracker."""
    tracker = Mock(spec=PositionTracker)
    
    # Mock positions
    positions = [
        Position(
            symbol="BTCUSDT",
            strategy_name="strategy1",
            quantity=0.1,
            entry_price=50000.0,
            current_price=51000.0,
            side="Buy"
        ),
        Position(
            symbol="ETHUSDT",
            strategy_name="strategy2",
            quantity=1.0,
            entry_price=3000.0,
            current_price=3100.0,
            side="Buy"
        )
    ]
    
    tracker.get_all_positions = AsyncMock(return_value=positions)
    tracker.close_position = AsyncMock(return_value=100.0)  # Mock P&L
    
    return tracker


@pytest.fixture
def mock_exchange():
    """Create mock exchange connector."""
    exchange = Mock(spec=ExchangeConnector)
    
    # Mock successful position closure
    exchange.close_position = AsyncMock(
        return_value=OrderResult(
            success=True,
            order_id="close_order_1",
            message="Position closed"
        )
    )
    
    # Mock get_positions
    exchange.get_positions = AsyncMock(return_value=[])
    
    # Mock disconnect
    exchange.disconnect = AsyncMock()
    
    return exchange


@pytest.fixture
def mock_strategy_engine():
    """Create mock strategy engine."""
    engine = Mock(spec=StrategyEngine)
    
    # Mock strategies
    engine.get_all_strategies = Mock(return_value={
        "strategy1": Mock(),
        "strategy2": Mock()
    })
    
    engine.unregister_strategy = AsyncMock()
    
    return engine


@pytest.fixture
def kill_switch_handler(
    mock_order_executor,
    mock_position_tracker,
    mock_exchange,
    mock_strategy_engine
):
    """Create kill-switch handler with mocked dependencies."""
    return KillSwitchHandler(
        order_executor=mock_order_executor,
        position_tracker=mock_position_tracker,
        exchange=mock_exchange,
        strategy_engine=mock_strategy_engine
    )


class TestKillSwitchHandler:
    """Test suite for KillSwitchHandler."""
    
    @pytest.mark.asyncio
    async def test_initialization(self, kill_switch_handler):
        """Test kill-switch handler initialization."""
        assert not kill_switch_handler.is_active
        assert kill_switch_handler.summary is None
    
    @pytest.mark.asyncio
    async def test_cancel_all_orders(
        self,
        kill_switch_handler,
        mock_order_executor
    ):
        """Test cancelling all pending orders."""
        # Execute
        cancelled_orders = await kill_switch_handler.cancel_all_orders()
        
        # Verify
        assert len(cancelled_orders) == 3
        assert cancelled_orders == ["order1", "order2", "order3"]
        mock_order_executor.cancel_all_orders.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close_all_positions(
        self,
        kill_switch_handler,
        mock_position_tracker,
        mock_exchange
    ):
        """Test closing all open positions."""
        # Execute
        closed_positions = await kill_switch_handler.close_all_positions()
        
        # Verify
        assert len(closed_positions) == 2
        
        # Check first position
        assert closed_positions[0]["symbol"] == "BTCUSDT"
        assert closed_positions[0]["strategy_name"] == "strategy1"
        assert closed_positions[0]["quantity"] == 0.1
        assert closed_positions[0]["realized_pnl"] == 100.0
        
        # Check second position
        assert closed_positions[1]["symbol"] == "ETHUSDT"
        assert closed_positions[1]["strategy_name"] == "strategy2"
        
        # Verify exchange close_position was called twice
        assert mock_exchange.close_position.call_count == 2
        
        # Verify position tracker close_position was called twice
        assert mock_position_tracker.close_position.call_count == 2
    
    @pytest.mark.asyncio
    async def test_close_all_positions_empty(
        self,
        kill_switch_handler,
        mock_position_tracker
    ):
        """Test closing positions when no positions exist."""
        # Setup: No positions
        mock_position_tracker.get_all_positions = AsyncMock(return_value=[])
        
        # Execute
        closed_positions = await kill_switch_handler.close_all_positions()
        
        # Verify
        assert len(closed_positions) == 0
    
    @pytest.mark.asyncio
    async def test_close_position_failure(
        self,
        kill_switch_handler,
        mock_exchange
    ):
        """Test handling of position closure failure."""
        # Setup: Exchange returns failure
        mock_exchange.close_position = AsyncMock(
            return_value=OrderResult(
                success=False,
                order_id=None,
                message="Insufficient margin"
            )
        )
        
        # Execute
        closed_positions = await kill_switch_handler.close_all_positions()
        
        # Verify: No positions closed
        assert len(closed_positions) == 0
    
    @pytest.mark.asyncio
    async def test_stop_strategies(
        self,
        kill_switch_handler,
        mock_strategy_engine,
        mock_exchange
    ):
        """Test stopping all strategies."""
        # Execute
        await kill_switch_handler.stop_strategies()
        
        # Verify strategies were unregistered
        assert mock_strategy_engine.unregister_strategy.call_count == 2
        mock_strategy_engine.unregister_strategy.assert_any_call("strategy1")
        mock_strategy_engine.unregister_strategy.assert_any_call("strategy2")
        
        # Verify exchange was disconnected
        mock_exchange.disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_strategies_no_engine(
        self,
        mock_order_executor,
        mock_position_tracker,
        mock_exchange
    ):
        """Test stopping strategies when no strategy engine provided."""
        # Create handler without strategy engine
        handler = KillSwitchHandler(
            order_executor=mock_order_executor,
            position_tracker=mock_position_tracker,
            exchange=mock_exchange,
            strategy_engine=None
        )
        
        # Execute - should not raise error
        await handler.stop_strategies()
        
        # Verify exchange was still disconnected
        mock_exchange.disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_should_block_orders(self, kill_switch_handler):
        """Test order blocking check."""
        # Initially not active
        assert not kill_switch_handler.should_block_orders()
        
        # Trigger kill-switch
        await kill_switch_handler.trigger()
        
        # Now should block orders
        assert kill_switch_handler.should_block_orders()
    
    @pytest.mark.asyncio
    async def test_trigger_full_sequence(
        self,
        kill_switch_handler,
        mock_order_executor,
        mock_position_tracker,
        mock_exchange,
        mock_strategy_engine
    ):
        """Test full kill-switch trigger sequence."""
        # Execute
        summary = await kill_switch_handler.trigger()
        
        # Verify kill-switch is active
        assert kill_switch_handler.is_active
        
        # Verify summary
        assert isinstance(summary, KillSwitchSummary)
        assert len(summary.cancelled_orders) == 3
        assert len(summary.closed_positions) == 2
        assert summary.execution_time_seconds >= 0
        assert isinstance(summary.triggered_at, datetime)
        
        # Verify all components were called
        mock_order_executor.cancel_all_orders.assert_called_once()
        mock_position_tracker.get_all_positions.assert_called()
        mock_exchange.close_position.assert_called()
        mock_strategy_engine.unregister_strategy.assert_called()
        mock_exchange.disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_trigger_idempotent(self, kill_switch_handler):
        """Test that triggering kill-switch multiple times is idempotent."""
        # First trigger
        summary1 = await kill_switch_handler.trigger()
        
        # Second trigger
        summary2 = await kill_switch_handler.trigger()
        
        # Should return same summary
        assert summary1 == summary2
    
    @pytest.mark.asyncio
    async def test_trigger_with_exception(
        self,
        kill_switch_handler,
        mock_order_executor
    ):
        """Test kill-switch trigger continues despite exception in one step."""
        # Setup: Make cancel_all_orders raise exception
        mock_order_executor.cancel_all_orders = AsyncMock(
            side_effect=Exception("Connection error")
        )
        
        # Execute - should not raise exception, but continue with other steps
        summary = await kill_switch_handler.trigger()
        
        # Verify kill-switch completed despite error
        assert kill_switch_handler.is_active
        assert isinstance(summary, KillSwitchSummary)
        # Orders won't be cancelled due to error, but positions should still close
        assert len(summary.cancelled_orders) == 0
        assert len(summary.closed_positions) == 2
    
    @pytest.mark.asyncio
    async def test_get_final_account_state(
        self,
        kill_switch_handler,
        mock_position_tracker,
        mock_exchange
    ):
        """Test getting final account state."""
        # Setup: Some positions remain
        remaining_positions = [
            Position(
                symbol="BTCUSDT",
                strategy_name="strategy1",
                quantity=0.05,
                entry_price=50000.0,
                current_price=51000.0,
                unrealized_pnl=50.0,
                side="Buy"
            )
        ]
        mock_position_tracker.get_all_positions = AsyncMock(
            return_value=remaining_positions
        )
        
        # Execute
        account_state = await kill_switch_handler._get_final_account_state()
        
        # Verify
        assert account_state["open_positions_count"] == 1
        assert account_state["exchange_positions_count"] == 0
        assert len(account_state["positions"]) == 1
        assert account_state["positions"][0]["symbol"] == "BTCUSDT"
    
    def test_setup_signal_handler(self, kill_switch_handler):
        """Test signal handler setup."""
        # Execute
        kill_switch_handler.setup_signal_handler()
        
        # Note: Actual signal handling is difficult to test in unit tests
        # This just verifies the method doesn't raise an error
        # Integration tests would be better for testing signal handling


class TestKillSwitchIntegration:
    """Integration tests for kill-switch handler."""
    
    @pytest.mark.asyncio
    async def test_concurrent_trigger_attempts(
        self,
        kill_switch_handler
    ):
        """Test multiple concurrent trigger attempts."""
        # Execute multiple triggers concurrently
        results = await asyncio.gather(
            kill_switch_handler.trigger(),
            kill_switch_handler.trigger(),
            kill_switch_handler.trigger()
        )
        
        # All should return the same summary
        assert results[0] == results[1] == results[2]
        
        # Kill-switch should be active
        assert kill_switch_handler.is_active
