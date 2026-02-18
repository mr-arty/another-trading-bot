"""
Kill-Switch Handler for emergency shutdown functionality.

Provides immediate shutdown capabilities including:
- Cancelling all pending orders
- Closing all open positions
- Preventing new orders
- Stopping strategy execution
- Logging final state
"""

import asyncio
import signal
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from src.execution.executor import OrderExecutor
from src.position.tracker import PositionTracker
from src.exchange.connector import ExchangeConnector
from src.strategy.engine import StrategyEngine


logger = logging.getLogger(__name__)


@dataclass
class KillSwitchSummary:
    """Summary of kill-switch execution."""
    triggered_at: datetime
    cancelled_orders: List[str]
    closed_positions: List[Dict[str, Any]]
    final_account_state: Dict[str, Any]
    execution_time_seconds: float


class KillSwitchHandler:
    """
    Emergency shutdown handler for the trading bot.
    
    Provides kill-switch functionality to immediately:
    1. Cancel all pending orders
    2. Close all open positions at market price
    3. Block new orders
    4. Stop all strategy execution
    5. Log summary of actions taken
    """
    
    def __init__(
        self,
        order_executor: OrderExecutor,
        position_tracker: PositionTracker,
        exchange: ExchangeConnector,
        strategy_engine: Optional[StrategyEngine] = None
    ):
        """
        Initialize Kill-Switch Handler.
        
        Args:
            order_executor: Order executor for cancelling orders
            position_tracker: Position tracker for managing positions
            exchange: Exchange connector for closing positions
            strategy_engine: Strategy engine for stopping strategies (optional)
        """
        self.order_executor = order_executor
        self.position_tracker = position_tracker
        self.exchange = exchange
        self.strategy_engine = strategy_engine
        
        # Kill-switch state
        self._active = False
        self._triggered_at: Optional[datetime] = None
        self._summary: Optional[KillSwitchSummary] = None
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        
        logger.info("Kill-switch handler initialized")
    
    @property
    def is_active(self) -> bool:
        """Check if kill-switch is currently active."""
        return self._active
    
    @property
    def summary(self) -> Optional[KillSwitchSummary]:
        """Get summary of last kill-switch execution."""
        return self._summary
    
    async def trigger(self) -> KillSwitchSummary:
        """
        Trigger kill-switch: cancel orders, close positions, stop trading.
        
        Executes emergency shutdown sequence:
        1. Cancel all pending orders
        2. Close all open positions at market
        3. Stop all strategy execution
        4. Unsubscribe from market data
        5. Log summary
        
        Returns:
            KillSwitchSummary with details of actions taken
        """
        async with self._lock:
            if self._active:
                logger.warning("Kill-switch already active")
                return self._summary
            
            start_time = datetime.utcnow()
            self._active = True
            self._triggered_at = start_time
            
            logger.critical("KILL-SWITCH TRIGGERED - Emergency shutdown initiated")
            
            try:
                # Step 1: Cancel all pending orders
                logger.info("Kill-switch: Cancelling all pending orders...")
                cancelled_orders = await self.cancel_all_orders()
                logger.info(f"Kill-switch: Cancelled {len(cancelled_orders)} orders")
                
                # Step 2: Close all open positions
                logger.info("Kill-switch: Closing all open positions...")
                closed_positions = await self.close_all_positions()
                logger.info(f"Kill-switch: Closed {len(closed_positions)} positions")
                
                # Step 3: Stop all strategy execution
                logger.info("Kill-switch: Stopping all strategies...")
                await self.stop_strategies()
                logger.info("Kill-switch: All strategies stopped")
                
                # Step 4: Get final account state
                logger.info("Kill-switch: Fetching final account state...")
                final_state = await self._get_final_account_state()
                
                # Calculate execution time
                end_time = datetime.utcnow()
                execution_time = (end_time - start_time).total_seconds()
                
                # Create summary
                self._summary = KillSwitchSummary(
                    triggered_at=start_time,
                    cancelled_orders=cancelled_orders,
                    closed_positions=closed_positions,
                    final_account_state=final_state,
                    execution_time_seconds=execution_time
                )
                
                # Log summary
                await self._log_summary(self._summary)
                
                logger.critical(
                    f"KILL-SWITCH COMPLETED - Shutdown finished in {execution_time:.2f}s"
                )
                
                return self._summary
                
            except Exception as e:
                logger.error(
                    f"Kill-switch execution error: {str(e)}",
                    exc_info=True
                )
                raise
    
    async def cancel_all_orders(self) -> List[str]:
        """
        Cancel all pending orders across all strategies.
        
        Returns:
            List of cancelled order IDs
        """
        try:
            cancelled_orders = await self.order_executor.cancel_all_orders()
            
            logger.info(
                f"Kill-switch: Successfully cancelled {len(cancelled_orders)} orders"
            )
            
            return cancelled_orders
            
        except Exception as e:
            logger.error(
                f"Kill-switch: Error cancelling orders: {str(e)}",
                exc_info=True
            )
            return []
    
    async def close_all_positions(self) -> List[Dict[str, Any]]:
        """
        Close all open positions at market price.
        
        Returns:
            List of closed position details
        """
        closed_positions = []
        
        try:
            # Get all open positions
            positions = await self.position_tracker.get_all_positions()
            
            if not positions:
                logger.info("Kill-switch: No open positions to close")
                return closed_positions
            
            logger.info(f"Kill-switch: Found {len(positions)} open positions to close")
            
            # Close each position
            for position in positions:
                try:
                    # Close position via exchange
                    result = await self.exchange.close_position(
                        symbol=position.symbol,
                        side=position.side
                    )
                    
                    if result.success:
                        # Update position tracker
                        realized_pnl = await self.position_tracker.close_position(
                            symbol=position.symbol,
                            strategy_name=position.strategy_name,
                            exit_price=position.current_price or position.entry_price,
                            exit_reason="kill_switch"
                        )
                        
                        closed_position_info = {
                            "symbol": position.symbol,
                            "strategy_name": position.strategy_name,
                            "quantity": position.quantity,
                            "entry_price": position.entry_price,
                            "exit_price": position.current_price or position.entry_price,
                            "realized_pnl": realized_pnl,
                            "order_id": result.order_id
                        }
                        
                        closed_positions.append(closed_position_info)
                        
                        logger.info(
                            f"Kill-switch: Closed position {position.symbol} "
                            f"for {position.strategy_name}, P&L: {realized_pnl}"
                        )
                    else:
                        logger.error(
                            f"Kill-switch: Failed to close position {position.symbol}: "
                            f"{result.message}"
                        )
                        
                except Exception as e:
                    logger.error(
                        f"Kill-switch: Error closing position {position.symbol}: {str(e)}",
                        exc_info=True
                    )
            
            return closed_positions
            
        except Exception as e:
            logger.error(
                f"Kill-switch: Error in close_all_positions: {str(e)}",
                exc_info=True
            )
            return closed_positions
    
    def should_block_orders(self) -> bool:
        """
        Check if new orders should be blocked.
        
        Returns:
            True if kill-switch is active and orders should be blocked
        """
        return self._active
    
    async def stop_strategies(self) -> None:
        """
        Stop all strategy execution and unsubscribe from market data.
        """
        try:
            if self.strategy_engine:
                # Get all registered strategies
                strategies = self.strategy_engine.get_all_strategies()
                
                logger.info(
                    f"Kill-switch: Stopping {len(strategies)} strategies"
                )
                
                # Unregister each strategy
                for strategy_name in list(strategies.keys()):
                    try:
                        await self.strategy_engine.unregister_strategy(strategy_name)
                        logger.info(f"Kill-switch: Stopped strategy {strategy_name}")
                    except Exception as e:
                        logger.error(
                            f"Kill-switch: Error stopping strategy {strategy_name}: {str(e)}",
                            exc_info=True
                        )
            
            # Disconnect from exchange (unsubscribes from market data)
            try:
                await self.exchange.disconnect()
                logger.info("Kill-switch: Disconnected from exchange")
            except Exception as e:
                logger.error(
                    f"Kill-switch: Error disconnecting from exchange: {str(e)}",
                    exc_info=True
                )
                
        except Exception as e:
            logger.error(
                f"Kill-switch: Error in stop_strategies: {str(e)}",
                exc_info=True
            )
    
    async def _get_final_account_state(self) -> Dict[str, Any]:
        """
        Get final account state after kill-switch execution.
        
        Returns:
            Dictionary with account state information
        """
        try:
            # Get all positions (should be empty after closing)
            positions = await self.position_tracker.get_all_positions()
            
            # Get exchange positions to verify
            exchange_positions = await self.exchange.get_positions()
            
            # Calculate total P&L from order history
            # This would require querying the database for all closed positions
            
            account_state = {
                "timestamp": datetime.utcnow().isoformat(),
                "open_positions_count": len(positions),
                "exchange_positions_count": len(exchange_positions),
                "positions": [
                    {
                        "symbol": p.symbol,
                        "quantity": p.quantity,
                        "entry_price": p.entry_price,
                        "unrealized_pnl": p.unrealized_pnl
                    }
                    for p in positions
                ]
            }
            
            return account_state
            
        except Exception as e:
            logger.error(
                f"Kill-switch: Error getting final account state: {str(e)}",
                exc_info=True
            )
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
    
    async def _log_summary(self, summary: KillSwitchSummary) -> None:
        """
        Log detailed summary of kill-switch execution.
        
        Args:
            summary: Kill-switch execution summary
        """
        logger.critical("=" * 80)
        logger.critical("KILL-SWITCH EXECUTION SUMMARY")
        logger.critical("=" * 80)
        logger.critical(f"Triggered at: {summary.triggered_at.isoformat()}")
        logger.critical(f"Execution time: {summary.execution_time_seconds:.2f} seconds")
        logger.critical("")
        
        # Log cancelled orders
        logger.critical(f"Cancelled Orders: {len(summary.cancelled_orders)}")
        for order_id in summary.cancelled_orders:
            logger.critical(f"  - Order ID: {order_id}")
        logger.critical("")
        
        # Log closed positions
        logger.critical(f"Closed Positions: {len(summary.closed_positions)}")
        total_pnl = 0.0
        for position in summary.closed_positions:
            pnl = position.get("realized_pnl", 0.0)
            total_pnl += pnl if pnl else 0.0
            logger.critical(
                f"  - {position['symbol']} ({position['strategy_name']}): "
                f"Qty={position['quantity']}, "
                f"Entry={position['entry_price']}, "
                f"Exit={position['exit_price']}, "
                f"P&L={pnl}"
            )
        logger.critical(f"Total Realized P&L: {total_pnl}")
        logger.critical("")
        
        # Log final account state
        logger.critical("Final Account State:")
        logger.critical(f"  Open Positions: {summary.final_account_state.get('open_positions_count', 0)}")
        logger.critical(f"  Exchange Positions: {summary.final_account_state.get('exchange_positions_count', 0)}")
        logger.critical("")
        logger.critical("=" * 80)
    
    def setup_signal_handler(self) -> None:
        """
        Setup signal handler for kill-switch trigger.
        
        Registers SIGINT (Ctrl+C) and SIGTERM handlers to trigger kill-switch.
        """
        def signal_handler(signum, frame):
            """Handle termination signals."""
            logger.critical(f"Received signal {signum}, triggering kill-switch...")
            
            # Create event loop if needed and trigger kill-switch
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self.trigger())
                else:
                    loop.run_until_complete(self.trigger())
            except Exception as e:
                logger.error(f"Error triggering kill-switch from signal: {str(e)}")
        
        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        logger.info("Kill-switch signal handlers registered (SIGINT, SIGTERM)")
