---
category: appendix
tags: [reference, expression, cheatsheet, binding, auto_iterate, method_chaining, date, finance, stats, format, lst, item, index, total, filter, map, sum, avg, flatten]
priority: high
---

# Expression Cheatsheet

## Data Binding Basics

Use `{{ }}` syntax to connect data between nodes.

```json
"data": "{{ nodes.account.positions }}"
"symbol": "{{ nodes.watchlist.symbols }}"
"balance": "{{ nodes.account.balance }}"
```

### Node Output References

```
{{ nodes.<nodeID>.<outputPort> }}
{{ nodes.account.positions }}
{{ nodes.market.value }}
{{ nodes.historical.values }}
```

## Auto-Iterate

When a preceding node outputs an array, the next node automatically executes for each item.

### Auto-Iterate Keywords

| Keyword | Description | Example |
|---------|-------------|---------|
| `item` | Current iteration item | `{{ item.symbol }}` |
| `index` | Current index (0-based) | `{{ index }}` |
| `total` | Total item count | `{{ total }}` |

### Example

```
[AccountNode] → [FieldMappingNode] → [NewOrderNode]
     │                                    │
     └─ positions: [{...}, {...}, {...}]   └─ Executes 3 times
                                           {{ item.symbol }}
                                           {{ item.quantity }}
```

```json
{
    "id": "order",
    "type": "OverseasStockNewOrderNode",
    "side": "{{ item.close_side }}",
    "order": {
        "symbol": "{{ item.symbol }}",
        "exchange": "{{ item.exchange }}",
        "quantity": "{{ item.quantity }}",
        "price": "{{ item.current_price }}"
    }
}
```

## Method Chaining

Methods available on `nodes.<nodeId>` expressions. Can be chained together.

### Basic Methods

| Method | Description | Example |
|--------|-------------|---------|
| `.all()` | Entire array | `{{ nodes.account.all() }}` |
| `.first()` | First item | `{{ nodes.account.first() }}` |
| `.last()` | Last item | `{{ nodes.account.last() }}` |
| `.count()` | Item count | `{{ nodes.account.count() }}` |

### Data Manipulation Methods

| Method | Description | Example |
|--------|-------------|---------|
| `.filter('condition')` | Condition filtering | `{{ nodes.account.filter('pnl > 0') }}` |
| `.map('field')` | Field extraction | `{{ nodes.account.map('symbol') }}` |
| `.sum('field')` | Sum | `{{ nodes.account.sum('quantity') }}` |
| `.avg('field')` | Average | `{{ nodes.account.avg('pnl') }}` |
| `.flatten('field')` | Flatten nested arrays | `{{ nodes.historical.flatten('time_series') }}` |

### Chaining Examples

```json
"profitable_count": "{{ nodes.account.filter('pnl > 0').count() }}"
"profitable_total": "{{ nodes.account.filter('pnl > 0').sum('quantity') }}"
"losing_symbols": "{{ nodes.account.filter('pnl < 0').map('symbol') }}"
"flattened_rsi": "{{ nodes.historical.flatten('time_series').filter('rsi < 30') }}"
```

### filter Condition Syntax

| Operator | Example |
|----------|---------|
| `>`, `<`, `>=`, `<=` | `filter('pnl > 0')` |
| `==`, `!=` | `filter('symbol == "AAPL"')` |
| Numeric | `filter('quantity >= 100')` |
| String | `filter('side != "long"')` |
| Boolean | `filter('active == true')` |

## Function Namespaces

### date - Date Functions

| Function | Description | Example | Result |
|----------|-------------|---------|--------|
| `date.today()` | Today (ISO) | `{{ date.today() }}` | `2026-02-14` |
| `date.today(format='yyyymmdd')` | Today (specified format) | `{{ date.today(format='yyyymmdd') }}` | `20260214` |
| `date.ago(N)` | N days ago | `{{ date.ago(30) }}` | `2026-01-15` |
| `date.ago(N, format='yyyymmdd')` | N days ago (formatted) | `{{ date.ago(30, format='yyyymmdd') }}` | `20260115` |
| `date.later(N)` | N days later | `{{ date.later(7) }}` | `2026-02-21` |
| `date.months_ago(N)` | N months ago (30-day basis) | `{{ date.months_ago(3) }}` | `2025-11-16` |
| `date.year_start()` | Start of year | `{{ date.year_start(format='yyyymmdd') }}` | `20260101` |
| `date.year_end()` | End of year | `{{ date.year_end() }}` | `2026-12-31` |
| `date.month_start()` | Start of month | `{{ date.month_start() }}` | `2026-02-01` |
| `date.now()` | Current datetime | `{{ date.now() }}` | `2026-02-14T10:30:45` |

**Commonly used pattern:**

```json
"start_date": "{{ date.ago(30, format='yyyymmdd') }}",
"end_date": "{{ date.today(format='yyyymmdd') }}"
```

### finance - Financial Calculations

| Function | Description | Example | Result |
|----------|-------------|---------|--------|
| `finance.pct_change(from, to)` | Percentage change (%) | `{{ finance.pct_change(100, 110) }}` | `10.0` |
| `finance.pct(part, whole)` | Ratio (%) | `{{ finance.pct(50, 200) }}` | `25.0` |
| `finance.discount(amount, pct)` | Discount | `{{ finance.discount(1000, 20) }}` | `800.0` |
| `finance.markup(amount, pct)` | Markup | `{{ finance.markup(100, 15) }}` | `115.0` |
| `finance.annualize(ret, days)` | Annualize (252-day basis) | `{{ finance.annualize(5, 30) }}` | Annualized return |
| `finance.compound(principal, rate, n)` | Compound interest | `{{ finance.compound(1000, 5, 10) }}` | Compound result |

### stats - Statistics

| Function | Description | Example | Result |
|----------|-------------|---------|--------|
| `stats.mean(arr)` | Mean | `{{ stats.mean([1,2,3,4,5]) }}` | `3.0` |
| `stats.avg(arr)` | Average (alias for mean) | `{{ stats.avg([10,20,30]) }}` | `20.0` |
| `stats.median(arr)` | Median | `{{ stats.median([1,2,3,4,5]) }}` | `3` |
| `stats.stdev(arr)` | Standard deviation | `{{ stats.stdev([1,2,3,4,5]) }}` | Standard deviation |
| `stats.variance(arr)` | Variance | `{{ stats.variance([1,2,3,4,5]) }}` | Variance |

### format - Formatting

| Function | Description | Example | Result |
|----------|-------------|---------|--------|
| `format.pct(value)` | Percent display | `{{ format.pct(12.34) }}` | `12.34%` |
| `format.pct(value, dp)` | Specify decimal places | `{{ format.pct(12.3456, 1) }}` | `12.3%` |
| `format.currency(value)` | Currency (USD) | `{{ format.currency(1234.56) }}` | `$1,234.56` |
| `format.currency(value, sym)` | Specify currency symbol | `{{ format.currency(1234, "€") }}` | `€1,234.00` |
| `format.number(value, dp)` | Number format | `{{ format.number(1234567.89, 1) }}` | `1,234,567.9` |

### lst - List Utilities

| Function | Description | Example |
|----------|-------------|---------|
| `lst.first(arr)` | First item | `{{ lst.first([1,2,3]) }}` → `1` |
| `lst.last(arr)` | Last item | `{{ lst.last([1,2,3]) }}` → `3` |
| `lst.count(arr)` | Item count | `{{ lst.count([1,2,3]) }}` → `3` |
| `lst.pluck(arr, key)` | Extract field | `{{ lst.pluck(items, 'name') }}` |
| `lst.pluck(arr, path)` | Nested field | `{{ lst.pluck(items, 'details.price') }}` |
| `lst.flatten(arr, key)` | Flatten nested arrays | `{{ lst.flatten(data, 'time_series') }}` |

## Built-in Functions

Built-in functions available directly within `{{ }}` expressions:

| Category | Functions |
|----------|-----------|
| Type conversion | `bool()`, `int()`, `float()`, `str()`, `list()`, `dict()` |
| Math | `abs()`, `min()`, `max()`, `sum()`, `pow()`, `round()`, `len()` |
| Advanced math | `sqrt()`, `log()`, `log10()`, `exp()`, `ceil()`, `floor()` |
| Constants | `pi`, `e`, `True`, `False`, `None` |
| Iteration | `range()`, `sorted()`, `zip()`, `all()`, `any()` |

### Built-in Function Usage Examples

```json
"quantity": "{{ int(item.quantity) }}",
"rounded_price": "{{ round(item.price, 2) }}",
"total": "{{ len(nodes.account.positions) }}",
"max_pnl": "{{ max(lst.pluck(nodes.account.positions, 'pnl')) }}"
```
