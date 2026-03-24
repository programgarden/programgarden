---
category: workflow_example
tags: [example, account, balance, stock, futures, OverseasStockAccountNode, OverseasFuturesAccountNode, positions, broker]
priority: high
---

# Example: Account Balance Inquiry

## Overview

A basic workflow that connects to a broker and retrieves account balance (deposit, held positions).

## Example 1: Overseas Stock Balance Inquiry

The most basic workflow. A 3-step composition of StartNode → BrokerNode → AccountNode.

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
      "id": "account",
      "type": "OverseasStockAccountNode"
    }
  ],
  "edges": [
    {"from": "start", "to": "broker"},
    {"from": "broker", "to": "account"}
  ],
  "credentials": [
    {"credential_id": "broker-cred"}
  ]
}
```

### DAG Structure

```
StartNode → OverseasStockBrokerNode → OverseasStockAccountNode
```

### Node Descriptions

| Node | Role |
|------|------|
| `StartNode` | Workflow entry point (one-shot execution) |
| `OverseasStockBrokerNode` | LS Securities overseas stock API connection. Authenticates via `credential_id` |
| `OverseasStockAccountNode` | Executes balance inquiry. Automatically inherits the broker connection |

### Output Data

Output of `OverseasStockAccountNode`:

| Port | Description |
|------|-------------|
| `balance` | Deposit information (`available`, `total`, etc.) |
| `positions` | Array of held positions (symbol, exchange, quantity, avg_price, pnl, etc.) |

### Key Patterns

- **Automatic Broker Connection Propagation**: When BrokerNode and AccountNode are connected via a `main` edge, AccountNode automatically inherits the broker's API connection. No `connection` binding is needed.
- **credential_id**: References authentication information defined in the workflow's `credentials` section.

## Example 2: Overseas Futures Balance Inquiry (Paper Trading)

Queries an overseas futures account in paper trading mode.

```json
{
  "nodes": [
    {
      "id": "start",
      "type": "StartNode"
    },
    {
      "id": "broker",
      "type": "OverseasFuturesBrokerNode",
      "credential_id": "futures-cred",
      "paper_trading": true
    },
    {
      "id": "account",
      "type": "OverseasFuturesAccountNode"
    }
  ],
  "edges": [
    {"from": "start", "to": "broker"},
    {"from": "broker", "to": "account"}
  ],
  "credentials": [
    {"credential_id": "futures-cred"}
  ]
}
```

### Key Differences

| Overseas Stocks | Overseas Futures |
|-----------------|------------------|
| `OverseasStockBrokerNode` | `OverseasFuturesBrokerNode` |
| `OverseasStockAccountNode` | `OverseasFuturesAccountNode` |
| Paper trading not supported (LS Securities) | `paper_trading: true` supported |

## Usage Patterns

### Using Balance Data in Subsequent Nodes

```json
{
  "id": "sizing",
  "type": "PositionSizingNode",
  "balance": "{{ nodes.account.balance }}"
}
```

### Auto-Iterate Over Held Positions

Since AccountNode's `positions` output is an array, subsequent nodes can access each position via `{{ item }}`:

```json
{
  "id": "close_order",
  "type": "OverseasStockNewOrderNode",
  "side": "sell",
  "order": {
    "symbol": "{{ item.symbol }}",
    "exchange": "{{ item.exchange }}",
    "quantity": "{{ item.quantity }}"
  }
}
```
