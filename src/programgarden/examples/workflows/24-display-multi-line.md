# Multi-Line Chart

Display multiple symbols' RSI on a single chart with MultiLineChartNode

## Workflow Structure

```mermaid
graph LR
    start(["Start"])
    broker(["Broker
(Overseas Stock)"])
    watchlist["Watchlist"]
    historical["Historical
(Overseas Stock)"]
    condition{"Condition
(RSI)"}
    chart[/"MultiLineChart"/]
    start --> broker
    watchlist --> historical
    broker --> condition
    historical --> condition
    condition --> chart
```

## Node List

| ID | Type | Description |
|----|------|------|
| start | StartNode | Workflow start |
| broker | OverseasStockBrokerNode | Overseas stock broker connection |
| watchlist | WatchlistNode | Define watchlist symbols |
| historical | OverseasStockHistoricalDataNode | Overseas stock historical data query |
| condition | ConditionNode | Condition check (plugin-based) |
| chart | MultiLineChartNode | Multi-line chart |

## Key Settings

- **watchlist**: AAPL, MSFT, NVDA
- **condition**: Plugin `RSI`

## Required Credentials

| ID | Type | Description |
|----|------|------|
| broker_cred | broker_ls_overseas_stock | LS Securities Overseas Stock API |

## Data Flow

1. **start** (StartNode) --> **broker** (OverseasStockBrokerNode)
1. **watchlist** (WatchlistNode) --> **historical** (OverseasStockHistoricalDataNode)
1. **broker** (OverseasStockBrokerNode) --> **condition** (ConditionNode)
1. **historical** (OverseasStockHistoricalDataNode) --> **condition** (ConditionNode)
1. **condition** (ConditionNode) --> **chart** (MultiLineChartNode)
