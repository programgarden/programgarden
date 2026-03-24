---
category: workflow_example
tags: [example, market, quote, stock, futures, OverseasStockMarketDataNode, realtime, symbols, price]
priority: high
---

# Example: Market Data Inquiry

## Overview

A workflow that retrieves current market data for overseas stocks/futures. Demonstrates various patterns from single to multiple symbols.

## Example 1: Multiple Symbol Market Data Inquiry

Retrieves market data for multiple symbols at once using a `symbols` array.

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
      "id": "market",
      "type": "OverseasStockMarketDataNode",
      "symbols": [
        {"symbol": "AAPL", "exchange": "NASDAQ"},
        {"symbol": "TSLA", "exchange": "NASDAQ"},
        {"symbol": "NVDA", "exchange": "NASDAQ"}
      ]
    }
  ],
  "edges": [
    {"from": "start", "to": "broker"},
    {"from": "broker", "to": "market"}
  ],
  "credentials": [
    {"credential_id": "broker-cred"}
  ]
}
```

### DAG Structure

```
StartNode → OverseasStockBrokerNode → OverseasStockMarketDataNode
```

### Output Data

Output of `OverseasStockMarketDataNode`:

| Port | Description |
|------|-------------|
| `value` | Single symbol market data (last query result) |
| `values` | Array of multiple symbol market data |

Market data fields per symbol:

| Field | Description |
|-------|-------------|
| `symbol` | Symbol code |
| `exchange` | Exchange |
| `price` | Current price |
| `change` | Change from previous close |
| `change_pct` | Change percentage (%) |
| `volume` | Trading volume |

## Example 2: WatchlistNode + Market Data Inquiry (auto-iterate)

Define a watchlist with WatchlistNode, and MarketDataNode automatically iterates over each symbol.

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
  "credentials": [
    {"credential_id": "broker-cred"}
  ]
}
```

### Key Pattern: auto-iterate

```
WatchlistNode (array output)
    ↓ auto-iterate
MarketDataNode (accesses each symbol via {{ item }})
    → Executes 4 times: AAPL, TSLA, NVDA, JPM
```

- `WatchlistNode` outputs the `symbols` array
- The subsequent `MarketDataNode` automatically iterates over each symbol via `{{ item }}`
- Individual fields can be accessed with `{{ item.symbol }}`, `{{ item.exchange }}`
- Binding `{{ item }}` to the `symbol` field passes the `{symbol, exchange}` object

## Example 3: Overseas Futures Market Data Inquiry

```json
{
  "nodes": [
    {"id": "start", "type": "StartNode"},
    {
      "id": "broker",
      "type": "OverseasFuturesBrokerNode",
      "credential_id": "futures-cred",
      "paper_trading": true
    },
    {
      "id": "market",
      "type": "OverseasFuturesMarketDataNode",
      "symbols": [
        {"symbol": "HMCEG26", "exchange": "HKEX"}
      ]
    }
  ],
  "edges": [
    {"from": "start", "to": "broker"},
    {"from": "broker", "to": "market"}
  ],
  "credentials": [
    {"credential_id": "futures-cred"}
  ]
}
```

### Overseas Futures Symbol Format

- `HMCEG26`: Hang Seng Mini Futures, February 2026 contract
- Month codes: F=Jan, G=Feb, H=Mar, J=Apr, K=May, M=Jun, N=Jul, Q=Aug, U=Sep, V=Oct, X=Nov, Z=Dec

## symbols vs symbol Usage

| Pattern | Configuration | Use Case |
|---------|---------------|----------|
| Direct specification | `symbols: [{...}, {...}]` | Query multiple symbols directly from the node |
| Binding | `symbol: "{{ item }}"` | Auto-iterate from WatchlistNode, etc. |
