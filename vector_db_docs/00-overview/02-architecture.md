---
category: overview
tags: [architecture, package, executor]
priority: high
---

# Architecture and Package Structure

## Package Structure

ProgramGarden consists of 4 independent Python packages:

```
src/
├── core/               # programgarden-core: node types, base classes, registry, i18n
├── finance/            # programgarden-finance: LS Securities API wrapper (overseas stock, futures, Korea stock)
├── community/          # programgarden-community: strategy plugins (RSI, MACD, etc.)
└── programgarden/      # programgarden: main package (workflow execution engine)
```

### Package Dependency Rules

| Package | Role | Dependencies |
|---------|------|-------------|
| `core` | Node definitions, base classes, registry, i18n | **None** (independent) |
| `finance` | LS Securities OpenAPI wrapper, real-time WebSocket | Depends on `core` only |
| `community` | Strategy plugins (RSI, MACD, etc.) | Depends on `core` only |
| `programgarden` | Workflow execution engine, Executor | Integrates all packages |

### Detailed Package Structure

#### core Package
```
programgarden_core/
├── nodes/          # Node definitions (68 core + 4 community = 72 nodes)
├── bases/          # Base classes: BaseNode, BaseExecutionListener, etc.
├── models/         # Pydantic models (FieldSchema, etc.)
├── registry/       # Node and plugin registries
└── i18n/locales/   # Translation files (ko.json, en.json)
```

#### programgarden Main Package
```
programgarden/
├── programgarden/  # Core module
│   ├── executor.py    # WorkflowExecutor (workflow execution)
│   ├── context.py     # ExecutionContext (execution context)
│   └── resolver.py    # Expression resolver
└── examples/
    └── python_server/ # FastAPI backend server example
```

## Execution Architecture

### WorkflowExecutor

The entry point for workflow execution:

```python
from programgarden import WorkflowExecutor

executor = WorkflowExecutor()
job = await executor.execute(workflow_json)
```

### Execution Flow

1. **JSON Parsing**: Convert workflow JSON into node/edge objects
2. **DAG Construction**: Determine execution order (DAG) based on edge information
3. **Credential Injection**: Inject credentials referenced by `credential_id` into corresponding nodes
4. **Broker Propagation**: Automatically propagate BrokerNode connection info to downstream nodes
5. **Expression Evaluation**: Evaluate `{{ }}` expressions at execution time
6. **Auto-Iterate**: When array output, automatically iterate next node for each item
7. **Result Collection**: Store each node's output in `context`

### ExecutionContext

Manages data sharing and state between nodes during execution:

- `context.get_all_outputs(node_id)`: Get all outputs from a specific node
- `context.risk_tracker`: Access risk management data (opt-in)
- Node outputs are referenced via `{{ nodes.nodeId.port }}` expressions

### ExecutionListener

A callback system that delivers workflow execution events externally:

| Callback | Description |
|----------|-------------|
| `on_node_state_change` | Node state change (pending/running/completed/failed) |
| `on_edge_state_change` | Edge state change |
| `on_log` | Log events |
| `on_job_state_change` | Job state change |
| `on_display_data` | Display data (charts, tables, etc.) |
| `on_workflow_pnl_update` | Real-time P&L update |
| `on_retry` | Node retry event |
| `on_token_usage` | AI Agent token usage |
| `on_ai_tool_call` | AI Agent tool call |
| `on_llm_stream` | AI Agent streaming chunk |
| `on_risk_event` | Risk threshold breach |
| `on_notification` | Investor notification (signal, risk, workflow state, schedule, retry exhausted) |

## Data Storage

| Purpose | Path | Format |
|---------|------|--------|
| Per-workflow DB | `{workflow_id}_workflow.db` | SQLite |
| Docker environment | `/app/data/` | - |
| Local environment | `./app/data/` (fallback) | - |

## Development Commands

```bash
# Run tests
cd src/core && poetry run pytest tests/
cd src/programgarden && poetry run pytest tests/

# Run server (port 8766)
cd src/programgarden && poetry run python examples/python_server/server.py
```
