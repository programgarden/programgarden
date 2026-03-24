---
category: workflow_example
tags: [example, strategy, rsi, full_pipeline, watchlist, historical, condition, sizing, order, table, end_to_end]
priority: critical
---

# Example: Full Strategy (RSI Trading)

## Overview

A comprehensive example implementing the entire trading pipeline from watchlist → historical data → RSI condition → position sizing → order execution. This pattern is the core structure of ProgramGarden workflows.

## Full Workflow

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
        {"symbol": "AAPL", "exchange": "NASDAQ"},
        {"symbol": "MSFT", "exchange": "NASDAQ"},
        {"symbol": "NVDA", "exchange": "NASDAQ"},
        {"symbol": "GOOGL", "exchange": "NASDAQ"},
        {"symbol": "AMZN", "exchange": "NASDAQ"}
      ]
    },
    {
      "id": "historical",
      "type": "OverseasStockHistoricalDataNode",
      "symbol": "{{ item }}",
      "interval": "1d",
      "start_date": "{{ date.ago(30, format='yyyymmdd') }}",
      "end_date": "{{ date.today(format='yyyymmdd') }}"
    },
    {
      "id": "rsi_condition",
      "type": "ConditionNode",
      "plugin": "RSI",
      "items": {
        "from": "{{ nodes.historical.value.time_series }}",
        "extract": {
          "symbol": "{{ nodes.historical.value.symbol }}",
          "exchange": "{{ nodes.historical.value.exchange }}",
          "date": "{{ row.date }}",
          "close": "{{ row.close }}"
        }
      },
      "fields": {"period": 14, "threshold": 30, "direction": "below"}
    },
    {
      "id": "market",
      "type": "OverseasStockMarketDataNode",
      "symbol": "{{ item }}"
    },
    {
      "id": "logic",
      "type": "LogicNode",
      "operator": "all",
      "conditions": [
        {
          "is_condition_met": "{{ nodes.rsi_condition.result }}",
          "passed_symbols": "{{ nodes.rsi_condition.passed_symbols }}"
        }
      ]
    },
    {
      "id": "sizing",
      "type": "PositionSizingNode",
      "symbol": "{{ nodes.logic.passed_symbols }}",
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
    },
    {
      "id": "table",
      "type": "TableDisplayNode",
      "title": "RSI Oversold Symbols",
      "data": "{{ nodes.rsi_condition.symbol_results }}",
      "columns": ["symbol", "exchange", "rsi", "current_price"],
      "limit": 10,
      "sort_by": "rsi",
      "sort_order": "asc"
    }
  ],
  "edges": [
    {"from": "start", "to": "broker"},
    {"from": "broker", "to": "account"},
    {"from": "watchlist", "to": "historical"},
    {"from": "watchlist", "to": "market"},
    {"from": "historical", "to": "rsi_condition"},
    {"from": "rsi_condition", "to": "logic"},
    {"from": "account", "to": "sizing"},
    {"from": "logic", "to": "sizing"},
    {"from": "market", "to": "sizing"},
    {"from": "sizing", "to": "new_order"},
    {"from": "rsi_condition", "to": "table"}
  ],
  "credentials": [{"credential_id": "broker-cred"}]
}
```

## DAG Structure

```
start → broker → account ──────────────────────→ sizing → new_order
                                                    ↑        ↑
                 watchlist → historical → rsi_condition → logic ─┘
                          → market ──────────────────────────────┘

                            rsi_condition → table
```

## Step-by-Step Explanation

### Step 1: Infrastructure Setup

```
StartNode → BrokerNode → AccountNode
```

- Connects to the LS Securities API and queries account balance
- `AccountNode`'s `balance` is used for position sizing later

### Step 2: Data Collection

```
WatchlistNode → HistoricalDataNode (auto-iterate, 5 symbols)
             → MarketDataNode (auto-iterate, 5 symbols)
```

- Simultaneously queries 30-day historical data and current market prices for 5 watchlist symbols
- Iterates through each symbol using `{{ item }}`

### Step 3: Condition Evaluation

```
HistoricalDataNode → ConditionNode (RSI) → LogicNode
```

- Calculates 14-day RSI and determines oversold status (RSI < 30)
- Oversold condition set via `fields` with `threshold: 30`, `direction: "below"`
- `LogicNode` performs final confirmation of condition pass/fail

### Step 4: Order Execution

```
AccountNode ──→ PositionSizingNode → NewOrderNode
LogicNode ────→
MarketDataNode →
```

- Calculates order quantity as 10% of available balance
- Places limit buy orders for symbols that passed the condition

### Step 5: Result Display

```
ConditionNode → TableDisplayNode
```

- Displays RSI oversold symbols in a table sorted by RSI in ascending order
- Branching structure: condition evaluation and display proceed in parallel

## Key Pattern Summary

| Pattern | Usage |
|------|-----------|
| **Broker auto-propagation** | BrokerNode → AccountNode, MarketDataNode |
| **auto-iterate** | WatchlistNode → HistoricalDataNode, MarketDataNode |
| **items { from, extract }** | Converting historical data time series in ConditionNode |
| **DAG branching** | WatchlistNode → HistoricalDataNode, MarketDataNode (parallel) |
| **DAG merging** | ConditionNode → LogicNode → PositionSizingNode |
| **Data binding** | `{{ nodes.account.balance }}` |
| **Date functions** | `{{ date.ago(30, format='yyyymmdd') }}` |

## Extension Patterns

### Adding a Schedule

Replace StartNode with ScheduleNode for periodic automated trading:

```json
{
  "id": "schedule",
  "type": "ScheduleNode",
  "cron": "*/30 9-16 * * 1-5",
  "timezone": "America/New_York"
}
```

### Adding Compound Conditions

Triple condition with RSI + MACD + BollingerBands:

```json
{
  "id": "logic",
  "type": "LogicNode",
  "operator": "at_least",
  "threshold": 2,
  "conditions": [
    {
      "is_condition_met": "{{ nodes.rsi_condition.result }}",
      "passed_symbols": "{{ nodes.rsi_condition.passed_symbols }}"
    },
    {
      "is_condition_met": "{{ nodes.macd_condition.result }}",
      "passed_symbols": "{{ nodes.macd_condition.passed_symbols }}"
    },
    {
      "is_condition_met": "{{ nodes.bb_condition.result }}",
      "passed_symbols": "{{ nodes.bb_condition.passed_symbols }}"
    }
  ]
}
```

Buy signal when at least 2 out of 3 conditions are met.
