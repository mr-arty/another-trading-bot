# Range Trading Strategy Guide

## Overview

The range trading strategy is designed to profit from price oscillations within a defined range. It buys at support when oversold and sells at resistance when overbought, taking profit at the mid-range.

## Strategy Logic

### Entry Conditions

**Long Entry (Buy)**:
- RSI (4h) < 30 (oversold)
- Price near support level
- Opens a long position expecting price to bounce up

**Short Entry (Sell)**:
- RSI (4h) > 70 (overbought)  
- Price near resistance level
- Opens a short position expecting price to drop

### Exit Conditions

**Take Profit**:
- Exit when price reaches mid-range (exactly halfway between support and resistance)
- For long: Sell when price rises to mid-range
- For short: Buy back when price falls to mid-range

**Stop Loss**:
- 2% stop loss to protect against range breakouts
- 24-hour time limit to avoid holding through structural changes

## Setup Instructions

### 1. Identify the Range

Use your charting tools to identify:
- **Support level**: Recent swing low where price bounced multiple times
- **Resistance level**: Recent swing high where price rejected multiple times

Example:
```
Resistance: 72,000
Mid-range:  70,000  ← (72,000 + 68,000) / 2
Support:    68,000
```

### 2. Update the Strategy File

Edit `strategies/range_trading_strategy.yaml`:

```yaml
# Update these values based on your analysis
support_level: 68000.0      # Your support level
resistance_level: 72000.0   # Your resistance level

# Update exit conditions with mid-range
exit_conditions:
  - type: "support_resistance"
    price: 70000.0  # (support + resistance) / 2
```

### 3. Validate the Range

Good ranges have these characteristics:
- **Clear boundaries**: Multiple touches at support/resistance
- **Sufficient width**: At least 3-5% range width
- **Recent formation**: Established within last few weeks
- **Volume confirmation**: Higher volume at range extremes

### 4. Monitor Entry Signals

The bot will automatically:
- Monitor RSI on 4-hour timeframe
- Generate long signals when RSI < 30
- Generate short signals when RSI > 70

**Important**: You should manually verify that price is actually near the support/resistance levels when signals are generated.

## Risk Management

### Position Sizing
- **Position size**: 0.01 BTC per trade
- **Max position**: 0.03 BTC total
- **Risk per trade**: 2% maximum

### Trade Limits
- **Max trades per day**: 4
- **Cooldown after loss**: 1 hour
- **Min time between trades**: 2 hours

### Stop Loss Protection
- **Stop loss**: 2% from entry
- **Time limit**: 24 hours maximum hold time

## When to Use This Strategy

### Good Conditions ✅
- Sideways/consolidating market
- Clear support and resistance levels
- Low volatility environment
- Multiple bounces at range boundaries

### Bad Conditions ❌
- Strong trending market (up or down)
- Range breakout in progress
- High volatility / news events
- Unclear support/resistance levels

## Monitoring and Maintenance

### Daily Tasks
1. Check if range is still valid
2. Monitor for breakout signals
3. Update support/resistance if range shifts
4. Review open positions

### Weekly Tasks
1. Analyze range performance
2. Adjust levels if market structure changes
3. Review win rate and profit factor
4. Consider pausing if range breaks

## Example Trade Scenarios

### Successful Long Trade
```
1. Price drops to 68,200 (near support)
2. RSI drops to 28 (oversold)
3. Bot enters long at 68,200
4. Price bounces and rises
5. Bot exits at 70,000 (mid-range)
6. Profit: ~2.6% (1,800 / 68,200)
```

### Successful Short Trade
```
1. Price rises to 71,800 (near resistance)
2. RSI rises to 72 (overbought)
3. Bot enters short at 71,800
4. Price rejects and falls
5. Bot exits at 70,000 (mid-range)
6. Profit: ~2.5% (1,800 / 71,800)
```

### Stop Loss Scenario
```
1. Price at 68,200, RSI at 28
2. Bot enters long
3. Support breaks, price drops to 66,800
4. Stop loss triggers at 2% loss
5. Exit at 66,836
6. Loss: 2% (1,364 / 68,200)
```

## Current Limitations

The current bot implementation has some limitations for range trading:

1. **Manual level monitoring**: You need to manually verify price is near support/resistance when RSI signals trigger
2. **Static levels**: Support/resistance levels must be manually updated in the YAML file
3. **No dynamic range detection**: The bot doesn't automatically detect or adjust ranges

### Workarounds

1. **Use price alerts**: Set alerts on your exchange at support/resistance levels
2. **Regular updates**: Update the YAML file weekly or when range shifts
3. **Manual confirmation**: Check price action before allowing trades to execute
4. **Test mode first**: Run in test mode to see signal frequency before live trading

## Testing the Strategy

### Test Mode
Run the strategy in test mode first:

```yaml
strategy_type: "test"  # Add this line temporarily
```

This will:
- Connect to exchange and receive data
- Calculate RSI indicator
- Log when conditions are met
- NOT place any actual trades

### Paper Trading
1. Run in test mode for 1-2 weeks
2. Manually track hypothetical trades
3. Calculate win rate and profit factor
4. Adjust levels and parameters as needed

### Live Trading
Only go live after:
- ✅ Successful test mode operation
- ✅ Positive paper trading results
- ✅ Clear understanding of range dynamics
- ✅ Proper risk management in place

## Troubleshooting

### No Signals Generated
- Check if RSI is reaching extreme levels (< 30 or > 70)
- Verify range is still valid
- Ensure 4-hour candles are completing
- Check logs for indicator calculation

### Too Many Signals
- Increase RSI thresholds (e.g., < 25 and > 75)
- Widen the range boundaries
- Increase min_time_between_trades
- Add additional filters

### Losses Exceeding Wins
- Range may be breaking down
- Support/resistance levels may need adjustment
- Consider pausing strategy during high volatility
- Review if market is trending instead of ranging

## Advanced Optimization

### Fine-Tuning RSI Levels
- More conservative: RSI < 25 and > 75
- More aggressive: RSI < 35 and > 65
- Backtest to find optimal levels for your range

### Dynamic Position Sizing
- Larger positions at extreme RSI levels
- Smaller positions at moderate RSI levels
- Scale in/out at different price levels

### Multiple Timeframe Confirmation
- Add 1-hour RSI for additional confirmation
- Use daily timeframe to confirm range structure
- Require alignment across timeframes

## Resources

- **Strategy file**: `strategies/range_trading_strategy.yaml`
- **Schema documentation**: `strategies/STRATEGY_SCHEMA.md`
- **Test mode guide**: `TEST_MODE_QUICK_START.md`
- **Main documentation**: `README.md`

## Support

For questions or issues:
1. Check the logs: `logs/trading_bot.log`
2. Review the strategy schema documentation
3. Test in test mode before live trading
4. Start with small position sizes

---

**Disclaimer**: This strategy is for educational purposes. Always test thoroughly and understand the risks before live trading. Past performance does not guarantee future results.
