---
category: workflow_example
tags: [example, ai, agent, LLMModelNode, AIAgentNode, risk_manager, strategist, tool, ai_model, preset, structured, output_schema, cooldown]
priority: high
---

# Example: AI Agent Workflow

## Overview

Examples of integrating LLM-based analysis and decision-making into workflows using LLMModelNode and AIAgentNode.

## Example 1: Basic AI Agent (Text Response)

Minimal LLMModelNode → AIAgentNode configuration. Generates only text responses without any Tools.

```json
{
  "nodes": [
    {"id": "start", "type": "StartNode"},
    {
      "id": "llm",
      "type": "LLMModelNode",
      "credential_id": "llm-cred",
      "model": "claude-haiku-4-5-20251001",
      "temperature": 0.7,
      "max_tokens": 500
    },
    {
      "id": "agent",
      "type": "AIAgentNode",
      "preset": "custom",
      "system_prompt": "You are a financial market analysis expert. Provide concise and essential analysis.",
      "user_prompt": "Summarize the overall trend of the US tech stock market in 3 lines.",
      "output_format": "text",
      "max_tool_calls": 0,
      "timeout_seconds": 30
    }
  ],
  "edges": [
    {"from": "start", "to": "llm"},
    {"from": "llm", "to": "agent", "type": "ai_model"}
  ],
  "credentials": [{"credential_id": "llm-cred"}]
}
```

### Key Patterns

#### 1. LLMModelNode (BrokerNode Pattern)

- Follows the same pattern as BrokerNode: authenticates LLM API via `credential_id`
- Connects to AIAgentNode via `ai_model` type edge
- **Credential separation**: LLM authentication and brokerage authentication are separate credentials

#### 2. Edge Type: ai_model

```json
{"from": "llm", "to": "agent", "type": "ai_model"}
```

- Connected via `ai_model` edge, not a regular `main` edge
- LLMModelNode's model settings (model, temperature, max_tokens) are propagated to AIAgentNode

#### 3. Output Formats

| format | Description |
|--------|------|
| `text` | Free-form text |
| `json` | JSON response |
| `structured` | Structured response based on `output_schema` (Pydantic validation) |

### LLMModelNode Settings

| Field | Description |
|------|------|
| `credential_id` | LLM API authentication (Anthropic, OpenAI, etc.) |
| `model` | Model ID |
| `temperature` | Response diversity (0.0-1.0) |
| `max_tokens` | Maximum token count |

### AIAgentNode Settings

| Field | Description |
|------|------|
| `preset` | Preset (`custom`, `risk_manager`, `technical_analyst`, `news_analyst`, `strategist`) |
| `system_prompt` | System prompt (when preset=custom) |
| `user_prompt` | User prompt |
| `output_format` | Output format (`text`, `json`, `structured`) |
| `max_tool_calls` | Maximum number of tool calls |
| `timeout_seconds` | Timeout (seconds) |
| `cooldown_sec` | Cooldown when connected to real-time nodes (default 60 seconds) |

## Example 2: AI Chief Strategist (Tool Usage + Structured Output)

Uses the `strategist` preset to perform comprehensive trading decisions by utilizing account/market/historical data as Tools.

```json
{
  "nodes": [
    {"id": "start", "type": "StartNode"},
    {
      "id": "broker",
      "type": "OverseasStockBrokerNode",
      "credential_id": "broker-cred"
    },
    {
      "id": "llm",
      "type": "LLMModelNode",
      "credential_id": "llm-cred",
      "model": "claude-haiku-4-5-20251001",
      "temperature": 0.5,
      "max_tokens": 2000
    },
    {
      "id": "account",
      "type": "OverseasStockAccountNode"
    },
    {
      "id": "watchlist",
      "type": "WatchlistNode",
      "symbols": [
        {"symbol": "AAPL", "exchange": "NASDAQ"},
        {"symbol": "MSFT", "exchange": "NASDAQ"},
        {"symbol": "NVDA", "exchange": "NASDAQ"},
        {"symbol": "TSLA", "exchange": "NASDAQ"}
      ]
    },
    {
      "id": "market",
      "type": "OverseasStockMarketDataNode",
      "symbols": [
        {"symbol": "AAPL", "exchange": "NASDAQ"},
        {"symbol": "MSFT", "exchange": "NASDAQ"},
        {"symbol": "NVDA", "exchange": "NASDAQ"},
        {"symbol": "TSLA", "exchange": "NASDAQ"}
      ]
    },
    {
      "id": "historical",
      "type": "OverseasStockHistoricalDataNode",
      "symbol": "{{ item }}",
      "interval": "1d",
      "start_date": "{{ date.ago(14, format='yyyymmdd') }}",
      "end_date": "{{ date.today(format='yyyymmdd') }}"
    },
    {
      "id": "open_orders",
      "type": "OverseasStockOpenOrdersNode"
    },
    {
      "id": "agent",
      "type": "AIAgentNode",
      "preset": "strategist",
      "user_prompt": "Comprehensively analyze the current positions, open orders, and market data, then determine the next action.\n\nWatchlist symbols: AAPL, MSFT, NVDA, TSLA\n\nConsider the following in your analysis:\n1. Current position returns and risk\n2. Open order status\n3. Technical position relative to current market prices\n4. Buy/sell/hold decision and rationale",
      "output_format": "structured",
      "output_schema": {
        "action": {"type": "string", "enum": ["buy", "sell", "hold"], "description": "Trading decision"},
        "symbol": {"type": "string", "description": "Target symbol"},
        "quantity": {"type": "number", "description": "Quantity"},
        "price": {"type": "number", "description": "Target price"},
        "confidence": {"type": "number", "description": "Confidence level (0-1)"},
        "reasoning": {"type": "string", "description": "Decision rationale"}
      },
      "max_tool_calls": 10,
      "timeout_seconds": 120,
      "cooldown_sec": 300
    },
    {
      "id": "result_table",
      "type": "TableDisplayNode",
      "title": "AI Strategy Decision Result",
      "data": "{{ nodes.agent.response }}"
    }
  ],
  "edges": [
    {"from": "start", "to": "broker"},
    {"from": "start", "to": "llm"},
    {"from": "broker", "to": "account"},
    {"from": "broker", "to": "market"},
    {"from": "broker", "to": "open_orders"},
    {"from": "watchlist", "to": "historical"},
    {"from": "llm", "to": "agent", "type": "ai_model"},
    {"from": "account", "to": "agent", "type": "tool"},
    {"from": "market", "to": "agent", "type": "tool"},
    {"from": "historical", "to": "agent", "type": "tool"},
    {"from": "open_orders", "to": "agent", "type": "tool"},
    {"from": "agent", "to": "result_table"}
  ],
  "credentials": [
    {"credential_id": "broker-cred"},
    {"credential_id": "llm-cred"}
  ]
}
```

### DAG Structure

```
start → broker → account ────→ agent (tool)
      │       → market ──────→ agent (tool)
      │       → open_orders ──→ agent (tool)
      │
      → llm ──────────────────→ agent (ai_model)

watchlist → historical ───────→ agent (tool)

agent → result_table
```

### Using 3 Edge Types

| Edge Type | Purpose | Example |
|-----------|------|------|
| `main` | DAG execution order | `start → broker`, `agent → result_table` |
| `ai_model` | LLM model connection | `llm → agent` |
| `tool` | AI Agent tool registration | `account → agent`, `market → agent` |

### Tool Edge Behavior

Nodes connected via `tool` type edges are registered as **tools** for the AI Agent:
- The Agent calls tools as needed during analysis
- Tool call results are reflected in the Agent's analysis
- `max_tool_calls: 10` → Up to 10 tool calls allowed

### output_schema (Structured Output)

```json
"output_schema": {
  "action": {"type": "string", "enum": ["buy", "sell", "hold"]},
  "symbol": {"type": "string"},
  "quantity": {"type": "number"},
  "confidence": {"type": "number"},
  "reasoning": {"type": "string"}
}
```

- Combination of `output_format: "structured"` + `output_schema`
- Pydantic-based validation ensures the structure of LLM responses
- Individual fields accessible in subsequent nodes via `{{ nodes.agent.response.action }}`

### Preset Types

| Preset | Role |
|--------|------|
| `custom` | Write your own system_prompt |
| `risk_manager` | Risk management expert |
| `technical_analyst` | Technical analysis expert |
| `news_analyst` | News/market analyst |
| `strategist` | Comprehensive strategy decision-making |

### Real-time Protection: cooldown_sec

```json
"cooldown_sec": 300
```

- Prevents excessive LLM calls when connected to real-time nodes (RealMarketDataNode, etc.)
- Agent executes only at 300-second (5-minute) intervals
- Direct connection to real-time nodes blocked without ThrottleNode

## AI Agent Notes

1. **Stateless**: Independent per execution (no conversation memory, queries current data directly via Tools)
2. **Credential separation**: LLM credentials and brokerage credentials are separate
3. **cooldown_sec**: Required when connected to real-time nodes (default 60 seconds)
4. **Tool Result Compact**: Large data is automatically compressed to save tokens
5. **Listeners**: Monitor via `on_token_usage`, `on_ai_tool_call`, `on_llm_stream` callbacks
