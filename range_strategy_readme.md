# Range Trading Strategy: Mean Reversion

## Overview

This strategy trades within established price ranges by:
- Going **LONG** at dynamic support levels
- Going **SHORT** at dynamic resistance levels
- Exiting at **mid-range** (POC/fair value) for profit
- Exiting via **stop-loss** when range breakout is confirmed

---

## Support/Resistance Calculation

### Method: Swing Highs and Lows

| Level | Calculation | Timeframe |
|-------|-------------|-----------|
| **Support** | Recent swing low | 1H (20 candle lookback) |
| **Resistance** | Recent swing high | 1H (20 candle lookback) |
| **Range** | Area between support and resistance | - |

### Swing Detection Parameters
- **Lookback period:** 20 candles
- **Pivot bars:** 3 bars on each side (price must be lower/higher than 3 bars on each side to qualify as swing)
- **Zone width:** ±0.3% around the exact level (creates a "band" not just a line)

### Range Validation
- Minimum range width: 1.0%
- Maximum range width: 5.0%

---

## 200 EMA (4H) Reference Line

The 200 EMA on the 4-hour timeframe serves two critical functions:

### 1. Trend Context for Entries
- **Price > 200 EMA:** Bullish bias, favor long entries at support
- **Price < 200 EMA:** Bearish bias, favor short entries at resistance
- **Price within 0.5% of EMA:** Neutral zone

### 2. Range Breakout Confirmation (100% Probability)

This is a critical signal that confirms the range is broken:

```
IF ema_200_4h > resistance_level THEN
    breakout_direction = UP
    probability = 100%
    action = CLOSE ALL POSITIONS

IF ema_200_4h < support_level THEN
    breakout_direction = DOWN
    probability = 100%
    action = CLOSE ALL POSITIONS
```

**Why this works:** The 200 EMA is a slow-moving average. When it crosses the range bounds, it indicates a sustained move that has shifted the macro structure, not just a temporary spike.

---

## State Machine Design

The strategy uses a state machine to track the probability of a range breakout.

### States

| State | Probability | Description | Trigger |
|-------|-------------|-------------|---------|
| **NEUTRAL** | 0% | Outside S/R bands, no trade setup | Default state |
| **BAND_ENTERED** | 20-40% | Price entered S/R zone | Price within ±0.5% of S/R |
| **AT_LEVEL** | 40-70% | Price at or very close to S/R | Price within ±0.2% of S/R |
| **PAST_LEVEL** | 70-90% | Price broke past S/R (suspected breakout) | Price beyond S/R by 0.2-0.5% |
| **CONFIRMED_BREAKOUT** | 100% | Range exit confirmed | See confirmation criteria below |

### State Transition Diagram

```
                    ┌─────────────────────────────────────────┐
                    │                                         │
                    ▼                                         │
┌─────────┐    ┌─────────────┐    ┌──────────┐    ┌───────────┴──┐    ┌────────────────────┐
│ NEUTRAL │───►│ BAND_ENTERED│───►│ AT_LEVEL │───►│  PAST_LEVEL  │───►│ CONFIRMED_BREAKOUT │
└─────────┘    └─────────────┘    └──────────┘    └──────────────┘    └────────────────────┘
                    │                   │               │                       ▲
                    │                   │               │                       │
                    │                   └───────────────┘                       │
                    │                   (price bounces back)                    │
                    │                                                           │
                    └───────────────────────────────────────────────────────────┘
                              (200 EMA crosses range bounds - from ANY state)
```

### Transition Rules

| From | To | Condition |
|------|----|-----------|
| NEUTRAL | BAND_ENTERED | Price enters S/R zone (within 0.5%) |
| BAND_ENTERED | AT_LEVEL | Price approaches exact level (within 0.2%) |
| BAND_ENTERED | NEUTRAL | Price moves back to mid-range |
| AT_LEVEL | BAND_ENTERED | Price bounces into band |
| AT_LEVEL | PAST_LEVEL | Price breaks through S/R |
| PAST_LEVEL | AT_LEVEL | Price pulls back (false breakout) |
| PAST_LEVEL | CONFIRMED_BREAKOUT | Breakout confirmed |
| **ANY STATE** | CONFIRMED_BREAKOUT | 200 EMA crosses range bounds |

---

## Breakout Confirmation Criteria

### Suspected Breakout (PAST_LEVEL: 70-90%)

Triggered when:
- Price beyond S/R by 0.3%
- At least 1 candle close beyond S/R

**Action:** Tighten stop-loss to 0.2%

### Confirmed Breakout (100%)

Triggered when ANY of the following occur:

1. **Price Action Confirmation:**
   - Price beyond S/R by >0.5%
   - 2 consecutive candle closes beyond S/R

2. **Volume Confirmation:**
   - Price beyond S/R by >0.5%
   - Volume >1.5x average

3. **200 EMA Confirmation (Highest Priority):**
   - 200 EMA (4H) crosses above resistance, OR
   - 200 EMA (4H) crosses below support

**Action:** Close all positions immediately, invalidate range

---

## Entry Logic

### Long Entry (at Support)

All conditions must be true:

| # | Condition | Description |
|---|-----------|-------------|
| 1 | State = AT_LEVEL | State machine indicates price at support |
| 2 | Price within 0.2% of support | Price in the support zone |
| 3 | RSI (15m) < 35 | Oversold confirmation |
| 4 | 200 EMA within range | Range is intact (EMA between S/R) |

### Short Entry (at Resistance)

All conditions must be true:

| # | Condition | Description |
|---|-----------|-------------|
| 1 | State = AT_LEVEL | State machine indicates price at resistance |
| 2 | Price within 0.2% of resistance | Price in the resistance zone |
| 3 | RSI (15m) > 65 | Overbought confirmation |
| 4 | 200 EMA within range | Range is intact (EMA between S/R) |

---

## Exit Logic

### Take Profit

- **Target:** Mid-range (Point of Control if available)
- **Calculation:** `(Support + Resistance) / 2`
- **POC:** If volume profile is available, use the price level with highest traded volume

### Stop Loss

- **Level:** 0.5% beyond the entry S/R level
- **For long:** Support - 0.5%
- **For short:** Resistance + 0.5%

### State-Based Exits

| State | Action |
|-------|--------|
| PAST_LEVEL | Tighten stop to 0.2% beyond S/R |
| CONFIRMED_BREAKOUT | Close all positions immediately |

### 200 EMA Breakout Exit

```
IF 200 EMA > Resistance OR 200 EMA < Support:
    → Close all positions immediately
    → Invalidate current range
    → Wait for new range to form
```

### Time-Based Exit

- Exit after 4 hours if neither take profit nor stop loss is hit

---

## Volume Profile / POC

### Point of Control (POC)

- **Definition:** Price level with the highest traded volume over the lookback period
- **Calculation:** Aggregate volume at each price level over 48 hours (1H candles)
- **Usage:** Take profit target (mean reversion point)

### Volume Filter for Entries

- Only enter when volume < 1.2x average
- Avoid entering during breakout attempts (high volume)

### Volume Confirmation for Breakout

- Breakout confirmed when volume > 1.5x average at breakout candle

---

## Risk Management

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Position Size | 0.01 BTC (1% of capital) | Conservative for range trading |
| Max Position | 0.03 BTC (3% of capital) | Allow scaling in |
| Stop Loss | 0.5% beyond S/R | Confirmed breakout level |
| Take Profit | Mid-range (POC) | Mean reversion target |
| Risk:Reward | 1:1.5 to 1:2 | Depends on range width |
| Max trades/day | 3 | Avoid overtrading |
| Cooldown after loss | 2 hours | Let market settle |
| Max daily loss | 2% | Capital preservation |

---

## Ideal Market Conditions

### Use This Strategy When:
- Market is ranging/consolidating
- Clear S/R levels with multiple touches
- Low volatility environment
- Price oscillates between defined levels
- 200 EMA is flat or within the range

### Avoid This Strategy When:
- Strong trending markets
- High volatility news events
- S/R levels are unclear or untested
- Price making new highs/lows
- 200 EMA is steeply sloped

---

## Decision Flow Summary

```
1. IDENTIFY RANGE
   └── Calculate swing high (resistance) and swing low (support)
   └── Verify 200 EMA is within range (range intact)

2. WAIT FOR ENTRY
   └── Monitor state machine for AT_LEVEL state
   └── Check RSI confirmation (oversold at support, overbought at resistance)

3. ENTER POSITION
   └── Long at support OR Short at resistance
   └── Set stop loss 0.5% beyond S/R
   └── Set take profit at mid-range (POC)

4. MONITOR POSITION
   └── Track state machine for breakout probability
   └── Watch 200 EMA position relative to range bounds

5. EXIT POSITION
   └── Take profit at mid-range, OR
   └── Stop loss if price breaks S/R, OR
   └── Immediate exit if 200 EMA crosses range bounds (100% confirmed)

6. REPEAT
   └── If range still valid, wait for next entry
   └── If range broken, wait for new range to form
```
