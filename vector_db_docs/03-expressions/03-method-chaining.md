---
category: expression
tags: [method, chaining, filter, map, sum, avg]
priority: high
---

# Method Chaining: filter, map, sum, avg

## What Is Method Chaining?

You can chain methods on node outputs to process data. By connecting (chaining) multiple methods, complex data processing can be expressed in a single line.

## Available Methods

| Method | Description | Returns | Example |
|--------|-------------|---------|---------|
| `.all()` | Entire array | Array | `{{ nodes.account.all() }}` |
| `.first()` | First item | Single | `{{ nodes.account.first() }}` |
| `.filter('condition')` | Filter by condition | Array | `{{ nodes.account.filter('pnl > 0') }}` |
| `.map('field')` | Extract specific field | Array | `{{ nodes.account.map('symbol') }}` |
| `.sum('field')` | Sum | Number | `{{ nodes.account.sum('quantity') }}` |
| `.avg('field')` | Average | Number | `{{ nodes.account.avg('pnl') }}` |
| `.count()` | Count | Number | `{{ nodes.account.count() }}` |

## Usage Examples

### Single Method

```json
{
  "all_positions": "{{ nodes.account.all() }}",
  "first_position": "{{ nodes.account.first() }}",
  "symbols_only": "{{ nodes.account.map('symbol') }}",
  "total_quantity": "{{ nodes.account.sum('quantity') }}",
  "avg_pnl": "{{ nodes.account.avg('pnl') }}",
  "position_count": "{{ nodes.account.count() }}"
}
```

### Filtering

The `filter()` method accepts a string condition expression:

```json
{
  "profitable": "{{ nodes.account.filter('pnl > 0') }}",
  "losing": "{{ nodes.account.filter('pnl < 0') }}",
  "large_positions": "{{ nodes.account.filter('quantity >= 10') }}"
}
```

### Method Chaining (Combinations)

Chain multiple methods together for complex processing in a single line:

```json
{
  "profit_count": "{{ nodes.account.filter('pnl > 0').count() }}",
  "loss_symbols": "{{ nodes.account.filter('pnl < 0').map('symbol') }}",
  "profit_avg": "{{ nodes.account.filter('pnl > 0').avg('pnl') }}"
}
```

## Practical Examples

### List of Losing Positions Among Holdings

```json
{
  "id": "summary",
  "type": "SummaryDisplayNode",
  "data": {
    "total_positions": "{{ nodes.account.count() }}",
    "profit_positions": "{{ nodes.account.filter('pnl > 0').count() }}",
    "loss_positions": "{{ nodes.account.filter('pnl < 0').count() }}",
    "avg_return": "{{ nodes.account.avg('pnl_rate') }}",
    "total_value": "{{ nodes.account.sum('eval_amount') }}"
  }
}
```

### Extract Only Symbols That Passed a Condition

```json
{
  "buy_symbols": "{{ nodes.rsi.result.passed_symbols.map('symbol') }}"
}
```

## Notes

- Field names used in `.filter()` conditions must actually exist in the data
- Calling `.first()` on an empty array returns `None`
- `.sum()` and `.avg()` should only be used on numeric fields
