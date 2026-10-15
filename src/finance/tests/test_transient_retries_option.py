"""``SetupOptions.transient_retries`` (SPEC K8), offline.

``None`` keeps the 0.5/1.5/3.0 s ladder. ``0`` disables spaced retries and the
reissue that otherwise follows an exhausted ladder, so callers that pace
requests themselves never trigger a competing token. Order endpoints still
never retry transient failures.
"""

import time
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from programgarden_finance.ls import tr_helpers as trh
from programgarden_finance.ls.models import SetupOptions
from programgarden_finance.ls.token_manager import TokenManager


class _Resp:
    def __init__(self, status):
        self.status = status
        self.status_code = status


def _token_manager():
    issued = []

    def provider(*, force_reissue: bool = False, stale_token=None):
        issued.append(force_reissue)
        return ("FRESH", time.time() + 3600)

    tm = TokenManager()
    tm.token_provider = provider
    tm.apply_token("CURRENT", time.time() + 3600)
    return tm, issued


def _generic(url, retries, token_manager=None):
    options = SetupOptions(rate_limit_count=100, rate_limit_seconds=1, on_rate_limit="wait",
                           rate_limit_key="", transient_retries=retries)
    options.token_manager = token_manager
    request_data = SimpleNamespace(options=options, header=SimpleNamespace(authorization="Bearer CURRENT"))
    return trh.GenericTR(request_data, lambda resp, rj, rh, exc: (resp, rj, rh, exc), url=url)


def _always(status, calls):
    def fake_execute(url, request_data, timeout=10):
        calls.append(request_data.header.authorization)
        return _Resp(status), {"rsp_cd": "IGW00201", "rsp_msg": "호출 거래건수를 초과하였습니다."}, {}
    return fake_execute


def test_option_bounds_follow_the_default_ladder():
    assert SetupOptions().transient_retries is None
    assert SetupOptions(transient_retries=len(trh.TRANSIENT_RETRY_DELAYS)).transient_retries == 3
    for bad in (-1, len(trh.TRANSIENT_RETRY_DELAYS) + 1):
        with pytest.raises(ValidationError):
            SetupOptions(transient_retries=bad)
    assert trh.transient_retry_delays(None) == (0.5, 1.5, 3.0)
    assert trh.transient_retry_delays(0) == ()
    assert trh.transient_retry_delays(1) == (0.5,)
    with pytest.raises(ValueError):
        trh.transient_retry_delays(True)


def test_zero_retries_sends_once_and_never_reissues(monkeypatch):
    monkeypatch.setattr(trh.time, "sleep", lambda _s: pytest.fail("slept although retries are off"))
    tm, issued = _token_manager()
    gtr = _generic("https://x/overseas-futureoption/accno", 0, tm)
    calls = []
    monkeypatch.setattr(gtr, "execute_sync", _always(500, calls))
    resp, _rj, _rh = gtr._execute_sync_with_retry()
    assert resp.status == 500
    assert calls == ["Bearer CURRENT"]
    assert issued == [] and tm.access_token == "CURRENT"


@pytest.mark.asyncio
async def test_zero_retries_async_sends_once_and_never_reissues(monkeypatch):
    async def no_sleep(_s):
        pytest.fail("slept although retries are off")

    monkeypatch.setattr(trh.asyncio, "sleep", no_sleep)
    tm, issued = _token_manager()
    gtr = _generic("https://x/overseas-futureoption/accno", 0, tm)
    calls = []

    async def fake_execute(session, url, request_data, timeout=10):
        calls.append(request_data.header.authorization)
        return _Resp(500), {"rsp_cd": "IGW00201"}, {}

    monkeypatch.setattr(gtr, "execute_async_with_session", fake_execute)
    resp, _rj, _rh = await gtr._execute_async_with_retry(session=None)
    assert resp.status == 500 and len(calls) == 1 and issued == []


def test_one_retry_uses_the_first_delay_then_keeps_the_reissue_rule(monkeypatch):
    slept = []
    monkeypatch.setattr(trh.time, "sleep", lambda s: slept.append(s))
    tm, issued = _token_manager()
    gtr = _generic("https://x/overseas-futureoption/accno", 1, tm)
    calls = []
    monkeypatch.setattr(gtr, "execute_sync", _always(500, calls))
    gtr._execute_sync_with_retry()
    # One ladder step only (later sleeps, if any, belong to the token manager's reissue pacing).
    assert slept[0] == 0.5 and 1.5 not in slept and 3.0 not in slept
    # After a ladder actually ran, the existing last-resort reissue still applies.
    assert issued and issued[0] is True
    assert calls[0] == "Bearer CURRENT" and calls[-1] == "Bearer FRESH"


def test_default_keeps_the_full_ladder(monkeypatch):
    slept = []
    monkeypatch.setattr(trh.time, "sleep", lambda s: slept.append(s))
    gtr = _generic("https://x/overseas-stock/market-data", None)
    calls = []
    monkeypatch.setattr(gtr, "execute_sync", _always(503, calls))
    gtr._execute_sync_with_retry()
    assert slept == [0.5, 1.5, 3.0] and len(calls) == 4


def test_order_endpoint_ignores_the_option(monkeypatch):
    monkeypatch.setattr(trh.time, "sleep", lambda _s: pytest.fail("order path waited"))
    gtr = _generic("https://x/overseas-stock/order", 3)
    calls = []
    monkeypatch.setattr(gtr, "execute_sync", _always(500, calls))
    resp, _rj, _rh = gtr._execute_sync_with_retry()
    assert resp.status == 500 and len(calls) == 1
