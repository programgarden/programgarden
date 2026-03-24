---
category: workflow_structure
tags: [edge, main, ai_model, tool, connection]
priority: critical
---

# Edge Types: main, ai_model, tool

## What is an Edge?

An Edge defines the connection between nodes. When the `from` node completes execution, the `to` node is executed.

```json
{"from": "broker", "to": "account"}
```

## 3 Edge Types

| Type | Default | Description | Usage Example |
|------|:-------:|-------------|---------------|
| `main` | O | DAG execution order connection. This type when `type` is omitted | `broker → account` |
| `ai_model` | - | LLM model connection. Exclusively for LLMModelNode → AIAgentNode | `llm → agent` |
| `tool` | - | AI tool registration. Registers existing nodes as AI tools | `history → agent` |

## main Edge (Default)

The most common edge type. Defines execution order between nodes. Automatically becomes `main` when `type` is omitted.

```json
{
  "edges": [
    {"from": "broker", "to": "watchlist"},
    {"from": "watchlist", "to": "history"},
    {"from": "history", "to": "rsi"},
    {"from": "rsi", "to": "order"}
  ]
}
```

### Broker Auto-Propagation

Broker connection information is automatically propagated to downstream nodes connected via `main` edges from BrokerNode. No separate `connection` binding is needed.

```json
{
  "edges": [
    {"from": "broker", "to": "account"},
    {"from": "broker", "to": "market"},
    {"from": "broker", "to": "order"}
  ]
}
```

### Branching and Merging

A single node can branch to multiple nodes, or multiple nodes can merge into one:

```json
{
  "edges": [
    {"from": "broker", "to": "account"},
    {"from": "broker", "to": "market"},
    {"from": "account", "to": "display"},
    {"from": "market", "to": "display"}
  ]
}
```

## ai_model Edge

Delivers the LLM connection information from LLMModelNode to AIAgentNode. Used only in the **LLMModelNode → AIAgentNode** direction.

```json
{
  "edges": [
    {"from": "llm", "to": "agent", "type": "ai_model"}
  ]
}
```

- LLMModelNode operates in a pattern similar to BrokerNode
- API key, model name, etc. are automatically delivered to AIAgentNode via the `ai_model` edge
- One LLMModelNode can connect to multiple AIAgentNodes

## tool Edge

Registers existing nodes as tools for AIAgentNode. The AI agent calls the corresponding node to fetch data when needed.

```json
{
  "edges": [
    {"from": "history", "to": "agent", "type": "tool"},
    {"from": "market", "to": "agent", "type": "tool"},
    {"from": "account", "to": "agent", "type": "tool"}
  ]
}
```

- Nodes connected via `tool` edges are automatically called by AI when deemed necessary
- Existing nodes can be used as AI tools without modification
- Multiple nodes can be registered as tools for a single AIAgentNode

## Complete AI Agent Edge Example

```json
{
  "nodes": [
    {"id": "llm", "type": "LLMModelNode", "credential_id": "openai-cred",
     "model": "gpt-4o"},
    {"id": "agent", "type": "AIAgentNode", "preset": "technical_analyst",
     "system_prompt": "Perform technical analysis"},
    {"id": "history", "type": "OverseasStockHistoricalDataNode"},
    {"id": "market", "type": "OverseasStockMarketDataNode"}
  ],
  "edges": [
    {"from": "llm", "to": "agent", "type": "ai_model"},
    {"from": "history", "to": "agent", "type": "tool"},
    {"from": "market", "to": "agent", "type": "tool"},
    {"from": "broker", "to": "history"},
    {"from": "broker", "to": "market"}
  ]
}
```

## Edge Rules Summary

1. Automatically becomes `main` type when `type` is omitted
2. `ai_model` must be in LLMModelNode → AIAgentNode direction
3. `tool` must be in existing node → AIAgentNode direction
4. BrokerNode connection info is automatically propagated along `main` edges
5. Circular edges (cycles) are not allowed (DAG structure)
