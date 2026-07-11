# 91 · CodeNode Kelly-fraction sizing (NASDAQ)

Computes a **capped Kelly fraction** from each symbol's historical win-rate and payoff ratio. It is an **educational hand-roll reference** for the `KellyCriterion` community plugin (no `PositionSizingNode` is wired, unlike example 88) — pure stdlib inside a `CodeNode`.

## Pipeline

```
StartNode → OverseasStockBrokerNode → OverseasStockHistoricalDataNode
          → CodeNode → TableDisplayNode
```

- `OverseasStockHistoricalDataNode` fetches 60 daily bars for 3 NASDAQ names → `values`
- `CodeNode` derives win-rate `p` and payoff, then `f* = p - (1-p)/payoff`, capped to `cap`
- `params = {cap: 0.10}`; declared `outputs` = `kelly` / `status`
- `TableDisplayNode` renders `{{ nodes.kelly.kelly }}` (sorted by capped fraction, descending)

## Outputs

- `kelly` — `[{symbol, exchange, win_rate, payoff, kelly_fraction, capped_fraction}]`
- `status` — `ok` / `insufficient_data` / `no_data`

## CodeNode contract

```python
async def execute(data, params, context):
    import statistics
    cap = float(params.get('cap', 0.10))
    rows = [r for r in (data or []) if isinstance(r, dict)]
    if not rows:
        return {'kelly': [], 'status': 'no_data'}
    out = []
    for row in rows:
        ts = row.get('time_series') or []
        closes = [b.get('close') for b in ts if isinstance(b, dict) and b.get('close') is not None]
        entry = {'symbol': row.get('symbol'), 'exchange': row.get('exchange'),
                 'win_rate': None, 'payoff': None, 'kelly_fraction': None, 'capped_fraction': 0.0}
        if len(closes) < 3:
            out.append(entry)
            continue
        rets = [closes[i] / closes[i - 1] - 1.0 for i in range(1, len(closes)) if closes[i - 1]]
        wins = [r for r in rets if r > 0]
        losses = [r for r in rets if r < 0]
        if not rets or not wins or not losses:
            out.append(entry)
            continue
        p = len(wins) / len(rets)
        avg_win = statistics.fmean(wins)
        avg_loss = abs(statistics.fmean(losses))
        if avg_loss == 0:
            out.append(entry)
            continue
        payoff = avg_win / avg_loss
        kelly = p - (1.0 - p) / payoff if payoff else None
        capped = max(0.0, min(kelly, cap)) if kelly is not None else 0.0
        out.append({'symbol': row.get('symbol'), 'exchange': row.get('exchange'),
                    'win_rate': round(p, 3), 'payoff': round(payoff, 3),
                    'kelly_fraction': round(kelly, 4) if kelly is not None else None,
                    'capped_fraction': round(capped, 4)})
    out.sort(key=lambda r: -(r['capped_fraction'] or 0.0))
    return {'kelly': out, 'status': 'ok' if out else 'insufficient_data'}
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
wf = json.load(open('examples/workflows/91-code-node-kelly.json'))
async def main():
    exe = WorkflowExecutor()
    job = await exe.execute(wf, context_params={'dry_run': True, 'max_cycles': 1})
    if getattr(job, '_task', None):
        await asyncio.wait_for(job._task, timeout=60)
    print(job.context.get_all_outputs('kelly'))
asyncio.run(main())
"
```

> ⚠️ This targets a real overseas-stock account, but the workflow uses only the
> **fetch → compute → display** path — it places no orders and is safe to dry_run.

## Expected output

- **Real data:** `kelly` such as `[{symbol:'NVDA', win_rate:0.55, payoff:1.3, kelly_fraction:0.19, capped_fraction:0.10}, ...]`.
- **dry_run (mocked LS, empty bars):** `{kelly: [], status: 'no_data'}` (mocked LS returns no bars).

## Edge cases (no silent failure)

- A symbol lacking BOTH winning and losing returns gets a **None-filled** entry (`kelly_fraction:null, capped_fraction:0.0`) — never silently dropped.
- `capped_fraction` is clamped to `[0, cap]`; a negative raw Kelly clamps to `0.0`.
