# Korea Stock RSI Oversold Buy Order

Samsung Electronics (005930) daily RSI(14) oversold signal → live KRX quote → PositionSizing (5% of orderable cash) → KoreaStockNewOrderNode limit buy. Korea stocks do NOT support paper trading — orders hit the real account immediately.

## Workflow Structure

```mermaid
graph LR
    start(["Start"])
    broker(["Broker
(Korea Stock)"])
    account["Account
(Korea Stock)"]
    split["Split"]
    historical["Historical
(Korea Stock)"]
    rsi_cond{"Condition
(RSI)"}
    market["MarketData
(Korea Stock)"]
    sizing["PositionSizing"]
    order["NewOrder
(Korea Stock)"]
    order_table[/"TableDisplay"/]
    start --> broker
    broker --> account
    broker --> split
    split --> historical
    broker --> historical
    historical --> rsi_cond
    split --> market
    broker --> market
    rsi_cond --> sizing
    market --> sizing
    account --> sizing
    sizing --> order
    broker --> order
    order --> order_table
```

## Node List

| ID | Type | Description |
|----|------|------|
| start | StartNode | Workflow start |
| broker | KoreaStockBrokerNode | Korea stock broker connection (real account only) |
| account | KoreaStockAccountNode | Orderable cash / positions |
| split | SplitNode | Emit single symbol item {symbol: 005930} |
| historical | KoreaStockHistoricalDataNode | 60-day adjusted daily OHLCV |
| rsi_cond | ConditionNode (RSI) | RSI(14) < 30 oversold filter → passed_symbols |
| market | KoreaStockMarketDataNode | Live KRX quote (current price) for sizing |
| sizing | PositionSizingNode | fixed_percent 5% of orderable cash → order dict |
| order | KoreaStockNewOrderNode | Limit buy (side=buy, order_type=limit) |
| order_table | TableDisplayNode | Order execution audit log |

## Required Credentials

| ID | Type | Description |
|----|------|------|
| kr_broker_cred | broker_ls_korea_stock | LS Securities Korea Stock API (real account) |

## Notes

- **No paper trading**: KoreaStockBrokerNode is real-market only. To study the flow without executing, drop the `order` node and inspect `rsi_cond` via a display node.
- The `order` dict for Korea stocks uses `{symbol, quantity, price?}` — no exchange field.
- Retry stays disabled by default to prevent duplicate KRW-denominated orders.
