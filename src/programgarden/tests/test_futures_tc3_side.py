"""Pass real SDK TC3 messages through the engine without network access."""

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from programgarden.executor import BrokerNodeExecutor
from programgarden_finance.ls.overseas_futureoption.real import Real
from programgarden_finance.ls.overseas_futureoption.real.TC3.blocks import TC3RealResponseBody


class MemorySocket:
    def __init__(self):
        self.messages = asyncio.Queue()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def recv(self):
        return await self.messages.get()

    async def send(self, message):
        # Subscription envelopes stay inside this in-memory transport.
        pass

    async def close(self):
        pass


def tc3_packet(side, **overrides):
    body = {
        name: "" for name, field in TC3RealResponseBody.model_fields.items()
        if field.is_required()
    }
    body.update(
        lineseq="1", key="synthetic-key", user="synthetic-user", svc_id="CH01",
        ordr_dt="20260909", ordr_no="000123", is_cd="SYNTHETIC", s_b_ccd=side,
        ccls_q="2", ccls_prc="100.25", ccls_no="000777",
        ccls_dt="20260910", ccls_tm="001500",
    )
    body.update(overrides)
    return {
        "header": {"tr_cd": "TC3", "rsp_cd": "00000", "rsp_msg": "synthetic"},
        "body": body,
    }


async def deliver_tc3(monkeypatch, side, *, managed=False, shutdown=False, **overrides):
    socket = MemorySocket()
    connect = Mock(return_value=socket)
    monkeypatch.setattr("programgarden_finance.ls.real_base.connect", connect)
    monkeypatch.setattr(BrokerNodeExecutor, "_active_trackers", {})
    real = Real(
        token_manager=SimpleNamespace(
            access_token="synthetic-token", wss_url="wss://offline.invalid",
        ),
        reconnect=False,
    )
    writes, scheduled, parsed = [], [], []

    async def record(**fields):
        writes.append(fields)

    context = SimpleNamespace(
        job_id="tc3-side-offline", is_shutdown=shutdown,
        order_lifecycle_handler=object() if managed else None,
        log=Mock(), record_workflow_fill=record,
    )
    ls = SimpleNamespace(overseas_futureoption=lambda: SimpleNamespace(real=lambda: real))
    executor = BrokerNodeExecutor()
    original_schedule = asyncio.run_coroutine_threadsafe

    def schedule(coroutine, loop):
        future = original_schedule(coroutine, loop)
        scheduled.append(future)
        return future

    monkeypatch.setattr(asyncio, "run_coroutine_threadsafe", schedule)
    loop = asyncio.get_running_loop()
    processed = asyncio.Event()
    try:
        await executor._subscribe_overseas_futures_fill_events(ls, "broker", context)
        registered = real._on_message_listeners["TC3"]
        # finance 1.9.7 부터 키당 리스너 리스트 — 원장 리스너는 이 테스트에서 유일한 등록자다
        callback = registered[0] if isinstance(registered, list) else registered

        def observe(response):
            try:
                parsed.append(response)
                callback(response)
            finally:
                loop.call_soon_threadsafe(processed.set)

        # finance 1.9.7: 키당 다중 리스너라 래퍼를 *추가*하면 원본도 같이 불려 체결이 두 번 기록된다 —
        # 원본을 떼고 래퍼(원본을 안에서 호출)만 남긴다.
        real.TC3().on_remove_tc3_message(callback)
        real.TC3().on_tc3_message(observe)
        await socket.messages.put(json.dumps(tc3_packet(side, **overrides)))
        await asyncio.wait_for(processed.wait(), timeout=2)
        # The callback has finished on the SDK thread. Drain every submitted
        # coroutine so a skipped event cannot appear successful due to a race.
        for future in scheduled:
            await asyncio.wait_for(asyncio.wrap_future(future), timeout=2)
        connect.assert_called_once()
        assert len(parsed) == 1
        assert isinstance(parsed[0].body, TC3RealResponseBody)
        assert parsed[0].body.s_b_ccd == side
        return writes, len(scheduled)
    finally:
        await real.close(force=True)
        executor._active_trackers.clear()


@pytest.mark.asyncio
@pytest.mark.parametrize("managed", [False, True], ids=["standalone", "app-managed"])
@pytest.mark.parametrize("side, expected", [("1", "sell"), ("2", "buy"), ("9", None), ("", None)])
async def test_tc3_sdk_side_and_managed_reconciliation_guard(monkeypatch, caplog, side, expected, managed):
    writes, scheduled = await deliver_tc3(monkeypatch, side, managed=managed)
    if managed or expected is None:
        assert writes == []
        assert scheduled == 0
        if not managed:
            assert "Ignoring TC3 fill with unknown side code" in caplog.text
    else:
        assert scheduled == 1
        assert writes == [{
            "order_no": "000123", "order_date": "20260909", "symbol": "SYNTHETIC",
            "exchange": "FUTURES", "side": expected, "quantity": 2, "price": 100.25,
            # TC3 프레임에는 통신매체코드 필드가 없다. 종전에는 '40'(OPEN API)을
            # 하드코딩해 프레임이 말하지 않은 값을 원장에 남겼고, tracker 의
            # detect_anomalies 가 그 '40' 을 unknown_api 비율의 분모로 써서
            # trust_score 까지 흔들렸다. 이제 빈 문자열('프레임이 말하지 않음')이며
            # media_channel('')='unknown' 은 api 와 같은 버퍼 분기라 분류는 그대로다.
            "fill_time": "001500", "commda_code": "",
            # 체결번호는 TC3 프레임 자신의 ccls_no 필드를 그대로 읽은 값이다.
            # (종전 단언은 `"execution_id" not in writes[0]` 이었다. 그 취지는
            #  "TC3 식별자를 REST 대사 식별자의 alias 로 지어내지 말라" 였는데,
            #  여기서 싣는 건 alias 추론이 아니라 프레임 필드 독출이므로 그 취지와
            #  충돌하지 않는다. 이 값이 없으면 원장의 execution_id 부분 유니크
            #  인덱스가 선물에서 통째로 비활성이라 같은 프레임 재전달이 FIFO 에
            #  이중계상된다.)
            "execution_id": "000777",
        }]


@pytest.mark.asyncio
@pytest.mark.parametrize("side", ["1", "2"])
async def test_tc3_after_shutdown_never_schedules_inventory_write(monkeypatch, side):
    writes, scheduled = await deliver_tc3(monkeypatch, side, shutdown=True)
    assert writes == []
    assert scheduled == 0


@pytest.mark.asyncio
async def test_tc3_without_order_number_keeps_the_fill_and_drops_execution_id(monkeypatch):
    """주문번호가 빈 TC3 프레임은 체결번호를 싣지 않고 **체결을 유지**한다.

    원장의 execution identity 키는 (product, provider, trading_mode, order_date,
    order_no, execution_id) 다(workflow_position_tracker._execution_key). 체결번호만
    있고 주문번호가 비면 그 키 생성이 ValueError 를 올리고, 그 예외를
    context.record_workflow_fill 의 try 가 삼켜 **체결이 통째로 유실**된다
    ("error" 반환). 그래서 이럴 때는 중복방지를 포기하고 종전 경로로 안전
    강등한다 — 체결 자체를 버리는 것보다 낫다.
    """
    writes, scheduled = await deliver_tc3(monkeypatch, "2", ordr_no="")

    assert scheduled == 1, "주문번호가 없다고 체결을 통째로 버리면 안 된다"
    assert writes[0]["order_no"] == ""
    assert writes[0]["execution_id"] is None


@pytest.mark.asyncio
async def test_tc3_all_zero_order_number_also_drops_execution_id(monkeypatch):
    """'0'/'000' 도 식별자가 아니다 — tracker._normalize_identifier 가 0-패딩을
    벗겨 None 으로 접기 때문에 빈 주문번호와 같은 ValueError 경로다."""
    writes, scheduled = await deliver_tc3(monkeypatch, "2", ordr_no="000")

    assert scheduled == 1
    assert writes[0]["execution_id"] is None


@pytest.mark.asyncio
async def test_tc3_missing_fill_time_is_empty_not_synthesized(monkeypatch):
    """체결시각이 없으면 **빈 문자열**이다 — 로컬 시계를 합성하지 않는다.

    종전에는 `or datetime.now().strftime('%H%M%S000')` 으로 파드 로컬(UTC) 벽시계를
    브로커 체결시각과 **같은 9자리 모양**으로 내보냈다. 소비자(pg-worker
    app/order_fill_updates.py)는 그 9자리를 시장 세션 타임존으로 읽어 executed_at 을
    '계산된 체결시각' 으로 확정하고 executed_at_source 태그도 붙이지 않는다.
    빈 문자열이면 그쪽 `and fill_time` 가드가 걸려 정직한 received_at 폴백이 된다.
    """
    writes, scheduled = await deliver_tc3(monkeypatch, "2", ccls_tm="")

    assert scheduled == 1
    assert writes[0]["fill_time"] == ""


@pytest.mark.asyncio
async def test_tc3_blank_order_date_keeps_the_fill_and_drops_execution_id(monkeypatch):
    """주문일자가 **빈 문자열**인 TC3 프레임도 체결을 잃지 않는다.

    executor 는 주문일자를 `getattr(body, 'ordr_dt', <로컬날짜>)` 로 읽는데,
    getattr 의 기본값은 **속성이 아예 없을 때만** 쓰인다 — 브로커가 `ordr_dt=""`
    를 실어 보내면 빈 문자열이 그대로 흐른다. 원장의 execution identity 키는
    order_no 뿐 아니라 order_date 도 요구해서
    (workflow_position_tracker._execution_key: `if order_no is None or not
    fill.order_date: raise ValueError`), 주문번호가 멀쩡해도 날짜가 비면 같은
    ValueError 경로로 **체결이 통째로 유실**된다(record_workflow_fill 의 try 가
    삼킴). 그래서 가드는 (주문번호, 주문일자)를 함께 본다. 여기서 로컬 날짜를
    지어내 채우지는 않는다 — 프레임이 말하지 않은 주문일자는 원장 대조 키를
    거짓으로 만든다.
    """
    writes, scheduled = await deliver_tc3(monkeypatch, "2", ordr_dt="")

    assert scheduled == 1, "주문일자가 없다고 체결을 통째로 버리면 안 된다"
    assert writes[0]["order_date"] == ""
    assert writes[0]["order_no"] == "000123", "주문번호는 멀쩡한 프레임이다"
    assert writes[0]["execution_id"] is None
