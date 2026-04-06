# Symbol Filtering (Watchlist - Positions)

Remove held positions from watchlist with SymbolFilterNode

## Workflow Structure

```mermaid
graph LR
    start(["Start"])
    broker(["Broker
(Overseas Stock)"])
    watchlist["Watchlist"]
    account["Account
(Overseas Stock)"]
    filter["SymbolFilter"]
    market["MarketData
(Overseas Stock)"]
    start --> broker
    broker --> watchlist
    broker --> account
    watchlist --> filter
    account --> filter
    filter --> market
```

## Node List

| ID | Type | Description |
|----|------|------|
| start | StartNode | Workflow start |
| broker | OverseasStockBrokerNode | Overseas stock broker connection |
| watchlist | WatchlistNode | Define watchlist symbols |
| account | OverseasStockAccountNode | Overseas stock account balance/position query |
| filter | SymbolFilterNode | Symbol filter (intersection/difference/union) |
| market | OverseasStockMarketDataNode | Overseas stock market data query |

## Key Settings

- **watchlist**: AAPL, TSLA, NVDA, MSFT, JPM

## Required Credentials

| ID | Type | Description |
|----|------|------|
| broker_cred | broker_ls_overseas_stock | LS Securities Overseas Stock API |

## Data Flow

1. **start** (StartNode) --> **broker** (OverseasStockBrokerNode)
1. **broker** (OverseasStockBrokerNode) --> **watchlist** (WatchlistNode)
1. **broker** (OverseasStockBrokerNode) --> **account** (OverseasStockAccountNode)
1. **watchlist** (WatchlistNode) --> **filter** (SymbolFilterNode)
1. **account** (OverseasStockAccountNode) --> **filter** (SymbolFilterNode)
1. **filter** (SymbolFilterNode) --> **market** (OverseasStockMarketDataNode)

## How to Run

```python
from programgarden import ProgramGarden

pg = ProgramGarden()
job = await pg.run_async(workflow)
```
