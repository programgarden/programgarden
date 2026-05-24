"""A-1: LS rate limit is account-cumulative, but the client keys buckets per-TR.

Account owner confirmed (2026-05-24): LS enforces ONE cumulative request budget
per account ("API 요청 수 제한은 API마다가 아니라 계정으로 누적 통합"), not a
separate budget per TR code. The client (``TRRequestAbstract``) keys its
sliding-window bucket by ``rate_limit_key`` (= the TR code), so requests to
different TRs use independent buckets and never coordinate at the account level.

This module first *reproduces* the bug (two TRs collectively exceed the account
budget) and then *verifies* the fix (an opt-in shared account gate throttles the
cumulative stream regardless of which TR issued it).
"""

import time

import pytest

from programgarden_finance.ls.tr_base import TRRequestAbstract, _ACCOUNT_RATE_REGISTRY


class _FakeTR(TRRequestAbstract):
    """Minimal concrete TR that only exercises the rate-limit gate."""

    async def req_async(self, **kwargs):  # pragma: no cover - unused
        return None

    def req(self, **kwargs):  # pragma: no cover - unused
        return None


@pytest.fixture(autouse=True)
def _clear_shared_buckets():
    """Buckets live in class-level registries; isolate every test."""
    TRRequestAbstract._shared_rate_data.clear()
    _ACCOUNT_RATE_REGISTRY.clear()
    yield
    TRRequestAbstract._shared_rate_data.clear()
    _ACCOUNT_RATE_REGISTRY.clear()


# Account-cumulative budget used by every scenario below: 5 requests / 1 second.
ACCOUNT_LIMIT = 5


@pytest.mark.asyncio
async def test_per_tr_keys_exceed_account_cumulative_limit():
    """BUG (A-1): per-TR buckets let two TRs push 2x the account budget.

    This is the exact gate ``execute_async_with_session`` calls before every
    POST (tr_base.py:134), so the unit-level assertion mirrors real traffic.
    """
    tr_a = _FakeTR(rate_limit_count=ACCOUNT_LIMIT, rate_limit_seconds=1,
                   on_rate_limit="wait", rate_limit_key="g3101")
    tr_b = _FakeTR(rate_limit_count=ACCOUNT_LIMIT, rate_limit_seconds=1,
                   on_rate_limit="wait", rate_limit_key="COSAT00301")

    start = time.monotonic()
    for _ in range(ACCOUNT_LIMIT):
        await tr_a.wait_until_available_async()
    for _ in range(ACCOUNT_LIMIT):
        await tr_b.wait_until_available_async()
    elapsed = time.monotonic() - start

    total_in_window = len(tr_a.request_timestamps) + len(tr_b.request_timestamps)
    # All 2*LIMIT requests cleared instantly: the account budget was ignored.
    assert total_in_window == 2 * ACCOUNT_LIMIT
    assert elapsed < 0.5, (
        "no cross-TR throttling: account-cumulative budget is not enforced"
    )


@pytest.mark.asyncio
async def test_account_gate_enforces_cumulative_limit_across_trs():
    """FIX: an opt-in shared account gate caps the cumulative stream.

    Both TRs pass the same ``account_rate_limit_key``; the first ACCOUNT_LIMIT
    requests fill the shared budget, so the next request (on the *other* TR)
    must wait ~1s for the sliding window to free a slot.
    """
    common = dict(
        rate_limit_seconds=1,
        on_rate_limit="wait",
        account_rate_limit_count=ACCOUNT_LIMIT,
        account_rate_limit_seconds=1,
        account_rate_limit_key="acct-123",
    )
    tr_a = _FakeTR(rate_limit_count=ACCOUNT_LIMIT, rate_limit_key="g3101", **common)
    tr_b = _FakeTR(rate_limit_count=ACCOUNT_LIMIT, rate_limit_key="COSAT00301", **common)

    start = time.monotonic()
    for _ in range(ACCOUNT_LIMIT):
        await tr_a.wait_until_available_async()
    # (ACCOUNT_LIMIT + 1)-th cumulative request, issued on a different TR.
    await tr_b.wait_until_available_async()
    elapsed = time.monotonic() - start

    assert elapsed >= 0.9, (
        "account gate did not throttle the cumulative request across TRs"
    )


def test_account_gate_is_opt_in_and_backward_compatible():
    """No account params -> behaviour is identical to today (no account bucket)."""
    tr = _FakeTR(rate_limit_count=ACCOUNT_LIMIT, rate_limit_seconds=1,
                 on_rate_limit="wait", rate_limit_key="g3101")
    assert tr._account_bucket is None
