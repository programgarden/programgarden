---
category: execution
tags: [executor, api, execute, validate, compile, job, WorkflowExecutor, WorkflowJob, listeners, context_params, secrets, dynamic]
priority: high
---

# WorkflowExecutor API

## Overview

`WorkflowExecutor` is the execution engine for ProgramGarden workflows. It receives a workflow definition (JSON) and handles the entire process of validation, compilation, and execution. It supports dynamic node injection and 24-hour continuous execution.

## Basic Usage

```python
from programgarden import WorkflowExecutor

executor = WorkflowExecutor()

# 1. Validate
validation = executor.validate(workflow_json)
if not validation.is_valid:
    print(validation.errors)

# 2. Execute
job = await executor.execute(
    definition=workflow_json,
    secrets={"appkey": "...", "appsecret": "..."},
    listeners=[my_listener],
)

# 3. Wait for completion
import asyncio
result = await asyncio.wait_for(job._task, timeout=300)
```

## WorkflowExecutor Methods

### validate(definition)

Validates the workflow definition.

```python
validation = executor.validate(workflow_json)
# → ValidationResult(is_valid=True/False, errors=[...], warnings=[...])
```

**Validation checks**:
- Required node existence (nodes, edges)
- Node type validity (registered nodes + dynamic nodes)
- Edge connection validity (connections between existing nodes)
- credential_id reference validity
- Dynamic node `Dynamic_` prefix verification
- Dynamic node credential_id usage prohibition
- Real-time node → AIAgentNode direct connection prohibition

### compile(definition, context_params)

Converts a workflow definition into an executable `ResolvedWorkflow` object.

```python
resolved, validation = executor.compile(workflow_json, context_params={"symbol": "AAPL"})
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `definition` | dict | Workflow JSON |
| `context_params` | dict (optional) | Runtime parameters |

### execute(definition, ...)

Executes a workflow asynchronously. Returns a `WorkflowJob`.

```python
job = await executor.execute(
    definition=workflow_json,
    context_params={"symbol": "AAPL"},
    secrets={"appkey": "...", "appsecret": "..."},
    job_id="my-job-1",
    listeners=[my_listener],
    storage_dir="/app/data",
)
```

| Parameter | Type | Required | Description |
|-----------|------|:--------:|-------------|
| `definition` | dict | O | Workflow JSON (nodes, edges, credentials, notes) |
| `context_params` | dict | - | Runtime parameters (symbols, dry_run, etc.) |
| `secrets` | dict | - | Sensitive authentication info (appkey, appsecret, etc.). Not recorded in logs |
| `job_id` | string | - | Job ID. Auto-generated as `job-{uuid}` if not specified |
| `listeners` | list | - | List of `ExecutionListener` instances |
| `resource_limits` | ResourceLimits | - | Resource limits (CPU, RAM, workers). None = auto-detect |
| `storage_dir` | string | - | DB/file storage directory. None = `/app/data` or `./app/data` |

**Execution flow**:
```
1. compile() → ResolvedWorkflow + ValidationResult
2. Raises ValueError on validation failure
3. ResourceContext setup (auto-detect)
4. ExecutionContext creation (job_id, secrets, listeners, etc.)
5. WorkflowJob creation + start
6. DAG-based sequential/parallel node execution
```

**Note**: Duplicate execution with the same `job_id` raises `DuplicateJobIdError`.

### execute_node(node_id, node_type, config, context, ...)

Executes a single node directly. Primarily used internally.

```python
result = await executor.execute_node(
    node_id="rsi-1",
    node_type="ConditionNode",
    config={"plugin": "RSI", "data": [...]},
    context=context,
)
```

A dedicated Executor matching the node type is used. If no dedicated Executor exists, it falls back to `GenericNodeExecutor`.

### get_job(job_id) / list_jobs()

```python
job = executor.get_job("my-job-1")   # Get a specific Job
jobs = executor.list_jobs()           # List all Jobs
```

### Dynamic Node API

| Method | Description |
|--------|-------------|
| `register_dynamic_schemas(schemas)` | Register dynamic node schemas (for UI display) |
| `get_required_dynamic_types(workflow)` | List of dynamic node types required by the workflow |
| `inject_node_classes(classes)` | Inject node classes (with validation) |
| `is_dynamic_node_ready(type)` | Check if schema is registered and class is injected |
| `list_dynamic_node_types()` | List of registered dynamic node types |
| `clear_injected_classes()` | Clear injected classes (memory cleanup) |

## WorkflowJob

A workflow execution instance. Returned by `execute()`.

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `job_id` | string | Unique Job ID |
| `status` | string | `"pending"`, `"running"`, `"completed"`, `"failed"`, `"stopped"` |
| `started_at` | datetime | Start time |
| `completed_at` | datetime | Completion time |
| `workflow_start_datetime` | datetime | Workflow start time (UTC, for PnL tracking) |
| `context` | ExecutionContext | Execution context |
| `stats` | dict | Execution statistics |

### stats Fields

```python
{
    "conditions_evaluated": 0,   # Number of conditions evaluated
    "orders_placed": 0,          # Number of orders placed
    "orders_filled": 0,          # Number of orders filled
    "errors_count": 0,           # Number of errors occurred
    "flow_executions": 0,        # Number of DAG flow executions
    "realtime_updates": 0,       # Number of real-time updates
}
```

### Execution Modes

The workflow operates in 4 modes depending on its structure:

| ScheduleNode | stay_connected | Execution Mode |
|:---:|:---:|------|
| None | False | One-shot: Execute once and terminate |
| None | True | Continuous: Maintained until `stop()` is called |
| Present | False | Scheduled: Execute per schedule, disconnected between runs |
| Present | True | Scheduled + Realtime: Scheduled execution + real-time connection maintained |

### Methods

```python
# Add listener (supports chaining)
job.add_listener(listener1).add_listener(listener2)

# Remove listener
job.remove_listener(listener1)

# Start execution (automatically called by execute())
await job.start()

# Wait for result (using asyncio)
import asyncio
result = await asyncio.wait_for(job._task, timeout=300)

# Query outputs
outputs = job.context.get_all_outputs("node_id")
```

**Note**: There is no `job.wait()` method. Use the `asyncio.wait_for(job._task, timeout)` pattern.

## ExecutionContext

A context object shared during node execution.

### Key Functions

| Function | Description |
|----------|-------------|
| `get_input(name)` | Get data from an input port |
| `get_all_outputs(node_id)` | Query all outputs of a specific node |
| `log(level, message, node_id)` | Record log + notify listeners |
| `set_listeners(listeners)` | Set listener list |
| `add_listener(listener)` | Add a listener |
| `remove_listener(listener)` | Remove a listener |
| `notify_retry(event)` | Notify listeners of a retry event |
| `notify_job_state(state, stats)` | Notify listeners of a Job state change |

### Properties

| Property | Description |
|----------|-------------|
| `job_id` | Current Job ID |
| `workflow_id` | Workflow ID |
| `context_params` | Runtime parameters |
| `secrets` | Authentication credentials |
| `risk_tracker` | WorkflowRiskTracker (None if no features declared) |

## Dedicated Executor Mapping

Each node type is assigned a dedicated Executor:

| Executor | Node |
|----------|------|
| `StartNodeExecutor` | StartNode |
| `BrokerNodeExecutor` | OverseasStockBrokerNode, OverseasFuturesBrokerNode |
| `AccountNodeExecutor` | OverseasStockAccountNode, OverseasFuturesAccountNode |
| `MarketDataNodeExecutor` | OverseasStockMarketDataNode, OverseasFuturesMarketDataNode |
| `RealMarketDataNodeExecutor` | OverseasStockRealMarketDataNode, OverseasFuturesRealMarketDataNode |
| `RealAccountNodeExecutor` | OverseasStockRealAccountNode, OverseasFuturesRealAccountNode |
| `HistoricalDataNodeExecutor` | OverseasStockHistoricalDataNode, OverseasFuturesHistoricalDataNode |
| `NewOrderNodeExecutor` | OverseasStockNewOrderNode, OverseasFuturesNewOrderNode |
| `ModifyOrderNodeExecutor` | OverseasStockModifyOrderNode, OverseasFuturesModifyOrderNode |
| `CancelOrderNodeExecutor` | OverseasStockCancelOrderNode, OverseasFuturesCancelOrderNode |
| `ConditionNodeExecutor` | ConditionNode |
| `LogicNodeExecutor` | LogicNode |
| `DisplayNodeExecutor` | All Display nodes |
| `ScheduleNodeExecutor` | ScheduleNode |
| `ThrottleNodeExecutor` | ThrottleNode |
| `LLMModelNodeExecutor` | LLMModelNode |
| `AIAgentNodeExecutor` | AIAgentNode |
| `GenericNodeExecutor` | Nodes without a dedicated Executor (fallback) |

## Workflow Definition Structure

```json
{
  "nodes": [
    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker-cred"},
    {"id": "account", "type": "OverseasStockAccountNode"},
    {"id": "market", "type": "OverseasStockMarketDataNode", "symbol": "AAPL", "exchange": "NASDAQ"}
  ],
  "edges": [
    {"from": "broker", "to": "account"},
    {"from": "broker", "to": "market"}
  ],
  "credentials": [
    {
      "credential_id": "broker-cred",
      "type": "broker_ls_overseas_stock",
      "data": [
        {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
        {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"}
      ]
    }
  ],
  "notes": [
    {"id": "note-1", "content": "## Memo", "color": 1, "width": 300, "height": 200, "position": {"x": 100, "y": 50}}
  ]
}
```

### credentials Section

Authentication information is defined in the `credentials` field of the workflow JSON and referenced by `credential_id` in nodes:

| Field | Description |
|-------|-------------|
| `credential_id` | Unique ID (referenced by nodes) |
| `type` | Credential type |
| `data` | Authentication field array `[{key, value, type, label}]` |

**Credential types**:

| type | Purpose |
|------|---------|
| `broker_ls_overseas_stock` | LS Securities overseas stocks |
| `broker_ls_overseas_futures` | LS Securities overseas futures |
| `llm_openai` | OpenAI API |
| `llm_anthropic` | Anthropic API |
| `llm_google` | Google AI API |
| `llm_azure_openai` | Azure OpenAI |
| `llm_ollama` | Ollama (local LLM) |

### notes Section

Memos (sticky notes) on the workflow canvas. They do not affect execution:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Note ID |
| `content` | string | Content (supports Markdown) |
| `color` | integer | Color (0~7) |
| `width` | integer | Width (px) |
| `height` | integer | Height (px) |
| `position` | object | Position `{x, y}` |

## secrets Passing Method

When calling `execute()`, values passed in `secrets` fill in the empty values of credential fields:

```python
job = await executor.execute(
    definition=workflow_json,
    secrets={
        "appkey": "actual_app_key",
        "appsecret": "actual_secret",
        "api_key": "openai_api_key",
    },
)
```

`secrets` are not recorded in logs and fill in empty `value` fields in `credential.data` at runtime.

## Complete Execution Example

```python
from programgarden import WorkflowExecutor
import asyncio

async def main():
    executor = WorkflowExecutor()

    workflow = {
        "nodes": [
            {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "cred"},
            {"id": "account", "type": "OverseasStockAccountNode"},
            {"id": "market", "type": "OverseasStockMarketDataNode",
             "symbol": "AAPL", "exchange": "NASDAQ"},
        ],
        "edges": [
            {"from": "broker", "to": "account"},
            {"from": "broker", "to": "market"},
        ],
        "credentials": [{
            "credential_id": "cred",
            "type": "broker_ls_overseas_stock",
            "data": [
                {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
            ],
        }],
    }

    # Validate
    validation = executor.validate(workflow)
    if not validation.is_valid:
        print(f"Error: {validation.errors}")
        return

    # Execute
    job = await executor.execute(
        definition=workflow,
        secrets={"appkey": "my-key", "appsecret": "my-secret"},
    )

    # Wait for completion
    try:
        result = await asyncio.wait_for(job._task, timeout=60)
        print(f"Completed: {job.stats}")
    except asyncio.TimeoutError:
        print("Timeout")

    # Query outputs
    account_data = job.context.get_all_outputs("account")
    market_data = job.context.get_all_outputs("market")

asyncio.run(main())
```
