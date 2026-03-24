---
category: workflow_example
tags: [example, risk, position_sizing, portfolio, PositionSizingNode, PortfolioNode, fixed_percent, balance, order_calculation]
priority: high
---

# Example: Risk / Position Sizing

## Overview

A workflow that calculates appropriate order quantities based on account balance and market data. Utilizes PositionSizingNode.

## Example 1: Balance-Based Position Sizing

Generates safe orders that buy only a fixed percentage of the account balance.

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
      "id": "watchlist",
      "type": "WatchlistNode",
      "symbols": [
        {"symbol": "AAPL", "exchange": "NASDAQ"}
      ]
    },
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

### DAG Structure

```
                  account ──→
                              sizing → new_order
watchlist → market ──────→
```

- Two paths from `account` and `market` merge into `sizing`
- `PositionSizingNode` receives both balance and market data simultaneously to calculate order quantity

### PositionSizingNode Configuration

| Field | Type | Description |
|-------|------|-------------|
| `symbol` | expression | Target symbol |
| `balance` | expression | Available balance amount |
| `market_data` | expression | Market data (including current price) |
| `method` | string | Sizing method |
| `max_percent` | number | Maximum investment percentage (%) |

### Sizing Methods (method)

| Method | Description |
|--------|-------------|
| `fixed_percent` | Invest N% of available balance |
| `fixed_amount` | Invest a fixed dollar amount |
| `risk_parity` | Risk parity based |

### Output

| Port | Description |
|------|-------------|
| `order` | Calculated order object (`{symbol, exchange, quantity, price}`) |
| `calculation` | Calculation details (investment amount, quantity rationale, etc.) |

### Calculation Example

```
Available balance: $50,000
max_percent: 10% → Investable amount: $5,000
AAPL current price: $150
→ Order quantity: 33 shares (= $5,000 / $150, rounded down)
→ Order price: $150 (limit order at current price)
```

## Key Patterns

### Balance Binding

```json
"balance": "{{ nodes.account.balance }}"
```

- Uses `available` (available deposit) from `AccountNode`'s `balance` output

### Market Data Binding

```json
"market_data": "{{ nodes.market.value }}"
```

- `MarketDataNode`'s `value` output (includes current price)

### Order Output Binding

```json
"order": "{{ nodes.sizing.order }}"
```

- Passes the order object calculated by `PositionSizingNode` to `NewOrderNode`
- No need to manually calculate quantity/price

## Data Flow Summary

```
1. AccountNode → balance (available deposit)
2. MarketDataNode → value (market data, current price)
3. PositionSizingNode → Calculates order quantity as N% of balance
4. NewOrderNode → Executes the calculated order
```
