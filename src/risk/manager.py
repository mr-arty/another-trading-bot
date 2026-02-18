"""Risk management for validating trading signals."""

import asyncio
from dataclasses import dataclass
from typing import Optional, Callable, Awaitable, Dict
import structlog

from src.strategy.engine import Signal
from src.config.config import Config


logger = structlog.get_logger(__name__)


@dataclass
class RiskCheckResult:
    """Result of a risk check."""
    approved: bool
    reason: str


class RiskManager:
    """
    Risk manager that validates signals against risk limits.
    
    Handles:
    - Position size validation for buy signals
    - Position existence and quantity validation for sell signals
    - Total exposure limit enforcement
    - Signal rejection with logging
    - Validated signal forwarding
    """
    
    def __init__(
        self,
        config: Config,
        signal_callback: Optional[Callable[[Signal], Awaitable[None]]] = None
    ):
        """
        Initialize risk manager.
        
        Args:
            config: System configuration
            signal_callback: Optional callback to receive validated signals
        """
        self.config = config
        self.signal_callback = signal_callback
        
        # Track positions: {(strategy_name, symbol): quantity}
        self._positions: Dict[tuple, float] = {}
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        
        logger.info(
            "risk_manager_initialized",
            max_total_exposure=config.max_total_exposure,
            max_position_size=config.max_position_size
        )
    
    async def validate_signal(self, signal: Signal) -> RiskCheckResult:
        """
        Validate signal against risk rules.
        
        This is the main entry point for risk validation. It performs all
        necessary checks and either approves or rejects the signal.
        
        Args:
            signal: Signal to validate
            
        Returns:
            RiskCheckResult with approval status and reason
        """
        async with self._lock:
            if signal.side == 'buy':
                return await self._validate_buy_signal(signal)
            elif signal.side == 'sell':
                return await self._validate_sell_signal(signal)
            else:
                return RiskCheckResult(
                    approved=False,
                    reason=f"Invalid signal side: {signal.side}"
                )
    
    async def _validate_buy_signal(self, signal: Signal) -> RiskCheckResult:
        """
        Validate a buy signal.
        
        Checks:
        1. Position size does not exceed max_position_size
        2. Total exposure does not exceed max_total_exposure
        
        Args:
            signal: Buy signal to validate
            
        Returns:
            RiskCheckResult with approval status and reason
        """
        # Check position size limit
        if signal.quantity > self.config.max_position_size:
            reason = (
                f"Position size {signal.quantity} exceeds max "
                f"{self.config.max_position_size}"
            )
            logger.warning(
                "signal_rejected_position_size",
                strategy=signal.strategy_name,
                symbol=signal.symbol,
                quantity=signal.quantity,
                max_position_size=self.config.max_position_size
            )
            return RiskCheckResult(approved=False, reason=reason)
        
        # Check total exposure limit
        current_exposure = await self._calculate_total_exposure()
        new_exposure = current_exposure + signal.quantity
        
        if new_exposure > self.config.max_total_exposure:
            reason = (
                f"Total exposure {new_exposure:.2f} would exceed max "
                f"{self.config.max_total_exposure}"
            )
            logger.warning(
                "signal_rejected_total_exposure",
                strategy=signal.strategy_name,
                symbol=signal.symbol,
                current_exposure=current_exposure,
                new_exposure=new_exposure,
                max_total_exposure=self.config.max_total_exposure
            )
            return RiskCheckResult(approved=False, reason=reason)
        
        # All checks passed
        logger.info(
            "buy_signal_approved",
            strategy=signal.strategy_name,
            symbol=signal.symbol,
            quantity=signal.quantity,
            new_exposure=new_exposure
        )
        return RiskCheckResult(
            approved=True,
            reason="Buy signal approved"
        )
    
    async def _validate_sell_signal(self, signal: Signal) -> RiskCheckResult:
        """
        Validate a sell signal.
        
        Checks:
        1. Position exists for this strategy and symbol
        2. Sell quantity does not exceed current holding
        
        Args:
            signal: Sell signal to validate
            
        Returns:
            RiskCheckResult with approval status and reason
        """
        position_key = (signal.strategy_name, signal.symbol)
        current_position = self._positions.get(position_key, 0.0)
        
        # Check if position exists
        if current_position <= 0:
            reason = (
                f"No position exists for {signal.symbol} "
                f"in strategy {signal.strategy_name}"
            )
            logger.warning(
                "signal_rejected_no_position",
                strategy=signal.strategy_name,
                symbol=signal.symbol
            )
            return RiskCheckResult(approved=False, reason=reason)
        
        # Check if sell quantity exceeds current holding
        if signal.quantity > current_position:
            reason = (
                f"Sell quantity {signal.quantity} exceeds current holding "
                f"{current_position}"
            )
            logger.warning(
                "signal_rejected_quantity_exceeds_holding",
                strategy=signal.strategy_name,
                symbol=signal.symbol,
                sell_quantity=signal.quantity,
                current_position=current_position
            )
            return RiskCheckResult(approved=False, reason=reason)
        
        # All checks passed
        logger.info(
            "sell_signal_approved",
            strategy=signal.strategy_name,
            symbol=signal.symbol,
            quantity=signal.quantity,
            current_position=current_position
        )
        return RiskCheckResult(
            approved=True,
            reason="Sell signal approved"
        )
    
    async def _calculate_total_exposure(self) -> float:
        """
        Calculate total exposure across all strategies.
        
        Returns:
            Total exposure (sum of all position quantities)
        """
        return sum(self._positions.values())
    
    async def check_position_limit(self, symbol: str, quantity: float) -> bool:
        """
        Check if position size is within limits.
        
        Args:
            symbol: Trading symbol
            quantity: Position quantity
            
        Returns:
            True if within limits, False otherwise
        """
        return quantity <= self.config.max_position_size
    
    async def check_total_exposure(self) -> bool:
        """
        Check if total exposure is within limits.
        
        Returns:
            True if within limits, False otherwise
        """
        current_exposure = await self._calculate_total_exposure()
        return current_exposure <= self.config.max_total_exposure
    
    async def process_signal(self, signal: Signal) -> None:
        """
        Process a signal: validate and forward if approved.
        
        This method combines validation, rejection logging, and forwarding.
        It's the main entry point for signal processing.
        
        Args:
            signal: Signal to process
        """
        # Validate signal
        result = await self.validate_signal(signal)
        
        if not result.approved:
            # Signal rejected - log rejection
            logger.warning(
                "signal_rejected",
                strategy=signal.strategy_name,
                symbol=signal.symbol,
                side=signal.side,
                quantity=signal.quantity,
                reason=result.reason
            )
            return
        
        # Signal approved - forward to order executor
        logger.info(
            "signal_forwarded",
            strategy=signal.strategy_name,
            symbol=signal.symbol,
            side=signal.side,
            quantity=signal.quantity
        )
        
        if self.signal_callback:
            try:
                await self.signal_callback(signal)
            except Exception as e:
                logger.error(
                    "signal_forwarding_error",
                    strategy=signal.strategy_name,
                    symbol=signal.symbol,
                    error=str(e),
                    exc_info=True
                )
    
    async def update_position(
        self,
        strategy_name: str,
        symbol: str,
        quantity: float
    ) -> None:
        """
        Update position tracking after order fills.
        
        Args:
            strategy_name: Name of strategy
            symbol: Trading symbol
            quantity: New position quantity (0 if closed)
        """
        async with self._lock:
            position_key = (strategy_name, symbol)
            
            if quantity <= 0:
                # Position closed
                if position_key in self._positions:
                    del self._positions[position_key]
                    logger.debug(
                        "position_closed",
                        strategy=strategy_name,
                        symbol=symbol
                    )
            else:
                # Position opened or updated
                self._positions[position_key] = quantity
                logger.debug(
                    "position_updated",
                    strategy=strategy_name,
                    symbol=symbol,
                    quantity=quantity
                )
    
    async def get_position(
        self,
        strategy_name: str,
        symbol: str
    ) -> float:
        """
        Get current position quantity for a strategy and symbol.
        
        Args:
            strategy_name: Name of strategy
            symbol: Trading symbol
            
        Returns:
            Position quantity (0 if no position)
        """
        async with self._lock:
            position_key = (strategy_name, symbol)
            return self._positions.get(position_key, 0.0)
    
    async def get_total_exposure(self) -> float:
        """
        Get total exposure across all strategies.
        
        Returns:
            Total exposure
        """
        async with self._lock:
            return await self._calculate_total_exposure()
    
    async def get_all_positions(self) -> Dict[tuple, float]:
        """
        Get all current positions.
        
        Returns:
            Dict mapping (strategy_name, symbol) to quantity
        """
        async with self._lock:
            return self._positions.copy()
