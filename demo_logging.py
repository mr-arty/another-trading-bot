#!/usr/bin/env python3
"""
Demo script for comprehensive logging system.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.logging import (
    setup_logging,
    get_logger,
    log_order,
    log_fill,
    log_error,
    log_system_event,
    LogRotationMonitor
)


def demo_logging():
    """Demonstrate the comprehensive logging system."""
    print("=== Trading Bot Logging System Demo ===\n")
    
    # 1. Set up logging
    print("1. Setting up logging system...")
    logger = setup_logging(
        log_dir="logs",
        log_level="INFO",
        max_bytes=1024 * 1024,  # 1 MB for demo
        backup_count=3,
        json_format=False  # Use console format for demo
    )
    print("   ✓ Logging system initialized\n")
    
    # 2. Log system events
    print("2. Logging system events...")
    log_system_event(
        "system_start",
        "Trading Bot System starting",
        version="1.0.0",
        environment="demo"
    )
    log_system_event(
        "config_loaded",
        "Configuration loaded successfully",
        config_file="config.yaml"
    )
    print("   ✓ System events logged\n")
    
    # 3. Log order placements
    print("3. Logging order placements...")
    log_order(
        order_id="ORD-001",
        symbol="BTCUSDT",
        side="BUY",
        quantity=0.1,
        price=50000.0,
        strategy_id="momentum-strategy-1",
        order_type="LIMIT"
    )
    log_order(
        order_id="ORD-002",
        symbol="ETHUSDT",
        side="SELL",
        quantity=1.5,
        price=None,
        strategy_id="mean-reversion-strategy-1",
        order_type="MARKET"
    )
    print("   ✓ Orders logged\n")
    
    # 4. Log order fills
    print("4. Logging order fills...")
    log_fill(
        order_id="ORD-001",
        symbol="BTCUSDT",
        side="BUY",
        quantity=0.1,
        price=49950.0,
        strategy_id="momentum-strategy-1",
        fill_type="FULL"
    )
    log_fill(
        order_id="ORD-002",
        symbol="ETHUSDT",
        side="SELL",
        quantity=0.75,
        price=3200.0,
        strategy_id="mean-reversion-strategy-1",
        fill_type="PARTIAL"
    )
    print("   ✓ Fills logged\n")
    
    # 5. Log errors
    print("5. Logging errors...")
    log_error(
        "api_error",
        "Failed to connect to exchange API",
        exchange="Bybit",
        retry_count=3
    )
    
    try:
        # Simulate an error
        raise ValueError("Invalid strategy configuration")
    except Exception as e:
        log_error(
            "strategy_error",
            "Strategy configuration validation failed",
            exc_info=e,
            strategy_id="invalid-strategy"
        )
    print("   ✓ Errors logged with stack traces\n")
    
    # 6. Demonstrate log rotation monitoring
    print("6. Checking log rotation status...")
    monitor = LogRotationMonitor(
        log_file="logs/trading_bot.log",
        max_bytes=1024 * 1024,
        backup_count=3
    )
    
    rotation_info = monitor.get_rotation_info()
    print(f"   Log file: {rotation_info['log_file']}")
    print(f"   Current size: {rotation_info['current_size']:,} bytes")
    print(f"   Max size: {rotation_info['max_bytes']:,} bytes")
    print(f"   Usage: {rotation_info['usage_percent']:.2f}%")
    print(f"   Should rotate: {rotation_info['should_rotate']}")
    print(f"   Backup count: {rotation_info['backup_count']}\n")
    
    # 7. Log shutdown
    print("7. Logging system shutdown...")
    log_system_event(
        "system_stop",
        "Trading Bot System shutting down",
        reason="demo_complete"
    )
    print("   ✓ Shutdown logged\n")
    
    print("=== Demo Complete ===")
    print(f"\nCheck the logs directory for output:")
    print(f"  - logs/trading_bot.log (main log file)")
    print(f"  - logs/trading_bot.log.1, .2, .3 (rotated backups)")


if __name__ == "__main__":
    demo_logging()
