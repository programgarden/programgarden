#!/usr/bin/env python
"""Scan corpus workflow JSONs for realtime-market-node symbol/symbols usage.

req1: how many use `symbols` (plural, undeclared) config?
req4: of `symbol` (singular, declared) bindings, how many DON'T resolve to a
      valid {exchange, symbol} dict (string/scalar binding, or no ancestor
      account so the old fallback also produced nothing)?
"""
import json
import sys
from pathlib import Path

RT_MARKET = {
    "OverseasStockRealMarketDataNode",
    "KoreaStockRealMarketDataNode",
    "OverseasFuturesRealMarketDataNode",
}
ACCOUNT_TYPES = {
    "RealAccountNode", "OverseasStockRealAccountNode", "OverseasFuturesRealAccountNode",
    "AccountNode", "OverseasStockAccountNode", "OverseasFuturesAccountNode",
}

roots = [Path(p) for p in sys.argv[1:]] or [Path("src/programgarden/examples/workflows")]
files = []
for r in roots:
    files += sorted(r.rglob("*.json"))

symbols_plural = []   # (file, node_id)
symbol_ok_dict = []   # binds {{...item}} or literal dict  -> resolves to dict
symbol_str_bind = []  # binds {{...item.symbol}} or a bare string -> NOT a dict (would raise)
symbol_no_account = []  # symbol set but NO ancestor account in workflow (old fallback also empty)
symbol_total = []

def has_account(nodes):
    return any(n.get("type") in ACCOUNT_TYPES for n in nodes)

for f in files:
    try:
        wf = json.loads(f.read_text())
    except Exception:
        continue
    nodes = wf.get("nodes", [])
    if not isinstance(nodes, list):
        continue
    acct = has_account(nodes)
    for n in nodes:
        if not isinstance(n, dict) or n.get("type") not in RT_MARKET:
            continue
        nid = n.get("id")
        if "symbols" in n and n.get("symbols") not in (None, "", []):
            symbols_plural.append((f.name, nid, repr(n.get("symbols"))[:80]))
        if "symbol" in n and n.get("symbol") not in (None, "", {}):
            sym = n.get("symbol")
            symbol_total.append((f.name, nid))
            if isinstance(sym, dict):
                symbol_ok_dict.append((f.name, nid))
            elif isinstance(sym, str):
                s = sym.strip()
                if s.startswith("{{") and s.endswith("}}"):
                    inner = s[2:-2].strip()
                    # `.item` (whole dict) -> ok ; `.item.symbol` / `.symbol` (leaf) -> string
                    if inner.endswith(".item") or ".item}" in s or inner.split(".")[-1] == "item":
                        symbol_ok_dict.append((f.name, nid))
                    else:
                        symbol_str_bind.append((f.name, nid, inner))
                else:
                    symbol_str_bind.append((f.name, nid, s))
            else:
                symbol_str_bind.append((f.name, nid, repr(sym)))
            if not acct:
                symbol_no_account.append((f.name, nid))

print(f"scanned {len(files)} workflow JSONs under {', '.join(str(r) for r in roots)}\n")
print(f"[req1] realtime-market nodes using `symbols` (plural, undeclared): {len(symbols_plural)}")
for x in symbols_plural:
    print("       ", x)
print(f"\n[symbol] total realtime-market nodes setting `symbol`: {len(symbol_total)}")
print(f"   ok  (resolves to dict: {{{{...item}}}} or literal dict): {len(symbol_ok_dict)}")
print(f"   BAD (string/leaf binding -> NOT a dict -> would raise) : {len(symbol_str_bind)}")
for x in symbol_str_bind:
    print("       ", x)
print(f"\n[req4] `symbol` set but NO ancestor account node in workflow "
      f"(old fallback #4 also empty): {len(symbol_no_account)}")
for x in symbol_no_account:
    print("       ", x)
