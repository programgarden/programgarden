---
category: execution
tags: [listener, callback, event, state_change, ExecutionListener, NodeStateEvent, EdgeStateEvent, LogEvent, JobStateEvent, DisplayDataEvent, WorkflowPnLEvent, RetryEvent, TokenUsageEvent, AIToolCallEvent, LLMStreamEvent, RiskEvent, NotificationEvent]
priority: high
---

# ExecutionListener Callbacks

## Overview

`ExecutionListener` is a protocol for receiving events that occur during workflow execution. It monitors node states, logs, P&L updates, AI Agent activity, and more through 12 callback methods.

## Listener Registration

### Registration at execute() Time

```python
job = await executor.execute(
    definition=workflow_json,
    listeners=[my_listener1, my_listener2],
)
```

### Direct Registration on Job (Chaining)

```python
job.add_listener(listener1).add_listener(listener2)
job.remove_listener(listener1)
```

## Listener Implementation

### Inheriting BaseExecutionListener

```python
from programgarden_core.bases.listener import BaseExecutionListener

class MyListener(BaseExecutionListener):
    """Override only the callbacks you need"""

    async def on_node_state_change(self, event):
        print(f"Node {event.node_id}: {event.state.value}")

    async def on_log(self, event):
        print(f"[{event.level}] {event.message}")
```

`BaseExecutionListener` has empty implementations (no-op) for all callbacks, so you only need to override the ones you need.

## 12 Callback Methods

### 1. on_node_state_change(event: NodeStateEvent)

Called when a node's execution state changes.

```python
async def on_node_state_change(self, event: NodeStateEvent):
    print(f"{event.node_id}: {event.state.value}")
    if event.outputs:
        print(f"  Outputs: {event.outputs}")
    if event.error:
        print(f"  Error: {event.error}")
```

**NodeState enum**:

| State | Value | Description |
|-------|-------|-------------|
| `PENDING` | `"pending"` | Waiting |
| `RUNNING` | `"running"` | Executing |
| `COMPLETED` | `"completed"` | Completed |
| `FAILED` | `"failed"` | Failed |
| `SKIPPED` | `"skipped"` | Skipped (Fallback SKIP) |
| `WAITING` | `"waiting"` | Waiting (schedule/trigger) |

**NodeStateEvent fields**:

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | str | Job ID |
| `node_id` | str | Node ID |
| `node_type` | str | Node type name |
| `state` | NodeState | Current state |
| `outputs` | dict (optional) | Node outputs (on COMPLETED) |
| `error` | str (optional) | Error message (on FAILED) |

### 2. on_edge_state_change(event: EdgeStateEvent)

Called when an edge (connection) state changes.

**EdgeState enum**:

| State | Value | Description |
|-------|-------|-------------|
| `IDLE` | `"idle"` | Idle |
| `ACTIVE` | `"active"` | Data transfer in progress |
| `COMPLETED` | `"completed"` | Transfer completed |

**EdgeStateEvent fields**:

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | str | Job ID |
| `from_node` | str | Source node ID |
| `to_node` | str | Destination node ID |
| `state` | EdgeState | Current state |
| `edge_type` | str | Edge type (`"main"`, `"ai_model"`, `"tool"`) |

### 3. on_log(event: LogEvent)

Called when a log event occurs.

**LogEvent fields**:

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | str | Job ID |
| `level` | str | Log level (`"debug"`, `"info"`, `"warning"`, `"error"`) |
| `message` | str | Log message |
| `node_id` | str (optional) | Related node ID |

### 4. on_job_state_change(event: JobStateEvent)

Called when the overall Job state changes.

**JobStateEvent fields**:

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | str | Job ID |
| `state` | str | `"running"`, `"completed"`, `"failed"`, `"stopped"` |
| `stats` | dict | Execution statistics |
| `error` | str (optional) | Error message |

### 5. on_display_data(event: DisplayDataEvent)

Called when a Display node outputs data for UI rendering.

**DisplayDataEvent fields**:

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | str | Job ID |
| `node_id` | str | Display node ID |
| `display_type` | str | Chart type (`"table"`, `"line_chart"`, `"candlestick"`, `"bar_chart"`, `"summary"`) |
| `data` | Any | Data to display |
| `config` | dict | Chart configuration |

### 6. on_workflow_pnl_update(event: WorkflowPnLEvent)

Called when real-time workflow/account P&L is updated. Uses FIFO-based tracking to separate workflow-created positions from manual positions.

**WorkflowPnLEvent fields**:

| Group | Field | Type | Description |
|-------|-------|------|-------------|
| Basic | `job_id` | str | Job ID |
| | `broker_node_id` | str | BrokerNode ID |
| | `product` | str | `"overseas_stock"`, `"overseas_futures"`, or `"korea_stock"` |
| | `paper_trading` | bool | `true`: paper, `false`: live (korea_stock always `false`) |
| | `currency` | str | `"USD"` (overseas) or `"KRW"` (korea_stock) |
| Workflow PnL | `workflow_pnl_rate` | Decimal/float | Workflow position P&L rate (%) |
| | `workflow_eval_amount` | Decimal/float | Workflow evaluation amount |
| | `workflow_buy_amount` | Decimal/float | Workflow buy amount |
| | `workflow_pnl_amount` | Decimal/float | Workflow P&L amount |
| Other PnL | `other_pnl_rate` | Decimal/float | Other (manual) position P&L rate (%) |
| | `other_eval_amount` | Decimal/float | Other evaluation amount |
| | `other_buy_amount` | Decimal/float | Other buy amount |
| | `other_pnl_amount` | Decimal/float | Other P&L amount |
| Total PnL | `total_pnl_rate` | Decimal/float | Total account P&L rate (%) |
| | `total_eval_amount` | Decimal/float | Total evaluation amount |
| | `total_buy_amount` | Decimal/float | Total buy amount |
| | `total_pnl_amount` | Decimal/float | Total P&L amount |
| Positions | `workflow_positions` | list[PositionDetail] | Workflow position details |
| | `other_positions` | list[PositionDetail] | Other (manual) position details |
| Trust | `trust_score` | int (0-100) | Data reliability score |
| | `anomaly_count` | int | Detected anomaly count |
| Per-product | `workflow_overseas_stock_pnl_rate` | Decimal? | Overseas stock workflow P&L (%) |
| | `workflow_overseas_futures_pnl_rate` | Decimal? | Overseas futures workflow P&L (%) |
| | `workflow_korea_stock_pnl_rate` | Decimal? | Korea stock workflow P&L (%) |
| Account | `account_total_pnl_rate` | Decimal? | Entire account P&L rate (%) |
| | `account_overseas_stock_pnl_rate` | Decimal? | Overseas stock account P&L (%) |
| | `account_overseas_futures_pnl_rate` | Decimal? | Overseas futures account P&L (%) |
| | `account_korea_stock_pnl_rate` | Decimal? | Korea stock account P&L (%) |
| | `total_position_count` | int? | Total held position count |
| Competition | `competition_start_date` | str? | Competition start date (YYYYMMDD) |
| | `competition_workflow_pnl_rate` | Decimal? | Workflow P&L from start date (%) |
| | `competition_account_pnl_rate` | Decimal? | Account P&L from start date (%) |
| Metadata | `workflow_start_datetime` | datetime? | Workflow start time |
| | `workflow_elapsed_days` | int? | Days since workflow started |
| | `timestamp` | datetime | Event timestamp |

**PositionDetail fields**:

| Field | Type | Description |
|-------|------|-------------|
| `symbol` | str | Stock symbol |
| `exchange` | str | Exchange (`NASDAQ`, `NYSE`, `KRX`, etc.) |
| `quantity` | int | Held quantity |
| `avg_price` | Decimal/float | Average purchase price |
| `current_price` | Decimal/float | Current price |
| `pnl_amount` | Decimal/float | Profit/loss amount |
| `pnl_rate` | Decimal/float | P&L rate (%) |

### 7. on_retry(event: RetryEvent)

Called when a node retry occurs.

**RetryEvent fields**:

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | str | Job ID |
| `node_id` | str | Node ID |
| `attempt` | int | Current attempt count |
| `max_retries` | int | Maximum retry count |
| `error_type` | RetryableError | Error type |
| `error_message` | str | Error message |
| `next_retry_in` | float | Wait time until next retry (seconds) |

### 8. on_token_usage(event: TokenUsageEvent)

LLM token usage event for AI Agent.

**TokenUsageEvent fields**:

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | str | Job ID |
| `node_id` | str | AIAgentNode ID |
| `model` | str | LLM model name |
| `prompt_tokens` | int | Input token count |
| `completion_tokens` | int | Output token count |
| `total_tokens` | int | Total token count |
| `cost_usd` | float | Estimated cost (USD) |

### 9. on_ai_tool_call(event: AIToolCallEvent)

Triggered when the AI Agent calls a Tool.

**AIToolCallEvent fields**:

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | str | Job ID |
| `node_id` | str | AIAgentNode ID |
| `tool_name` | str | Called Tool name |
| `tool_args` | dict | Tool arguments |
| `tool_result` | Any | Tool execution result |
| `duration_ms` | float | Execution time (ms) |
| `success` | bool | Success status |

### 10. on_llm_stream(event: LLMStreamEvent)

Called when a chunk of the AI Agent's streaming response arrives.

**LLMStreamEvent fields**:

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | str | Job ID |
| `node_id` | str | AIAgentNode ID |
| `chunk` | str | Text chunk |
| `is_final` | bool | Whether this is the final chunk |

### 11. on_risk_event(event: RiskEvent)

Called when a risk management event occurs.

**RiskEvent fields**:

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | str | Job ID |
| `node_id` | str | Related node ID |
| `event_type` | str | Event type (`"drawdown_alert"`, `"trailing_stop_trigger"`, etc.) |
| `severity` | str | Severity (`"info"`, `"warning"`, `"critical"`) |
| `symbol` | str (optional) | Related symbol |
| `details` | dict | Detailed information |

### 12. on_notification(event: NotificationEvent)

Called when an investor-facing notification is generated. Separate from `on_log` — only fires on meaningful state changes (signal triggered, risk alert, workflow state change, etc.).

**NotificationEvent fields**:

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | str | Job ID |
| `category` | NotificationCategory | SIGNAL_TRIGGERED, RISK_ALERT, RISK_HALT, WORKFLOW_STARTED, WORKFLOW_COMPLETED, WORKFLOW_FAILED, RETRY_EXHAUSTED, SCHEDULE_STARTED |
| `severity` | NotificationSeverity | INFO, WARNING, CRITICAL |
| `title` | str | Notification title |
| `message` | str | Notification message |
| `details` | dict (optional) | Additional details (plugin outputs, risk data, etc.) |

## ConsoleExecutionListener

A built-in listener that prints events to the console. Used for debugging and development.

```python
from programgarden_core.bases.listener import ConsoleExecutionListener

job = await executor.execute(
    definition=workflow_json,
    listeners=[ConsoleExecutionListener()],
)
```

Output example:
```
[node] broker: running
[node] broker: completed
[edge] broker → account: active
[node] account: running
[log][info] Balance query completed: 3 symbols
[node] account: completed
[job] running → completed
```

## Custom Listener Patterns

### WebSocket Real-time Forwarding

```python
class WebSocketListener(BaseExecutionListener):
    def __init__(self, websocket):
        self.ws = websocket

    async def on_node_state_change(self, event):
        await self.ws.send_json({
            "type": "node_state",
            "node_id": event.node_id,
            "state": event.state.value,
            "outputs": event.outputs,
        })

    async def on_log(self, event):
        await self.ws.send_json({
            "type": "log",
            "level": event.level,
            "message": event.message,
        })

    async def on_workflow_pnl_update(self, event):
        await self.ws.send_json({
            "type": "pnl_update",
            "workflow_pnl_rate": event.workflow_pnl_rate,
            "total_pnl_rate": event.total_pnl_rate,
            "positions": [
                {"symbol": p.symbol, "pnl_rate": p.pnl_rate}
                for p in event.workflow_positions
            ],
        })
```

### DB Logging

```python
class DBLogListener(BaseExecutionListener):
    async def on_log(self, event):
        await db.insert("logs", {
            "job_id": event.job_id,
            "level": event.level,
            "message": event.message,
            "node_id": event.node_id,
            "timestamp": datetime.utcnow(),
        })

    async def on_job_state_change(self, event):
        await db.update("jobs",
            {"job_id": event.job_id},
            {"state": event.state, "stats": event.stats},
        )
```

## Event Flow Examples

### Simple Workflow Execution

```
on_job_state_change(state="running")
on_node_state_change(broker, RUNNING)
on_node_state_change(broker, COMPLETED)
on_edge_state_change(broker→account, ACTIVE)
on_node_state_change(account, RUNNING)
on_log(info, "Balance query completed")
on_node_state_change(account, COMPLETED)
on_edge_state_change(broker→account, COMPLETED)
on_job_state_change(state="completed")
```

### AI Agent Execution

```
on_node_state_change(agent, RUNNING)
on_token_usage(prompt_tokens=500, completion_tokens=100)
on_ai_tool_call(tool_name="overseas_stock_market_data_node", duration_ms=230)
on_token_usage(prompt_tokens=800, completion_tokens=200)
on_node_state_change(agent, COMPLETED)
```

### Retry Occurrence

```
on_node_state_change(market, RUNNING)
on_retry(attempt=1, error_type=TIMEOUT, next_retry_in=1.2)
on_retry(attempt=2, error_type=TIMEOUT, next_retry_in=2.5)
on_node_state_change(market, COMPLETED)
```
