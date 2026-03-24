---
category: workflow_example
tags: [example, http, field_mapping, data, HTTPRequestNode, FieldMappingNode, SQLiteNode, external_api, transform, resilience]
priority: medium
---

# Example: Data Processing

## Overview

A data processing workflow utilizing external API calls (HTTPRequestNode), data transformation (FieldMappingNode), and DB storage (SQLiteNode).

## Example 1: HTTP Request + Data Transformation + Display

Calls an external API and transforms the response data to display as a table.

```json
{
  "nodes": [
    {"id": "start", "type": "StartNode"},
    {
      "id": "api_call",
      "type": "HTTPRequestNode",
      "method": "GET",
      "url": "https://httpbin.org/json",
      "timeout_seconds": 30,
      "resilience": {
        "retry": {
          "enabled": true,
          "max_retries": 3,
          "base_delay": 1.0,
          "exponential_backoff": true
        },
        "fallback": {
          "mode": "error"
        }
      }
    },
    {
      "id": "mapper",
      "type": "FieldMappingNode",
      "data": "{{ nodes.api_call.response }}",
      "mappings": [
        {"from": "slideshow.title", "to": "title"},
        {"from": "slideshow.author", "to": "author"}
      ],
      "preserve_unmapped": true
    },
    {
      "id": "display",
      "type": "TableDisplayNode",
      "title": "HTTP Response Result",
      "data": "{{ [nodes.mapper.data] }}",
      "columns": ["title", "author"]
    }
  ],
  "edges": [
    {"from": "start", "to": "api_call"},
    {"from": "api_call", "to": "mapper"},
    {"from": "mapper", "to": "display"}
  ],
  "credentials": []
}
```

### DAG Structure

```
StartNode → HTTPRequestNode → FieldMappingNode → TableDisplayNode
```

### HTTPRequestNode Settings

| Field | Description |
|------|------|
| `method` | HTTP method (`GET`, `POST`, `PUT`, `DELETE`) |
| `url` | Request URL |
| `headers` | Headers (optional) |
| `body` | Request body (optional, POST/PUT) |
| `timeout_seconds` | Timeout (seconds) |
| `resilience` | Retry/fallback settings |

### FieldMappingNode Settings

| Field | Description |
|------|------|
| `data` | Input data (binding) |
| `mappings` | Array of field mapping rules |
| `preserve_unmapped` | Whether to preserve unmapped fields |

### mappings Structure

```json
"mappings": [
  {"from": "slideshow.title", "to": "title"},
  {"from": "slideshow.author", "to": "author"}
]
```

- `from`: Source field path (access nested objects with `.`)
- `to`: Transformed field name

### Resilience (Retry) Settings

In this example, resilience is configured on the HTTPRequestNode:

```json
"resilience": {
  "retry": {
    "enabled": true,
    "max_retries": 3,
    "base_delay": 1.0,
    "exponential_backoff": true
  },
  "fallback": {"mode": "error"}
}
```

- **Retry**: Up to 3 retries on failure
- **Exponential backoff**: 1s → 2s → 4s (±25% jitter)
- **Fallback**: Raise error if all retries fail

### Fallback Modes

| Mode | Behavior |
|------|------|
| `error` | Raise error, halt workflow |
| `skip` | Skip node, return `_skipped: true` |
| `default_value` | Return default value |

## Example 2: External API → Default Value Fallback

Returns a default value on API failure to continue the workflow.

```json
{
  "id": "api_call",
  "type": "HTTPRequestNode",
  "method": "GET",
  "url": "https://api.example.com/data",
  "resilience": {
    "retry": {
      "enabled": true,
      "max_retries": 2,
      "retry_on": ["timeout", "server_error"]
    },
    "fallback": {
      "mode": "default_value",
      "default_value": {
        "data": [],
        "status": "unavailable"
      }
    }
  }
}
```

- `retry_on`: Retry only on specific error types (`timeout`, `server_error` only)
- If all retries fail, `default_value` is returned so subsequent nodes continue executing

## Key Patterns

### HTTPRequestNode → No Credential Required

HTTPRequestNode can run independently without a BrokerNode. `credentials: []` can be left empty.

### Data Transformation Pipeline

```
External API → FieldMappingNode → Normalized data → Subsequent nodes
```

FieldMappingNode transforms complex API responses into a structure that is easy to use within the workflow.
