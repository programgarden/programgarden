"""A-1 wiring: account-scope the per-TR rate-limit bucket key.

``set_tr_header_options()`` namespaces each TR's shared ``rate_limit_key`` by the
logged-in account (``token_manager.appkey``). The per-TR ``rate_limit_count`` /
``rate_limit_seconds`` numbers are left untouched — only the bucket *key* changes,
so the same account's concurrent connections (LS allows up to 3 per account)
share one sliding-window bucket while different accounts running in one process
stay isolated. Single-account deployments are unaffected: one appkey resolves to
exactly one bucket, identical to today.

This complements the opt-in cumulative gate in
``test_account_cumulative_rate_limit.py`` (``_RateBucket``), which stays dormant
until an LS account-total number is available.
"""

from types import SimpleNamespace

from programgarden_finance.ls.models import SetupOptions
from programgarden_finance.ls.tr_base import set_tr_header_options
from programgarden_finance.ls.token_manager import TokenManager


def _make_request(rate_limit_key, tr_cd="g3101"):
    """Build a stand-in request_data shaped like a real TR request.

    The header carries a non-empty ``authorization`` so ``set_tr_header_options``
    never needs to mint a bearer token (which would require a live login).
    """
    header = SimpleNamespace(authorization="Bearer test-token", tr_cd=tr_cd)
    kwargs = dict(rate_limit_count=3, rate_limit_seconds=1, on_rate_limit="wait")
    if rate_limit_key is not None:
        kwargs["rate_limit_key"] = rate_limit_key
    return SimpleNamespace(header=header, options=SetupOptions(**kwargs))


def _apply(token_manager, request_data):
    set_tr_header_options(
        token_manager=token_manager,
        header=None,
        options=None,
        request_data=request_data,
    )


def test_key_is_namespaced_by_account():
    tm = TokenManager(appkey="APPKEY_A", appsecretkey="secret")
    req = _make_request("g3101")
    _apply(tm, req)
    assert req.options.rate_limit_key == "APPKEY_A:g3101"


def test_same_account_same_tr_share_one_key():
    tm = TokenManager(appkey="APPKEY_A", appsecretkey="secret")
    r1, r2 = _make_request("g3101"), _make_request("g3101")
    _apply(tm, r1)
    _apply(tm, r2)
    # Identical composed key -> both resolve to the same shared bucket, so the
    # account's parallel connections coordinate one budget.
    assert r1.options.rate_limit_key == r2.options.rate_limit_key == "APPKEY_A:g3101"


def test_different_accounts_same_tr_are_isolated():
    tm_a = TokenManager(appkey="APPKEY_A", appsecretkey="secret")
    tm_b = TokenManager(appkey="APPKEY_B", appsecretkey="secret")
    ra, rb = _make_request("g3101"), _make_request("g3101")
    _apply(tm_a, ra)
    _apply(tm_b, rb)
    # Different accounts no longer collide on the process-global per-TR bucket.
    assert ra.options.rate_limit_key == "APPKEY_A:g3101"
    assert rb.options.rate_limit_key == "APPKEY_B:g3101"
    assert ra.options.rate_limit_key != rb.options.rate_limit_key


def test_missing_appkey_preserves_original_key():
    tm = TokenManager(appkey=None, appsecretkey=None)
    req = _make_request("g3101")
    _apply(tm, req)
    assert req.options.rate_limit_key == "g3101"  # behaviour-preserving fallback


def test_missing_base_key_skips_composition():
    tm = TokenManager(appkey="APPKEY_A", appsecretkey="secret")
    req = _make_request(None)  # TR that never opted into a shared bucket
    _apply(tm, req)
    assert req.options.rate_limit_key is None  # stays per-instance, unchanged


def test_composition_is_idempotent():
    tm = TokenManager(appkey="APPKEY_A", appsecretkey="secret")
    req = _make_request("g3101")
    _apply(tm, req)
    _apply(tm, req)  # second pass on the same options must not double-prefix
    assert req.options.rate_limit_key == "APPKEY_A:g3101"
