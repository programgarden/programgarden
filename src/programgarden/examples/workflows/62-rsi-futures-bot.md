# RSI Oversold Overseas Futures Auto-Trading (Paper Trading)

HKEX mini futures RSI(14) oversold (<=30) long entry, liquidate held positions every cycle. 1-min interval paper trading.

> ## RSI Oversold Overseas Futures Bot (Paper Trading)

**Strategy**: RSI(14) oversold mean reversion

**Buy (Long)**: RSI < 30 oversold symbols
  -> Long 1 contract for non-held symbols only

**Liquidate**: Close all held positions with opposite trade

**Interval**: Every 1 min (no TradingHoursFilter)

**Symbols**: HMHJ26 (Mini Hang Seng Apr), HMCEJ26 (Mini H-Shares 

## Workflow Structure

```mermaid
graph LR
    start(["Start"])
    broker(["Broker
(Overseas Futures)"])
    schedule{{"Schedule"}}
    account["Account
(Overseas Futures)"]
    watchlist["Watchlist"]
    historical["Historical
(Overseas Futures)"]
    rsi{"Condition
(RSI)"}
    filter_buy["SymbolFilter"]
    buy_order[["NewOrder
(Overseas Futures)"]]
    account_sell["Account
(Overseas Futures)"]
    sell_order[["NewOrder
(Overseas Futures)"]]
    start --> broker
    broker --> schedule
    schedule --> account
    schedule --> watchlist
    watchlist --> historical
    historical --> rsi
    rsi --> filter_buy
    account --> filter_buy
    filter_buy --> buy_order
    schedule --> account_sell
    account_sell --> sell_order
```

## Node List

| ID | Type | Description |
|----|------|------|
| start | StartNode | Workflow start |
| broker | OverseasFuturesBrokerNode | Overseas futures broker connection (paper trading, HKEX) |
| schedule | ScheduleNode | Schedule trigger (cron) |
| account | OverseasFuturesAccountNode | Overseas futures account balance/position query |
| watchlist | WatchlistNode | Define watchlist symbols |
| historical | OverseasFuturesHistoricalDataNode | Overseas futures historical data query |
| rsi | ConditionNode | Condition check (plugin-based) |
| filter_buy | SymbolFilterNode | Symbol filter (intersection/difference/union) |
| buy_order | OverseasFuturesNewOrderNode | Overseas futures new order |
| account_sell | OverseasFuturesAccountNode | Overseas futures account balance/position query |
| sell_order | OverseasFuturesNewOrderNode | Overseas futures new order |

## Key Settings

- **broker**: Paper trading mode
- **schedule**: cron `*/1 * * * *` (timezone: Asia/Hong_Kong)
- **watchlist**: HMHJ26, HMCEJ26
- **rsi**: Plugin `RSI`
- **rsi**: period=14, threshold=30, direction=below
- **buy_order**: side=`buy`
- **sell_order**: side=`{{ item.close_side }}`

## Required Credentials

| ID | Type | Description |
|----|------|------|
| broker_cred | broker_ls_overseas_futures | LS Securities Overseas Futures API (paper trading, HKEX only) |

## Data Flow

1. **start** (StartNode) --> **broker** (OverseasFuturesBrokerNode)
1. **broker** (OverseasFuturesBrokerNode) --> **schedule** (ScheduleNode)
1. **schedule** (ScheduleNode) --> **account** (OverseasFuturesAccountNode)
1. **schedule** (ScheduleNode) --> **watchlist** (WatchlistNode)
1. **watchlist** (WatchlistNode) --> **historical** (OverseasFuturesHistoricalDataNode)
1. **historical** (OverseasFuturesHistoricalDataNode) --> **rsi** (ConditionNode)
1. **rsi** (ConditionNode) --> **filter_buy** (SymbolFilterNode)
1. **account** (OverseasFuturesAccountNode) --> **filter_buy** (SymbolFilterNode)
1. **filter_buy** (SymbolFilterNode) --> **buy_order** (OverseasFuturesNewOrderNode)
1. **schedule** (ScheduleNode) --> **account_sell** (OverseasFuturesAccountNode)
1. **account_sell** (OverseasFuturesAccountNode) --> **sell_order** (OverseasFuturesNewOrderNode)
