---
category: node_reference
tags: [condition, logic, plugin, signal]
priority: critical
---

# Condition Nodes: ConditionNode, LogicNode

Core nodes for evaluating buy/sell conditions.

## ConditionNode

Evaluates trading conditions based on plugins. Choose from 52 technical analysis plugins (RSI, MACD, Bollinger Bands, Ichimoku, VWAP, Z-Score, Squeeze Momentum, Pair Trading, Support/Resistance Levels, Level Touch, etc.) and 15 position management plugins.

```json
{
  "id": "rsi",
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

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `plugin` | string | O | Plugin ID (RSI, MACD, etc.) |
| `items` | object | O | Data input (`from`: iteration array, `extract`: field mapping) |
| `fields` | object | - | Plugin-specific parameters |
| `positions` | expression | Conditional | Position data (required for take-profit/stop-loss plugins) |

**Required Data by Plugin Type:**

| Plugin Type | Required Data | Node to Connect | Example Plugins |
|-------------|--------------|-----------------|-----------------|
| Time-series based | Historical OHLCV data | HistoricalDataNode | RSI, MACD, BollingerBands, VolumeSpike |
| Position based | Held position info | AccountNode.positions | ProfitTarget, StopLoss |

**Output**: `result`

```json
{
  "passed": true,
  "passed_symbols": [
    {"symbol": "AAPL", "exchange": "NASDAQ", "rsi": 28.5}
  ],
  "analysis": [
    {"symbol": "AAPL", "rsi": 28.5, "signal": "oversold"},
    {"symbol": "NVDA", "rsi": 55.2, "signal": "neutral"}
  ]
}
```

- `passed`: `true` if at least one symbol passes the condition
- `passed_symbols`: Only symbols that passed the condition
- `analysis`: Analysis results for all symbols

## LogicNode

Logically combines multiple conditions. Creates compound conditions like "RSI AND MACD", "RSI OR Bollinger".

```json
{
  "id": "logic",
  "type": "LogicNode",
  "operator": "all",
  "conditions": [
    {
      "is_condition_met": "{{ nodes.rsi.result }}",
      "passed_symbols": "{{ nodes.rsi.result.passed_symbols }}"
    },
    {
      "is_condition_met": "{{ nodes.macd.result }}",
      "passed_symbols": "{{ nodes.macd.result.passed_symbols }}"
    }
  ]
}
```

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `operator` | string | O | Logical operator |
| `threshold` | number | Conditional | Threshold value (for at_least, weighted, etc.) |
| `conditions` | array | O | Condition list |

**conditions Items:**

| Field | Description |
|-------|-------------|
| `is_condition_met` | Binding to ConditionNode's result |
| `passed_symbols` | Binding to ConditionNode's passed_symbols |
| `weight` | Weight (used with weighted operator, 0~1) |

**Operators:**

| Operator | Meaning | Example |
|----------|---------|---------|
| `all` | All conditions met (AND) | RSI oversold AND MACD golden cross |
| `any` | One or more met (OR) | RSI oversold OR Bollinger lower band break |
| `not` | No conditions met | Symbols not RSI overbought |
| `xor` | Exactly one met | Only one of two signals |
| `at_least` | N or more met | 2+ of 3 conditions (threshold: 2) |
| `at_most` | N or fewer met | At most 1 only |
| `exactly` | Exactly N met | Exactly 2 |
| `weighted` | Weighted sum >= threshold | RSI 40% + MACD 35% + BB 25% |

**weighted Example (Scoring):**

```json
{
  "id": "logic",
  "type": "LogicNode",
  "operator": "weighted",
  "threshold": 0.6,
  "conditions": [
    {"is_condition_met": "{{ nodes.rsi.result }}", "passed_symbols": "{{ nodes.rsi.result.passed_symbols }}", "weight": 0.4},
    {"is_condition_met": "{{ nodes.macd.result }}", "passed_symbols": "{{ nodes.macd.result.passed_symbols }}", "weight": 0.35},
    {"is_condition_met": "{{ nodes.bb.result }}", "passed_symbols": "{{ nodes.bb.result.passed_symbols }}", "weight": 0.25}
  ]
}
```

RSI(40%) + MACD(35%) = 75% >= 60%(threshold) triggers buy signal.

**Typical Pattern:**
```
HistoricalDataNode → ConditionNode (RSI) ──┐
                   → ConditionNode (MACD) ──├──▶ LogicNode (all) ──▶ NewOrderNode
                   → ConditionNode (BB) ────┘
```
