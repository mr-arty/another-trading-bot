"""Comprehensive logging system with structlog and log rotation."""

import os
import sys
import logging
import logging.handlers
from pathlib import Path
from typing import Any, Dict, Optional
import structlog
from structlog.types import FilteringBoundLogger


# Global logger instance
_logger: Optional[FilteringBoundLogger] = None


def setup_logging(
    log_dir: str = "logs",
    log_level: str = "INFO",
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB default
    backup_count: int = 5,
    json_format: bool = True
) -> FilteringBoundLogger:
    """
    Set up comprehensive logging with structlog and log rotation.
    
    Args:
        log_dir: Directory for log files
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup log files to keep
        json_format: Whether to use JSON formatting
    
    Returns:
        Configured structlog logger
    """
    global _logger
    
    # Create log directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Configure standard logging
    log_file = log_path / "trading_bot.log"
    
    # Clear existing handlers to avoid duplicates
    logging.root.handlers.clear()
    
    # Set up rotating file handler
    file_handler = logging.handlers.RotatingFileHandler(
        filename=str(log_file),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    
    # Set up console handler
    console_handler = logging.StreamHandler(sys.stdout)
    
    # Configure handlers
    handlers = [file_handler, console_handler]
    
    # Set log level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    logging.basicConfig(
        format="%(message)s",
        level=numeric_level,
        handlers=handlers,
        force=True  # Force reconfiguration
    )
    
    # Configure structlog processors
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    # Add JSON or console renderer based on configuration
    if json_format:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    # Configure structlog to use standard logging
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    _logger = structlog.get_logger()
    
    # Log system startup
    _logger.info(
        "logging_system_initialized",
        log_dir=str(log_path),
        log_level=log_level,
        max_bytes=max_bytes,
        backup_count=backup_count,
        json_format=json_format
    )
    
    return _logger


def get_logger() -> FilteringBoundLogger:
    """
    Get the configured logger instance.
    
    Returns:
        Configured structlog logger
    
    Raises:
        RuntimeError: If logging has not been set up
    """
    global _logger
    
    if _logger is None:
        # Auto-initialize with defaults if not already set up
        return setup_logging()
    
    return _logger


def log_order(
    order_id: str,
    symbol: str,
    side: str,
    quantity: float,
    price: Optional[float],
    strategy_id: str,
    order_type: str = "MARKET",
    **kwargs: Any
) -> None:
    """
    Log order placement with all relevant details.
    
    Args:
        order_id: Unique order identifier
        symbol: Trading pair symbol
        side: Order side (BUY/SELL)
        quantity: Order quantity
        price: Order price (None for market orders)
        strategy_id: Strategy that generated the order
        order_type: Type of order (MARKET, LIMIT, etc.)
        **kwargs: Additional order details
    """
    logger = get_logger()
    logger.info(
        "order_placed",
        order_id=order_id,
        symbol=symbol,
        side=side,
        quantity=quantity,
        price=price,
        strategy_id=strategy_id,
        order_type=order_type,
        **kwargs
    )


def log_fill(
    order_id: str,
    symbol: str,
    side: str,
    quantity: float,
    price: float,
    strategy_id: str,
    fill_type: str = "FULL",
    **kwargs: Any
) -> None:
    """
    Log order fill with all relevant details.
    
    Args:
        order_id: Unique order identifier
        symbol: Trading pair symbol
        side: Order side (BUY/SELL)
        quantity: Filled quantity
        price: Fill price
        strategy_id: Strategy that generated the order
        fill_type: Type of fill (FULL, PARTIAL)
        **kwargs: Additional fill details
    """
    logger = get_logger()
    logger.info(
        "order_filled",
        order_id=order_id,
        symbol=symbol,
        side=side,
        quantity=quantity,
        price=price,
        strategy_id=strategy_id,
        fill_type=fill_type,
        **kwargs
    )


def log_error(
    error_type: str,
    message: str,
    exc_info: Optional[Exception] = None,
    **kwargs: Any
) -> None:
    """
    Log error with stack trace and context.
    
    Args:
        error_type: Type/category of error
        message: Error message
        exc_info: Exception object for stack trace
        **kwargs: Additional context information
    """
    logger = get_logger()
    logger.error(
        error_type,
        message=message,
        exc_info=exc_info,
        **kwargs
    )


def log_system_event(
    event_type: str,
    message: str,
    level: str = "INFO",
    **kwargs: Any
) -> None:
    """
    Log system lifecycle events (start, stop, configuration changes).
    
    Args:
        event_type: Type of system event
        message: Event message
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        **kwargs: Additional event details
    """
    logger = get_logger()
    log_method = getattr(logger, level.lower(), logger.info)
    log_method(
        event_type,
        message=message,
        **kwargs
    )
