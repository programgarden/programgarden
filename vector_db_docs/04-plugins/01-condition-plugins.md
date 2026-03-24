---
category: plugin
tags: [condition, rsi, macd, bollinger, stochastic, adx, obv, atr, volume, momentum, trend, ichimoku, vwap, parabolic_sar, williams_r, cci, supertrend, keltner, trix, cmf, engulfing, hammer, doji, morning_star, candlestick, partial_profit, time_exit, connors_rsi, mfi, coppock_curve, tsmom, elder_ray, turtle_breakout, volatility_breakout, seasonal_filter, taa, magic_formula, z_score, squeeze_momentum, momentum_rank, market_internals, pair_trading, support_resistance, level_touch, dynamic_stop_loss, max_position_limit]
priority: critical
---

# Condition Plugins: Technical Analysis + Position Management

## Overview

Condition plugins are used by specifying them in the `plugin` field of a `ConditionNode`. There are two categories:

| Category | Description | Input | Count | Plugins |
|----------|-------------|-------|-------|---------|
| **TECHNICAL** | Price/volume-based technical analysis | `items` (from/extract) | 52 | RSI, MACD, BollingerBands, etc. |
| **POSITION** | P&L/risk analysis for held positions | `positions` / `data` | 15 | StopLoss, ProfitTarget, KellyCriterion, RiskParity, etc. |

> For a complete list of all 67 plugins with settings, see the [Plugin Quick Reference](../11-appendix/02-plugin-quick-reference.md).

## Common Input/Output Structure

### TECHNICAL Plugin Input

```json
{
  "id": "rsi_check",
  "type": "ConditionNode",
  "plugin": "RSI",
  "items": {
    "from": "{{ nodes.historical.value.time_series }}",
    "extract": {
      "symbol": "{{ nodes.historical.value.symbol }}",
      "exchange": "{{ nodes.historical.value.exchange }}",
      "date": "{{ row.date }}",
      "close": "{{ row.close }}"
    }
  },
  "fields": {
    "period": 14,
    "threshold": 30,
    "direction": "below"
  }
}
```

- `items`: Data input (`from`: iteration array, `extract`: field mapping)
- `fields`: Plugin-specific parameters
- `field_mapping`: Field name customization (optional, using defaults is recommended)

> In the individual plugin examples below, `items` follows the same common structure shown above, so only `fields` are displayed.

### POSITION Plugin Input

```json
{
  "id": "stop_check",
  "type": "ConditionNode",
  "plugin": "StopLoss",
  "positions": "{{ nodes.real_account.positions }}",
  "fields": {
    "stop_percent": -3.0
  }
}
```

- `positions`: Output from `RealAccountNode`'s `positions`

### Common Output Structure

All plugins return the same output structure:

```json
{
  "passed_symbols": [{"exchange": "NASDAQ", "symbol": "AAPL"}],
  "failed_symbols": [{"exchange": "NASDAQ", "symbol": "NVDA"}],
  "symbol_results": [
    {"symbol": "AAPL", "exchange": "NASDAQ", "rsi": 28.5, "current_price": 150.0}
  ],
  "values": [
    {
      "symbol": "AAPL",
      "exchange": "NASDAQ",
      "time_series": [
        {"date": "20260101", "close": 148.0, "rsi": 32.1, "signal": null, "side": "long"},
        {"date": "20260102", "close": 145.0, "rsi": 28.5, "signal": "buy", "side": "long"}
      ]
    }
  ],
  "result": true
}
```

| Field | Description |
|-------|-------------|
| `passed_symbols` | Symbols that passed the condition |
| `failed_symbols` | Symbols that failed the condition |
| `symbol_results` | Detailed indicator values per symbol |
| `values` | Time series data (for chart display, includes signal/side) |
| `result` | `true` if at least one symbol passed |

### signal/side Fields in time_series

All TECHNICAL plugins include `signal` and `side` fields in their `time_series`:
- `signal`: `"buy"`, `"sell"`, or `null` (no signal)
- `side`: `"long"` (default; overseas stocks only support long positions)

---

## TECHNICAL Plugins (52)

> This section documents 29 core plugins in detail. For the full list of 52 TECHNICAL plugins including ConnorsRSI, MFI, CoppockCurve, TimeSeriesMomentum, ElderRay, TurtleBreakout, VolatilityBreakout, SeasonalFilter, TacticalAssetAllocation, MagicFormula, ZScore, SqueezeMomentum, MomentumRank, MarketInternals, PairTrading, SupportResistanceLevels, LevelTouch, and more, see the [Plugin Quick Reference](../11-appendix/02-plugin-quick-reference.md).

### Momentum / Oscillators

#### 1. RSI (Relative Strength Index)

Identifies overbought/oversold conditions. RSI below 30 = buy opportunity, above 70 = sell opportunity.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `period` | int | 14 | RSI calculation period (2~100) |
| `threshold` | float | 30 | Oversold/overbought threshold (0~100) |
| `direction` | string | `"below"` | `below`: oversold, `above`: overbought |

**Required data**: close, date, symbol, exchange
**Minimum data**: period + 1 days

```json
{
  "id": "rsi", "type": "ConditionNode", "plugin": "RSI",
  "fields": {"period": 14, "threshold": 30, "direction": "below"}
}
```

**symbol_results output**: `rsi`, `current_price`
**tags**: momentum, oscillator

---

#### 2. Stochastic Oscillator

Identifies overbought/oversold conditions using %K and %D crossovers. %K crossing above %D below 20 = buy signal.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `k_period` | int | 14 | %K calculation period (1~100) |
| `d_period` | int | 3 | %D smoothing period (1~50) |
| `threshold` | float | 20 | Oversold threshold (overbought = 100-threshold) |
| `direction` | string | `"oversold"` | `oversold`, `overbought` |

**Required data**: high, low, close, date, symbol, exchange
**Minimum data**: k_period + d_period - 1 days

```json
{
  "id": "stoch", "type": "ConditionNode", "plugin": "Stochastic",
  "fields": {"k_period": 14, "d_period": 3, "threshold": 20, "direction": "oversold"}
}
```

**symbol_results output**: `k`, `d`
**tags**: momentum, oscillator

---

#### 3. DualMomentum

Absolute momentum (recent returns) + relative momentum (performance vs. benchmark). Based on Gary Antonacci's strategy.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `lookback_period` | int | 252 | Lookback period (approx. 1 year) |
| `absolute_threshold` | float | 0.0 | Absolute momentum threshold (%) |
| `use_relative` | bool | true | Whether to use relative momentum |
| `relative_benchmark` | string | `"SHY"` | Benchmark (`SHY`, `BIL`, `CASH`) |

**Required data**: close, date, symbol, exchange
**Minimum data**: lookback_period + 1 days
**Additional output**: `ranking` (momentum ranking)

```json
{
  "id": "dm", "type": "ConditionNode", "plugin": "DualMomentum",
  "fields": {"lookback_period": 252, "absolute_threshold": 0.0, "use_relative": true}
}
```

**symbol_results output**: `momentum`, `benchmark_momentum`, `absolute_pass`, `relative_pass`
**tags**: momentum, trend, asset_allocation

---

#### 4. MeanReversion

Expects price reversion to the mean when it deviates significantly from the moving average.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `ma_period` | int | 20 | MA period (5~200) |
| `deviation` | float | 2.0 | Standard deviation multiplier (1.0~4.0) |
| `direction` | string | `"oversold"` | `oversold`, `overbought` |

**Required data**: close, date, symbol, exchange

```json
{
  "id": "mr", "type": "ConditionNode", "plugin": "MeanReversion",
  "fields": {"ma_period": 20, "deviation": 2.0, "direction": "oversold"}
}
```

**symbol_results output**: `ma`, `std`, `upper`, `lower`, `current_price`, `deviation_pct`
**tags**: momentum, mean_reversion

---

#### 5. WilliamsR

Oscillator on an inverted scale (-100 to 0). Below -80 = oversold (buy signal), above -20 = overbought (sell signal).

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `period` | int | 14 | Lookback period (2~100) |
| `threshold` | float | -80 | Oversold threshold (-99~-1) |
| `direction` | string | `"oversold"` | `oversold`, `overbought` |

**Required data**: high, low, close, date, symbol, exchange

```json
{
  "id": "wr", "type": "ConditionNode", "plugin": "WilliamsR",
  "fields": {"period": 14, "threshold": -80, "direction": "oversold"}
}
```

**symbol_results output**: `williams_r`
**tags**: momentum, oscillator, williams

---

#### 6. CCI (Commodity Channel Index)

Measures deviation from the moving average of the typical price (TP). Above +100 = overbought, below -100 = oversold. A key indicator for futures traders.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `period` | int | 20 | CCI calculation period (2~200) |
| `threshold` | float | 100 | Overbought/oversold threshold (50~300) |
| `direction` | string | `"oversold"` | `oversold`, `overbought` |

**Required data**: high, low, close, date, symbol, exchange

```json
{
  "id": "cci", "type": "ConditionNode", "plugin": "CCI",
  "fields": {"period": 20, "threshold": 100, "direction": "oversold"}
}
```

**symbol_results output**: `cci`, `typical_price`
**tags**: momentum, oscillator, cci, futures

---

### Trend / Moving Averages

#### 7. MACD (Moving Average Convergence Divergence)

Detects trend reversal points using short/long-term moving average crossovers. Histogram turning positive = bullish signal.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `fast_period` | int | 12 | Fast EMA period |
| `slow_period` | int | 26 | Slow EMA period |
| `signal_period` | int | 9 | Signal line period |
| `signal_type` | string | `"bullish_cross"` | `bullish_cross`, `bearish_cross` |

**Required data**: close, date, symbol, exchange
**Minimum data**: slow_period + signal_period days (default 35 days)

```json
{
  "id": "macd", "type": "ConditionNode", "plugin": "MACD",
  "fields": {"fast_period": 12, "slow_period": 26, "signal_period": 9, "signal_type": "bullish_cross"}
}
```

**symbol_results output**: `macd`, `signal`, `histogram`
**tags**: trend, momentum

---

#### 8. MovingAverageCross

Short MA crossing above long MA = Golden Cross (bullish). Short MA crossing below long MA = Death Cross (bearish).

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `short_period` | int | 5 | Short MA period |
| `long_period` | int | 20 | Long MA period |
| `cross_type` | string | `"golden"` | `golden`, `dead` |

**Required data**: close, date, symbol, exchange
**Minimum data**: long_period + 1 days

```json
{
  "id": "ma", "type": "ConditionNode", "plugin": "MovingAverageCross",
  "fields": {"short_period": 5, "long_period": 20, "cross_type": "golden"}
}
```

**symbol_results output**: `short_ma`, `long_ma`, `status` (bullish/bearish)
**tags**: trend, moving_average, crossover

---

#### 9. ADX (Average Directional Index)

Measures trend strength (regardless of direction). ADX > 25 = strong trend, < 20 = sideways/range-bound.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `period` | int | 14 | ADX period (5~50) |
| `threshold` | float | 25.0 | Strong trend threshold (15~50) |
| `direction` | string | `"strong_trend"` | `strong_trend`, `uptrend`, `downtrend` |

**Required data**: high, low, close, date, symbol, exchange
**Minimum data**: period x 2 days

```json
{
  "id": "adx", "type": "ConditionNode", "plugin": "ADX",
  "fields": {"period": 14, "threshold": 25.0, "direction": "uptrend"}
}
```

**symbol_results output**: `adx`, `plus_di`, `minus_di`
**tags**: trend, momentum, strength

---

#### 10. IchimokuCloud

Comprehensive trend analysis using Tenkan-sen, Kijun-sen, Senkou Span A/B (cloud), and Chikou Span. Supports price-cloud position, TK cross, and cloud color change signals.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `tenkan_period` | int | 9 | Tenkan-sen (conversion line) period (2~100) |
| `kijun_period` | int | 26 | Kijun-sen (base line) period (2~200) |
| `senkou_b_period` | int | 52 | Senkou Span B period (2~300) |
| `signal_type` | string | `"price_above_cloud"` | `price_above_cloud`, `price_below_cloud`, `tk_cross_bullish`, `tk_cross_bearish`, `cloud_bullish`, `cloud_bearish` |

**Required data**: close, high, low, date, symbol, exchange
**Minimum data**: senkou_b_period + kijun_period days

```json
{
  "id": "ichimoku", "type": "ConditionNode", "plugin": "IchimokuCloud",
  "fields": {"tenkan_period": 9, "kijun_period": 26, "senkou_b_period": 52, "signal_type": "price_above_cloud"}
}
```

**symbol_results output**: `tenkan_sen`, `kijun_sen`, `senkou_span_a`, `senkou_span_b`, `chikou_span`, `current_close`, `cloud_top`, `cloud_bottom`
**tags**: trend, ichimoku, cloud, japanese

---

#### 11. ParabolicSAR

Tracks trend direction and reversal points by plotting dots above/below the price. The acceleration factor increases as the trend strengthens. Useful for trailing stops and trend detection.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `af_start` | float | 0.02 | Initial acceleration factor (0.001~0.1) |
| `af_step` | float | 0.02 | Acceleration factor increment (0.001~0.1) |
| `af_max` | float | 0.20 | Maximum acceleration factor (0.05~0.5) |
| `signal_type` | string | `"bullish_reversal"` | `bullish_reversal`, `bearish_reversal`, `uptrend`, `downtrend` |

**Required data**: close, high, low, date, symbol, exchange

```json
{
  "id": "psar", "type": "ConditionNode", "plugin": "ParabolicSAR",
  "fields": {"af_start": 0.02, "af_step": 0.02, "af_max": 0.20, "signal_type": "bullish_reversal"}
}
```

**symbol_results output**: `sar`, `trend`, `current_close`
**tags**: trend, reversal, parabolic, trailing_stop

---

#### 12. Supertrend

ATR-based trend-following indicator. Provides clear buy/sell signals with upper/lower bands.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `period` | int | 10 | ATR calculation period (2~100) |
| `multiplier` | float | 3.0 | ATR multiplier (0.5~10.0) |
| `signal_type` | string | `"bullish"` | `bullish`, `bearish`, `uptrend`, `downtrend` |

**Required data**: close, high, low, date, symbol, exchange

```json
{
  "id": "st", "type": "ConditionNode", "plugin": "Supertrend",
  "fields": {"period": 10, "multiplier": 3.0, "signal_type": "bullish"}
}
```

**symbol_results output**: `supertrend`, `trend`
**tags**: trend, atr, supertrend

---

#### 13. TRIX (Triple Exponential Moving Average)

Removes noise by applying EMA three times. Determines trends via TRIX-signal line crossovers and zero-line crossovers.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `period` | int | 15 | Triple EMA smoothing period (2~100) |
| `signal_period` | int | 9 | Signal line EMA period (2~50) |
| `signal_type` | string | `"bullish_cross"` | `bullish_cross`, `bearish_cross`, `above_zero`, `below_zero` |

**Required data**: close, date, symbol, exchange

```json
{
  "id": "trix", "type": "ConditionNode", "plugin": "TRIX",
  "fields": {"period": 15, "signal_period": 9, "signal_type": "bullish_cross"}
}
```

**symbol_results output**: `trix`, `signal_line`, `histogram`
**tags**: trend, momentum, trix, ema

---

### Volatility / Channels

#### 14. BollingerBands

Measures how far the price has deviated from the mean. Near the lower band = undervalued, near the upper band = overvalued.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `period` | int | 20 | Moving average period (5~100) |
| `std_dev` | float | 2.0 | Standard deviation multiplier (0.5~4.0) |
| `position` | string | `"below_lower"` | `below_lower`, `above_upper` |

**Required data**: close, date, symbol, exchange (optional: high, low)
**Minimum data**: period days

```json
{
  "id": "bb", "type": "ConditionNode", "plugin": "BollingerBands",
  "fields": {"period": 20, "std_dev": 2.0, "position": "below_lower"}
}
```

**symbol_results output**: `upper`, `middle`, `lower`, `current_price`
**tags**: volatility, mean-reversion

---

#### 15. ATR (Average True Range)

Measures volatility. Uses ATR band breakouts to determine entry/exit timing.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `period` | int | 14 | ATR period (1~100) |
| `multiplier` | float | 2.0 | ATR multiplier (0.5~5.0) |
| `direction` | string | `"breakout_up"` | `breakout_up`, `breakout_down` |

**Required data**: high, low, close, date, symbol, exchange
**Minimum data**: period + 1 days

```json
{
  "id": "atr", "type": "ConditionNode", "plugin": "ATR",
  "fields": {"period": 14, "multiplier": 2.0, "direction": "breakout_up"}
}
```

**symbol_results output**: `atr`, `ma`, `upper_band`, `lower_band`, `current_price`
**tags**: volatility, breakout

---

#### 16. PriceChannel (Donchian Channel)

N-day high/low channel breakout signals.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `period` | int | 20 | Channel period (5~100) |
| `direction` | string | `"breakout_high"` | `breakout_high`, `breakout_low` |

**Required data**: high, low, close, date, symbol, exchange
**Minimum data**: period days

```json
{
  "id": "dc", "type": "ConditionNode", "plugin": "PriceChannel",
  "fields": {"period": 20, "direction": "breakout_high"}
}
```

**symbol_results output**: `upper_channel`, `lower_channel`, `middle_channel`, `current_price`
**tags**: trend, breakout, channel

---

#### 17. KeltnerChannel

EMA + ATR-based channel. Price above the upper band indicates strong uptrend; below the lower band indicates strong downtrend. Used in squeeze strategies with Bollinger Bands.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `ema_period` | int | 20 | EMA period (2~200) |
| `atr_period` | int | 10 | ATR period (2~100) |
| `multiplier` | float | 1.5 | ATR multiplier (0.5~5.0) |
| `direction` | string | `"above_upper"` | `above_upper`, `below_lower`, `squeeze` |

**Required data**: close, high, low, date, symbol, exchange

```json
{
  "id": "kc", "type": "ConditionNode", "plugin": "KeltnerChannel",
  "fields": {"ema_period": 20, "atr_period": 10, "multiplier": 1.5, "direction": "above_upper"}
}
```

**symbol_results output**: `middle`, `upper`, `lower`, `current_close`
**tags**: channel, keltner, atr, ema, squeeze

---

### Volume Analysis

#### 18. VolumeSpike

Detects symbols with significantly higher volume than usual.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `period` | int | 20 | Average period (5+) |
| `multiplier` | float | 2.0 | Multiplier vs. average (1.0+) |

**Required data**: volume, date, symbol, exchange
**Minimum data**: 2 days

```json
{
  "id": "vol", "type": "ConditionNode", "plugin": "VolumeSpike",
  "fields": {"period": 20, "multiplier": 2.0}
}
```

**symbol_results output**: `current_volume`, `avg_volume`, `ratio`, `passed`
**tags**: volume

---

#### 19. OBV (On-Balance Volume)

Tracks buying/selling pressure through volume flow. OBV > MA = bullish momentum.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `ma_period` | int | 20 | OBV moving average period (5~100) |
| `direction` | string | `"bullish"` | `bullish`, `bearish` |

**Required data**: close, volume, date, symbol, exchange
**Minimum data**: ma_period days

```json
{
  "id": "obv", "type": "ConditionNode", "plugin": "OBV",
  "fields": {"ma_period": 20, "direction": "bullish"}
}
```

**symbol_results output**: `obv`, `obv_ma`
**tags**: volume, trend, momentum

---

#### 20. VWAP (Volume Weighted Average Price)

Volume-weighted average price. Price above VWAP indicates buying dominance; below indicates selling dominance. Supports standard deviation band options.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `direction` | string | `"above"` | Price position (`above`, `below`) |
| `band_multiplier` | float | 0.0 | Standard deviation band multiplier (0 = no bands, 0.0~5.0) |

**Required data**: close, volume, date, symbol, exchange

```json
{
  "id": "vwap", "type": "ConditionNode", "plugin": "VWAP",
  "fields": {"direction": "above", "band_multiplier": 0.0}
}
```

**symbol_results output**: `vwap`, `current_close`, `upper_band`, `lower_band`
**tags**: volume, vwap, intraday

---

#### 21. CMF (Chaikin Money Flow)

Measures accumulation and distribution using volume-weighted price. Positive CMF = accumulation (buying pressure), negative CMF = distribution (selling pressure).

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `period` | int | 20 | CMF period (2~100) |
| `threshold` | float | 0.05 | Accumulation/distribution threshold (0.01~0.5) |
| `direction` | string | `"accumulation"` | `accumulation`, `distribution` |

**Required data**: close, high, low, volume, date, symbol, exchange

```json
{
  "id": "cmf", "type": "ConditionNode", "plugin": "CMF",
  "fields": {"period": 20, "threshold": 0.05, "direction": "accumulation"}
}
```

**symbol_results output**: `cmf`, `mfv`
**tags**: volume, accumulation, distribution, chaikin

---

### Price Levels / Patterns

#### 22. GoldenRatio (Fibonacci Retracement)

Determines support/resistance levels using Fibonacci ratios (23.6%, 38.2%, 50%, 61.8%, 78.6%).

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `lookback` | int | 50 | Swing high/low search period (10~200) |
| `level` | string | `"0.618"` | Fibonacci level (`0.236`, `0.382`, `0.5`, `0.618`, `0.786`) |
| `direction` | string | `"support"` | `support`, `resistance` |
| `tolerance` | float | 0.02 | Level proximity tolerance (0.5%~10%) |

**Required data**: high, low, close, date, symbol, exchange

```json
{
  "id": "fib", "type": "ConditionNode", "plugin": "GoldenRatio",
  "fields": {"lookback": 50, "level": "0.618", "direction": "support", "tolerance": 0.02}
}
```

**symbol_results output**: `fib_level`, `fib_price`, `swing_high`, `swing_low`, `distance_pct`, `is_uptrend`
**tags**: fibonacci, support, resistance, price_level

---

#### 23. PivotPoint

Calculates daily support/resistance levels using the previous day's high, low, and close. Supports three methods: Standard, Fibonacci, and Camarilla.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `pivot_type` | string | `"standard"` | Calculation method (`standard`, `fibonacci`, `camarilla`) |
| `direction` | string | `"support"` | `support`: buy near support, `resistance`: sell near resistance |
| `tolerance` | float | 0.01 | Level proximity tolerance (0.2%~5%) |

**Required data**: high, low, close, date, symbol, exchange

```json
{
  "id": "pivot", "type": "ConditionNode", "plugin": "PivotPoint",
  "fields": {"pivot_type": "standard", "direction": "support", "tolerance": 0.01}
}
```

**symbol_results output**: `pivot_type`, `pp`, `r1`, `r2`, `r3`, `s1`, `s2`, `s3`, `current_price`, `nearest_level`, `nearest_price`, `distance_pct`
**tags**: pivot, support, resistance, price_level

---

#### 24. BreakoutRetest

Entry signal on a pullback (retest) after breaking through a key level.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `lookback` | int | 20 | Breakout level search period (5~100) |
| `retest_threshold` | float | 0.02 | Retest recognition range (0.5%~10%) |
| `direction` | string | `"bullish"` | `bullish`, `bearish` |

**Required data**: high, low, close, date, symbol, exchange
**Minimum data**: lookback + 5 days

```json
{
  "id": "br", "type": "ConditionNode", "plugin": "BreakoutRetest",
  "fields": {"lookback": 20, "retest_threshold": 0.02, "direction": "bullish"}
}
```

**symbol_results output**: `resistance`, `support`, `breakout_level`, `breakout_type`, `is_retest`
**tags**: breakout, retest, pattern

---

### Candlestick Patterns

#### 25. ThreeLineStrike

A powerful reversal pattern where a large candle in the opposite direction appears after 3 consecutive candles in the same direction. Bullish: 3 consecutive bearish candles followed by a large bullish candle. Bearish: 3 consecutive bullish candles followed by a large bearish candle.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `pattern` | string | `"bullish"` | `bullish`: bullish reversal, `bearish`: bearish reversal |
| `min_body_pct` | float | 0.3 | Minimum body ratio (0.1~1.0) |

**Required data**: open, high, low, close, date, symbol, exchange
**Minimum data**: 4 days

```json
{
  "id": "tls", "type": "ConditionNode", "plugin": "ThreeLineStrike",
  "fields": {"pattern": "bullish", "min_body_pct": 0.3}
}
```

**symbol_results output**: `pattern_detected`, `confidence`, `details`, `pattern_type`
**tags**: candlestick, pattern, reversal, three_line_strike

---

#### 26. Engulfing

The most reliable reversal candlestick pattern. The current candle completely engulfs the body of the previous candle.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `pattern` | string | `"bullish"` | `bullish`: bullish reversal, `bearish`: bearish reversal |
| `min_body_ratio` | float | 0.5 | Minimum body/range ratio for a valid candle (0.1~1.0) |

**Required data**: open, high, low, close, date, symbol, exchange

```json
{
  "id": "eng", "type": "ConditionNode", "plugin": "Engulfing",
  "fields": {"pattern": "bullish", "min_body_ratio": 0.5}
}
```

**symbol_results output**: `pattern_detected`, `confidence`, `pattern_type`
**tags**: candlestick, pattern, reversal, engulfing

---

#### 27. HammerShootingStar

Hammer (long lower shadow, bullish reversal) and Shooting Star (long upper shadow, bearish reversal).

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `pattern` | string | `"hammer"` | `hammer`: bullish reversal, `shooting_star`: bearish reversal |
| `shadow_ratio` | float | 2.0 | Minimum shadow/body ratio (1.0~10.0) |
| `body_position` | float | 0.3 | Body position range (upper/lower N%, 0.1~0.5) |

**Required data**: open, high, low, close, date, symbol, exchange

```json
{
  "id": "hs", "type": "ConditionNode", "plugin": "HammerShootingStar",
  "fields": {"pattern": "hammer", "shadow_ratio": 2.0, "body_position": 0.3}
}
```

**symbol_results output**: `pattern_detected`, `confidence`, `pattern_type`
**tags**: candlestick, pattern, reversal, hammer, shooting_star

---

#### 28. Doji

A cross-shaped candle where the open and close are nearly identical. Indicates market indecision and potential trend reversal. Supports standard, long-legged, dragonfly, and gravestone doji types.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `doji_type` | string | `"standard"` | `standard`, `long_legged`, `dragonfly`, `gravestone` |
| `body_threshold` | float | 0.1 | Maximum body/range ratio for doji detection (0.01~0.3) |

**Required data**: open, high, low, close, date, symbol, exchange

```json
{
  "id": "doji", "type": "ConditionNode", "plugin": "Doji",
  "fields": {"doji_type": "standard", "body_threshold": 0.1}
}
```

**symbol_results output**: `pattern_detected`, `doji_type`, `body_ratio`, `confidence`
**tags**: candlestick, pattern, doji, reversal, indecision

---

#### 29. MorningEveningStar

A 3-candle reversal pattern. Morning Star (large bearish + small body + large bullish = bullish reversal). Evening Star (large bullish + small body + large bearish = bearish reversal).

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `pattern` | string | `"morning_star"` | `morning_star`: bullish reversal, `evening_star`: bearish reversal |
| `star_body_max` | float | 0.3 | Maximum body ratio for the middle (star) candle (0.05~0.5) |
| `confirmation_ratio` | float | 0.5 | 3rd candle must recover N% or more of the 1st candle's body (0.2~1.0) |

**Required data**: open, high, low, close, date, symbol, exchange
**Minimum data**: 3 days

```json
{
  "id": "mes", "type": "ConditionNode", "plugin": "MorningEveningStar",
  "fields": {"pattern": "morning_star", "star_body_max": 0.3, "confirmation_ratio": 0.5}
}
```

**symbol_results output**: `pattern_detected`, `confidence`, `pattern_type`
**tags**: candlestick, pattern, reversal, morning_star, evening_star

---

## POSITION Plugins (15)

> This section documents 13 core plugins in detail. For the full list of 15 POSITION plugins including DynamicStopLoss and MaxPositionLimit, see the [Plugin Quick Reference](../11-appendix/02-plugin-quick-reference.md).

POSITION plugins are used for position management, risk management, and portfolio allocation. There are two types based on input data:

- **positions-based**: `positions` (held positions info) input -- StopLoss, ProfitTarget, DrawdownProtection, RollManagement, etc.
- **data-based**: `data` (OHLCV time series) input -- KellyCriterion, RiskParity, VarCvarMonitor, etc.

### 30. StopLoss

Generates a sell signal when a held position's loss exceeds the threshold.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `stop_percent` | float | -3.0 | Stop loss percentage (%) |

**Input**: `positions` (output from RealAccountNode or AccountNode)

```json
{
  "id": "sl", "type": "ConditionNode", "plugin": "StopLoss",
  "positions": "{{ nodes.real_account.positions }}",
  "fields": {"stop_percent": -3.0}
}
```

**symbol_results output**: `pnl_rate`, `current_price`, `stop_percent`, `triggered`
**tags**: exit, risk, realtime

---

### 31. ProfitTarget

Generates a sell signal when a held position reaches the target return.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `target_percent` | float | 5.0 | Target return (%) |

**Input**: `positions` (output from RealAccountNode or AccountNode)

```json
{
  "id": "pt", "type": "ConditionNode", "plugin": "ProfitTarget",
  "positions": "{{ nodes.real_account.positions }}",
  "fields": {"target_percent": 5.0}
}
```

**symbol_results output**: `pnl_rate`, `current_price`, `target_percent`, `reached`
**tags**: exit, profit, realtime

---

### 32. TrailingStop

Two modes:
1. **Order price tracking modification**: Automatically modifies unfilled order prices to match the current price
2. **Ratio-based scaling**: HWM drawdown-based sell signal when integrated with risk_tracker

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `price_gap_percent` | float | 0.5 | Gap from current price (%, order modification mode) |
| `max_modifications` | int | 5 | Maximum number of modifications |
| `trail_ratio` | float | 0.3 | Trailing ratio (return x ratio = allowed drawdown) |

**Scaling example** (trail_ratio = 0.3):
- 5% profit -> allowed drawdown 1.5% (5% x 0.3)
- 10% profit -> allowed drawdown 3.0%
- 20% profit -> allowed drawdown 6.0%

**risk_features**: `hwm` (enables WorkflowRiskTracker HWM tracking)

```json
{
  "id": "ts", "type": "ConditionNode", "plugin": "TrailingStop",
  "fields": {"trail_ratio": 0.3}
}
```

**tags**: modify, tracking, trailing_stop

---

### 33. PartialTakeProfit

Reduces risk while securing profits by selling in multiple stages. Sells a specified proportion when each stage's return threshold is reached.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `levels` | string (JSON) | `[{"pnl_pct":5,"sell_pct":50},{"pnl_pct":10,"sell_pct":30},{"pnl_pct":20,"sell_pct":20}]` | Partial take-profit stages array |

Each item in the `levels` array:
- `pnl_pct`: Trigger return (%)
- `sell_pct`: Sell ratio relative to original quantity (%)

**Input**: `positions` (output from RealAccountNode)
**risk_features**: `state` (for tracking completed stages)

```json
{
  "id": "ptp", "type": "ConditionNode", "plugin": "PartialTakeProfit",
  "positions": "{{ nodes.real_account.positions }}",
  "fields": {"levels": "[{\"pnl_pct\": 5, \"sell_pct\": 50}, {\"pnl_pct\": 10, \"sell_pct\": 30}]"}
}
```

**symbol_results output**: `pnl_rate`, `qty`, `sell_quantity`, `sell_pct`, `level_index`, `remaining_levels`, `action`
**tags**: exit, profit, partial, scaling

---

### 34. TimeBasedExit

Automatically generates an exit signal when the holding period exceeds the configured number of days. Entry date is tracked automatically.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_hold_days` | int | 5 | Maximum holding days (1~365) |
| `warn_days` | int | 0 | Warning start days before expiry (0 = disabled) |

**Input**: `positions` (output from RealAccountNode)
**risk_features**: `state` (for tracking entry dates)

```json
{
  "id": "tbe", "type": "ConditionNode", "plugin": "TimeBasedExit",
  "positions": "{{ nodes.real_account.positions }}",
  "fields": {"max_hold_days": 5, "warn_days": 2}
}
```

**symbol_results output**: `entry_date`, `hold_days`, `max_hold_days`, `warn`, `action` (`hold`/`warn`/`exit`)
**tags**: exit, time, holding_period

---

### 35. DrawdownProtection

Generates an exit signal when the portfolio/per-symbol drawdown exceeds the configured threshold. Tracks the current decline from HWM (high water mark).

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_drawdown_pct` | float | -10.0 | Maximum allowed drawdown (%, negative value) |
| `action` | string | exit_all | Action on drawdown breach (exit_all/reduce/alert_only) |
| `recovery_threshold` | float | 5.0 | Recovery percentage to resume trading (%) |

**Input**: `positions` (output from AccountNode/RealAccountNode)
**risk_features**: `hwm`, `events` (WorkflowRiskTracker HWM tracking + event logging)

```json
{
  "id": "dd", "type": "ConditionNode", "plugin": "DrawdownProtection",
  "positions": "{{ nodes.real_account.positions }}",
  "fields": {"max_drawdown_pct": -10.0, "action": "exit_all"}
}
```

**symbol_results output**: `drawdown_pct`, `high_water_mark`, `current_value`, `action`
**tags**: drawdown, risk, protection, portfolio

---

### 36. VolatilityPositionSizing

Allocates position size inversely proportional to each symbol's realized volatility. Higher volatility symbols get smaller positions; lower volatility symbols get larger positions.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `target_volatility` | float | 15.0 | Target annualized volatility (%) |
| `vol_lookback` | int | 20 | Volatility calculation period |
| `max_position_pct` | float | 20.0 | Maximum position weight (%) |
| `min_position_pct` | float | 2.0 | Minimum position weight (%) |
| `scaling_method` | string | inverse_vol | Sizing method (inverse_vol/target_vol) |

**Input**: `data` (OHLCV time series, using items)

```json
{
  "id": "volsize", "type": "ConditionNode", "plugin": "VolatilityPositionSizing",
  "items": {"from": "{{ nodes.historical.value.time_series }}", "extract": {"symbol": "{{ nodes.historical.value.symbol }}", "exchange": "{{ nodes.historical.value.exchange }}", "date": "{{ row.date }}", "close": "{{ row.close }}"}},
  "fields": {"target_volatility": 15.0, "vol_lookback": 20}
}
```

**symbol_results output**: `volatility`, `position_pct`, `scaling_factor`
**tags**: position_sizing, volatility, risk_management

---

### 37. RollManagement (Futures Rollover Management)

Generates rollover signals (front month to back month contract switch) as futures approach their expiration date.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `days_before_expiry` | int | 5 | Business days before expiry to start rolling |
| `roll_strategy` | string | calendar | Roll timing strategy (calendar/volume) |

**Input**: `positions` (futures position info)
**risk_features**: `state` (roll status tracking)

```json
{
  "id": "roll", "type": "ConditionNode", "plugin": "RollManagement",
  "positions": "{{ nodes.futures_account.positions }}",
  "fields": {"days_before_expiry": 5, "roll_strategy": "calendar"}
}
```

**symbol_results output**: `days_to_expiry`, `roll_signal`, `next_contract`
**tags**: futures, roll, expiry, contract_management

---

### 38. KellyCriterion

Calculates optimal position size using the Kelly formula from historical return distributions. In practice, fractional Kelly (typically 25%) is applied.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `lookback` | int | 60 | Return calculation period |
| `kelly_fraction` | float | 0.25 | Fraction of full Kelly to apply (0.1~1.0) |
| `min_position_pct` | float | 2.0 | Minimum position weight (%) |
| `max_position_pct` | float | 25.0 | Maximum position weight (%) |
| `return_period` | string | daily | Return period (daily/weekly) |

**Input**: `data` (OHLCV time series, using items)
**risk_features**: `state` (optional)

Kelly formula: `K% = (win_rate x avg_win/avg_loss - (1-win_rate)) / (avg_win/avg_loss)`

```json
{
  "id": "kelly", "type": "ConditionNode", "plugin": "KellyCriterion",
  "items": {"from": "{{ nodes.historical.value.time_series }}", "extract": {"symbol": "{{ nodes.historical.value.symbol }}", "exchange": "{{ nodes.historical.value.exchange }}", "date": "{{ row.date }}", "close": "{{ row.close }}"}},
  "fields": {"lookback": 60, "kelly_fraction": 0.25}
}
```

**symbol_results output**: `kelly_pct`, `fractional_kelly_pct`, `position_pct`, `win_rate`, `avg_win`, `avg_loss`, `payoff_ratio`, `expected_value`
**tags**: kelly, position_sizing, risk_management, optimal

---

### 39. RiskParity

Allocates weights so that each asset contributes equally to the overall portfolio risk. Assets with lower volatility receive higher weights.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `lookback` | int | 60 | Volatility calculation period |
| `target_volatility` | float | 15.0 | Target annualized portfolio volatility (%) |
| `method` | string | inverse_vol | Allocation method (inverse_vol/equal_risk_contribution) |
| `min_weight_pct` | float | 2.0 | Minimum allocation weight (%) |
| `max_weight_pct` | float | 40.0 | Maximum allocation weight (%) |

**Input**: `data` (OHLCV time series - multiple symbols)

```json
{
  "id": "rp", "type": "ConditionNode", "plugin": "RiskParity",
  "items": {"from": "{{ nodes.historical.value.time_series }}", "extract": {"symbol": "{{ nodes.historical.value.symbol }}", "exchange": "{{ nodes.historical.value.exchange }}", "date": "{{ row.date }}", "close": "{{ row.close }}"}},
  "fields": {"lookback": 60, "method": "inverse_vol", "target_volatility": 15.0}
}
```

**symbol_results output**: `volatility`, `weight_pct`, `risk_contribution_pct`
**tags**: risk_parity, portfolio, allocation, volatility

---

### 40. VarCvarMonitor (VaR/CVaR Monitor)

Calculates Value at Risk (VaR) and Conditional VaR (Expected Shortfall), and warns/responds when risk limits are exceeded.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `lookback` | int | 60 | VaR calculation period |
| `confidence_level` | float | 95.0 | Confidence level (90.0/95.0/99.0) |
| `var_method` | string | historical | VaR calculation method (historical/parametric) |
| `time_horizon` | int | 1 | VaR time horizon (business days, 1~10) |
| `alert_threshold_pct` | float | 5.0 | Alert threshold VaR (%) |
| `action` | string | alert_only | Action on limit breach (alert_only/reduce_position/exit_all) |

**Input**: `data` (OHLCV time series), optional `positions`
**risk_features**: `events` (risk event logging)

```json
{
  "id": "var", "type": "ConditionNode", "plugin": "VarCvarMonitor",
  "items": {"from": "{{ nodes.historical.value.time_series }}", "extract": {"symbol": "{{ nodes.historical.value.symbol }}", "exchange": "{{ nodes.historical.value.exchange }}", "date": "{{ row.date }}", "close": "{{ row.close }}"}},
  "fields": {"lookback": 60, "confidence_level": 95.0, "var_method": "historical", "action": "alert_only"}
}
```

**symbol_results output**: `var_pct`, `cvar_pct`, `var_dollar` (when positions available), `breached`
**tags**: var, cvar, risk, monitoring, expected_shortfall

---

### 41. CorrelationGuard

Monitors correlations between symbols in a portfolio and warns when entering a high-correlation regime that diminishes diversification benefits. Uses hysteresis to prevent frequent regime switches.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `lookback` | int | 60 | Correlation calculation period |
| `correlation_threshold` | float | 0.8 | High-correlation regime entry threshold |
| `recovery_threshold` | float | 0.6 | Normal regime recovery threshold |
| `action` | string | reduce_pct | Action during high correlation (reduce_pct/alert_only/exit_highest) |
| `reduce_by_pct` | float | 30.0 | Position reduction ratio (%) |
| `method` | string | pearson | Correlation method (pearson/spearman) |

**Input**: `data` (OHLCV time series - multiple symbols)
**risk_features**: `state`, `events` (regime state tracking + event logging)

```json
{
  "id": "cg", "type": "ConditionNode", "plugin": "CorrelationGuard",
  "items": {"from": "{{ nodes.historical.value.time_series }}", "extract": {"symbol": "{{ nodes.historical.value.symbol }}", "exchange": "{{ nodes.historical.value.exchange }}", "date": "{{ row.date }}", "close": "{{ row.close }}"}},
  "fields": {"lookback": 60, "correlation_threshold": 0.8, "method": "pearson"}
}
```

**symbol_results output**: `max_correlation`, `correlated_with`, `regime`, `action_taken`
**pair_correlations output**: `symbol_a`, `symbol_b`, `correlation`
**tags**: correlation, guard, regime, risk_management, diversification

---

### 42. BetaHedge

Monitors portfolio beta and recommends hedging strategies when market exposure is excessive relative to the target beta.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `lookback` | int | 120 | Beta calculation period |
| `market_symbol` | string | SPY | Market benchmark symbol (must be included in data) |
| `target_beta` | float | 1.0 | Target portfolio beta |
| `beta_tolerance` | float | 0.2 | Allowed beta deviation |
| `hedge_method` | string | long_inverse_etf | Hedging strategy (long_inverse_etf/reduce_high_beta) |
| `inverse_etf_symbol` | string | SH | Inverse ETF symbol |
| `max_hedge_pct` | float | 30.0 | Maximum hedge weight (%) |

**Input**: `data` (OHLCV time series - multiple symbols including benchmark), optional `positions`
**risk_features**: `state`, `events` (beta history tracking + event logging)

```json
{
  "id": "bh", "type": "ConditionNode", "plugin": "BetaHedge",
  "items": {"from": "{{ nodes.historical.value.time_series }}", "extract": {"symbol": "{{ nodes.historical.value.symbol }}", "exchange": "{{ nodes.historical.value.exchange }}", "date": "{{ row.date }}", "close": "{{ row.close }}"}},
  "fields": {"lookback": 120, "market_symbol": "SPY", "target_beta": 1.0}
}
```

**symbol_results output**: `beta`, `weight` (when positions available), `beta_contribution`
**hedge_recommendation output**: `action`, `inverse_etf`, `suggested_allocation_pct` (when hedging is needed)
**tags**: beta, hedge, market_neutral, risk_management

---

## Plugin Selection Guide

### By Entry Strategy

| Strategy | Recommended Plugins | Description |
|----------|-------------------|-------------|
| Oversold buying | RSI, Stochastic, MeanReversion, WilliamsR, CCI | Expecting a bounce after price decline |
| Trend following | MACD, MovingAverageCross, DualMomentum, IchimokuCloud, ParabolicSAR, Supertrend, TRIX | Enter after confirming an uptrend |
| Breakout trading | ATR, PriceChannel, BreakoutRetest, KeltnerChannel | Enter on key level breakouts |
| Volume confirmation | VolumeSpike, OBV, VWAP, CMF | Confirm volume/money flow |
| Trend strength | ADX | Confirm trend presence before combining with other strategies |
| Support/Resistance | BollingerBands, GoldenRatio, PivotPoint | Utilize band/Fibonacci/pivot levels |
| Candlestick reversal | Engulfing, HammerShootingStar, Doji, MorningEveningStar, ThreeLineStrike | Reversal signals based on candle patterns |

### By Exit Strategy

| Strategy | Recommended Plugins | Description |
|----------|-------------------|-------------|
| Fixed stop loss | StopLoss | Sell when loss exceeds threshold |
| Fixed take profit | ProfitTarget | Sell when target return is reached |
| Trailing stop | TrailingStop | Sell on decline after maximizing profit |
| Partial take profit | PartialTakeProfit | Stage-based profit taking (risk management) |
| Time-based exit | TimeBasedExit | Auto-exit when holding period expires |

### By Quantitative Risk Management

| Strategy | Recommended Plugins | Description |
|----------|-------------------|-------------|
| Optimal sizing | KellyCriterion | Optimal position size via Kelly formula |
| Risk parity | RiskParity | Equal risk contribution-based allocation |
| VaR monitoring | VarCvarMonitor | VaR/CVaR calculation and limit monitoring |
| Correlation monitoring | CorrelationGuard | High-correlation regime detection and diversification protection |
| Beta hedging | BetaHedge | Market beta exposure management and hedge recommendation |
| Drawdown protection | DrawdownProtection | Drawdown monitoring vs. HWM |
| Volatility sizing | VolatilityPositionSizing | Inverse-volatility position allocation |

### Compound Conditions (Using LogicNode)

```json
{
  "nodes": [
    {"id": "rsi", "type": "ConditionNode", "plugin": "RSI",
     "fields": {"threshold": 30, "direction": "below"}},
    {"id": "vol", "type": "ConditionNode", "plugin": "VolumeSpike",
     "fields": {"multiplier": 1.5}},
    {"id": "logic", "type": "LogicNode", "operator": "all"}
  ],
  "edges": [
    {"from": "rsi", "to": "logic"},
    {"from": "vol", "to": "logic"}
  ]
}
```

Buy signal when RSI is oversold **AND** volume spikes.

## field_mapping (Optional)

Specify field mapping when using data with different field names than the defaults:

```json
{
  "field_mapping": {
    "close_field": "close",
    "open_field": "open",
    "high_field": "high",
    "low_field": "low",
    "volume_field": "volume",
    "date_field": "date",
    "symbol_field": "symbol",
    "exchange_field": "exchange"
  }
}
```

In most cases, the defaults are used, so specifying `field_mapping` is unnecessary.
