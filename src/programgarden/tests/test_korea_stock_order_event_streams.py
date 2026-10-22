"""E1: 국내주식 주문이벤트 노드(KoreaStockRealOrderEventNode)의 스트림 등록·파서.

수정 전 결함 두 가지:

1. **파서가 존재하지 않는 필드명을 읽었다.** `_ls_korea_stock_order_event` 의
   핸들러는 ``OrdNo``/``OrdQty``/``OrdPrc``/``ExecQty``/``ExecPrc``/``UnercQty``/
   ``OrdTime``/``BnsTpCode``/``IsuNm``/``shtnIsuNo`` 같은 PascalCase 를 읽었는데,
   SC0~SC4 바디의 실제 필드명은 전부 소문자다(SC0: ``ordno``/``ordqty``/
   ``ordprice``/``shtcode``/``hname``/``ordtm``/``bnstp``, SC1 계열: ``ordno``/
   ``ordqty``/``ordprc``/``execqty``/``execprc``/``unercqty``/``exectime``/
   ``execno``/``shtnIsuno``/``Isunm``/``bnstp``). pydantic v2 는 기본
   ``extra='ignore'`` 라 그런 속성이 아예 없고, getattr 기본값이 그대로 나가
   **모든 필드가 0/빈값**이었다.

2. **SC1~SC4 프레임은 노드에 도달조차 못 했다.** 리스너를 ``SC0()
   .on_sc0_message(...)`` 하나만 걸고 핸들러 안에서 ``tr_cd`` 로 SC1~SC4 를
   분기했는데, SDK 디스패치는 프레임 헤더 ``tr_cd`` **정확일치 키**로만 이뤄진다
   (``ls/real_base.py`` ``self._on_message_listeners.get(tr_cd, None)``).

이 테스트는 (가) 스트림마다 리스너가 실제로 등록되는지, (나) 스트림별 파서가
SDK 의 실제 필드명을 읽는지, (다) SC0 에 없는 체결 필드를 0 으로 지어내지 않는지를
단언한다. 프레임은 SDK 응답 모델(``SC0RealResponse``/``SCnRealResponse``)로 직접
만들어, 필드명이 하나라도 틀리면 테스트가 깨지게 한다.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

import pytest

from programgarden.context import ExecutionContext
from programgarden.executor import RealOrderEventNodeExecutor

from programgarden_finance.ls.korea_stock.real.SC0.blocks import (
    SC0RealResponse,
    SC0RealResponseBody,
    SC0RealResponseHeader,
)
from programgarden_finance.ls.korea_stock.real.SC1.blocks import (
    SC1RealResponse,
    SC1RealResponseBody,
    SC1RealResponseHeader,
)
from programgarden_finance.ls.korea_stock.real.SC2.blocks import (
    SC2RealResponse,
    SC2RealResponseBody,
    SC2RealResponseHeader,
)
from programgarden_finance.ls.korea_stock.real.SC3.blocks import (
    SC3RealResponse,
    SC3RealResponseBody,
    SC3RealResponseHeader,
)
from programgarden_finance.ls.korea_stock.real.SC4.blocks import (
    SC4RealResponse,
    SC4RealResponseBody,
    SC4RealResponseHeader,
)


# ──────────────────────────────────────────────────────────────────────────
# 프레임 빌더 — 전 필드가 required(str) 라 ''로 채운 뒤 관심 필드만 덮어쓴다.
# ──────────────────────────────────────────────────────────────────────────

_SC_MODELS = {
    "SC0": (SC0RealResponse, SC0RealResponseHeader, SC0RealResponseBody),
    "SC1": (SC1RealResponse, SC1RealResponseHeader, SC1RealResponseBody),
    "SC2": (SC2RealResponse, SC2RealResponseHeader, SC2RealResponseBody),
    "SC3": (SC3RealResponse, SC3RealResponseHeader, SC3RealResponseBody),
    "SC4": (SC4RealResponse, SC4RealResponseHeader, SC4RealResponseBody),
}


def _body(tr_cd: str, **overrides: str):
    _, _, body_model = _SC_MODELS[tr_cd]
    payload: Dict[str, Any] = {name: "" for name in body_model.model_fields}
    unknown = set(overrides) - set(payload)
    assert not unknown, f"{tr_cd} 바디에 없는 필드명: {sorted(unknown)}"
    payload.update(overrides)
    return body_model.model_validate(payload)


def _frame(tr_cd: str, **overrides: str):
    response_model, header_model, _ = _SC_MODELS[tr_cd]
    return response_model(
        header=header_model(tr_cd=tr_cd),
        body=_body(tr_cd, **overrides),
        rsp_cd="",
        rsp_msg="",
    )


# ──────────────────────────────────────────────────────────────────────────
# SDK 모양을 흉내 낸 real client — 등록된 리스너 키를 그대로 보관한다.
# ──────────────────────────────────────────────────────────────────────────

class _FakeStream:
    """``real.SC1()`` 이 돌려주는 객체. ``on_sc1_message`` 만 갖는다."""

    def __init__(self, tr_cd: str, registry: Dict[str, Any]):
        self._tr_cd = tr_cd
        self._registry = registry

    def _register(self, listener):
        self._registry[self._tr_cd] = listener
        return listener

    def __getattr__(self, name: str):
        if name == f"on_{self._tr_cd.lower()}_message":
            return self._register
        raise AttributeError(name)


class _FakeRealClient:
    def __init__(self, available: Optional[List[str]] = None):
        self.listeners: Dict[str, Any] = {}
        self.connect_calls = 0
        self._available = tuple(available) if available is not None else ("SC0", "SC1", "SC2", "SC3", "SC4")
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


class _FakeKoreaStock:
    def __init__(self, real_client):
        self._real = real_client

    def real(self):
        return self._real


class _FakeLS:
    def __init__(self, real_client):
        self._korea = _FakeKoreaStock(real_client)

    def korea_stock(self):
        return self._korea


def _context() -> ExecutionContext:
    ctx = ExecutionContext(job_id="job-e1", workflow_id="wf-e1")
    ctx.notified: List[Dict[str, Any]] = []          # type: ignore[attr-defined]
    ctx.emitted: List[Dict[str, Any]] = []           # type: ignore[attr-defined]
    ctx.fill_price_updates: List[Dict[str, Any]] = []  # type: ignore[attr-defined]
    ctx.logs: List[tuple] = []                       # type: ignore[attr-defined]

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

    ctx.notify_output_update = _notify        # type: ignore[assignment]
    ctx.emit_event = _emit                    # type: ignore[assignment]
    ctx.update_workflow_order_fill_price = _update_fill_price  # type: ignore[assignment]
    ctx.log = _log                            # type: ignore[assignment]
    return ctx


async def _drain(cycles: int = 5) -> None:
    """``asyncio.run_coroutine_threadsafe`` 로 예약된 콜백까지 실제로 돌린다.

    핸들러는 동기 콜백이라 notify/emit 를 루프에 예약만 한다 — 한 틱으로는
    예약만 처리되고 코루틴 본문이 아직 안 돈다.
    """
    for _ in range(cycles):
        await asyncio.sleep(0)


async def _subscribe(ctx, real_client, event_filter="all", node_id="order_event", stay_connected=True):
    executor = RealOrderEventNodeExecutor()
    return await executor._ls_korea_stock_order_event(
        _FakeLS(real_client),
        node_id,
        {},
        ctx,
        stay_connected,
        event_filter,
    )


# ──────────────────────────────────────────────────────────────────────────
# 1. 종전 파서가 읽던 PascalCase 필드는 SDK 바디에 존재하지 않는다 (결함의 근거)
# ──────────────────────────────────────────────────────────────────────────

class TestOldFieldNamesDoNotExist:
    def test_sc0_body_has_no_pascal_case_fields(self):
        body = _body("SC0")
        for legacy in ("OrdNo", "OrdQty", "OrdPrc", "ExecQty", "ExecPrc",
                       "UnercQty", "OrdTime", "BnsTpCode", "IsuNm", "shtnIsuNo"):
            assert not hasattr(body, legacy), f"SC0 바디에 {legacy} 가 생겼다 — 파서 재확인 필요"

    def test_sc1_body_has_no_pascal_case_fields(self):
        body = _body("SC1")
        for legacy in ("OrdNo", "OrdQty", "OrdPrc", "ExecQty", "ExecPrc",
                       "UnercQty", "OrdTime", "BnsTpCode", "IsuNm", "shtnIsuNo"):
            assert not hasattr(body, legacy), f"SC1 바디에 {legacy} 가 생겼다 — 파서 재확인 필요"

    def test_sc2_sc3_sc4_share_the_sc1_body_model(self):
        """SC2~SC4 는 SC1RealResponseBody 를 상속한다 → SC1 계열 파서 하나로 충분."""
        assert issubclass(SC2RealResponseBody, SC1RealResponseBody)
        assert issubclass(SC3RealResponseBody, SC1RealResponseBody)
        assert issubclass(SC4RealResponseBody, SC1RealResponseBody)
        assert list(SC2RealResponseBody.model_fields) == list(SC1RealResponseBody.model_fields)

    def test_sc0_body_really_has_no_fill_fields(self):
        """SC0 는 주문접수 TR — 체결수량/체결가격/미체결수량 선언 자체가 없다."""
        fields = set(SC0RealResponseBody.model_fields)
        assert "execqty" not in fields
        assert "execprc" not in fields
        assert "unercqty" not in fields
        assert "execno" not in fields
        assert "exectime" not in fields
        # 반대로 SC1 계열에는 전부 있다.
        sc1_fields = set(SC1RealResponseBody.model_fields)
        assert {"execqty", "execprc", "unercqty", "execno", "exectime"} <= sc1_fields
        # 그리고 SC1 계열에는 주문시각(ordtm)이 없다.
        assert "ordtm" not in sc1_fields
        assert "ordtm" in fields


# ──────────────────────────────────────────────────────────────────────────
# 2. 스트림별 파서
# ──────────────────────────────────────────────────────────────────────────

class TestSc0Parser:
    def test_reads_sc0_lowercase_fields(self):
        body = _body(
            "SC0",
            ordchegb="01",
            marketgb="10",
            orgordno="0",
            expcode="KR7005930003",
            shtcode="A005930",
            hname="삼성전자",
            ordqty="10",
            ordprice="73500",
            ordno="1234567",
            ordtm="090015123",
            bnstp="2",
            orgordundrqty="3",
            orgordmdfyqty="2",
            ordordcancelqty="1",
        )
        event = RealOrderEventNodeExecutor._parse_korea_sc0_event(body)

        assert event["tr_cd"] == "SC0"
        assert event["event_code"] == "01"
        assert event["symbol"] == "005930"          # 'A' 접두어 제거
        assert event["symbol_short_code"] == "A005930"
        assert event["symbol_std_code"] == "KR7005930003"
        assert event["symbol_name"] == "삼성전자"
        assert event["order_no"] == "1234567"
        assert event["orig_order_no"] == "0"
        assert event["side"] == "2"
        assert event["order_qty"] == 10
        assert event["order_price"] == 73500.0
        assert event["order_time"] == "090015123"
        assert event["exchange"] == "KRX"
        assert event["market_code"] == "10"         # 상수 'KRX' 가 아니라 프레임 값
        assert event["orig_order_remain_qty"] == 3
        assert event["orig_order_modified_qty"] == 2
        assert event["orig_order_cancelled_qty"] == 1

    def test_does_not_invent_fill_fields(self):
        body = _body("SC0", ordno="1234567", ordqty="10", ordprice="73500")
        event = RealOrderEventNodeExecutor._parse_korea_sc0_event(body)

        for key in ("filled_qty", "filled_price", "remain_qty"):
            assert key not in event, f"SC0 에 없는 {key} 를 지어냈다"
            assert event[f"{key}_unavailable_reason"] == "sc0_order_acceptance_frame_has_no_fill_fields"

    def test_empty_price_does_not_raise(self):
        """해당 없는 이벤트는 ''를 싣는다 — float('') 로 터지면 안 된다."""
        event = RealOrderEventNodeExecutor._parse_korea_sc0_event(_body("SC0"))
        assert event["order_price"] == 0.0
        assert event["order_qty"] == 0
        assert event["symbol"] == ""


class TestSc1FamilyParser:
    def test_reads_sc1_lowercase_fields(self):
        body = _body(
            "SC1",
            ordxctptncode="11",
            shtnIsuno="A005930",
            Isuno="KR7005930003",
            Isunm="삼성전자",
            ordno="1234567",
            orgordno="0",
            bnstp="2",
            ordqty="10",
            ordprc="73500",
            execqty="4",
            execprc="73400",
            unercqty="6",
            execno="9876543",
            exectime="091532123",
            ordmktcode="10",
        )
        event = RealOrderEventNodeExecutor._parse_korea_sc1_family_event(body, "SC1")

        assert event["tr_cd"] == "SC1"
        assert event["event_code"] == "11"
        assert event["symbol"] == "005930"
        assert event["symbol_short_code"] == "A005930"
        assert event["symbol_std_code"] == "KR7005930003"
        assert event["symbol_name"] == "삼성전자"
        assert event["order_no"] == "1234567"
        assert event["side"] == "2"
        assert event["order_qty"] == 10
        assert event["order_price"] == 73500.0
        assert event["filled_qty"] == 4
        assert event["filled_price"] == 73400.0
        assert event["remain_qty"] == 6
        assert event["fill_no"] == "9876543"
        assert event["fill_time"] == "091532123"
        assert event["exchange"] == "KRX"
        assert event["market_code"] == "10"

    def test_does_not_pretend_to_know_order_time(self):
        """SC1 계열에는 주문시각 필드가 없다 — 체결시각으로 채우지 않는다."""
        body = _body("SC1", exectime="091532123")
        event = RealOrderEventNodeExecutor._parse_korea_sc1_family_event(body, "SC1")
        assert "order_time" not in event
        assert event["order_time_unavailable_reason"] == "sc1_family_frame_has_no_order_time_field"
        assert event["fill_time"] == "091532123"

    def test_sc2_modify_confirm_fields(self):
        body = _body("SC2", ordxctptncode="12", ordno="1234567",
                     mdfycnfqty="7", mdfycnfprc="73900")
        event = RealOrderEventNodeExecutor._parse_korea_sc1_family_event(body, "SC2")
        assert event["tr_cd"] == "SC2"
        assert event["modified_qty"] == 7
        assert event["modified_price"] == 73900.0

    def test_sc3_cancel_confirm_fields(self):
        body = _body("SC3", ordxctptncode="13", ordno="1234567", canccnfqty="5")
        event = RealOrderEventNodeExecutor._parse_korea_sc1_family_event(body, "SC3")
        assert event["tr_cd"] == "SC3"
        assert event["cancelled_qty"] == 5

    def test_sc4_reject_fields(self):
        body = _body("SC4", ordxctptncode="14", ordno="1234567", rjtqty="10")
        event = RealOrderEventNodeExecutor._parse_korea_sc1_family_event(body, "SC4")
        assert event["tr_cd"] == "SC4"
        assert event["rejected_qty"] == 10

    def test_non_standard_symbol_code_is_passed_through(self):
        """규약('A'/'J' + 6자리)에 안 맞으면 손대지 않는다."""
        body = _body("SC1", shtnIsuno="005930")
        event = RealOrderEventNodeExecutor._parse_korea_sc1_family_event(body, "SC1")
        assert event["symbol"] == "005930"
        assert event["symbol_short_code"] == "005930"

    def test_fractional_exec_qty_is_preserved(self):
        """소수점 체결수량은 int() 절단 없이 보존된다 (_qty_num 경로 고정).

        국내주식에 소수점 체결은 드물지만, 파서가 ``_qty_num`` 을 쓰는 한 int 절단
        회귀(0.5 → 0)가 생기면 체결 이벤트가 조용히 사라진다. 경로를 고정한다."""
        body = _body("SC1", ordno="1234567", execqty="0.5", execprc="73400")
        event = RealOrderEventNodeExecutor._parse_korea_sc1_family_event(body, "SC1")
        assert event["filled_qty"] == 0.5
        assert isinstance(event["filled_qty"], float)


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

        # SDK 리스너 키 — 종전에는 'SC0' 하나뿐이라 SC1~SC4 프레임이 버려졌다.
        assert sorted(real_client.listeners) == ["SC0", "SC1", "SC2", "SC3", "SC4"]
        # 노드 핸들러도 스트림마다 등록된다.
        for tr_cd in ("SC0", "SC1", "SC2", "SC3", "SC4"):
            handlers = ctx.get_order_event_handlers("korea_stock", tr_cd)
            assert [h[0] for h in handlers] == ["order_event"], tr_cd
        assert result["status"] == "subscribed"
        assert result["subscribed_streams"] == ["SC0", "SC1", "SC2", "SC3", "SC4"]
        assert "unavailable_streams" not in result

    @pytest.mark.asyncio
    async def test_filtered_node_registers_only_its_stream(self):
        ctx = _context()
        real_client = _FakeRealClient()

        result = await _subscribe(ctx, real_client, event_filter="SC1")
        await _drain()

        assert result["subscribed_streams"] == ["SC1"]
        assert ctx.get_order_event_handlers("korea_stock", "SC1")
        for tr_cd in ("SC0", "SC2", "SC3", "SC4"):
            assert ctx.get_order_event_handlers("korea_stock", tr_cd) == []
        # 마스터는 그래도 다섯 개 전부 — 뒤에 붙는 다른 filter 노드를 위해서다.
        assert sorted(real_client.listeners) == ["SC0", "SC1", "SC2", "SC3", "SC4"]

    @pytest.mark.asyncio
    async def test_second_node_with_other_filter_reuses_masters(self):
        ctx = _context()
        real_client = _FakeRealClient()

        await _subscribe(ctx, real_client, event_filter="SC1", node_id="node_fill")
        await _subscribe(ctx, real_client, event_filter="SC4", node_id="node_reject")
        await _drain()

        assert real_client.connect_calls == 1
        assert [h[0] for h in ctx.get_order_event_handlers("korea_stock", "SC1")] == ["node_fill"]
        assert [h[0] for h in ctx.get_order_event_handlers("korea_stock", "SC4")] == ["node_reject"]

    @pytest.mark.asyncio
    async def test_unknown_event_filter_is_an_error(self):
        ctx = _context()
        real_client = _FakeRealClient()

        result = await _subscribe(ctx, real_client, event_filter="SC9")

        assert "error" in result
        assert real_client.listeners == {}

    @pytest.mark.asyncio
    async def test_missing_sdk_stream_is_reported_not_guessed(self):
        """SDK 에 등록 API 가 없는 스트림은 조용히 넘어가지 않고 사실로 보고된다."""
        ctx = _context()
        real_client = _FakeRealClient(available=["SC0", "SC1", "SC2"])

        result = await _subscribe(ctx, real_client, event_filter="all")
        await _drain()

        assert sorted(real_client.listeners) == ["SC0", "SC1", "SC2"]
        assert result["unavailable_streams"] == ["SC3", "SC4"]
        warnings = [m for lvl, m, _ in ctx.logs if lvl == "warning"]
        assert any("SC3, SC4" in m for m in warnings), warnings


# ──────────────────────────────────────────────────────────────────────────
# 4. 종단 — 프레임이 실제로 포트까지 도달하는가
# ──────────────────────────────────────────────────────────────────────────

class TestFrameReachesPorts:
    @pytest.mark.asyncio
    async def test_sc1_fill_frame_reaches_filled_port(self):
        ctx = _context()
        real_client = _FakeRealClient()
        await _subscribe(ctx, real_client, event_filter="all")

        real_client.listeners["SC1"](
            _frame(
                "SC1",
                ordxctptncode="11",
                shtnIsuno="A005930",
                Isunm="삼성전자",
                ordno="1234567",
                bnstp="2",
                ordqty="10",
                ordprc="73500",
                execqty="10",
                execprc="73400",
                unercqty="0",
                execno="9876543",
                exectime="091532123",
                ordmktcode="10",
            )
        )
        await _drain()

        output = ctx.get_output("order_event", "filled")
        assert output is not None, "SC1 프레임이 filled 포트에 도달하지 않았다"
        assert output["symbol"] == "005930"
        assert output["filled_qty"] == 10
        assert output["filled_price"] == 73400.0
        assert output["status"] == "체결"
        # 구독 결과 알림과 이벤트 알림이 같은 큐에 섞이므로 순서를 가정하지 않는다.
        port_notifications = [n for n in ctx.notified if "filled" in n["outputs"]]
        assert len(port_notifications) == 1
        assert port_notifications[0]["node_type"] == "KoreaStockRealOrderEventNode"
        assert port_notifications[0]["outputs"]["filled"]["filled_price"] == 73400.0
        assert [e["event_type"] for e in ctx.emitted] == ["order_event"]

    @pytest.mark.asyncio
    async def test_sc1_fill_updates_order_fill_price_with_local_date(self):
        """프레임에 주문일자 필드가 없어 로컬 날짜를 쓴다 — 원장 쓰기 쪽과 같은 규약."""
        ctx = _context()
        real_client = _FakeRealClient()
        await _subscribe(ctx, real_client, event_filter="all")

        real_client.listeners["SC1"](
            _frame("SC1", ordno="1234567", execqty="10", execprc="73400")
        )
        await _drain()

        assert ctx.fill_price_updates == [
            {
                "order_no": "1234567",
                "order_date": datetime.now().strftime("%Y%m%d"),
                "fill_price": 73400.0,
            }
        ]

    @pytest.mark.asyncio
    async def test_fill_price_update_skipped_without_order_no(self):
        ctx = _context()
        real_client = _FakeRealClient()
        await _subscribe(ctx, real_client, event_filter="all")

        real_client.listeners["SC1"](_frame("SC1", execqty="10", execprc="73400"))
        await _drain()

        assert ctx.fill_price_updates == []

    @pytest.mark.asyncio
    async def test_sc0_frame_reaches_accepted_port_without_fake_fill(self):
        ctx = _context()
        real_client = _FakeRealClient()
        await _subscribe(ctx, real_client, event_filter="all")

        real_client.listeners["SC0"](
            _frame(
                "SC0",
                ordchegb="01",
                marketgb="20",
                shtcode="A035420",
                hname="NAVER",
                ordqty="3",
                ordprice="180000",
                ordno="7654321",
                ordtm="090015123",
                bnstp="1",
            )
        )
        await _drain()

        output = ctx.get_output("order_event", "accepted")
        assert output is not None
        assert output["symbol"] == "035420"
        assert output["order_qty"] == 3
        assert output["order_price"] == 180000.0
        assert output["order_time"] == "090015123"
        assert output["market_code"] == "20"
        assert output["status"] == "주문접수"
        assert "filled_qty" not in output and "filled_price" not in output
        assert ctx.fill_price_updates == []

    @pytest.mark.parametrize(
        "tr_cd,port,status",
        [
            ("SC2", "modified", "정정확인"),
            ("SC3", "cancelled", "취소확인"),
            ("SC4", "rejected", "거부"),
        ],
    )
    @pytest.mark.asyncio
    async def test_sc2_sc3_sc4_reach_their_own_ports(self, tr_cd, port, status):
        ctx = _context()
        real_client = _FakeRealClient()
        await _subscribe(ctx, real_client, event_filter="all")

        real_client.listeners[tr_cd](
            _frame(tr_cd, ordno="1234567", shtnIsuno="A005930", bnstp="2")
        )
        await _drain()

        output = ctx.get_output("order_event", port)
        assert output is not None, f"{tr_cd} 프레임이 {port} 포트에 도달하지 않았다"
        assert output["tr_cd"] == tr_cd
        assert output["status"] == status
        assert output["symbol"] == "005930"

    @pytest.mark.asyncio
    async def test_filtered_node_only_sees_its_own_stream(self):
        ctx = _context()
        real_client = _FakeRealClient()
        await _subscribe(ctx, real_client, event_filter="SC4", node_id="only_rejects")

        real_client.listeners["SC1"](_frame("SC1", ordno="1", execqty="1", execprc="100"))
        real_client.listeners["SC4"](_frame("SC4", ordno="2", rjtqty="1"))
        await _drain()

        assert ctx.get_output("only_rejects", "filled") is None
        rejected = ctx.get_output("only_rejects", "rejected")
        assert rejected is not None and rejected["order_no"] == "2"

    @pytest.mark.asyncio
    async def test_unknown_tr_frame_is_skipped_not_parsed_as_sc1(self):
        """모르는 TR 은 SC1 계열 파서로 넘기지 않는다 — 빈값 이벤트를 만들지 않는다."""
        ctx = _context()
        real_client = _FakeRealClient()
        await _subscribe(ctx, real_client, event_filter="all")

        mislabelled = SC1RealResponse(
            header=SC1RealResponseHeader(tr_cd="SC9"),
            body=_body("SC1", ordno="1234567", execqty="10", execprc="73400"),
            rsp_cd="",
            rsp_msg="",
        )
        real_client.listeners["SC1"](mislabelled)
        await _drain()

        assert ctx.get_all_outputs("order_event") == {}
        assert ctx.fill_price_updates == []
        assert any("SC9" in m for lvl, m, _ in ctx.logs if lvl == "warning")

    @pytest.mark.asyncio
    async def test_body_less_frame_is_skipped_not_zero_filled(self):
        """real_base 는 바디 검증 실패 시 body=None 으로 준다 — 0짜리 체결을 만들지 않는다."""
        ctx = _context()
        real_client = _FakeRealClient()
        await _subscribe(ctx, real_client, event_filter="all")

        broken = SC1RealResponse(
            header=SC1RealResponseHeader(tr_cd="SC1"),
            body=None,
            rsp_cd="",
            rsp_msg="",
            error_msg="validation failed",
        )
        real_client.listeners["SC1"](broken)
        await _drain()

        assert ctx.get_output("order_event", "filled") is None
        assert ctx.fill_price_updates == []
        assert any(lvl == "warning" for lvl, _, _ in ctx.logs)

    @pytest.mark.asyncio
    async def test_header_none_frame_falls_back_to_registered_stream(self):
        """헤더 없이 body 만 있는 프레임은 **등록된 스트림**을 TR 로 삼는다.

        real_base 는 tr_cd 정확일치로만 배달하므로, SC1 리스너에 온 프레임은 설령
        header 가 없어도 SC1 이다. 핸들러는 `(header.tr_cd if header else '') or _stream`
        으로 등록 스트림에 폴백해야 한다 — 종전처럼 'SC0' 으로 떨어지면 엉뚱한 파서로
        간다."""
        ctx = _context()
        real_client = _FakeRealClient()
        await _subscribe(ctx, real_client, event_filter="all")

        frame = SC1RealResponse(
            header=None,
            body=_body("SC1", ordno="1234567", execqty="10", execprc="73400", shtnIsuno="A005930"),
            rsp_cd="",
            rsp_msg="",
        )
        real_client.listeners["SC1"](frame)
        await _drain()

        output = ctx.get_output("order_event", "filled")
        assert output is not None, "header=None 프레임이 filled 포트에 도달하지 않았다"
        assert output["tr_cd"] == "SC1"
        assert output["filled_qty"] == 10
        assert output["symbol"] == "005930"
        assert output["status"] == "체결"
