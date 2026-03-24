---
category: workflow_example
tags: [example, watchlist, universe, screener, filter, WatchlistNode, MarketUniverseNode, ScreenerNode, SymbolFilterNode, symbol_list]
priority: high
---

# Example: Symbol Management

## Overview

Usage examples for the 4 nodes that manage symbol lists in workflows.

## Symbol Management Node Comparison

| Node | Purpose | Number of Symbols |
|------|---------|-------------------|
| `WatchlistNode` | Manually specify watchlist symbols | Small (manual input) |
| `MarketUniverseNode` | Entire market / sector-based symbol pool | Large scale |
| `ScreenerNode` | Condition-based symbol screening | Filter results |
| `SymbolFilterNode` | Filter existing symbol lists | Depends on input |

## Example 1: Basic WatchlistNode Usage

Directly specify watchlist symbols and retrieve market data.

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
        {"exchange": "NYSE", "symbol": "JPM"}
      ]
    },
    {
      "id": "market",
      "type": "OverseasStockMarketDataNode",
      "symbol": "{{ item }}"
    }
  ],
  "edges": [
    {"from": "start", "to": "broker"},
    {"from": "broker", "to": "watchlist"},
    {"from": "watchlist", "to": "market"}
  ],
  "credentials": [{"credential_id": "broker-cred"}]
}
```

### Key Patterns

- When `WatchlistNode`'s `symbols` array is output, subsequent nodes auto-iterate
- Each symbol is in `{symbol, exchange}` format
- Access the full object with `{{ item }}`, or individual fields with `{{ item.symbol }}`

### Output

| Port | Type | Description |
|------|------|-------------|
| `symbols` | symbol_list | Symbol array `[{symbol, exchange}, ...]` |

## Example 2: WatchlistNode → Historical Data → Condition Filter

A typical symbol management pattern: watchlist → data collection → condition evaluation

```json
{
  "nodes": [
    {"id": "start", "type": "StartNode"},
    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker-cred"},
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

### DAG Structure

```
StartNode → BrokerNode → WatchlistNode → HistoricalDataNode → ConditionNode (RSI)
                              ↓ auto-iterate
                         Retrieves historical data per symbol → RSI calculation
```

### ConditionNode items Pattern

The `items` field transforms time-series data into row-level data:

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

- `from`: The array to iterate over
- `extract`: Fields to extract from each row (`row`)
- Symbol information (`symbol`, `exchange`) is taken from the parent level

## Symbol Data Format Rules

Symbol data must always use arrays containing `symbol` and `exchange` fields:

```json
// Correct format
[
  {"symbol": "AAPL", "exchange": "NASDAQ"},
  {"symbol": "TSLA", "exchange": "NASDAQ"}
]

// Incorrect format (do not use symbol as dictionary key)
{"AAPL": {"exchange": "NASDAQ"}}
```
