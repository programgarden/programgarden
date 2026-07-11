# 92 · CodeNode performance & risk metrics (single symbol)

Computes **Sharpe, Sortino, max drawdown, Calmar, annualized volatility and total return** from a single symbol's close series. It is an **educational hand-roll reference** for the `SharpeRatioMonitor`, `SortinoRatio` and `CalmarRatio` community plugins — pure stdlib (`statistics` + `math`) inside a `CodeNode`.

## Pipeline

```
StartNode → OverseasStockBrokerNode → OverseasStockHistoricalDataNode
          → CodeNode → SummaryDisplayNode
```

- `OverseasStockHistoricalDataNode` fetches 120 daily bars for AAPL → `values`
- `CodeNode` converts closes to returns and computes the risk/return metrics
- `params = {periods_per_year: 252, rf: 0.0}`; declared `outputs` = `metrics` (object, `status` carried inside)
- `SummaryDisplayNode` renders `{{ nodes.perf.metrics }}`

## Outputs

- `metrics` — `{symbol, exchange, sharpe, sortino, max_drawdown_pct, calmar, volatility_pct, total_return_pct, status}`

## CodeNode contract

```python
async def execute(data, params, context):
    import statistics, math
    ppy = float(params.get('periods_per_year', 252))
    rf = float(params.get('rf', 0.0))
    rows = [r for r in (data or []) if isinstance(r, dict)]
    if not rows:
        return {'metrics': {'status': 'no_data'}}
    row = rows[0]
    ts = row.get('time_series') or []
    closes = [b.get('close') for b in ts if isinstance(b, dict) and b.get('close') is not None]
    if len(closes) < 3 or closes[0] <= 0:
        return {'metrics': {'status': 'insufficient_data', 'symbol': row.get('symbol')}}
    rets = [closes[i] / closes[i - 1] - 1.0 for i in range(1, len(closes)) if closes[i - 1]]
    if len(rets) < 2:
        return {'metrics': {'status': 'insufficient_data', 'symbol': row.get('symbol')}}
    mean_r = statistics.fmean(rets)
    sd = statistics.pstdev(rets)
    sharpe = ((mean_r - rf / ppy) / sd * math.sqrt(ppy)) if sd else None
    downside = [r for r in rets if r < 0]
    if len(downside) >= 2:
        dd_dev = statistics.pstdev(downside)
    elif downside:
        dd_dev = abs(downside[0])
    else:
        dd_dev = 0.0
    sortino = ((mean_r - rf / ppy) / dd_dev * math.sqrt(ppy)) if dd_dev else None
    peak = closes[0]
    max_dd = 0.0
    for c in closes:
        if c > peak:
            peak = c
        dd = (c / peak - 1.0) if peak else 0.0
        if dd < max_dd:
            max_dd = dd
    total_return_pct = (closes[-1] / closes[0] - 1.0) * 100.0
    growth = closes[-1] / closes[0]
    annual_return = growth ** (ppy / len(rets)) - 1.0 if growth > 0 else None
    calmar = (annual_return / abs(max_dd)) if (annual_return is not None and max_dd != 0) else None
    metrics = {'symbol': row.get('symbol'), 'exchange': row.get('exchange'),
               'sharpe': round(sharpe, 3) if sharpe is not None else None,
               'sortino': round(sortino, 3) if sortino is not None else None,
               'max_drawdown_pct': round(max_dd * 100.0, 2),
               'calmar': round(calmar, 3) if calmar is not None else None,
               'volatility_pct': round(sd * math.sqrt(ppy) * 100.0, 2),
               'total_return_pct': round(total_return_pct, 2), 'status': 'ok'}
    return {'metrics': metrics}
```

- `data` / `params` are evaluated to concrete values before the code runs.
- `context` is a **read-only scrubbed context** — only the safe helpers
  (`context.date/finance/stats/format/lst`), risk snapshots and workflow metadata. **No
  credential / broker / network access.**
- The return value must be **JSON-serializable** (it crosses the child→parent boundary).

## Security (always on, no off switch)

The `CodeNode` body runs in an **app-key-free subprocess**:

1. **Scrubbed context** — no credential access path exists.
2. **Restricted builtins + AST denylist** — `os/socket/urllib/subprocess/open` and introspection
   dunders (`__class__`/`__globals__`/…), plus `eval/exec/getattr`, are blocked. Only
   pure-computation stdlib (`math`, `statistics`, `json`, `datetime`, …) may be imported; any other
   import — numpy, pandas, scipy, pandas-ta, TA-Lib — is rejected with `CODE_NODE_FORBIDDEN`.
3. **Binding lockdown** — credential-like bindings in `data`/`params` are refused.
4. **Subprocess isolation** — fixed worker pool, no app key in the child, JSON-only round trip.

## Run (dry_run end-to-end)

```bash
cd src/programgarden
poetry run python -c "
import asyncio, json
from programgarden import WorkflowExecutor
wf = json.load(open('examples/workflows/92-code-node-perf-metrics.json'))
async def main():
    exe = WorkflowExecutor()
    job = await exe.execute(wf, context_params={'dry_run': True, 'max_cycles': 1})
    if getattr(job, '_task', None):
        await asyncio.wait_for(job._task, timeout=60)
    print(job.context.get_all_outputs('perf'))
asyncio.run(main())
"
```

> ⚠️ This targets a real overseas-stock account, but the workflow uses only the
> **fetch → compute → display** path — it places no orders and is safe to dry_run.

## Expected output

- **Real data:** `metrics` such as `{symbol:'AAPL', sharpe:-1.9, sortino:-2.4, max_drawdown_pct:-18.37, calmar:-1.9, volatility_pct:21.43, total_return_pct:-9.8, status:'ok'}`.
- **dry_run (mocked LS, empty bars):** `{metrics: {status: 'no_data'}}` (mocked LS returns no bars).

## Edge cases (no silent failure)

- When `pstdev==0` (flat returns) or there is no downside, `sharpe`/`sortino` return `null` — not `NaN`.
- Fewer than 3 closes returns `{status:'insufficient_data'}`; all numbers are JSON-finite.
