---
category: expression
tags: [function, namespace, date, finance, stats]
priority: high
---

# Function Namespaces: date, finance, stats, format, lst

Built-in functions available in expressions are organized by namespace.

## date - Date Functions

| Function | Description | Example | Result |
|----------|-------------|---------|--------|
| `date.today()` | Today's date | `{{ date.today(format='yyyymmdd') }}` | `"20260214"` |
| `date.ago(n)` | N days ago | `{{ date.ago(30, format='yyyymmdd') }}` | `"20260115"` |
| `date.later(n)` | N days later | `{{ date.later(7) }}` | `"2026-02-21"` |
| `date.months_ago(n)` | N months ago | `{{ date.months_ago(3) }}` | `"2025-11-14"` |
| `date.year_start()` | January 1st of this year | `{{ date.year_start() }}` | `"2026-01-01"` |
| `date.year_end()` | December 31st of this year | `{{ date.year_end() }}` | `"2026-12-31"` |
| `date.month_start()` | 1st of this month | `{{ date.month_start() }}` | `"2026-02-01"` |

**format parameter:**
- `'yyyymmdd'` -> `"20260214"` (Used for HistoricalDataNode's start_date/end_date)
- Omitted -> `"2026-02-14"` (ISO format)

**Practical usage:**

```json
{
  "id": "history",
  "type": "OverseasStockHistoricalDataNode",
  "start_date": "{{ date.ago(90, format='yyyymmdd') }}",
  "end_date": "{{ date.today(format='yyyymmdd') }}"
}
```

## finance - Financial Calculation Functions

| Function | Description | Example | Result |
|----------|-------------|---------|--------|
| `finance.pct_change(old, new)` | Percentage change (%) | `{{ finance.pct_change(100, 110) }}` | `10.0` |
| `finance.pct(value, pct)` | Percentage calculation | `{{ finance.pct(1000, 10) }}` | `100` |
| `finance.discount(price, pct)` | Discounted price | `{{ finance.discount(100, 5) }}` | `95` |
| `finance.markup(price, pct)` | Marked-up price | `{{ finance.markup(100, 5) }}` | `105` |
| `finance.annualize(ret, days)` | Annualized return | `{{ finance.annualize(5, 30) }}` | Annualized rate |
| `finance.compound(p, r, n)` | Compound interest | `{{ finance.compound(1000, 5, 3) }}` | `1157.63` |

## stats - Statistical Functions

| Function | Description | Example | Result |
|----------|-------------|---------|--------|
| `stats.mean(arr)` | Arithmetic mean | `{{ stats.mean([1,2,3,4,5]) }}` | `3.0` |
| `stats.avg(arr)` | Average (alias for mean) | `{{ stats.avg(prices) }}` | - |
| `stats.median(arr)` | Median | `{{ stats.median([1,3,5,7,9]) }}` | `5` |
| `stats.stdev(arr)` | Standard deviation | `{{ stats.stdev([1,2,3,4,5]) }}` | `1.58...` |
| `stats.variance(arr)` | Variance | `{{ stats.variance([1,2,3,4,5]) }}` | `2.5` |

## format - Formatting Functions

| Function | Description | Example | Result |
|----------|-------------|---------|--------|
| `format.pct(v, decimals)` | Percentage format | `{{ format.pct(12.345, 1) }}` | `"12.3%"` |
| `format.currency(v, symbol)` | Currency format | `{{ format.currency(1234.5) }}` | `"$1,234.50"` |
| `format.number(v, decimals)` | Number format | `{{ format.number(1234567, 0) }}` | `"1,234,567"` |

**Practical usage:**

```json
{
  "id": "summary",
  "type": "SummaryDisplayNode",
  "items": [
    {"label": "Return Rate", "value": "{{ format.pct(nodes.account.pnl_rate, 2) }}"},
    {"label": "Total Assets", "value": "{{ format.currency(nodes.account.total_eval) }}"}
  ]
}
```

## lst - List Utilities

| Function | Description | Example | Result |
|----------|-------------|---------|--------|
| `lst.first(arr)` | First element | `{{ lst.first(symbols) }}` | `{"symbol": "AAPL", ...}` |
| `lst.last(arr)` | Last element | `{{ lst.last(symbols) }}` | - |
| `lst.count(arr)` | Element count | `{{ lst.count(trades) }}` | - |
| `lst.pluck(arr, key)` | Extract specific key values | `{{ lst.pluck(items, 'name') }}` | `["AAPL", "TSLA"]` |
| `lst.flatten(arr, key)` | Flatten nested arrays | `{{ lst.flatten(values, 'time_series') }}` | See below |

### pluck vs flatten

Input data:
```json
[
  {"symbol": "AAPL", "time_series": [{"date": "20251224", "rsi": 33.5}]},
  {"symbol": "TSLA", "time_series": [{"date": "20251224", "rsi": 62.1}]}
]
```

| Function | Result |
|----------|--------|
| `pluck(values, "symbol")` | `["AAPL", "TSLA"]` |
| `flatten(values, "time_series")` | `[{"symbol": "AAPL", "date": "20251224", "rsi": 33.5}, ...]` |

`flatten` flattens nested arrays while preserving parent fields. This is useful when passing data to chart nodes.

### pluck with Deep Nested Paths

Access deep paths using dot notation:

```
{{ lst.pluck(positions, "details.sector") }}   ->   ["Tech", "Auto", "Finance"]
```

## Legacy Function Names (Backward Compatibility)

Functions that can be used without a namespace for backward compatibility:

| Function | Namespaced Version |
|----------|-------------------|
| `today()` | `date.today()` |
| `days_ago(n)` | `date.ago(n)` |
| `days_later(n)` | `date.later(n)` |
| `pct_change(a, b)` | `finance.pct_change(a, b)` |
| `mean(arr)` | `stats.mean(arr)` |
| `first(arr)` | `lst.first(arr)` |
| `pluck(arr, key)` | `lst.pluck(arr, key)` |

Using the namespaced versions is recommended.
