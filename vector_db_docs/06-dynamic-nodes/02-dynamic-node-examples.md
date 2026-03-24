---
category: dynamic_node
tags: [dynamic, example, code, python, AI_chatbot, code_generation, workflow]
priority: high
---

# Dynamic Node Code Examples

## AI Chatbot Scenario

The complete flow of an AI chatbot creating dynamic nodes tailored to user requests and injecting them into workflows.

### Scenario: "Create an RSI + Bollinger Bands composite condition node"

#### Step 1: AI Generates Code

```python
from typing import Dict, Any, List
from programgarden_core.nodes.base import BaseNode, NodeCategory, InputPort, OutputPort

class Dynamic_RSI_BB_Combo(BaseNode):
    """RSI + Bollinger Bands composite condition node"""

    type: str = "Dynamic_RSI_BB_Combo"
    category: NodeCategory = NodeCategory.CONDITION

    # User configuration fields
    rsi_period: int = 14
    bb_period: int = 20
    bb_std: float = 2.0
    rsi_oversold: float = 30.0

    _inputs: List[InputPort] = [
        InputPort(name="data", type="array", required=True, description="OHLCV time series"),
    ]

    _outputs: List[OutputPort] = [
        OutputPort(name="signal", type="string"),
        OutputPort(name="rsi", type="number"),
        OutputPort(name="bb_position", type="string"),
        OutputPort(name="details", type="object"),
    ]

    async def execute(self, context) -> Dict[str, Any]:
        import numpy as np

        data = context.get_input("data") or []
        if not data or len(data) < max(self.rsi_period, self.bb_period) + 1:
            return {
                "signal": "insufficient_data",
                "rsi": 0.0,
                "bb_position": "unknown",
                "details": {"error": "Insufficient data"},
            }

        closes = [float(d.get("close", 0)) for d in data]

        # RSI calculation
        deltas = np.diff(closes[-self.rsi_period - 1:])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gains) if len(gains) > 0 else 0
        avg_loss = np.mean(losses) if len(losses) > 0 else 1
        rs = avg_gain / avg_loss if avg_loss != 0 else 100
        rsi = 100 - (100 / (1 + rs))

        # Bollinger Bands calculation
        bb_closes = closes[-self.bb_period:]
        sma = np.mean(bb_closes)
        std = np.std(bb_closes)
        upper = sma + self.bb_std * std
        lower = sma - self.bb_std * std
        current = closes[-1]

        # Position determination
        if current <= lower:
            bb_position = "below_lower"
        elif current >= upper:
            bb_position = "above_upper"
        else:
            bb_position = "inside"

        # Composite signal: RSI oversold + below lower band = buy
        if rsi < self.rsi_oversold and bb_position == "below_lower":
            signal = "strong_buy"
        elif rsi < self.rsi_oversold:
            signal = "buy"
        elif rsi > (100 - self.rsi_oversold) and bb_position == "above_upper":
            signal = "strong_sell"
        else:
            signal = "hold"

        return {
            "signal": signal,
            "rsi": round(float(rsi), 2),
            "bb_position": bb_position,
            "details": {
                "rsi": round(float(rsi), 2),
                "bb_upper": round(float(upper), 2),
                "bb_lower": round(float(lower), 2),
                "bb_sma": round(float(sma), 2),
                "current_price": current,
            },
        }
```

#### Step 2: Schema Registration + Class Injection

```python
from programgarden import WorkflowExecutor

executor = WorkflowExecutor()

# Register schema
executor.register_dynamic_schemas([{
    "node_type": "Dynamic_RSI_BB_Combo",
    "category": "condition",
    "description": "RSI + Bollinger Bands composite condition. Buy signal when RSI oversold + below lower band",
    "inputs": [{"name": "data", "type": "array", "required": True}],
    "outputs": [
        {"name": "signal", "type": "string"},
        {"name": "rsi", "type": "number"},
        {"name": "bb_position", "type": "string"},
        {"name": "details", "type": "object"},
    ],
    "config_schema": {
        "rsi_period": {"type": "integer", "default": 14},
        "bb_period": {"type": "integer", "default": 20},
        "bb_std": {"type": "number", "default": 2.0},
        "rsi_oversold": {"type": "number", "default": 30.0},
    },
}])

# Inject class
executor.inject_node_classes({"Dynamic_RSI_BB_Combo": Dynamic_RSI_BB_Combo})
```

#### Step 3: Generate Workflow JSON

```json
{
  "nodes": [
    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker-cred"},
    {"id": "history", "type": "OverseasStockHistoricalDataNode",
     "symbol": "AAPL", "exchange": "NASDAQ",
     "start_date": "{{ date.ago(60, format='yyyymmdd') }}",
     "end_date": "{{ date.today(format='yyyymmdd') }}"},
    {"id": "combo", "type": "Dynamic_RSI_BB_Combo",
     "rsi_period": 14, "bb_period": 20, "rsi_oversold": 30},
    {"id": "order", "type": "OverseasStockNewOrderNode",
     "side": "buy", "order_type": "market", "order": "{{ item }}"}
  ],
  "edges": [
    {"from": "broker", "to": "history"},
    {"from": "history", "to": "combo"},
    {"from": "combo", "to": "order"}
  ]
}
```

## Example 1: Custom Scoring Node

A node that aggregates multiple indicators into a score:

```python
class Dynamic_MultiScore(BaseNode):
    """Multi-indicator composite scoring"""

    type: str = "Dynamic_MultiScore"
    category: NodeCategory = NodeCategory.CONDITION

    rsi_weight: float = 0.3
    macd_weight: float = 0.3
    volume_weight: float = 0.4

    _inputs: List[InputPort] = [
        InputPort(name="data", type="array", required=True),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="score", type="number"),
        OutputPort(name="grade", type="string"),
    ]

    async def execute(self, context) -> Dict[str, Any]:
        data = context.get_input("data") or []
        if not data:
            return {"score": 0.0, "grade": "N/A"}

        # Calculate each indicator score (0~100)
        rsi_score = self._calc_rsi_score(data)
        macd_score = self._calc_macd_score(data)
        volume_score = self._calc_volume_score(data)

        # Weighted sum
        total = (
            rsi_score * self.rsi_weight +
            macd_score * self.macd_weight +
            volume_score * self.volume_weight
        )

        # Grade determination
        if total >= 80: grade = "A"
        elif total >= 60: grade = "B"
        elif total >= 40: grade = "C"
        else: grade = "D"

        return {"score": round(total, 1), "grade": grade}
```

## Example 2: External API Integration Node

```python
import aiohttp

class Dynamic_FearGreedIndex(BaseNode):
    """Fear & Greed Index query node"""

    type: str = "Dynamic_FearGreedIndex"
    category: NodeCategory = NodeCategory.DATA

    _outputs: List[OutputPort] = [
        OutputPort(name="index", type="number"),
        OutputPort(name="classification", type="string"),
    ]

    async def execute(self, context) -> Dict[str, Any]:
        url = "https://api.alternative.me/fng/"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    data = await resp.json()
                    item = data["data"][0]
                    return {
                        "index": int(item["value"]),
                        "classification": item["value_classification"],
                    }
        except Exception as e:
            context.log("error", f"API call failed: {e}", self.id)
            return {"index": 0, "classification": "error"}
```

## Example 3: Data Transformation Node

```python
class Dynamic_PriceNormalizer(BaseNode):
    """Price data normalization node"""

    type: str = "Dynamic_PriceNormalizer"
    category: NodeCategory = NodeCategory.DATA

    method: str = "min_max"  # "min_max" | "z_score"

    _inputs: List[InputPort] = [
        InputPort(name="data", type="array", required=True),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="normalized", type="array"),
        OutputPort(name="stats", type="object"),
    ]

    async def execute(self, context) -> Dict[str, Any]:
        data = context.get_input("data") or []
        if not data:
            return {"normalized": [], "stats": {}}

        prices = [float(d.get("close", 0)) for d in data]

        if self.method == "min_max":
            min_p, max_p = min(prices), max(prices)
            diff = max_p - min_p if max_p != min_p else 1
            normalized = [(p - min_p) / diff for p in prices]
            stats = {"min": min_p, "max": max_p, "method": "min_max"}
        else:
            import statistics
            mean = statistics.mean(prices)
            stdev = statistics.stdev(prices) if len(prices) > 1 else 1
            normalized = [(p - mean) / stdev for p in prices]
            stats = {"mean": mean, "stdev": stdev, "method": "z_score"}

        # Add normalized values to original data
        result = []
        for i, d in enumerate(data):
            row = dict(d)
            row["normalized_close"] = round(normalized[i], 6)
            result.append(row)

        return {"normalized": result, "stats": stats}
```

## Example 4: Using as an AI Agent Tool

Dynamic nodes can also be connected as AI Agent Tools:

```json
{
  "nodes": [
    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker-cred"},
    {"id": "llm", "type": "LLMModelNode", "credential_id": "llm-cred", "model": "gpt-4o"},
    {"id": "history", "type": "OverseasStockHistoricalDataNode",
     "symbol": "AAPL", "exchange": "NASDAQ",
     "start_date": "{{ date.ago(30, format='yyyymmdd') }}",
     "end_date": "{{ date.today(format='yyyymmdd') }}"},
    {"id": "custom_score", "type": "Dynamic_MultiScore"},
    {"id": "agent", "type": "AIAgentNode",
     "user_prompt": "Analyze AAPL's historical data and scoring results.",
     "output_format": "json"}
  ],
  "edges": [
    {"from": "broker", "to": "history"},
    {"from": "llm", "to": "agent", "type": "ai_model"},
    {"from": "history", "to": "agent", "type": "tool"},
    {"from": "custom_score", "to": "agent", "type": "tool"}
  ]
}
```

For a dynamic node to be used as an AI Agent Tool, the class must override `is_tool_enabled()`:

```python
class Dynamic_MultiScore(BaseNode):
    # ... existing definitions ...

    @classmethod
    def is_tool_enabled(cls) -> bool:
        return True  # Enable as AI Agent Tool
```

## Full Integration Flow (Server-Side)

```python
from programgarden import WorkflowExecutor

# At server startup: Load all dynamic node schemas from DB
executor = WorkflowExecutor()
schemas = db.get_all_dynamic_node_schemas()  # DB query
executor.register_dynamic_schemas(schemas)

# On workflow execution request
async def execute_workflow(workflow_json: dict):
    # 1. Check required dynamic nodes
    required = executor.get_required_dynamic_types(workflow_json)

    # 2. Load and inject classes
    for node_type in required:
        code = await storage.download(f"nodes/{node_type}.py")
        module = dynamic_import(code)  # Using exec() or importlib
        node_class = getattr(module, node_type)
        executor.inject_node_classes({node_type: node_class})

    # 3. Validate
    validation = executor.validate(workflow_json)
    if not validation.is_valid:
        return {"error": validation.errors}

    # 4. Execute
    job = await executor.execute(workflow_json)

    # 5. Wait for completion
    import asyncio
    result = await asyncio.wait_for(job._task, timeout=300)

    # 6. Memory cleanup
    executor.clear_injected_classes()

    return result
```

## Important Notes

1. **`Dynamic_` prefix required**: Missing it raises a ValueError during schema registration
2. **credential_id cannot be used**: Direct API authentication in dynamic nodes is blocked
3. **Output ports must match**: Schema outputs and class _outputs must correspond
4. **Memory management**: Calling `clear_injected_classes()` after execution is recommended
5. **External libraries like numpy**: Must be installed in the server environment
6. **Security**: Since dynamic code is executed, only inject code from trusted sources
