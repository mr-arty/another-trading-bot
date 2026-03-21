"""Position tracking for managing trading positions and P&L calculation."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Tuple
import structlog

from src.database.db import Database


logger = structlog.get_logger(__name__)


@dataclass
class Position:
    """
    Position data structure.
    
    Represents a trading position with entry price, current quantity,
    and P&L tracking.
    """
    symbol: str
    strategy_name: str
    quantity: float
    entry_price: float
    current_price: Optional[float] = None
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    status: str = "open"  # 'open' or 'closed'
    opened_at: datetime = field(default_factory=datetime.utcnow)
    closed_at: Optional[datetime] = None
    side: str = "Buy"  # 'Buy' for long, 'Sell' for short


@dataclass
class OrderFill:
    """
    Order fill data structure.
    
    Represents a filled order with execution details.
    """
    order_id: str
    symbol: str
    side: str  # 'Buy' or 'Sell'
    quantity: float
    price: float
    fee: float
    timestamp: datetime
    strategy_name: str = ""


class PositionTracker:
    """
    Position tracker for managing positions and calculating P&L.
    
    Handles:
    - Position updates on order fills
    - Average entry price calculation
    - Realized and unrealized P&L calculation
    - Position persistence to database
    - Position synchronization with exchange
    """
    
    def __init__(self, database: Database):
        """
        Initialize position tracker.
        
        Args:
            database: Database instance for persistence
        """
        self.database = database
        
        # Track positions: {(strategy_name, symbol): Position}
        self._positions: Dict[Tuple[str, str], Position] = {}
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        
        logger.info("position_tracker_initialized")
    
    async def update_position(
        self,
        symbol: str,
        fill: OrderFill,
        strategy_name: Optional[str] = None
    ) -> None:
        """
        Update position based on order fill.
        
        For buy fills: Increases position quantity and calculates new average entry price
        For sell fills: Decreases position quantity and calculates realized P&L
        
        Args:
            symbol: Trading symbol
            fill: Order fill details
            strategy_name: Strategy name (uses fill.strategy_name if not provided)
        """
        async with self._lock:
            strat_name = strategy_name or fill.strategy_name
            position_key = (strat_name, symbol)
            
            # Get or create position
            position = self._positions.get(position_key)
            
            if fill.side == "Buy":
                await self._handle_buy_fill(position_key, position, fill, strat_name)
            elif fill.side == "Sell":
                await self._handle_sell_fill(position_key, position, fill, strat_name)
            
            # Persist position state
            await self._persist_position(position_key)
            
            logger.info(
                "position_updated",
                strategy=strat_name,
                symbol=symbol,
                side=fill.side,
                quantity=fill.quantity,
                price=fill.price
            )
    
    async def _handle_buy_fill(
        self,
        position_key: Tuple[str, str],
        position: Optional[Position],
        fill: OrderFill,
        strategy_name: str
    ) -> None:
        """
        Handle buy order fill.
        
        For long positions: Opens or adds to position (positive quantity)
        For short positions: Closes or reduces position (negative quantity becomes less negative)
        
        Args:
            position_key: Position key (strategy_name, symbol)
            position: Existing position or None
            fill: Order fill details
            strategy_name: Strategy name
        """
        if position is None:
            # New long position
            self._positions[position_key] = Position(
                symbol=fill.symbol,
                strategy_name=strategy_name,
                quantity=fill.quantity,
                entry_price=fill.price,
                current_price=fill.price,
                opened_at=fill.timestamp,
                side="Buy"
            )
            logger.info(
                "position_opened",
                strategy=strategy_name,
                symbol=fill.symbol,
                quantity=fill.quantity,
                entry_price=fill.price,
                position_type="long"
            )
        elif position.quantity < 0:
            # Closing/reducing short position
            realized_pnl = (position.entry_price - fill.price) * fill.quantity - fill.fee
            position.realized_pnl += realized_pnl
            
            new_quantity = position.quantity + fill.quantity
            position.quantity = new_quantity
            position.current_price = fill.price
            
            if new_quantity >= 0:
                # Short position fully closed
                position.status = "closed"
                position.closed_at = fill.timestamp
                
                await self._store_trade_log(position, fill.price, "manual_close")
                del self._positions[position_key]
                
                logger.info(
                    "short_position_closed",
                    strategy=strategy_name,
                    symbol=fill.symbol,
                    realized_pnl=position.realized_pnl,
                    exit_price=fill.price
                )
            else:
                logger.info(
                    "short_position_reduced",
                    strategy=strategy_name,
                    symbol=fill.symbol,
                    new_quantity=new_quantity,
                    realized_pnl=realized_pnl
                )
        else:
            # Add to existing long position - calculate new average entry price
            total_cost = (position.quantity * position.entry_price) + (fill.quantity * fill.price)
            new_quantity = position.quantity + fill.quantity
            new_entry_price = total_cost / new_quantity
            
            position.quantity = new_quantity
            position.entry_price = new_entry_price
            position.current_price = fill.price
            
            logger.info(
                "position_increased",
                strategy=strategy_name,
                symbol=fill.symbol,
                new_quantity=new_quantity,
                new_entry_price=new_entry_price
            )
    
    async def _handle_sell_fill(
        self,
        position_key: Tuple[str, str],
        position: Optional[Position],
        fill: OrderFill,
        strategy_name: str
    ) -> None:
        """
        Handle sell order fill.
        
        For long positions: Closes or reduces position (positive quantity becomes less positive)
        For short positions: Opens or adds to position (negative quantity)
        
        Args:
            position_key: Position key (strategy_name, symbol)
            position: Existing position or None
            fill: Order fill details
            strategy_name: Strategy name
        """
        if position is None:
            # New short position
            self._positions[position_key] = Position(
                symbol=fill.symbol,
                strategy_name=strategy_name,
                quantity=-fill.quantity,  # Negative for short
                entry_price=fill.price,
                current_price=fill.price,
                opened_at=fill.timestamp,
                side="Sell"
            )
            logger.info(
                "position_opened",
                strategy=strategy_name,
                symbol=fill.symbol,
                quantity=-fill.quantity,
                entry_price=fill.price,
                position_type="short"
            )
        elif position.quantity > 0:
            # Closing/reducing long position
            realized_pnl = (fill.price - position.entry_price) * fill.quantity - fill.fee
            position.realized_pnl += realized_pnl
            
            new_quantity = position.quantity - fill.quantity
            position.quantity = new_quantity
            position.current_price = fill.price
            
            if new_quantity <= 0:
                # Long position fully closed
                position.status = "closed"
                position.closed_at = fill.timestamp
                
                await self._store_trade_log(position, fill.price, "manual_close")
                del self._positions[position_key]
                
                logger.info(
                    "position_closed",
                    strategy=strategy_name,
                    symbol=fill.symbol,
                    realized_pnl=position.realized_pnl,
                    exit_price=fill.price
                )
            else:
                logger.info(
                    "position_decreased",
                    strategy=strategy_name,
                    symbol=fill.symbol,
                    new_quantity=new_quantity,
                    realized_pnl=realized_pnl
                )
        else:
            # Add to existing short position - calculate new average entry price
            total_cost = (abs(position.quantity) * position.entry_price) + (fill.quantity * fill.price)
            new_quantity = position.quantity - fill.quantity  # More negative
            new_entry_price = total_cost / abs(new_quantity)
            
            position.quantity = new_quantity
            position.entry_price = new_entry_price
            position.current_price = fill.price
            
            logger.info(
                "short_position_increased",
                strategy=strategy_name,
                symbol=fill.symbol,
                new_quantity=new_quantity,
                new_entry_price=new_entry_price
            )
    
    async def calculate_unrealized_pnl(
        self,
        symbol: str,
        strategy_name: str,
        current_price: float
    ) -> float:
        """
        Calculate unrealized P&L for an open position.
        
        Args:
            symbol: Trading symbol
            strategy_name: Strategy name
            current_price: Current market price
            
        Returns:
            Unrealized P&L
        """
        async with self._lock:
            position_key = (strategy_name, symbol)
            position = self._positions.get(position_key)
            
            if position is None or position.status != "open":
                return 0.0
            
            # Update current price
            position.current_price = current_price
            
            # Calculate unrealized P&L
            unrealized_pnl = (current_price - position.entry_price) * position.quantity
            position.unrealized_pnl = unrealized_pnl
            
            return unrealized_pnl
    
    async def close_position(
        self,
        symbol: str,
        strategy_name: str,
        exit_price: float,
        exit_reason: str = "manual_close"
    ) -> Optional[float]:
        """
        Close a position and calculate final realized P&L.
        
        Args:
            symbol: Trading symbol
            strategy_name: Strategy name
            exit_price: Exit price
            exit_reason: Reason for closing (e.g., 'take_profit', 'stop_loss')
            
        Returns:
            Realized P&L or None if position doesn't exist
        """
        async with self._lock:
            position_key = (strategy_name, symbol)
            position = self._positions.get(position_key)
            
            if position is None:
                logger.warning(
                    "close_position_not_found",
                    strategy=strategy_name,
                    symbol=symbol
                )
                return None
            
            # Calculate final realized P&L
            realized_pnl = (exit_price - position.entry_price) * position.quantity
            position.realized_pnl += realized_pnl
            position.status = "closed"
            position.closed_at = datetime.utcnow()
            position.current_price = exit_price
            
            # Store in trade log
            await self._store_trade_log(position, exit_price, exit_reason)
            
            # Persist final state
            await self._persist_position(position_key)
            
            # Remove from active positions
            del self._positions[position_key]
            
            logger.info(
                "position_closed",
                strategy=strategy_name,
                symbol=symbol,
                realized_pnl=position.realized_pnl,
                exit_price=exit_price,
                exit_reason=exit_reason
            )
            
            return position.realized_pnl
    
    async def get_position(
        self,
        symbol: str,
        strategy_name: str
    ) -> Optional[Position]:
        """
        Get current position for a symbol and strategy.
        
        Args:
            symbol: Trading symbol
            strategy_name: Strategy name
            
        Returns:
            Position or None if not found
        """
        async with self._lock:
            position_key = (strategy_name, symbol)
            return self._positions.get(position_key)
    
    async def get_all_positions(self) -> List[Position]:
        """
        Get all open positions.
        
        Returns:
            List of all open positions
        """
        async with self._lock:
            return list(self._positions.values())
    
    async def _persist_position(self, position_key: Tuple[str, str]) -> None:
        """
        Save position state to database.
        
        Args:
            position_key: Position key (strategy_name, symbol)
        """
        position = self._positions.get(position_key)
        if position is None:
            return
        
        try:
            conn = await self.database.get_connection()
            
            # Check if position exists in database
            cursor = await conn.execute(
                """
                SELECT id FROM positions 
                WHERE symbol = ? AND strategy_name = ? AND status = 'open'
                """,
                (position.symbol, position.strategy_name)
            )
            row = await cursor.fetchone()
            
            if row:
                # Update existing position
                await conn.execute(
                    """
                    UPDATE positions 
                    SET quantity = ?, entry_price = ?, current_price = ?,
                        unrealized_pnl = ?, realized_pnl = ?, status = ?
                    WHERE id = ?
                    """,
                    (
                        position.quantity,
                        position.entry_price,
                        position.current_price,
                        position.unrealized_pnl,
                        position.realized_pnl,
                        position.status,
                        row[0]
                    )
                )
            else:
                # Insert new position
                await conn.execute(
                    """
                    INSERT INTO positions 
                    (symbol, quantity, entry_price, current_price, unrealized_pnl,
                     realized_pnl, status, opened_at, strategy_name)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        position.symbol,
                        position.quantity,
                        position.entry_price,
                        position.current_price,
                        position.unrealized_pnl,
                        position.realized_pnl,
                        position.status,
                        position.opened_at,
                        position.strategy_name
                    )
                )
            
            await conn.commit()
            
        except Exception as e:
            logger.error(
                "position_persist_error",
                strategy=position.strategy_name,
                symbol=position.symbol,
                error=str(e),
                exc_info=True
            )
    
    async def load_state(self) -> None:
        """
        Load position state from database on startup.
        """
        try:
            conn = await self.database.get_connection()
            
            cursor = await conn.execute(
                """
                SELECT symbol, quantity, entry_price, current_price, unrealized_pnl,
                       realized_pnl, status, opened_at, closed_at, strategy_name
                FROM positions
                WHERE status = 'open'
                """
            )
            
            rows = await cursor.fetchall()
            
            for row in rows:
                position = Position(
                    symbol=row[0],
                    strategy_name=row[9],
                    quantity=row[1],
                    entry_price=row[2],
                    current_price=row[3],
                    unrealized_pnl=row[4],
                    realized_pnl=row[5],
                    status=row[6],
                    opened_at=datetime.fromisoformat(row[7]) if row[7] else datetime.utcnow(),
                    closed_at=datetime.fromisoformat(row[8]) if row[8] else None
                )
                
                position_key = (position.strategy_name, position.symbol)
                self._positions[position_key] = position
            
            logger.info(
                "positions_loaded",
                count=len(rows)
            )
            
        except Exception as e:
            logger.error(
                "position_load_error",
                error=str(e),
                exc_info=True
            )
    
    async def _store_trade_log(
        self,
        position: Position,
        exit_price: float,
        exit_reason: str
    ) -> None:
        """
        Store completed trade in trade_log table.
        
        Args:
            position: Position being closed
            exit_price: Exit price
            exit_reason: Reason for exit
        """
        try:
            conn = await self.database.get_connection()
            
            # Calculate P&L percentage
            pnl_percent = ((exit_price - position.entry_price) / position.entry_price) * 100
            
            await conn.execute(
                """
                INSERT INTO trade_log
                (strategy_name, symbol, side, quantity, entry_price, exit_price,
                 pnl, pnl_percent, opened_at, closed_at, exit_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    position.strategy_name,
                    position.symbol,
                    position.side,
                    position.quantity,
                    position.entry_price,
                    exit_price,
                    position.realized_pnl,
                    pnl_percent,
                    position.opened_at,
                    position.closed_at or datetime.utcnow(),
                    exit_reason
                )
            )
            
            await conn.commit()
            
            logger.info(
                "trade_logged",
                strategy=position.strategy_name,
                symbol=position.symbol,
                pnl=position.realized_pnl,
                pnl_percent=pnl_percent
            )
            
        except Exception as e:
            logger.error(
                "trade_log_error",
                strategy=position.strategy_name,
                symbol=position.symbol,
                error=str(e),
                exc_info=True
            )
    
    async def sync_with_exchange(
        self,
        exchange_positions: List[Dict[str, any]]
    ) -> None:
        """
        Synchronize local position state with exchange positions.
        
        Reconciles differences between local tracking and exchange state.
        
        Args:
            exchange_positions: List of positions from exchange API
        """
        async with self._lock:
            logger.info(
                "syncing_positions",
                exchange_count=len(exchange_positions),
                local_count=len(self._positions)
            )
            
            # Create a set of exchange position keys
            exchange_keys = set()
            
            for ex_pos in exchange_positions:
                symbol = ex_pos.get("symbol")
                quantity = float(ex_pos.get("size", 0))
                entry_price = float(ex_pos.get("avgPrice", 0))
                
                if quantity <= 0:
                    continue
                
                # For now, we'll use a default strategy name for exchange positions
                # In a real system, you'd need to track which strategy owns which position
                strategy_name = ex_pos.get("strategy_name", "unknown")
                position_key = (strategy_name, symbol)
                exchange_keys.add(position_key)
                
                # Check if we have this position locally
                local_pos = self._positions.get(position_key)
                
                if local_pos is None:
                    # Position exists on exchange but not locally - create it
                    self._positions[position_key] = Position(
                        symbol=symbol,
                        strategy_name=strategy_name,
                        quantity=quantity,
                        entry_price=entry_price,
                        current_price=entry_price,
                        status="open",
                        opened_at=datetime.utcnow()
                    )
                    logger.warning(
                        "position_sync_created",
                        strategy=strategy_name,
                        symbol=symbol,
                        quantity=quantity
                    )
                elif abs(local_pos.quantity - quantity) > 0.0001:
                    # Quantity mismatch - update to exchange value
                    logger.warning(
                        "position_sync_quantity_mismatch",
                        strategy=strategy_name,
                        symbol=symbol,
                        local_quantity=local_pos.quantity,
                        exchange_quantity=quantity
                    )
                    local_pos.quantity = quantity
                    local_pos.entry_price = entry_price
            
            # Check for positions that exist locally but not on exchange
            local_keys = set(self._positions.keys())
            missing_on_exchange = local_keys - exchange_keys
            
            for position_key in missing_on_exchange:
                position = self._positions[position_key]
                logger.warning(
                    "position_sync_missing_on_exchange",
                    strategy=position.strategy_name,
                    symbol=position.symbol,
                    quantity=position.quantity
                )
                # Optionally close these positions or mark them for review
            
            logger.info("position_sync_complete")
