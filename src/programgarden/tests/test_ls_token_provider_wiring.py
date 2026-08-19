"""Executor wiring for the opt-in LS token provider (Verified League §3.2.3).

Verifies LSClientManager.get_or_create attaches the context's ls_token_provider
to the LS instance and that login() then consumes the server-issued token
without self-issuing via GenerateToken (no appsecret required).
"""

import pytest

from programgarden.executor import LSClientManager


class _FakeContext:
    """Minimal ExecutionContext stand-in for LSClientManager.get_or_create."""

    def __init__(self, ls_token_provider=None):
        self.ls_token_provider = ls_token_provider
        self.logs = []

    def log(self, level, message, node_id=None):
        self.logs.append((level, message))


@pytest.fixture(autouse=True)
def _reset_ls_clients():
    LSClientManager.reset()
    yield
    LSClientManager.reset()


def test_provider_attached_and_consumed_without_self_issue(monkeypatch):
    import time

    # GenerateToken must never be constructed in provider mode.
    class _Boom:
        def __init__(self, *a, **k):
            raise AssertionError("GenerateToken must not be used in provider mode")

    monkeypatch.setattr(
        "programgarden_finance.ls.oauth.generate_token.GenerateToken", _Boom
    )

    calls = {"n": 0, "args": None}

    def provider(appkey, product, paper_trading):
        calls["n"] += 1
        calls["args"] = (appkey, product, paper_trading)
        return "PROVIDED_TOKEN", time.time() + 3600

    ctx = _FakeContext(ls_token_provider=provider)

    ls, success, err = LSClientManager.get_or_create(
        product="overseas_stock",
        appkey="AK",
        appsecret="",  # consumer mode: no secret held
        paper_trading=False,
        context=ctx,
        node_id="broker-1",
    )

    assert success is True and err is None
    assert calls["n"] == 1
    assert calls["args"] == ("AK", "overseas_stock", False)
    assert ls.token_manager.access_token == "PROVIDED_TOKEN"
    assert ls.token_manager.has_provider() is True


def test_no_provider_does_not_attach(monkeypatch):
    """Without a provider, no provider is attached (self-issue path preserved).

    The self-issue token flow itself is covered by
    src/finance/tests/test_token_provider.py; here we only assert the executor
    leaves the LS instance in non-provider mode and login is still attempted via
    the appkey/appsecret path.
    """
    attempted = {"login": 0}

    real_get_or_create = LSClientManager.get_or_create

    # Stub LS.login to avoid a real network call while asserting non-provider mode.
    from programgarden_finance import LS

    def _fake_login(self, appkey=None, appsecretkey=None, paper_trading=False):
        attempted["login"] += 1
        assert self.token_manager.has_provider() is False
        # mimic a successful self-issue without network
        self.token_manager.apply_token("SELF_ISSUED", __import__("time").time() + 3600)
        return True

    monkeypatch.setattr(LS, "login", _fake_login)

    ctx = _FakeContext(ls_token_provider=None)
    ls, success, err = real_get_or_create(
        product="overseas_stock",
        appkey="AK",
        appsecret="AS",
        paper_trading=False,
        context=ctx,
        node_id="broker-1",
    )

    assert success is True
    assert attempted["login"] == 1
    assert ls.token_manager.has_provider() is False


def test_force_reissue_is_forwarded_to_a_provider_that_supports_it(monkeypatch):
    """사용 중 토큰 무효로 촉발된 강제 재발급이 주입된 provider 까지 도달해야 한다.

    도달하지 않으면 서버가 만료 전 캐시 토큰을 그대로 돌려주므로 재발급이 무의미해진다.
    """
    import time

    seen = []

    def provider(appkey, product, paper_trading, *, force_reissue=False, stale_token=None):
        seen.append({"force": force_reissue, "stale": stale_token})
        return f"TOK{len(seen)}", time.time() + 3600

    ctx = _FakeContext(ls_token_provider=provider)
    ls, success, _err = LSClientManager.get_or_create(
        product="overseas_futures", appkey="AK", appsecret="",
        paper_trading=False, context=ctx, node_id="broker-1",
    )
    assert success is True and seen[0]["force"] is False

    assert ls.token_manager.force_reissue() is True
    assert seen[1] == {"force": True, "stale": "TOK1"}
    assert ls.token_manager.access_token == "TOK2"


def test_legacy_three_arg_provider_still_works_under_force(monkeypatch):
    """구판 3-인자 provider 에 force 를 넘겨 TypeError 로 죽지 않아야 한다."""
    import time

    calls = {"n": 0}

    def legacy_provider(appkey, product, paper_trading):
        calls["n"] += 1
        return f"LEGACY{calls['n']}", time.time() + 3600

    ctx = _FakeContext(ls_token_provider=legacy_provider)
    ls, success, _err = LSClientManager.get_or_create(
        product="overseas_stock", appkey="AK", appsecret="",
        paper_trading=False, context=ctx, node_id="broker-1",
    )
    assert success is True

    assert ls.token_manager.force_reissue() is True
    assert calls["n"] == 2 and ls.token_manager.access_token == "LEGACY2"
