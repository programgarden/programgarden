# Korea Stock Open Orders

KoreaStockBrokerNode → KoreaStockOpenOrdersNode: Query open orders list

## Workflow Structure

```mermaid
graph LR
    start(["Start"])
    broker(["Broker
(Korea Stock)"])
    orders["OpenOrders
(Korea Stock)"]
    display[/"TableDisplay"/]
    start --> broker
    broker --> orders
    orders --> display
```

## Node List

| ID | Type | Description |
|----|------|------|
| start | StartNode | Workflow start |
| broker | KoreaStockBrokerNode | Korea stock broker connection |
| orders | KoreaStockOpenOrdersNode | Korea stock open orders query |
| display | TableDisplayNode | Table display output |

## Required Credentials

| ID | Type | Description |
|----|------|------|
| broker_cred | broker_ls_korea_stock | LS Securities Korea Stock API |

## Data Flow

1. **start** (StartNode) --> **broker** (KoreaStockBrokerNode)
1. **broker** (KoreaStockBrokerNode) --> **orders** (KoreaStockOpenOrdersNode)
1. **orders** (KoreaStockOpenOrdersNode) --> **display** (TableDisplayNode)
