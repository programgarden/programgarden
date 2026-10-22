"""Fill-subscription LS connection/listener leak fix (2026-10-21).

Prod (user 2fe9a961, overseas_stock cloud pod, worker v1.26.52 = engine 2.7.2):
"Workflow fill recorded" was logged 3× per fill at first and 35× a day later while
``order_fills`` stayed 1 row/fill and pod RSS crept 552→567 MiB. Cause:
  - ``LSClientManager.get_or_create`` replaced a not-logged-in LS with a brand new
    instance WITHOUT closing the old one, so the stale websocket stayed alive with
    its order listeners; and
  - the BrokerNode re-subscribed AS0/AS1 fill events every cycle, and the broker SDK
    APPENDS a listener per ``on_asX_message`` call (each cycle builds a new closure),
    so listeners/connections accumulated and every fill was processed N times.

Fix pinned here:
  - get_or_create re-logs in place (reuse the same LS + its websocket) when the
    token lapsed, and closes the old LS before replacing it on a genuine swap;
  - ``_fill_subscription_already_active`` skips re-registering when a fill
    subscription is already active on the same LS, and detaches the stale real's
    order callbacks on a swap.

Run: cd src/programgarden && poetry run pytest tests/test_fill_subscription_leak.py -v
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import programgarden.executor as ex
from programgarden.executor import LSClientManager, BrokerNodeExecutor


class _StubReal:
    """Minimal stand-in for a finance real-time client with removable callbacks."""

    def __init__(self):
        self.removed = []

    def AS0(self):
        return SimpleNamespace(on_remove_as0_message=lambda: self.removed.append("AS0"))

    def AS1(self):
        return SimpleNamespace(on_remove_as1_message=lambda: self.removed.append("AS1"))


class _StubLS:
    """LS stand-in: controllable login state, records close()."""

    def __init__(self):
        self._logged_in = False
        self._login_makes_logged_in = True  # new instances log in successfully
        self.login_calls = 0
        self.closed = False

    def set_token_provider(self, **kwargs):
        return True

    def is_logged_in(self):
        return self._logged_in

    def login(self, **kwargs):
        self.login_calls += 1
        self._logged_in = self._login_makes_logged_in
        return self._logged_in

    async def close(self):
        self.closed = True


def _ctx():
    ctx = MagicMock()
    ctx.log = MagicMock()
    return ctx


@pytest.fixture(autouse=True)
def _reset_manager():
    LSClientManager.reset()
    yield
    LSClientManager.reset()


# --------------------------------------------------------------------------- #
# get_or_create: reuse on reconnect, close-before-replace                      #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_get_or_create_closes_old_before_replacing(monkeypatch):
    """Not-logged-in LS whose re-login does NOT restore → old closed, one live."""
    old = _StubLS()
    old._logged_in = False
    old._login_makes_logged_in = False  # re-login fails to restore → must replace
    LSClientManager._instances["overseas_stock"] = old
    LSClientManager._credentials["overseas_stock"] = ("ak", "sk", False)

    monkeypatch.setattr(ex, "attach_context_token_provider", lambda *a, **k: True)
    with patch("programgarden_finance.LS", _StubLS):
        ls, ok, err = LSClientManager.get_or_create(
            "overseas_stock", "ak", "sk", False, _ctx(), "n1"
        )
    await asyncio.sleep(0)  # let the scheduled close() task run

    assert ok is True and err is None
    assert ls is not old, "a replaced LS must be a fresh instance"
    assert old.closed is True, "the stale LS must be closed before replacement"
    assert LSClientManager._instances["overseas_stock"] is ls
    assert old.login_calls == 1  # re-login attempted in place first


@pytest.mark.asyncio
async def test_get_or_create_reuses_same_ls_on_reconnect(monkeypatch):
    """Not-logged-in LS whose re-login restores → SAME instance reused, not closed."""
    old = _StubLS()
    old._logged_in = False
    old._login_makes_logged_in = True  # re-login in place restores the session
    LSClientManager._instances["overseas_stock"] = old
    LSClientManager._credentials["overseas_stock"] = ("ak", "sk", False)

    monkeypatch.setattr(ex, "attach_context_token_provider", lambda *a, **k: True)
    with patch("programgarden_finance.LS", _StubLS):
        ls, ok, err = LSClientManager.get_or_create(
            "overseas_stock", "ak", "sk", False, _ctx(), "n1"
        )
    await asyncio.sleep(0)

    assert ok is True
    assert ls is old, "a recoverable session must reuse the same LS (no new websocket)"
    assert old.closed is False
    assert old.login_calls == 1


@pytest.mark.asyncio
async def test_get_or_create_returns_logged_in_without_relogin():
    """Already logged in → returned as-is, no re-login, no close."""
    live = _StubLS()
    live._logged_in = True
    LSClientManager._instances["overseas_stock"] = live
    LSClientManager._credentials["overseas_stock"] = ("ak", "sk", False)

    ls, ok, err = LSClientManager.get_or_create(
        "overseas_stock", "ak", "sk", False, _ctx(), "n1"
    )
    assert ls is live and ok is True
    assert live.login_calls == 0 and live.closed is False


# --------------------------------------------------------------------------- #
# re-subscribe guard                                                          #
# --------------------------------------------------------------------------- #


def test_fill_subscription_skips_when_active_on_same_ls():
    ls = _StubLS()
    real = _StubReal()
    holder = SimpleNamespace(
        _active_trackers={"j_n1_fill_sub": {"ls": ls, "real": real, "type": "fill_subscription"}}
    )
    skip = BrokerNodeExecutor._fill_subscription_already_active(holder, "j_n1_fill_sub", ls)
    assert skip is True
    assert real.removed == []  # same LS → nothing detached


def test_fill_subscription_detaches_stale_callbacks_on_swap():
    old_ls, new_ls = _StubLS(), _StubLS()
    real = _StubReal()
    holder = SimpleNamespace(
        _active_trackers={"j_n1_fill_sub": {"ls": old_ls, "real": real, "type": "fill_subscription"}}
    )
    skip = BrokerNodeExecutor._fill_subscription_already_active(holder, "j_n1_fill_sub", new_ls)
    assert skip is False  # different LS → caller re-registers on the new connection
    assert "AS1" in real.removed and "AS0" in real.removed  # stale listeners detached


def test_fill_subscription_no_prior_is_not_skipped():
    holder = SimpleNamespace(_active_trackers={})
    skip = BrokerNodeExecutor._fill_subscription_already_active(holder, "j_n1_fill_sub", _StubLS())
    assert skip is False
