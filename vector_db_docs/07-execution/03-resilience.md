---
category: execution
tags: [resilience, retry, fallback, error_handling, RetryConfig, FallbackConfig, ResilienceConfig, RetryableError, FallbackMode, exponential_backoff, BaseMessagingNode, RetryExecutor]
priority: medium
---

# Resilience: Retry and Fallback

## Overview

Resilience is a retry and fallback system for handling failures in nodes that call external APIs. It is configured via the `resilience` field in nodes that inherit from `BaseMessagingNode`.

## Basic Structure

```python
from programgarden_core.models.resilience import (
    ResilienceConfig, RetryConfig, FallbackConfig, FallbackMode
)

class MyAPINode(BaseMessagingNode):
    resilience: ResilienceConfig = Field(
        default_factory=lambda: ResilienceConfig(
            retry=RetryConfig(enabled=True, max_retries=3),
            fallback=FallbackConfig(mode=FallbackMode.SKIP),
        )
    )
```

Configuration in workflow JSON:

```json
{
  "id": "market",
  "type": "OverseasStockMarketDataNode",
  "symbol": "AAPL",
  "exchange": "NASDAQ",
  "resilience": {
    "retry": {
      "enabled": true,
      "max_retries": 3,
      "base_delay": 1.0,
      "exponential_backoff": true
    },
    "fallback": {
      "mode": "skip"
    }
  }
}
```

## RetryConfig

Configures retry behavior.

| Field | Type | Default | Range | Description |
|-------|------|---------|-------|-------------|
| `enabled` | boolean | `false` | - | Enable retries |
| `max_retries` | integer | `3` | 1~10 | Maximum number of retries |
| `base_delay` | float | `1.0` | 0.1~60 | Base delay between retries (seconds) |
| `max_delay` | float | `30.0` | 1~120 | Maximum delay (seconds) |
| `exponential_backoff` | boolean | `true` | - | Enable exponential backoff |
| `retry_on` | list | all | - | List of error types to retry on |

### Exponential Backoff with Jitter

When `exponential_backoff=true`, the delay is calculated as:

```
delay = base_delay × 2^(attempt-1) ± 25% jitter
```

| Attempt | base_delay=1.0 | base_delay=2.0 |
|---------|----------------|----------------|
| 1st | ~1.0s (±0.25) | ~2.0s (±0.5) |
| 2nd | ~2.0s (±0.5) | ~4.0s (±1.0) |
| 3rd | ~4.0s (±1.0) | ~8.0s (±2.0) |

If `max_delay` is exceeded, the delay is capped at `max_delay`.

When `exponential_backoff=false`, the delay is fixed at `base_delay` ± 25% jitter for every attempt.

## RetryableError

Retryable error types. The node's `is_retryable_error()` method classifies errors.

| Error Type | Value | Description |
|------------|-------|-------------|
| `TIMEOUT` | `"timeout"` | Request timeout |
| `RATE_LIMIT` | `"rate_limit"` | API rate limit exceeded |
| `NETWORK_ERROR` | `"network_error"` | Network connection error |
| `SERVER_ERROR` | `"server_error"` | Server 5xx error |
| `PARSE_ERROR` | `"parse_error"` | Response parsing error |

### retry_on Filter

Configure retries for specific error types only:

```json
{
  "retry": {
    "enabled": true,
    "max_retries": 3,
    "retry_on": ["timeout", "rate_limit", "network_error"]
  }
}
```

By default, all RetryableError types are retried. If `is_retryable_error()` returns `None`, no retry is attempted (e.g., authentication failure, invalid parameters).

## FallbackConfig

Configures how to handle failures after all retries are exhausted.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `mode` | FallbackMode | `"error"` | Fallback mode |
| `default_value` | dict (optional) | None | Default value to return when `mode="default_value"` |

### FallbackMode

| Mode | Value | Behavior |
|------|-------|----------|
| `ERROR` | `"error"` | Re-raise the exception and abort the workflow |
| `SKIP` | `"skip"` | Skip the node and continue |
| `DEFAULT_VALUE` | `"default_value"` | Return the specified default value and continue |

### ERROR Mode

```json
{"fallback": {"mode": "error"}}
```

The original exception is raised as-is. The node state changes to `FAILED`, and subsequent nodes are not executed.

### SKIP Mode

```json
{"fallback": {"mode": "skip"}}
```

Return value:
```python
{
    "_skipped": True,
    "_error": "Error message",
    "_error_type": "TimeoutError",
}
```

The node state changes to `SKIPPED`. Subsequent nodes can receive and process this result.

### DEFAULT_VALUE Mode

```json
{
  "fallback": {
    "mode": "default_value",
    "default_value": {
      "price": 0,
      "status": "unavailable"
    }
  }
}
```

Return value:
```python
{
    "price": 0,
    "status": "unavailable",
    "_fallback": True,
    "_error": "Error message",
}
```

## ResilienceConfig

A configuration that combines `RetryConfig` + `FallbackConfig` into one.

```python
class ResilienceConfig:
    retry: RetryConfig = RetryConfig()       # Default: enabled=False
    fallback: FallbackConfig = FallbackConfig()  # Default: mode=ERROR
```

## RetryExecutor

`RetryExecutor` is a common class that executes retry logic. It is automatically used by all nodes that inherit from `BaseMessagingNode`.

### Execution Flow

```
execute_fn() called
    ↓
Success? → Return result
    ↓ (Failure)
is_retryable_error(e) → Retryable?
    ├─ No → Fallback handling
    └─ Yes → Included in retry_on?
        ├─ No → Fallback handling
        └─ Yes → Last attempt?
            ├─ Yes → Fallback handling
            └─ No → Calculate delay → on_retry event → sleep → Retry call
```

### Retry Events

Each retry generates a `RetryEvent` that is delivered to listeners:

```python
RetryEvent(
    job_id="job-abc123",
    node_id="market-1",
    attempt=2,               # Current attempt (starting from 1)
    max_retries=3,            # Maximum retry count
    error_type=RetryableError.TIMEOUT,
    error_message="Request timed out after 10s",
    next_retry_in=2.3,        # Seconds until next retry
)
```

## Default Settings by Node Type

### General API Nodes (Market Data, Account Balance, etc.)

```python
resilience = ResilienceConfig(
    retry=RetryConfig(enabled=True, max_retries=3),
    fallback=FallbackConfig(mode=FallbackMode.SKIP),
)
```

### Order Nodes (Caution)

Order nodes have retries **disabled by default** due to the risk of **duplicate orders**:

```python
resilience = ResilienceConfig(
    retry=RetryConfig(enabled=False),  # Retries disabled
    fallback=FallbackConfig(mode=FallbackMode.ERROR),
)
```

Users can explicitly enable retries, but caution is needed as idempotency is not guaranteed.

## Workflow JSON Examples

### Market Data Query + Retry

```json
{
  "nodes": [
    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "cred"},
    {"id": "market", "type": "OverseasStockMarketDataNode",
     "symbol": "AAPL", "exchange": "NASDAQ",
     "resilience": {
       "retry": {"enabled": true, "max_retries": 3, "base_delay": 1.0},
       "fallback": {"mode": "skip"}
     }}
  ],
  "edges": [{"from": "broker", "to": "market"}]
}
```

### Historical Data + Default Value Fallback

```json
{
  "id": "history",
  "type": "OverseasStockHistoricalDataNode",
  "symbol": "AAPL",
  "exchange": "NASDAQ",
  "resilience": {
    "retry": {"enabled": true, "max_retries": 2, "retry_on": ["timeout", "server_error"]},
    "fallback": {
      "mode": "default_value",
      "default_value": {"values": [], "count": 0}
    }
  }
}
```

## Important Notes

1. **Order node retries**: Disabled by default due to duplicate order risk. Verify idempotency before enabling
2. **retry_on default**: All RetryableError types are retried if not specified
3. **max_delay cap**: Exponential backoff does not exceed `max_delay` (default 30 seconds)
4. **Fallback result distinction**: Use `_skipped`, `_fallback`, `_error` fields to distinguish normal vs. fallback results
5. **Listener notifications**: The `on_retry` callback is invoked for each retry attempt
