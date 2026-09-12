"""해외주식 주문이벤트 노드(OverseasStockRealOrderEventNode)의 스트림 등록·파서.

수정 전 결함(국내 SC 와 **동형**):

1. **AS1~AS4 프레임이 노드에 도달조차 못 했다.** 리스너를 ``AS0().on_as0_message(...)``
   하나만 걸고 핸들러 안에서 ``tr_cd`` 로 AS1~AS4 를 분기했는데, SDK 디스패치는
   프레임 ``tr_cd`` **정확일치 키**로만 이뤄진다
   (``ls/real_base.py`` ``self._on_message_listeners.get(tr_cd)``). 그래서 AS1(체결)·
   AS2(정정)·AS3(취소확인)·AS4(거부) 프레임은 리스너가 없어 버려졌다 —
   filled/modified/cancelled/rejected 포트는 영구히 0건.

2. **체결가 갱신이 주문가를 체결가로 썼다.** 체결('11') 분기가 ``sOrdPrc``(주문가)를
   체결가로 썼는데 체결가는 ``sExecPrc`` 다. 게다가 '11' 은 AS0 의 enum
   ('01'/'03'/'12'/'13'/'14')에 없어 그 분기는 한 번도 타지 않았다(AS1 도 안 왔다).

이 테스트는 실제 SDK 응답 모델(``AS0RealResponse``/``AS1RealResponse`` 등)로 프레임을
만들어 (가) 스트림마다 리스너가 실제로 등록되는지, (나) 스트림별 파서가 SDK 의 실제
필드명을 읽는지, (다) AS0 에 없는 체결 필드를 0 으로 지어내지 않는지, (라) 소수점
``sExecQty`` 가 보존되는지, (마) event_filter 로 AS1 을 고르면 AS1 프레임이 filled 포트에
도달하는지를 단언한다. 또한 체결 원장 리스너가 노드 마스터 등록 후에도 보존되는지
(SDK 가 키당 리스너 리스트로 바뀐 전제)와 core 선언 필드명 alias 를 확인한다.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

import pytest

from programgarden.context import ExecutionContext
from programgarden.executor import RealOrderEventNodeExecutor

from programgarden_finance.ls.overseas_stock.real.AS0.blocks import (
    AS0RealResponse,
    AS0RealResponseBody,
    AS0RealResponseHeader,
)
from programgarden_finance.ls.overseas_stock.real.AS1.blocks import (
    AS1RealResponse,
    AS1RealResponseBody,
    AS1RealResponseHeader,
)
from programgarden_finance.ls.overseas_stock.real.AS2.blocks import (
    AS2RealResponse,
    AS2RealResponseBody,
    AS2RealResponseHeader,
)
from programgarden_finance.ls.overseas_stock.real.AS3.blocks import (
    AS3RealResponse,
    AS3RealResponseBody,
    AS3RealResponseHeader,
)
from programgarden_finance.ls.overseas_stock.real.AS4.blocks import (
    AS4RealResponse,
    AS4RealResponseBody,
    AS4RealResponseHeader,
)
from programgarden_finance.ls.korea_stock.real.SC1.blocks import SC1RealResponseBody


# ──────────────────────────────────────────────────────────────────────────
# 프레임 빌더 — AS 바디는 str/int/float 혼합이라 타입별 기본값으로 채운 뒤
# 관심 필드만 덮어쓴다. 필드명이 하나라도 틀리면 _body 가 단언으로 깨진다.
# ──────────────────────────────────────────────────────────────────────────

_AS_MODELS = {
    "AS0": (AS0RealResponse, AS0RealResponseHeader, AS0RealResponseBody),
    "AS1": (AS1RealResponse, AS1RealResponseHeader, AS1RealResponseBody),
    "AS2": (AS2RealResponse, AS2RealResponseHeader, AS2RealResponseBody),
    "AS3": (AS3RealResponse, AS3RealResponseHeader, AS3RealResponseBody),
    "AS4": (AS4RealResponse, AS4RealResponseHeader, AS4RealResponseBody),
}


def _body(tr_cd: str, **overrides: Any):
    body_model = _AS_MODELS[tr_cd][2]
    payload: Dict[str, Any] = {}
    for name, field in body_model.model_fields.items():
        ann = field.annotation
        if ann is int:
            payload[name] = 0
        elif ann is float:
            payload[name] = 0.0
        else:
            payload[name] = ""
    unknown = set(overrides) - set(payload)
    assert not unknown, f"{tr_cd} 바디에 없는 필드명: {sorted(unknown)}"
    payload.update(overrides)
    return body_model.model_validate(payload)


def _frame(tr_cd: str, *, with_header: bool = True, **overrides: Any):
    response_model, header_model, _ = _AS_MODELS[tr_cd]
    header = header_model(tr_cd=tr_cd) if with_header else None
    return response_model(
        header=header,
        body=_body(tr_cd, **overrides),
        rsp_cd="",
        rsp_msg="",
    )


# ──────────────────────────────────────────────────────────────────────────
# SDK 모양을 흉내 낸 real client. 🔴 새 SDK 는 키당 리스너를 **리스트로 append**
# 한다(real_base._on_message). 원장 리스너를 노드 마스터가 덮어쓰지 않는지 보려면
# 가짜도 append 여야 한다.
# ──────────────────────────────────────────────────────────────────────────

class _FakeStream:
    def __init__(self, tr_cd: str, registry: Dict[str, List[Any]]):
        self._tr_cd = tr_cd
        self._registry = registry

    def _register(self, listener):
        self._registry.setdefault(self._tr_cd, []).append(listener)
        return listener

    def __getattr__(self, name: str):
        if name == f"on_{self._tr_cd.lower()}_message":
            return self._register
        raise AttributeError(name)


class _FakeRealClient:
    def __init__(self, available: Optional[List[str]] = None):
        self.listeners: Dict[str, List[Any]] = {}
        self.connect_calls = 0
        self._available = tuple(available) if available is not None else ("AS0", "AS1", "AS2", "AS3", "AS4")
        for tr_cd in self._available:
            setattr(self, tr_cd, self._make_factory(tr_cd))

    def _make_factory(self, tr_cd: str):
        def factory():
            return _FakeStream(tr_cd, self.listeners)
        return factory

    async def is_connected(self) -> bool:
        return self.connect_calls > 0

    async def connect(self) -> None:
        self.connect_calls += 1

    def dispatch(self, tr_cd: str, frame) -> None:
        """SDK 디스패치 흉내 — tr_cd 키에 등록된 **모든** 리스너를 호출."""
        for listener in list(self.listeners.get(tr_cd, [])):
            listener(frame)


class _FakeOverseasStock:
    def __init__(self, real_client):
        self._real = real_client

    def real(self):
        return self._real


class _FakeLS:
    def __init__(self, real_client):
        self._os = _FakeOverseasStock(real_client)

    def overseas_stock(self):
        return self._os


def _context() -> ExecutionContext:
    ctx = ExecutionContext(job_id="job-as", workflow_id="wf-as")
    ctx.notified: List[Dict[str, Any]] = []            # type: ignore[attr-defined]
    ctx.emitted: List[Dict[str, Any]] = []             # type: ignore[attr-defined]
    ctx.fill_price_updates: List[Dict[str, Any]] = []  # type: ignore[attr-defined]
    ctx.logs: List[tuple] = []                         # type: ignore[attr-defined]

    async def _notify(node_id, node_type, outputs, **kwargs):
        ctx.notified.append({"node_id": node_id, "node_type": node_type, "outputs": outputs})

    async def _emit(**kwargs):
        ctx.emitted.append(kwargs)

    def _update_fill_price(order_no, order_date, fill_price):
        ctx.fill_price_updates.append(
            {"order_no": order_no, "order_date": order_date, "fill_price": fill_price}
        )
        return True

    def _log(level, message, node_id=None, *args, **kwargs):
        ctx.logs.append((level, message, node_id))

    ctx.notify_output_update = _notify          # type: ignore[assignment]
    ctx.emit_event = _emit                      # type: ignore[assignment]
    ctx.update_workflow_order_fill_price = _update_fill_price  # type: ignore[assignment]
    ctx.log = _log                              # type: ignore[assignment]
    return ctx


async def _drain(cycles: int = 5) -> None:
    for _ in range(cycles):
        await asyncio.sleep(0)


async def _subscribe(ctx, real_client, event_filter="all", node_id="order_event", stay_connected=True):
    executor = RealOrderEventNodeExecutor()
    return await executor._ls_stock_order_event(
        _FakeLS(real_client),
        node_id,
        {},
        ctx,
        stay_connected,
        event_filter,
    )


# ──────────────────────────────────────────────────────────────────────────
# 1. AS1 계열 바디는 AS0 와 **다른** 필드 집합을 쓴다 (결함의 근거)
# ──────────────────────────────────────────────────────────────────────────

class TestBodyShapes:
    def test_as0_has_no_fill_fields(self):
        """AS0 는 주문접수 TR — 체결/정정확인/취소확인/거부 필드 선언 자체가 없다."""
        fields = set(AS0RealResponseBody.model_fields)
        for absent in ("sExecQty", "sExecPrc", "sExecNO", "sExecTime",
                       "sMdfyCnfQty", "sCancCnfQty", "sRjtQty", "sUnercQty"):
            assert absent not in fields, f"AS0 에 {absent} 가 생겼다 — 파서 재확인 필요"

    def test_as1_family_has_execution_fields(self):
        """AS1~AS4 는 execution-shape 필드를 공유한다(module docstring: mirrors AS1)."""
        expected = {"sExecQty", "sExecPrc", "sExecNO", "sExecTime",
                    "sMdfyCnfQty", "sMdfyCnfPrc", "sCancCnfQty", "sRjtQty", "sUnercQty"}
        for model in (AS1RealResponseBody, AS2RealResponseBody,
                      AS3RealResponseBody, AS4RealResponseBody):
            assert expected <= set(model.model_fields), model.__name__
        # AS1 계열에는 주문시각(sOrdTime)이 없다 — 시각은 sExecTime/sRcptExecTime 뿐.
        assert "sOrdTime" not in set(AS1RealResponseBody.model_fields)
        # 반대로 AS0 에는 sOrdTime 이 있다.
        assert "sOrdTime" in set(AS0RealResponseBody.model_fields)

    def test_as2_as3_as4_share_as1_parsed_field_set(self):
        """파서가 읽는 필드는 AS1~AS4 에 **모두** 있다(계열 파서 하나로 충분).

        관측(SDK 2026-09-12): AS1/AS2/AS3 는 108개 필드로 완전히 동일하고, AS4 는
        103개 — 뒤쪽 잔고/증거금 5개(sOrdAbleSubstAmt·sMgntrnCode·sRuseAbleAmt·
        sCsgnSubstMgn·sOrdAbleMny)를 빼고 선언한다. 그 5개는 파서가 읽지 않으므로
        계열 파서 공유에 영향이 없다. 중요한 건 파서가 실제로 읽는 필드의 공통 존재다.
        """
        parsed = {
            "sOrdxctPtnCode", "sOrdMktCode", "sShtnIsuNo", "sIsuNo", "sStdIsuNo",
            "sIsuNm", "sOrdNo", "sOrgOrdNo", "sBnsTp", "sOrdQty", "sOrdPrc",
            "sExecQty", "sExecPrc", "sUnercQty", "sExecNO", "sExecTime",
            "sRcptExecTime", "sMdfyCnfQty", "sMdfyCnfPrc", "sCancCnfQty",
            "sRjtQty", "sRjtRsn",
        }
        for model in (AS1RealResponseBody, AS2RealResponseBody,
                      AS3RealResponseBody, AS4RealResponseBody):
            assert parsed <= set(model.model_fields), (
                model.__name__, sorted(parsed - set(model.model_fields))
            )
        # AS1/AS2/AS3 는 완전히 동일, AS4 만 뒤쪽 잔고/증거금 필드 5개를 뺀다.
        assert list(AS2RealResponseBody.model_fields) == list(AS1RealResponseBody.model_fields)
        assert list(AS3RealResponseBody.model_fields) == list(AS1RealResponseBody.model_fields)
        assert set(AS1RealResponseBody.model_fields) - set(AS4RealResponseBody.model_fields) == {
            "sOrdAbleSubstAmt", "sMgntrnCode", "sRuseAbleAmt", "sCsgnSubstMgn", "sOrdAbleMny",
        }


# ──────────────────────────────────────────────────────────────────────────
# 2. 스트림별 파서
# ──────────────────────────────────────────────────────────────────────────

class TestAs0Parser:
    def test_reads_as0_acceptance_fields(self):
        body = _body(
            "AS0",
            sOrdxctPtnCode="01",
            sOrdMktCode="82",
            sShtnIsuNo="AAPL",
            sIsuNo="82AAPL",
            sIsuNm="애플",
            sOrdNo=231,
            sOrgOrdNo=0,
            sBnsTp="2",
            sOrdQty="10",
            sOrdPrc=180.5,
            sOrdTime="093015",
            sOrgOrdUnercQty=3.0,
            sOrgOrdMdfyQty=1.0,
            sOrgOrdCancQty=0.0,
        )
        event = RealOrderEventNodeExecutor._parse_overseas_stock_as0_event(body)

        assert event["tr_cd"] == "AS0"
        assert event["event_code"] == "01"
        assert event["symbol"] == "AAPL"
        assert event["symbol_full_code"] == "82AAPL"
        assert event["symbol_name"] == "애플"
        assert event["order_no"] == 231
        assert event["side"] == "2"
        assert event["order_qty"] == 10
        assert event["order_price"] == 180.5
        assert event["order_time"] == "093015"
        assert event["market_code"] == "82"
        assert event["exchange"] == "NASDAQ"       # 82 → NASDAQ (원장 경로와 같은 맵)
        assert event["orig_order_remain_qty"] == 3

    def test_does_not_invent_fill_fields(self):
        event = RealOrderEventNodeExecutor._parse_overseas_stock_as0_event(
            _body("AS0", sOrdNo=231, sOrdQty="10", sOrdPrc=180.5)
        )
        for key in ("filled_qty", "filled_price", "remain_qty"):
            assert key not in event, f"AS0 에 없는 {key} 를 지어냈다"
            assert event[f"{key}_unavailable_reason"] == "as0_order_acceptance_frame_has_no_fill_fields"

    def test_unknown_market_code_does_not_invent_exchange(self):
        event = RealOrderEventNodeExecutor._parse_overseas_stock_as0_event(
            _body("AS0", sOrdMktCode="99")
        )
        assert "exchange" not in event
        assert event["exchange_unavailable_reason"] == "overseas_stock_market_code_not_in_known_exchange_map"
        assert event["market_code"] == "99"        # 원값은 그대로 싣는다

    def test_empty_price_does_not_raise(self):
        event = RealOrderEventNodeExecutor._parse_overseas_stock_as0_event(_body("AS0"))
        assert event["order_price"] == 0.0
        assert event["order_qty"] == 0
        assert event["symbol"] == ""


class TestAs1FamilyParser:
    def test_reads_as1_execution_fields(self):
        body = _body(
            "AS1",
            sOrdxctPtnCode="11",
            sOrdMktCode="81",
            sShtnIsuNo="AAPL",
            sIsuNo="82AAPL",
            sStdIsuNo="US0378331005",
            sIsuNm="애플",
            sOrdNo=1234567,
            sOrgOrdNo=0,
            sBnsTp="2",
            sOrdQty=10.0,
            sOrdPrc=180.0,
            sExecQty=4.0,
            sExecPrc=181.25,
            sUnercQty=6.0,
            sExecNO="E99",
            sExecTime="093015",
        )
        event = RealOrderEventNodeExecutor._parse_overseas_stock_fill_family_event(body, "AS1")

        assert event["tr_cd"] == "AS1"
        assert event["symbol"] == "AAPL"
        assert event["symbol_std_code"] == "US0378331005"
        assert event["order_no"] == 1234567
        assert event["side"] == "2"
        assert event["order_qty"] == 10
        assert event["order_price"] == 180.0
        # 🔴 체결가/체결수량은 sExecPrc/sExecQty 다 (주문가/주문수량이 아니다)
        assert event["filled_qty"] == 4
        assert event["filled_price"] == 181.25
        assert event["remain_qty"] == 6
        assert event["fill_no"] == "E99"
        assert event["fill_time"] == "093015"
        assert event["market_code"] == "81"
        assert event["exchange"] == "NYSE"         # 81 → NYSE

    def test_fractional_exec_qty_is_preserved(self):
        """소수점 체결수량(prod 관측 IBM 0.847972주)은 int() 절단 없이 보존된다."""
        body = _body("AS1", sOrdNo=1, sExecQty=0.532, sExecPrc=181.25)
        event = RealOrderEventNodeExecutor._parse_overseas_stock_fill_family_event(body, "AS1")
        assert event["filled_qty"] == 0.532
        assert isinstance(event["filled_qty"], float)

    def test_does_not_pretend_to_know_order_time(self):
        """AS1 계열에는 주문시각 필드가 없다 — 체결시각으로 채우지 않는다."""
        body = _body("AS1", sExecTime="093015")
        event = RealOrderEventNodeExecutor._parse_overseas_stock_fill_family_event(body, "AS1")
        assert "order_time" not in event
        assert event["order_time_unavailable_reason"] == "overseas_stock_fill_family_frame_has_no_order_time_field"
        assert event["fill_time"] == "093015"

    def test_fill_time_falls_back_to_rcpt_exec_time(self):
        body = _body("AS1", sExecTime="", sRcptExecTime="093020")
        event = RealOrderEventNodeExecutor._parse_overseas_stock_fill_family_event(body, "AS1")
        assert event["fill_time"] == "093020"

    def test_as2_modify_confirm_fields(self):
        body = _body("AS2", sOrdNo=1, sMdfyCnfQty=7.0, sMdfyCnfPrc=182.0)
        event = RealOrderEventNodeExecutor._parse_overseas_stock_fill_family_event(body, "AS2")
        assert event["tr_cd"] == "AS2"
        assert event["modified_qty"] == 7
        assert event["modified_price"] == 182.0

    def test_as3_cancel_confirm_fields(self):
        body = _body("AS3", sOrdNo=1, sCancCnfQty=5.0)
        event = RealOrderEventNodeExecutor._parse_overseas_stock_fill_family_event(body, "AS3")
        assert event["tr_cd"] == "AS3"
        assert event["cancelled_qty"] == 5

    def test_as4_reject_fields(self):
        body = _body("AS4", sOrdNo=1, sRjtQty=10.0, sRjtRsn="한도초과")
        event = RealOrderEventNodeExecutor._parse_overseas_stock_fill_family_event(body, "AS4")
        assert event["tr_cd"] == "AS4"
        assert event["rejected_qty"] == 10
        assert event["reject_reason"] == "한도초과"


# ──────────────────────────────────────────────────────────────────────────
# 3. 리스너 등록 — 어떤 키로 등록되는가
# ──────────────────────────────────────────────────────────────────────────

class TestStreamRegistration:
    @pytest.mark.asyncio
    async def test_all_five_streams_get_a_listener(self):
        ctx = _context()
        real_client = _FakeRealClient()

        result = await _subscribe(ctx, real_client, event_filter="all")
        await _drain()

        # SDK 리스너 키 — 종전에는 'AS0' 하나뿐이라 AS1~AS4 프레임이 버려졌다.
        assert sorted(real_client.listeners) == ["AS0", "AS1", "AS2", "AS3", "AS4"]
        for tr_cd in ("AS0", "AS1", "AS2", "AS3", "AS4"):
            handlers = ctx.get_order_event_handlers("overseas_stock", tr_cd)
            assert [h[0] for h in handlers] == ["order_event"], tr_cd
        assert result["status"] == "subscribed"
        assert result["subscribed_streams"] == ["AS0", "AS1", "AS2", "AS3", "AS4"]
        assert "unavailable_streams" not in result
        # 마스터가 스트림별로 저장된다 (정리 경로가 이것만 뗀다).
        assert set(ctx.get_order_event_masters("overseas_stock")) == {"AS0", "AS1", "AS2", "AS3", "AS4"}

    @pytest.mark.asyncio
    async def test_filtered_node_registers_only_its_stream(self):
        ctx = _context()
        real_client = _FakeRealClient()

        result = await _subscribe(ctx, real_client, event_filter="AS1")
        await _drain()

        assert result["subscribed_streams"] == ["AS1"]
        assert ctx.get_order_event_handlers("overseas_stock", "AS1")
        for tr_cd in ("AS0", "AS2", "AS3", "AS4"):
            assert ctx.get_order_event_handlers("overseas_stock", tr_cd) == []
        # 마스터는 그래도 다섯 개 전부 — 뒤에 붙는 다른 filter 노드를 위해서다.
        assert sorted(real_client.listeners) == ["AS0", "AS1", "AS2", "AS3", "AS4"]

    @pytest.mark.asyncio
    async def test_unknown_event_filter_is_an_error(self):
        ctx = _context()
        real_client = _FakeRealClient()

        result = await _subscribe(ctx, real_client, event_filter="AS9")

        assert "error" in result
        assert real_client.listeners == {}

    @pytest.mark.asyncio
    async def test_missing_sdk_stream_is_reported_not_guessed(self):
        """SDK 에 등록 API 가 없는 스트림은 조용히 넘어가지 않고 사실로 보고된다."""
        ctx = _context()
        real_client = _FakeRealClient(available=["AS0", "AS1", "AS2"])

        result = await _subscribe(ctx, real_client, event_filter="all")
        await _drain()

        assert sorted(real_client.listeners) == ["AS0", "AS1", "AS2"]
        assert result["unavailable_streams"] == ["AS3", "AS4"]
        warnings = [m for lvl, m, _ in ctx.logs if lvl == "warning"]
        assert any("AS3, AS4" in m for m in warnings), warnings

    @pytest.mark.asyncio
    async def test_second_node_picking_missing_stream_is_not_a_silent_success(self):
        """디렉티브(3): 첫 노드가 마스터를 건 뒤, 두 번째 노드가 SDK 에 없는 스트림을
        filter 로 고르면 status='subscribed' 인데 이벤트 0건인 조용한 실패가 된다.
        저장된 masters 키로 노드별 확인해 unavailable_streams + warning 을 싣는다."""
        ctx = _context()
        real_client = _FakeRealClient(available=["AS0", "AS1", "AS2"])

        first = await _subscribe(ctx, real_client, event_filter="AS1", node_id="node_fill")
        assert "unavailable_streams" not in first   # AS1 은 등록됨

        second = await _subscribe(ctx, real_client, event_filter="AS4", node_id="node_reject")
        assert real_client.connect_calls == 1        # 마스터는 첫 노드만 등록
        assert second["subscribed_streams"] == ["AS4"]
        assert second["unavailable_streams"] == ["AS4"]
        warnings = [m for lvl, m, _ in ctx.logs if lvl == "warning"]
        assert any("AS4" in m for m in warnings), warnings


# ──────────────────────────────────────────────────────────────────────────
# 4. 체결 원장 리스너 보존 (디렉티브 2 — SDK 키당 리스너 리스트)
# ──────────────────────────────────────────────────────────────────────────

class TestLedgerListenerPreserved:
    @pytest.mark.asyncio
    async def test_node_master_does_not_clobber_pre_registered_ledger_listener(self):
        """같은 Real 객체에 체결 원장 리스너가 먼저 걸려 있어도, 노드 마스터 등록 후
        두 리스너가 **모두** 남고 둘 다 호출된다(덮어쓰기 금지)."""
        ctx = _context()
        real_client = _FakeRealClient()

        ledger_as0: List[Any] = []
        ledger_as1: List[Any] = []
        real_client.AS0().on_as0_message(lambda resp: ledger_as0.append(resp))
        real_client.AS1().on_as1_message(lambda resp: ledger_as1.append(resp))

        await _subscribe(ctx, real_client, event_filter="all")
        await _drain()

        # AS0/AS1 키에는 원장 리스너 + 노드 마스터 둘 다.
        assert len(real_client.listeners["AS0"]) == 2
        assert len(real_client.listeners["AS1"]) == 2
        # 노드만 건 스트림은 하나.
        assert len(real_client.listeners["AS2"]) == 1
        # 저장된 마스터는 노드 마스터뿐(원장 리스너는 아니다).
        assert set(ctx.get_order_event_masters("overseas_stock")) == {"AS0", "AS1", "AS2", "AS3", "AS4"}

        # AS1 체결 프레임을 배달 → 원장 리스너 **와** 노드 마스터 둘 다 동작.
        real_client.dispatch(
            "AS1", _frame("AS1", sOrdNo=1, sExecQty=1.0, sExecPrc=100.0, sShtnIsuNo="AAPL")
        )
        await _drain()

        assert len(ledger_as1) == 1, "원장 리스너가 노드 마스터에 덮어쓰여 사라졌다"
        assert ctx.get_output("order_event", "filled") is not None, "노드 마스터가 동작하지 않았다"


# ──────────────────────────────────────────────────────────────────────────
# 5. 종단 — 프레임이 실제로 포트까지 도달하는가
# ──────────────────────────────────────────────────────────────────────────

class TestFrameReachesPorts:
    @pytest.mark.asyncio
    async def test_as1_fill_frame_reaches_filled_port(self):
        ctx = _context()
        real_client = _FakeRealClient()
        await _subscribe(ctx, real_client, event_filter="all")

        real_client.dispatch(
            "AS1",
            _frame(
                "AS1",
                sOrdxctPtnCode="11",
                sOrdMktCode="82",
                sShtnIsuNo="AAPL",
                sIsuNm="애플",
                sOrdNo=1234567,
                sBnsTp="2",
                sOrdQty=10.0,
                sOrdPrc=180.0,
                sExecQty=10.0,
                sExecPrc=181.25,
                sUnercQty=0.0,
                sExecNO="E99",
                sExecTime="093015",
            ),
        )
        await _drain()

        output = ctx.get_output("order_event", "filled")
        assert output is not None, "AS1 프레임이 filled 포트에 도달하지 않았다"
        assert output["symbol"] == "AAPL"
        assert output["filled_qty"] == 10
        assert output["filled_price"] == 181.25     # 체결가 = sExecPrc (주문가 아님)
        assert output["status"] == "체결"
        port_notifications = [n for n in ctx.notified if "filled" in n["outputs"]]
        assert len(port_notifications) == 1
        assert port_notifications[0]["node_type"] == "RealOrderEventNode"
        assert [e["event_type"] for e in ctx.emitted] == ["order_event"]

    @pytest.mark.asyncio
    async def test_as1_fill_updates_order_fill_price_with_exec_price_and_local_date(self):
        """🔴 체결가 갱신은 sExecPrc(체결가)로, 주문일자는 로컬 오늘(AS1 엔 일자 필드
        없음 — 원장 경로와 같은 규약)로 한다."""
        ctx = _context()
        real_client = _FakeRealClient()
        await _subscribe(ctx, real_client, event_filter="all")

        real_client.dispatch(
            "AS1",
            _frame("AS1", sOrdNo=1234567, sOrdPrc=180.0, sExecQty=10.0, sExecPrc=181.25),
        )
        await _drain()

        assert ctx.fill_price_updates == [
            {
                "order_no": "1234567",
                "order_date": datetime.now().strftime("%Y%m%d"),
                "fill_price": 181.25,       # 주문가 180.0 이 아니라 체결가 181.25
            }
        ]

    @pytest.mark.asyncio
    async def test_fill_price_update_skipped_without_order_no(self):
        ctx = _context()
        real_client = _FakeRealClient()
        await _subscribe(ctx, real_client, event_filter="all")

        real_client.dispatch("AS1", _frame("AS1", sOrdNo=0, sExecQty=10.0, sExecPrc=181.25))
        await _drain()

        assert ctx.fill_price_updates == []

    @pytest.mark.asyncio
    async def test_as0_frame_reaches_accepted_port_without_fake_fill(self):
        ctx = _context()
        real_client = _FakeRealClient()
        await _subscribe(ctx, real_client, event_filter="all")

        real_client.dispatch(
            "AS0",
            _frame(
                "AS0",
                sOrdxctPtnCode="01",
                sOrdMktCode="82",
                sShtnIsuNo="TSLA",
                sIsuNm="테슬라",
                sOrdNo=7654321,
                sBnsTp="1",
                sOrdQty="3",
                sOrdPrc=250.0,
                sOrdTime="090015",
            ),
        )
        await _drain()

        output = ctx.get_output("order_event", "accepted")
        assert output is not None
        assert output["symbol"] == "TSLA"
        assert output["order_qty"] == 3
        assert output["order_price"] == 250.0
        assert output["order_time"] == "090015"
        assert output["status"] == "주문접수"
        assert "filled_qty" not in output and "filled_price" not in output
        assert ctx.fill_price_updates == []

    @pytest.mark.parametrize(
        "tr_cd,port,status",
        [
            ("AS2", "modified", "정정"),
            ("AS3", "cancelled", "취소확인"),
            ("AS4", "rejected", "거부"),
        ],
    )
    @pytest.mark.asyncio
    async def test_as2_as3_as4_reach_their_own_ports(self, tr_cd, port, status):
        ctx = _context()
        real_client = _FakeRealClient()
        await _subscribe(ctx, real_client, event_filter="all")

        real_client.dispatch(tr_cd, _frame(tr_cd, sOrdNo=1, sShtnIsuNo="AAPL", sBnsTp="2"))
        await _drain()

        output = ctx.get_output("order_event", port)
        assert output is not None, f"{tr_cd} 프레임이 {port} 포트에 도달하지 않았다"
        assert output["tr_cd"] == tr_cd
        assert output["status"] == status
        assert output["symbol"] == "AAPL"

    @pytest.mark.asyncio
    async def test_event_filter_as1_only_sees_as1(self):
        """(마) event_filter 로 AS1 을 고르면 AS1 프레임이 filled 포트에 도달하고,
        다른 스트림 프레임은 이 노드로 오지 않는다."""
        ctx = _context()
        real_client = _FakeRealClient()
        await _subscribe(ctx, real_client, event_filter="AS1", node_id="only_fills")

        real_client.dispatch("AS4", _frame("AS4", sOrdNo=2, sRjtQty=1.0))   # 이 노드 무관
        real_client.dispatch("AS1", _frame("AS1", sOrdNo=1, sExecQty=1.0, sExecPrc=100.0, sShtnIsuNo="AAPL"))
        await _drain()

        assert ctx.get_output("only_fills", "rejected") is None
        filled = ctx.get_output("only_fills", "filled")
        assert filled is not None and filled["order_no"] == 1

    @pytest.mark.asyncio
    async def test_header_none_frame_falls_back_to_registered_stream(self):
        """헤더 없이 body 만 있는 프레임은 등록된 스트림을 TR 로 삼는다(종전 'AS0' 고정 결함)."""
        ctx = _context()
        real_client = _FakeRealClient()
        await _subscribe(ctx, real_client, event_filter="all")

        real_client.dispatch(
            "AS1",
            _frame("AS1", with_header=False, sOrdNo=1, sExecQty=5.0, sExecPrc=99.0, sShtnIsuNo="AAPL"),
        )
        await _drain()

        output = ctx.get_output("order_event", "filled")
        assert output is not None, "header=None 프레임이 filled 포트에 도달하지 않았다"
        assert output["tr_cd"] == "AS1"
        assert output["filled_qty"] == 5

    @pytest.mark.asyncio
    async def test_body_less_frame_is_skipped_not_zero_filled(self):
        ctx = _context()
        real_client = _FakeRealClient()
        await _subscribe(ctx, real_client, event_filter="all")

        broken = AS1RealResponse(
            header=AS1RealResponseHeader(tr_cd="AS1"),
            body=None,
            rsp_cd="",
            rsp_msg="",
            error_msg="validation failed",
        )
        real_client.dispatch("AS1", broken)
        await _drain()

        assert ctx.get_output("order_event", "filled") is None
        assert ctx.fill_price_updates == []
        assert any(lvl == "warning" for lvl, _, _ in ctx.logs)


# ──────────────────────────────────────────────────────────────────────────
# 6. core 선언 필드명 alias (과제 B) — 세 파서 각각 1건
# ──────────────────────────────────────────────────────────────────────────

class TestOrderEventAliases:
    """선언(order_id/quantity/filled_quantity/price)과 런타임(order_no/order_qty/
    filled_qty/order_price)의 이름 불일치를 alias 로 메운다. 의미 1:1 인 것만,
    원 키가 있을 때만."""

    def test_overseas_stock_fill_family_aliases(self):
        body = _body("AS1", sOrdNo=1234567, sOrdQty=10.0, sOrdPrc=180.0, sExecQty=4.0, sExecPrc=181.25)
        event = RealOrderEventNodeExecutor._parse_overseas_stock_fill_family_event(body, "AS1")
        assert event["order_id"] == event["order_no"] == 1234567
        assert event["quantity"] == event["order_qty"] == 10
        assert event["filled_quantity"] == event["filled_qty"] == 4
        assert event["price"] == event["order_price"] == 180.0

    def test_korea_sc1_family_aliases(self):
        body = SC1RealResponseBody.model_validate(
            {name: "" for name in SC1RealResponseBody.model_fields}
            | {"ordno": "1234567", "ordqty": "10", "ordprc": "73500", "execqty": "4", "execprc": "73400"}
        )
        event = RealOrderEventNodeExecutor._parse_korea_sc1_family_event(body, "SC1")
        assert event["order_id"] == event["order_no"] == "1234567"
        assert event["quantity"] == event["order_qty"] == 10
        assert event["filled_quantity"] == event["filled_qty"] == 4
        assert event["price"] == event["order_price"] == 73500.0

    def test_tc3_aliases(self):
        # TC3 파서는 getattr 기반이라 SimpleNamespace 로 충분(선물 SDK 블록 불필요).
        # TC3 은 order_qty/order_price 를 싣지 않으므로 quantity/price alias 는 없고,
        # order_id(←order_no)·filled_quantity(←filled_qty)만 생긴다.
        body = SimpleNamespace(
            svc_id="", is_cd="ESZ5", ordr_no="A1", ordr_dt="20260912",
            orgn_ordr_no="", s_b_ccd="2", ccls_q=3, ccls_prc=5000.0,
            ccls_no="C1", ccls_tm="093015", avg_byng_uprc=0.0, clr_pl_amt=0.0,
            ent_fee=0.0, crncy_cd="USD",
        )
        event = RealOrderEventNodeExecutor()._parse_tc3_data(body)
        assert event["order_id"] == event["order_no"] == "A1"
        assert event["filled_quantity"] == event["filled_qty"] == 3
        # TC3 에 없는 원 키는 alias 도 만들지 않는다(지어내기 금지).
        assert "quantity" not in event and "price" not in event
