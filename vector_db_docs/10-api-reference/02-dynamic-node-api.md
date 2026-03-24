---
category: api_reference
tags: [api, dynamic_node, injection, Dynamic_, register, inject, BaseNode, execute, runtime, dynamic_node, code_generation]
priority: high
---

# Dynamic Node Injection API

## Overview

Dynamic Node Injection is an API that allows external users to create custom nodes at runtime for use in workflows. You can build your own nodes without contributing to the community package.

## Basic Usage Flow

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
        data = context.get_input("data")
        rsi_value = calculate_rsi(data, self.period)
        signal = "oversold" if rsi_value < 30 else "overbought" if rsi_value > 70 else "neutral"
        return {"rsi": rsi_value, "signal": signal}

# 2. Create Executor and register schema
executor = WorkflowExecutor()
executor.register_dynamic_schemas([{
    "node_type": "Dynamic_RSI",
    "category": "condition",
    "description": "Custom RSI calculation",
    "outputs": [
        {"name": "rsi", "type": "number"},
        {"name": "signal", "type": "string"},
    ],
}])

# 3. Check required dynamic types in the workflow
workflow = {
    "nodes": [
        {"id": "start", "type": "StartNode"},
        {"id": "my_rsi", "type": "Dynamic_RSI", "period": 14}
    ],
    "edges": [{"from": "start", "to": "my_rsi"}]
}
required = executor.get_required_dynamic_types(workflow)
# ["Dynamic_RSI"]

# 4. Inject classes
executor.inject_node_classes({"Dynamic_RSI": DynamicRSINode})

# 5. Verify readiness
assert executor.is_dynamic_node_ready("Dynamic_RSI")

# 6. Execute workflow
job = await executor.execute(workflow)

# 7. Clean up memory (optional)
executor.clear_injected_classes()
```

## API Methods

### register_dynamic_schemas(schemas)

Registers schemas for dynamic nodes. Used for UI display and workflow validation. At this step, only schemas are stored without classes.

```python
executor.register_dynamic_schemas([
    {
        "node_type": "Dynamic_MyRSI",
        "category": "condition",
        "description": "My custom RSI indicator",
        "fields": [
            {"name": "period", "type": "int", "default": 14}
        ],
        "outputs": [
            {"name": "rsi", "type": "number"},
            {"name": "signal", "type": "string"}
        ]
    }
])
```

**Schema fields:**

| Field | Type | Description |
|-------|------|-------------|
| `node_type` | `str` | Node type name (must have `Dynamic_` prefix) |
| `category` | `str` | Category (condition, data, display, etc.) |
| `description` | `str` | Node description |
| `fields` | `List[Dict]` | Input field definitions (optional) |
| `outputs` | `List[Dict]` | Output port definitions |

**Note**: A `ValueError` is raised if `node_type` does not start with `Dynamic_`.

### get_required_dynamic_types(workflow) → List[str]

Returns the list of dynamic node types used in a workflow. Used to load only the required classes.

```python
required = executor.get_required_dynamic_types(workflow)
# ["Dynamic_MyRSI", "Dynamic_MyMACD"]

for node_type in required:
    code = await cloud.download(f"nodes/{node_type}.py")
    cls = dynamic_import(code)
    executor.inject_node_classes({node_type: cls})
```

### inject_node_classes(node_classes)

Injects dynamic node classes. Four validations are performed during injection:

1. Whether the schema is registered
2. Whether it inherits from `BaseNode`
3. Whether the `execute()` method is implemented
4. Whether the output ports match between the schema and the class

```python
executor.inject_node_classes({
    "Dynamic_MyRSI": MyRSINode,
    "Dynamic_MyMACD": MyMACDNode,
})
```

**Error conditions:**

| Condition | Error |
|-----------|-------|
| Schema not registered | `ValueError` |
| Does not inherit BaseNode | `TypeError` |
| execute() not implemented | `TypeError` |
| Output port mismatch | `ValueError` |

### is_dynamic_node_ready(node_type) → bool

Checks whether a dynamic node is ready for execution. Returns `True` only when both schema registration and class injection are complete.

```python
if executor.is_dynamic_node_ready("Dynamic_MyRSI"):
    job = await executor.execute(workflow)
```

### clear_injected_classes()

Cleans up injected classes. Schemas are retained while only classes are removed.

```python
job = await executor.execute(workflow)
executor.clear_injected_classes()  # Memory cleanup
```

## Dynamic Node Class Writing Rules

### Required Elements

```python
from programgarden_core.nodes.base import BaseNode, NodeCategory, OutputPort, InputPort

class DynamicMyNode(BaseNode):
    # 1. type field: must have Dynamic_ prefix
    type: str = "Dynamic_MyNode"

    # 2. category field
    category: NodeCategory = NodeCategory.CONDITION

    # 3. Custom configuration fields (optional)
    period: int = 14
    threshold: float = 0.5

    # 4. Input ports (optional)
    _inputs = [InputPort(name="data", type="any")]

    # 5. Output ports: must match the schema
    _outputs = [
        OutputPort(name="result", type="any"),
        OutputPort(name="signal", type="string"),
    ]

    # 6. execute() method: must be implemented
    async def execute(self, context):
        data = context.get_input("data")
        # ... custom logic ...
        return {"result": processed_data, "signal": "buy"}
```

### Constraints

| Constraint | Description |
|------------|-------------|
| `Dynamic_` prefix required | Must be used to distinguish from built-in nodes |
| `credential_id` not available | Credential access is blocked for security reasons |
| Must inherit `BaseNode` | Cannot use other base classes |
| Must implement `execute()` | Must be an async method |
| Output port match | Schema `outputs` must match the class `_outputs` |

### Using Dynamic Nodes in Workflows

```json
{
    "nodes": [
        {"id": "start", "type": "StartNode"},
        {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "cred-1"},
        {"id": "historical", "type": "OverseasStockHistoricalDataNode",
         "symbol": "AAPL", "start_date": "{{ date.ago(30, format='yyyymmdd') }}",
         "end_date": "{{ date.today(format='yyyymmdd') }}"},
        {"id": "my_rsi", "type": "Dynamic_RSI",
         "period": 14, "data": "{{ nodes.historical.value }}"},
        {"id": "table", "type": "TableDisplayNode",
         "title": "RSI Results", "data": "{{ nodes.my_rsi.result }}"}
    ],
    "edges": [
        {"from": "start", "to": "broker"},
        {"from": "broker", "to": "historical"},
        {"from": "historical", "to": "my_rsi"},
        {"from": "my_rsi", "to": "table"}
    ]
}
```

Dynamic nodes support `{{ }}` data binding, auto-iterate, and edge connections just like regular nodes.
