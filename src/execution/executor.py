"""
Order Executor module for submitting and tracking orders
"""
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Callable, List, TYPE_CHECKING
from enum import Enum

from src.exchange.connector import (
    ExchangeConnector, Order, OrderResult, OrderSide, 
    OrderType, OrderStatus
)
from src.position.tracker import PositionTracker, OrderFill
from src.database.db import Database

if TYPE_CHECKING:
    from src.killswitch.handler import KillSwitchHandler


logger = logging.getLogger(__name__)


class OrderExecutor:
    """
    Executes trading signals as orders on the exchange.
    Tracks order status and updates position tracker on fills.
    """
    
    def __init__(
        self,
        exchange: ExchangeConnector,
        position_tracker: PositionTracker,
        database: Database,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
        kill_switch_handler: Optional['KillSwitchHandler'] = None
    ):
        """
        Initialize Order Executor.
        
        Args:
            exchange: Exchange connector for order submission
            position_tracker: Position tracker for updating positions
            database: Database for storing order history
            max_retries: Maximum number of retry attempts for failed submissions
            retry_base_delay: Base delay in seconds for exponential backoff
            kill_switch_handler: Optional kill-switch handler for order prevention
        """
        self.exchange = exchange
        self.position_tracker = position_tracker
        self.database = database
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay
        self.kill_switch_handler = kill_switch_handler
        
        # Track active orders: order_id -> (order, strategy_callback)
        self.active_orders: Dict[str, tuple[Order, Optional[Callable]]] = {}
        
        # Track order monitoring tasks
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        
        # Strategy notification callbacks: strategy_name -> callback
        self.strategy_callbacks: Dict[str, Callable] = {}
        
    def register_strategy_callback(
        self, 
        strategy_name: str, 
        callback: Callable
    ) -> None:
        """
        Register a callback for strategy notifications.
        
        Args:
            strategy_name: Name of the strategy
            callback: Async callback function(order_id, status, fill_info)
        """
        self.strategy_callbacks[strategy_name] = callback
        
    async def execute_signal(self, signal) -> Optional[str]:
        """
        Execute a validated signal as an order.
        
        Args:
            signal: Trading signal to execute
            
        Returns:
            Order ID if successful, None otherwise
        """
        # Check if kill-switch is active
        if self.kill_switch_handler and self.kill_switch_handler.should_block_orders():
            logger.warning(
                f"Order blocked by kill-switch: strategy={signal.strategy_name}, "
                f"symbol={signal.symbol}, side={signal.side}"
            )
            return None
        
        # Create order from signal
        order = self._create_order_from_signal(signal)
        
        # Submit order with retry logic
        order_id = await self._submit_order_with_retry(order)
        
        if order_id:
            # Store order in active orders
            callback = self.strategy_callbacks.get(signal.strategy_name)
            self.active_orders[order_id] = (order, callback)
            
            # Start tracking order status
            task = asyncio.create_task(self.track_order(order_id))
            self.monitoring_tasks[order_id] = task
            
            logger.info(
                f"Order submitted: order_id={order_id}, "
                f"strategy={signal.strategy_name}, symbol={signal.symbol}, "
                f"side={signal.side}, quantity={signal.quantity}"
            )
            
        return order_id
        
    def _create_order_from_signal(self, signal) -> Order:
        """
        Create an Order from a Signal.
        
        Args:
            signal: Trading signal
            
        Returns:
            Order object
        """
        # Map signal side to OrderSide enum
        side = OrderSide.BUY if signal.side == 'buy' else OrderSide.SELL
        
        # Determine order type based on whether price is specified
        order_type = OrderType.LIMIT if signal.price else OrderType.MARKET
        
        order = Order(
            order_id="",  # Will be assigned by exchange
            strategy_name=signal.strategy_name,
            symbol=signal.symbol,
            side=side,
            order_type=order_type,
            quantity=signal.quantity,
            price=signal.price,
            status=OrderStatus.PENDING,
            timestamp=signal.timestamp
        )
        
        return order
        
    async def _submit_order_with_retry(self, order: Order) -> Optional[str]:
        """
        Submit order with exponential backoff retry logic.
        
        Args:
            order: Order to submit
            
        Returns:
            Order ID if successful, None otherwise
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                # Submit order to exchange
                result = await self.exchange.place_order(
                    symbol=order.symbol,
                    side=order.side,
                    order_type=order.order_type,
                    quantity=order.quantity,
                    price=order.price
                )
                
                if result.success:
                    # Store order in database
                    await self._store_order_history(
                        order_id=result.order_id,
                        order=order,
                        status=OrderStatus.PENDING
                    )
                    return result.order_id
                else:
                    last_error = result.message
                    logger.warning(
                        f"Order submission failed (attempt {attempt + 1}): "
                        f"strategy={order.strategy_name}, symbol={order.symbol}, "
                        f"error={result.message}"
                    )
                    
            except Exception as e:
                last_error = str(e)
                logger.error(
                    f"Order submission exception (attempt {attempt + 1}): "
                    f"strategy={order.strategy_name}, symbol={order.symbol}, "
                    f"error={str(e)}",
                    exc_info=True
                )
            
            # Exponential backoff before retry
            if attempt < self.max_retries - 1:
                delay = self.retry_base_delay * (2 ** attempt)
                logger.info(
                    f"Retrying order submission (attempt {attempt + 1}), "
                    f"delay={delay}s"
                )
                await asyncio.sleep(delay)
        
        # All retries failed
        logger.error(
            f"Order submission failed after all retries: "
            f"strategy={order.strategy_name}, symbol={order.symbol}, "
            f"error={last_error}"
        )
        return None
        
    async def track_order(self, order_id: str) -> None:
        """
        Track order status until filled or cancelled.
        
        Args:
            order_id: Order ID to track
        """
        if order_id not in self.active_orders:
            logger.warning(f"Order not found for tracking: order_id={order_id}")
            return
            
        order, callback = self.active_orders[order_id]
        
        # Track remaining quantity for partial fills
        remaining_quantity = order.quantity
        filled_quantity = 0.0
        
        try:
            # Poll order status periodically
            while True:
                # In a real implementation, we would query the exchange
                # For now, we'll simulate by checking exchange state
                # This would be replaced with actual exchange API calls
                
                # Wait before next check
                await asyncio.sleep(1.0)
                
                # Check if order is still active
                # This is a placeholder - actual implementation would
                # query exchange API for order status
                
                # For now, we'll break after one iteration
                # Real implementation would continue until filled/cancelled
                break
                
        except asyncio.CancelledError:
            logger.info(f"Order tracking cancelled: order_id={order_id}")
            raise
        except Exception as e:
            logger.error(
                f"Order tracking error: order_id={order_id}, error={str(e)}",
                exc_info=True
            )
        finally:
            # Clean up
            if order_id in self.active_orders:
                del self.active_orders[order_id]
            if order_id in self.monitoring_tasks:
                del self.monitoring_tasks[order_id]
                
    async def _handle_order_fill(
        self,
        order_id: str,
        order: Order,
        fill_quantity: float,
        fill_price: float,
        fee: float = 0.0
    ) -> None:
        """
        Handle order fill event.
        
        Args:
            order_id: Order ID
            order: Order object
            fill_quantity: Quantity filled
            fill_price: Fill price
            fee: Trading fee
        """
        # Create OrderFill object
        fill = OrderFill(
            order_id=order_id,
            symbol=order.symbol,
            side='buy' if order.side == OrderSide.BUY else 'sell',
            quantity=fill_quantity,
            price=fill_price,
            fee=fee,
            timestamp=datetime.utcnow()
        )
        
        # Update position tracker
        await self.position_tracker.update_position(
            symbol=order.symbol,
            fill=fill,
            strategy_name=order.strategy_name
        )
        
        # Update order status in database
        status = OrderStatus.FILLED
        await self._update_order_status(
            order_id=order_id,
            status=status,
            filled_quantity=fill_quantity
        )
        
        # Notify strategy
        await self._notify_strategy(
            order_id=order_id,
            order=order,
            status=status,
            fill_info=fill
        )
        
        logger.info(
            f"Order filled: order_id={order_id}, strategy={order.strategy_name}, "
            f"symbol={order.symbol}, quantity={fill_quantity}, price={fill_price}"
        )
        
    async def _handle_partial_fill(
        self,
        order_id: str,
        order: Order,
        fill_quantity: float,
        fill_price: float,
        remaining_quantity: float,
        fee: float = 0.0
    ) -> None:
        """
        Handle partial order fill event.
        
        Args:
            order_id: Order ID
            order: Order object
            fill_quantity: Quantity filled in this partial fill
            fill_price: Fill price
            remaining_quantity: Remaining unfilled quantity
            fee: Trading fee
        """
        # Create OrderFill object
        fill = OrderFill(
            order_id=order_id,
            symbol=order.symbol,
            side='buy' if order.side == OrderSide.BUY else 'sell',
            quantity=fill_quantity,
            price=fill_price,
            fee=fee,
            timestamp=datetime.utcnow()
        )
        
        # Update position tracker with partial fill
        await self.position_tracker.update_position(
            symbol=order.symbol,
            fill=fill,
            strategy_name=order.strategy_name
        )
        
        # Update order status in database
        total_filled = order.quantity - remaining_quantity
        await self._update_order_status(
            order_id=order_id,
            status=OrderStatus.PARTIALLY_FILLED,
            filled_quantity=total_filled
        )
        
        # Notify strategy of partial fill
        await self._notify_strategy(
            order_id=order_id,
            order=order,
            status=OrderStatus.PARTIALLY_FILLED,
            fill_info=fill
        )
        
        logger.info(
            f"Order partially filled: order_id={order_id}, "
            f"strategy={order.strategy_name}, symbol={order.symbol}, "
            f"filled_quantity={fill_quantity}, remaining_quantity={remaining_quantity}, "
            f"price={fill_price}"
        )
        
    async def _notify_strategy(
        self,
        order_id: str,
        order: Order,
        status: OrderStatus,
        fill_info: Optional[OrderFill] = None
    ) -> None:
        """
        Notify originating strategy of order status.
        
        Args:
            order_id: Order ID
            order: Order object
            status: Order status
            fill_info: Fill information if order was filled
        """
        callback = self.strategy_callbacks.get(order.strategy_name)
        
        if callback:
            try:
                await callback(order_id, status, fill_info)
            except Exception as e:
                logger.error(
                    f"Strategy notification error: order_id={order_id}, "
                    f"strategy={order.strategy_name}, error={str(e)}",
                    exc_info=True
                )
                
    async def _store_order_history(
        self,
        order_id: str,
        order: Order,
        status: OrderStatus
    ) -> None:
        """
        Store order in database.
        
        Args:
            order_id: Order ID
            order: Order object
            status: Order status
        """
        conn = await self.database.get_connection()
        
        await conn.execute(
            """
            INSERT INTO order_history (
                order_id, strategy_name, symbol, side, order_type,
                quantity, price, filled_quantity, status,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                order_id,
                order.strategy_name,
                order.symbol,
                order.side.value,
                order.order_type.value,
                order.quantity,
                order.price,
                0.0,  # Initial filled quantity
                status.value,
                order.timestamp,
                datetime.utcnow()
            )
        )
        
        await conn.commit()
        
    async def _update_order_status(
        self,
        order_id: str,
        status: OrderStatus,
        filled_quantity: float
    ) -> None:
        """
        Update order status in database.
        
        Args:
            order_id: Order ID
            status: New order status
            filled_quantity: Total filled quantity
        """
        conn = await self.database.get_connection()
        
        await conn.execute(
            """
            UPDATE order_history
            SET status = ?, filled_quantity = ?, updated_at = ?
            WHERE order_id = ?
            """,
            (status.value, filled_quantity, datetime.utcnow(), order_id)
        )
        
        await conn.commit()
        
    async def cancel_all_orders(self) -> List[str]:
        """
        Cancel all pending orders.
        
        Returns:
            List of cancelled order IDs
        """
        cancelled_orders = []
        
        for order_id, (order, _) in list(self.active_orders.items()):
            try:
                success = await self.exchange.cancel_order(
                    symbol=order.symbol,
                    order_id=order_id
                )
                
                if success:
                    cancelled_orders.append(order_id)
                    
                    # Update database
                    await self._update_order_status(
                        order_id=order_id,
                        status=OrderStatus.CANCELLED,
                        filled_quantity=0.0
                    )
                    
                    # Cancel monitoring task
                    if order_id in self.monitoring_tasks:
                        self.monitoring_tasks[order_id].cancel()
                        
                    logger.info(
                        f"Order cancelled: order_id={order_id}, "
                        f"strategy={order.strategy_name}"
                    )
                    
            except Exception as e:
                logger.error(
                    f"Order cancellation error: order_id={order_id}, error={str(e)}",
                    exc_info=True
                )
                
        return cancelled_orders
        
    async def get_order_status(self, order_id: str) -> Optional[OrderStatus]:
        """
        Get current status of an order.
        
        Args:
            order_id: Order ID
            
        Returns:
            Order status or None if not found
        """
        conn = await self.database.get_connection()
        
        async with conn.execute(
            "SELECT status FROM order_history WHERE order_id = ?",
            (order_id,)
        ) as cursor:
            row = await cursor.fetchone()
            
        if row:
            return OrderStatus(row[0])
        return None
        
    async def get_order_history(
        self,
        strategy_name: Optional[str] = None,
        symbol: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get order history from database.
        
        Args:
            strategy_name: Filter by strategy name
            symbol: Filter by symbol
            limit: Maximum number of records
            
        Returns:
            List of order records
        """
        conn = await self.database.get_connection()
        
        query = "SELECT * FROM order_history WHERE 1=1"
        params = []
        
        if strategy_name:
            query += " AND strategy_name = ?"
            params.append(strategy_name)
            
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
            
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        async with conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
        return [dict(zip(columns, row)) for row in rows]
