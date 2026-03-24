---
category: node_reference
tags: [node, category, selection, guide]
priority: critical
---

# Node Category Overview and Selection Guide

## What is a Node?

A Node is a block responsible for a single function in a workflow. Nodes are connected by edges to create automated trading strategies. ProgramGarden has 12 categories and 72 nodes.

## 12 Category Summary

| Category | Node Count | Purpose | Key Nodes |
|----------|-----------|---------|-----------|
| `infra` | 8 | Start/connection/flow control/conditional branching | StartNode, OverseasStockBrokerNode, OverseasFuturesBrokerNode, KoreaStockBrokerNode, ThrottleNode, SplitNode, AggregateNode, IfNode |
| `account` | 12 | Account balance/positions/open orders | AccountNode, OpenOrdersNode, RealAccountNode, RealOrderEventNode (overseas stock/futures + korea stock) |
| `market` | 22 | Quotes/symbols/historical data/fundamentals/exchange rates/sentiment/exclusion list | MarketDataNode, HistoricalDataNode, RealMarketDataNode, FundamentalNode, WatchlistNode, ScreenerNode, ExclusionListNode, CurrencyRateNode, FearGreedIndexNode, FundamentalDataNode, KoreaStock* |
| `condition` | 2 | Trading condition evaluation | ConditionNode, LogicNode |
| `order` | 10 | Order execution | NewOrderNode, ModifyOrderNode, CancelOrderNode, PositionSizingNode (overseas stock/futures + korea stock) |
| `risk` | 1 | Risk/portfolio | PortfolioNode |
| `schedule` | 2 | Schedule/trading hours | ScheduleNode, TradingHoursFilterNode |
| `data` | 4 | DB/API/field mapping/file parsing | SQLiteNode, HTTPRequestNode, FieldMappingNode, FileReaderNode |
| `display` | 6 | Charts/tables/summary | TableDisplayNode, LineChartNode, MultiLineChartNode, CandlestickChartNode, BarChartNode, SummaryDisplayNode |
| `analysis` | 2 | Backtesting/benchmark | BacktestEngineNode, BenchmarkCompareNode |
| `ai` | 2 | AI Agent | LLMModelNode, AIAgentNode |
| `messaging` | 1 | Notifications/messaging | TelegramNode |

## Product-Specific Node Names (Overseas Stocks vs Overseas Futures vs Korea Stocks)

Most nodes have different names per product:

| Function | Overseas Stocks | Overseas Futures | Korea Stocks |
|----------|----------------|-----------------|--------------|
| Broker connection | `OverseasStockBrokerNode` | `OverseasFuturesBrokerNode` | `KoreaStockBrokerNode` |
| Account query | `OverseasStockAccountNode` | `OverseasFuturesAccountNode` | `KoreaStockAccountNode` |
| Open orders | `OverseasStockOpenOrdersNode` | `OverseasFuturesOpenOrdersNode` | `KoreaStockOpenOrdersNode` |
| Current price | `OverseasStockMarketDataNode` | `OverseasFuturesMarketDataNode` | `KoreaStockMarketDataNode` |
| Historical data | `OverseasStockHistoricalDataNode` | `OverseasFuturesHistoricalDataNode` | `KoreaStockHistoricalDataNode` |
| Real-time quotes | `OverseasStockRealMarketDataNode` | `OverseasFuturesRealMarketDataNode` | `KoreaStockRealMarketDataNode` |
| Real-time account | `OverseasStockRealAccountNode` | `OverseasFuturesRealAccountNode` | `KoreaStockRealAccountNode` |
| Real-time orders | `OverseasStockRealOrderEventNode` | `OverseasFuturesRealOrderEventNode` | `KoreaStockRealOrderEventNode` |
| Symbol search | `OverseasStockSymbolQueryNode` | `OverseasFuturesSymbolQueryNode` | `KoreaStockSymbolQueryNode` |
| Symbol fundamentals | `OverseasStockFundamentalNode` | - | `KoreaStockFundamentalNode` |
| New order | `OverseasStockNewOrderNode` | `OverseasFuturesNewOrderNode` | `KoreaStockNewOrderNode` |
| Modify order | `OverseasStockModifyOrderNode` | `OverseasFuturesModifyOrderNode` | `KoreaStockModifyOrderNode` |
| Cancel order | `OverseasStockCancelOrderNode` | `OverseasFuturesCancelOrderNode` | `KoreaStockCancelOrderNode` |

Product-agnostic nodes (single name):
- `StartNode`, `ThrottleNode`, `SplitNode`, `AggregateNode`, `IfNode`
- `WatchlistNode`, `MarketUniverseNode`, `ScreenerNode`, `SymbolFilterNode`, `ExclusionListNode`
- `ConditionNode`, `LogicNode`
- `PositionSizingNode`, `PortfolioNode`
- `ScheduleNode`, `TradingHoursFilterNode`
- `SQLiteNode`, `HTTPRequestNode`, `FieldMappingNode`, `FileReaderNode`
- `TableDisplayNode`, `LineChartNode`, `MultiLineChartNode`, `CandlestickChartNode`, `BarChartNode`, `SummaryDisplayNode`
- `BacktestEngineNode`, `BenchmarkCompareNode`
- `LLMModelNode`, `AIAgentNode`

## Node Selection Guide

### "Which node should I use?"

| What You Want to Do | Node to Use |
|--------------------|------------|
| Connect to broker | `OverseasStockBrokerNode` or `OverseasFuturesBrokerNode` |
| Check balance/holdings | `AccountNode` (one-time) or `RealAccountNode` (real-time) |
| View current price | `MarketDataNode` (one-time) or `RealMarketDataNode` (real-time) |
| Historical chart data | `HistoricalDataNode` |
| Define symbol list | `WatchlistNode` (manual) or `MarketUniverseNode` (index constituents) |
| Symbol screening | `ScreenerNode` |
| Symbol fundamentals (PER/EPS etc.) | `OverseasStockFundamentalNode` |
| Conditional branching (if/else) | `IfNode` |
| RSI/MACD condition evaluation | `ConditionNode` + plugin |
| Combine multiple conditions | `LogicNode` |
| Buy/sell orders | `NewOrderNode` + order plugin |
| Calculate order quantity | `PositionSizingNode` |
| Periodic execution | `ScheduleNode` |
| Store data | `SQLiteNode` |
| External API call | `HTTPRequestNode` |
| Chart visualization | `LineChartNode`, `CandlestickChartNode`, etc. |
| Backtesting | `BacktestEngineNode` |
| AI analysis | `LLMModelNode` + `AIAgentNode` |

### Required vs Optional Nodes

| Required | Node | Reason |
|:--------:|------|--------|
| O | BrokerNode | Cannot access quotes/orders without broker connection |
| - | StartNode | Required when using ScheduleNode |
| - | ThrottleNode | Required when using real-time nodes |
| - | Others | Choose based on strategy |

## Symbol Data Format (Required Rule)

Symbol data must always use object arrays with `symbol` and `exchange` fields:

```json
[
  {"symbol": "AAPL", "exchange": "NASDAQ", "rsi": 28.5},
  {"symbol": "NVDA", "exchange": "NASDAQ", "rsi": 55.2}
]
```

Do not use symbols as dictionary keys:
```json
// Wrong format
{"AAPL": {"rsi": 28.5}}
```
