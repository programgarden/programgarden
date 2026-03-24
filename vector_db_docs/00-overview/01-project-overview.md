---
category: overview
tags: [introduction, platform, no-code, trading]
priority: high
---

# ProgramGarden Project Overview

## What is ProgramGarden?

ProgramGarden is an open-source DSL (Domain Specific Language) platform for designing automated trading strategies for overseas stocks, futures, and Korea stocks using a **node-based workflow**. It integrates with LS Securities OpenAPI to automatically execute actual trades without coding.

## Core Concepts

- **Node**: A block responsible for a single function (price lookup, condition evaluation, order placement, etc.)
- **Edge**: A connection line between nodes that defines execution order
- **Workflow**: An automated trading strategy combining nodes and edges, represented in JSON

## Key Features

| Feature | Description |
|---------|-------------|
| 72 Nodes | From price lookup, fundamental analysis, conditional branching, orders, risk management to chart visualization |
| 67 Strategy Plugins | Ready-to-use strategies: RSI, MACD, Bollinger Bands, Ichimoku, VWAP, Dual Momentum, Correlation Analysis, Regime Detection, Z-Score, Squeeze Momentum, Momentum Ranking, Market Internals, Pair Trading, Turtle Breakout, Volatility Breakout, Magic Formula, Support/Resistance Levels, Level Touch, Kelly Criterion, Risk Parity, VaR/CVaR, Dynamic Stop Loss, etc. |
| Real-time Monitoring | Receive real-time quotes/account/order events via WebSocket |
| Backtesting | Validate strategies with historical data and compare against benchmarks |
| AI Agent | LLMs like GPT/Claude analyze markets and support decision-making |
| Overseas Stocks + Futures + Korean Stocks | All three product types supported. Korean stock Finance API (69 TRs) available |
| Dynamic Node Injection | Extend by injecting custom nodes at runtime |

## Supported Products

| Product | Live Trading | Paper Trading | Note |
|---------|:----------:|:------------:|------|
| Overseas Stocks | O | O | LS Securities |
| Overseas Futures | O | O | LS Securities |
| Korean Stocks | O | - | LS Securities (Finance API only, workflow nodes in progress) |

## How Workflows Work

Create strategies by connecting nodes:

```
[Broker Connection] → [Symbol Selection] → [Historical Data] → [RSI Condition] → [Market Order]
```

All configurations are represented in JSON:

```json
{
  "nodes": [
    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "my-cred"},
    {"id": "watchlist", "type": "WatchlistNode", "symbols": [{"exchange": "NASDAQ", "symbol": "AAPL"}]},
    {"id": "history", "type": "OverseasStockHistoricalDataNode", "interval": "1d"},
    {"id": "rsi", "type": "ConditionNode", "plugin": "RSI",
     "items": {"from": "{{ nodes.history.value.time_series }}", "extract": {"symbol": "{{ nodes.history.value.symbol }}", "exchange": "{{ nodes.history.value.exchange }}", "date": "{{ row.date }}", "close": "{{ row.close }}"}},
     "fields": {"period": 14, "threshold": 30, "direction": "below"}},
    {"id": "order", "type": "OverseasStockNewOrderNode", "plugin": "MarketOrder", "fields": {"side": "buy"}}
  ],
  "edges": [
    {"from": "broker", "to": "watchlist"},
    {"from": "watchlist", "to": "history"},
    {"from": "history", "to": "rsi"},
    {"from": "rsi", "to": "order"}
  ],
  "credentials": [
    {
      "credential_id": "my-cred",
      "type": "broker_ls_overseas_stock",
      "data": [
        {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
        {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"}
      ]
    }
  ]
}
```

## Node Categories (12 categories, 72 nodes)

| Category | Purpose | Representative Nodes |
|----------|---------|---------------------|
| `infra` | Workflow start, broker connection, flow control, conditional branching | StartNode, BrokerNode, ThrottleNode, IfNode |
| `account` | Balance, positions, open orders | AccountNode, OpenOrdersNode |
| `market` | Quotes, symbols, historical data, fundamentals, exchange rates, sentiment, exclusion list | WatchlistNode, MarketDataNode, FundamentalNode, ExclusionListNode, CurrencyRateNode, FearGreedIndexNode, FundamentalDataNode |
| `condition` | Trading condition evaluation, logic combinations | ConditionNode, LogicNode |
| `order` | New/modify/cancel orders | NewOrderNode, ModifyOrderNode, CancelOrderNode, PositionSizingNode |
| `risk` | Portfolio allocation, rebalancing | PortfolioNode |
| `schedule` | Schedule triggers, trading hours filter | ScheduleNode, TradingHoursFilterNode |
| `data` | DB, external API, field mapping, file parsing | SQLiteNode, HTTPRequestNode, FieldMappingNode, FileReaderNode |
| `display` | Charts, tables, summary visualization | TableDisplayNode, LineChartNode, CandlestickChartNode |
| `analysis` | Backtesting, benchmark comparison | BacktestEngineNode, BenchmarkCompareNode |
| `ai` | AI Agent | LLMModelNode, AIAgentNode |
| `messaging` | Notifications/messaging | TelegramNode |

## Usage Flow

1. Open an LS Securities account and obtain OpenAPI app keys
2. Write workflow JSON (nodes + edges + credentials)
3. Execute with WorkflowExecutor (FastAPI server or direct call)
4. Operates automatically based on schedule or real-time events
