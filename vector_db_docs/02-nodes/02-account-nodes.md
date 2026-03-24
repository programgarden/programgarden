---
category: node_reference
tags: [account, balance, open_orders, real_account]
priority: high
---

# Account Nodes: Balance Query, Open Orders, Real-time

## AccountNode (One-time Account Query)

Queries account information at the current point in time via REST API.

| Product | Node Type |
|---------|----------|
| Overseas Stocks | `OverseasStockAccountNode` |
| Overseas Futures | `OverseasFuturesAccountNode` |

```json
{"id": "account", "type": "OverseasStockAccountNode"}
```

**Output:**
- `held_symbols` - List of held symbol codes `["AAPL", "NVDA"]`
- `balance` - Available cash/buying power
- `positions` - Held position details

```json
[
  {
    "symbol": "AAPL", "exchange": "NASDAQ",
    "quantity": 10, "buy_price": 185.50,
    "current_price": 192.30, "pnl_rate": 3.67
  }
]
```

If no positions are held, `positions` returns an empty array `[]` (not an error).

## OpenOrdersNode (Open Order Query)

Queries the list of open (unfilled) orders.

| Product | Node Type |
|---------|----------|
| Overseas Stocks | `OverseasStockOpenOrdersNode` |
| Overseas Futures | `OverseasFuturesOpenOrdersNode` |

```json
{"id": "openOrders", "type": "OverseasStockOpenOrdersNode"}
```

**Output:**
- `open_orders` - List of open orders
- `count` - Number of open orders

```json
[
  {
    "order_no": "12345", "symbol": "AAPL", "side": "buy",
    "order_type": "limit", "price": 180.00,
    "quantity": 10, "filled_quantity": 0
  }
]
```

## RealAccountNode (Real-time Account)

Receives account information in real-time via WebSocket.

| Product | Node Type |
|---------|----------|
| Overseas Stocks | `OverseasStockRealAccountNode` |
| Overseas Futures | `OverseasFuturesRealAccountNode` |

```json
{
  "id": "realAccount",
  "type": "OverseasStockRealAccountNode",
  "stay_connected": true,
  "sync_interval_sec": 60,
  "commission_rate": 0.25
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `stay_connected` | boolean | `true` | Keep WebSocket connection after workflow ends |
| `sync_interval_sec` | number | `60` | REST API sync interval (seconds, 10~3600) |
| `commission_rate` | number | `0.25` | Commission rate (%) |
| `tax_rate` | number | `0.0` | Tax rate (%) |

**Output**: `held_symbols`, `balance`, `open_orders`, `positions` (includes real-time P&L)

**AccountNode vs RealAccountNode:**

| Item | AccountNode | RealAccountNode |
|------|-------------|-----------------|
| Connection | REST API (one-time) | WebSocket (real-time) |
| Refresh | Once at call time | Automatic on events |
| Use case | Pre-trade balance check | Real-time monitoring/risk management |

**Note**: When connecting order nodes downstream of RealAccountNode, ThrottleNode must be placed in between.

## RealOrderEventNode (Real-time Order Events)

Receives order acceptance/fill/modification/cancellation/rejection events in real-time.

| Product | Node Type |
|---------|----------|
| Overseas Stocks | `OverseasStockRealOrderEventNode` |
| Overseas Futures | `OverseasFuturesRealOrderEventNode` |

```json
{
  "id": "orderEvents",
  "type": "OverseasStockRealOrderEventNode",
  "stay_connected": true
}
```

**Output Ports (per event):**

| Port | Description |
|------|-------------|
| `accepted` | Order accepted |
| `filled` | Order filled |
| `modified` | Modification complete |
| `cancelled` | Cancellation complete |
| `rejected` | Order rejected |

Usage: Connecting condition logic to the `filled` port enables flows like "on fill → auto-generate take-profit/stop-loss order".
