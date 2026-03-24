---
category: dynamic_node
tags: [dynamic, injection, schema, runtime, Dynamic_, BaseNode, register_dynamic_schemas, inject_node_classes, credential_id]
priority: high
---

# Dynamic Node Injection Guide

## Overview

Dynamic Node Injection allows external users to **inject custom nodes at runtime** and use them in workflows without contributing to the `community` package. This is utilized in scenarios where an AI chatbot generates and executes code tailored to user requirements.

## Naming Convention

Dynamic nodes must use the **`Dynamic_` prefix**:

```
Dynamic_MyRSI        (O)
Dynamic_CustomMACD   (O)
MyRSI                (X) - No prefix, error raised
```

This is a mandatory rule for preventing collisions with existing nodes and identifying dynamic nodes.

## Usage Flow (Lazy Loading)

```
1. App start:  register_dynamic_schemas() → Register schemas only (for UI display)
2. Pre-run:    get_required_dynamic_types() → Check required dynamic nodes
3. Pre-run:    inject_node_classes() → Inject classes
4. Execution:  execute() → Run workflow
5. Cleanup:    clear_injected_classes() → Memory cleanup
```

### Step-by-Step Code

```python
from programgarden import WorkflowExecutor
from programgarden_core.nodes.base import BaseNode, NodeCategory, OutputPort

# 1. Define dynamic node class
class DynamicRSINode(BaseNode):
    type: str = "Dynamic_RSI"
    category: NodeCategory = NodeCategory.CONDITION
    period: int = 14

    _outputs = [
        OutputPort(name="rsi", type="number"),
        OutputPort(name="signal", type="string"),
    ]

    async def execute(self, context):
        # Actual RSI calculation logic
        return {"rsi": 35.5, "signal": "oversold"}

# 2. Create Executor and register schema
executor = WorkflowExecutor()
executor.register_dynamic_schemas([{
    "node_type": "Dynamic_RSI",
    "category": "condition",
    "description": "Dynamic RSI indicator node",
    "inputs": [{"name": "data", "type": "array", "required": True}],
    "outputs": [
        {"name": "rsi", "type": "number"},
        {"name": "signal", "type": "string"},
    ],
    "config_schema": {
        "period": {"type": "integer", "default": 14, "min": 1, "max": 100}
    },
}])

# 3. Check required types
required = executor.get_required_dynamic_types(workflow)
# → ["Dynamic_RSI"]

# 4. Inject classes
executor.inject_node_classes({"Dynamic_RSI": DynamicRSINode})

# 5. Verify readiness
assert executor.is_dynamic_node_ready("Dynamic_RSI")

# 6. Execute workflow
job = await executor.execute(workflow)

# 7. Memory cleanup (optional)
executor.clear_injected_classes()
```

## DynamicNodeSchema Fields

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `node_type` | string | O | Unique node type name (`Dynamic_` prefix required) |
| `category` | string | - | Node category (default: `"data"`) |
| `description` | string | - | Node description (for UI display) |
| `inputs` | array | - | Input port definitions `[{name, type, required, description}]` |
| `outputs` | array | - | Output port definitions `[{name, type, description}]` |
| `config_schema` | object | - | Configuration field schema `{field_name: {type, default, ...}}` |
| `version` | string | - | Node version (default: `"1.0.0"`) |
| `author` | string | - | Author |

### Schema Registration Example

```python
executor.register_dynamic_schemas([
    {
        "node_type": "Dynamic_RSI",
        "category": "condition",
        "description": "Condition evaluation based on RSI indicator",
        "inputs": [
            {"name": "data", "type": "array", "required": True, "description": "OHLCV data"}
        ],
        "outputs": [
            {"name": "rsi", "type": "number", "description": "RSI value"},
            {"name": "signal", "type": "string", "description": "Trading signal"}
        ],
        "config_schema": {
            "period": {"type": "integer", "default": 14, "min": 1, "max": 100},
            "overbought": {"type": "number", "default": 70},
            "oversold": {"type": "number", "default": 30}
        }
    }
])
```

## Node Class Implementation Rules

### Required

1. **Must inherit `BaseNode`**
2. **Must implement `execute()` method** (async)
3. **`type` field**: Must include `Dynamic_` prefix
4. **Output ports**: Schema `outputs` must match class `_outputs`

### Class Validation Items

Automatically validated when `inject_node_classes()` is called:

| Validation | On Failure |
|------------|------------|
| Schema registered | `ValueError: Schema not registered for type` |
| BaseNode inheritance | `TypeError: Must inherit from BaseNode` |
| execute() method exists | `TypeError: Missing execute() method` |
| Output ports match | `ValueError: Output port defined in schema missing from class` |

### Base Class Template

```python
from typing import Dict, Any, List
from programgarden_core.nodes.base import (
    BaseNode, NodeCategory, InputPort, OutputPort
)

class Dynamic_MyNode(BaseNode):
    """Dynamic node class template"""

    type: str = "Dynamic_MyNode"
    category: NodeCategory = NodeCategory.CONDITION  # or DATA, MARKET, etc.

    # Configuration fields (matching config_schema)
    period: int = 14
    threshold: float = 50.0

    # Input port definitions
    _inputs: List[InputPort] = [
        InputPort(name="data", type="array", required=True, description="Input data"),
    ]

    # Output port definitions (must match schema outputs)
    _outputs: List[OutputPort] = [
        OutputPort(name="result", type="object", description="Calculation result"),
        OutputPort(name="signal", type="string", description="Trading signal"),
    ]

    async def execute(self, context) -> Dict[str, Any]:
        """
        Node execution logic

        Args:
            context: ExecutionContext (logging, state management)

        Returns:
            Dict corresponding to output ports
        """
        # Log output
        context.log("info", f"MyNode execution: period={self.period}", self.id)

        # Business logic implementation
        result = {"value": 42.0, "period": self.period}
        signal = "buy" if result["value"] > self.threshold else "hold"

        return {
            "result": result,
            "signal": signal,
        }
```

## Security Constraints

### credential_id Cannot Be Used

Dynamic nodes cannot use `credential_id` (credential access is blocked for security):

```json
{
  "nodes": [
    {"id": "custom", "type": "Dynamic_RSI", "credential_id": "my-cred"}
  ]
}
```

A `credential_id cannot be used` error is raised during workflow validation.

### When API Calls Are Needed

You must implement HTTP calls directly within the dynamic node, or connect existing nodes (such as HTTPRequestNode) in the workflow to pass data.

## WorkflowExecutor API

| Method | Description |
|--------|-------------|
| `register_dynamic_schemas(schemas)` | Register schemas (for UI display) |
| `get_required_dynamic_types(workflow)` | List of dynamic node types required by the workflow |
| `inject_node_classes(classes)` | Inject node classes |
| `is_dynamic_node_ready(type)` | Check if ready for execution |
| `list_dynamic_node_types()` | List of registered dynamic node types |
| `clear_injected_classes()` | Clear injected classes (memory cleanup) |

### DynamicNodeRegistry API (Internal)

| Method | Description |
|--------|-------------|
| `register_schema(schema)` | Register a single schema |
| `register_schemas(schemas)` | Register multiple schemas |
| `get_schema(node_type)` | Query schema |
| `inject_node_class(type, cls)` | Inject a single class (with validation) |
| `get_node_class(node_type)` | Query injected class |
| `is_class_injected(node_type)` | Check if class is injected |
| `is_schema_registered(node_type)` | Check if schema is registered |
| `unregister(node_type)` | Remove schema + class |
| `clear_all()` | Clear everything |

## Usage in Workflows

```json
{
  "nodes": [
    {"id": "start", "type": "StartNode"},
    {"id": "custom_rsi", "type": "Dynamic_RSI", "period": 14}
  ],
  "edges": [
    {"from": "start", "to": "custom_rsi"}
  ]
}
```

Dynamic nodes can use `{{ }}` expressions, auto-iterate, edge connections, etc. just like regular nodes.

## Error Handling

| Situation | Error |
|-----------|-------|
| Validation without schema registered | `"Schema not registered"` |
| Execution without class injected | `"Dynamic node class not injected. Call inject_node_classes() first."` |
| Missing Dynamic_ prefix | `ValueError: Dynamic nodes require 'Dynamic_' prefix` |
| Using credential_id | `"credential_id cannot be used"` |
| Unknown node type | `"Unknown node type"` |

## Singleton Pattern

`DynamicNodeRegistry` is managed as a **global singleton**. Since `WorkflowExecutor` internally accesses the singleton, multiple Executor instances share the same registry.

```python
# Two executors share the same registry
executor1 = WorkflowExecutor()
executor2 = WorkflowExecutor()

executor1.register_dynamic_schemas([...])
# The schema is also available in executor2
```
