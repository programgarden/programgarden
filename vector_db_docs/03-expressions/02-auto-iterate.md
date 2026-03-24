---
category: expression
tags: [auto_iterate, item, index, total, split, aggregate]
priority: critical
---

# Auto-Iterate: Automatic Array Iteration

## Basic Behavior

When a node outputs an array, the next node automatically executes repeatedly for each item.

```
[AccountNode]        -> [ConditionNode]        -> [NewOrderNode]
  positions:             (executes 3 times)         (executes 3 times)
  [{AAPL}, {NVDA}, {TSM}]  | item = {AAPL}          | item = {AAPL}
                            | item = {NVDA}          | item = {NVDA}
                            | item = {TSM}           | item = {TSM}
```

## Iteration Keywords

Special keywords available during iteration:

| Keyword | Description | Example |
|---------|-------------|---------|
| `item` | Current iteration item | `{{ item.symbol }}` -> `"AAPL"` |
| `index` | Current index (0-based) | `{{ index }}` -> `0` |
| `total` | Total item count | `{{ total }}` -> `3` |

**Usage example:**

```json
{
  "id": "history",
  "type": "OverseasStockHistoricalDataNode",
  "symbol": "{{ item }}"
}
```

If WatchlistNode outputs 3 symbols, HistoricalDataNode executes 3 times, once for each symbol.

## Auto-Iterate vs SplitNode

| Feature | Auto-Iterate | SplitNode |
|---------|-------------|-----------|
| Usage | Automatic (no configuration needed) | Explicit node addition required |
| Parallel processing | Not available | `parallel: true` supported |
| Delay between items | Not available | `delay_ms` configurable |
| Error control | Not available | `continue_on_error` configurable |
| Recommended use | Simple iteration | When fine-grained control is needed |

## SplitNode + AggregateNode Pattern

Results split by SplitNode are collected back together with AggregateNode:

```json
{
  "nodes": [
    {"id": "watchlist", "type": "WatchlistNode",
     "symbols": [
       {"exchange": "NASDAQ", "symbol": "AAPL"},
       {"exchange": "NASDAQ", "symbol": "NVDA"},
       {"exchange": "NYSE", "symbol": "TSM"}
     ]},
    {"id": "split", "type": "SplitNode"},
    {"id": "history", "type": "OverseasStockHistoricalDataNode",
     "symbol": "{{ item }}", "interval": "1d"},
    {"id": "rsi", "type": "ConditionNode", "plugin": "RSI",
     "fields": {"period": 14, "threshold": 30, "direction": "below"}},
    {"id": "aggregate", "type": "AggregateNode",
     "mode": "filter", "filter_field": "passed"}
  ],
  "edges": [
    {"from": "watchlist", "to": "split"},
    {"from": "split", "to": "history"},
    {"from": "history", "to": "rsi"},
    {"from": "rsi", "to": "aggregate"}
  ]
}
```

**Flow:**
1. WatchlistNode -> Outputs 3 symbols
2. SplitNode -> Splits into individual items
3. HistoricalDataNode -> Fetches chart data for each symbol (3 times)
4. ConditionNode -> Evaluates RSI condition (3 times)
5. AggregateNode -> Collects only the symbols that passed the condition

## API Rate Limit Considerations

When there are many symbols, setting `parallel: true` may trigger broker API rate limits due to many simultaneous calls. For 10 or more symbols, `parallel: false` with `delay_ms: 500` is recommended.

```json
{
  "id": "split",
  "type": "SplitNode",
  "parallel": false,
  "delay_ms": 500,
  "continue_on_error": true
}
```
