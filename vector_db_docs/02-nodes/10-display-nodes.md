---
category: node_reference
tags: [display, table, chart, summary]
priority: medium
---

# Display Nodes: Tables, Charts, Summary

Generates charts and tables. Data auto-refreshes when connected to real-time nodes.

## TableDisplayNode (Table)

Displays data in table format.

```json
{
  "id": "table",
  "type": "TableDisplayNode",
  "title": "Held Positions Status",
  "data": "{{ nodes.account.positions }}",
  "columns": ["symbol", "quantity", "buy_price", "current_price", "pnl_rate"],
  "limit": 20,
  "sort_by": "pnl_rate",
  "sort_order": "desc"
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `title` | string | - | Table title |
| `data` | expression | - | Data to display (array) |
| `columns` | array | All | Column list to display |
| `limit` | number | `10` | Maximum rows (1~100) |
| `sort_by` | string | - | Sort column |
| `sort_order` | string | `"desc"` | `"asc"` or `"desc"` |

## LineChartNode (Line Chart)

Displays time-series data as a line chart.

```json
{
  "id": "chart",
  "type": "LineChartNode",
  "title": "RSI Trend",
  "data": "{{ nodes.rsi.result.analysis }}",
  "x_field": "date",
  "y_field": "rsi"
}
```

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `title` | string | - | Chart title |
| `data` | expression | O | Chart data (array) |
| `x_field` | string | O | X-axis field name (usually `"date"`) |
| `y_field` | string | O | Y-axis field name |

**Note**: `x_field` and `y_field` must be explicitly specified.

## MultiLineChartNode (Multi-Line Chart)

Displays multiple series (symbols) in a single chart.

```json
{
  "id": "multiChart",
  "type": "MultiLineChartNode",
  "title": "Price Trends by Symbol",
  "data": "{{ nodes.history.values }}",
  "x_field": "date",
  "y_field": "close",
  "series_key": "symbol"
}
```

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `series_key` | string | O | Series distinguishing key (e.g., `"symbol"`) |

## CandlestickChartNode (Candlestick Chart)

Displays OHLCV data as a candlestick chart.

```json
{
  "id": "candle",
  "type": "CandlestickChartNode",
  "title": "AAPL Daily",
  "data": "{{ nodes.history.value }}",
  "date_field": "date",
  "open_field": "open",
  "high_field": "high",
  "low_field": "low",
  "close_field": "close",
  "volume_field": "volume"
}
```

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `date_field` | string | O | Date field |
| `open_field` | string | O | Open price field |
| `high_field` | string | O | High price field |
| `low_field` | string | O | Low price field |
| `close_field` | string | O | Close price field |
| `volume_field` | string | - | Volume field |

## BarChartNode (Bar Chart)

Displays categorical data as a bar chart.

```json
{
  "id": "bar",
  "type": "BarChartNode",
  "title": "P&L by Symbol",
  "data": "{{ nodes.account.positions }}",
  "x_field": "symbol",
  "y_field": "pnl_rate"
}
```

## SummaryDisplayNode (Summary Card)

Displays key metrics in summary card format.

```json
{
  "id": "summary",
  "type": "SummaryDisplayNode",
  "title": "Account Summary",
  "data": "{{ nodes.account }}"
}
```

Displays at-a-glance summary information like KPI cards on a dashboard.
