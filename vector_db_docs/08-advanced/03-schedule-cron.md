---
category: advanced
tags: [schedule, cron, trading_hours, ScheduleNode, TradingHoursFilterNode, timezone, trigger, periodic]
priority: medium
---

# Schedule/Cron Configuration Guide

## Overview

ProgramGarden uses `ScheduleNode` and `TradingHoursFilterNode` to control workflow execution intervals and trading hours filtering.

## ScheduleNode

Triggers periodic execution using cron expressions.

### Configuration Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `cron` | string | `"*/5 * * * *"` | Cron expression |
| `timezone` | string | `"America/New_York"` | IANA timezone |
| `enabled` | boolean | `true` | Enable/disable schedule |

### Cron Expression Format

```
┌────── Minute (0-59)
│ ┌──── Hour (0-23)
│ │ ┌── Day (1-31)
│ │ │ ┌── Month (1-12)
│ │ │ │ ┌── Day of week (0-7, 0=Sunday, 7=Sunday)
│ │ │ │ │
* * * * *
```

### Common Cron Examples

| Expression | Description |
|------------|-------------|
| `*/5 * * * *` | Every 5 minutes |
| `*/30 * * * *` | Every 30 minutes |
| `0 * * * *` | Every hour on the hour |
| `0 9 * * 1-5` | Weekdays at 9:00 AM |
| `0 9,16 * * 1-5` | Weekdays at 9:00 AM and 4:00 PM |
| `0 23 * * 1-5` | Weekdays at 11:00 PM (before US market open in KST) |
| `30 9 * * 1-5` | Weekdays at 9:30 AM (US regular market open) |
| `0 16 * * 1-5` | Weekdays at 4:00 PM (US regular market close) |
| `0 0 1 * *` | First of every month at midnight |

### Workflow JSON

```json
{
  "id": "schedule",
  "type": "ScheduleNode",
  "cron": "0 9 * * 1-5",
  "timezone": "America/New_York",
  "enabled": true
}
```

### Timezone Guide

| Market | Timezone | Regular Hours |
|--------|----------|---------------|
| US (NYSE/NASDAQ) | `America/New_York` | 09:30~16:00 ET |
| US market in KST | `Asia/Seoul` | (configure separately) |
| Hong Kong (HKEX) | `Asia/Hong_Kong` | 09:30~16:00 HKT |
| Europe (EUREX) | `Europe/London` | 08:00~16:30 GMT |

### ScheduleNode and Execution Modes

The WorkflowJob's execution mode varies depending on the presence of a ScheduleNode:

| ScheduleNode | stay_connected | Behavior |
|:---:|:---:|------|
| None | False | One-shot: Execute once |
| None | True | Maintain real-time node connections |
| **Present** | False | Execute per schedule, disconnected between runs |
| **Present** | True | Schedule execution + real-time connection maintained |

## TradingHoursFilterNode

A filter that only passes signals during trading hours.

### Configuration Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `start` | string | `"09:30"` | Start time (HH:MM, 24-hour) |
| `end` | string | `"16:00"` | End time (HH:MM, 24-hour) |
| `timezone` | string | `"America/New_York"` | IANA timezone |
| `days` | array | `["mon","tue","wed","thu","fri"]` | Active days of the week |

### Output Ports

| Port | Description |
|------|-------------|
| `passed` | Within trading hours: Signal passes through |
| `blocked` | Outside trading hours: Signal blocked |

### Behavior

- **Within** trading hours: Passes immediately (`passed=True`)
- **Outside** trading hours: Waits until trading hours begin (checks every 1 minute)
- On workflow termination: Graceful shutdown

### Workflow JSON

```json
{
  "id": "trading_hours",
  "type": "TradingHoursFilterNode",
  "start": "09:30",
  "end": "16:00",
  "timezone": "America/New_York",
  "days": ["mon", "tue", "wed", "thu", "fri"]
}
```

## Practical Patterns

### Pattern 1: Check Account Balance at Market Open Daily

```json
{
  "nodes": [
    {"id": "schedule", "type": "ScheduleNode",
     "cron": "30 9 * * 1-5", "timezone": "America/New_York"},
    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "cred"},
    {"id": "account", "type": "OverseasStockAccountNode"}
  ],
  "edges": [
    {"from": "schedule", "to": "broker"},
    {"from": "broker", "to": "account"}
  ]
}
```

### Pattern 2: Schedule + Trading Hours Filter

```json
{
  "nodes": [
    {"id": "schedule", "type": "ScheduleNode",
     "cron": "*/30 * * * *", "timezone": "America/New_York"},
    {"id": "trading_hours", "type": "TradingHoursFilterNode",
     "start": "09:30", "end": "15:50", "timezone": "America/New_York"},
    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "cred"},
    {"id": "account", "type": "OverseasStockAccountNode"}
  ],
  "edges": [
    {"from": "schedule", "to": "trading_hours"},
    {"from": "trading_hours", "to": "broker"},
    {"from": "broker", "to": "account"}
  ]
}
```

Triggers every 30 minutes, but only executes during trading hours (09:30~15:50).

### Pattern 3: Configuration Based on Korea Standard Time (KST)

Scheduling US stocks based on Korea Standard Time:

```json
{
  "id": "schedule",
  "type": "ScheduleNode",
  "cron": "0 23 * * 1-5",
  "timezone": "Asia/Seoul"
}
```

23:00 KST = 09:00 US Eastern Time (10:00 during daylight saving time)

## Overseas Stock Trading Hours Reference

| Category | US Local Time | Korea Standard Time (KST) |
|----------|--------------|---------------------------|
| Regular hours | 09:30~16:00 ET | 23:30~06:00 |
| Pre-market | 04:00~09:30 ET | 18:00~23:30 |
| After-market | 16:00~20:00 ET | 06:00~10:00 |
| LS Securities daytime trading | - | Available AM/PM |

## Important Notes

1. **ScheduleNode replaces StartNode**: When a ScheduleNode is present, the workflow operates without a StartNode
2. **Verify timezone**: Cron times are based on the `timezone` setting. Use `America/New_York` for US market-based schedules
3. **Daylight saving time**: `America/New_York` automatically accounts for daylight saving time
4. **Minimum interval**: Very short intervals (< 1 minute) may trigger API rate limits
