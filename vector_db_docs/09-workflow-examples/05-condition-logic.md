---
category: workflow_example
tags: [example, condition, logic, rsi, macd, ConditionNode, LogicNode, plugin, all, any, weighted, golden_cross, oversold]
priority: critical
---

# Example: Conditions + Logic Combinations

## Overview

A workflow that calculates technical indicators with ConditionNode and logically combines multiple conditions with LogicNode.

## Example 1: RSI Oversold Filtering

Filters oversold symbols through a WatchlistNode → HistoricalDataNode → ConditionNode(RSI) pipeline.

```json
{
  "nodes": [
    {"id": "start", "type": "StartNode"},
    {
      "id": "broker",
      "type": "OverseasStockBrokerNode",
      "credential_id": "broker-cred"
    },
    {
      "id": "watchlist",
      "type": "WatchlistNode",
      "symbols": [
        {"exchange": "NASDAQ", "symbol": "AAPL"},
        {"exchange": "NASDAQ", "symbol": "TSLA"},
        {"exchange": "NASDAQ", "symbol": "NVDA"}
      ]
    },
    {
      "id": "historical",
      "type": "OverseasStockHistoricalDataNode",
      "symbol": "{{ item }}",
      "interval": "1d",
      "start_date": "{{ date.ago(60, format='yyyymmdd') }}",
      "end_date": "{{ date.today(format='yyyymmdd') }}"
    },
    {
      "id": "rsi_condition",
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
  ],
  "edges": [
    {"from": "start", "to": "broker"},
    {"from": "broker", "to": "watchlist"},
    {"from": "watchlist", "to": "historical"},
    {"from": "historical", "to": "rsi_condition"}
  ],
  "credentials": [{"credential_id": "broker-cred"}]
}
```

### ConditionNode Configuration

| Field | Description |
|-------|-------------|
| `plugin` | Plugin to use (`"RSI"`, `"MACD"`, `"BollingerBands"`, etc.) |
| `items` | Input data (`from`: iteration array, `extract`: field mapping) |
| `fields` | Plugin parameters |

### RSI Plugin fields

| Parameter | Description | Default |
|-----------|-------------|---------|
| `period` | RSI calculation period | 14 |
| `threshold` | Threshold value | 30 |
| `direction` | `"below"` (oversold) or `"above"` (overbought) | `"below"` |

### ConditionNode Output

| Port | Description |
|------|-------------|
| `result` | Includes whether the condition is met, passed_symbols, symbol_results, etc. |

## Example 2: RSI + MACD Combined Conditions (LogicNode)

Combines results from two ConditionNodes with AND logic using LogicNode.

```json
{
  "nodes": [
    {"id": "start", "type": "StartNode"},
    {
      "id": "broker",
      "type": "OverseasStockBrokerNode",
      "credential_id": "broker-cred"
    },
    {
      "id": "watchlist",
      "type": "WatchlistNode",
      "symbols": [
        {"exchange": "NASDAQ", "symbol": "AAPL"},
        {"exchange": "NASDAQ", "symbol": "TSLA"},
        {"exchange": "NASDAQ", "symbol": "NVDA"},
        {"exchange": "NASDAQ", "symbol": "MSFT"},
        {"exchange": "NYSE", "symbol": "JPM"}
      ]
    },
    {
      "id": "historical",
      "type": "OverseasStockHistoricalDataNode",
      "symbol": "{{ item }}",
      "interval": "1d",
      "start_date": "{{ date.ago(90, format='yyyymmdd') }}",
      "end_date": "{{ date.today(format='yyyymmdd') }}"
    },
    {
      "id": "rsi_condition",
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
    },
    {
      "id": "macd_condition",
      "type": "ConditionNode",
      "plugin": "MACD",
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
        "fast_period": 12,
        "slow_period": 26,
        "signal_period": 9,
        "signal_type": "golden_cross"
      }
    },
    {
      "id": "logic",
      "type": "LogicNode",
      "operator": "all",
      "conditions": [
        {
          "is_condition_met": "{{ nodes.rsi_condition.result.passed }}",
          "passed_symbols": "{{ nodes.rsi_condition.result }}"
        },
        {
          "is_condition_met": "{{ nodes.macd_condition.result.passed }}",
          "passed_symbols": "{{ nodes.macd_condition.result }}"
        }
      ]
    }
  ],
  "edges": [
    {"from": "start", "to": "broker"},
    {"from": "broker", "to": "watchlist"},
    {"from": "watchlist", "to": "historical"},
    {"from": "historical", "to": "rsi_condition"},
    {"from": "historical", "to": "macd_condition"},
    {"from": "rsi_condition", "to": "logic"},
    {"from": "macd_condition", "to": "logic"}
  ],
  "credentials": [{"credential_id": "broker-cred"}]
}
```

### DAG Structure (Branch + Merge)

```
                         → rsi_condition ──→
watchlist → historical ──                     logic (all)
                         → macd_condition ──→
```

- Branches into two paths from the `historical` node (RSI, MACD)
- Both ConditionNode results merge at the `LogicNode`
- `operator: "all"` → Must satisfy both RSI oversold AND MACD golden cross to pass

### LogicNode Configuration

| Field | Description |
|-------|-------------|
| `operator` | Logical operator (`all`, `any`, `not`, `xor`, `at_least`, `at_most`, `exactly`, `weighted`) |
| `threshold` | Threshold value (used with `at_least`, `at_most`, `exactly`, `weighted`) |
| `conditions` | Conditions array |

### conditions Array Structure

```json
{
  "is_condition_met": "{{ nodes.rsi_condition.result.passed }}",
  "passed_symbols": "{{ nodes.rsi_condition.result }}",
  "weight": 0.4
}
```

| Field | Required | Description |
|-------|:--------:|-------------|
| `is_condition_met` | Y | Boolean indicating whether the condition is met |
| `passed_symbols` | Y | Data of symbols that passed |
| `weight` | - | Weight (for the `weighted` operator) |

### MACD Plugin fields

| Parameter | Description | Default |
|-----------|-------------|---------|
| `fast_period` | Short-term EMA period | 12 |
| `slow_period` | Long-term EMA period | 26 |
| `signal_period` | Signal period | 9 |
| `signal_type` | `"golden_cross"` or `"dead_cross"` | - |

## Example 3: Weighted Conditions (weighted)

```json
{
  "id": "logic",
  "type": "LogicNode",
  "operator": "weighted",
  "threshold": 0.6,
  "conditions": [
    {
      "is_condition_met": "{{ nodes.rsi.result.passed }}",
      "passed_symbols": "{{ nodes.rsi.result }}",
      "weight": 0.4
    },
    {
      "is_condition_met": "{{ nodes.macd.result.passed }}",
      "passed_symbols": "{{ nodes.macd.result }}",
      "weight": 0.3
    },
    {
      "is_condition_met": "{{ nodes.bb.result.passed }}",
      "passed_symbols": "{{ nodes.bb.result }}",
      "weight": 0.3
    }
  ]
}
```

- RSI(0.4) + MACD(0.3) + BollingerBands(0.3) = 1.0
- Only RSI met → 0.4 (does not pass)
- RSI + MACD met → 0.7 >= 0.6 (passes)

## Available Plugins

| Plugin | Description |
|--------|-------------|
| `RSI` | Relative Strength Index |
| `MACD` | Moving Average Convergence Divergence |
| `BollingerBands` | Bollinger Bands |
| `Stochastic` | Stochastic Oscillator |
| `MovingAverageCross` | Moving Average Crossover |
| `VolumeSpike` | Volume Spike |
| `DualMomentum` | Dual Momentum |
| `ATR` | Average True Range |
| `PriceChannel` | Price Channel |
| `ADX` | Average Directional Index |
| `OBV` | On-Balance Volume |
