---
category: api_reference
tags: [api, WorkflowExecutor, WorkflowJob, execute, validate, compile, secrets, listeners, resource_limits, job, context, programming]
priority: high
---

# WorkflowExecutor API

## Overview

`WorkflowExecutor` is the core class for validating, compiling, and executing ProgramGarden workflows. It is used to programmatically run workflows from Python code.

## Basic Usage

```python
from programgarden import WorkflowExecutor

# 1. Create Executor
executor = WorkflowExecutor()

# 2. Define workflow (JSON dict)
workflow = {
    "nodes": [
        {"id": "start", "type": "StartNode"},
        {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "cred-1"},
        {"id": "account", "type": "OverseasStockAccountNode"}
    ],
    "edges": [
        {"from": "start", "to": "broker"},
        {"from": "broker", "to": "account"}
    ],
    "credentials": [
        {
            "credential_id": "cred-1",
            "type": "broker_ls_overseas_stock",
            "data": [
                {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"}
            ]
        }
    ]
}

# 3. Execute
job = await executor.execute(
    definition=workflow,
    secrets={"cred-1": {"appkey": "YOUR_KEY", "appsecret": "YOUR_SECRET"}},
)

# 4. Wait for completion
import asyncio
await asyncio.wait_for(job._task, timeout=60)

# 5. Retrieve results
outputs = job.context.get_all_outputs("account")
print(outputs)  # {"balance": {...}, "positions": [...]}
```

## WorkflowExecutor Methods

### validate(definition) → ValidationResult

Validates the structural validity of a workflow definition.

```python
result = executor.validate(workflow)

if result.is_valid:
    print("Valid workflow")
else:
    for error in result.errors:
        print(f"Error: {error}")
    for warning in result.warnings:
        print(f"Warning: {warning}")
```

**Return value**: `ValidationResult`
- `is_valid: bool` - Whether the workflow is valid
- `errors: List[str]` - List of errors (execution is blocked if any exist)
- `warnings: List[str]` - List of warnings (execution is possible but caution is needed)

### compile(definition, context_params) → (ResolvedWorkflow, ValidationResult)

Compiles the workflow into an execution object. Performs validate + internal object conversion.

```python
resolved, result = executor.compile(
    definition=workflow,
    context_params={"dry_run": True}
)

if result.is_valid and resolved:
    print("Compilation successful")
```

**Parameters**:
- `definition: Dict` - Workflow definition
- `context_params: Optional[Dict]` - Execution context parameters

### execute(definition, ...) → WorkflowJob

Executes a workflow asynchronously.

```python
job = await executor.execute(
    definition=workflow,
    context_params=None,
    secrets={"cred-1": {"appkey": "...", "appsecret": "..."}},
    job_id=None,
    listeners=[my_listener],
    resource_limits=None,
    storage_dir=None,
)
```

**Parameters**:

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `definition` | `Dict` | Workflow definition (JSON dict) | Required |
| `context_params` | `Optional[Dict]` | Runtime parameters (symbols, dry_run, etc.) | None |
| `secrets` | `Optional[Dict]` | Sensitive credentials (never logged) | None |
| `job_id` | `Optional[str]` | Job ID (auto-generated if not specified) | None |
| `listeners` | `Optional[List[ExecutionListener]]` | List of state callback listeners | None |
| `resource_limits` | `Optional[ResourceLimits]` | Resource limits (CPU, RAM). None = auto-detect | None |
| `storage_dir` | `Optional[str]` | DB/file storage path. None = auto (/app/data or ./app/data) | None |

### secrets Format

`secrets` is a dictionary with `credential_id` as keys and the corresponding credentials as values:

```python
secrets = {
    "broker-cred": {
        "appkey": "YOUR_APPKEY",
        "appsecret": "YOUR_APPSECRET"
    },
    "llm-cred": {
        "api_key": "YOUR_ANTHROPIC_KEY"
    }
}
```

## WorkflowJob API

Returned by `execute()`, it manages the state and results of the running workflow.

### Key Properties

| Property | Type | Description |
|----------|------|-------------|
| `job_id` | `str` | Unique Job ID |
| `status` | `str` | Status: pending, running, completed, failed, stopping, cancelled |
| `started_at` | `Optional[datetime]` | Start time |
| `completed_at` | `Optional[datetime]` | Completion time |
| `workflow_start_datetime` | `datetime` | Workflow start reference time (UTC, for PnL tracking) |
| `context` | `ExecutionContext` | Context for accessing node output data |
| `stats` | `Dict[str, int]` | Execution statistics |

### stats Fields

```python
job.stats = {
    "conditions_evaluated": 0,   # Number of condition evaluations
    "orders_placed": 0,          # Number of orders placed
    "orders_filled": 0,          # Number of orders filled
    "errors_count": 0,           # Number of errors
    "flow_executions": 0,        # Number of flow executions
    "realtime_updates": 0,       # Number of realtime updates
}
```

### add_listener(listener) → self

Adds a listener. Supports chaining.

```python
job.add_listener(state_listener).add_listener(pnl_listener)
```

### remove_listener(listener) → self

Removes a listener.

### start() → None

Starts execution (automatically called internally by execute).

### stop() → None

Safely stops execution.

```python
await job.stop()  # Cleans up realtime subscriptions then stops
```

### Retrieving Results

```python
# Get all outputs of a specific node
outputs = job.context.get_all_outputs("account")
# {"balance": {...}, "positions": [...]}

# Wait for completion
import asyncio
await asyncio.wait_for(job._task, timeout=120)
```

## Workflow Execution Modes

| Mode | Description | Behavior |
|------|-------------|----------|
| **One-shot** | No realtime nodes | Completes automatically after all nodes execute |
| **Realtime** | Includes RealMarketDataNode, etc. | Maintains subscriptions, runs until stop() is called |
| **Schedule** | Includes ScheduleNode | Executes repeatedly based on cron schedule |
| **Mixed** | Realtime + Schedule combined | Both modes operate simultaneously |

## Full Example: Execution with Listener

```python
import asyncio
from programgarden import WorkflowExecutor
from programgarden_core.bases.listener import BaseExecutionListener

class MyListener(BaseExecutionListener):
    async def on_node_state_change(self, event):
        print(f"[{event.node_id}] {event.state}")

    async def on_job_state_change(self, event):
        print(f"Job: {event.state}")

async def main():
    executor = WorkflowExecutor()
    listener = MyListener()

    workflow = {
        "nodes": [
            {"id": "start", "type": "StartNode"},
            {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "cred-1"},
            {"id": "account", "type": "OverseasStockAccountNode"},
            {"id": "table", "type": "TableDisplayNode", "title": "Balance", "data": "{{ nodes.account.positions }}"}
        ],
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "account"},
            {"from": "account", "to": "table"}
        ],
        "credentials": [{"credential_id": "cred-1", "type": "broker_ls_overseas_stock", "data": []}]
    }

    job = await executor.execute(
        definition=workflow,
        secrets={"cred-1": {"appkey": "KEY", "appsecret": "SECRET"}},
        listeners=[listener],
    )

    await asyncio.wait_for(job._task, timeout=60)
    print(f"Status: {job.status}, Stats: {job.stats}")

asyncio.run(main())
```
