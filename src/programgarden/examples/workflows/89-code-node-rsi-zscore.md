# 89 · CodeNode RSI + Z-Score composite (NASDAQ)

Runs a **hand-rolled Wilder RSI combined with a rolling z-score** over a close series and tags each symbol with a composite signal (`oversold` / `overbought` / `neutral`). It is an **educational hand-roll reference** for the `RSI` and `ZScore` community plugins — the same math done in pure stdlib inside a `CodeNode`, not a new capability.

## Pipeline

```
StartNode → OverseasStockBrokerNode → OverseasStockHistoricalDataNode
          → CodeNode → TableDisplayNode
```

- `OverseasStockHistoricalDataNode` fetches 60 daily bars for 5 NASDAQ names → `values`
- `CodeNode` receives the whole array via `data = {{ nodes.historical.values }}` and loops in-code (not auto-iterated)
- `params = {period: 14, z_window: 20}`; declared `outputs` = `signals` / `oversold_count` / `skipped` / `status`
- `TableDisplayNode` renders `{{ nodes.rsizscore.signals }}` (signals sorted ascending by RSI)

## Outputs

- `signals` — `[{symbol, exchange, rsi, zscore, signal}]`, sorted ascending by `rsi`
- `oversold_count` — number of symbols flagged `oversold` (RSI<30 and z<-1)
- `skipped` — `[{symbol, exchange, reason}]` for symbols with fewer than `period+1` bars
- `status` — `ok` / `insufficient_data` / `no_data`

## CodeNode contract

```python
async def execute(data, params, context):
    import statistics
    period = int(params.get('period', 14))
    z_window = int(params.get('z_window', 20))
    rows = [r for r in (data or []) if isinstance(r, dict)]
    if not rows:
        return {'signals': [], 'oversold_count': 0, 'skipped': [], 'status': 'no_data'}
    signals = []
    skipped = []
    for row in rows:
        ts = row.get('time_series') or []
        closes = [b.get('close') for b in ts if isinstance(b, dict) and b.get('close') is not None]
        if len(closes) < period + 1:
            skipped.append({'symbol': row.get('symbol'), 'exchange': row.get('exchange'),
                            'reason': 'insufficient_bars'})
            continue
        gains = 0.0
        losses = 0.0
        for i in range(1, period + 1):
            diff = closes[i] - closes[i - 1]
            if diff >= 0:
                gains += diff
            else:
                losses -= diff
        avg_gain = gains / period
        avg_loss = losses / period
        for i in range(period + 1, len(closes)):
            diff = closes[i] - closes[i - 1]
            gain = diff if diff > 0 else 0.0
            loss = -diff if diff < 0 else 0.0
            avg_gain = (avg_gain * (period - 1) + gain) / period
            avg_loss = (avg_loss * (period - 1) + loss) / period
        if avg_loss == 0:
            rsi = 100.0
        else:
            rsi = 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
        window = closes[-z_window:] if len(closes) >= z_window else closes
        mean = statistics.fmean(window)
        sd = statistics.pstdev(window)
        zscore = (closes[-1] - mean) / sd if sd else 0.0
        if rsi < 30 and zscore < -1:
            sig = 'oversold'
        elif rsi > 70 and zscore > 1:
            sig = 'overbought'
        else:
            sig = 'neutral'
        signals.append({'symbol': row.get('symbol'), 'exchange': row.get('exchange'),
                        'rsi': round(rsi, 2), 'zscore': round(zscore, 2), 'signal': sig})
    signals.sort(key=lambda r: r['rsi'])
    oversold = sum(1 for s in signals if s['signal'] == 'oversold')
    return {'signals': signals, 'oversold_count': oversold, 'skipped': skipped,
            'status': 'ok' if signals else 'insufficient_data'}
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
wf = json.load(open('examples/workflows/89-code-node-rsi-zscore.json'))
async def main():
    exe = WorkflowExecutor()
    job = await exe.execute(wf, context_params={'dry_run': True, 'max_cycles': 1})
    if getattr(job, '_task', None):
        await asyncio.wait_for(job._task, timeout=60)
    print(job.context.get_all_outputs('rsizscore'))
asyncio.run(main())
"
```

> ⚠️ This targets a real overseas-stock account, but the workflow uses only the
> **fetch → compute → display** path — it places no orders and is safe to dry_run.

## Expected output

- **Real data:** `signals` is a ranked list such as `[{symbol:'AAPL', rsi:41.2, zscore:-0.8, signal:'neutral'}, ...]`; any symbol with <15 bars appears in `skipped` with `reason:'insufficient_bars'`.
- **dry_run (mocked LS, empty bars):** `{signals: [], oversold_count: 0, skipped: [], status: 'no_data'}` (mocked LS returns no bars).

## Edge cases (no silent failure)

- A symbol with fewer than `period+1` bars is emitted in `skipped` — never silently dropped.
- A flat window (`pstdev==0`) yields `zscore=0.0` rather than a division error.
