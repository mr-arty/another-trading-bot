"""Demo script to test configuration loading."""

import asyncio
import os
from src.config import load_config


async def main():
    """Test configuration loading."""
    # Set minimal required environment variables
    os.environ["BYBIT_API_KEY"] = "demo_key_12345"
    os.environ["BYBIT_API_SECRET"] = "demo_secret_67890"
    
    try:
        config = await load_config()
        print("✓ Configuration loaded successfully!")
        print(f"\nConfiguration:")
        print(f"  API Key: {config.exchange_api_key[:10]}...")
        print(f"  Testnet: {config.exchange_testnet}")
        print(f"  Strategies Dir: {config.strategies_dir}")
        print(f"  Max Total Exposure: ${config.max_total_exposure}")
        print(f"  Log Level: {config.log_level}")
        print(f"  Volatility Threshold: {config.volatility_threshold}")
        print(f"  Database Path: {config.database_path}")
    except ValueError as e:
        print(f"✗ Configuration validation failed:")
        print(f"  {e}")


if __name__ == "__main__":
    asyncio.run(main())
