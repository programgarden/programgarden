"""High-fidelity offline sim for example 13 (RSI AND MACD via LogicNode).

dry_run mock returns empty time_series, which hides binding bugs in the
ConditionNode -> LogicNode hop. So we run the REAL node executors + REAL
plugins (RSI / MACD) over SYNTHETIC OHLCV, patching only the historical
fetch. Weekend-safe (no live API, no orders).

Goal:
  1. Confirm synthetic candles flow historical -> rsi/macd -> logic.
  2. Confirm LogicNode(all) == intersection(rsi.passed, macd.passed).
  3. Contrast fixed bindings vs the old buggy bindings.
"""
import asyncio
import copy
import json
import math
from pathlib import Path
from unittest.mock import MagicMock, patch

from programgarden import WorkflowExecutor
from programgarden_core.bases import BaseExecutionListener
from programgarden.executor import HistoricalDataNodeExecutor

WF = Path(__file__).resolve().parents[1] / "workflows" / "13-logic-complex.json"


def _candles(n, shape):
    """Deterministic OHLCV. `shape(i)` -> close price."""
    out = []
    for i in range(n):
        close = round(shape(i), 2)
        op = round(shape(i - 1) if i else shape(i), 2)
        hi = max(op, close) + 0.5
        lo = min(op, close) - 0.5
        # date ascending YYYYMMDD-ish (synthetic, plugin only needs order)
        out.append({
            "date": f"202603{(i % 28) + 1:02d}",
            "open": op, "high": round(hi, 2), "low": round(lo, 2),
            "close": close, "volume": 1000 + i,
        })
    return out


N = 60
# Distinct shapes so RSI(<30) and MACD(golden_cross) land on different subsets.
SHAPES = {
    "AAPL": lambda i: 100 - i * 0.9,                       # steady decline -> RSI oversold
    "TSLA": lambda i: 100 - max(0, 40 - i) * 1.2,          # decline then flat-up tail -> MACD cross
    "NVDA": lambda i: 100 - i * 0.8 + (i > 50) * (i - 50) * 4,  # deep dip + sharp recovery tail
    "MSFT": lambda i: 50 + i * 0.9,                        # steady uptrend -> high RSI
    "JPM":  lambda i: 80 + 10 * math.sin(i / 6.0),         # oscillating -> recent cross maybe
}
SYNTH = {sym: _candles(N, shp) for sym, shp in SHAPES.items()}


async def _fake_fetch(self, symbols, start_date, end_date, interval, context,
                      node_id, positions=None, symbol_exchange_map=None, symbols_raw=None):
    ex_map = {}
    for entry in (symbols_raw or []):
        if isinstance(entry, dict):
            ex_map[entry.get("symbol")] = entry.get("exchange", "NASDAQ")
    out = []
    for sym in symbols:
        out.append({
            "symbol": sym,
            "exchange": ex_map.get(sym, "NASDAQ"),
            "time_series": SYNTH.get(sym, []),
        })
    return out


class Listener(BaseExecutionListener):
    def __init__(self):
        self.warns = []

    async def on_log(self, event):
        msg = getattr(event, "message", "") or str(event)
        lvl = getattr(event, "level", "")
        if "is_condition_met" in msg and ("missing" in msg.lower()):
            self.warns.append(msg)


def _as_symbols(val):
    """Normalize passed_symbols (list of dicts or strings) -> set of symbol str."""
    out = set()
    if isinstance(val, list):
        for v in val:
            if isinstance(v, dict):
                out.add(v.get("symbol"))
            elif isinstance(v, str):
                out.add(v)
    return out


async def run(workflow, tag):
    ls = Listener()
    ex = WorkflowExecutor()
    with patch.object(HistoricalDataNodeExecutor, "_fetch_overseas_stock", _fake_fetch), \
         patch("programgarden.executor.ensure_ls_login") as login:
        login.return_value = (MagicMock(), True, None)
        job = await ex.execute(
            workflow,
            context_params={"dry_run": False, "max_cycles": 1},
            listeners=[ls],
        )
        try:
            await asyncio.wait_for(job._task, timeout=40)
        except asyncio.TimeoutError:
            await job.stop()

    ctx = job.context
    def outs(nid):
        return ctx.get_all_outputs(nid) if hasattr(ctx, "get_all_outputs") else {}

    rsi = outs("rsi_condition")
    macd = outs("macd_condition")
    logic = outs("logic")

    rsi_pass = _as_symbols(rsi.get("passed_symbols"))
    macd_pass = _as_symbols(macd.get("passed_symbols"))
    logic_pass = _as_symbols(logic.get("passed_symbols"))
    expect = rsi_pass & macd_pass

    print(f"\n========== {tag} ==========")
    print(f"  status            : {job.get_state().get('status')}")
    print(f"  RAW rsi.result    : {rsi.get('result')!r}")
    print(f"  RAW rsi.passed    : {rsi.get('passed_symbols')!r}")
    print(f"  RAW macd.passed   : {macd.get('passed_symbols')!r}")
    print(f"  RAW logic.details : {logic.get('details')!r}")
    print(f"  rsi.result        : {rsi.get('result')}  passed={sorted(rsi_pass)}")
    print(f"  macd.result       : {macd.get('result')}  passed={sorted(macd_pass)}")
    print(f"  logic.result      : {logic.get('result')}")
    print(f"  logic.passed      : {sorted(logic_pass)}")
    print(f"  expected (AND ∩)  : {sorted(expect)}")
    print(f"  missing-warns     : {len(ls.warns)}")
    ok = (logic_pass == expect) and (len(ls.warns) == 0)
    print(f"  → {'✅ intersection correct, no warns' if ok else '⚠️ MISMATCH'}")
    return ok, rsi_pass, macd_pass, logic_pass, len(ls.warns)


async def main():
    fixed = json.loads(WF.read_text())

    # Reconstruct the OLD buggy bindings to contrast.
    buggy = copy.deepcopy(fixed)
    for n in buggy["nodes"]:
        if n.get("type") == "LogicNode":
            for c in n["conditions"]:
                # old pattern: result.passed (None) + result (bool) as passed_symbols
                src = c["passed_symbols"].split(".passed_symbols")[0]  # {{ nodes.x
                c["is_condition_met"] = src + ".result.passed }}"
                c["passed_symbols"] = src + ".result }}"

    print("Synthetic candles:", {k: len(v) for k, v in SYNTH.items()})
    ok_fixed, r, m, lg, w = await run(fixed, "FIXED bindings (current 13)")
    ok_buggy, *_ , lgb, wb = await run(buggy, "BUGGY bindings (pre-fix, reconstructed)")

    print("\n========== VERDICT ==========")
    print(f"  FIXED: logic.passed={sorted(lg)} warns={w}  -> {'PASS' if ok_fixed else 'FAIL'}")
    print(f"  BUGGY: logic.passed={sorted(lgb)} warns={wb}  (demonstrates the silent break)")
    return 0 if ok_fixed else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
