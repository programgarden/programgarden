# 93 · CodeNode pairs spread & z-score (KO / PEP)

Estimates a **log-price hedge ratio** via `statistics.linear_regression` and turns the spread's z-score into a mean-reversion entry signal. It is an **educational hand-roll reference** for the `PairTrading` and `ZScore` community plugins — pure stdlib inside a `CodeNode`.

## Pipeline

```
StartNode → OverseasStockBrokerNode → OverseasStockHistoricalDataNode
          → CodeNode → SummaryDisplayNode
```

- `OverseasStockHistoricalDataNode` fetches 90 daily bars for KO@NYSE and PEP@NASDAQ → `values`
- `CodeNode` regresses `log(A)` on `log(B)` for the hedge ratio, then z-scores the spread
- `params = {entry_z: 2.0}`; declared `outputs` = `pair` (object, `status`/`signal` inside)
- `SummaryDisplayNode` renders `{{ nodes.pairs.pair }}`

## Outputs

- `pair` — `{a, b, hedge_ratio, spread, spread_z, signal, status}`
- `signal` — `short_a_long_b` (z>entry_z) / `long_a_short_b` (z<-entry_z) / `flat`

## CodeNode contract

```python
async def execute(data, params, context):
    import statistics, math
    entry_z = float(params.get('entry_z', 2.0))
    rows = [r for r in (data or []) if isinstance(r, dict)]
    if len(rows) < 2:
        return {'pair': {'status': 'insufficient_symbols', 'signal': 'flat', 'spread_z': None}}
    a_row, b_row = rows[0], rows[1]

    def closes_of(row):
        ts = row.get('time_series') or []
        return [b.get('close') for b in ts
                if isinstance(b, dict) and b.get('close') is not None and b.get('close') > 0]

    ca = closes_of(a_row)
    cb = closes_of(b_row)
    base = {'a': a_row.get('symbol'), 'b': b_row.get('symbol')}
    n = min(len(ca), len(cb))
    if n < 3:
        return {'pair': {**base, 'status': 'insufficient_data', 'signal': 'flat', 'spread_z': None}}
    la = [math.log(x) for x in ca[-n:]]
    lb = [math.log(x) for x in cb[-n:]]
    try:
        beta = statistics.linear_regression(lb, la).slope
    except statistics.StatisticsError:
        beta = None
    if beta is None:
        return {'pair': {**base, 'status': 'degenerate', 'signal': 'flat', 'spread_z': None}}
    spread = [la[i] - beta * lb[i] for i in range(n)]
    mean_s = statistics.fmean(spread)
    sd_s = statistics.pstdev(spread)
    if sd_s == 0:
        return {'pair': {**base, 'hedge_ratio': round(beta, 3),
                         'status': 'degenerate', 'signal': 'flat', 'spread_z': None}}
    z = (spread[-1] - mean_s) / sd_s
    if z > entry_z:
        sig = 'short_a_long_b'
    elif z < -entry_z:
        sig = 'long_a_short_b'
    else:
        sig = 'flat'
    return {'pair': {**base, 'hedge_ratio': round(beta, 3),
                     'spread': round(spread[-1], 4), 'spread_z': round(z, 3),
                     'signal': sig, 'status': 'ok'}}
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
wf = json.load(open('examples/workflows/93-code-node-pairs-spread.json'))
async def main():
    exe = WorkflowExecutor()
    job = await exe.execute(wf, context_params={'dry_run': True, 'max_cycles': 1})
    if getattr(job, '_task', None):
        await asyncio.wait_for(job._task, timeout=60)
    print(job.context.get_all_outputs('pairs'))
asyncio.run(main())
"
```

> ⚠️ This targets a real overseas-stock account, but the workflow uses only the
> **fetch → compute → display** path — it places no orders and is safe to dry_run.

## Expected output

- **Real data:** `pair` such as `{a:'KO', b:'PEP', hedge_ratio:0.98, spread:0.012, spread_z:-0.98, signal:'flat', status:'ok'}`.
- **dry_run (mocked LS, empty bars):** `{pair: {status: 'insufficient_symbols', signal: 'flat', spread_z: null}}` (mocked LS returns no bars).

## Edge cases (no silent failure)

- A constant/degenerate series (`pstdev==0` or a failed regression) returns `status:'degenerate'`, `signal:'flat'`.
- Fewer than 3 aligned points returns `status:'insufficient_data'` with `signal:'flat'`.
