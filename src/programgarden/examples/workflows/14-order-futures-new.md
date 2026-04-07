# Overseas Futures New Order

Test overseas futures new order with OverseasFuturesNewOrderNode

## Workflow Structure

```mermaid
graph LR
    start(["Start"])
    broker(["Broker
(Overseas Futures)"])
    account["Account
(Overseas Futures)"]
    new_order[["NewOrder
(Overseas Futures)"]]
    start --> broker
    broker --> account
    account --> new_order
```

## Node List

| ID | Type | Description |
|----|------|------|
| start | StartNode | Workflow start |
| broker | OverseasFuturesBrokerNode | Overseas futures broker connection (paper trading, HKEX) |
| account | OverseasFuturesAccountNode | Overseas futures account balance/position query |
| new_order | OverseasFuturesNewOrderNode | Overseas futures new order |

## Key Settings

- **broker**: Paper trading mode
- **new_order**: side=`buy`

## Required Credentials

| ID | Type | Description |
|----|------|------|
| futures_cred | broker_ls_overseas_futures | LS Securities Overseas Futures API (paper trading, HKEX only) |

## Data Flow

1. **start** (StartNode) --> **broker** (OverseasFuturesBrokerNode)
1. **broker** (OverseasFuturesBrokerNode) --> **account** (OverseasFuturesAccountNode)
1. **account** (OverseasFuturesAccountNode) --> **new_order** (OverseasFuturesNewOrderNode)
