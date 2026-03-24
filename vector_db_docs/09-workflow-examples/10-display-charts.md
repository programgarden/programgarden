---
category: workflow_example
tags: [example, display, table, chart, summary, TableDisplayNode, LineChartNode, CandlestickChartNode, BarChartNode, SummaryDisplayNode, on_display_data]
priority: medium
---

# Example: Display/Charts

## Overview

Examples of nodes that visualize workflow execution results as tables, charts, summaries, etc. Display nodes deliver data through the `on_display_data` listener callback.

## Example 1: Position Table Display

Displays held positions as a table sorted by profit/loss in descending order.

```json
{
  "nodes": [
    {"id": "start", "type": "StartNode"},
    {
      "id": "broker",
      "type": "OverseasStockBrokerNode",
      "credential_id": "broker-cred"
    },
    {
      "id": "account",
      "type": "OverseasStockAccountNode"
    },
    {
      "id": "table",
      "type": "TableDisplayNode",
      "title": "Held Positions",
      "data": "{{ nodes.account.positions }}",
      "columns": ["symbol", "exchange", "quantity", "pnl"],
      "limit": 10,
      "sort_by": "pnl",
      "sort_order": "desc"
    }
  ],
  "edges": [
    {"from": "start", "to": "broker"},
    {"from": "broker", "to": "account"},
    {"from": "account", "to": "table"}
  ],
  "credentials": [{"credential_id": "broker-cred"}]
}
```

### TableDisplayNode Settings

| Field | Type | Description |
|------|------|------|
| `title` | string | Table title |
| `data` | expression | Data to display (array) |
| `columns` | array | List of columns to display |
| `limit` | number | Maximum number of rows |
| `sort_by` | string | Field to sort by |
| `sort_order` | string | `"asc"` or `"desc"` |

## Display Node Types

| Node | Purpose |
|------|------|
| `TableDisplayNode` | Display data as a table |
| `LineChartNode` | Line chart |
| `MultiLineChartNode` | Multi-line chart (compare multiple symbols) |
| `CandlestickChartNode` | Candlestick chart (OHLCV) |
| `BarChartNode` | Bar chart |
| `SummaryDisplayNode` | Summary information card |

## Example 2: Condition Filter Result Table

Filters only RSI oversold symbols and displays them as a table.

```json
{
  "id": "table",
  "type": "TableDisplayNode",
  "title": "RSI Oversold Symbols",
  "data": "{{ nodes.rsi_condition.symbol_results }}",
  "columns": ["symbol", "exchange", "rsi", "signal"],
  "limit": 10,
  "sort_by": "rsi",
  "sort_order": "asc"
}
```

### Using Method Chaining

```json
// Filter + Sort
"data": "{{ nodes.rsi_condition.symbol_results }}"

// Extract specific fields
"data": "{{ nodes.account.positions.map('symbol') }}"

// Count
"count": "{{ nodes.account.positions.filter('pnl > 0').count() }}"
```

## Example 3: HTTP Response Result Display

Transforms an external API response with FieldMappingNode then displays as a table:

```json
{
  "id": "display",
  "type": "TableDisplayNode",
  "title": "HTTP Response Result",
  "data": "{{ [nodes.mapper.data] }}",
  "columns": ["title", "author"]
}
```

- `{{ [nodes.mapper.data] }}`: Wraps a single object in an array for table display
- `columns`: Select only the fields to display

## Receiving Display Data

Display nodes deliver data through the `on_display_data` listener callback:

```python
class MyListener(BaseExecutionListener):
    async def on_display_data(self, event: DisplayDataEvent):
        print(f"Node: {event.node_id}")
        print(f"Type: {event.display_type}")  # "table", "line_chart", etc.
        print(f"Data: {event.data}")
```

### DisplayDataEvent Fields

| Field | Description |
|------|------|
| `node_id` | Display node ID |
| `display_type` | Display type (`table`, `line_chart`, `candlestick`, `bar_chart`, `summary`) |
| `title` | Title |
| `data` | Display data |
| `config` | Chart/table configuration |
