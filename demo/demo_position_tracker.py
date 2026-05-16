"""Demo script for Position Tracker functionality."""

import asyncio
from datetime import datetime
from src.position.tracker import PositionTracker, OrderFill
from src.database.db import Database


async def main():
    """Demonstrate position tracker functionality."""
    print("=== Position Tracker Demo ===\n")
    
    # Initialize database and tracker
    db = Database(":memory:")
    await db.initialize()
    tracker = PositionTracker(db)
    
    print("1. Opening a new position with a buy order")
    buy_fill = OrderFill(
        order_id="ORDER_001",
        symbol="BTCUSDT",
        side="Buy",
        quantity=1.5,
        price=50000.0,
        fee=15.0,
        timestamp=datetime.utcnow(),
        strategy_name="momentum_strategy"
    )
    await tracker.update_position("BTCUSDT", buy_fill)
    
    position = await tracker.get_position("BTCUSDT", "momentum_strategy")
    print(f"   Position opened: {position.quantity} BTC @ ${position.entry_price:,.2f}")
    print()
    
    print("2. Adding to the position (averaging entry price)")
    buy_fill2 = OrderFill(
        order_id="ORDER_002",
        symbol="BTCUSDT",
        side="Buy",
        quantity=0.5,
        price=52000.0,
        fee=5.0,
        timestamp=datetime.utcnow(),
        strategy_name="momentum_strategy"
    )
    await tracker.update_position("BTCUSDT", buy_fill2)
    
    position = await tracker.get_position("BTCUSDT", "momentum_strategy")
    print(f"   Position increased: {position.quantity} BTC @ ${position.entry_price:,.2f}")
    print(f"   (Average entry: (1.5*50000 + 0.5*52000) / 2.0 = ${position.entry_price:,.2f})")
    print()
    
    print("3. Calculating unrealized P&L at current market price")
    current_price = 53000.0
    unrealized_pnl = await tracker.calculate_unrealized_pnl(
        "BTCUSDT",
        "momentum_strategy",
        current_price
    )
    print(f"   Current price: ${current_price:,.2f}")
    print(f"   Unrealized P&L: ${unrealized_pnl:,.2f}")
    print()
    
    print("4. Partially closing the position")
    sell_fill = OrderFill(
        order_id="ORDER_003",
        symbol="BTCUSDT",
        side="Sell",
        quantity=1.0,
        price=53000.0,
        fee=10.0,
        timestamp=datetime.utcnow(),
        strategy_name="momentum_strategy"
    )
    await tracker.update_position("BTCUSDT", sell_fill)
    
    position = await tracker.get_position("BTCUSDT", "momentum_strategy")
    print(f"   Position reduced: {position.quantity} BTC remaining")
    print(f"   Realized P&L from partial close: ${position.realized_pnl:,.2f}")
    print()
    
    print("5. Closing the remaining position")
    realized_pnl = await tracker.close_position(
        "BTCUSDT",
        "momentum_strategy",
        54000.0,
        "take_profit"
    )
    print(f"   Position closed at ${54000.0:,.2f}")
    print(f"   Total realized P&L: ${realized_pnl:,.2f}")
    print()
    
    print("6. Checking trade log in database")
    conn = await db.get_connection()
    cursor = await conn.execute(
        """
        SELECT symbol, entry_price, exit_price, pnl, pnl_percent, exit_reason
        FROM trade_log
        """
    )
    rows = await cursor.fetchall()
    
    print("   Trade Log:")
    for row in rows:
        print(f"   - {row[0]}: Entry ${row[1]:,.2f} -> Exit ${row[2]:,.2f}")
        print(f"     P&L: ${row[3]:,.2f} ({row[4]:.2f}%)")
        print(f"     Exit Reason: {row[5]}")
    print()
    
    print("7. Demonstrating multiple strategies on same symbol")
    # Strategy 1
    fill_s1 = OrderFill(
        order_id="ORDER_004",
        symbol="ETHUSDT",
        side="Buy",
        quantity=10.0,
        price=3000.0,
        fee=5.0,
        timestamp=datetime.utcnow(),
        strategy_name="strategy_1"
    )
    await tracker.update_position("ETHUSDT", fill_s1)
    
    # Strategy 2
    fill_s2 = OrderFill(
        order_id="ORDER_005",
        symbol="ETHUSDT",
        side="Buy",
        quantity=5.0,
        price=3100.0,
        fee=3.0,
        timestamp=datetime.utcnow(),
        strategy_name="strategy_2"
    )
    await tracker.update_position("ETHUSDT", fill_s2)
    
    all_positions = await tracker.get_all_positions()
    print(f"   Total open positions: {len(all_positions)}")
    for pos in all_positions:
        print(f"   - {pos.strategy_name}: {pos.quantity} {pos.symbol} @ ${pos.entry_price:,.2f}")
    print()
    
    print("8. Testing position persistence and reload")
    # Create new tracker instance
    tracker2 = PositionTracker(db)
    await tracker2.load_state()
    
    loaded_positions = await tracker2.get_all_positions()
    print(f"   Loaded {len(loaded_positions)} positions from database")
    for pos in loaded_positions:
        print(f"   - {pos.strategy_name}: {pos.quantity} {pos.symbol}")
    
    await db.close()
    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
