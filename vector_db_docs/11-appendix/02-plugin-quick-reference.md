---
category: appendix
tags: [reference, plugin, quick, all, 67_plugins, condition, RSI, MACD, BollingerBands, Stochastic, MovingAverageCross, ADX, ATR, OBV, PriceChannel, VolumeSpike, DualMomentum, MeanReversion, BreakoutRetest, GoldenRatio, PivotPoint, ThreeLineStrike, IchimokuCloud, VWAP, ParabolicSAR, WilliamsR, CCI, Supertrend, KeltnerChannel, TRIX, CMF, Engulfing, HammerShootingStar, Doji, MorningEveningStar, RegimeDetection, RelativeStrength, MultiTimeframeConfirmation, CorrelationAnalysis, ContangoBackwardation, CalendarSpread, ZScore, SqueezeMomentum, MomentumRank, MarketInternals, PairTrading, SupportResistanceLevels, LevelTouch, ConnorsRSI, MFI, CoppockCurve, TimeSeriesMomentum, ElderRay, TurtleBreakout, VolatilityBreakout, SeasonalFilter, TacticalAssetAllocation, MagicFormula, StopLoss, ProfitTarget, TrailingStop, PartialTakeProfit, TimeBasedExit, DrawdownProtection, VolatilityPositionSizing, RollManagement, KellyCriterion, RiskParity, VarCvarMonitor, CorrelationGuard, BetaHedge, DynamicStopLoss, MaxPositionLimit]
priority: high
---

# 67 Plugins Quick Reference

## Technical Analysis Plugins (52)

All 52 technical analysis plugins are referenced via the `plugin` field of `ConditionNode`. The `items` field specifies the data source (`from`) and extraction fields (`extract`), and the `fields` parameter passes plugin-specific settings.

### Basic Pattern

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

### Momentum / Oscillators (12)

| Plugin | Description | Required Data Fields | Key Settings |
|--------|-------------|----------------------|--------------|
| `RSI` | Relative Strength Index - overbought/oversold | symbol, exchange, date, close | `period` (14), `threshold` (30), `direction` (below/above) |
| `Stochastic` | Stochastic Oscillator | symbol, exchange, date, high, low, close | `k_period` (14), `d_period` (3), `threshold` (20), `direction` (oversold/overbought) |
| `DualMomentum` | Absolute + relative momentum | symbol, exchange, date, close | `lookback_period` (252), `absolute_threshold` (0.0), `use_relative` (true) |
| `MeanReversion` | Mean reversion strategy | symbol, exchange, date, close | `ma_period` (20), `deviation` (2.0), `direction` (oversold/overbought) |
| `ZScore` | Standard deviation normalized overbought/oversold | symbol, exchange, date, close | `lookback` (20), `entry_threshold` (2.0), `exit_threshold` (0.5), `direction` (below/above) |
| `PairTrading` | Pair spread Z-Score trading signal | symbol, exchange, date, close | `symbol_a`, `symbol_b`, `lookback` (60), `entry_z` (2.0), `spread_method` (ratio/log_ratio/difference) |
| `WilliamsR` | Williams %R Oscillator | symbol, exchange, date, high, low, close | `period` (14), `threshold` (-80), `direction` (oversold/overbought) |
| `CCI` | Commodity Channel Index | symbol, exchange, date, high, low, close | `period` (20), `threshold` (100), `direction` (oversold/overbought) |
| `ConnorsRSI` | RSI + Streak RSI + Percentile Rank composite | symbol, exchange, date, close | `rsi_period` (3), `streak_period` (2), `pct_rank_period` (100), `threshold` (10), `direction` (below/above) |
| `MFI` | Money Flow Index (volume-weighted RSI) | symbol, exchange, date, close, high, low, volume | `period` (14), `overbought` (80), `oversold` (20), `direction` (below/above) |
| `CoppockCurve` | Long-term bottom detection (ROC + WMA) | symbol, exchange, date, close | `long_roc` (14), `short_roc` (11), `wma_period` (10), `signal_mode` (zero_cross/direction) |
| `TimeSeriesMomentum` | Past N-day return sign momentum (TSMOM) | symbol, exchange, date, close | `lookback_days` (252), `signal_mode` (binary/scaled), `volatility_adjust` (true), `vol_target` (0.15) |

### Trend / Moving Averages (8)

| Plugin | Description | Required Data Fields | Key Settings |
|--------|-------------|----------------------|--------------|
| `MACD` | Moving Average Convergence Divergence | symbol, exchange, date, close | `fast_period` (12), `slow_period` (26), `signal_period` (9), `signal_type` (bullish_cross/bearish_cross) |
| `MovingAverageCross` | Golden/Dead Cross | symbol, exchange, date, close | `short_period` (5), `long_period` (20), `cross_type` (golden/dead) |
| `ADX` | Average Directional Index - trend strength | symbol, exchange, date, high, low, close | `period` (14), `threshold` (25), `direction` (strong_trend/uptrend/downtrend) |
| `IchimokuCloud` | Ichimoku Cloud - comprehensive trend | symbol, exchange, date, close, high, low | `tenkan_period` (9), `kijun_period` (26), `senkou_b_period` (52), `signal_type` |
| `ParabolicSAR` | Parabolic SAR - trend reversal | symbol, exchange, date, close, high, low | `af_start` (0.02), `af_step` (0.02), `af_max` (0.20), `signal_type` |
| `Supertrend` | ATR-based trend following | symbol, exchange, date, close, high, low | `period` (10), `multiplier` (3.0), `signal_type` (bullish/bearish/uptrend/downtrend) |
| `TRIX` | Triple Exponential Moving Average | symbol, exchange, date, close | `period` (15), `signal_period` (9), `signal_type` (bullish_cross/bearish_cross/above_zero/below_zero) |
| `ElderRay` | Elder Ray (Bull/Bear Power + EMA) | symbol, exchange, date, close, high, low | `ema_period` (13), `signal_mode` (conservative/aggressive) |

### Volatility / Channels (7)

| Plugin | Description | Required Data Fields | Key Settings |
|--------|-------------|----------------------|--------------|
| `BollingerBands` | Bollinger Bands | symbol, exchange, date, close | `period` (20), `std_dev` (2.0), `position` (below_lower/above_upper) |
| `ATR` | Average True Range - volatility | symbol, exchange, date, high, low, close | `period` (14), `multiplier` (2.0), `direction` (breakout_up/breakout_down) |
| `PriceChannel` | Donchian Channel - breakout detection | symbol, exchange, date, high, low, close | `period` (20), `direction` (breakout_high/breakout_low) |
| `KeltnerChannel` | Keltner Channel - EMA+ATR | symbol, exchange, date, close, high, low | `ema_period` (20), `atr_period` (10), `multiplier` (1.5), `direction` (above_upper/below_lower/squeeze) |
| `SqueezeMomentum` | BB+KC Squeeze fire + momentum | symbol, exchange, date, close, high, low | `bb_period` (20), `kc_period` (20), `momentum_period` (12), `direction` (squeeze_fire_long/short/on/off) |
| `TurtleBreakout` | Turtle Donchian breakout (20/55-day) | symbol, exchange, date, close, high, low | `system` (system1/system2), `entry_period` (20), `exit_period` (10), `atr_period` (20), `stop_atr_multiple` |
| `VolatilityBreakout` | Larry Williams range breakout | symbol, exchange, date, open, close, high, low | `k_factor` (0.5), `atr_adaptive` (false), `direction` (long/short/both), `exit_mode` (close/next_open/trailing) |

### Volume Analysis (4)

| Plugin | Description | Required Data Fields | Key Settings |
|--------|-------------|----------------------|--------------|
| `VolumeSpike` | Volume spike detection | symbol, exchange, date, volume | `period` (20), `multiplier` (2.0) |
| `OBV` | On-Balance Volume | symbol, exchange, date, close, volume | `ma_period` (20), `direction` (bullish/bearish) |
| `VWAP` | Volume Weighted Average Price | symbol, exchange, date, close, volume | `direction` (above/below), `band_multiplier` (0.0) |
| `CMF` | Chaikin Money Flow | symbol, exchange, date, close, high, low, volume | `period` (20), `threshold` (0.05), `direction` (accumulation/distribution) |

### Price Levels / Patterns (5)

| Plugin | Description | Required Data Fields | Key Settings |
|--------|-------------|----------------------|--------------|
| `GoldenRatio` | Fibonacci Retracement | symbol, exchange, date, high, low, close | `lookback` (50), `level` ("0.618"), `direction` (support/resistance) |
| `PivotPoint` | Pivot Points | symbol, exchange, date, high, low, close | `pivot_type` (standard/fibonacci/camarilla), `direction` (support/resistance) |
| `BreakoutRetest` | Breakout retest pattern | symbol, exchange, date, high, low, close | `lookback` (20), `retest_threshold` (0.02), `direction` (bullish/bearish) |
| `SupportResistanceLevels` | Swing-based S/R level detection + clustering | symbol, exchange, date, open, high, low, close, volume | `lookback` (60), `swing_strength` (5), `cluster_tolerance` (0.015), `min_cluster_size` (2), `proximity_threshold` (0.02), `direction` (both/support/resistance) |
| `LevelTouch` | Level touch/breakout/role reversal detection | symbol, exchange, date, open, high, low, close, volume | `levels` (JSON/symbol_results), `touch_tolerance` (0.01), `breakout_threshold` (0.015), `confirm_bars` (2), `mode` (first_touch/role_reversal/cluster_bounce) |

### Candlestick Patterns (5)

| Plugin | Description | Required Data Fields | Key Settings |
|--------|-------------|----------------------|--------------|
| `ThreeLineStrike` | Three Line Strike - strong reversal | symbol, exchange, date, open, high, low, close | `pattern` (bullish/bearish), `min_body_pct` (0.3) |
| `Engulfing` | Engulfing - reversal pattern | symbol, exchange, date, open, high, low, close | `pattern` (bullish/bearish), `min_body_ratio` (0.5) |
| `HammerShootingStar` | Hammer/Shooting Star | symbol, exchange, date, open, high, low, close | `pattern` (hammer/shooting_star), `shadow_ratio` (2.0) |
| `Doji` | Doji - indecision | symbol, exchange, date, open, high, low, close | `doji_type` (standard/long_legged/dragonfly/gravestone), `body_threshold` (0.1) |
| `MorningEveningStar` | Morning/Evening Star - 3-candle reversal | symbol, exchange, date, open, high, low, close | `pattern` (morning_star/evening_star), `star_body_max` (0.3), `confirmation_ratio` (0.5) |

### Market Analysis (8)

| Plugin | Description | Required Data Fields | Key Settings |
|--------|-------------|----------------------|--------------|
| `RegimeDetection` | Market regime detection (bull/bear/sideways) | symbol, exchange, date, close, high, low | `ma_period` (20), `adx_period` (14), `adx_threshold` (25), `vol_lookback` (60) |
| `RelativeStrength` | Relative strength vs benchmark | symbol, exchange, date, close | `lookback` (60), `benchmark_symbol` ("SPY"), `rank_method` (raw/percentile/z_score), `threshold` (0.0) |
| `CorrelationAnalysis` | Inter-asset correlation analysis | symbol, exchange, date, close | `lookback` (60), `method` (pearson/spearman), `threshold` (0.7), `direction` (above/below) |
| `MomentumRank` | Universe momentum ranking selection | symbol, exchange, date, close | `lookback` (63), `top_n` (5), `selection` (top/bottom), `momentum_type` (simple/log/risk_adjusted) |
| `MarketInternals` | Market internal health (AD ratio, % above MA) | symbol, exchange, date, close, high, low | `metric` (advance_decline_ratio/above_ma_pct/composite), `threshold` (60), `direction` (above/below) |
| `SeasonalFilter` | Date-based seasonal pattern filter (Halloween effect) | symbol, exchange, date, close | `strategy` (halloween/custom), `buy_months`, `sell_months`, `hemisphere` (northern/southern) |
| `TacticalAssetAllocation` | SMA-based trend filter for asset allocation (Faber 2007) | symbol, exchange, date, close | `sma_period` (200), `signal_mode` (binary/scaled), `rebalance_check` (daily/monthly), `margin_pct` (0) |
| `MagicFormula` | Magic Formula ranking (quality + cheapness, multi-symbol) | symbol, exchange, per, roe (simplified) or ebit, enterprise_value, invested_capital (full) | `mode` (simplified/full), `top_n` (30), `min_market_cap` (0) |

### Multi-Timeframe (1)

| Plugin | Description | Required Data Fields | Key Settings |
|--------|-------------|----------------------|--------------|
| `MultiTimeframeConfirmation` | Multi-timeframe MA alignment | symbol, exchange, date, close | `short_period` (5), `medium_period` (20), `long_period` (60), `direction` (bullish/bearish), `require_all` (true) |

### Futures-Only (2)

| Plugin | Description | Input | Key Settings |
|--------|-------------|-------|--------------|
| `ContangoBackwardation` | Contango/backwardation detection | positions (with market_code) | `structure` (contango/backwardation), `spread_threshold` (0.5) |
| `CalendarSpread` | Calendar spread Z-score | positions (with market_code) | `lookback` (20), `z_threshold` (2.0), `strategy` (mean_revert/momentum) |

## Position Management Plugins (15)

Position management plugins are used with position data in `ConditionNode`.

| Plugin | Description | Key Settings | risk_features |
|--------|-------------|--------------|---------------|
| `StopLoss` | Automatic stop-loss trigger | `stop_percent` (-3.0) | - |
| `ProfitTarget` | Profit-taking trigger | `target_percent` (5.0) | - |
| `TrailingStop` | Trailing stop (HWM-based) | `trail_ratio` (0.3), `price_gap_percent` (0.5) | `hwm` |
| `PartialTakeProfit` | Staged partial profit-taking | `levels` (JSON array: pnl_pct, sell_pct) | `state` |
| `TimeBasedExit` | Time-based automatic exit | `max_hold_days` (5), `warn_days` (0) | `state` |
| `DrawdownProtection` | Drawdown protection (HWM-linked) | `max_drawdown_pct` (10.0), `action` (exit_all/reduce_half/stop_new_orders) | `hwm`, `events` |
| `VolatilityPositionSizing` | Volatility-based position sizing | `vol_lookback` (20), `target_volatility` (15.0), `scaling_method` (inverse_vol/vol_target/equal_risk) | - |
| `RollManagement` | Futures rollover management | `days_before_expiry` (5) | `state` |
| `DynamicStopLoss` | ATR-based dynamic stop-loss | `atr_period` (14), `atr_multiplier` (2.0), `trailing` (false) | - |
| `MaxPositionLimit` | Position count/weight/total value limits | `max_positions` (10), `max_single_weight_pct` (20), `action` (warn/block_new/exit_excess) | - |
| `KellyCriterion` | Kelly Criterion position sizing | `lookback` (60), `kelly_fraction` (0.25), `min_position_pct` (2.0), `max_position_pct` (25.0) | `state` |
| `RiskParity` | Risk parity allocation | `lookback` (60), `target_volatility` (15.0), `method` (inverse_vol/equal_risk_contribution) | - |
| `VarCvarMonitor` | VaR/CVaR monitoring | `lookback` (60), `confidence_level` (95.0), `var_method` (historical/parametric), `alert_threshold_pct` (5.0) | `events` |
| `CorrelationGuard` | Correlation guard (regime monitoring) | `lookback` (60), `correlation_threshold` (0.8), `recovery_threshold` (0.6), `method` (pearson/spearman) | `state`, `events` |
| `BetaHedge` | Beta hedge (portfolio beta management) | `lookback` (120), `market_symbol` ("SPY"), `target_beta` (1.0), `hedge_method` (long_inverse_etf/reduce_high_beta) | `state`, `events` |

### PartialTakeProfit Example

```json
{
    "id": "ptp",
    "type": "ConditionNode",
    "plugin": "PartialTakeProfit",
    "positions": "{{ nodes.real_account.positions }}",
    "fields": {
        "levels": "[{\"pnl_pct\": 5, \"sell_pct\": 50}, {\"pnl_pct\": 10, \"sell_pct\": 30}, {\"pnl_pct\": 20, \"sell_pct\": 20}]"
    }
}
```

Sells 50% when profit reaches 5%, 30% at 10%, and the remaining 20% at 20%. Tracks completed stages with `risk_features: state`.

### TimeBasedExit Example

```json
{
    "id": "tbe",
    "type": "ConditionNode",
    "plugin": "TimeBasedExit",
    "positions": "{{ nodes.real_account.positions }}",
    "fields": {
        "max_hold_days": 5,
        "warn_days": 2
    }
}
```

Signals exit when held for more than 5 days, with warnings starting from day 3 (5-2). Automatically tracks entry date with `risk_features: state`.

### TrailingStop Example

```json
{
    "id": "trailing",
    "type": "ConditionNode",
    "plugin": "TrailingStop",
    "positions": "{{ nodes.real_account.positions }}",
    "fields": {
        "trail_ratio": 0.3
    }
}
```

TrailingStop uses the WorkflowRiskTracker's `hwm` feature to track the decline rate from the high-water mark.

## Common Output Structure

Output of all technical analysis plugins:

```python
{
    "passed_symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}, ...],
    "failed_symbols": [{"symbol": "MSFT", "exchange": "NASDAQ"}, ...],
    "symbol_results": [
        {"symbol": "AAPL", "exchange": "NASDAQ", "rsi": 28.5, "signal": "oversold", ...}
    ],
    "values": [
        {"symbol": "AAPL", "exchange": "NASDAQ", "time_series": [...]}
    ],
    "result": true,
    "analysis": {...}
}
```

### items Field Structure

The `items` field of ConditionNode specifies input data:

```json
"items": {
    "from": "{{ nodes.historical.value.time_series }}",
    "extract": {
        "symbol": "{{ nodes.historical.value.symbol }}",
        "exchange": "{{ nodes.historical.value.exchange }}",
        "date": "{{ row.date }}",
        "close": "{{ row.close }}"
    }
}
```

| Field | Description |
|-------|-------------|
| `from` | Data array to iterate over (time series, etc.) |
| `extract` | Field mapping to extract from each row (`row`) |

Outputs are accessed via the `result` port: `{{ nodes.rsi_check.result.passed_symbols }}`, `{{ nodes.rsi_check.result.symbol_results }}`

## Plugin Selection Guide

| Desired Analysis | Recommended Plugin |
|------------------|-------------------|
| Overbought/oversold detection | `RSI`, `Stochastic`, `WilliamsR`, `CCI`, `ZScore`, `ConnorsRSI`, `MFI` |
| Trend reversal | `MACD`, `MovingAverageCross`, `IchimokuCloud`, `ParabolicSAR`, `ElderRay` |
| Trend strength measurement | `ADX`, `Supertrend` |
| Volatility analysis | `BollingerBands`, `ATR`, `KeltnerChannel`, `SqueezeMomentum` |
| Breakout strategy | `PriceChannel`, `BreakoutRetest`, `TurtleBreakout`, `VolatilityBreakout` |
| Volume analysis | `VolumeSpike`, `OBV`, `VWAP`, `CMF` |
| Momentum strategy | `DualMomentum`, `MeanReversion`, `TRIX`, `MomentumRank`, `TimeSeriesMomentum` |
| Long-term bottom detection | `CoppockCurve` |
| Fibonacci/Pivot | `GoldenRatio`, `PivotPoint` |
| Support/resistance levels | `SupportResistanceLevels`, `LevelTouch` |
| Candlestick patterns | `Engulfing`, `HammerShootingStar`, `Doji`, `MorningEveningStar`, `ThreeLineStrike` |
| Market state classification | `RegimeDetection`, `MarketInternals` |
| Seasonal/tactical | `SeasonalFilter`, `TacticalAssetAllocation` |
| Quality + value ranking | `MagicFormula` |
| Benchmark comparison | `RelativeStrength` |
| Inter-asset correlation | `CorrelationAnalysis`, `PairTrading` |
| Multi-timeframe | `MultiTimeframeConfirmation` |
| Futures contango/backwardation | `ContangoBackwardation` |
| Futures spread | `CalendarSpread` |
| Auto stop-loss/take-profit | `StopLoss`, `ProfitTarget`, `TrailingStop`, `DynamicStopLoss` |
| Partial take-profit/time-based exit | `PartialTakeProfit`, `TimeBasedExit` |
| Drawdown protection | `DrawdownProtection` |
| Position limit management | `MaxPositionLimit` |
| Volatility position sizing | `VolatilityPositionSizing` |
| Futures rollover | `RollManagement` |
| Compound conditions | `LogicNode` + multiple plugin combination |
