---
category: ai_agent
tags: [tool, edge, semi_auto, supervised, is_tool_enabled, as_tool_schema, function_calling, tool_call]
priority: high
---

# Tool Edges: Using Existing Nodes as AI Tools

## Overview

A `tool` edge is a special edge type that registers existing workflow nodes as **Tools** for the AIAgentNode, allowing the LLM to call them directly when needed. Through this, the AI Agent can autonomously perform market data queries, position checks, order execution, and more.

## Tool Edge Basic Structure

```json
{
  "edges": [
    {"from": "market_data", "to": "agent", "type": "tool"},
    {"from": "account", "to": "agent", "type": "tool"},
    {"from": "order", "to": "agent", "type": "tool"}
  ]
}
```

- `type: "tool"` edges are not included in the DAG execution order
- Multiple nodes can be connected as tools to a single AIAgentNode
- The LLM selectively calls only the Tools it determines are needed

## Tool Registration Process

### 1. is_tool_enabled Check

Verifies that a node connected via tool edge has `is_tool_enabled() == True`. If `False`, the node is not registered as a Tool and only a warning log is emitted.

**Tool-enabled Nodes** (is_tool_enabled=True, default):

| Category | Nodes |
|----------|-------|
| market | OverseasStockMarketDataNode, OverseasFuturesMarketDataNode, OverseasStockHistoricalDataNode, OverseasFuturesHistoricalDataNode, OverseasStockSymbolQueryNode, OverseasFuturesSymbolQueryNode |
| account | OverseasStockAccountNode, OverseasFuturesAccountNode, OverseasStockOpenOrdersNode, OverseasFuturesOpenOrdersNode |
| condition | ConditionNode |
| order | OverseasStockNewOrderNode, OverseasFuturesNewOrderNode, OverseasStockModifyOrderNode, OverseasFuturesModifyOrderNode, OverseasStockCancelOrderNode, OverseasFuturesCancelOrderNode |
| data | HTTPRequestNode, FieldMappingNode |
| risk | PortfolioNode |

**Tool-disabled Nodes** (is_tool_enabled=False):

| Node | Reason |
|------|--------|
| StartNode | Infrastructure node, meaningless as Tool |
| ThrottleNode | Infrastructure node |
| LLMModelNode | Connection provider node |
| AIAgentNode | The agent itself |
| Real-time nodes | Subscription-based, unsuitable as Tool |
| Schedule nodes | Trigger nodes |
| Display nodes | UI-only |

### 2. as_tool_schema Conversion

Tool-enabled nodes generate an OpenAI function calling format schema via `as_tool_schema()`:

```python
# Inside node class
@classmethod
def as_tool_schema(cls) -> Dict[str, Any]:
    # Node name → snake_case conversion
    # OverseasStockMarketDataNode → overseas_stock_market_data_node
    # Parameters: extracted from FieldSchema (excluding credential_id etc.)
```

Converted Tool definition (OpenAI function calling format):

```json
{
  "type": "function",
  "function": {
    "name": "overseas_stock_market_data_node",
    "description": "Overseas stock current price query",
    "parameters": {
      "type": "object",
      "properties": {
        "symbol": {"type": "string", "description": "Stock symbol (e.g., AAPL)"},
        "exchange": {"type": "string", "description": "Exchange (e.g., NASDAQ)"}
      }
    }
  }
}
```

### 3. Tool Naming Convention

Node types are converted to snake_case:

| Node Type | Tool Name |
|-----------|-----------|
| `OverseasStockMarketDataNode` | `overseas_stock_market_data_node` |
| `OverseasStockAccountNode` | `overseas_stock_account_node` |
| `ConditionNode` | `condition_node` |
| `HTTPRequestNode` | `http_request_node` |

### 4. Parameter Filtering

- **Excluded**: `credential_id`, `connection`, `_source_node_id` (security/internal)
- **Included**: User-configurable fields defined in the node's FieldSchema
- **Fixed config**: Values already set on the node are preserved; values passed by the LLM are merged (override)

## Tool Call Execution Process

### LLM → Tool Call → LLM Re-call Loop

```
LLM call (messages + tools)
    ↓
finish_reason == "tool_calls"?
    ├─ Yes → Execute Tool → Compact result → Add to messages → Re-call LLM
    └─ No → Final response → Output Parser
```

### Tool Execution Details

1. LLM requests Tool call (function name + arguments)
2. `AIAgentToolExecutor.call_tool()` executes
3. LLM arguments merged with node fixed config
4. **Broker connection auto-injected** (product_scope matching)
5. Node executed via GenericNodeExecutor or dedicated Executor
6. Result compressed via `_compact_tool_result()` for LLM consumption
7. Added to messages as a tool role message

### Broker Connection Auto-Injection

When a tool-edge-connected node needs to make API calls, the BrokerNode connection with matching `product_scope` is automatically injected:

```
[BrokerNode] → connection output
                  ↓ (auto-injected)
[MarketDataNode] ←tool── [AIAgentNode]
```

When the LLM calls MarketDataNode as a Tool, the connection from the already-executed BrokerNode in the workflow is automatically injected into the config.

### LLM Arguments Preprocessing

Automatically handles cases where the LLM sends object-type parameters as JSON strings:

```python
# LLM sent args: {"symbol": "AAPL"}         → Used as-is
# LLM sent args: {"symbol": "{\"AAPL\"}"}   → JSON parsed before use
```

## Tool Error Handling

Handled with 3 strategies based on the `tool_error_strategy` setting:

### retry_with_context (Default)

Passes the error message + hint to the LLM for retry with a different approach:

```json
// Delivered as tool role message
{
  "error": "API connection failed",
  "hint": "This tool call failed. Try a different approach or answer with available information."
}
```

### skip

Replaces the Tool result with an error message and tells the LLM to continue:

```json
// Delivered as tool role message
{
  "error": "API timeout",
  "status": "skipped"
}
```

### abort

Immediately fails the node execution on Tool failure. The result includes an `error` field.

## max_tool_calls Limit

To prevent infinite loops, `max_tool_calls` (default 10) limits the number of Tool calls:

```
Tool call count >= max_tool_calls?
    ├─ Yes → Send "tool call limit reached" message → Final LLM call (tools parameter removed)
    └─ No → Continue normal Tool calls
```

## Practical Patterns

### Market Data Query + Analysis

```json
{
  "nodes": [
    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker-cred"},
    {"id": "llm", "type": "LLMModelNode", "credential_id": "llm-cred", "model": "gpt-4o"},
    {"id": "market", "type": "OverseasStockMarketDataNode", "symbol": "AAPL", "exchange": "NASDAQ"},
    {"id": "agent", "type": "AIAgentNode",
     "user_prompt": "Query the current AAPL market data and analyze it.",
     "output_format": "json"}
  ],
  "edges": [
    {"from": "broker", "to": "market"},
    {"from": "llm", "to": "agent", "type": "ai_model"},
    {"from": "market", "to": "agent", "type": "tool"}
  ]
}
```

### Position Check + Risk Management

```json
{
  "nodes": [
    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker-cred"},
    {"id": "llm", "type": "LLMModelNode", "credential_id": "llm-cred", "model": "gpt-4o", "temperature": 0.2},
    {"id": "account", "type": "OverseasStockAccountNode"},
    {"id": "market", "type": "OverseasStockMarketDataNode"},
    {"id": "agent", "type": "AIAgentNode",
     "preset": "risk_manager",
     "user_prompt": "Check all positions and evaluate risk."}
  ],
  "edges": [
    {"from": "broker", "to": "account"},
    {"from": "broker", "to": "market"},
    {"from": "llm", "to": "agent", "type": "ai_model"},
    {"from": "account", "to": "agent", "type": "tool"},
    {"from": "market", "to": "agent", "type": "tool"}
  ]
}
```

### Semi-Auto Trading (AI Judgment + Automatic Orders)

Semi-automatic trading where AI analyzes and executes orders through Tool nodes:

```json
{
  "nodes": [
    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker-cred"},
    {"id": "llm", "type": "LLMModelNode", "credential_id": "llm-cred", "model": "gpt-4o", "temperature": 0.1},
    {"id": "account", "type": "OverseasStockAccountNode"},
    {"id": "market", "type": "OverseasStockMarketDataNode"},
    {"id": "history", "type": "OverseasStockHistoricalDataNode",
     "start_date": "{{ date.ago(30, format='yyyymmdd') }}",
     "end_date": "{{ date.today(format='yyyymmdd') }}"},
    {"id": "order", "type": "OverseasStockNewOrderNode", "side": "buy", "order_type": "limit"},
    {"id": "agent", "type": "AIAgentNode",
     "preset": "strategist",
     "user_prompt": "Analyze positions, market data, and historical data, then execute an order if a trade is needed.",
     "max_tool_calls": 15}
  ],
  "edges": [
    {"from": "broker", "to": "account"},
    {"from": "broker", "to": "market"},
    {"from": "broker", "to": "history"},
    {"from": "broker", "to": "order"},
    {"from": "llm", "to": "agent", "type": "ai_model"},
    {"from": "account", "to": "agent", "type": "tool"},
    {"from": "market", "to": "agent", "type": "tool"},
    {"from": "history", "to": "agent", "type": "tool"},
    {"from": "order", "to": "agent", "type": "tool"}
  ]
}
```

**Caution**: Connecting an order node as a Tool allows the LLM to directly execute orders. Set `temperature` low and use `tool_error_strategy: "abort"` is recommended.

### Real-time Monitoring + AI Analysis

Real-time data throttled by ThrottleNode before AI analysis:

```json
{
  "nodes": [
    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker-cred"},
    {"id": "llm", "type": "LLMModelNode", "credential_id": "llm-cred", "model": "gpt-4o-mini"},
    {"id": "real_account", "type": "OverseasStockRealAccountNode"},
    {"id": "throttle", "type": "ThrottleNode", "mode": "debounce", "interval_ms": 30000},
    {"id": "market", "type": "OverseasStockMarketDataNode"},
    {"id": "agent", "type": "AIAgentNode",
     "preset": "risk_manager",
     "user_prompt": "Analyze current position changes and evaluate risk.",
     "cooldown_sec": 120}
  ],
  "edges": [
    {"from": "broker", "to": "real_account"},
    {"from": "broker", "to": "market"},
    {"from": "real_account", "to": "throttle"},
    {"from": "throttle", "to": "agent"},
    {"from": "llm", "to": "agent", "type": "ai_model"},
    {"from": "market", "to": "agent", "type": "tool"}
  ]
}
```

**Safety Mechanism**: ThrottleNode (30-second debounce) + cooldown_sec (120 seconds) = minimum 2-minute execution interval

## Tool Edge vs main Edge Comparison

| Characteristic | main Edge | tool Edge |
|----------------|-----------|-----------|
| DAG order | Included | Not included |
| Execution timing | Automatic (in order) | Called when LLM determines needed |
| Data passing | `{{ nodes.id.port }}` | LLM passes via arguments |
| Repeated calls | Once | LLM can call multiple times |
| Conditional execution | Always executed | Called only when LLM deems necessary |

## Important Notes

1. **Broker node required**: Tool-connected nodes that need API calls require a corresponding BrokerNode in the workflow
2. **credential_id not exposed**: Credential-related fields are excluded from Tool parameters (security)
3. **Fixed config priority**: Values already set on the node (symbol, exchange, etc.) are preserved; LLM-provided values are merged
4. **Caution with order node Tools**: The LLM directly executes orders, so set temperature low and ensure thorough validation
5. **Single concurrent execution**: AIAgentNode rate limiting prevents multiple simultaneous executions
