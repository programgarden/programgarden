---
category: plugin
tags: [order, market_order, limit_order, position_sizing, trailing_stop, stop_loss, profit_target]
priority: critical
---

# Order System: Order Types + Position Management

## Order Types (NewOrderNode)

Specify the order type using the `order_type` field of a `NewOrderNode`.

### Market Order

Executed immediately at the current market price.

```json
{
  "id": "order",
  "type": "OverseasStockNewOrderNode",
  "side": "buy",
  "order_type": "market",
  "order": "{{ item }}"
}
```

- Advantage: Guaranteed immediate execution
- Disadvantage: Slippage may occur
- Suitable for: When fast entry/exit is needed

### Limit Order

Executed only at or below the specified price (buy) / at or above (sell).

```json
{
  "id": "order",
  "type": "OverseasStockNewOrderNode",
  "side": "buy",
  "order_type": "limit",
  "order": "{{ item }}"
}
```

- Advantage: Executed at the desired price
- Disadvantage: May not be filled
- Suitable for: When precise price control is needed

### Order Input Format

Order data passed to the `order` field:

```json
{
  "symbol": "AAPL",
  "exchange": "NASDAQ",
  "quantity": 10,
  "price": 150.00
}
```

## Order Node Safety Mechanisms

### Rate Limit

Built into all order nodes by default:
- **Minimum interval**: 5 seconds (prevents consecutive executions of the same node)
- **Concurrent execution**: 1 (prevents duplicate orders)
- **On excess**: skip (ignored)

### Direct Connection to Real-time Nodes Blocked

Direct connection from real-time data nodes to order nodes is prohibited. A `ThrottleNode` must be used in between:

```
[RealMarketDataNode] → [ThrottleNode] → [ConditionNode] → [NewOrderNode]  (O)
[RealMarketDataNode] → [ConditionNode] → [NewOrderNode]                    (X Error)
```

### Resilience (Retry Settings)

Order nodes have **retries disabled by default** due to duplicate order risk:
- Only network errors (connection failures) are allowed to retry
- Errors that reached the server must not be retried

```json
{
  "id": "order",
  "type": "OverseasStockNewOrderNode",
  "resilience": {
    "retry": {"enabled": false},
    "fallback": {"mode": "error"}
  }
}
```

## PositionSizingNode (Order Quantity Calculation)

A node that calculates the appropriate quantity before placing an order.

```json
{
  "id": "sizing",
  "type": "PositionSizingNode",
  "method": "fixed_amount",
  "fixed_amount": 1000
}
```

### Quantity Calculation Methods

| method | Description | Required Fields |
|--------|-------------|----------------|
| `fixed_quantity` | Fixed quantity | `fixed_quantity` |
| `fixed_amount` | Fixed amount (auto-calculates quantity) | `fixed_amount` |
| `percent_of_equity` | Percentage of equity | `equity_percent` |
| `equal_weight` | Equal weight distribution | (auto-calculated) |
| `kelly_criterion` | Kelly criterion | `win_rate`, `avg_win`, `avg_loss` |

### Usage Example (Fixed Amount)

```json
{
  "nodes": [
    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "cred"},
    {"id": "account", "type": "OverseasStockAccountNode"},
    {"id": "sizing", "type": "PositionSizingNode",
     "method": "fixed_amount", "fixed_amount": 500},
    {"id": "order", "type": "OverseasStockNewOrderNode",
     "side": "buy", "order_type": "limit", "order": "{{ item }}"}
  ],
  "edges": [
    {"from": "broker", "to": "account"},
    {"from": "account", "to": "sizing"},
    {"from": "sizing", "to": "order"}
  ]
}
```

## Order Modification/Cancellation

### ModifyOrderNode (Order Modification)

Modifies the price/quantity of an unfilled order.

```json
{
  "id": "modify",
  "type": "OverseasStockModifyOrderNode",
  "original_order_id": "{{ item.order_id }}",
  "symbol": "{{ item.symbol }}",
  "exchange": "{{ item.exchange }}",
  "new_price": "{{ item.new_price }}"
}
```

### CancelOrderNode (Order Cancellation)

Cancels an unfilled order.

```json
{
  "id": "cancel",
  "type": "OverseasStockCancelOrderNode",
  "original_order_id": "{{ item.order_id }}",
  "symbol": "{{ item.symbol }}",
  "exchange": "{{ item.exchange }}"
}
```

## Position Management Strategy Patterns

### Automated Stop Loss/Take Profit (Real-time)

```json
{
  "nodes": [
    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "cred"},
    {"id": "real_account", "type": "OverseasStockRealAccountNode"},
    {"id": "throttle", "type": "ThrottleNode", "mode": "debounce", "interval_ms": 10000},
    {"id": "stop_loss", "type": "ConditionNode", "plugin": "StopLoss",
     "positions": "{{ nodes.real_account.positions }}",
     "fields": {"stop_percent": -3.0}},
    {"id": "profit_target", "type": "ConditionNode", "plugin": "ProfitTarget",
     "positions": "{{ nodes.real_account.positions }}",
     "fields": {"target_percent": 5.0}},
    {"id": "exit_logic", "type": "LogicNode", "operator": "any"},
    {"id": "sell_order", "type": "OverseasStockNewOrderNode",
     "side": "sell", "order_type": "market", "order": "{{ item }}"}
  ],
  "edges": [
    {"from": "broker", "to": "real_account"},
    {"from": "real_account", "to": "throttle"},
    {"from": "throttle", "to": "stop_loss"},
    {"from": "throttle", "to": "profit_target"},
    {"from": "stop_loss", "to": "exit_logic"},
    {"from": "profit_target", "to": "exit_logic"},
    {"from": "exit_logic", "to": "sell_order"}
  ]
}
```

**Flow**: Real-time account monitoring -> 10-second debounce -> stop loss OR take profit condition -> market sell

### Trailing Stop (RiskTracker Integration)

```json
{
  "nodes": [
    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "cred"},
    {"id": "real_account", "type": "OverseasStockRealAccountNode"},
    {"id": "throttle", "type": "ThrottleNode", "mode": "debounce", "interval_ms": 5000},
    {"id": "trailing", "type": "ConditionNode", "plugin": "TrailingStop",
     "fields": {"trail_ratio": 0.3}},
    {"id": "sell_order", "type": "OverseasStockNewOrderNode",
     "side": "sell", "order_type": "market", "order": "{{ item }}"}
  ],
  "edges": [
    {"from": "broker", "to": "real_account"},
    {"from": "real_account", "to": "throttle"},
    {"from": "throttle", "to": "trailing"},
    {"from": "trailing", "to": "sell_order"}
  ]
}
```

**TrailingStop + RiskTracker**: When a PortfolioNode is present in the workflow, the `hwm` feature is automatically activated, enabling HWM-based drawdown tracking.

## BacktestEngineNode Exit Rules

Built-in exit rules available in backtesting:

| Field | Description | Example |
|-------|-------------|---------|
| `stop_loss_percent` | Stop loss percentage (%) | `-5.0` |
| `take_profit_percent` | Take profit percentage (%) | `10.0` |
| `trailing_stop_percent` | Trailing stop (%) | `3.0` |
| `time_stop_days` | Time-based stop (days) | `30` |
| `max_holding_days` | Maximum holding period | `60` |

```json
{
  "id": "backtest",
  "type": "BacktestEngineNode",
  "exit_rules": {
    "stop_loss_percent": -5.0,
    "take_profit_percent": 10.0,
    "trailing_stop_percent": 3.0,
    "time_stop_days": 30
  }
}
```

## Order Nodes by Product Type

| Product | New Order | Modify | Cancel |
|---------|-----------|--------|--------|
| Overseas Stocks | `OverseasStockNewOrderNode` | `OverseasStockModifyOrderNode` | `OverseasStockCancelOrderNode` |
| Overseas Futures | `OverseasFuturesNewOrderNode` | `OverseasFuturesModifyOrderNode` | `OverseasFuturesCancelOrderNode` |
