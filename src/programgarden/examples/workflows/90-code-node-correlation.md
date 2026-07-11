# 90 · CodeNode return-correlation matrix (NASDAQ)

Builds a **pairwise return-correlation matrix** and a per-symbol average correlation using `statistics.correlation`. It is an **educational hand-roll reference** for the `CorrelationAnalysis` community plugin — pure stdlib inside a `CodeNode`, not a new capability.

## Pipeline

```
StartNode → OverseasStockBrokerNode → OverseasStockHistoricalDataNode
          → CodeNode → TableDisplayNode
```

- `OverseasStockHistoricalDataNode` fetches 60 daily bars for 5 NASDAQ names → `values`
- `CodeNode` converts each close series to daily returns and correlates every pair
- `params = {lookback: 40}`; declared `outputs` = `matrix` / `avg_corr` / `skipped` / `status`
- `TableDisplayNode` renders `{{ nodes.corr.avg_corr }}` (symbols sorted by average correlation)

## Outputs

- `matrix` — `[{a, b, corr}]` for every symbol pair (`corr` is `null` when undefined)
- `avg_corr` — `[{symbol, exchange, avg_corr}]`, sorted ascending (most diversifying first)
- `skipped` — `[{symbol, exchange, reason}]` for symbols with fewer than 3 closes
- `status` — `ok` / `insufficient_symbols` / `insufficient_data`

## CodeNode contract

```python
async def execute(data, params, context):
    import statistics
    lookback = int(params.get('lookback', 40))
    rows = [r for r in (data or []) if isinstance(r, dict)]
    if len(rows) < 2:
        return {'matrix': [], 'avg_corr': [], 'skipped': [], 'status': 'insufficient_symbols'}
    series = {}
    order = []
    skipped = []
    for row in rows:
        ts = row.get('time_series') or []
        closes = [b.get('close') for b in ts if isinstance(b, dict) and b.get('close') is not None]
        if len(closes) > lookback + 1:
            closes = closes[-(lookback + 1):]
        if len(closes) < 3:
            skipped.append({'symbol': row.get('symbol'), 'exchange': row.get('exchange'),
                            'reason': 'insufficient_data'})
            continue
        rets = [closes[i] / closes[i - 1] - 1.0 for i in range(1, len(closes)) if closes[i - 1]]
        key = (row.get('symbol'), row.get('exchange'))
        series[key] = rets
        order.append(key)
    if len(order) < 2:
        return {'matrix': [], 'avg_corr': [], 'skipped': skipped, 'status': 'insufficient_data'}
    matrix = []
    by_symbol = {k: [] for k in order}
    for i in range(len(order)):
        for j in range(i + 1, len(order)):
            a = series[order[i]]
            b = series[order[j]]
            n = min(len(a), len(b))
            corr = None
            if n >= 3:
                try:
                    corr = statistics.correlation(a[-n:], b[-n:])
                except statistics.StatisticsError:
                    corr = None
            matrix.append({'a': order[i][0], 'b': order[j][0],
                           'corr': round(corr, 3) if corr is not None else None})
            if corr is not None:
                by_symbol[order[i]].append(corr)
                by_symbol[order[j]].append(corr)
    avg_corr = []
    for k in order:
        vals = by_symbol[k]
        avg_corr.append({'symbol': k[0], 'exchange': k[1],
                         'avg_corr': round(statistics.fmean(vals), 3) if vals else None})
    avg_corr.sort(key=lambda r: (r['avg_corr'] is None, r['avg_corr'] if r['avg_corr'] is not None else 0.0))
    return {'matrix': matrix, 'avg_corr': avg_corr, 'skipped': skipped, 'status': 'ok'}
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
wf = json.load(open('examples/workflows/90-code-node-correlation.json'))
async def main():
    exe = WorkflowExecutor()
    job = await exe.execute(wf, context_params={'dry_run': True, 'max_cycles': 1})
    if getattr(job, '_task', None):
        await asyncio.wait_for(job._task, timeout=60)
    print(job.context.get_all_outputs('corr'))
asyncio.run(main())
"
```

> ⚠️ This targets a real overseas-stock account, but the workflow uses only the
> **fetch → compute → display** path — it places no orders and is safe to dry_run.

## Expected output

- **Real data:** `avg_corr` such as `[{symbol:'NVDA', avg_corr:0.31}, {symbol:'AAPL', avg_corr:0.62}, ...]`; `matrix` holds one row per pair. Symbols with <3 closes appear in `skipped`.
- **dry_run (mocked LS, empty bars):** `{matrix: [], avg_corr: [], skipped: [], status: 'insufficient_symbols'}` (mocked LS returns no bars).

## Edge cases (no silent failure)

- Symbols with fewer than 3 closes go to `skipped` with `reason:'insufficient_data'`.
- A constant (degenerate) series makes `statistics.correlation` raise; the pair's `corr` becomes `null` instead of crashing.
