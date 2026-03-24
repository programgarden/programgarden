---
category: workflow_example
tags: [example, schedule, cron, trading_hours, ScheduleNode, TradingHoursFilterNode, trigger, periodic, timezone]
priority: medium
---

# Example: Schedule/Trigger

## Overview

Examples of using ScheduleNode and TradingHoursFilterNode to execute workflows periodically or restrict operation to within trading hours.

## Example 1: Weekday 9 AM Balance Check

Queries account balance every weekday at 9 AM New York time.

```json
{
  "nodes": [
    {
      "id": "schedule",
      "type": "ScheduleNode",
      "cron": "0 9 * * 1-5",
      "timezone": "America/New_York",
      "enabled": true
    },
    {
      "id": "broker",
      "type": "OverseasStockBrokerNode",
      "credential_id": "broker-cred"
    },
    {
      "id": "account",
      "type": "OverseasStockAccountNode"
    }
  ],
  "edges": [
    {"from": "schedule", "to": "broker"},
    {"from": "broker", "to": "account"}
  ],
  "credentials": [{"credential_id": "broker-cred"}]
}
```

### Key Pattern: ScheduleNode Replaces StartNode

- When a ScheduleNode is present, the workflow operates **without a StartNode**
- ScheduleNode acts as the first node and triggers according to the Cron schedule
- `cron: "0 9 * * 1-5"` → Weekdays at 9 AM (Mon-Fri)
- `timezone: "America/New_York"` → Based on New York time (daylight saving time automatically applied)

### Cron Expression

```
┌────── Minute (0-59)
│ ┌──── Hour (0-23)
│ │ ┌── Day (1-31)
│ │ │ ┌── Month (1-12)
│ │ │ │ ┌── Day of week (0-7, 0=Sun, 7=Sun)
* * * * *
```

| Expression | Description |
|--------|------|
| `*/5 * * * *` | Every 5 minutes |
| `*/30 * * * *` | Every 30 minutes |
| `0 * * * *` | Every hour on the hour |
| `0 9 * * 1-5` | Weekdays at 9 AM |
| `30 9 * * 1-5` | Weekdays at 9:30 AM (US regular market open) |
| `0 16 * * 1-5` | Weekdays at 4 PM (US regular market close) |

## Example 2: Schedule + Trading Hours Filter

Triggers every 30 minutes, but only executes within trading hours (09:30-15:50).

```json
{
  "nodes": [
    {
      "id": "schedule",
      "type": "ScheduleNode",
      "cron": "*/30 * * * *",
      "timezone": "America/New_York"
    },
    {
      "id": "trading_hours",
      "type": "TradingHoursFilterNode",
      "start": "09:30",
      "end": "15:50",
      "timezone": "America/New_York",
      "days": ["mon", "tue", "wed", "thu", "fri"]
    },
    {
      "id": "broker",
      "type": "OverseasStockBrokerNode",
      "credential_id": "broker-cred"
    },
    {
      "id": "account",
      "type": "OverseasStockAccountNode"
    }
  ],
  "edges": [
    {"from": "schedule", "to": "trading_hours"},
    {"from": "trading_hours", "to": "broker"},
    {"from": "broker", "to": "account"}
  ],
  "credentials": [{"credential_id": "broker-cred"}]
}
```

### DAG Structure

```
ScheduleNode → TradingHoursFilterNode → BrokerNode → AccountNode
                     ↓
              Within trading hours: Pass through
              Outside trading hours: Wait (checks every 1 minute)
```

### TradingHoursFilterNode Settings

| Field | Description | Default |
|------|------|--------|
| `start` | Start time (HH:MM) | `"09:30"` |
| `end` | End time (HH:MM) | `"16:00"` |
| `timezone` | IANA timezone | `"America/New_York"` |
| `days` | Active days | `["mon","tue","wed","thu","fri"]` |

## Example 3: Pre-US-Market Schedule Based on Korea Time

Executes at 11 PM Korea time (9:00 AM US Eastern, or 10:00 AM during daylight saving time):

```json
{
  "nodes": [
    {
      "id": "schedule",
      "type": "ScheduleNode",
      "cron": "0 23 * * 1-5",
      "timezone": "Asia/Seoul"
    },
    {
      "id": "broker",
      "type": "OverseasStockBrokerNode",
      "credential_id": "broker-cred"
    },
    {
      "id": "account",
      "type": "OverseasStockAccountNode"
    }
  ],
  "edges": [
    {"from": "schedule", "to": "broker"},
    {"from": "broker", "to": "account"}
  ],
  "credentials": [{"credential_id": "broker-cred"}]
}
```

## ScheduleNode and Execution Modes

| ScheduleNode | stay_connected | Behavior |
|:---:|:---:|------|
| None | False | One-shot: Execute once |
| None | True | Maintain real-time node connection |
| Present | False | Execute per schedule, disconnect between runs |
| Present | True | Schedule + maintain real-time connection |

## Timezone Reference

| Market | Timezone | Regular Hours |
|------|--------|--------|
| US (NYSE/NASDAQ) | `America/New_York` | 09:30-16:00 ET |
| Hong Kong (HKEX) | `Asia/Hong_Kong` | 09:30-16:00 HKT |
| Europe (EUREX) | `Europe/London` | 08:00-16:30 GMT |
