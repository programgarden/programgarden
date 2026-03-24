---
category: execution
tags: [risk, tracker, hwm, drawdown, WorkflowRiskTracker, high_water_mark, sliding_window, risk_events, strategy_state, feature_gated, hot_layer, cold_layer]
priority: medium
---

# WorkflowRiskTracker

## Overview

`WorkflowRiskTracker` is a **feature-gated 2-layer** infrastructure that tracks risk management data for workflows. When nodes/plugins within a workflow declare the features they need, only those features are activated. If no one declares any features, the tracker is not created at all.

## Opt-in Mechanism

### Declaration in Nodes

```python
from typing import ClassVar, Set

class PortfolioNode(BaseNode):
    _risk_features: ClassVar[Set[str]] = {"hwm", "window"}
```

### Declaration in Plugins (Module Level)

```python
# plugins/trailing_stop.py
risk_features: Set[str] = {"hwm"}

async def trailing_stop(data, fields, context=None, **kwargs):
    if context and context.risk_tracker:
        hwm = context.risk_tracker.get_hwm("AAPL")
```

### Activation Condition

```
Are there any nodes/plugins with _risk_features declared in the workflow?
    ├─ No → context.risk_tracker = None (not created)
    └─ Yes → Initialize with the union of all declared features
```

## 4 Features

| Feature | Description | DB Table | Hot Layer | Purpose |
|---------|-------------|----------|-----------|---------|
| `hwm` | HWM/drawdown tracking | `risk_high_water_mark` | `Dict[str, HWMState]` | Track drawdown from peak |
| `window` | Sliding window metrics | (none) | `deque(maxlen=300)` | Volatility/MDD calculation |
| `events` | Risk event audit trail | `risk_events` | (none) | Risk event logging/querying |
| `state` | Strategy state KV store | `strategy_state` | (none) | Strategy state persistence |

## 2-Layer Architecture

### Hot Layer (In-Memory)

- HWM state: `Dict[str, HWMState]` — O(1) lookup/update
- Sliding window: `deque(maxlen=300)` — latest 300 ticks

### Cold Layer (SQLite)

- Shared DB: Tables are added to the existing `{workflow_id}_workflow.db`
- HWM flush: Batch saves only dirty records every 30 seconds
- events/state: Immediate INSERT/UPSERT

```
[Per tick] → Hot Layer (O(1) update)
                ↓ (30-second periodic flush)
            Cold Layer (SQLite batch save)
```

## Feature "hwm" — HWM Tracking

### HWMState

In-memory HWM state structure:

| Field | Type | Description |
|-------|------|-------------|
| `symbol` | str | Stock symbol |
| `exchange` | str | Exchange |
| `hwm_price` | Decimal | High Water Mark price |
| `hwm_datetime` | datetime | HWM timestamp |
| `current_price` | Decimal | Current price |
| `drawdown_pct` | Decimal | Current drawdown (%) |
| `position_qty` | int | Held quantity |
| `position_avg_price` | Decimal | Average purchase price |

### API

```python
# Register symbol (on buy fill)
tracker.register_symbol("AAPL", "NASDAQ", entry_price=150.0, qty=10)

# Update price (per tick)
result = tracker.update_price("AAPL", "NASDAQ", price=155.0)
# → HWMUpdateResult(symbol="AAPL", high_water_mark=155.0, drawdown_pct=0.0, hwm_updated=True)

result = tracker.update_price("AAPL", "NASDAQ", price=148.0)
# → HWMUpdateResult(symbol="AAPL", high_water_mark=155.0, drawdown_pct=4.52, hwm_updated=False)

# Query
state = tracker.get_hwm("AAPL")
all_hwm = tracker.get_all_hwm()

# Check drawdown threshold
is_over = tracker.check_drawdown_threshold("AAPL", threshold_pct=5.0)

# Unregister symbol (on liquidation)
tracker.unregister_symbol("AAPL")
```

### HWMUpdateResult

Return value of `update_price()`:

| Field | Type | Description |
|-------|------|-------------|
| `symbol` | str | Stock symbol |
| `high_water_mark` | Decimal | High water mark |
| `current_price` | Decimal | Current price |
| `drawdown_pct` | Decimal | Drawdown (%) |
| `hwm_updated` | bool | Whether the high water mark was updated |

### Additional Purchase Handling

When `register_symbol()` is called on an already-registered symbol, the average purchase price is recalculated:

```python
tracker.register_symbol("AAPL", "NASDAQ", entry_price=150.0, qty=10)
tracker.register_symbol("AAPL", "NASDAQ", entry_price=160.0, qty=5)
# → position_qty=15, position_avg_price=153.33, HWM retains existing value
```

### DB Table (risk_high_water_mark)

```sql
CREATE TABLE risk_high_water_mark (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product TEXT NOT NULL,
    provider TEXT NOT NULL,
    symbol TEXT NOT NULL,
    exchange TEXT,
    high_water_mark REAL NOT NULL,
    hwm_datetime TEXT NOT NULL,
    current_price REAL,
    current_drawdown_pct REAL,
    position_qty INTEGER,
    position_avg_price REAL,
    trading_mode TEXT NOT NULL DEFAULT 'live',
    updated_at TEXT NOT NULL,
    UNIQUE(product, provider, symbol, trading_mode)
)
```

### Flush Interval

- Batch saves only `dirty=True` records at **30-second** intervals
- `flush_to_db()`: Manual flush
- `start_flush_loop()`: Start background flush loop
- `stop_flush_loop()`: Stop loop + final flush

### Validation on Restart

When a workflow restarts, it validates that the DB's HWM data matches current positions:

```python
results = tracker.validate_hwm_on_restart(position_tracker)
# → [HWMValidationResult(symbol="AAPL", action="kept", reason="Same position"), ...]
```

| action | Description |
|--------|-------------|
| `kept` | Same position, HWM retained |
| `reset` | Quantity/avg price changed, HWM reset |
| `deleted` | No position (liquidated), HWM deleted |
| `new` | New position, HWM created |

## Feature "window" — Sliding Window

Keeps the latest 300 ticks of price data in memory to calculate volatility and MDD.

### API

```python
# Add tick (auto-linked from update_price, can also be used independently)
tracker.add_tick("AAPL", price=150.5)

# Volatility (standard deviation / mean × 100, None if fewer than 30 ticks)
vol = tracker.get_volatility("AAPL")
# → Decimal("2.35") or None

# Maximum drawdown within window
mdd = tracker.get_max_drawdown_window("AAPL")
# → Decimal("3.21") or None

# MDD for all symbols
mdd_all = tracker.get_max_drawdown_window()

# Tick count in the last 60 seconds
count = tracker.get_tick_count("AAPL", seconds=60)
```

### Window Characteristics

- **Size**: Maximum 300 ticks (`PRICE_WINDOW_SIZE`)
- **Storage**: In-memory only (no DB)
- **Data**: `(symbol, price, timestamp)` tuples
- **Integration**: Automatically added to the window when `update_price()` is called

## Feature "events" — Risk Events

An audit trail feature that records and queries risk events in the DB.

### API

```python
# Record event (immediate DB INSERT)
event_id = tracker.record_risk_event(
    event_type="drawdown_alert",
    severity="warning",        # "info", "warning", "critical"
    symbol="AAPL",
    exchange="NASDAQ",
    details={"drawdown_pct": 5.2, "threshold": 5.0},
    node_id="portfolio-1",
)

# Query events
events = tracker.get_risk_events(
    event_type="drawdown_alert",
    symbol="AAPL",
    limit=50,
)
# → [{"id": 1, "event_type": "drawdown_alert", "severity": "warning", ...}]

# Query event count
count = tracker.get_risk_event_count(
    event_type="drawdown_alert",
    since="2024-01-01T00:00:00+00:00",
)
```

### DB Table (risk_events)

```sql
CREATE TABLE risk_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product TEXT NOT NULL,
    provider TEXT NOT NULL,
    event_type TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'warning',
    symbol TEXT,
    exchange TEXT,
    details TEXT,        -- JSON string
    job_id TEXT,
    node_id TEXT,
    trading_mode TEXT NOT NULL DEFAULT 'live',
    created_at TEXT NOT NULL
)
```

## Feature "state" — Strategy State KV

A Key-Value store for persisting strategy state.

### API

```python
# Save (immediate DB UPSERT)
tracker.save_state("last_trade_time", "2024-01-15T10:30:00")
tracker.save_state("trade_count", 42)
tracker.save_state("config", {"max_position": 100, "stop_loss": 0.05})

# Load
value = tracker.load_state("trade_count", default=0)  # → 42

# Bulk load by prefix
states = tracker.load_states("strategy.")  # → {"param1": ..., "param2": ...}

# Delete
tracker.delete_state("last_trade_time")
count = tracker.delete_states("temp.")  # Bulk delete by prefix

# Snapshot (namespace-level bulk save/restore)
tracker.save_snapshot("portfolio", {
    "total_value": 1000000,
    "positions": {"AAPL": 10, "MSFT": 5},
})
snapshot = tracker.load_snapshot("portfolio")
# → {"total_value": 1000000, "positions": {"AAPL": 10, "MSFT": 5}}
```

### Supported Types

| Python Type | value_type | Description |
|-------------|-----------|-------------|
| `bool` | `"bool"` | True/False |
| `int` | `"int"` | Integer |
| `float` | `"float"` | Floating point |
| `Decimal` | `"decimal"` | Precise floating point |
| `dict`, `list` | `"json"` | JSON serialization |
| `str` (default) | `"string"` | String |

### DB Table (strategy_state)

```sql
CREATE TABLE strategy_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product TEXT NOT NULL,
    provider TEXT NOT NULL,
    state_key TEXT NOT NULL,
    state_value TEXT,
    value_type TEXT NOT NULL DEFAULT 'string',
    trading_mode TEXT NOT NULL DEFAULT 'live',
    updated_at TEXT NOT NULL,
    UNIQUE(product, provider, state_key, trading_mode)
)
```

## Initialization Parameters

```python
tracker = WorkflowRiskTracker(
    db_path="/app/data/wf123_workflow.db",
    job_id="job-abc",
    product="overseas_stock",
    provider="ls",
    trading_mode="live",
    features={"hwm", "window", "events"},
)
```

| Parameter | Description |
|-----------|-------------|
| `db_path` | SQLite DB path (shared with existing workflow DB) |
| `job_id` | Current Job ID (for event recording) |
| `product` | Product (`"overseas_stock"` / `"overseas_futures"` / `"korea_stock"`) |
| `provider` | Brokerage (`"ls"`) |
| `trading_mode` | `"paper"` or `"live"` |
| `features` | Set of features to activate |

## Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `FLUSH_INTERVAL` | 30 | HWM flush interval (seconds) |
| `PRICE_WINDOW_SIZE` | 300 | Sliding window maximum size |
| `METRICS_CACHE_TTL` | 5 | Metrics cache TTL (seconds) |

## Utility Methods

```python
# Check feature
tracker.has_feature("hwm")     # → True
tracker.features                # → frozenset({"hwm", "window"})

# Check if HWM data exists in DB
tracker.has_hwm_data()          # → True/False

# Delete specific symbol's HWM from DB
tracker.delete_hwm_from_db("AAPL")
```

## Plugin Usage Example

### Trailing Stop Plugin

```python
# plugins/trailing_stop.py
risk_features: Set[str] = {"hwm"}

async def trailing_stop(data, fields, context=None, **kwargs):
    if not context or not context.risk_tracker:
        return {"signal": False, "reason": "risk_tracker not activated"}

    tracker = context.risk_tracker
    symbol = fields.get("symbol", "")
    trail_pct = fields.get("trail_pct", 5.0)

    hwm = tracker.get_hwm(symbol)
    if hwm is None:
        return {"signal": False, "reason": "No HWM data"}

    if float(hwm.drawdown_pct) >= trail_pct:
        return {
            "signal": True,
            "reason": f"Trailing stop triggered: drawdown {hwm.drawdown_pct}% >= {trail_pct}%",
            "hwm_price": float(hwm.hwm_price),
            "current_price": float(hwm.current_price),
        }

    return {"signal": False, "drawdown_pct": float(hwm.drawdown_pct)}
```

## Important Notes

1. **Opt-in**: If `_risk_features` is not declared, `context.risk_tracker = None`
2. **Feature cross-linking**: `update_price()` sends data to both hwm and window
3. **Shared DB**: Only adds tables to the existing `{workflow_id}_workflow.db` (not a separate DB)
4. **trading_mode separation**: Paper trading and live trading data are separated in the same DB using the `trading_mode` column
5. **Decimal usage**: Financial data such as HWM and prices are processed precisely using `Decimal`
6. **Memory cleanup**: `stop_flush_loop()` must be called for final flush + loop termination
