---
category: node_reference
tags: [schedule, cron, trading_hours]
priority: high
---

# Schedule Nodes: Schedule, TradingHoursFilter

## ScheduleNode

Repeatedly executes the workflow on a cron schedule.

```json
{
  "id": "schedule",
  "type": "ScheduleNode",
  "cron": "0 */15 9-16 * * mon-fri",
  "timezone": "America/New_York"
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `cron` | string | `"*/5 * * * *"` | Cron expression |
| `timezone` | string | `"America/New_York"` | Timezone |
| `enabled` | boolean | `true` | Whether enabled |

**Common Cron Examples:**

| Expression | Description |
|-----------|-------------|
| `0 30 9 * * *` | Every day at 9:30 AM (New York time) |
| `0 */15 9-16 * * mon-fri` | Weekdays 9-16, every 15 minutes |
| `0 0 9 * * mon` | Every Monday at 9:00 |
| `0 0 23 * * *` | Daily at 08:00 Korea time (23:00 New York) |

**Output**: `trigger` - Schedule trigger signal

**Note**: Set to New York time (`America/New_York`) for US stocks.

**LS Securities US Stock Trading Hours (Korea Time):**

| Session | Winter | Summer (DST, Mar~Nov) |
|---------|--------|----------------------|
| Day trading | 10:00~17:30 | 09:00~16:30 |
| Pre-market | 18:00~23:30 | 17:00~22:30 |
| Regular hours | 23:30~06:00 | 22:30~05:00 |
| After-hours | 06:00~09:30 | 05:00~08:30 |

Only limit orders are available during day trading sessions, so use the `LimitOrder` plugin.

## TradingHoursFilterNode

A trading hours filter. Waits when outside trading hours and passes through when trading hours begin.

```json
{
  "id": "tradingHours",
  "type": "TradingHoursFilterNode",
  "start": "09:30",
  "end": "16:00",
  "timezone": "America/New_York",
  "days": ["mon", "tue", "wed", "thu", "fri"]
}
```

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `start` | string | O | Start time (HH:MM) |
| `end` | string | O | End time (HH:MM) |
| `timezone` | string | O | Timezone |
| `days` | array | O | Active days |

**Behavior:**

| Situation | Behavior |
|-----------|----------|
| Within trading hours | Pass through immediately |
| Outside trading hours | Wait until trading hours (blocking) |

**Output**: `passed` (whether passed), `blocked` (whether blocked)

**Note**: If workflow starts outside trading hours, it will wait at this node. Combine with ScheduleNode to ensure execution only during trading hours.
