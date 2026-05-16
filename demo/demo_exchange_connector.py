"""Demo script for Exchange Connector usage."""

import asyncio
from src.exchange import ExchangeConnector, OrderSide, OrderType, MarketData


async def market_data_handler(data: MarketData):
    """Handle incoming market data."""
    print(f"Received market data for {data.symbol}:")
    print(f"  Time: {data.timestamp}")
    print(f"  OHLC: {data.open}/{data.high}/{data.low}/{data.close}")
    print(f"  Volume: {data.volume}")


async def error_handler(operation: str, error: Exception):
    """Handle API errors."""
    print(f"Error in {operation}: {error}")


async def main():
    """Demonstrate Exchange Connector functionality."""
    
    # Note: This demo requires valid API credentials
    # Set BYBIT_API_KEY and BYBIT_API_SECRET environment variables
    
    print("Exchange Connector Demo")
    print("=" * 50)
    
    # Initialize connector
    connector = ExchangeConnector(
        api_key="demo_key",  # Replace with actual key
        api_secret="demo_secret",  # Replace with actual secret
        testnet=True,
        rate_limit_per_second=10,
        max_reconnect_delay=60
    )
    
    # Register error callback
    connector.register_error_callback(error_handler)
    
    print("\n1. Connector initialized")
    print(f"   - Testnet: {connector.testnet}")
    print(f"   - Rate limit: 10 req/s")
    print(f"   - Max reconnect delay: 60s")
    
    # Note: Actual connection requires valid credentials
    # Uncomment the following to test with real credentials:
    
    # try:
    #     # Connect to exchange
    #     await connector.connect()
    #     print("\n2. Connected to Bybit")
    #     
    #     # Subscribe to market data
    #     await connector.subscribe_market_data(
    #         symbols=["BTCUSDT"],
    #         callback=market_data_handler
    #     )
    #     print("\n3. Subscribed to BTCUSDT market data")
    #     
    #     # Get current positions
    #     positions = await connector.get_positions()
    #     print(f"\n4. Current positions: {len(positions)}")
    #     for pos in positions:
    #         print(f"   - {pos.symbol}: {pos.quantity} @ {pos.entry_price}")
    #     
    #     # Place a test order (be careful with real money!)
    #     # result = await connector.place_order(
    #     #     symbol="BTCUSDT",
    #     #     side=OrderSide.BUY,
    #     #     order_type=OrderType.LIMIT,
    #     #     quantity=0.001,
    #     #     price=30000.0,
    #     #     strategy_name="demo"
    #     # )
    #     # print(f"\n5. Order result: {result.message}")
    #     
    #     # Keep running to receive market data
    #     print("\n6. Listening for market data (Ctrl+C to stop)...")
    #     await asyncio.sleep(30)
    #     
    # except Exception as e:
    #     print(f"\nError: {e}")
    # finally:
    #     await connector.disconnect()
    #     print("\n7. Disconnected from exchange")
    
    print("\n" + "=" * 50)
    print("Demo complete!")
    print("\nFeatures implemented:")
    print("  ✓ Authenticated connection with API credentials")
    print("  ✓ WebSocket connection for market data streams")
    print("  ✓ REST API methods for order placement and position queries")
    print("  ✓ Reconnection logic with exponential backoff")
    print("  ✓ Market data subscription and parsing")
    print("  ✓ API rate limiting using token bucket algorithm")
    print("  ✓ API error handling with callbacks")


if __name__ == "__main__":
    asyncio.run(main())
