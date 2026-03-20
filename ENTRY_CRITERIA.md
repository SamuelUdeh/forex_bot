# Trading Machine - Entry Criteria Documentation

## System Overview

The Trading Machine uses a 15-point confluence system combining:
- **Technical Indicators** (6 points): EMA, RSI, MACD, ADX, Bollinger Bands
- **Smart Money Concepts** (4 points): Structure, S/R, Order Blocks, Liquidity
- **Candlestick Patterns** (2 points): 20+ reversal/continuation patterns
- **Volume Analysis** (2 points): OBV, Volume Spikes (when available)
- **Session Filter** (1 point): London/NY sessions (Forex only)

---

## Backtest Results (Trading Machine v4)

| Pair | Timeframe | Win Rate | Signals | Profit Factor | Status |
|------|-----------|----------|---------|---------------|--------|
| **R_10** | H1 | **65.8%** | 38 | 2.02 | BEST |
| **R_100** | H1 | 57.1% | 42 | 1.41 | GOOD |
| **R_75** | H4 | 47.5% | 40 | 0.68 | A-ONLY |
| **R_25** | H1 | 33.3% | 3 | 0.49 | DISABLE |

### A-Grade Performance (73%+ confluence)
| Pair | A Win Rate | B Win Rate |
|------|------------|------------|
| R_75 | 66.7% | 45.9% |
| R_100 | 100% | 56.1% |

**Recommendation**: Only trade A and A+ grade setups for best results.

---

## Confluence Scoring System (12-15 points max)

### Technical Indicators (6 points)

| Indicator | BUY Condition | SELL Condition | Points |
|-----------|---------------|----------------|--------|
| EMA 200 | Price > EMA200 | Price < EMA200 | +1 |
| EMA Cross | EMA50 > EMA200 | EMA50 < EMA200 | +1 |
| RSI (14) | RSI 45-55 (neutral) | RSI 45-55 (neutral) | +1 |
| MACD | Above signal line | Below signal line | +1 |
| ADX | ADX > 20 | ADX > 20 | +1 |
| Bollinger | At lower band | At upper band | +1 |

### Smart Money Concepts (4 points)

| SMC Factor | BUY Condition | SELL Condition | Points |
|------------|---------------|----------------|--------|
| Structure | Higher highs/lows | Lower highs/lows | +1 |
| S/R Level | At support | At resistance | +1 |
| Order Block | In bullish OB | In bearish OB | +1 |
| Liquidity | NOT near liquidity | NOT near liquidity | +1 |

### Candlestick Patterns (2 points max)

**Bullish Patterns**: Engulfing, Hammer, Inverted Hammer, Morning Star, Dragonfly Doji, Three White Soldiers, Piercing Line, Tweezer Bottom, Tower Bottom, Bullish Harami, Rising Three Methods

**Bearish Patterns**: Engulfing, Shooting Star, Hanging Man, Evening Star, Gravestone Doji, Three Black Crows, Dark Cloud Cover, Tweezer Top, Tower Top, Upside Gap Two Crows, Bearish Harami, Falling Three Methods

### Volume Analysis (2 points - when available)

| Volume Factor | Condition | Points |
|---------------|-----------|--------|
| Volume Spike | Volume > 1.5x average | +1 |
| OBV Trend | OBV trending with direction | +1 |

---

## Signal Grading System

| Grade | Confluence | Action |
|-------|------------|--------|
| **A+** | 87%+ (11+/12) | TAKE TRADE - Highest confidence |
| **A** | 73%+ (9-10/12) | TAKE TRADE - High confidence |
| **B** | 60%+ (7-8/12) | CAUTION - Only with confirmation |

**Note**: For synthetics without volume, max score is 12. For Forex with volume, max score is 15.

---

## Risk Management

### ATR-Based Stops & Targets

| Pair | SL | TP1 | TP2 |
|------|-----|-----|-----|
| R_10, R_25, R_100 | 1.5x ATR | 1.5x ATR | 2.5x ATR |
| R_75 | 2.0x ATR | 1.5x ATR | 2.5x ATR |
| BOOM/CRASH | 2.0x ATR | 2.0x ATR | 4.0x ATR |

### Position Sizing
- Risk 1-2% of account per trade
- Take 50% at TP1, let 50% run to TP2

---

## Boom/Crash Rules

| Index | Direction | Reason |
|-------|-----------|--------|
| BOOM300N/500/1000 | BUY ONLY | Spikes upward |
| CRASH300N/500/1000 | SELL ONLY | Spikes downward |

---

## Quick Entry Checklist

Before taking any trade, confirm:

1. [ ] Grade is A or A+ (73%+ confluence)
2. [ ] EMA trend aligned
3. [ ] Market structure confirmed (HH/HL or LH/LL)
4. [ ] ADX > 20 (market is trending)
5. [ ] Candlestick pattern confirms direction (if available)
6. [ ] Using correct timeframe (H4 for R_75, H1 for others)
7. [ ] Boom = BUY only, Crash = SELL only

---

## Recommended Pairs

### High Performance (Always Trade)
- **R_10** (H1): 65.8% win rate, Profit Factor 2.02

### Good Performance
- **R_100** (H1): 57.1% win rate, Profit Factor 1.41

### A-Grade Only
- **R_75** (H4): Only trade A-grade setups (66.7% win rate)

### Disabled
- R_25: Poor performance (33.3%)
- 1HZ pairs: Not suitable for this strategy
