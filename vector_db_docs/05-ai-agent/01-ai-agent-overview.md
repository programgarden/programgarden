---
category: ai_agent
tags: [ai, llm, agent, overview, LLMModelNode, AIAgentNode, ai_model, tool_edge, credential]
priority: high
---

# AI Agent Workflow Overview

## AI Agent System Architecture

ProgramGarden's AI Agent system consists of **2 nodes**:

| Node | Role | Category |
|------|------|----------|
| `LLMModelNode` | Provides LLM API connection (BrokerNode pattern) | ai |
| `AIAgentNode` | General-purpose AI agent (Tool utilization, decision-making) | ai |

## Core Architecture

```
[LLMModelNode] ──ai_model──> [AIAgentNode] <──tool── [Existing Nodes]
   (LLM connection)              (Agent)               (Used as tools)
```

### 3 Edge Types

| Edge Type | Purpose | Example |
|-----------|---------|---------|
| `main` | DAG execution order (default) | StartNode → AIAgentNode |
| `ai_model` | LLM connection propagation | LLMModelNode → AIAgentNode |
| `tool` | Register existing nodes as Tools | MarketDataNode → AIAgentNode |

```json
{
  "edges": [
    {"from": "start", "to": "agent"},
    {"from": "llm", "to": "agent", "type": "ai_model"},
    {"from": "market", "to": "agent", "type": "tool"},
    {"from": "account", "to": "agent", "type": "tool"}
  ]
}
```

## LLMModelNode

A node that provides LLM API connections. Following the same pattern as BrokerNode, it connects to an API via credentials and propagates to AIAgentNode through `ai_model` edges. **Multiple AIAgentNodes can share the same LLMModelNode**.

### Configuration Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `credential_id` | credential | (required) | LLM API authentication information |
| `model` | string | `"gpt-4o"` | LLM model ID |
| `temperature` | number | `0.7` | Generation temperature (0.0~2.0) |
| `max_tokens` | integer | `1000` | Maximum output token count (100~128000) |
| `seed` | integer | null | Seed for reproducibility (OpenAI seed parameter) |
| `streaming` | boolean | `false` | Whether to use streaming responses |

### Supported Credential Types

| credential_type | Provider | Model Examples |
|-----------------|----------|----------------|
| `llm_openai` | OpenAI | gpt-4o, gpt-4o-mini |
| `llm_anthropic` | Anthropic | claude-sonnet-4-5-20250929, claude-haiku-4-5-20251001 |
| `llm_google` | Google | gemini-pro |
| `llm_azure_openai` | Azure OpenAI | azure/gpt-4o-deploy |
| `llm_ollama` | Ollama (local) | ollama/llama3.1 |

### Output Ports

| Port | Type | Description |
|------|------|-------------|
| `connection` | ai_model | LLM connection information (connects to AIAgentNode's ai_model port) |

### Workflow JSON

```json
{
  "id": "llm",
  "type": "LLMModelNode",
  "credential_id": "llm-cred",
  "model": "gpt-4o",
  "temperature": 0.3,
  "max_tokens": 2000,
  "streaming": true
}
```

Credential definition:

```json
{
  "credential_id": "llm-cred",
  "type": "llm_openai",
  "data": [
    {"key": "api_key", "value": "", "type": "password", "label": "OpenAI API Key"}
  ]
}
```

## AIAgentNode

A general-purpose agent that calls LLMs to perform data analysis and decision-making, and invokes existing nodes connected via `tool` edges as tools.

### Key Characteristics

- **Stateless**: Operates independently on each execution (no conversation memory, queries current data directly via Tools)
- **ReAct/Function Calling Loop**: LLM call → Tool needed? → Tool execution → LLM re-call
- **Built-in Output Parser**: 3 output formats: text/json/structured

### Input Ports

| Port | Type | Required | Description |
|------|------|:--------:|-------------|
| `trigger` | signal | - | Execution trigger (main edge) |
| `ai_model` | ai_model | O | LLM connection (from LLMModelNode via ai_model edge) |
| `tools` | tool | - | AI tools (connect existing nodes via tool edges, multiple allowed) |

### Output Ports

| Port | Type | Description |
|------|------|-------------|
| `response` | any | AI response (depending on output_format: text→string, json/structured→object) |

### Configuration Fields (PARAMETERS)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `preset` | enum | `"custom"` | Preset (custom, risk_manager, news_analyst, technical_analyst, strategist) |
| `system_prompt` | string | `""` | Role/persona definition (system prompt) |
| `user_prompt` | string | (required) | User instructions (supports `{{ }}` expressions) |
| `output_format` | enum | `"text"` | Output format (text, json, structured) |
| `output_schema` | json | null | Output schema for structured mode (shown only when output_format="structured") |

### Configuration Fields (SETTINGS)

| Field | Type | Default | Range | Description |
|-------|------|---------|-------|-------------|
| `max_tool_calls` | integer | `10` | 1~50 | Maximum Tool calls per execution |
| `timeout_seconds` | integer | `60` | 10~300 | LLM call timeout (seconds) |
| `cooldown_sec` | integer | `60` | 1~3600 | Minimum execution interval (seconds) |
| `tool_error_strategy` | enum | `"retry_with_context"` | - | Strategy for Tool call failures |

### tool_error_strategy Options

| Strategy | Behavior |
|----------|----------|
| `retry_with_context` | Pass error + hint to LLM for retry |
| `skip` | Replace Tool result with error message and continue |
| `abort` | Immediately fail node execution on Tool failure |

## Execution Flow

```
1. Inject LLM connection from ai_model edge
2. Collect Tool list from tool edges (as_tool_schema → OpenAI function calling format)
3. Apply preset (if present)
4. Assemble prompts (system + user + output instructions)
5. LLM call loop:
   ├─ Tool call requested? → Execute Tool → Compact result → Re-call LLM
   ├─ max_tool_calls reached? → Send forced termination message → Final LLM call
   └─ Final response? → Output Parser
6. Output to response port
```

## Output Formats (Output Parser)

| output_format | Description | Response Type |
|---------------|-------------|---------------|
| `text` | Return raw text as-is | string |
| `json` | JSON parsing (auto-extracts ```json blocks) | object |
| `structured` | Pydantic validation based on output_schema | object |

### structured Mode output_schema Example

```json
{
  "output_format": "structured",
  "output_schema": {
    "signal": {"type": "string", "enum": ["buy", "hold", "sell"], "description": "Trading signal"},
    "confidence": {"type": "number", "description": "Confidence level (0~1)"},
    "reasoning": {"type": "string", "description": "Basis for judgment"}
  }
}
```

On validation failure, the original dict is returned as-is (fallback, not an error).

## Safety Mechanisms

### Direct Connection to Real-time Nodes Blocked

```
[RealMarketDataNode] → [AIAgentNode]                    (X Error)
[RealMarketDataNode] → [ThrottleNode] → [AIAgentNode]   (O)
```

### Rate Limit

- **cooldown_sec**: Default 60-second interval (user setting takes priority)
- **Concurrent execution**: 1 (max_concurrent=1)
- **When exceeded**: skip (ignored)

## Tool Result Compact (Adaptive Downsampling)

Automatically compresses large Tool execution results to fit the LLM context:

| Data Type | Detection Criteria | Compression Method |
|-----------|-------------------|-------------------|
| Time series (OHLCV) | 3+ of open/high/low/close present | M4 (first/min/max/last per bucket) |
| Ranked (positions) | symbol + pnl/quantity etc. | Top-N (top 5 + bottom 5) |
| Simple arrays | Other dict/value arrays | Uniform sampling |

- Activates when array has 10+ items
- 4000-character guardrail (further reduction if exceeded)
- Original data is separately delivered via response output port + AIToolCallEvent (no data loss)

## ExecutionListener Events

Events emitted during AI Agent execution:

| Event | Description |
|-------|-------------|
| `on_token_usage` | Token usage (total_tokens, cost_usd) |
| `on_ai_tool_call` | Tool call (tool_name, duration_ms) |
| `on_llm_stream` | Streaming chunk (is_final) |

## Basic Workflow Pattern

```json
{
  "nodes": [
    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker-cred"},
    {"id": "llm", "type": "LLMModelNode", "credential_id": "llm-cred", "model": "gpt-4o", "temperature": 0.3},
    {"id": "market", "type": "OverseasStockMarketDataNode", "symbol": "AAPL", "exchange": "NASDAQ"},
    {"id": "account", "type": "OverseasStockAccountNode"},
    {"id": "agent", "type": "AIAgentNode",
     "system_prompt": "You are an investment analyst.",
     "user_prompt": "Analyze the current positions and market prices, and make a trading decision.",
     "output_format": "json"}
  ],
  "edges": [
    {"from": "broker", "to": "market"},
    {"from": "broker", "to": "account"},
    {"from": "llm", "to": "agent", "type": "ai_model"},
    {"from": "market", "to": "agent", "type": "tool"},
    {"from": "account", "to": "agent", "type": "tool"}
  ]
}
```
