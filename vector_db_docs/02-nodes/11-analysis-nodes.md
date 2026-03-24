---
category: node_reference
tags: [analysis, backtest, benchmark]
priority: medium
---

# Analysis Nodes: Backtest, Benchmark

## BacktestEngineNode

Validates strategies with historical data. Simulates "How much would this strategy have profited in the past?"

```json
{
  "id": "backtest",
  "type": "BacktestEngineNode",
  "initial_capital": 10000,
  "commission_rate": 0.001,
  "position_sizing": "kelly",
  "exit_rules": {
    "stop_loss_percent": 5,
    "take_profit_percent": 15
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `initial_capital` | number | Initial investment capital (USD) |
| `commission_rate` | number | Commission rate (0.001 = 0.1%) |
| `position_sizing` | string | Position sizing: `fixed`, `percent`, `kelly`, `atr` |
| `exit_rules` | object | Automatic exit rules |

**exit_rules:**

| Field | Description |
|-------|-------------|
| `stop_loss_percent` | Stop loss ratio (%) - Auto-sell when loss exceeds this |
| `take_profit_percent` | Take profit ratio (%) - Auto-sell when profit exceeds this |

**Output:**

- `equity_curve` - Equity curve (daily asset trend)
- `summary` - Performance summary

```json
{
  "total_return": 25.3,
  "mdd": -8.2,
  "win_rate": 62.5,
  "sharpe_ratio": 1.85,
  "total_trades": 48
}
```

**Performance Metric Interpretation:**
- `sharpe_ratio` >= 1.0: Decent strategy, >= 2.0: Excellent strategy
- `mdd` <= -20%: May be risky
- `win_rate`: Win rate (60% or above is good)

## BenchmarkCompareNode

Compares multiple backtest results. Used for comparative analysis like "RSI strategy vs Buy & Hold".

```json
{
  "id": "compare",
  "type": "BenchmarkCompareNode",
  "strategies": [
    "{{ nodes.backtestRSI }}",
    "{{ nodes.backtestSPY }}"
  ],
  "ranking_metric": "sharpe"
}
```

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `strategies` | array | O | BacktestEngineNode outputs |
| `ranking_metric` | string | - | Ranking criterion (default: `sharpe`) |

**ranking_metric Options:**

| Metric | Description | Good Value |
|--------|-------------|-----------|
| `sharpe` | Risk-adjusted return | Higher is better (>1.0) |
| `return` | Total return | Higher is better |
| `mdd` | Maximum drawdown | Closer to 0 is better |
| `calmar` | Return / MDD | Higher is better |

**Output:**
- `combined_curve` - Combined equity curve (for comparison charts)
- `comparison_metrics` - Per-strategy comparison metrics
- `ranking` - Rankings

**Usage Pattern:**
```
BacktestEngineNode (RSI strategy) ──┐
                                    ├──▶ BenchmarkCompareNode ──▶ LineChartNode
BacktestEngineNode (Buy & Hold) ───┘
```

**Buy & Hold Benchmark**: Feeding only data without condition signals to BacktestEngineNode automatically applies a Buy & Hold strategy. Compare whether your strategy outperforms simple holding.
