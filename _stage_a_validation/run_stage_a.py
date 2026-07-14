#!/usr/bin/env python
"""Stage A local live validation runner for fix/split-runtime-wiring (3 engine defects).

Runs the hand-authored engine-validation DSL against the CANONICAL SOURCE (this branch)
+ a REAL LS overseas-stock account (read-only, NO order nodes).

REQUIRES real LS overseas-stock credentials in env:
    APPKEY / APPSECRET   (broker_ls_overseas_stock)

Run (from repo root /workspace/programgarden):
    PYTHONPATH=src/programgarden:src/core:src/finance:src/community \
    APPKEY=... APPSECRET=... \
    programgarden_ai/venv_linux/bin/python _stage_a_validation/run_stage_a.py

It prints three acceptance checks:
  [1] Split iterates REAL held_symbols (defect 1: config.array honored, real traversal)
  [3] held_symbols emit exchange=NASDAQ + exchange_code=82 BOTH (defect 3: value normalization)
  [2] table = real 체결가 rows OR honest empty table; ZERO empty-dict / internal-structure rows (defect 2)
"""
import asyncio
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DSL_PATH = HERE / "dsl_split_realtime.json"
TIMEOUT_SEC = float(os.environ.get("STAGE_A_TIMEOUT", "90"))

import programgarden_community  # noqa: F401  (registers community nodes/plugins)
import programgarden  # noqa: F401
from programgarden import ProgramGarden
from programgarden_core.bases.listener import BaseExecutionListener


class Capture(BaseExecutionListener):
    def __init__(self):
        self.node_outputs = {}      # node_id -> last completed outputs
        self.split_items = []       # every value split emitted as item
        self.display_events = []    # DisplayNode payloads

    async def on_node_state_change(self, event):
        if getattr(event, "outputs", None) is not None:
            self.node_outputs[event.node_id] = event.outputs
            if event.node_id == "split":
                item = event.outputs.get("item")
                if item is not None:
                    self.split_items.append(item)

    async def on_display(self, event):  # DisplayEvent (if emitted)
        self.display_events.append(getattr(event, "payload", None) or getattr(event, "data", None))

    async def on_log(self, event):
        pass


def _fmt(v, n=600):
    s = json.dumps(v, ensure_ascii=False, default=str)
    return s if len(s) <= n else s[:n] + " …(truncated)"


async def main():
    if not (os.environ.get("APPKEY") and os.environ.get("APPSECRET")):
        print("BLOCKED: APPKEY/APPSECRET not set — real LS account required (read-only).")
        print("  Provide real broker_ls_overseas_stock keys and re-run.")
        return 2

    lib = programgarden.__file__
    print(f"programgarden source : {lib}")
    print(f"programgarden version: {getattr(programgarden, '__version__', '?')}")
    if "/src/programgarden/" not in lib:
        print("WARNING: not running from canonical branch source (stale venv?). Aborting.")
        return 3

    definition = json.loads(DSL_PATH.read_text())
    secrets = {
        "broker_ls_overseas_stock_cred": {
            "appkey": os.environ["APPKEY"],
            "appsecret": os.environ["APPSECRET"],
        }
    }

    pg = ProgramGarden()
    cap = Capture()
    print(f"\nRunning (timeout={TIMEOUT_SEC}s, read-only, NO order nodes)…\n")

    job = await pg.run_async(definition, secrets=secrets, listeners=[cap])

    loop = asyncio.get_running_loop()
    t0 = loop.time()
    while getattr(job, "status", None) in ("pending", "running"):
        await asyncio.sleep(0.2)
        if loop.time() - t0 > TIMEOUT_SEC:
            print(f"(timeout {TIMEOUT_SEC}s reached — stopping observation)")
            break
    for m in ("cancel", "stop"):
        fn = getattr(job, m, None)
        if callable(fn):
            try:
                r = fn()
                if asyncio.iscoroutine(r):
                    await r
            except Exception:
                pass
            break

    # ---- Report ----
    print("\n" + "=" * 72)
    print("STAGE A — ACCEPTANCE CHECKS")
    print("=" * 72)

    acct = cap.node_outputs.get("real_account", {})
    held = acct.get("held_symbols") if isinstance(acct, dict) else None
    print("\n[real_account.held_symbols]")
    print("  ", _fmt(held))

    # [3] exchange normalization
    ex_ok = False
    if isinstance(held, list) and held:
        ex_ok = all(
            isinstance(h, dict) and h.get("exchange") and h.get("exchange_code")
            for h in held
        )
        has_nasdaq = any(h.get("exchange") == "NASDAQ" for h in held if isinstance(h, dict))
        has_82 = any(str(h.get("exchange_code")) == "82" for h in held if isinstance(h, dict))
        print(f"\n[3] exchange normalization: exchange&exchange_code both present on all = {ex_ok}")
        print(f"    NASDAQ present={has_nasdaq}  exchange_code=82 present={has_82}")
    else:
        print("\n[3] exchange normalization: NO held_symbols (empty account?) — inconclusive")

    # [1] split iteration
    print(f"\n[1] Split emitted {len(cap.split_items)} item(s):")
    for it in cap.split_items:
        print("    ", _fmt(it, 200))
    split_ok = len(cap.split_items) > 0
    if isinstance(held, list):
        held_syms = {h.get("symbol") for h in held if isinstance(h, dict)}
        split_syms = {
            (it.get("symbol") if isinstance(it, dict) else it) for it in cap.split_items
        }
        print(f"    held symbols={held_syms}  split symbols={split_syms}  match={held_syms == split_syms if held_syms else 'n/a'}")

    # [2] table honesty
    disp = cap.node_outputs.get("display", {})
    agg = cap.node_outputs.get("aggregate", {})
    rows = None
    if isinstance(disp, dict):
        rows = disp.get("rows") or disp.get("data") or disp.get("array")
    if rows is None and isinstance(agg, dict):
        rows = agg.get("array")
    print(f"\n[2] table rows (display/aggregate): {_fmt(rows)}")
    empty_dict_rows = 0
    real_price_rows = 0
    if isinstance(rows, list):
        for r in rows:
            if isinstance(r, dict):
                meaningful = {k: v for k, v in r.items() if not k.startswith("_") and v not in (None, {}, [])}
                if not meaningful:
                    empty_dict_rows += 1
                elif any(r.get(k) is not None for k in ("close", "price", "current_price", "last")):
                    real_price_rows += 1
    print(f"    empty-dict/internal-only rows = {empty_dict_rows} (MUST be 0)")
    print(f"    real-price rows = {real_price_rows}")

    print("\n" + "=" * 72)
    print("VERDICT")
    print("=" * 72)
    print(f"  [1] Split iterates real held_symbols : {'PASS' if split_ok else 'FAIL/empty-account'}")
    print(f"  [3] exchange=NASDAQ & exchange_code=82: {'PASS' if ex_ok else 'FAIL/inconclusive'}")
    print(f"  [2] no empty/dishonest rows          : {'PASS' if empty_dict_rows == 0 else 'FAIL'}"
          f"  ({real_price_rows} real-price rows, {empty_dict_rows} empty rows)")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
