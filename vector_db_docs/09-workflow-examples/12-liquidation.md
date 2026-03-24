---
category: workflow_example
tags: [example, liquidation, close_all, futures, auto_iterate, close_side, position, OverseasFuturesNewOrderNode]
priority: high
---

# Example: Liquidation Strategy

## Overview

A workflow that fully liquidates all held positions. It auto-iterates over the positions output from AccountNode and submits a reverse order for each position.

## Example 1: Full Liquidation of Overseas Futures Positions

Liquidates all overseas futures positions in a paper trading environment.

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
      "id": "close_order",
      "type": "OverseasFuturesNewOrderNode",
      "side": "{{ item.close_side }}",
      "order_type": "limit",
      "order": {
        "symbol": "{{ item.symbol }}",
        "exchange": "{{ item.exchange }}",
        "quantity": "{{ item.quantity }}",
        "price": "{{ item.current_price }}"
      }
    }
  ],
  "edges": [
    {"from": "start", "to": "broker"},
    {"from": "broker", "to": "account"},
    {"from": "account", "to": "close_order"}
  ],
  "credentials": [{"credential_id": "futures-cred"}]
}
```

### DAG Structure

```
StartNode → BrokerNode → AccountNode → NewOrderNode
                              ↓ auto-iterate
                         Liquidation order for each position
```

### Key Pattern: Full Liquidation via auto-iterate

1. `AccountNode` outputs the held positions array (`positions`)
2. `NewOrderNode` automatically executes for each position
3. Access each position's fields with `{{ item }}`

### Position Data Field Usage

| Binding | Description |
|--------|------|
| `{{ item.symbol }}` | Position symbol code |
| `{{ item.exchange }}` | Exchange |
| `{{ item.quantity }}` | Held quantity |
| `{{ item.current_price }}` | Current price |
| `{{ item.close_side }}` | Liquidation direction (long → `"sell"`, short → `"buy"`) |

### Automatic close_side Calculation

`close_side` is automatically calculated by AccountNode:
- Long position → `close_side = "sell"` (liquidate by selling)
- Short position → `close_side = "buy"` (liquidate by buying)

Therefore, binding `"side": "{{ item.close_side }}"` automatically sets the correct liquidation direction.

### Notes

- **HKEX**: Market orders not supported → use `order_type: "limit"` with `price: "{{ item.current_price }}"`
- **Paper trading**: `paper_trading: true` required (overseas futures)
- **Overseas stocks**: Paper trading not supported (LS Securities), orders only available in live trading

## Example 2: Overseas Stock Position Liquidation

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
      "id": "account",
      "type": "OverseasStockAccountNode"
    },
    {
      "id": "close_order",
      "type": "OverseasStockNewOrderNode",
      "side": "sell",
      "order_type": "limit",
      "order": {
        "symbol": "{{ item.symbol }}",
        "exchange": "{{ item.exchange }}",
        "quantity": "{{ item.quantity }}",
        "price": "{{ item.current_price }}"
      }
    }
  ],
  "edges": [
    {"from": "start", "to": "broker"},
    {"from": "broker", "to": "account"},
    {"from": "account", "to": "close_order"}
  ],
  "credentials": [{"credential_id": "broker-cred"}]
}
```

Since overseas stocks only support long positions, liquidation is always `"sell"`.

## Liquidation Pattern Comparison

| Product | BrokerNode | OrderNode | side |
|------|------------|-----------|------|
| Overseas stocks | `OverseasStockBrokerNode` | `OverseasStockNewOrderNode` | `"sell"` (fixed) |
| Overseas futures | `OverseasFuturesBrokerNode` | `OverseasFuturesNewOrderNode` | `"{{ item.close_side }}"` (dynamic) |

### Overseas Futures vs Overseas Stocks Differences

- **Overseas futures**: Both long and short positions → dynamic liquidation via `close_side`
- **Overseas stocks**: Long positions only → fixed `"sell"`
