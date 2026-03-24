---
category: workflow_structure
tags: [credential, broker, api_key, paper_trading]
priority: high
---

# Credential System

## What are Credentials?

A system for managing sensitive authentication information such as broker API keys and LLM API keys. Defined in the `credentials` array of the workflow JSON and referenced by nodes via `credential_id`.

## Basic Structure

```json
{
  "credentials": [
    {
      "credential_id": "my-broker",
      "type": "broker_ls_overseas_stock",
      "data": [
        {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
        {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"}
      ]
    }
  ]
}
```

| Field | Description |
|-------|-------------|
| `credential_id` | Unique ID. Referenced by node's `credential_id` field |
| `type` | Authentication type (see type list below) |
| `data` | Authentication data array |

### data Array Items

| Field | Description |
|-------|-------------|
| `key` | Data key (e.g., `appkey`, `api_key`) |
| `value` | Actual value (leave as empty string when sharing) |
| `type` | Input type (`password`, `text`, `url`, etc.) |
| `label` | Display label for UI |

## Credential Type List

### Broker

| Type | Description | Required data Keys |
|------|-------------|-------------------|
| `broker_ls_overseas_stock` | LS Securities Overseas Stocks | `appkey`, `appsecret` |
| `broker_ls_overseas_futures` | LS Securities Overseas Futures | `appkey`, `appsecret` |
| `broker_ls_korea_stock` | LS Securities Korea Stocks | `appkey`, `appsecret` |

### LLM (AI Model)

| Type | Description | Required data Keys |
|------|-------------|-------------------|
| `llm_openai` | OpenAI (GPT) | `api_key` |
| `llm_anthropic` | Anthropic (Claude) | `api_key` |
| `llm_google` | Google (Gemini) | `api_key` |
| `llm_azure_openai` | Azure OpenAI | `api_key`, `endpoint`, `deployment` |
| `llm_ollama` | Ollama (Local LLM) | `base_url` |

### HTTP (External API)

| Type | Description | Required data Keys |
|------|-------------|-------------------|
| `http_custom` | Custom HTTP Authentication | Free-form array |
| `http_bearer` | Bearer Token | `token` |
| `http_basic` | Basic Auth | `username`, `password` |

## Referencing Credentials from Nodes

Specify the credential's `credential_id` in the node's `credential_id` field:

```json
{
  "nodes": [
    {
      "id": "broker",
      "type": "OverseasStockBrokerNode",
      "credential_id": "my-broker"
    },
    {
      "id": "llm",
      "type": "LLMModelNode",
      "credential_id": "openai-cred",
      "model": "gpt-4o"
    }
  ],
  "credentials": [
    {
      "credential_id": "my-broker",
      "type": "broker_ls_overseas_stock",
      "data": [
        {"key": "appkey", "value": "YOUR_KEY", "type": "password", "label": "App Key"},
        {"key": "appsecret", "value": "YOUR_SECRET", "type": "password", "label": "App Secret"}
      ]
    },
    {
      "credential_id": "openai-cred",
      "type": "llm_openai",
      "data": [
        {"key": "api_key", "value": "sk-...", "type": "password", "label": "API Key"}
      ]
    }
  ]
}
```

## Paper Trading Setup

To use paper trading for overseas stocks/futures, set `paper_trading: true` on the BrokerNode:

```json
{
  "id": "broker",
  "type": "OverseasStockBrokerNode",
  "credential_id": "my-broker",
  "paper_trading": true
}
```

| Product | Live Trading | Paper Trading | Note |
|---------|:----------:|:------------:|------|
| Overseas Stocks | O | O | Real-time quotes available in live only |
| Overseas Futures | O | O | Real-time supported in paper trading too |
| Korea Stocks | O | - | Finance API only (workflow nodes in progress) |

## Security Notes

- Leave `value` as an empty string (`""`) when sharing workflows
- The server injects encrypted values at execution time
- Managing via environment variables in `.env` files is recommended
- `credential_id` cannot be used in dynamic nodes (blocked for security)
