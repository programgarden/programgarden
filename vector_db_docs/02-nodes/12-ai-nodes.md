---
category: node_reference
tags: [ai, llm, agent, tool_edge]
priority: high
---

# AI Nodes: LLMModelNode, AIAgentNode

## LLMModelNode

Connects to an LLM (Large Language Model) API. Just as BrokerNode connects to a broker, LLMModelNode connects to an AI service.

```json
{
  "id": "llm",
  "type": "LLMModelNode",
  "credential_id": "my-openai-cred",
  "model": "gpt-4o",
  "temperature": 0.3,
  "max_tokens": 2000
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `credential_id` | string | - | LLM API credential ID |
| `model` | string | `"gpt-4o"` | Model name |
| `temperature` | number | `0.7` | Response creativity (0.0=precise, 2.0=creative) |
| `max_tokens` | number | `1000` | Maximum response length (100~128000) |
| `streaming` | boolean | `false` | Whether to stream responses |

**Supported LLM Providers:**

| Provider | Credential Type | Representative Models |
|----------|----------------|----------------------|
| OpenAI | `llm_openai` | gpt-4o, gpt-4o-mini |
| Anthropic | `llm_anthropic` | claude-sonnet-4-5-20250929 |
| Google | `llm_google` | gemini-2.0-flash |
| Azure OpenAI | `llm_azure_openai` | (use deployment name) |
| Ollama | `llm_ollama` | llama3, mistral (local, free) |

**Output**: `connection` - LLM connection (delivered to AIAgentNode via `ai_model` edge)

**Recommended temperature**: Investment analysis `0.1~0.3`, strategy ideas `0.7~1.0`

## AIAgentNode

An AI agent that analyzes markets and makes decisions by using other workflow nodes as tools.

```json
{
  "id": "agent",
  "type": "AIAgentNode",
  "preset": "technical_analyst",
  "user_prompt": "Analyze recent charts for AAPL and NVDA and evaluate buy suitability.",
  "output_format": "json",
  "max_tool_calls": 10,
  "cooldown_sec": 60
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `preset` | string | `"custom"` | Agent preset |
| `system_prompt` | string | - | Role instructions (required for custom) |
| `user_prompt` | string | - | Question/instruction (expressions supported) |
| `output_format` | string | `"text"` | `text`, `json`, `structured` |
| `output_schema` | object | - | Response structure for structured mode |
| `max_tool_calls` | number | `10` | Maximum tool calls (1~50) |
| `timeout_seconds` | number | `60` | Maximum execution time (seconds) |
| `cooldown_sec` | number | `60` | Minimum wait between executions (seconds, 1~3600) |

**Presets:**

| Preset | Role | Suitable For |
|--------|------|-------------|
| `technical_analyst` | Technical analyst | RSI, MACD chart analysis |
| `risk_manager` | Risk manager | Position risk assessment |
| `news_analyst` | News analyst | News/event impact analysis |
| `strategist` | General strategist | Overall portfolio strategy |
| `custom` | User-defined | Specify directly with system_prompt |

**Connection Method (3 Edge Types):**

```json
{
  "edges": [
    {"from": "llm", "to": "agent", "type": "ai_model"},
    {"from": "history", "to": "agent", "type": "tool"},
    {"from": "market", "to": "agent", "type": "tool"},
    {"from": "broker", "to": "agent"}
  ]
}
```

| Edge Type | Purpose | Required |
|-----------|---------|:--------:|
| `ai_model` | LLM connection | O (1) |
| `tool` | Register existing nodes as tools | - (multiple allowed) |
| `main` | Execution order | - |

**Output**: `response` - AI response

**Key Rules:**
- `tool` edge nodes are called only when AI deems necessary (not always executed)
- Direct connection from real-time nodes is blocked (ThrottleNode required)
- Stateless: No memory of previous conversations per execution
- `cooldown_sec` prevents excessive API calls

**Complete AI Agent Workflow:**

```json
{
  "nodes": [
    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker-cred"},
    {"id": "llm", "type": "LLMModelNode", "credential_id": "openai-cred", "model": "gpt-4o", "temperature": 0.3},
    {"id": "history", "type": "OverseasStockHistoricalDataNode", "interval": "1d"},
    {"id": "market", "type": "OverseasStockMarketDataNode"},
    {"id": "account", "type": "OverseasStockAccountNode"},
    {"id": "agent", "type": "AIAgentNode", "preset": "technical_analyst",
     "user_prompt": "Perform technical analysis on current holdings and watchlist symbols.",
     "output_format": "json", "max_tool_calls": 15}
  ],
  "edges": [
    {"from": "broker", "to": "history"},
    {"from": "broker", "to": "market"},
    {"from": "broker", "to": "account"},
    {"from": "llm", "to": "agent", "type": "ai_model"},
    {"from": "history", "to": "agent", "type": "tool"},
    {"from": "market", "to": "agent", "type": "tool"},
    {"from": "account", "to": "agent", "type": "tool"}
  ],
  "credentials": [
    {"credential_id": "broker-cred", "type": "broker_ls_overseas_stock",
     "data": [{"key": "appkey", "value": "", "type": "password", "label": "App Key"},
              {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"}]},
    {"credential_id": "openai-cred", "type": "llm_openai",
     "data": [{"key": "api_key", "value": "", "type": "password", "label": "API Key"}]}
  ]
}
```
