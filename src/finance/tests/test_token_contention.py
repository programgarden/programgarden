"""LS 토큰 경합 대응 — 사용 중 실패 판정 · 강제 재발급 · single-flight · 상한.

배경: 종전 구현은 **만료시각만** 보고 토큰을 내줬다. 같은 앱키로 토큰이 한 번 더
발급되면 앞 토큰은 LS 에서 죽는데, 만료 전이라 계속 재사용돼
``HTTP 500: 유효하지 않은 token 입니다`` 로 실패했다(해외선물 시세 o3101 실측).

여기서 검증하는 것:
  ① 응답이 토큰 무효를 **말해 주면** 재시도 없이 즉시 재발급한다.
  ② 토큰인지 알 수 없는 일시 실패만 간격을 두고 재시도한다.
  ③ 주문 엔드포인트는 일시 실패를 **재시도하지 않는다**(중복 주문 방지).
  ④ 여러 호출자가 같은 실패를 만나도 재발급은 한 번만 나간다(세대 기반 single-flight).
  ⑤ 재발급에는 상한이 있고, 초과 시 조용히 실패하지 않고 사유를 담아 예외를 올린다.

    cd src/finance && poetry run pytest tests/test_token_contention.py -v
"""

import time
from types import SimpleNamespace

import pytest

from programgarden_finance.ls import token_manager as tm_mod
from programgarden_finance.ls import tr_helpers as trh
from programgarden_finance.ls.token_errors import (
    TokenFailureKind,
    TokenReissueLimitExceeded,
    classify_token_failure,
)
from programgarden_finance.ls.token_manager import TokenManager


class _Resp:
    """status(aiohttp) / status_code(requests) 를 모두 흉내내는 최소 응답."""

    def __init__(self, status: int):
        self.status = status
        self.status_code = status


# ---------------------------------------------------------------------------
# ① 판정기
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "status, body, expected",
    [
        # 실측 문구 — o3101 은 401 이 아니라 HTTP 500 으로 온다.
        (500, {"rsp_msg": "유효하지 않은 token 입니다"}, TokenFailureKind.TOKEN_INVALID),
        (500, {"rsp_msg": "기간이 만료된 token 입니다"}, TokenFailureKind.TOKEN_INVALID),
        # error_msg 만 채우는 경로도 잡아야 한다.
        (500, {"error_msg": "invalid token"}, TokenFailureKind.TOKEN_INVALID),
        # 인증 거부는 문구가 없어도 확정.
        (401, None, TokenFailureKind.TOKEN_INVALID),
        (403, {}, TokenFailureKind.TOKEN_INVALID),
        # HTTP 200 이어도 본문이 토큰 무효를 말하면 확정.
        (200, {"rsp_msg": "유효하지 않은 token 입니다"}, TokenFailureKind.TOKEN_INVALID),
        # 문구가 없는 5xx/429 는 '토큰인지 모름' → 일시 실패.
        (500, {"rsp_msg": "일시적인 오류"}, TokenFailureKind.TRANSIENT),
        (503, None, TokenFailureKind.TRANSIENT),
        (429, None, TokenFailureKind.TRANSIENT),
        # 요청 자체의 문제는 재시도도 재발급도 소용없다.
        (400, {"rsp_msg": "필수값 누락"}, TokenFailureKind.NONE),
        (404, None, TokenFailureKind.NONE),
        (200, {"rsp_cd": "00000"}, TokenFailureKind.NONE),
    ],
)
def test_classify(status, body, expected):
    assert classify_token_failure(_Resp(status), body) is expected


def test_classify_exception_is_transient():
    assert classify_token_failure(None, None, exc=OSError("conn reset")) is TokenFailureKind.TRANSIENT


# ---------------------------------------------------------------------------
# ② TokenManager — force 가 실제로 재발급을 낸다
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _no_reissue_sleep(monkeypatch):
    monkeypatch.setattr(tm_mod, "FORCED_REISSUE_MIN_INTERVAL_SECONDS", 0.0)


def test_force_refresh_reissues_even_when_not_expired():
    """종전 결함: 만료 전이면 force_refresh=True 를 **무시**하고 죽은 토큰을 유지했다."""
    calls = {"n": 0}

    def provider(*, force_reissue: bool = False, stale_token=None):
        calls["n"] += 1
        return (f"T{calls['n']}", time.time() + 3600)

    tm = TokenManager()
    tm.token_provider = provider
    assert tm.ensure_fresh_token(force_refresh=True) is True
    assert tm.access_token == "T1"

    # 아직 만료 전이다 — 그래도 강제 재발급이면 provider 를 다시 불러야 한다.
    assert tm.is_expired() is False
    assert tm.ensure_fresh_token(force_refresh=True) is True
    assert calls["n"] == 2 and tm.access_token == "T2"


def test_provider_receives_force_reissue_and_stale_token():
    seen = {}

    def provider(*, force_reissue: bool = False, stale_token=None):
        seen["force"] = force_reissue
        seen["stale"] = stale_token
        return ("NEW", time.time() + 3600)

    tm = TokenManager()
    tm.token_provider = provider
    tm.apply_token("DEAD", time.time() + 3600)
    assert tm.force_reissue() is True
    assert seen == {"force": True, "stale": "DEAD"}
    assert tm.access_token == "NEW"


def test_legacy_provider_without_force_kwarg_still_works():
    """구판 provider(키워드 미지원)에 force 를 넘겨 TypeError 로 죽지 않아야 한다."""
    def legacy_provider():
        return ("LEGACY", time.time() + 3600)

    tm = TokenManager()
    tm.token_provider = legacy_provider
    assert tm.force_reissue() is True
    assert tm.access_token == "LEGACY"


def test_generation_joins_concurrent_reissue():
    """다른 호출자가 이미 재발급했으면 재발급을 또 내지 않고 합류한다."""
    calls = {"n": 0}

    def provider(*, force_reissue: bool = False, stale_token=None):
        calls["n"] += 1
        return (f"T{calls['n']}", time.time() + 3600)

    tm = TokenManager()
    tm.token_provider = provider
    tm.apply_token("OLD", time.time() + 3600)
    stale_generation = tm.token_generation

    # 다른 호출자가 먼저 재발급을 끝냈다고 가정.
    tm.apply_token("ISSUED_BY_OTHER", time.time() + 3600)

    # 뒤늦게 실패를 관측한 호출자는 옛 세대를 들고 온다 → 발급하지 않고 합류.
    assert tm.force_reissue(observed_generation=stale_generation) is True
    assert calls["n"] == 0
    assert tm.access_token == "ISSUED_BY_OTHER"


def test_forced_reissue_cap_raises_with_reason():
    def provider(*, force_reissue: bool = False, stale_token=None):
        return ("T", time.time() + 3600)

    tm = TokenManager()
    tm.token_provider = provider
    for _ in range(tm_mod.FORCED_REISSUE_MAX):
        assert tm.force_reissue() is True

    with pytest.raises(TokenReissueLimitExceeded) as exc_info:
        tm.force_reissue()
    # 조용한 False 가 아니라 사람이 읽을 사유가 담겨야 한다.
    assert "재발급" in str(exc_info.value)


def test_on_token_refreshed_hook_fires():
    """자체 발급 경로가 만든 토큰을 공유 저장소에 되쓰기할 수 있어야 한다."""
    seen = []
    tm = TokenManager()
    tm.set_on_token_refreshed(lambda token, expires_at: seen.append((token, expires_at)))
    tm.apply_token("WRITTEN", 12345.0)
    assert seen == [("WRITTEN", 12345.0)]


@pytest.mark.asyncio
async def test_async_force_refresh_reissues_even_when_not_expired():
    calls = {"n": 0}

    async def aprovider(*, force_reissue: bool = False, stale_token=None):
        calls["n"] += 1
        return (f"A{calls['n']}", time.time() + 3600)

    tm = TokenManager()
    tm.async_token_provider = aprovider
    assert await tm.ensure_fresh_token_async(force_refresh=True) is True
    assert await tm.ensure_fresh_token_async(force_refresh=True) is True
    assert calls["n"] == 2 and tm.access_token == "A2"


# ---------------------------------------------------------------------------
# ③ GenericTR — 판정 결과별 동작
# ---------------------------------------------------------------------------

def _make_generic(url: str, token_manager=None) -> trh.GenericTR:
    request_data = SimpleNamespace(
        options=SimpleNamespace(
            rate_limit_count=100,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="test",
            account_rate_limit_count=None,
            account_rate_limit_seconds=None,
            account_rate_limit_key=None,
            token_manager=token_manager,
        ),
        header=SimpleNamespace(authorization=""),
    )
    return trh.GenericTR(request_data, lambda resp, rj, rh, exc: (resp, rj, rh, exc), url=url)


def _token_manager_with_provider(tokens):
    it = iter(tokens)

    def provider(*, force_reissue: bool = False, stale_token=None):
        return (next(it), time.time() + 3600)

    tm = TokenManager()
    tm.token_provider = provider
    tm.apply_token("DEAD", time.time() + 3600)
    return tm


def test_token_invalid_reissues_immediately_without_sleeping(monkeypatch):
    """토큰 무효는 확정 신호다 — 간격 재시도를 거치지 않고 곧장 재발급한다."""
    monkeypatch.setattr(trh.time, "sleep", lambda _s: pytest.fail("토큰 무효인데 대기했다"))

    tm = _token_manager_with_provider(["FRESH"])
    gtr = _make_generic("https://x/overseas-futureoption/market-data", tm)

    attempts = []

    def fake_execute(url, request_data, timeout=10):
        attempts.append(request_data.header.authorization)
        if len(attempts) == 1:
            return _Resp(500), {"rsp_msg": "유효하지 않은 token 입니다"}, {}
        return _Resp(200), {"rsp_cd": "00000"}, {}

    monkeypatch.setattr(gtr, "execute_sync", fake_execute)
    resp, rj, _rh = gtr._execute_sync_with_retry()

    assert len(attempts) == 2
    assert tm.access_token == "FRESH"
    # 재시도는 새 토큰으로 나가야 한다.
    assert attempts[1] == "Bearer FRESH"
    assert resp.status == 200


def test_transient_failure_retries_with_intervals(monkeypatch):
    monkeypatch.setattr(trh, "TRANSIENT_RETRY_DELAYS", (0.0, 0.0, 0.0))
    slept = []
    monkeypatch.setattr(trh.time, "sleep", lambda s: slept.append(s))

    gtr = _make_generic("https://x/overseas-stock/market-data")
    calls = {"n": 0}

    def fake_execute(url, request_data, timeout=10):
        calls["n"] += 1
        if calls["n"] <= 2:
            return _Resp(503), None, {}
        return _Resp(200), {"rsp_cd": "00000"}, {}

    monkeypatch.setattr(gtr, "execute_sync", fake_execute)
    resp, _rj, _rh = gtr._execute_sync_with_retry()

    assert calls["n"] == 3 and len(slept) == 2
    assert resp.status == 200


def test_transient_retry_is_bounded(monkeypatch):
    monkeypatch.setattr(trh, "TRANSIENT_RETRY_DELAYS", (0.0, 0.0, 0.0))
    monkeypatch.setattr(trh.time, "sleep", lambda _s: None)

    gtr = _make_generic("https://x/overseas-stock/market-data")
    calls = {"n": 0}

    def fake_execute(url, request_data, timeout=10):
        calls["n"] += 1
        return _Resp(503), None, {}

    monkeypatch.setattr(gtr, "execute_sync", fake_execute)
    resp, _rj, _rh = gtr._execute_sync_with_retry()

    # token_manager 가 없으면 재발급 경로도 없으므로 1 + 3 회에서 멈춘다.
    assert calls["n"] == 4
    assert resp.status == 503


def test_order_endpoint_never_retries_transient_failures(monkeypatch):
    """주문은 접수 여부를 알 수 없다 — 5xx 를 재시도하면 중복 주문이 된다."""
    monkeypatch.setattr(trh.time, "sleep", lambda _s: pytest.fail("주문 경로에서 대기했다"))

    gtr = _make_generic("https://x/overseas-stock/order")
    calls = {"n": 0}

    def fake_execute(url, request_data, timeout=10):
        calls["n"] += 1
        return _Resp(500), {"rsp_msg": "일시적인 오류"}, {}

    monkeypatch.setattr(gtr, "execute_sync", fake_execute)
    resp, _rj, _rh = gtr._execute_sync_with_retry()

    assert calls["n"] == 1
    assert resp.status == 500


def test_order_endpoint_does_retry_after_token_reissue(monkeypatch):
    """토큰 무효는 인증 단계 거부라 주문이 나가지 않았음이 보장된다 — 재시도 안전."""
    tm = _token_manager_with_provider(["FRESH"])
    gtr = _make_generic("https://x/overseas-stock/order", tm)
    calls = {"n": 0}

    def fake_execute(url, request_data, timeout=10):
        calls["n"] += 1
        if calls["n"] == 1:
            return _Resp(500), {"rsp_msg": "유효하지 않은 token 입니다"}, {}
        return _Resp(200), {"rsp_cd": "00000"}, {}

    monkeypatch.setattr(gtr, "execute_sync", fake_execute)
    resp, _rj, _rh = gtr._execute_sync_with_retry()

    assert calls["n"] == 2 and resp.status == 200


def test_repeated_token_invalid_stops_at_cap(monkeypatch):
    """새 토큰으로도 계속 거부되면 무한 재발급 대신 사유를 담아 실패한다."""
    monkeypatch.setattr(tm_mod, "FORCED_REISSUE_MAX", 2)
    tm = _token_manager_with_provider(["A", "B", "C", "D"])
    gtr = _make_generic("https://x/overseas-futureoption/market-data", tm)
    calls = {"n": 0}

    def fake_execute(url, request_data, timeout=10):
        calls["n"] += 1
        return _Resp(500), {"rsp_msg": "유효하지 않은 token 입니다"}, {}

    monkeypatch.setattr(gtr, "execute_sync", fake_execute)
    resp, _rj, _rh = gtr._execute_sync_with_retry()

    # 요청당 재발급 상한(TOKEN_REISSUE_RETRY_MAX=2) 에서 멈추고 마지막 응답을 돌려준다.
    assert calls["n"] == trh.TOKEN_REISSUE_RETRY_MAX + 1
    assert resp.status == 500


@pytest.mark.asyncio
async def test_async_token_invalid_reissues_and_retries(monkeypatch):
    tm = _token_manager_with_provider(["FRESH"])
    gtr = _make_generic("https://x/overseas-futureoption/market-data", tm)
    attempts = []

    async def fake_execute(session, url, request_data, timeout=10):
        attempts.append(request_data.header.authorization)
        if len(attempts) == 1:
            return _Resp(500), {"rsp_msg": "유효하지 않은 token 입니다"}, {}
        return _Resp(200), {"rsp_cd": "00000"}, {}

    monkeypatch.setattr(gtr, "execute_async_with_session", fake_execute)
    resp, _rj, _rh = await gtr._execute_async_with_retry(session=None)

    assert len(attempts) == 2 and attempts[1] == "Bearer FRESH"
    assert resp.status == 200
