---
category: node_reference
tags: [market, quote, real_market, historical, fundamental, per, eps]
priority: high
---

# Market Nodes: Current Price, Real-time Quotes, Historical Data, Fundamentals

## MarketDataNode (Current Price Query)

Queries the current day's price once via REST API.

| Product | Node Type |
|---------|----------|
| Overseas Stocks | `OverseasStockMarketDataNode` |
| Overseas Futures | `OverseasFuturesMarketDataNode` |

```json
{
  "id": "market",
  "type": "OverseasStockMarketDataNode",
  "symbol": "{{ item }}"
}
```

`symbol` specification: Use `"{{ item }}"` with SplitNode or directly `{"exchange": "NASDAQ", "symbol": "AAPL"}`

**Output**: `value` - Quote data

```json
{
  "symbol": "AAPL", "exchange": "NASDAQ",
  "price": 192.30, "change": 1.50, "change_pct": 0.79,
  "volume": 45123456,
  "open": 190.50, "high": 193.20, "low": 189.80, "close": 192.30
}
```

**MarketDataNode vs HistoricalDataNode**: MarketDataNode queries only today's current price (1 record). Technical indicators like RSI/MACD require N days of historical data, so use HistoricalDataNode.

## HistoricalDataNode (Historical Chart Query)

Queries N days of OHLCV (Open/High/Low/Close/Volume) data. Essential for technical indicator calculation.

| Product | Node Type |
|---------|----------|
| Overseas Stocks | `OverseasStockHistoricalDataNode` |
| Overseas Futures | `OverseasFuturesHistoricalDataNode` |

```json
{
  "id": "history",
  "type": "OverseasStockHistoricalDataNode",
  "symbol": "{{ item }}",
  "interval": "1d",
  "start_date": "{{ date.ago(90, format='yyyymmdd') }}",
  "end_date": "{{ date.today(format='yyyymmdd') }}"
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `symbol` | object | - | Symbol information |
| `interval` | string | `"1d"` | Data interval |
| `start_date` | string | 3 months ago | Start date (YYYYMMDD) |
| `end_date` | string | Today | End date (YYYYMMDD) |
| `adjust` | boolean | `false` | Whether to apply adjusted prices |

**interval Options:**

| Value | Interval | Use Case |
|-------|----------|----------|
| `1m` | 1-minute bars | Day trading/scalping |
| `5m` | 5-minute bars | Short-term trading |
| `15m` | 15-minute bars | Short-term trading |
| `1h` | 1-hour bars | Swing trading |
| `1d` | Daily bars | Most commonly used |
| `1w` | Weekly bars | Medium to long-term |
| `1M` | Monthly bars | Long-term |

**Output**: `value` - OHLCV array

```json
[
  {"date": "2025-01-10", "open": 190.0, "high": 193.5, "low": 189.2, "close": 192.3, "volume": 45000000}
]
```

**Note**: RSI 14-day calculation requires at least 14 days of data. Generally 90+ days recommended. Minute bars have limited queryable range (recent few days only).

## RealMarketDataNode (Real-time Quotes)

Receives real-time quotes via WebSocket. Data updates on every trade execution.

| Product | Node Type |
|---------|----------|
| Overseas Stocks | `OverseasStockRealMarketDataNode` |
| Overseas Futures | `OverseasFuturesRealMarketDataNode` |

```json
{
  "id": "realMarket",
  "type": "OverseasStockRealMarketDataNode",
  "symbol": "{{ item }}",
  "stay_connected": true
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `symbol` | object | - | Symbol |
| `stay_connected` | boolean | `true` | Whether to keep connection |

**Output**: `ohlcv_data` (OHLCV), `data` (full quote data)

**LS Securities US Stock Trading Hours (Korea Time):**

| Session | Winter | Summer (DST) |
|---------|--------|-------------|
| Day trading | 10:00~17:30 | 09:00~16:30 |
| Pre-market | 18:00~23:30 | 17:00~22:30 |
| Regular hours | 23:30~06:00 | 22:30~05:00 |
| After-hours | 06:00~09:30 | 05:00~08:30 |

**Note**: ThrottleNode is required when connecting order/AI nodes downstream of real-time nodes.

## FundamentalNode (Symbol Fundamental Query)

Queries fundamental data such as PER, EPS, market cap, 52-week high/low via LS Securities g3104 API. **Overseas stocks only** (futures are derivatives with no fundamental concept).

| Product | Node Type |
|---------|----------|
| Overseas Stocks | `OverseasStockFundamentalNode` |
| Overseas Futures | - (not supported) |

```json
{
  "id": "fundamental",
  "type": "OverseasStockFundamentalNode",
  "symbols": [
    {"exchange": "NASDAQ", "symbol": "AAPL"},
    {"exchange": "NASDAQ", "symbol": "MSFT"}
  ]
}
```

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `symbol` | object | - | Single symbol (`{exchange, symbol}`) |
| `symbols` | array | - | Multiple symbols array |

Specify either `symbol` or `symbols`. Use `"symbol": "{{ item }}"` when used with SplitNode.

**Output**: `value` / `values` - Fundamental data

```json
{
  "exchange": "NASDAQ",
  "symbol": "AAPL",
  "name": "APPLE INC",
  "industry": "Technology",
  "nation": "USA",
  "exchange_name": "NASDAQ",
  "current_price": 264.35,
  "volume": 45123456,
  "change_percent": 1.25,
  "per": 33.39,
  "eps": 7.9,
  "market_cap": 3869057094000,
  "shares_outstanding": 14681100000,
  "high_52w": 288.62,
  "low_52w": 169.21,
  "exchange_rate": 1443.1
}
```

| Output Field | Type | Description |
|-------------|------|-------------|
| `exchange` | string | Exchange code |
| `symbol` | string | Symbol code |
| `name` | string | English symbol name |
| `industry` | string | Industry name |
| `nation` | string | Country name |
| `exchange_name` | string | Exchange name |
| `current_price` | number | Current price |
| `volume` | number | Trading volume |
| `change_percent` | number | Change rate (%) |
| `per` | number | PER (Price-to-Earnings Ratio) |
| `eps` | number | EPS (Earnings Per Share) |
| `market_cap` | number | Market capitalization |
| `shares_outstanding` | number | Outstanding shares |
| `high_52w` | number | 52-week high |
| `low_52w` | number | 52-week low |
| `exchange_rate` | number | Exchange rate |

**MarketDataNode vs FundamentalNode**: MarketDataNode focuses on quotes (price/change) and also includes PER/EPS. FundamentalNode additionally provides market cap, industry, 52-week high/low, outstanding shares, and other symbol information.

**AI Agent Tool**: Since `is_tool_enabled = true`, it can be called directly as a tool from AIAgentNode.
