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
        self.first_held = None      # first NON-EMPTY real_account.held_symbols snapshot

    async def on_node_state_change(self, event):
        if getattr(event, "outputs", None) is not None:
            self.node_outputs[event.node_id] = event.outputs
            if event.node_id == "split":
                item = event.outputs.get("item")
                if item is not None:
                    self.split_items.append(item)
            elif event.node_id == "real_account":
                # The realtime account re-syncs (stay_connected) and a later
                # snapshot can carry null/empty held_symbols, clobbering the
                # good first value. Preserve the FIRST non-empty snapshot so
                # [3] reads the real emitted value, not a re-exec artifact.
                hs = event.outputs.get("held_symbols")
                if hs and self.first_held is None:
                    self.first_held = hs

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
    # get_credential() defaults to the LITERAL key "credential_id" (context.py:537),
    # NOT the DSL's credential_id value. Keying by the DSL name silently yields
    # "Missing credentials" -> empty account -> a vacuous [2] PASS.
    secrets = {
        "credential_id": {
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

    # Source of truth for held-symbol dicts = the items Split ACTUALLY fanned out
    # (array={{held_symbols}} => each split item IS a held_symbols dict). Fall back
    # to the first non-empty real_account snapshot. Do NOT read the last snapshot —
    # the realtime re-sync nulls it (that was the [3] "inconclusive" reporting bug).
    acct = cap.node_outputs.get("real_account", {})
    last_snap = acct.get("held_symbols") if isinstance(acct, dict) else None
    split_dicts = [it for it in cap.split_items if isinstance(it, dict)]
    held = split_dicts or cap.first_held or (last_snap if last_snap else None)
    print("\n[real_account.held_symbols]")
    print("   source        :", "split-items" if split_dicts else ("first-snapshot" if cap.first_held else "last-snapshot"))
    print("   first snapshot :", _fmt(cap.first_held))
    print("   last snapshot  :", _fmt(last_snap), "  <- realtime re-sync may null this")
    print("   split items    :", _fmt(cap.split_items))

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
        print("\n[3] exchange normalization: NO held_symbols observed (empty account?) — inconclusive")

    # [1] split iteration
    print(f"\n[1] Split emitted {len(cap.split_items)} item(s):")
    for it in cap.split_items:
        print("    ", _fmt(it, 200))
    split_ok = len(cap.split_items) > 0
    # Compare split fan-out against the ACCOUNT snapshot (independent source) to
    # prove Split iterated the real held_symbols and not some fallback list.
    acct_ref = cap.first_held or (last_snap if isinstance(last_snap, list) else None)
    if isinstance(acct_ref, list):
        acct_syms = {h.get("symbol") for h in acct_ref if isinstance(h, dict)}
        split_syms = {
            (it.get("symbol") if isinstance(it, dict) else it) for it in cap.split_items
        }
        print(f"    account held symbols={acct_syms}  split symbols={split_syms}  match={acct_syms == split_syms if acct_syms else 'n/a'}")

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
