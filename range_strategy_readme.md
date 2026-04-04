# Range Trading Strategy Guide

## Overview

The range trading strategy is designed to profit from price oscillations within a defined range. It buys at support when oversold and sells at resistance when overbought, taking profit at the mid-range.

## Strategy Logic

### Entry Conditions

**Long Entry (Buy)**:
- RSI (4h) < 30 (oversold)
- Price near support level (automatically detected within 0.5% by default)
- Opens a long position expecting price to bounce up

**Short Entry (Sell)**:
- RSI (4h) > 70 (overbought)  
- Price near resistance level (automatically detected within 0.5% by default)
- Opens a short position expecting price to drop

### Automatic Price Proximity Detection

The bot automatically monitors when price is near your defined support or resistance levels:

- **Proximity threshold**: Configurable via `level_proximity_percent` (default: 0.5%)
- **Automatic logging**: Bot logs when price enters/exits proximity zones
- **Combined conditions**: Entry signals only generated when BOTH RSI AND proximity conditions are met
- **No manual monitoring needed**: The bot handles all proximity detection automatically

### Exit Conditions

**Take Profit**:
- Exit when price reaches mid-range (exactly halfway between support and resistance)
- For long: Sell when price rises to mid-range
- For short: Buy back when price falls to mid-range

**Stop Loss**:
- 2% stop loss to protect against range breakouts
- 72-hour time limit to avoid holding through structural changes

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

# Optional: Adjust proximity threshold (default: 0.5%)
level_proximity_percent: 0.5  # Price within 0.5% of level

# Entry conditions - bot automatically detects proximity
entry_conditions:
  - type: "less_than"
    indicator: "rsi_4h"
    value: 30
    description: "RSI below 30 (oversold)"
  
  - type: "price_near_level"
    level: "support"
    description: "Price within 0.5% of support level"

# Update exit conditions with mid-range
exit_conditions:
  - type: "support_resistance"
    price: 70000.0  # (support + resistance) / 2
    direction: "above"
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
- Detect when price is near support/resistance levels
- Generate long signals when RSI < 30 AND price near support
- Generate short signals when RSI > 70 AND price near resistance
- Log proximity zone entry/exit events for debugging

Check the logs to see proximity detection in action:
```
entering_level_proximity: strategy=btc_range_trading, level=support, current_price=68200, distance_percent=0.29%
```

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
- Price respecting the defined levels

### Bad Conditions ❌
- Strong trending market (up or down)
- Range breakout in progress
- High volatility / news events
- Unclear support/resistance levels
- Frequent false breakouts

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

## Automatic Level Detection Features

The bot includes sophisticated automatic price proximity detection:

### How It Works

1. **Distance Calculation**: The bot continuously calculates the percentage distance from current price to your defined levels:
   ```
   distance_percent = abs(current_price - level_price) / level_price * 100
   ```

2. **Proximity Threshold**: You define how close is "near" using `level_proximity_percent` (default: 0.5%)

3. **Zone Tracking**: The bot tracks when price enters and exits proximity zones:
   - Logs `entering_level_proximity` when price moves within threshold
   - Logs `exiting_level_proximity` when price moves outside threshold

4. **Combined Conditions**: Entry signals only generated when ALL conditions are met:
   - RSI condition (oversold/overbought)
   - Price proximity condition (near support/resistance)

### Example Log Output

```
[INFO] range_levels_configured: support=68000.0, resistance=72000.0, mid_range=70000.0, range_width_percent=5.88%
[INFO] entering_level_proximity: strategy=btc_range_trading, level=support, level_price=68000.0, current_price=68200.0, distance_percent=0.29%, threshold_percent=0.5%
[INFO] entry_signal_generated: strategy=btc_range_trading, side=buy, reason="RSI below 30 (oversold); Price 68200.00 within 0.29% of support 68000.00"
[INFO] exiting_level_proximity: strategy=btc_range_trading, level=support, level_price=68000.0, current_price=69500.0, distance_percent=2.21%, threshold_percent=0.5%
```

### Configuration Options

**Adjust Proximity Threshold**:
```yaml
level_proximity_percent: 0.3  # Tighter - only 0.3% from level
level_proximity_percent: 1.0  # Looser - within 1% of level
```

**Valid Range**: 0.1% to 5.0%

### Benefits

- ✅ No manual price monitoring required
- ✅ Precise entry timing at optimal levels
- ✅ Clear logging for debugging and analysis
- ✅ Prevents false signals when price is far from levels
- ✅ Configurable sensitivity via proximity threshold

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

**Check RSI Levels**:
- Verify RSI is reaching extreme levels (< 30 or > 70)
- Check logs for RSI values: `rsi_4h=28.5`
- Consider adjusting thresholds if market conditions changed

**Check Price Proximity**:
- Look for `entering_level_proximity` log messages
- If not appearing, price may not be reaching your levels
- Verify support/resistance levels are still valid
- Check distance_percent in logs to see how far price is from levels

**Check Both Conditions**:
- Entry requires BOTH RSI AND proximity conditions
- Look for `entry_condition_not_met` debug logs
- These show which specific condition failed

**Verify Configuration**:
- Ensure 4-hour candles are completing
- Check that `price_near_level` condition is in entry_conditions
- Verify `support_level` and `resistance_level` are defined

### Too Many Signals

**Tighten Proximity Threshold**:
```yaml
level_proximity_percent: 0.3  # Reduce from 0.5% to 0.3%
```

**Adjust RSI Thresholds**:
```yaml
# More conservative
- type: "less_than"
  indicator: "rsi_4h"
  value: 25  # Changed from 30
```

**Increase Trade Spacing**:
```yaml
risk_parameters:
  min_time_between_trades: 14400  # 4 hours instead of 2
```

### Proximity Detection Not Working

**Check Level Configuration**:
```
[ERROR] missing_support_level: price_near_level condition requires support_level to be defined
```
- Ensure `support_level` is defined in YAML
- Ensure `resistance_level` is defined in YAML

**Check Validation Errors**:
```
[ERROR] resistance_level must be greater than support_level
```
- Verify resistance > support
- Check for typos in level values

**Check Range Width Warnings**:
```
[WARNING] narrow_range_detected: range_width_percent=0.8%, message="Range width < 1% may result in frequent false signals"
```
- Consider widening the range
- Or accept more frequent signals with narrow range

### Losses Exceeding Wins

**Range May Be Breaking Down**:
- Check if price is breaking out of range
- Look for trend formation on higher timeframes
- Consider pausing strategy during breakouts

**Levels Need Adjustment**:
- Support/resistance may have shifted
- Update levels based on recent price action
- Check for new swing highs/lows

**Market Conditions Changed**:
- High volatility can invalidate ranges
- News events can cause breakouts
- Consider pausing during major announcements

### Understanding Log Messages

**Level Configuration**:
```
[INFO] range_levels_configured: support=68000.0, resistance=72000.0, mid_range=70000.0, range_width_percent=5.88%
```
- Confirms your levels loaded correctly
- Shows calculated mid-range
- Displays range width percentage

**Proximity Zone Entry**:
```
[INFO] entering_level_proximity: strategy=btc_range_trading, level=support, level_price=68000.0, current_price=68200.0, distance_percent=0.29%, threshold_percent=0.5%
```
- Price moved within proximity threshold
- Shows exact distance from level
- Indicates proximity condition can now be met

**Proximity Zone Exit**:
```
[INFO] exiting_level_proximity: strategy=btc_range_trading, level=support, current_price=69500.0, distance_percent=2.21%
```
- Price moved outside proximity threshold
- Proximity condition no longer met
- No entry signals will generate until price returns

**Entry Signal Generated**:
```
[INFO] entry_signal_generated: strategy=btc_range_trading, side=buy, reason="RSI below 30 (oversold); Price 68200.00 within 0.29% of support 68000.00"
```
- All conditions met, signal generated
- Shows which conditions triggered
- Includes exact price and distance

**Condition Not Met**:
```
[DEBUG] entry_condition_not_met: strategy=btc_range_trading, condition_type=price_near_level, reason="Price 69500.00 is 2.21% from support 68000.00 (threshold: 0.5%)"
```
- Shows why entry didn't trigger
- Helps debug configuration issues
- Indicates which condition failed

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
