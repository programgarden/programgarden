"""A-6: per-connection real-time subscription cap.

LS allows up to 3 concurrent connections per account and limits the number of
real-time registrations per connection. ``RealRequestAbstract._add_message_symbols``
now enforces a configurable cap (default ``DEFAULT_MAX_SUBSCRIBE_SYMBOLS`` = 100,
summed across all TR codes on the connection) and raises
``SubscriptionLimitExceeded`` on overflow instead of silently flooding the socket.

These tests replicate the connected-websocket environment with mocks (holiday-safe,
no live API): ``_connected_event`` is set, ``_ws`` is a stub, and the per-symbol
``asyncio.create_task(...send())`` is patched away so the cap accounting is
exercised in isolation. The cap check runs *before* any send, so an over-cap
request rejects without mutating subscription state.
"""

from unittest.mock import MagicMock, patch

import pytest

from programgarden_finance.ls.real_base import (
    DEFAULT_MAX_SUBSCRIBE_SYMBOLS,
    SubscriptionLimitExceeded,
)
from programgarden_finance.ls.overseas_stock.real import Real as OverseasStockReal
from programgarden_finance.ls.korea_stock.real import Real as KoreaStockReal
from programgarden_finance.ls.overseas_futureoption.real import Real as FuturesReal


def _make_tm():
    tm = MagicMock()
    tm.access_token = "test-token"
    tm.appkey = "test-appkey"
    return tm


def _connected_real(real_cls=OverseasStockReal, max_subscribe_symbols=DEFAULT_MAX_SUBSCRIBE_SYMBOLS):
    """A real-time client wired to look connected, without a live websocket."""
    r = real_cls(token_manager=_make_tm(), max_subscribe_symbols=max_subscribe_symbols)
    r._connected_event.set()
    r._ws = MagicMock()  # non-None so the connection guard passes
    return r


def _subscribe(real, symbols, tr_cd):
    """Subscribe with the per-symbol websocket send stubbed out."""
    with patch("asyncio.create_task"):
        real._add_message_symbols(symbols, tr_cd)


def _syms(n, prefix="SYM"):
    return [f"{prefix}{i:04d}" for i in range(n)]


# ── default cap (100) ────────────────────────────────────────────────────────

def test_default_cap_is_100():
    assert DEFAULT_MAX_SUBSCRIBE_SYMBOLS == 100


def test_subscribe_up_to_cap_succeeds():
    real = _connected_real()
    _subscribe(real, _syms(100), "GSC")
    assert real.get_subscription_count() == 100
    assert real.get_subscription_capacity() == 0


def test_one_over_cap_raises_and_does_not_mutate():
    real = _connected_real()
    _subscribe(real, _syms(100), "GSC")
    with pytest.raises(SubscriptionLimitExceeded):
        _subscribe(real, ["EXTRA"], "GSC")
    # rejected request must not have been recorded
    assert real.get_subscription_count() == 100
    assert "EXTRA" not in real.get_subscribed_symbols().get("GSC", [])


def test_single_batch_over_cap_raises_before_any_record():
    real = _connected_real()
    with pytest.raises(SubscriptionLimitExceeded):
        _subscribe(real, _syms(101), "GSC")
    assert real.get_subscription_count() == 0


# ── dedup / resubscribe (reconnect path) ─────────────────────────────────────

def test_duplicate_symbols_not_double_counted():
    real = _connected_real()
    _subscribe(real, _syms(50), "GSC")
    # resubscribing the same symbols (e.g. reconnect auto-resubscribe) is a no-op
    _subscribe(real, _syms(50), "GSC")
    assert real.get_subscription_count() == 50
    assert real.get_subscription_capacity() == 50


def test_resubscribe_at_cap_is_allowed():
    """Reconnect resubscribe of already-tracked symbols must never trip the cap."""
    real = _connected_real()
    _subscribe(real, _syms(100), "GSC")
    # same 100 symbols again → 0 new unique → still within cap
    _subscribe(real, _syms(100), "GSC")
    assert real.get_subscription_count() == 100


def test_intra_batch_duplicates_collapse():
    real = _connected_real(max_subscribe_symbols=3)
    _subscribe(real, ["AAA", "AAA", "BBB"], "GSC")
    assert real.get_subscription_count() == 2


# ── cap spans all TR codes on the connection ─────────────────────────────────

def test_cap_is_summed_across_tr_codes():
    real = _connected_real()
    _subscribe(real, _syms(60, "G"), "GSC")
    _subscribe(real, _syms(40, "H"), "GSH")
    assert real.get_subscription_count() == 100
    with pytest.raises(SubscriptionLimitExceeded):
        _subscribe(real, ["ONE_MORE"], "GSC")


# ── configurability ──────────────────────────────────────────────────────────

def test_cap_is_configurable():
    real = _connected_real(max_subscribe_symbols=5)
    _subscribe(real, _syms(5), "GSC")
    assert real.get_subscription_capacity() == 0
    with pytest.raises(SubscriptionLimitExceeded):
        _subscribe(real, ["SIXTH"], "GSC")


def test_cap_disabled_when_non_positive():
    real = _connected_real(max_subscribe_symbols=0)
    _subscribe(real, _syms(250), "GSC")
    assert real.get_subscription_count() == 250
    assert real.get_subscription_capacity() is None


# ── subclass param threading (every product class) ───────────────────────────

@pytest.mark.parametrize(
    "real_cls,tr_cd",
    [
        (OverseasStockReal, "GSC"),
        (FuturesReal, "OVC"),
        (KoreaStockReal, "S3_"),
    ],
)
def test_cap_threaded_through_each_subclass(real_cls, tr_cd):
    real = _connected_real(real_cls=real_cls, max_subscribe_symbols=3)
    _subscribe(real, _syms(3), tr_cd)
    with pytest.raises(SubscriptionLimitExceeded):
        _subscribe(real, ["OVERFLOW"], tr_cd)


# ── error contract ───────────────────────────────────────────────────────────

def test_exception_subclasses_runtime_error():
    # existing real-time handling catches RuntimeError; the cap stays catchable there
    assert issubclass(SubscriptionLimitExceeded, RuntimeError)


def test_error_message_is_actionable():
    real = _connected_real(max_subscribe_symbols=2)
    with pytest.raises(SubscriptionLimitExceeded) as exc:
        _subscribe(real, _syms(3), "GSC")
    msg = str(exc.value)
    assert "2" in msg  # the cap value
    assert "max_subscribe_symbols" in msg  # the knob to adjust
