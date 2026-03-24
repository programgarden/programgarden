---
category: workflow_example
tags: [example, order, new, modify, cancel, OverseasStockNewOrderNode, OverseasFuturesNewOrderNode, buy, sell, limit, market, auto_iterate]
priority: critical
---

# Example: Order Management

## Overview

Workflow examples for placing new orders, modifying, and canceling orders for overseas stocks/futures.

## Example 1: Overseas Futures New Order (Paper Trading)

Submits a limit buy order to an overseas futures account.

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
      "id": "account",
      "type": "OverseasFuturesAccountNode"
    },
    {
      "id": "new_order",
      "type": "OverseasFuturesNewOrderNode",
      "side": "buy",
      "order_type": "limit",
      "order": {
        "symbol": "HMCEG26",
        "exchange": "HKEX",
        "quantity": 1,
        "price": 9500.0
      }
    }
  ],
  "edges": [
    {"from": "start", "to": "broker"},
    {"from": "broker", "to": "account"},
    {"from": "account", "to": "new_order"}
  ],
  "credentials": [{"credential_id": "futures-cred"}]
}
```

### DAG Structure

```
StartNode → BrokerNode → AccountNode → NewOrderNode
```

### Order Node Configuration

| Field | Description | Values |
|-------|-------------|--------|
| `side` | Order direction | `"buy"` or `"sell"` |
| `order_type` | Order type | `"limit"` (limit order), `"market"` (market order) |
| `order` | Order details | symbol, exchange, quantity, price |

### order Field

| Field | Required | Description |
|-------|:--------:|-------------|
| `symbol` | Y | Symbol code |
| `exchange` | Y | Exchange |
| `quantity` | Y | Quantity |
| `price` | - | Price (required for limit orders) |

### Important Notes

- **HKEX (Hong Kong Exchange)**: Market orders are not supported; must use `limit`
- **Paper Trading**: Set `paper_trading: true` on BrokerNode (only supported for overseas futures)
- **Resilience Disabled by Default**: Order nodes have retry disabled by default due to duplicate order risk

## Example 2: Overseas Stock Buy Order

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
      "id": "new_order",
      "type": "OverseasStockNewOrderNode",
      "side": "buy",
      "order_type": "limit",
      "order": {
        "symbol": "AAPL",
        "exchange": "NASDAQ",
        "quantity": 10,
        "price": 150.0
      }
    }
  ],
  "edges": [
    {"from": "start", "to": "broker"},
    {"from": "broker", "to": "new_order"}
  ],
  "credentials": [{"credential_id": "broker-cred"}]
}
```

## Example 3: Condition-Based Automatic Buy

Automatically submits buy orders for symbols that meet the RSI oversold condition.

```json
{
  "nodes": [
    {"id": "start", "type": "StartNode"},
    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker-cred"},
    {"id": "account", "type": "OverseasStockAccountNode"},
    {"id": "watchlist", "type": "WatchlistNode", "symbols": [
      {"symbol": "AAPL", "exchange": "NASDAQ"}
    ]},
    {
      "id": "market",
      "type": "OverseasStockMarketDataNode",
      "symbol": "{{ item }}"
    },
    {
      "id": "sizing",
      "type": "PositionSizingNode",
      "symbol": "{{ item }}",
      "balance": "{{ nodes.account.balance }}",
      "market_data": "{{ nodes.market.value }}",
      "method": "fixed_percent",
      "max_percent": 10.0
    },
    {
      "id": "new_order",
      "type": "OverseasStockNewOrderNode",
      "side": "buy",
      "order_type": "limit",
      "order": "{{ nodes.sizing.order }}"
    }
  ],
  "edges": [
    {"from": "start", "to": "broker"},
    {"from": "broker", "to": "account"},
    {"from": "watchlist", "to": "market"},
    {"from": "account", "to": "sizing"},
    {"from": "market", "to": "sizing"},
    {"from": "sizing", "to": "new_order"}
  ],
  "credentials": [{"credential_id": "broker-cred"}]
}
```

### Key Pattern: PositionSizingNode → NewOrderNode

- `PositionSizingNode` calculates the appropriate order quantity based on balance (`balance`) and market data (`market_data`)
- The calculated `order` output is bound to `NewOrderNode`: `"order": "{{ nodes.sizing.order }}"`
- `method: "fixed_percent"` → Uses only 10% of the available balance

## Order Node Types

### Overseas Stocks

| Node | Purpose |
|------|---------|
| `OverseasStockNewOrderNode` | New order |
| `OverseasStockModifyOrderNode` | Order modification |
| `OverseasStockCancelOrderNode` | Order cancellation |

### Overseas Futures

| Node | Purpose |
|------|---------|
| `OverseasFuturesNewOrderNode` | New order |
| `OverseasFuturesModifyOrderNode` | Order modification |
| `OverseasFuturesCancelOrderNode` | Order cancellation |

## Order Binding Patterns

### Direct Specification

```json
"order": {
  "symbol": "AAPL",
  "exchange": "NASDAQ",
  "quantity": 10,
  "price": 150.0
}
```

### Binding from PositionSizingNode

```json
"order": "{{ nodes.sizing.order }}"
```

### Binding in auto-iterate (for liquidation)

```json
"order": {
  "symbol": "{{ item.symbol }}",
  "exchange": "{{ item.exchange }}",
  "quantity": "{{ item.quantity }}",
  "price": "{{ item.current_price }}"
}
```
