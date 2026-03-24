---
category: node_reference
tags: [risk, portfolio, drawdown]
priority: high
---

# Risk Nodes: PortfolioNode

## PortfolioNode

Manages capital allocation and rebalancing for multi-strategy portfolios.

```json
{
  "id": "portfolio",
  "type": "PortfolioNode",
  "total_capital": 100000,
  "allocation_method": "equal",
  "rebalance_rule": "drift",
  "drift_threshold": 5.0,
  "reserve_percent": 10
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `total_capital` | number | `100000` | Total investment capital (USD) |
| `allocation_method` | string | `"equal"` | Capital allocation method |
| `rebalance_rule` | string | `"none"` | Rebalancing rule |
| `drift_threshold` | number | `5.0` | Allocation drift tolerance (%) |
| `reserve_percent` | number | `0` | Cash reserve ratio (%) |

**Allocation Methods (allocation_method):**

| Method | Description | Example ($100,000, 3 strategies) |
|--------|-------------|----------------------------------|
| `equal` | Equal allocation | $33,333 each |
| `custom` | User-defined | RSI 50%, MACD 30%, BB 20% |
| `risk_parity` | Inverse volatility | More to stable strategies |
| `momentum` | Proportional to recent returns | Concentrate on winning strategies |

**Rebalancing Rules (rebalance_rule):**

| Rule | Description |
|------|-------------|
| `none` | No rebalancing |
| `periodic` | Periodic (daily/weekly/monthly/quarterly) |
| `drift` | When allocation deviates by threshold% or more |
| `both` | Periodic + drift |

**Output:**
- `combined_equity` - Combined equity curve
- `allocation_weights` - Allocation ratios
- `rebalance_signal` - Rebalancing signal
- `allocated_capital` - Per-strategy allocated amount

**Usage**: Setting `reserve_percent: 10` to always keep 10% in cash provides buying power for additional purchases during sharp drops.
