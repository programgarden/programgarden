"""해외선물 주문이벤트 노드(TC3)의 체결가 갱신 — 키 오타로 죽어 있던 경로 (M1, 2026-09-12).

무엇이 깨져 있었나
------------------
``RealOrderEventNodeExecutor._ls_futures_order_event`` 의 TC3 분기는 바로 위에서 부른
``_parse_tc3_data`` 의 결과에서 ``event_data.get('fill_price', 0)`` 을 읽었다. 그런데
그 파서가 만드는 dict 에 ``fill_price`` 라는 키는 **없다** — 체결가는
``filled_price`` 로 담긴다(노드가 선언한 출력 필드명도 ``filled_price`` 다:
``programgarden_core/nodes/base.py`` ORDER_EVENT_FIELDS). 그래서 늘 0 을 받아
``if fill_price > 0:`` 이 한 번도 참이 되지 않았고, 시장가 주문의 체결가 갱신
(``update_workflow_order_fill_price``)이 이 경로에서 통째로 죽어 있었다.

덧붙여 ``order_date`` 키도 파서에 없어 ``datetime.now()`` 폴백이 쓰였다. TC3 프레임은
``ordr_dt`` 를 실제로 싣는다(SDK ``overseas_futureoption/real/TC3/blocks.py`` — 이
파일의 체결 원장 핸들러 ``on_tc3_event`` 는 이미 그 이름을 읽는다). 로컬 날짜를
주문일자로 지어내면 브로커 영업일과 어긋나는 구간(야간장)에서 (order_no, order_date)
대조가 조용히 빗나간다.

여기서는 네트워크 없이 실제 SDK 블록(``TC3RealResponseBody``)으로 프레임을 만들어
핸들러에 직접 흘린다.
"""

import asyncio
from unittest.mock import Mock

import pytest

from programgarden.executor import RealOrderEventNodeExecutor
from programgarden_finance.ls.overseas_futureoption.real.TC3.blocks import (
    TC3RealResponseBody,
)


def tc3_body(**overrides):
    """실제 TC3 응답 블록 — 필수 필드는 빈 문자열로 채우고 관심 필드만 덮어쓴다."""
    fields = {
        name: "" for name, field in TC3RealResponseBody.model_fields.items()
        if field.is_required()
    }
    fields.update(
        lineseq="1", key="k", user="u", svc_id="CH01",
        ordr_dt="20260909", ordr_no="000123", is_cd="ESM26", s_b_ccd="2",
        ccls_q="2", ccls_prc="100.25", ccls_no="000777", ccls_tm="001500",
    )
    fields.update(overrides)
    return TC3RealResponseBody(**fields)


class FakeContext:
    """주문이벤트 노드가 실제로 호출하는 표면만 구현한 컨텍스트."""

    is_shutdown = False
    is_deep_validate = False

    def __init__(self):
        self.handlers = {}
        self.fill_price_updates = []
        self.outputs = []
        self.logs = []

    # --- 주문이벤트 구독 표면 ---
    def register_order_event_handler(self, product, tr_cd, node_id, event_filter, handler):
        self.handlers[tr_cd] = handler

    def has_order_event_subscription(self, product):
        # 이미 마스터 콜백이 있다고 보고(다른 노드가 먼저 등록한 상태) 실제 WebSocket
        # 연결 경로를 타지 않게 한다.
        return True

    def get_order_event_real_client(self, product):
        return Mock()

    def register_persistent(self, node_id, client, metadata=None):
        pass

    def register_cleanup_on_flow_end(self, node_id, client):
        pass

    # --- 출력/이벤트 표면 ---
    def set_output(self, node_id, port, data):
        self.outputs.append((node_id, port, data))

    async def notify_output_update(self, **kwargs):
        pass

    async def emit_event(self, **kwargs):
        pass

    def log(self, level, message, node_id=None, data=None):
        self.logs.append((level, message))

    # --- 검증 대상 ---
    def update_workflow_order_fill_price(self, order_no, order_date, fill_price):
        self.fill_price_updates.append(
            {"order_no": order_no, "order_date": order_date, "fill_price": fill_price}
        )


async def _tc3_handler(context):
    executor = RealOrderEventNodeExecutor()
    await executor._ls_futures_order_event(
        ls=Mock(), node_id="evt", config={}, context=context,
        stay_connected=True, event_filter="all",
    )
    return context.handlers["TC3"]


def test_parse_tc3_carries_filled_price_and_order_date():
    """파서 dict 의 실제 키 이름 고정 — 'fill_price' 는 없고 'filled_price' 다."""
    parsed = RealOrderEventNodeExecutor()._parse_tc3_data(tc3_body())
    assert parsed["filled_price"] == 100.25
    assert "fill_price" not in parsed, "이 키를 읽던 게 M1 결함의 원인이었다"
    assert parsed["order_date"] == "20260909"
    assert parsed["order_no"] == "000123"


@pytest.mark.asyncio
async def test_tc3_fill_updates_order_fill_price():
    """체결 프레임 1건 → 체결가 갱신이 **실제로** 호출된다 (구 코드: 0건)."""
    context = FakeContext()
    handler = await _tc3_handler(context)

    handler(Mock(body=tc3_body()))
    await asyncio.sleep(0)

    assert context.fill_price_updates == [
        {"order_no": "000123", "order_date": "20260909", "fill_price": 100.25}
    ]
    ports = [port for _, port, _ in context.outputs]
    assert ports == ["filled"]


@pytest.mark.asyncio
async def test_tc3_uses_frame_order_date_not_today():
    """주문일자는 프레임의 ordr_dt 를 그대로 쓴다 — 오늘 날짜로 지어내지 않는다."""
    from datetime import datetime

    context = FakeContext()
    handler = await _tc3_handler(context)

    handler(Mock(body=tc3_body(ordr_dt="20260101")))
    await asyncio.sleep(0)

    assert context.fill_price_updates[0]["order_date"] == "20260101"
    assert context.fill_price_updates[0]["order_date"] != datetime.now().strftime("%Y%m%d")


@pytest.mark.asyncio
async def test_tc3_without_order_date_skips_update():
    """ordr_dt 가 비면 갱신을 건너뛴다 — 오늘 날짜를 지어내 원장을 오염시키지 않는다."""
    context = FakeContext()
    handler = await _tc3_handler(context)

    handler(Mock(body=tc3_body(ordr_dt="")))
    await asyncio.sleep(0)

    assert context.fill_price_updates == []
    # 체결 이벤트 자체는 종전대로 발행된다 (갱신만 건너뛴다).
    assert [port for _, port, _ in context.outputs] == ["filled"]


@pytest.mark.asyncio
async def test_tc3_without_fill_price_does_not_update():
    """체결가가 0 이면 갱신하지 않는다 (종전 동작 유지)."""
    context = FakeContext()
    handler = await _tc3_handler(context)

    handler(Mock(body=tc3_body(ccls_prc="0")))
    await asyncio.sleep(0)

    assert context.fill_price_updates == []
