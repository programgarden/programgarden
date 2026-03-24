---
category: api_reference
tags: [api, ExecutionListener, callback, event, on_node_state_change, on_display_data, on_workflow_pnl_update, on_retry, on_llm_stream, on_token_usage, on_ai_tool_call, on_risk_event, on_notification, monitoring]
priority: high
---

# ExecutionListener API

## Overview

`ExecutionListener` (= `BaseExecutionListener`) is a callback interface for receiving events during workflow execution. It supports 12 types of events including node state changes, chart data, PnL updates, AI Agent streaming, investor notifications, and more.

## Basic Usage

```python
from programgarden_core.bases.listener import BaseExecutionListener

class MyListener(BaseExecutionListener):
    """Override only the callbacks you need"""

    async def on_node_state_change(self, event):
        print(f"[{event.node_id}] {event.state}")

    async def on_display_data(self, event):
        print(f"Chart: {event.chart_type} - {event.title}")

# Register listener
listener = MyListener()
job = await executor.execute(workflow, listeners=[listener])

# Or add to Job
job.add_listener(listener)
```

### Constructor

```python
BaseExecutionListener(start_date: Optional[str] = None)
```

- `start_date`: PnL start date (YYYYMMDD format). When specified, the `WorkflowPnLEvent` calculates returns based on this date (`competition_*` fields).

## 12 Callback Details

### 1. on_node_state_change(event: NodeStateEvent)

Called when a node's execution state changes.

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | `str` | Job ID |
| `node_id` | `str` | Node ID |
| `node_type` | `str` | Node type (e.g., "OverseasStockAccountNode") |
| `state` | `NodeState` | PENDING, RUNNING, COMPLETED, FAILED, SKIPPED, THROTTLING |
| `timestamp` | `datetime` | Event time |
| `outputs` | `Optional[Dict]` | Node outputs (only when COMPLETED) |
| `error` | `Optional[str]` | Error message (only when FAILED) |
| `duration_ms` | `Optional[float]` | Execution duration (only when COMPLETED/FAILED) |

```python
async def on_node_state_change(self, event):
    if event.state == "COMPLETED":
        print(f"{event.node_id} completed ({event.duration_ms}ms)")
    elif event.state == "FAILED":
        print(f"{event.node_id} failed: {event.error}")
```

### 2. on_edge_state_change(event: EdgeStateEvent)

Called when an edge's data transmission state changes.

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | `str` | Job ID |
| `from_node_id` | `str` | Source node ID |
| `from_port` | `str` | Source port name |
| `to_node_id` | `str` | Destination node ID |
| `to_port` | `str` | Destination port name |
| `state` | `EdgeState` | IDLE, TRANSMITTING, TRANSMITTED |
| `timestamp` | `datetime` | Event time |
| `data_preview` | `Optional[str]` | Transmitted data preview |

### 3. on_log(event: LogEvent)

Called when a log entry is generated.

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | `str` | Job ID |
| `level` | `str` | debug, info, warning, error |
| `message` | `str` | Log message |
| `timestamp` | `datetime` | Event time |
| `node_id` | `Optional[str]` | Related node ID |
| `data` | `Optional[Dict]` | Additional data |

### 4. on_job_state_change(event: JobStateEvent)

Called when the overall Job state changes.

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | `str` | Job ID |
| `state` | `str` | pending, running, completed, failed, cancelled |
| `timestamp` | `datetime` | Event time |
| `stats` | `Optional[Dict]` | Execution statistics (on completion/failure) |

### 5. on_display_data(event: DisplayDataEvent)

Called when a DisplayNode generates visualization data. Used for rendering charts/tables in the UI.

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | `str` | Job ID |
| `node_id` | `str` | Display node ID |
| `chart_type` | `str` | line, candlestick, bar, scatter, radar, heatmap, table |
| `title` | `Optional[str]` | Chart title |
| `data` | `Any` | Chart data array |
| `x_label` | `Optional[str]` | X-axis label |
| `y_label` | `Optional[str]` | Y-axis label |
| `options` | `Optional[Dict]` | Additional options |
| `data_schema` | `Optional[Dict]` | Data schema |
| `timestamp` | `datetime` | Event time |

### 6. on_workflow_pnl_update(event: WorkflowPnLEvent)

Called when the realtime PnL of workflow positions is updated. Uses FIFO-based tracking to separately track workflow-created positions and manual positions.

**Key fields:**

| Group | Field | Description |
|-------|-------|-------------|
| Basic | `job_id`, `broker_node_id`, `product` | Identification info |
| Workflow PnL | `workflow_pnl_rate`, `workflow_eval_amount`, `workflow_buy_amount`, `workflow_pnl_amount` | Workflow position returns |
| Other PnL | `other_pnl_rate`, `other_eval_amount`, `other_buy_amount`, `other_pnl_amount` | Manual/existing position returns |
| Total PnL | `total_pnl_rate`, `total_eval_amount`, `total_buy_amount`, `total_pnl_amount` | Total account returns |
| Positions | `workflow_positions`, `other_positions` | Detailed position lists |
| Trust | `trust_score` (0-100), `anomaly_count` | Data reliability |
| Per-product | `workflow_overseas_stock_pnl_rate`, `workflow_overseas_futures_pnl_rate`, `workflow_korea_stock_pnl_rate` | Separate overseas stock/futures/korea stock returns |
| Date-based | `competition_start_date`, `competition_workflow_pnl_rate` | Returns from start date |
| Other | `paper_trading`, `currency`, `timestamp` | Metadata |

```python
async def on_workflow_pnl_update(self, event):
    print(f"Workflow PnL: {event.workflow_pnl_rate:.2f}%")
    print(f"Total PnL: {event.total_pnl_rate:.2f}%")
    print(f"Trust score: {event.trust_score}/100")
```

### 7. on_retry(event: RetryEvent)

Called when a node retry occurs. Used for displaying "Retrying (2/3)..." in the UI.

| Field | Type | Description |
|-------|------|-------------|
| `node_id` | `str` | Node ID |
| `attempt` | `int` | Current attempt number |
| `max_retries` | `int` | Maximum retry count |
| `error_type` | `ErrorType` | Error type |
| `next_retry_in` | `float` | Wait time until next retry (seconds) |

### 8. on_token_usage(event: TokenUsageEvent)

Called when an AI Agent LLM call completes and token usage is finalized.

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | `str` | Job ID |
| `node_id` | `str` | AIAgentNode ID |
| `model` | `str` | Model used (e.g., claude-haiku-4-5-20251001) |
| `input_tokens` | `int` | Input token count |
| `output_tokens` | `int` | Output token count |
| `total_tokens` | `int` | Total token count |
| `cost_usd` | `float` | Estimated cost (USD) |
| `timestamp` | `datetime` | Event time |

### 9. on_ai_tool_call(event: AIToolCallEvent)

Triggered when an AI Agent calls a node connected via a Tool edge.

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | `str` | Job ID |
| `node_id` | `str` | AIAgentNode ID |
| `tool_name` | `str` | Tool name |
| `tool_node_id` | `str` | Called tool node ID |
| `tool_input` | `Dict` | Tool input |
| `tool_output` | `Any` | Tool output |
| `duration_ms` | `Optional[float]` | Execution duration |
| `timestamp` | `datetime` | Event time |

### 10. on_llm_stream(event: LLMStreamEvent)

Called on a per-token basis when an AI Agent streams an LLM response. Used for realtime typing effects in the UI.

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | `str` | Job ID |
| `node_id` | `str` | AIAgentNode ID |
| `token` | `str` | Streaming token |
| `is_final` | `bool` | Whether this is the last token |
| `timestamp` | `datetime` | Event time |

### 11. on_risk_event(event: RiskEvent)

Called when a risk threshold is exceeded or a trailing stop is triggered.

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | `str` | Job ID |
| `event_type` | `str` | trailing_stop_triggered, drawdown_alert, etc. |
| `severity` | `str` | info, warning, critical |
| `symbol` | `Optional[str]` | Symbol code |
| `exchange` | `Optional[str]` | Exchange |
| `details` | `Dict` | Detailed information |
| `timestamp` | `datetime` | Event time |

### 12. on_notification(event: NotificationEvent)

Called when an investor-facing notification is generated. Unlike `on_log`, this only fires on meaningful state changes and is designed for end-user alerts.

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | `str` | Job ID |
| `category` | `NotificationCategory` | SIGNAL_TRIGGERED, RISK_ALERT, RISK_HALT, WORKFLOW_STARTED, WORKFLOW_COMPLETED, WORKFLOW_FAILED, RETRY_EXHAUSTED, SCHEDULE_STARTED |
| `severity` | `NotificationSeverity` | INFO, WARNING, CRITICAL |
| `title` | `str` | Notification title |
| `message` | `str` | Notification message |
| `details` | `Optional[Dict]` | Additional details (plugin output fields, risk data, etc.) |
| `timestamp` | `datetime` | Event time |

```python
async def on_notification(self, event):
    if event.severity == "CRITICAL":
        await send_telegram(f"[{event.category}] {event.title}: {event.message}")
    elif event.severity == "WARNING":
        await send_push(event.title, event.message)
```

## Practical Listener Implementation Example

```python
class FullListener(BaseExecutionListener):
    def __init__(self, start_date=None):
        super().__init__(start_date=start_date)
        self.events = []

    async def on_node_state_change(self, event):
        self.events.append({"type": "node", "node": event.node_id, "state": str(event.state)})

    async def on_display_data(self, event):
        # Send chart data to frontend
        await websocket.send_json({
            "type": "chart",
            "chart_type": event.chart_type,
            "title": event.title,
            "data": event.data
        })

    async def on_workflow_pnl_update(self, event):
        # Broadcast realtime PnL
        await websocket.send_json({
            "type": "pnl",
            "workflow_pnl_rate": event.workflow_pnl_rate,
            "total_pnl_rate": event.total_pnl_rate,
            "positions": [p.__dict__ for p in event.workflow_positions]
        })

    async def on_llm_stream(self, event):
        # Realtime AI response streaming
        await websocket.send_json({
            "type": "llm_stream",
            "token": event.token,
            "is_final": event.is_final
        })

    async def on_retry(self, event):
        await websocket.send_json({
            "type": "retry",
            "node_id": event.node_id,
            "attempt": event.attempt,
            "max": event.max_retries
        })

# Track returns from a specific date (with start_date)
listener = FullListener(start_date="20260201")
job = await executor.execute(workflow, listeners=[listener])
```
