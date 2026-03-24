---
category: node_reference
tags: [order, new_order, modify, cancel, position_sizing]
priority: critical
---

# Order Nodes: New, Modify, Cancel, Position Sizing

## NewOrderNode (New Order)

Executes new buy/sell orders. Select the order method via plugin.

| Product | Node Type |
|---------|----------|
| Overseas Stocks | `OverseasStockNewOrderNode` |
| Overseas Futures | `OverseasFuturesNewOrderNode` |

```json
{
  "id": "order",
  "type": "OverseasStockNewOrderNode",
  "plugin": "MarketOrder",
  "fields": {
    "side": "buy",
    "amount_type": "percent_balance",
    "amount": 90
  }
}
```

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `plugin` | string | O | Order plugin (`MarketOrder` or `LimitOrder`) |
| `fields` | object | - | Plugin parameters |
| `order` | object | Conditional | PositionSizingNode output binding |

**Output**: `result`

```json
{
  "success": true, "order_no": "12345",
  "symbol": "AAPL", "side": "buy",
  "quantity": 10, "price": 192.30
}
```

**Safety Rules:**
- Direct connection from real-time nodes is blocked (ThrottleNode required)
- Auto-retry disabled (duplicate order prevention)
- Overseas stock BrokerNode does not support paper trading → actual trades

## ModifyOrderNode (Order Modification)

Modifies the price of open (unfilled) orders.

| Product | Node Type |
|---------|----------|
| Overseas Stocks | `OverseasStockModifyOrderNode` |
| Overseas Futures | `OverseasFuturesModifyOrderNode` |

```json
{
  "id": "modify",
  "type": "OverseasStockModifyOrderNode",
  "plugin": "TrailingStop",
  "fields": {
    "price_gap_percent": 0.5,
    "max_modifications": 5
  }
}
```

TrailingStop plugin: Tracks the current price and automatically modifies the order price to increase fill probability.

## CancelOrderNode (Order Cancellation)

Cancels open (unfilled) orders.

| Product | Node Type |
|---------|----------|
| Overseas Stocks | `OverseasStockCancelOrderNode` |
| Overseas Futures | `OverseasFuturesCancelOrderNode` |

```json
{
  "id": "cancel",
  "type": "OverseasStockCancelOrderNode",
  "plugin": "TimeStop",
  "fields": {"timeout_minutes": 30}
}
```

TimeStop plugin: Automatically cancels if unfilled within the specified time.

## PositionSizingNode (Position Size Calculation)

Automatically calculates order quantities. Applies rules like "invest only 10% of balance".

```json
{
  "id": "sizing",
  "type": "PositionSizingNode",
  "symbol": "{{ item }}",
  "balance": "{{ nodes.account.balance }}",
  "method": "fixed_percent",
  "max_percent": 10
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `symbol` | expression | - | Target symbol |
| `balance` | expression | - | Available balance |
| `market_data` | expression | - | Current price (optional) |
| `method` | string | `"fixed_percent"` | Sizing method |
| `max_percent` | number | `10` | Balance ratio (%) |
| `fixed_amount` | number | - | Fixed amount |
| `fixed_quantity` | number | `1` | Fixed quantity |

**method Options:**

| Method | Description |
|--------|-------------|
| `fixed_percent` | N% of balance (most common) |
| `fixed_amount` | Fixed amount ($1000 per symbol, etc.) |
| `fixed_quantity` | Fixed quantity (10 shares per symbol, etc.) |
| `kelly` | Kelly formula (optimal ratio based on win rate) |
| `atr_based` | ATR-based (volatility-based) |

**Output**: `order`

```json
{"symbol": "AAPL", "exchange": "NASDAQ", "quantity": 5, "price": 192.30}
```

**Typical Pattern:**
```
AccountNode ──(balance)──┐
                         ├──▶ PositionSizingNode ──(order)──▶ NewOrderNode
ConditionNode ──(symbols)─┘
```

Binding PositionSizingNode output to NewOrderNode's `order` field enables automatic ordering with calculated quantities.
