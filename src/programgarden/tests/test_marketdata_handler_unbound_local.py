"""MarketDataNode realtime fetchers — the per-symbol except handler must never touch an unassigned name.

Background (AI model benchmark 2026-09-06, D1 in the server repo's
``.claude/plans/2026-09-06-engine-defects-from-benchmark.md``): each realtime fetch loop
assigns ``exchange`` / ``symbol`` INSIDE ``try``. When a symbol entry was not a dict (a bare
``"AAPL"`` string, as several chat models emit) the first statement raised before either name
existed, the ``except`` then raised ``UnboundLocalError`` itself, and the outer handler reported
``Market data fetch error: cannot access local variable 'exchange' ...`` — masking the real cause
and killing the dry_run / save gate regardless of which model built the workflow.

The fix seeds handler-safe defaults at the top of every loop iteration; the handler names the raw
entry when ``symbol`` is still empty so the log shows what was actually wrong.
"""

import asyncio

import pytest

import programgarden.executor as ex_mod
from programgarden.executor import MarketDataNodeExecutor


class _Ctx:
    def __init__(self):
        self.logs: list[tuple[str, str]] = []

    def get_credential(self):
        return {"appkey": "k", "appsecret": "s", "paper_trading": False}

    def log(self, level, msg, node_id=None):
        self.logs.append((level, msg))


class _NoData:
    block = None
    block1 = None

    def req(self):
        return self


class _Market:
    def __getattr__(self, _tr):          # g3101 / o3105 / t1102 → "no data" response
        return lambda body=None, **kw: _NoData()


class _Api:
    def market(self):
        return _Market()


class _LS:
    def overseas_stock(self):
        return _Api()

    def overseas_futureoption(self):
        return _Api()

    def korea_stock(self):
        return _Api()


@pytest.fixture
def fake_login(monkeypatch):
    monkeypatch.setattr(ex_mod, "ensure_ls_login", lambda *a, **k: (_LS(), True, None))


BAD_ENTRIES = ["AAPL", {"symbol": ""}, {"exchange": "NASDAQ"}, {"symbol": "MSFT", "exchange": "NASDAQ"}]


@pytest.mark.parametrize("method", ["_fetch_overseas_stock", "_fetch_overseas_futures", "_fetch_korea_stock"])
def test_realtime_fetch_bad_symbol_entry_reports_real_cause(fake_login, method):
    ctx = _Ctx()
    ex = MarketDataNodeExecutor.__new__(MarketDataNodeExecutor)
    out = asyncio.run(getattr(ex, method)(BAD_ENTRIES, ctx, "md"))

    # No data for the valid entry, the bad ones skipped — but the node did NOT die.
    assert out["values"] == []
    assert not any(lvl == "error" for lvl, _ in ctx.logs), ctx.logs
    assert not any("cannot access local variable" in m for _, m in ctx.logs), ctx.logs

    # The real cause is named, together with the offending entry.
    warnings = [m for lvl, m in ctx.logs if lvl == "warning"]
    assert any("'AAPL'" in m and "'str' object has no attribute 'get'" in m for m in warnings), warnings
    # The valid dict entry reached the API and got the ordinary "No data" warning.
    assert any(m.startswith("No data for") and "MSFT" in m for m in warnings), warnings
