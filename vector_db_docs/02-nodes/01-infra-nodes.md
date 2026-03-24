---
category: node_reference
tags: [infra, start, throttle, split, aggregate, broker, if, conditional]
priority: high
---

# Infrastructure Nodes: Start, Throttle, Split, Aggregate, Broker, IfNode

Infrastructure nodes handle workflow initiation, broker connection, and data flow control.

## StartNode

The entry point of a workflow. When used with ScheduleNode, it enables repeated execution.

```json
{"id": "start", "type": "StartNode"}
```

**Output**: `start` - Workflow start signal

## BrokerNode (Broker Connection)

Connects to the LS Securities API. Account/quote/order nodes require this node first.

| Product | Node Type | Paper Trading |
|---------|----------|:------------:|
| Overseas Stocks | `OverseasStockBrokerNode` | X (live only) |
| Overseas Futures | `OverseasFuturesBrokerNode` | O |

```json
{
  "id": "broker",
  "type": "OverseasStockBrokerNode",
  "credential_id": "my-stock-cred"
}
```

```json
{
  "id": "broker",
  "type": "OverseasFuturesBrokerNode",
  "credential_id": "my-futures-cred",
  "paper_trading": true
}
```

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `credential_id` | string | O | Authentication ID from the credentials section |
| `paper_trading` | boolean | - | Paper trading mode (futures only, default: false) |

**Output**: `connection` - Broker connection object (automatically propagated to downstream nodes)

**Auto-propagation**: BrokerNode's connection is automatically delivered to downstream nodes connected via edges. There is no need to bind directly like `{{ nodes.broker.connection }}`.

## ThrottleNode (Rate Limiting)

Controls real-time data flow. Prevents downstream nodes from executing too frequently from real-time nodes (RealMarketData, RealAccount, etc.).

```json
{
  "id": "throttle",
  "type": "ThrottleNode",
  "mode": "latest",
  "interval_sec": 5,
  "pass_first": true
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `mode` | string | `"latest"` | `skip` (discard data) or `latest` (keep only latest) |
| `interval_sec` | number | `5` | Minimum execution interval (seconds, 0.1~300) |
| `pass_first` | boolean | `true` | Whether to pass first data immediately |

**Mode Comparison:**

| Mode | Behavior | Recommended Use |
|------|----------|----------------|
| `skip` | Discards all data during cooldown | Simply reducing frequency |
| `latest` | Remembers only latest data during cooldown, executes when done | Always reflecting latest state (recommended) |

**Required Usage Rule**: Direct connection from real-time node → order node or real-time node → AI agent is blocked. ThrottleNode must be placed in between.

```
RealAccountNode → ThrottleNode → ConditionNode → OrderNode
```

## SplitNode (Array Splitting)

Splits array data into individual items for one-by-one processing.

```json
{
  "id": "split",
  "type": "SplitNode",
  "parallel": false,
  "delay_ms": 500,
  "continue_on_error": true
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `parallel` | boolean | `false` | Parallel execution |
| `delay_ms` | number | `0` | Wait time between items (milliseconds, 0~60000) |
| `continue_on_error` | boolean | `true` | Continue processing remaining items on error |

**Output**: `item` (current item), `index` (sequence number, 0-based), `total` (total count)

Reference current item with `{{ item }}` in downstream nodes:

```json
{"id": "history", "type": "OverseasStockHistoricalDataNode", "symbol": "{{ item }}"}
```

**Difference from Auto-Iterate**: Even without SplitNode, when a previous node outputs an array, the next node automatically iterates (Auto-Iterate). SplitNode is used when fine-grained control like `parallel`, `delay_ms` is needed.

## AggregateNode (Result Collection)

Collects results split by SplitNode back into one.

```json
{
  "id": "aggregate",
  "type": "AggregateNode",
  "mode": "filter",
  "filter_field": "passed"
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `mode` | string | `"collect"` | Aggregation method |
| `filter_field` | string | `"passed"` | Field to filter by in filter mode |
| `value_field` | string | `"value"` | Target field for sum/avg/min/max |

**mode Options:**

| Mode | Description |
|------|-------------|
| `collect` | Collect all results into an array |
| `filter` | Only items where specific field is true |
| `sum` | Numeric sum |
| `avg` | Numeric average |
| `min` / `max` | Minimum / Maximum value |
| `count` | Count |
| `first` / `last` | First / Last item |

**Output**: `array` (array), `value` (single value), `count` (count)

**Typical Pattern**: `WatchlistNode → SplitNode → HistoricalDataNode → ConditionNode → AggregateNode`

## IfNode (Conditional Branching)

Branches execution flow with if/else conditions in the workflow DAG.

```json
{
  "id": "if-balance",
  "type": "IfNode",
  "left": "{{ nodes.account.balance }}",
  "operator": ">=",
  "right": 1000000
}
```

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `left` | any | O | Left comparison value (expression binding supported) |
| `operator` | string | O | Comparison operator |
| `right` | any | - | Right comparison value (not needed for `is_empty`/`is_not_empty`) |

**Comparison Operators:**

| Operator | Meaning | Example |
|----------|---------|---------|
| `==` | Equal | Status check |
| `!=` | Not equal | Error status check |
| `>`, `>=`, `<`, `<=` | Size comparison | Balance/price comparison |
| `in` | Contained in | Whether symbol is in list |
| `not_in` | Not contained in | Blacklist check |
| `contains` | String contains | Symbol name search |
| `not_contains` | String not contains | Filtering |
| `is_empty` | Is empty | Data existence check |
| `is_not_empty` | Is not empty | Data existence check |

**Output Ports:**
- `true` - When condition is true
- `false` - When condition is false
- `result` - Boolean value

**Branch Routing**: Route branches using the edge's `from_port` field or dot notation:

```json
{
  "edges": [
    {"from": "if-balance", "to": "order", "from_port": "true"},
    {"from": "if-balance", "to": "notify", "from_port": "false"}
  ]
}
```

Or dot notation:

```json
{
  "edges": [
    {"from": "if-balance.true", "to": "order"},
    {"from": "if-balance.false", "to": "notify"}
  ]
}
```

**Cascading Skip**: The entire downstream node chain of inactive branches is automatically skipped. Merge nodes are only skipped when all incoming edges are inactive.

**Typical Pattern**: `AccountNode → IfNode(balance >= 1,000,000) → [true: buy order] / [false: notification]`
