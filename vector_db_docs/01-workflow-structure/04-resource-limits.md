---
category: workflow_structure
tags: [resource_limits, timeout, parallel]
priority: medium
---

# Resource Limit Settings

## What are resource_limits?

Adding `resource_limits` to the workflow JSON allows you to limit CPU/memory usage. If omitted, the system automatically sets appropriate values.

## Configuration

```json
{
  "resource_limits": {
    "max_cpu_percent": 70,
    "max_memory_percent": 75,
    "max_workers": 2,
    "throttle_strategy": "conservative"
  },
  "nodes": [...],
  "edges": [...]
}
```

## Configuration Fields

| Field | Default | Description |
|-------|---------|-------------|
| `max_cpu_percent` | 80 | Maximum CPU usage (%) |
| `max_memory_percent` | 80 | Maximum memory usage (%) |
| `max_workers` | 4 | Number of concurrent workers |
| `throttle_strategy` | `"gradual"` | Throttle strategy |

### throttle_strategy Options

| Strategy | Description |
|----------|-------------|
| `gradual` | Default. Gradually applies limits based on resource usage |
| `aggressive` | Applies limits quickly. For environments where resource limits are critical |
| `conservative` | Applies limits slowly. Performance-first |

## Auto Throttle Levels

Execution speed is automatically adjusted when resource usage increases:

| Level | Trigger Condition | Behavior |
|-------|-------------------|----------|
| NONE | < 60% | Normal execution |
| LIGHT | 60~75% | 20% batch size reduction |
| MODERATE | 75~85% | 50% batch size reduction |
| HEAVY | 85~95% | 50% concurrent worker limit |
| CRITICAL | > 95% | New tasks paused |

**Important**: Even in CRITICAL state, **order nodes are always executed with priority**. Trading opportunities are never missed.

## Usage Examples

### Resource-Constrained Environment (Small Server)

```json
{
  "resource_limits": {
    "max_cpu_percent": 50,
    "max_memory_percent": 60,
    "max_workers": 1,
    "throttle_strategy": "aggressive"
  }
}
```

### High-Performance Environment (Dedicated Server)

```json
{
  "resource_limits": {
    "max_cpu_percent": 90,
    "max_memory_percent": 90,
    "max_workers": 8,
    "throttle_strategy": "conservative"
  }
}
```

### Using Defaults (Recommended)

Omitting `resource_limits` lets the system automatically set appropriate values. Default values are sufficient for most cases.
