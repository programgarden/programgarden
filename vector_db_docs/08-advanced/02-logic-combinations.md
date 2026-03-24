---
category: advanced
tags: [logic, operator, all, any, not, xor, at_least, at_most, exactly, weighted, LogicNode, ConditionNode, condition_result]
priority: high
---

# Logic Combinations: 8 Operators

## Overview

`LogicNode` is a node that logically combines results from multiple `ConditionNode`s. It supports 8 operators and is used to construct composite trading conditions.

## LogicNode Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `operator` | enum | `"all"` | Logic operator |
| `threshold` | number | null | Threshold (for at_least, at_most, exactly, weighted) |
| `conditions` | array | [] | List of conditions |

### conditions Array Structure

```json
{
  "conditions": [
    {
      "is_condition_met": "{{ nodes.rsi_condition.result.passed }}",
      "passed_symbols": "{{ nodes.rsi_condition.result }}",
      "weight": 0.4
    },
    {
      "is_condition_met": "{{ nodes.macd_condition.result.passed }}",
      "passed_symbols": "{{ nodes.macd_condition.result }}",
      "weight": 0.6
    }
  ]
}
```

| Field | Required | Description |
|-------|:--------:|-------------|
| `is_condition_met` | O | Whether the condition is met (boolean expression) |
| `passed_symbols` | O | List of symbols that passed (symbol_list expression) |
| `weight` | - | Weight (for the weighted operator, 0.0~1.0) |

## 8 Operators

### 1. all (AND)

**All** conditions must be met to pass:

```json
{"operator": "all"}
```

- RSI oversold AND MACD golden cross → Both must be satisfied to buy

### 2. any (OR)

Pass if **one or more** conditions are met:

```json
{"operator": "any"}
```

- RSI oversold OR Bollinger Band lower breakout → Buy if even one is satisfied

### 3. not (NOT)

Inverts the condition. Pass if the condition is **not met**:

```json
{"operator": "not"}
```

- NOT RSI overbought → Proceed only when not overbought

### 4. xor (XOR)

Pass if exactly **one** condition is met:

```json
{"operator": "xor"}
```

- RSI oversold XOR MACD death cross → Only one satisfied (fails if both are met)

### 5. at_least (N or more)

Pass if **N or more** conditions are met:

```json
{"operator": "at_least", "threshold": 2}
```

- RSI, MACD, Bollinger Band: buy if 2 or more are satisfied

### 6. at_most (N or fewer)

Pass if **N or fewer** conditions are met:

```json
{"operator": "at_most", "threshold": 1}
```

- Only 1 or fewer out of 3 risk signals triggered → Safe

### 7. exactly (Exactly N)

Pass if **exactly N** conditions are met:

```json
{"operator": "exactly", "threshold": 2}
```

### 8. weighted (Weighted Sum)

Assigns a weight to each condition and passes if the summed score meets or exceeds the threshold:

```json
{
  "operator": "weighted",
  "threshold": 0.6,
  "conditions": [
    {"is_condition_met": "{{ nodes.rsi.result.passed }}", "passed_symbols": "{{ nodes.rsi.result }}", "weight": 0.4},
    {"is_condition_met": "{{ nodes.macd.result.passed }}", "passed_symbols": "{{ nodes.macd.result }}", "weight": 0.3},
    {"is_condition_met": "{{ nodes.bb.result.passed }}", "passed_symbols": "{{ nodes.bb.result }}", "weight": 0.3}
  ]
}
```

- RSI(0.4) + MACD(0.3) + BB(0.3) = 1.0
- Only RSI met → 0.4 (fail)
- RSI + MACD met → 0.7 (pass, >= 0.6)

## Output Ports

| Port | Type | Description |
|------|------|-------------|
| `result` | condition_result | Combined result |
| `passed_symbols` | symbol_list | List of symbols that passed all conditions |

## Workflow Example: RSI + MACD Composite Condition

```json
{
  "nodes": [
    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "cred"},
    {"id": "watchlist", "type": "WatchlistNode", "symbols": [
      {"symbol": "AAPL", "exchange": "NASDAQ"},
      {"symbol": "TSLA", "exchange": "NASDAQ"},
      {"symbol": "NVDA", "exchange": "NASDAQ"}
    ]},
    {"id": "historical", "type": "OverseasStockHistoricalDataNode",
     "symbol": "{{ item }}", "interval": "1d",
     "start_date": "{{ date.ago(90, format='yyyymmdd') }}",
     "end_date": "{{ date.today(format='yyyymmdd') }}"},
    {"id": "rsi_condition", "type": "ConditionNode",
     "plugin": "RSI",
     "items": {"from": "{{ nodes.historical.value.time_series }}", "extract": {"symbol": "{{ nodes.historical.value.symbol }}", "exchange": "{{ nodes.historical.value.exchange }}", "date": "{{ row.date }}", "close": "{{ row.close }}"}},
     "fields": {"period": 14, "threshold": 30, "direction": "below"}},
    {"id": "macd_condition", "type": "ConditionNode",
     "plugin": "MACD",
     "items": {"from": "{{ nodes.historical.value.time_series }}", "extract": {"symbol": "{{ nodes.historical.value.symbol }}", "exchange": "{{ nodes.historical.value.exchange }}", "date": "{{ row.date }}", "close": "{{ row.close }}"}},
     "fields": {"fast_period": 12, "slow_period": 26, "signal_period": 9, "signal_type": "golden_cross"}},
    {"id": "logic", "type": "LogicNode",
     "operator": "all",
     "conditions": [
       {"is_condition_met": "{{ nodes.rsi_condition.result.passed }}", "passed_symbols": "{{ nodes.rsi_condition.result }}"},
       {"is_condition_met": "{{ nodes.macd_condition.result.passed }}", "passed_symbols": "{{ nodes.macd_condition.result }}"}
     ]}
  ],
  "edges": [
    {"from": "broker", "to": "watchlist"},
    {"from": "watchlist", "to": "historical"},
    {"from": "historical", "to": "rsi_condition"},
    {"from": "historical", "to": "macd_condition"},
    {"from": "rsi_condition", "to": "logic"},
    {"from": "macd_condition", "to": "logic"}
  ]
}
```

**DAG Structure**:
```
watchlist → historical → rsi_condition ──→ logic (all)
                       → macd_condition ──→
```

## Input Ports

The LogicNode's `input` port is configured with `multiple=True` and `min_connections=2`. At least 2 ConditionNodes must be connected.

## Important Notes

1. **threshold required**: threshold is required for the `at_least`, `at_most`, `exactly`, and `weighted` operators
2. **Weight sum**: In the `weighted` operator, the sum of weights does not need to equal 1.0 (ratio comparison)
3. **Symbol intersection**: The `all` operator returns the intersection of symbols that passed all conditions
4. **Minimum 2 conditions**: LogicNode requires at least 2 condition inputs
