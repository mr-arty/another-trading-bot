"""Demo script for Strategy Engine functionality."""

import asyncio
from datetime import datetime

from src.strategy.engine import StrategyEngine, Signal
from src.strategy.config import (
    StrategyConfig,
    IndicatorConfig,
    EntryCondition,
    ExitCondition
)
from src.exchange.connector import MarketData
from src.indicators.calculator import IndicatorCalculator


async def signal_handler(signal: Signal):
    """Handle generated signals."""
    print(f"\n🚨 SIGNAL GENERATED:")
    print(f"   Strategy: {signal.strategy_name}")
    print(f"   Symbol: {signal.symbol}")
    print(f"   Side: {signal.side.upper()}")
    print(f"   Quantity: {signal.quantity}")
    print(f"   Reason: {signal.reason}")
    print(f"   Timestamp: {signal.timestamp}")


async def main():
    """Demonstrate Strategy Engine functionality."""
    print("=" * 70)
    print("Strategy Engine Demo")
    print("=" * 70)
    
    # Create indicator calculator
    indicator_calc = IndicatorCalculator(cache_ttl_seconds=60)
    
    # Create strategy engine with signal callback
    engine = StrategyEngine(indicator_calc, signal_callback=signal_handler)
    
    # Create a sample strategy configuration
    strategy_config = StrategyConfig(
        name="momentum_strategy",
        symbol="BTCUSDT",
        timeframes=["15m"],
        indicators={
            "rsi": IndicatorConfig(
                type="rsi",
                timeframe="15m",
                period=14
            ),
            "ema_fast": IndicatorConfig(
                type="ema",
                timeframe="15m",
                period=9
            ),
            "ema_slow": IndicatorConfig(
                type="ema",
                timeframe="15m",
                period=21
            )
        },
        entry_conditions=[
            EntryCondition(
                type="greater_than",
                indicator="rsi",
                value=50,
                description="RSI above 50"
            ),
            EntryCondition(
                type="cross_above",
                indicator1="ema_fast",
                indicator2="ema_slow",
                description="Fast EMA crosses above slow EMA"
            )
        ],
        exit_conditions=[
            ExitCondition(
                type="take_profit",
                percent=4.0,
                description="Take profit at 4%"
            ),
            ExitCondition(
                type="stop_loss",
                percent=1.0,
                description="Stop loss at 1%"
            ),
            ExitCondition(
                type="time_exceeds",
                seconds=3600,
                description="Exit after 1 hour"
            )
        ],
        position_size=0.01,
        max_position_size=0.05
    )
    
    print("\n📋 Registering Strategy:")
    print(f"   Name: {strategy_config.name}")
    print(f"   Symbol: {strategy_config.symbol}")
    print(f"   Indicators: {', '.join(strategy_config.indicators.keys())}")
    print(f"   Entry Conditions: {len(strategy_config.entry_conditions)}")
    print(f"   Exit Conditions: {len(strategy_config.exit_conditions)}")
    
    # Register strategy
    await engine.register_strategy(strategy_config)
    
    print("\n✅ Strategy registered successfully!")
    
    # Simulate market data to build up indicator history
    print("\n📊 Simulating market data...")
    
    base_price = 50000.0
    for i in range(30):  # Need enough data for indicators
        price = base_price + (i * 10)
        market_data = MarketData(
            symbol="BTCUSDT",
            timestamp=datetime.now(),
            open=price - 5,
            high=price + 10,
            low=price - 10,
            close=price,
            volume=100.0 + i
        )
        
        await engine.process_market_data(market_data)
        
        if i % 10 == 0:
            print(f"   Processed {i+1} data points...")
    
    print(f"   ✓ Processed 30 market data points")
    
    # Get strategy statistics
    stats = await engine.get_statistics()
    print("\n📈 Strategy Engine Statistics:")
    print(f"   Total Strategies: {stats['total_strategies']}")
    print(f"   Active Strategies: {stats['active_strategies']}")
    print(f"   Strategies with Positions: {stats['strategies_with_positions']}")
    
    # Get strategy state
    state = engine.get_strategy_state("momentum_strategy")
    print(f"\n🔍 Strategy State:")
    print(f"   Active: {state.is_active}")
    print(f"   Has Position: {state.has_position}")
    print(f"   Error Count: {state.error_count}")
    print(f"   Last Signal: {state.last_signal_time or 'None'}")
    
    # Demonstrate concurrent execution with multiple strategies
    print("\n🔄 Testing Concurrent Strategy Execution...")
    
    # Add another strategy for ETH
    eth_strategy = StrategyConfig(
        name="eth_momentum",
        symbol="ETHUSDT",
        timeframes=["15m"],
        indicators={
            "rsi": IndicatorConfig(type="rsi", timeframe="15m", period=14)
        },
        entry_conditions=[
            EntryCondition(type="greater_than", indicator="rsi", value=50)
        ],
        exit_conditions=[
            ExitCondition(type="take_profit", percent=3.0)
        ],
        position_size=0.1,
        max_position_size=0.5
    )
    
    await engine.register_strategy(eth_strategy)
    print("   ✓ Registered second strategy for ETHUSDT")
    
    # Process data for both symbols
    btc_data = MarketData(
        symbol="BTCUSDT",
        timestamp=datetime.now(),
        open=50500.0,
        high=50600.0,
        low=50400.0,
        close=50550.0,
        volume=150.0
    )
    
    eth_data = MarketData(
        symbol="ETHUSDT",
        timestamp=datetime.now(),
        open=3000.0,
        high=3010.0,
        low=2990.0,
        close=3005.0,
        volume=200.0
    )
    
    # Process concurrently
    await asyncio.gather(
        engine.process_market_data(btc_data),
        engine.process_market_data(eth_data)
    )
    
    print("   ✓ Processed market data for both symbols concurrently")
    
    # Final statistics
    final_stats = await engine.get_statistics()
    print(f"\n📊 Final Statistics:")
    print(f"   Total Strategies: {final_stats['total_strategies']}")
    print(f"   Active Strategies: {final_stats['active_strategies']}")
    
    print("\n" + "=" * 70)
    print("Demo Complete!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
