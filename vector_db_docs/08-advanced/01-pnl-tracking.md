---
category: advanced
tags: [pnl, profit, loss, tracking, trading_mode, WorkflowPnLEvent, on_workflow_pnl_update, FIFO, PositionDetail, start_date, competition]
priority: high
---

# P&L Tracking System

## Overview

ProgramGarden tracks P&L in real-time during workflow execution. It separates workflow positions from manual positions using FIFO and delivers real-time data via the `on_workflow_pnl_update` callback.

## P&L Event (WorkflowPnLEvent)

Generated when a real-time account node (`OverseasStockRealAccountNode`, `OverseasFuturesRealAccountNode`, `KoreaStockRealAccountNode`) is active and account data changes.

```python
class MyListener(BaseExecutionListener):
    async def on_workflow_pnl_update(self, event: WorkflowPnLEvent):
        print(f"Product: {event.product}, Currency: {event.currency}")
        print(f"Workflow P&L: {event.workflow_pnl_rate}%")
        print(f"Total P&L: {event.total_pnl_rate}%")
        print(f"Trust: {event.trust_score}/100")
        for pos in event.workflow_positions:
            print(f"  {pos.symbol}: {pos.pnl_rate}%")
```

## Product Types

| Product | Broker Node | Currency | Paper Trading |
|---------|-------------|----------|:---:|
| `overseas_stock` | `OverseasStockBrokerNode` | USD | Not supported |
| `overseas_futures` | `OverseasFuturesBrokerNode` | USD | Supported |
| `korea_stock` | `KoreaStockBrokerNode` | KRW | Not supported (live only) |

## Trading Mode (Paper Trading / Live Trading)

All P&L data is stored separately by `trading_mode`:

| Mode | Value | Description |
|------|-------|-------------|
| Paper trading | `"paper"` | Paper trading environment data |
| Live trading | `"live"` | Live trading environment data |

- Data is **not reset** when switching modes (each is stored independently)
- All DB queries apply a `WHERE trading_mode = ?` filter
- `paper_trading: true` must be included in the **BrokerNode configuration**
- **Korea stock** always uses live trading (`paper_trading: false`)

## Workflow vs Other Positions

| Category | Description |
|----------|-------------|
| `workflow_positions` | Positions ordered by the workflow |
| `other_positions` | Positions ordered manually or from other sources |

Workflow and other positions are automatically separated using FIFO.

## Date-Based P&L (Competition)

Setting a `start_date` on the listener calculates period P&L from a specific date:

| Field | Description |
|-------|-------------|
| `competition_start_date` | P&L start date (YYYYMMDD) |
| `competition_workflow_pnl_rate` | Workflow P&L from start date (%) |
| `competition_workflow_pnl_amount` | Workflow P&L amount from start date |
| `competition_account_pnl_rate` | Account P&L from start date (%) |
| `competition_account_pnl_amount` | Account P&L amount from start date |

Product-specific competition fields are also available (e.g., `competition_workflow_overseas_stock_pnl_rate`, `competition_workflow_korea_stock_pnl_rate`).

## Complete P&L Fields

```python
WorkflowPnLEvent(
    job_id="job-abc",
    broker_node_id="broker",
    product="overseas_stock",        # "overseas_stock" | "overseas_futures" | "korea_stock"
    paper_trading=False,             # korea_stock always False

    # Workflow P&L
    workflow_pnl_rate=2.35,          # Workflow P&L rate (%)
    workflow_eval_amount=10235.0,    # Workflow evaluation amount
    workflow_buy_amount=10000.0,     # Workflow buy amount
    workflow_pnl_amount=235.0,       # Workflow P&L amount

    # Other (manual) P&L
    other_pnl_rate=-1.20,
    other_eval_amount=4940.0,
    other_buy_amount=5000.0,
    other_pnl_amount=-60.0,

    # Total P&L
    total_pnl_rate=1.17,
    total_eval_amount=15175.0,
    total_buy_amount=15000.0,
    total_pnl_amount=175.0,

    # Positions
    workflow_positions=[...],        # List[PositionDetail]
    other_positions=[...],           # List[PositionDetail]

    # Trust
    trust_score=100,                 # 0-100
    anomaly_count=0,

    # Currency
    currency="USD",                  # "USD" or "KRW" (korea_stock)

    # Per-product P&L (v2.0)
    workflow_overseas_stock_pnl_rate=2.35,
    workflow_overseas_futures_pnl_rate=None,
    workflow_korea_stock_pnl_rate=None,

    # Account P&L (v2.0)
    account_total_pnl_rate=1.17,
    account_overseas_stock_pnl_rate=1.17,
    account_korea_stock_pnl_rate=None,
    total_position_count=5,

    # Competition (optional, only if listener has start_date)
    competition_start_date="20260115",
    competition_workflow_pnl_rate=1.85,
    competition_account_pnl_rate=0.92,
)
```

## Real-time P&L Workflow Example

```json
{
  "nodes": [
    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "cred"},
    {"id": "real_account", "type": "OverseasStockRealAccountNode"},
    {"id": "throttle", "type": "ThrottleNode", "mode": "debounce", "interval_ms": 5000}
  ],
  "edges": [
    {"from": "broker", "to": "real_account"},
    {"from": "real_account", "to": "throttle"}
  ]
}
```

P&L is delivered in real-time when you implement `on_workflow_pnl_update` in your listener.

## DB Storage

P&L data is automatically saved to `{workflow_id}_workflow.db`:
- Docker: `/app/data/`
- Local: `./app/data/` (fallback)
