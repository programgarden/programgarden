---
category: workflow_structure
tags: [json, nodes, edges, credentials, notes]
priority: critical
---

# Workflow JSON Format

## Top-Level Structure

A workflow is a JSON object consisting of 4 components:

```json
{
  "nodes": [ ... ],
  "edges": [ ... ],
  "credentials": [ ... ],
  "notes": [ ... ]
}
```

| Component | Required | Description |
|-----------|:--------:|-------------|
| `nodes` | O | Array of functional blocks |
| `edges` | O | Connections between blocks (defines execution order) |
| `credentials` | O | Broker/API authentication information |
| `notes` | - | Canvas memos (not executed, for documentation purposes) |

## Optional Top-Level Fields

### inputs (Workflow Input Parameters)

Defines parameters that can be injected externally when executing a workflow:

```json
{
  "inputs": {
    "symbols": {
      "type": "symbol_list",
      "default": [{"exchange": "NASDAQ", "symbol": "AAPL"}],
      "description": "Target symbols"
    },
    "rsi_period": {
      "type": "integer",
      "default": 14,
      "description": "RSI period"
    }
  },
  "nodes": [ ... ],
  "edges": [ ... ]
}
```

Reference in nodes with `{{ input.symbols }}`, `{{ input.rsi_period }}`.

### resource_limits (Resource Limits)

```json
{
  "resource_limits": {
    "max_cpu_percent": 70,
    "max_memory_percent": 75,
    "max_workers": 2,
    "throttle_strategy": "conservative"
  },
  "nodes": [ ... ],
  "edges": [ ... ]
}
```

## Node Basic Fields

Fields common to all nodes:

```json
{
  "id": "broker",
  "type": "OverseasStockBrokerNode",
  "credential_id": "my-broker"
}
```

| Field | Required | Description |
|-------|:--------:|-------------|
| `id` | O | Unique identifier (alphanumeric, underscores). Referenced by other nodes via `{{ nodes.id.field }}` |
| `type` | O | Node type (e.g., `OverseasStockBrokerNode`) |
| `credential_id` | - | Credential reference (used by BrokerNode, LLMModelNode, etc.) |

### Node ID Reserved Words

The following names cannot be used as node IDs:
- `nodes` — Reserved for node output references
- `input` — Reserved for workflow input references
- `context` — Reserved for runtime context references

## Edge Basic Fields

```json
{"from": "broker", "to": "account"}
{"from": "llm", "to": "agent", "type": "ai_model"}
```

| Field | Required | Description |
|-------|:--------:|-------------|
| `from` | O | Source node ID |
| `to` | O | Target node ID |
| `type` | - | Edge type (defaults to `main` if omitted). Possible values: `main`, `ai_model`, `tool` |

## Credential Basic Fields

```json
{
  "credential_id": "my-broker",
  "type": "broker_ls_overseas_stock",
  "data": [
    {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
    {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"}
  ]
}
```

| Field | Description |
|-------|-------------|
| `credential_id` | Unique ID (referenced by node's `credential_id`) |
| `type` | Authentication type |
| `data` | Authentication data array (`key`, `value`, `type`, `label`) |

## Note Basic Fields

```json
{
  "id": "note-1",
  "content": "## Note Title\n\nNote content",
  "color": 1,
  "width": 300,
  "height": 200,
  "position": {"x": 100, "y": 50}
}
```

| Field | Description |
|-------|-------------|
| `id` | Note unique ID |
| `content` | Note content in Markdown format |
| `color` | Color number (0~7) |
| `width`, `height` | Note size (pixels) |
| `position` | Canvas position (`x`, `y`) |

## Complete Workflow Example

```json
{
  "inputs": {
    "target_symbols": {
      "type": "symbol_list",
      "default": [
        {"exchange": "NASDAQ", "symbol": "AAPL"},
        {"exchange": "NASDAQ", "symbol": "NVDA"}
      ]
    }
  },
  "nodes": [
    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "my-broker"},
    {"id": "watchlist", "type": "WatchlistNode", "symbols": "{{ input.target_symbols }}"},
    {"id": "history", "type": "OverseasStockHistoricalDataNode", "interval": "1d",
     "start_date": "{{ date.ago(30, format='yyyymmdd') }}",
     "end_date": "{{ date.today(format='yyyymmdd') }}"},
    {"id": "rsi", "type": "ConditionNode", "plugin": "RSI",
     "items": {"from": "{{ nodes.history.value.time_series }}", "extract": {"symbol": "{{ nodes.history.value.symbol }}", "exchange": "{{ nodes.history.value.exchange }}", "date": "{{ row.date }}", "close": "{{ row.close }}"}},
     "fields": {"period": 14, "threshold": 30, "direction": "below"}},
    {"id": "order", "type": "OverseasStockNewOrderNode", "plugin": "MarketOrder",
     "fields": {"side": "buy", "amount_type": "percent_balance", "amount": 10}}
  ],
  "edges": [
    {"from": "broker", "to": "watchlist"},
    {"from": "watchlist", "to": "history"},
    {"from": "history", "to": "rsi"},
    {"from": "rsi", "to": "order"}
  ],
  "credentials": [
    {
      "credential_id": "my-broker",
      "type": "broker_ls_overseas_stock",
      "data": [
        {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
        {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"}
      ]
    }
  ],
  "notes": [
    {
      "id": "note-strategy",
      "content": "## RSI Buy Strategy\n\nMarket buy with 10% of balance when RSI below 30",
      "color": 2,
      "width": 300,
      "height": 150,
      "position": {"x": 0, "y": -100}
    }
  ]
}
```
