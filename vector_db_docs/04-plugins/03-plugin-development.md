---
category: plugin
tags: [development, custom, plugin_result, plugin_schema, community]
priority: medium
---

# Custom Plugin Development Guide

## Overview

ProgramGarden plugins are technical analysis/position management logic used in `ConditionNode`. This guide explains how to add new plugins to the `community` package.

## Plugin Structure

```
src/community/programgarden_community/plugins/
├── __init__.py          # Plugin registry (register_all_plugins)
├── rsi/
│   └── __init__.py      # RSI_SCHEMA + rsi_condition()
├── macd/
│   └── __init__.py      # MACD_SCHEMA + macd_condition()
└── my_plugin/           # New plugin
    └── __init__.py
```

## Plugin Development Steps

### 1. Define PluginSchema

```python
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType

MY_PLUGIN_SCHEMA = PluginSchema(
    id="MyPlugin",                          # Unique ID (used in ConditionNode's plugin field)
    name="My Custom Plugin",                # Display name
    category=PluginCategory.TECHNICAL,      # TECHNICAL or POSITION
    version="1.0.0",
    description="English description for AI agent reference.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "period": {
            "type": "int",
            "default": 14,
            "title": "Period",
            "description": "Calculation period",
            "ge": 2,      # Minimum value
            "le": 100,     # Maximum value
        },
        "threshold": {
            "type": "float",
            "default": 50.0,
            "title": "Threshold",
            "ge": 0,
            "le": 100,
        },
        "direction": {
            "type": "string",
            "default": "above",
            "title": "Direction",
            "enum": ["above", "below"],     # Options
        },
    },
    required_data=["data"],                 # TECHNICAL: ["data"], POSITION: ["positions"]
    required_fields=["symbol", "exchange", "date", "close"],  # Required data fields
    optional_fields=["high", "low", "volume"],
    tags=["momentum", "custom"],
    output_fields={
        "indicator": {"type": "float", "description": "Custom indicator value"},
        "current_price": {"type": "float", "description": "Latest closing price"},
    },
    locales={
        "ko": {
            "name": "My Custom Plugin",
            "description": "Korean description",
            "fields.period": "Calculation period",
            "fields.threshold": "Threshold value",
            "fields.direction": "Direction",
        },
    },
)
```

### PluginSchema Field Descriptions

| Field | Required | Description |
|-------|:--------:|-------------|
| `id` | O | Unique ID to use in ConditionNode's `plugin` field |
| `name` | - | Display name |
| `category` | O | `TECHNICAL` or `POSITION` |
| `version` | - | Plugin version (default "1.0.0") |
| `description` | - | English description (for AI agent reference) |
| `products` | O | List of supported products |
| `fields_schema` | O | User-configurable field definitions |
| `required_data` | O | Required input (`["data"]` or `["positions"]`) |
| `required_fields` | O | Fields that must be present in data |
| `optional_fields` | - | Optional fields used when available |
| `tags` | - | Tags for search/categorization |
| `output_fields` | - | Output field metadata (`{field: {type, description}}`) |
| `locales` | - | Multi-language support |

### fields_schema Types

| type | Description | Additional Attributes |
|------|-------------|----------------------|
| `"int"` | Integer | `ge`, `le`, `default` |
| `"float"` | Float | `ge`, `le`, `default` |
| `"string"` | String | `enum`, `default` |
| `"bool"` | Boolean | `default` |

### 2. Implement the Condition Function

#### TECHNICAL Plugin Pattern

```python
from typing import List, Dict, Any, Optional

async def my_plugin_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
    **kwargs,
) -> dict:
    """
    Custom condition evaluation

    Args:
        data: Flat array [{symbol, exchange, date, close, ...}, ...]
        fields: User settings {"period": 14, "threshold": 50}
        field_mapping: Field name mapping (using defaults is recommended)
        symbols: Symbols to evaluate (auto-extracted from data if not provided)
    """
    # 1. Field mapping
    mapping = field_mapping or {}
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")

    # 2. Parameter extraction
    period = fields.get("period", 14)
    threshold = fields.get("threshold", 50.0)
    direction = fields.get("direction", "above")

    # 3. Empty data handling
    if not data:
        return {
            "passed_symbols": [],
            "failed_symbols": symbols or [],
            "symbol_results": [],
            "values": [],
            "result": False,
        }

    # 4. Group data by symbol
    grouped: Dict[str, List[Dict]] = {}
    exchange_map: Dict[str, str] = {}
    for row in data:
        sym = row.get(symbol_field, "")
        if sym:
            grouped.setdefault(sym, []).append(row)
            exchange_map.setdefault(sym, row.get(exchange_field, "UNKNOWN"))

    # 5. Determine symbol list
    if not symbols:
        symbols = [{"symbol": s, "exchange": exchange_map[s]} for s in grouped]

    # 6. Evaluate each symbol
    passed, failed, symbol_results, values = [], [], [], []

    for sym_info in symbols:
        symbol = sym_info.get("symbol", "")
        exchange = sym_info.get("exchange", "UNKNOWN")
        sym_dict = {"symbol": symbol, "exchange": exchange}

        rows = sorted(grouped.get(symbol, []), key=lambda x: x.get(date_field, ""))
        prices = [float(r[close_field]) for r in rows if r.get(close_field)]

        if len(prices) < period:
            failed.append(sym_dict)
            symbol_results.append({"symbol": symbol, "exchange": exchange, "error": "insufficient_data"})
            continue

        # 7. Calculate indicator
        indicator_value = calculate_my_indicator(prices, period)

        # 8. Evaluate condition
        if direction == "above":
            passed_condition = indicator_value > threshold
        else:
            passed_condition = indicator_value < threshold

        # 9. Store results
        symbol_results.append({
            "symbol": symbol,
            "exchange": exchange,
            "my_indicator": round(indicator_value, 2),
            "current_price": prices[-1],
        })

        # 10. Generate time_series (including signal/side)
        time_series = []
        for i, row in enumerate(rows):
            signal = None
            side = "long"
            # Add signal on the last bar when condition is met
            if i == len(rows) - 1 and passed_condition:
                signal = "buy" if direction == "below" else "sell"

            time_series.append({
                "date": row.get(date_field, ""),
                "close": row.get(close_field),
                "my_indicator": indicator_value if i == len(rows) - 1 else None,
                "signal": signal,
                "side": side,
            })

        values.append({"symbol": symbol, "exchange": exchange, "time_series": time_series})

        if passed_condition:
            passed.append(sym_dict)
        else:
            failed.append(sym_dict)

    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "symbol_results": symbol_results,
        "values": values,
        "result": len(passed) > 0,
        "analysis": {
            "indicator": "MyPlugin",
            "period": period,
            "threshold": threshold,
            "direction": direction,
        },
    }
```

#### POSITION Plugin Pattern

```python
async def my_position_condition(
    positions: Optional[Dict[str, Any]] = None,
    fields: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> dict:
    """
    Position-based condition evaluation

    Args:
        positions: {symbol: {pnl_rate, current_price, avg_price, qty, market_code, ...}}
        fields: {"my_threshold": 5.0}
    """
    positions = positions or {}
    fields = fields or {}

    passed, failed, symbol_results = [], [], []

    for symbol, pos_data in positions.items():
        pnl_rate = pos_data.get("pnl_rate", 0)
        exchange = pos_data.get("market_code", "UNKNOWN")
        sym_dict = {"exchange": exchange, "symbol": symbol}

        # Evaluate condition
        if pnl_rate >= fields.get("my_threshold", 5.0):
            passed.append(sym_dict)
        else:
            failed.append(sym_dict)

        symbol_results.append({
            "symbol": symbol,
            "exchange": exchange,
            "pnl_rate": round(pnl_rate, 2),
        })

    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "symbol_results": symbol_results,
        "values": [],  # POSITION plugins typically have no time_series
        "result": len(passed) > 0,
    }
```

### 3. Declare risk_features (Optional)

Plugins that need WorkflowRiskTracker functionality declare `risk_features` at the module level:

```python
from typing import Set

# Declare at module level (not a class member)
risk_features: Set[str] = {"hwm"}
```

| Feature | Purpose |
|---------|---------|
| `hwm` | High Water Mark / drawdown tracking |
| `window` | Volatility / MDD calculation window |
| `events` | Risk event audit trail |
| `state` | Strategy state KV store |

Usage example:

```python
async def my_condition(data, fields, context=None, **kwargs):
    if context and context.risk_tracker:
        hwm = context.risk_tracker.get_hwm("AAPL")
        if hwm:
            drawdown = float(hwm.drawdown_pct)
```

### 4. Register in the Registry

Register in the `register_all_plugins()` function in `plugins/__init__.py`:

```python
from .my_plugin import MY_PLUGIN_SCHEMA, my_plugin_condition

# Inside the register_all_plugins() function:
registry.register(
    plugin_id="MyPlugin",
    plugin_callable=my_plugin_condition,
    schema=MY_PLUGIN_SCHEMA,
)
```

### 5. Use in a Workflow

```json
{
  "id": "my_check",
  "type": "ConditionNode",
  "plugin": "MyPlugin",
  "items": {
    "from": "{{ nodes.historical.value.time_series }}",
    "extract": {
      "symbol": "{{ nodes.historical.value.symbol }}",
      "exchange": "{{ nodes.historical.value.exchange }}",
      "date": "{{ row.date }}",
      "close": "{{ row.close }}"
    }
  },
  "fields": {
    "period": 14,
    "threshold": 50,
    "direction": "above"
  }
}
```

## Required Return Fields

All plugins must return the following fields:

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `passed_symbols` | array | O | Symbols that passed the condition `[{exchange, symbol}]` |
| `failed_symbols` | array | O | Symbols that failed the condition |
| `symbol_results` | array | O | Detailed results per symbol |
| `values` | array | O | Time series data (for chart display) |
| `result` | bool | O | `true` if at least one symbol passed |
| `analysis` | object | - | Analysis metadata |

## Symbol Data Format Rules

Always use the array + `symbol`/`exchange` field format:

```python
# Correct format
[{"symbol": "AAPL", "exchange": "NASDAQ", "rsi": 28.5}]

# Incorrect format (do not use symbol as key)
{"AAPL": {"rsi": 28.5}}
```

## Plugin API Utilities

```python
from programgarden_community.plugins import (
    register_all_plugins,  # Register all plugins
    get_plugin,            # Retrieve plugin schema
    list_plugins,          # List plugins
)

# Register
register_all_plugins()

# Retrieve
schema = get_plugin("RSI")
# → {"id": "RSI", "name": "RSI (Relative Strength Index)", "category": "technical", ...}

# List
plugins = list_plugins(category="technical")
# → {"technical": ["RSI", "MACD", ...]}

plugins = list_plugins(product="overseas_stock")
# → {"technical": [...], "position": [...]}
```

## Checklist

1. [ ] `PluginSchema` definition complete (id, category, fields_schema, required_data, output_fields)
2. [ ] Async condition function implemented (correct signature)
3. [ ] Empty data handling (safe return when data/positions is missing)
4. [ ] Required return fields included (passed_symbols, failed_symbols, symbol_results, values, result)
5. [ ] signal/side fields included in time_series
6. [ ] Symbol data format rules followed (array + symbol/exchange)
7. [ ] Korean (ko) translation added to locales
8. [ ] Registered in `__init__.py` registry
9. [ ] Tests written and passing
