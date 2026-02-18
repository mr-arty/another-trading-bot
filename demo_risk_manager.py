"""Demo script for Risk Manager functionality."""

import asyncio
from datetime import datetime
from src.risk.manager import RiskManager
from src.strategy.engine import Signal
from src.config.config import Config


async def demo_risk_manager():
    """Demonstrate Risk Manager functionality."""
    print("=" * 60)
    print("Risk Manager Demo")
    print("=" * 60)
    
    # Create configuration
    config = Config(
        exchange_api_key="demo_key",
        exchange_api_secret="demo_secret",
        exchange_testnet=True,
        strategies_dir="./strategies",
        max_total_exposure=1000.0,
        max_position_size=100.0,
        log_level="INFO",
        log_file="./logs/demo.log"
    )
    
    print(f"\nConfiguration:")
    print(f"  Max Position Size: {config.max_position_size}")
    print(f"  Max Total Exposure: {config.max_total_exposure}")
    
    # Create risk manager
    risk_manager = RiskManager(config=config)
    
    # Demo 1: Approve buy signal within limits
    print("\n" + "-" * 60)
    print("Demo 1: Buy signal within limits")
    print("-" * 60)
    
    signal1 = Signal(
        strategy_name="momentum_strategy",
        symbol="BTCUSDT",
        side="buy",
        quantity=50.0,
        price=None,
        timestamp=datetime.now(),
        reason="RSI > 50 and EMA cross"
    )
    
    result1 = await risk_manager.validate_signal(signal1)
    print(f"Signal: {signal1.side.upper()} {signal1.quantity} {signal1.symbol}")
    print(f"Result: {'✓ APPROVED' if result1.approved else '✗ REJECTED'}")
    print(f"Reason: {result1.reason}")
    
    # Simulate position opened
    await risk_manager.update_position("momentum_strategy", "BTCUSDT", 50.0)
    
    # Demo 2: Reject buy signal exceeding position size
    print("\n" + "-" * 60)
    print("Demo 2: Buy signal exceeding position size limit")
    print("-" * 60)
    
    signal2 = Signal(
        strategy_name="mean_reversion",
        symbol="ETHUSDT",
        side="buy",
        quantity=150.0,  # Exceeds max_position_size
        price=None,
        timestamp=datetime.now(),
        reason="Price at support level"
    )
    
    result2 = await risk_manager.validate_signal(signal2)
    print(f"Signal: {signal2.side.upper()} {signal2.quantity} {signal2.symbol}")
    print(f"Result: {'✓ APPROVED' if result2.approved else '✗ REJECTED'}")
    print(f"Reason: {result2.reason}")
    
    # Demo 3: Reject buy signal exceeding total exposure
    print("\n" + "-" * 60)
    print("Demo 3: Buy signal exceeding total exposure limit")
    print("-" * 60)
    
    # Add more positions
    await risk_manager.update_position("strategy2", "ETHUSDT", 400.0)
    await risk_manager.update_position("strategy3", "SOLUSDT", 500.0)
    
    total_exposure = await risk_manager.get_total_exposure()
    print(f"Current total exposure: {total_exposure}")
    
    signal3 = Signal(
        strategy_name="strategy4",
        symbol="ADAUSDT",
        side="buy",
        quantity=100.0,  # Would exceed total exposure
        price=None,
        timestamp=datetime.now(),
        reason="Breakout signal"
    )
    
    result3 = await risk_manager.validate_signal(signal3)
    print(f"Signal: {signal3.side.upper()} {signal3.quantity} {signal3.symbol}")
    print(f"Result: {'✓ APPROVED' if result3.approved else '✗ REJECTED'}")
    print(f"Reason: {result3.reason}")
    
    # Demo 4: Reject sell signal with no position
    print("\n" + "-" * 60)
    print("Demo 4: Sell signal with no position")
    print("-" * 60)
    
    signal4 = Signal(
        strategy_name="new_strategy",
        symbol="DOGEUSDT",
        side="sell",
        quantity=50.0,
        price=None,
        timestamp=datetime.now(),
        reason="Exit signal"
    )
    
    result4 = await risk_manager.validate_signal(signal4)
    print(f"Signal: {signal4.side.upper()} {signal4.quantity} {signal4.symbol}")
    print(f"Result: {'✓ APPROVED' if result4.approved else '✗ REJECTED'}")
    print(f"Reason: {result4.reason}")
    
    # Demo 5: Reject sell signal exceeding holding
    print("\n" + "-" * 60)
    print("Demo 5: Sell signal exceeding current holding")
    print("-" * 60)
    
    current_position = await risk_manager.get_position("momentum_strategy", "BTCUSDT")
    print(f"Current position: {current_position} BTCUSDT")
    
    signal5 = Signal(
        strategy_name="momentum_strategy",
        symbol="BTCUSDT",
        side="sell",
        quantity=100.0,  # More than we have
        price=None,
        timestamp=datetime.now(),
        reason="Stop loss triggered"
    )
    
    result5 = await risk_manager.validate_signal(signal5)
    print(f"Signal: {signal5.side.upper()} {signal5.quantity} {signal5.symbol}")
    print(f"Result: {'✓ APPROVED' if result5.approved else '✗ REJECTED'}")
    print(f"Reason: {result5.reason}")
    
    # Demo 6: Approve sell signal within holding
    print("\n" + "-" * 60)
    print("Demo 6: Sell signal within current holding")
    print("-" * 60)
    
    signal6 = Signal(
        strategy_name="momentum_strategy",
        symbol="BTCUSDT",
        side="sell",
        quantity=50.0,  # Exactly what we have
        price=None,
        timestamp=datetime.now(),
        reason="Take profit target reached"
    )
    
    result6 = await risk_manager.validate_signal(signal6)
    print(f"Signal: {signal6.side.upper()} {signal6.quantity} {signal6.symbol}")
    print(f"Result: {'✓ APPROVED' if result6.approved else '✗ REJECTED'}")
    print(f"Reason: {result6.reason}")
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    all_positions = await risk_manager.get_all_positions()
    print(f"\nCurrent Positions:")
    for (strategy, symbol), quantity in all_positions.items():
        print(f"  {strategy} - {symbol}: {quantity}")
    
    total_exposure = await risk_manager.get_total_exposure()
    print(f"\nTotal Exposure: {total_exposure} / {config.max_total_exposure}")
    print(f"Remaining Capacity: {config.max_total_exposure - total_exposure}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(demo_risk_manager())
