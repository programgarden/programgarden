---
category: appendix
tags: [reference, node, quick, all, 72_nodes, category, lookup]
priority: high
---

# 72 Nodes Quick Reference

## infra (Infrastructure)

| Node | Description | Required Fields | Key Outputs |
|------|-------------|-----------------|-------------|
| `StartNode` | Workflow starting point | - | - |
| `ThrottleNode` | Execution frequency control | `mode`, `interval_ms` | - |
| `SplitNode` | Splits an array into individual items | `data` | `item` |
| `AggregateNode` | Collects split results into an array | `data` | `items` |
| `OverseasStockBrokerNode` | LS Securities overseas stock API connection | `credential_id` | connection |
| `OverseasFuturesBrokerNode` | LS Securities overseas futures API connection | `credential_id`, `paper_trading` | connection |
| `KoreaStockBrokerNode` | LS Securities Korea stock API connection | `credential_id` | connection |
| `IfNode` | Conditional branching (if/else) | `left`, `operator`, `right` | `true`, `false`, `result` |

## account (Account)

| Node | Description | Required Fields | Key Outputs |
|------|-------------|-----------------|-------------|
| `OverseasStockAccountNode` | Overseas stock balance/position query | - | `balance`, `positions` |
| `OverseasFuturesAccountNode` | Overseas futures balance/position query | - | `balance`, `positions` |
| `OverseasStockOpenOrdersNode` | Overseas stock open orders query | - | `orders` |
| `OverseasFuturesOpenOrdersNode` | Overseas futures open orders query | - | `orders` |
| `OverseasStockRealAccountNode` | Overseas stock realtime balance | - | `balance`, `positions` |
| `OverseasFuturesRealAccountNode` | Overseas futures realtime balance | - | `balance`, `positions` |
| `OverseasStockRealOrderEventNode` | Overseas stock realtime fill events | - | `event` |
| `OverseasFuturesRealOrderEventNode` | Overseas futures realtime fill events | - | `event` |
| `KoreaStockAccountNode` | Korea stock balance/position query | - | `balance`, `positions` |
| `KoreaStockOpenOrdersNode` | Korea stock open orders query | - | `orders` |
| `KoreaStockRealAccountNode` | Korea stock realtime balance | - | `balance`, `positions` |
| `KoreaStockRealOrderEventNode` | Korea stock realtime fill events | - | `event` |

## market (Market Data)

| Node | Description | Required Fields | Key Outputs |
|------|-------------|-----------------|-------------|
| `OverseasStockMarketDataNode` | Overseas stock market data query | `symbol` or `symbols` | `value`, `values` |
| `OverseasFuturesMarketDataNode` | Overseas futures market data query | `symbol` or `symbols` | `value`, `values` |
| `OverseasStockRealMarketDataNode` | Overseas stock realtime market data | `symbols` | `value` |
| `OverseasFuturesRealMarketDataNode` | Overseas futures realtime market data | `symbols` | `value` |
| `OverseasStockHistoricalDataNode` | Overseas stock historical data | `symbol`, `start_date`, `end_date` | `value`, `values` |
| `OverseasFuturesHistoricalDataNode` | Overseas futures historical data | `symbol`, `start_date`, `end_date` | `value`, `values` |
| `OverseasStockSymbolQueryNode` | Overseas stock symbol search | `query` | `results` |
| `OverseasFuturesSymbolQueryNode` | Overseas futures symbol search | `query` | `results` |
| `WatchlistNode` | Watchlist management | `symbols` | `symbols` |
| `MarketUniverseNode` | Market symbol pool | `market`, `sector` | `symbols` |
| `ScreenerNode` | Criteria-based screening | `criteria` | `symbols` |
| `SymbolFilterNode` | Symbol list filtering | `symbols`, `filter` | `symbols` |
| `ExclusionListNode` | Trade exclusion list management | `symbols`, `dynamic_symbols`, `input_symbols`, `default_reason` | `excluded`, `filtered`, `count`, `reasons` |
| `OverseasStockFundamentalNode` | Overseas stock fundamentals (PER/EPS/market cap) | `symbol` or `symbols` | `value`, `values` |
| `CurrencyRateNode` | Exchange rate query (no credential required) | `base_currency`, `target_currencies` | `rates`, `krw_rate` |
| `FearGreedIndexNode` | CNN Fear & Greed Index (no credential required) | - | `value`, `label` |
| `FundamentalDataNode` | Financial data (FMP API, credential required) | `symbol`, `data_type` | `profile`, `income`, `balance`, `metrics` |
| `KoreaStockMarketDataNode` | Korea stock market data query | `symbol` or `symbols` | `value`, `values` |
| `KoreaStockFundamentalNode` | Korea stock fundamentals (PER/EPS/market cap) | `symbol` or `symbols` | `value`, `values` |
| `KoreaStockHistoricalDataNode` | Korea stock historical data | `symbol`, `start_date`, `end_date` | `value`, `values` |
| `KoreaStockSymbolQueryNode` | Korea stock symbol search | `query` | `results` |
| `KoreaStockRealMarketDataNode` | Korea stock realtime market data | `symbols` | `value` |

## condition (Condition)

| Node | Description | Required Fields | Key Outputs |
|------|-------------|-----------------|-------------|
| `ConditionNode` | Condition evaluation (plugin-based) | `plugin`, `items`, `fields` | `result` |
| `LogicNode` | Logic combination (8 operators) | `operator`, `conditions` | `result`, `passed_symbols` |

## order (Order)

| Node | Description | Required Fields | Key Outputs |
|------|-------------|-----------------|-------------|
| `OverseasStockNewOrderNode` | Overseas stock new order | `side`, `order_type`, `order` | `result` |
| `OverseasStockModifyOrderNode` | Overseas stock order modification | `order_id`, `price`/`quantity` | `result` |
| `OverseasStockCancelOrderNode` | Overseas stock order cancellation | `order_id` | `result` |
| `OverseasFuturesNewOrderNode` | Overseas futures new order | `side`, `order_type`, `order` | `result` |
| `OverseasFuturesModifyOrderNode` | Overseas futures order modification | `order_id`, `price`/`quantity` | `result` |
| `OverseasFuturesCancelOrderNode` | Overseas futures order cancellation | `order_id` | `result` |
| `PositionSizingNode` | Order quantity calculation | `symbol`, `balance`, `market_data`, `method` | `order`, `calculation` |
| `KoreaStockNewOrderNode` | Korea stock new order | `side`, `order_type`, `order` | `result` |
| `KoreaStockModifyOrderNode` | Korea stock order modification | `order_id`, `price`/`quantity` | `result` |
| `KoreaStockCancelOrderNode` | Korea stock order cancellation | `order_id` | `result` |

## risk (Risk)

| Node | Description | Required Fields | Key Outputs |
|------|-------------|-----------------|-------------|
| `PortfolioNode` | Portfolio management | - | `portfolio` |

## schedule (Schedule)

| Node | Description | Required Fields | Key Outputs |
|------|-------------|-----------------|-------------|
| `ScheduleNode` | Cron-based periodic trigger | `cron`, `timezone` | - |
| `TradingHoursFilterNode` | Trading hours filter | `start`, `end`, `timezone` | `passed`, `blocked` |

## data (Data)

| Node | Description | Required Fields | Key Outputs |
|------|-------------|-----------------|-------------|
| `SQLiteNode` | SQLite query execution | `query` | `rows` |
| `HTTPRequestNode` | HTTP API call | `method`, `url` | `response` |
| `FieldMappingNode` | Data field transformation | `data`, `mappings` | `data` |
| `FileReaderNode` | File parsing (PDF, TXT, CSV, JSON, MD, DOCX, XLSX) | `file_paths` or `file_data_list` | `texts`, `data_list`, `metadata` |

## display (Display)

| Node | Description | Required Fields | Key Outputs |
|------|-------------|-----------------|-------------|
| `TableDisplayNode` | Table display | `title`, `data` | display_data |
| `LineChartNode` | Line chart | `title`, `data` | display_data |
| `MultiLineChartNode` | Multi-line chart | `title`, `data` | display_data |
| `CandlestickChartNode` | Candlestick chart | `title`, `data` | display_data |
| `BarChartNode` | Bar chart | `title`, `data` | display_data |
| `SummaryDisplayNode` | Summary card | `title`, `data` | display_data |

## analysis (Analysis)

| Node | Description | Required Fields | Key Outputs |
|------|-------------|-----------------|-------------|
| `BacktestEngineNode` | Backtest execution | `strategy`, `data` | `results` |
| `BenchmarkCompareNode` | Benchmark comparison | `portfolio`, `benchmark` | `comparison` |

## ai (AI)

| Node | Description | Required Fields | Key Outputs |
|------|-------------|-----------------|-------------|
| `LLMModelNode` | LLM API connection | `credential_id`, `model` | connection (ai_model edge) |
| `AIAgentNode` | AI agent execution | `preset`/`system_prompt`, `user_prompt` | `response` |

## Node Selection Guide

| What You Want to Do | Node to Use |
|---------------------|-------------|
| Query account balance | `OverseasStock/Futures/KoreaStockAccountNode` |
| Query current market data | `OverseasStock/Futures/KoreaStockMarketDataNode` |
| Query historical data | `OverseasStock/Futures/KoreaStockHistoricalDataNode` |
| Stock fundamentals (PER/EPS, etc.) | `OverseasStock/KoreaStockFundamentalNode` |
| Manage watchlist | `WatchlistNode` |
| Conditional branching (if/else) | `IfNode` |
| Technical analysis | `ConditionNode` + plugin |
| Compound conditions | `LogicNode` |
| Calculate order quantity | `PositionSizingNode` |
| Place buy/sell orders | `OverseasStock/Futures/KoreaStockNewOrderNode` |
| Periodic execution | `ScheduleNode` |
| Trading hours filter | `TradingHoursFilterNode` |
| External API calls | `HTTPRequestNode` |
| AI analysis | `LLMModelNode` + `AIAgentNode` |
| Display results | `TableDisplayNode`, `LineChartNode`, etc. |
