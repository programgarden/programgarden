"""
FuturesContractNode — 만기 종속성 근본 해결 테스트

선물 워크플로우가 월물 종목코드(HMHU26)를 하드코딩하면 만기가 지나는 순간 조용히 죽는다.
LS 는 만기 경과 종목에 과거봉도 현재가도 주지 않고 **에러도 내지 않기** 때문이다(빈 배열).
FuturesContractNode 는 실행 시점에 LS 종목마스터(o3101)를 조회해 살아있는 월물만 고른다.

여기서 지키는 계약:
1. front / next / quarterly 선택이 만기 오름차순 기준으로 정확하다
2. 만기 경과 월물은 마스터에 남아 있어도 **절대** 선택되지 않는다
3. 알 수 없는 기초자산은 **조용한 빈 배열이 아니라** 사유가 담긴 에러다
4. symbols 출력이 WatchlistNode 와 같은 [{exchange, symbol}] 계약이다 (하류 배선 불변)
5. deep_validate 는 네트워크 없이 통과한다
6. 배열 생성 노드이므로 auto-iterate 대상이 아니다

실행:
    cd src/programgarden && poetry run pytest tests/test_futures_contract_node.py -v
"""

import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from programgarden.executor import (
    FuturesContractNodeExecutor,
    WorkflowJob,
)
from programgarden import deep_fixtures as _df


# ---------------------------------------------------------------------------
# Mock helpers — o3101 마스터 응답을 실제 LS 필드명 그대로 흉내낸다.
# (실측: LstngM 은 월물 **문자 코드**('N'=7월)이지 숫자가 아니다.)
# ---------------------------------------------------------------------------

def _row(symbol, base, year, month_letter, exch="HKEX", name=None):
    return SimpleNamespace(
        Symbol=symbol,
        SymbolNm=name or f"{base}({year}.{month_letter})",
        BscGdsCd=base,
        BscGdsNm="Mini Hang Seng" if base == "HMH" else "Mini H-Shares",
        ExchCd=exch,
        ExchNm="홍콩거래소",
        CrncyCd="HKD",
        LstngYr=str(year),
        LstngM=month_letter,
    )


# 2026-07 기준 실제 LS 상장 월물 (실측 반영)
LISTED_ROWS = [
    _row("HMHN26", "HMH", 2026, "N"),    # 7월 (근월)
    _row("HMHQ26", "HMH", 2026, "Q"),    # 8월 (차월)
    _row("HMHU26", "HMH", 2026, "U"),    # 9월 (분기)
    _row("HMHZ26", "HMH", 2026, "Z"),    # 12월
    _row("HMCEN26", "HMCE", 2026, "N"),
    _row("HMCEQ26", "HMCE", 2026, "Q"),
    _row("HMCEU26", "HMCE", 2026, "U"),
    _row("LSRN26", "LSR", 2026, "N", exch="LME"),
]


def _make_context():
    ctx = MagicMock()
    ctx.is_deep_validate = False
    ctx.is_dry_run = False
    ctx.log = MagicMock()
    ctx.get_credential = MagicMock(return_value={
        "appkey": "k", "appsecret": "s", "paper_trading": False,
    })
    ctx.get_deep_fixture = MagicMock(return_value=None)
    return ctx


def _patched_master(rows):
    """ensure_ls_login + o3101 마스터 응답을 통째로 대체한다 (네트워크 0)."""
    response = SimpleNamespace(block=rows)

    query = MagicMock()

    async def _req_async():
        return response

    query.req_async = _req_async

    ls = MagicMock()
    ls.overseas_futureoption.return_value.market.return_value.해외선물마스터조회.return_value = query
    return patch("programgarden.executor.ensure_ls_login", return_value=(ls, True, None))


async def _run(config, rows=LISTED_ROWS, now=(2026, 7)):
    """지정한 '오늘'로 노드를 실행한다 (만기 판정이 시계에 의존하므로 고정)."""
    ex = FuturesContractNodeExecutor()

    class _FixedNow:
        @staticmethod
        def now():
            import datetime as _dt
            return _dt.datetime(now[0], now[1], 15)

    with _patched_master(rows), patch("programgarden.executor.datetime", _FixedNow):
        return await ex.execute("contract", "FuturesContractNode", config, _make_context())


# ---------------------------------------------------------------------------
# 1. 월물 선택
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_front_picks_nearest_expiry():
    out = await _run({"base_products": ["HMH", "HMCE"], "contract_selection": "front"})
    assert out["symbols"] == [
        {"exchange": "HKEX", "symbol": "HMHN26"},
        {"exchange": "HKEX", "symbol": "HMCEN26"},
    ]
    assert out["count"] == 2


@pytest.mark.asyncio
async def test_next_picks_second_nearest():
    out = await _run({"base_products": ["HMH"], "contract_selection": "next"})
    assert out["symbols"] == [{"exchange": "HKEX", "symbol": "HMHQ26"}]


@pytest.mark.asyncio
async def test_quarterly_picks_nearest_quarter_month():
    """분기월물 = 3/6/9/12월. 7월(N)/8월(Q)을 건너뛰고 9월(U)을 골라야 한다."""
    out = await _run({"base_products": ["HMH"], "contract_selection": "quarterly"})
    assert out["symbols"] == [{"exchange": "HKEX", "symbol": "HMHU26"}]


@pytest.mark.asyncio
async def test_base_products_order_is_preserved():
    out = await _run({"base_products": ["HMCE", "HMH"]})
    assert [s["symbol"] for s in out["symbols"]] == ["HMCEN26", "HMHN26"]


# ---------------------------------------------------------------------------
# 2. 만기 경과 월물 — 이 프로젝트의 존재 이유
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_expired_contract_is_never_selected():
    """마스터에 만기 경과 월물이 남아 있어도 근월물로 뽑히면 안 된다.

    LS 는 보통 만기분을 빼주지만, 하루라도 남아 있으면 그게 front 로 뽑혀
    워크플로우가 조용히 죽는다(시세도 과거봉도 빈 배열). 노드가 직접 잘라낸다.
    """
    rows = [
        _row("HMHM26", "HMH", 2026, "M"),   # 6월 — 이미 만기 경과
        _row("HMHN26", "HMH", 2026, "N"),   # 7월 — 살아있는 근월
    ]
    out = await _run({"base_products": ["HMH"], "contract_selection": "front"}, rows=rows)
    assert out["symbols"] == [{"exchange": "HKEX", "symbol": "HMHN26"}]


@pytest.mark.asyncio
async def test_all_contracts_expired_raises_with_reason():
    rows = [_row("HMHM26", "HMH", 2026, "M")]  # 6월만 있고 오늘은 7월
    with pytest.raises(RuntimeError, match="no listed contract for underlying"):
        await _run({"base_products": ["HMH"]}, rows=rows)


@pytest.mark.asyncio
async def test_rollover_happens_automatically_next_month():
    """8월이 되면 같은 워크플로우가 손대지 않고도 8월물로 넘어간다."""
    out = await _run({"base_products": ["HMH"], "contract_selection": "front"}, now=(2026, 8))
    assert out["symbols"] == [{"exchange": "HKEX", "symbol": "HMHQ26"}]


# ---------------------------------------------------------------------------
# 3. 실패는 조용하지 않다
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_unknown_base_product_raises_listing_available_codes():
    with pytest.raises(RuntimeError) as e:
        await _run({"base_products": ["NOPE"]})
    msg = str(e.value)
    assert "NOPE" in msg
    assert "HMH" in msg and "HMCE" in msg  # 무엇을 쓸 수 있는지 알려준다


@pytest.mark.asyncio
async def test_contract_symbol_in_base_products_is_rejected_loudly():
    """base_products 에 월물 심볼(HMHN26)을 넣는 흔한 실수 — 빈 배열이 아니라 에러여야 한다."""
    with pytest.raises(RuntimeError, match="HMHN26"):
        await _run({"base_products": ["HMHN26"]})


@pytest.mark.asyncio
async def test_empty_base_products_raises():
    ex = FuturesContractNodeExecutor()
    with pytest.raises(RuntimeError, match="base_products"):
        await ex.execute("contract", "FuturesContractNode", {"base_products": []}, _make_context())


@pytest.mark.asyncio
async def test_missing_broker_credential_raises_pointing_at_broker_node():
    ex = FuturesContractNodeExecutor()
    ctx = _make_context()
    ctx.get_credential = MagicMock(return_value=None)
    with pytest.raises(RuntimeError, match="OverseasFuturesBrokerNode"):
        await ex.execute("contract", "FuturesContractNode", {"base_products": ["HMH"]}, ctx)


@pytest.mark.asyncio
async def test_next_unavailable_raises_instead_of_dropping_symbol():
    rows = [_row("HMHN26", "HMH", 2026, "N")]  # 월물이 하나뿐
    with pytest.raises(RuntimeError, match="contract_selection='next'"):
        await _run({"base_products": ["HMH"], "contract_selection": "next"}, rows=rows)


# ---------------------------------------------------------------------------
# 4. 거래소 필터 / 하류 계약
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_exchange_filter_narrows_master():
    with pytest.raises(RuntimeError, match="no listed contract"):
        await _run({"base_products": ["LSR"], "futures_exchange": "HKEX"})  # LSR 은 LME 다

    out = await _run({"base_products": ["LSR"], "futures_exchange": "LME"})
    assert out["symbols"] == [{"exchange": "LME", "symbol": "LSRN26"}]


@pytest.mark.asyncio
async def test_symbols_port_matches_watchlist_contract():
    """symbols 원소는 정확히 {exchange, symbol} 2키 — WatchlistNode 와 동일해야
    하류(historical/market/condition/order) 배선이 그대로 유지된다."""
    out = await _run({"base_products": ["HMH"]})
    assert all(set(s.keys()) == {"exchange", "symbol"} for s in out["symbols"])
    # 거래소는 레지스트리 코드(HKEX)여야 한다 — LS 의 한글명('홍콩거래소')이 새면 주문이 깨진다.
    assert out["symbols"][0]["exchange"] == "HKEX"


@pytest.mark.asyncio
async def test_contracts_port_carries_detail_for_reports():
    out = await _run({"base_products": ["HMH"]})
    c = out["contracts"][0]
    assert c["symbol"] == "HMHN26"
    assert c["base_product"] == "HMH"
    assert c["contract_month"] == "2026-07"


# ---------------------------------------------------------------------------
# 5. 게이트 — deep_validate / auto-iterate
# ---------------------------------------------------------------------------

def test_deep_fixture_needs_no_network_and_matches_port_shape():
    fx = _df.futures_contract_fixture({"base_products": ["HMH", "HMCE"]})
    assert fx["count"] == 2
    assert all(set(s.keys()) == {"exchange", "symbol"} for s in fx["symbols"])
    assert [c["base_product"] for c in fx["contracts"]] == ["HMH", "HMCE"]


@pytest.mark.asyncio
async def test_dry_run_does_not_touch_ls():
    """dry_run = '브로커를 건드리지 않는다'. o3101 을 부르면 mock LS 에 걸려 워크플로우가 죽는다
    (examples dry-run 게이트가 정확히 이걸 잡는다)."""
    ex = FuturesContractNodeExecutor()
    ctx = _make_context()
    ctx.is_dry_run = True
    out = await ex.execute("contract", "FuturesContractNode", {"base_products": ["HMH"]}, ctx)
    assert out["count"] == 1
    assert set(out["symbols"][0].keys()) == {"exchange", "symbol"}


@pytest.mark.asyncio
async def test_deep_validate_does_not_touch_ls():
    ex = FuturesContractNodeExecutor()
    ctx = _make_context()
    ctx.is_deep_validate = True
    ctx.get_credential = MagicMock(return_value=None)  # 자격 없어도 통과해야 한다
    out = await ex.execute("contract", "FuturesContractNode", {"base_products": ["HMH"]}, ctx)
    assert out["count"] == 1
    assert set(out["symbols"][0].keys()) == {"exchange", "symbol"}


def test_array_producing_nodes_are_not_auto_iterated():
    """배열을 **생성**하는 노드가 auto-iterate 대상이 되면 상류 아이템 수만큼
    마스터 조회를 반복해 같은 목록을 N 번 받아온다."""
    no_iter = WorkflowJob.NO_AUTO_ITERATE_NODE_TYPES
    assert "FuturesContractNode" in no_iter
    assert "OverseasFuturesSymbolQueryNode" in no_iter
    assert "OverseasStockSymbolQueryNode" in no_iter
    assert "KoreaStockSymbolQueryNode" in no_iter
