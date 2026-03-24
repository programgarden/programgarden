---
category: workflow_example
tags: [example, historical, chart_data, OverseasStockHistoricalDataNode, date_binding, candle, OHLCV, timeframe]
priority: high
---

# Example: Historical Data Retrieval

## Overview

A workflow that retrieves historical OHLCV (Open/High/Low/Close/Volume) data. Demonstrates date binding functions and various period configurations.

## Example 1: Single Symbol 30-Day Historical Data

```json
{
  "nodes": [
    {
      "id": "start",
      "type": "StartNode"
    },
    {
      "id": "broker",
      "type": "OverseasStockBrokerNode",
      "credential_id": "broker-cred"
    },
    {
      "id": "historical",
      "type": "OverseasStockHistoricalDataNode",
      "symbol": {"symbol": "AAPL", "exchange": "NASDAQ"},
      "start_date": "{{ date.ago(30, format='yyyymmdd') }}",
      "end_date": "{{ date.today(format='yyyymmdd') }}",
      "interval": "1d"
    }
  ],
  "edges": [
    {"from": "start", "to": "broker"},
    {"from": "broker", "to": "historical"}
  ],
  "credentials": [
    {"credential_id": "broker-cred"}
  ]
}
```

### Key Pattern: Date Binding Functions

| Function | Description | Example Result |
|----------|-------------|----------------|
| `date.today(format='yyyymmdd')` | Today's date | `"20260214"` |
| `date.ago(30, format='yyyymmdd')` | 30 days ago | `"20260115"` |
| `date.ago(90, format='yyyymmdd')` | 90 days ago | `"20251116"` |
| `date.months_ago(3, format='yyyymmdd')` | 3 months ago | `"20251114"` |
| `date.year_start(format='yyyymmdd')` | January 1st of this year | `"20260101"` |

### Output Data

| Port | Description |
|------|-------------|
| `value` | Symbol result (`symbol`, `exchange`, `time_series`) |

Each item in the `time_series` array:

| Field | Description |
|-------|-------------|
| `date` | Date (YYYYMMDD) |
| `open` | Open price |
| `high` | High price |
| `low` | Low price |
| `close` | Close price |
| `volume` | Trading volume |

## Example 2: Multiple Symbol Historical Data (auto-iterate)

Combines with WatchlistNode to retrieve historical data for multiple symbols.

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
    }
  ],
  "edges": [
    {"from": "start", "to": "broker"},
    {"from": "broker", "to": "watchlist"},
    {"from": "watchlist", "to": "historical"}
  ],
  "credentials": [
    {"credential_id": "broker-cred"}
  ]
}
```

### DAG Structure

```
StartNode → BrokerNode → WatchlistNode → HistoricalDataNode
                              ↓ auto-iterate
                         Executes 3 times (AAPL, TSLA, NVDA)
```

## Example 3: Historical Data → Technical Analysis Connection

Passes historical data to a ConditionNode to perform technical analysis.

```json
{
  "nodes": [
    {"id": "start", "type": "StartNode"},
    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker-cred"},
    {"id": "watchlist", "type": "WatchlistNode", "symbols": [
      {"exchange": "NASDAQ", "symbol": "AAPL"},
      {"exchange": "NASDAQ", "symbol": "TSLA"}
    ]},
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

### Data Flow

```
WatchlistNode → HistoricalDataNode → ConditionNode (RSI)
                     ↓                      ↓
              time_series array        RSI value + signal determination
```

## symbol Field Format

The `symbol` field must be an object containing `symbol` and `exchange`:

```json
// Direct specification
"symbol": {"symbol": "AAPL", "exchange": "NASDAQ"}

// Binding (from WatchlistNode)
"symbol": "{{ item }}"
```
