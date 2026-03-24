---
category: expression
tags: [binding, expression, template, type_cast]
priority: critical
---

# Data Binding Syntax: {{ nodes.id.port }}

## Basic Syntax

ProgramGarden's Expression system uses `{{ }}` syntax to compute dynamic values.

```json
"symbols": "{{ nodes.watchlist.symbols }}"
"symbols": "{{ input.symbols }}"
"quantity": "{{ balance * 0.1 }}"
"start_date": "{{ date.ago(30) }}"
"action": "{{ 'buy' if rsi < 30 else 'hold' }}"
```

## Variable Types

### nodes Variable (Node Output Reference)

Reference previous node outputs using the `nodes.nodeID.field` format:

```json
"price": "{{ nodes.marketData.price }}"
"quantity": "{{ nodes.sizing.calculated_quantity }}"
"symbols": "{{ nodes.watchlist.symbols }}"
"positions": "{{ nodes.account.positions }}"
```

### input Variable (Workflow Input)

References values defined in the workflow's `inputs` section:

```json
{
  "inputs": {
    "symbols": {"type": "symbol_list", "default": [{"exchange": "NASDAQ", "symbol": "AAPL"}]},
    "rsi_period": {"type": "integer", "default": 14}
  },
  "nodes": [
    {"id": "watchlist", "type": "WatchlistNode", "symbols": "{{ input.symbols }}"},
    {"id": "rsi", "type": "ConditionNode", "plugin": "RSI",
     "fields": {"period": "{{ input.rsi_period }}"}}
  ]
}
```

### context Variable (Runtime Context)

Runtime parameters passed from the execution context:

```json
"balance": "{{ context.available_balance }}"
```

### item, index, total (Iteration Keywords)

Used during array Auto-Iterate:

| Keyword | Description | Example |
|---------|-------------|---------|
| `item` | Current iteration item | `{{ item.symbol }}` -> `"AAPL"` |
| `index` | Current index (0-based) | `{{ index }}` -> `0` |
| `total` | Total item count | `{{ total }}` -> `3` |

## Reserved Words (Cannot Be Used as Node IDs)

- `nodes` -- For referencing node outputs
- `input` -- For referencing workflow inputs
- `context` -- For referencing runtime context

## Expression Features

### Arithmetic Operations

```json
"quantity": "{{ balance * 0.1 }}"
"total": "{{ price * quantity }}"
"change": "{{ (new_price - old_price) / old_price * 100 }}"
```

### Conditional Expressions

```json
"action": "{{ 'buy' if rsi < 30 else 'hold' }}"
"size": "{{ min(max_position, balance * 0.1) }}"
```

### Type Conversion Functions

| Function | Description | Example |
|----------|-------------|---------|
| `bool(x)` | Convert to boolean | `{{ bool(value) }}` |
| `int(x)` | Convert to integer | `{{ int(price) }}` |
| `float(x)` | Convert to float | `{{ float("3.14") }}` |
| `str(x)` | Convert to string | `{{ str(quantity) }}` |
| `list(x)` | Convert to list | `{{ list(range(5)) }}` |

### Basic Built-in Functions

| Function | Description | Example |
|----------|-------------|---------|
| `abs(x)` | Absolute value | `{{ abs(-5) }}` -> `5` |
| `min(a, b)` | Minimum value | `{{ min(10, 5) }}` -> `5` |
| `max(a, b)` | Maximum value | `{{ max(10, 5) }}` -> `10` |
| `sum(list)` | Sum | `{{ sum([1,2,3]) }}` -> `6` |
| `round(x, n)` | Round | `{{ round(3.14159, 2) }}` -> `3.14` |
| `len(x)` | Length | `{{ len(symbols) }}` |
| `sorted(list)` | Sort | `{{ sorted([3,1,2]) }}` -> `[1,2,3]` |

### Advanced Math Functions

| Function | Description |
|----------|-------------|
| `sqrt(x)` | Square root |
| `log(x)` | Natural logarithm |
| `log10(x)` | Common logarithm (base 10) |
| `ceil(x)` | Ceiling (round up) |
| `floor(x)` | Floor (round down) |

### Constants

| Constant | Value |
|----------|-------|
| `True` | `True` |
| `False` | `False` |
| `None` | `None` |
| `pi` | `3.14159...` |
| `e` | `2.71828...` |

## Notes

**The `$input.xxx` syntax is not used.** Always use the `{{ input.xxx }}` format.

| Incorrect | Correct |
|-----------|---------|
| `"$input.symbols"` | `"{{ input.symbols }}"` |

### Unsupported Features (Security)

- `import` statements
- `exec()`, `eval()` functions
- File I/O (`open()`, `read()`, `write()`)
- Network access
- System commands
- Class/function definitions

### Error Handling

When an expression error occurs, an `ExpressionError` is raised and the node execution is aborted:
- `{{ undefined_variable }}` -> Undefined variable
- `{{ 10 / 0 }}` -> Division by zero
