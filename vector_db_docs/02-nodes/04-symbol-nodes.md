---
category: node_reference
tags: [symbol, watchlist, universe, screener, filter]
priority: high
---

# Symbol Management Nodes: Watchlist, Universe, Screener, Filter

## WatchlistNode (Watchlist)

A user-defined list of symbols of interest.

```json
{
  "id": "watchlist",
  "type": "WatchlistNode",
  "symbols": [
    {"exchange": "NASDAQ", "symbol": "AAPL"},
    {"exchange": "NASDAQ", "symbol": "NVDA"},
    {"exchange": "NYSE", "symbol": "TSM"}
  ]
}
```

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `symbols` | array | O | Symbol list (`{exchange, symbol}` array) |

**Output**: `symbols` - Symbol list

**Exchange Codes:**

| Exchange | Code | Examples |
|----------|------|----------|
| NASDAQ | `NASDAQ` | AAPL, NVDA, TSLA, MSFT |
| New York Stock Exchange | `NYSE` | TSM, JPM, V, WMT |
| AMEX | `AMEX` | SPY, QQQ, GLD |

**Note**: Both `exchange` and `symbol` must be specified together. Symbol code alone is not valid.

## SymbolQueryNode (Symbol Search)

Searches symbols by code or name.

| Product | Node Type |
|---------|----------|
| Overseas Stocks | `OverseasStockSymbolQueryNode` |
| Overseas Futures | `OverseasFuturesSymbolQueryNode` |

```json
{"id": "query", "type": "OverseasStockSymbolQueryNode", "keyword": "AAPL"}
```

**Output**: `symbols` - Search result symbol list

## MarketUniverseNode (Index Constituents)

Automatically fetches constituents of major indices like NASDAQ 100, S&P 500. Overseas stocks only, no broker connection required.

```json
{"id": "universe", "type": "MarketUniverseNode", "universe": "NASDAQ100"}
```

| universe | Symbol Count | Description |
|----------|-------------|-------------|
| `NASDAQ100` | ~101 | NASDAQ large-cap top 100 |
| `SP500` | ~503 | S&P 500 |
| `SP100` | ~100 | S&P 100 (large-cap) |
| `DOW30` | 30 | Dow Jones Industrial Average |

**Output**: `symbols` (symbol list), `count` (symbol count)

## ScreenerNode (Symbol Screening)

Filters symbols by conditions such as market cap, volume, sector. Overseas stocks only, no broker connection required.

```json
{
  "id": "screener",
  "type": "ScreenerNode",
  "market_cap_min": 100000000000,
  "volume_min": 1000000,
  "sector": "Technology",
  "exchange": "NASDAQ",
  "max_results": 10
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `symbols` | array | - | Input symbols (all if unspecified) |
| `market_cap_min` | number | - | Minimum market cap (USD) |
| `market_cap_max` | number | - | Maximum market cap |
| `volume_min` | number | - | Minimum volume |
| `sector` | string | - | Sector (Technology, Healthcare, etc.) |
| `exchange` | string | - | Exchange |
| `max_results` | number | `100` | Maximum results (1~500) |

**Output**: `symbols` (matching symbols), `count` (result count)

## ExclusionListNode (Trading Exclusion List)

Manages symbols to exclude from trading. Combines manual input (`symbols`) and dynamic binding (`dynamic_symbols`), and automatically filters when `input_symbols` is connected.

```json
{
  "id": "exclusion",
  "type": "ExclusionListNode",
  "symbols": [
    {"exchange": "NASDAQ", "symbol": "NVDA", "reason": "Excessive volatility"},
    {"exchange": "NYSE", "symbol": "BA", "reason": "Incident risk"}
  ],
  "default_reason": "Risk management",
  "input_symbols": "{{ nodes.watchlist.symbols }}"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `symbols` | array | Manual exclusion symbols `[{exchange, symbol, reason}]` |
| `dynamic_symbols` | expression | Dynamic exclusion symbol binding |
| `input_symbols` | expression | Original symbol list to filter |
| `default_reason` | string | Default reason when none specified |

**Output**: `excluded` (excluded symbols), `filtered` (filtered results), `count` (exclusion count), `reasons` (per-symbol reasons)

**Order Safety**: When ExclusionListNode exists in a workflow, NewOrderNode automatically blocks orders for excluded symbols.

## SymbolFilterNode (Symbol Set Operations)

Performs set operations by comparing two symbol lists.

```json
{
  "id": "filter",
  "type": "SymbolFilterNode",
  "operation": "difference",
  "input_a": "{{ nodes.universe.symbols }}",
  "input_b": "{{ nodes.account.held_symbols }}"
}
```

| operation | Meaning | Practical Example |
|-----------|---------|-------------------|
| `difference` | Only in A (A-B) | Unheld symbols from NASDAQ 100 |
| `intersection` | In both A and B | Held symbols from watchlist |
| `union` | Combine A + B | Merge two lists (deduplicated) |

**Output**: `symbols` (result), `count` (count)

**Usage Pattern - Buy only unheld symbols:**
```
MarketUniverseNode ──┐
                     ├──▶ SymbolFilterNode (difference) ──▶ Buy logic
AccountNode ─────────┘
```
