"""Actual AS1 callback and SQLite ledger preserve individual stock executions."""

import asyncio
from datetime import datetime
import json
import socket
import sqlite3
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from programgarden.context import ExecutionContext
from programgarden.database.workflow_position_tracker import WorkflowPositionTracker
from programgarden.executor import BrokerNodeExecutor
from programgarden_finance.ls.overseas_stock.real.AS1.blocks import AS1RealResponseBody


@pytest.fixture(autouse=True)
def isolate_runtime(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Stock execution identity tests are offline")

    for name in ("connect", "connect_ex", "sendto"):
        monkeypatch.setattr(socket.socket, name, denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)
    monkeypatch.setattr(BrokerNodeExecutor, "_active_trackers", {})


def execution_body(execution_id):
    values = {name: field.examples[0] for name, field in AS1RealResponseBody.model_fields.items()}
    values.update(sOrdNo=123, sExecNO=execution_id, sExecQty=0.5, sExecPrc=100,
                  sShtnIsuNo="SYNTH", sOrdMktCode="82", sOrdPtnCode="02", sBnsTp="2",
                  proctm="120000001")
    return AS1RealResponseBody.model_validate(values)


def ledger_rows(path):
    with sqlite3.connect(path) as conn:
        return conn.execute(
            "SELECT execution_id, quantity, execution_payload FROM trade_history ORDER BY id"
        ).fetchall()


@pytest.mark.asyncio
async def test_as1_replay_and_identical_partials_reach_durable_identity(tmp_path, monkeypatch):
    context = ExecutionContext(job_id="stock-identity", workflow_id="offline")
    path = str(tmp_path / "stock.sqlite")
    tracker = WorkflowPositionTracker(path, context.job_id, "broker", product="overseas_stock")
    context._workflow_position_tracker = tracker
    tracker.record_order("123", datetime.now().strftime("%Y%m%d"), "SYNTH", "NASDAQ",
                         "buy", 1, 100, context.job_id, "order-node")

    callbacks = {}
    real = SimpleNamespace(
        connect=AsyncMock(),
        AS0=lambda: SimpleNamespace(on_as0_message=lambda callback: callbacks.update(as0=callback)),
        AS1=lambda: SimpleNamespace(on_as1_message=lambda callback: callbacks.update(as1=callback)),
    )
    ls = SimpleNamespace(overseas_stock=lambda: SimpleNamespace(real=lambda: real))
    submitted = []
    schedule = asyncio.run_coroutine_threadsafe

    def capture(coroutine, loop):
        future = schedule(coroutine, loop)
        submitted.append(future)
        return future

    monkeypatch.setattr(asyncio, "run_coroutine_threadsafe", capture)
    await BrokerNodeExecutor()._subscribe_overseas_stock_fill_events(ls, "broker", context)

    async def emit(execution_id):
        callbacks["as1"](SimpleNamespace(body=execution_body(execution_id)))
        assert submitted, "AS1 callback did not schedule execution recording"
        await asyncio.wrap_future(submitted.pop())

    await emit("0001")
    first = ledger_rows(path)
    assert len(first) == 1 and first[0][:2] == ("1", 0.5)
    assert json.loads(first[0][2])["reported_execution_id"] == "0001"

    await emit("1")
    assert ledger_rows(path) == first

    # Same order, time, price and quantity; the distinct broker execution ID
    # proves that this is another partial fill, not a repeated notification.
    await emit("0002")
    both = ledger_rows(path)
    assert [(row[0], row[1]) for row in both] == [("1", 0.5), ("2", 0.5)]

    context._workflow_position_tracker = WorkflowPositionTracker(
        path, context.job_id, "broker", product="overseas_stock")
    await emit("0002")
    assert ledger_rows(path) == both
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT SUM(remaining_qty) FROM workflow_position_lots").fetchone()[0] == 1


@pytest.mark.asyncio
async def test_context_call_without_execution_identity_retains_legacy_arguments(tmp_path):
    context = ExecutionContext(job_id="stock-legacy", workflow_id="offline")
    calls = []

    class LegacyTracker:
        async def record_fill(self, **kwargs):
            calls.append(kwargs)
            return "manual"

    context._workflow_position_tracker = LegacyTracker()
    result = await context.record_workflow_fill(
        "123", "20260909", "SYNTH", "NASDAQ", "buy", 0.5, 100, "120000001", "10")
    assert result == "manual"
    assert calls == [{"order_no": "123", "order_date": "20260909", "symbol": "SYNTH",
                      "exchange": "NASDAQ", "side": "buy", "quantity": 0.5, "price": 100,
                      "fill_time": "120000001", "commda_code": "10"}]


async def _capture_as1_fill_kwargs(monkeypatch, **field_overrides):
    """AS1 콜백을 실제로 태워 context.record_workflow_fill 의 kwargs 를 잡아온다."""
    values = {name: field.examples[0] for name, field in AS1RealResponseBody.model_fields.items()}
    values.update(sOrdNo=123, sExecNO="0001", sExecQty=0.5, sExecPrc=100,
                  sShtnIsuNo="SYNTH", sOrdMktCode="82", sOrdPtnCode="02", sBnsTp="2")
    values.update(field_overrides)
    body = AS1RealResponseBody.model_validate(values)

    writes = []

    async def record(**kwargs):
        writes.append(kwargs)
        return "workflow"

    context = SimpleNamespace(
        job_id="as1-fill-time", is_shutdown=False, log=lambda *a, **k: None,
        record_workflow_fill=record,
    )

    callbacks = {}
    real = SimpleNamespace(
        connect=AsyncMock(),
        AS0=lambda: SimpleNamespace(on_as0_message=lambda cb: callbacks.update(as0=cb)),
        AS1=lambda: SimpleNamespace(on_as1_message=lambda cb: callbacks.update(as1=cb)),
    )
    ls = SimpleNamespace(overseas_stock=lambda: SimpleNamespace(real=lambda: real))

    submitted = []
    schedule = asyncio.run_coroutine_threadsafe

    def capture(coroutine, loop):
        future = schedule(coroutine, loop)
        submitted.append(future)
        return future

    monkeypatch.setattr(asyncio, "run_coroutine_threadsafe", capture)
    await BrokerNodeExecutor()._subscribe_overseas_stock_fill_events(ls, "broker", context)
    callbacks["as1"](SimpleNamespace(body=body))
    assert submitted, "AS1 callback did not schedule the fill recording"
    await asyncio.wrap_future(submitted.pop())
    assert len(writes) == 1
    return writes[0]


@pytest.mark.asyncio
async def test_as1_fill_time_prefers_execution_time(monkeypatch):
    """sExecTime(체결시각)이 있으면 그 값을 쓴다."""
    kwargs = await _capture_as1_fill_kwargs(
        monkeypatch, sExecTime="093015", sRcptExecTime="093020", proctm="120000001")
    assert kwargs["fill_time"] == "093015"


@pytest.mark.asyncio
async def test_as1_fill_time_falls_back_to_exchange_received_time(monkeypatch):
    """sExecTime 이 공백이면 sRcptExecTime(거래소수신체결시각)으로 내려간다."""
    kwargs = await _capture_as1_fill_kwargs(
        monkeypatch, sExecTime="   ", sRcptExecTime="093020", proctm="120000001")
    assert kwargs["fill_time"] == "093020"


@pytest.mark.asyncio
async def test_as1_fill_time_is_empty_when_frame_reports_none(monkeypatch):
    """둘 다 비면 **빈 문자열**이다 — proctm 도, 로컬 시계도 쓰지 않는다.

    proctm 은 AP처리시간(증권사 서버 처리시각)이지 거래소 체결시각이 아니다
    (출처: 오너 진술 2026-09-12; SDK AS1/blocks.py:91 이 proctm 을 AS0~AS4 공유
    WS 프레임 헤더 구간으로, :317 이 sExecTime 을 AS1 체결 전용 구간으로 둔다).
    그리고 `datetime.now().strftime('%H%M%S000')` 합성값은 파드 로컬(UTC) 벽시계를
    브로커 체결시각과 같은 9자리 모양으로 내보내, 소비자(pg-worker
    app/order_fill_updates.py)가 그걸 America/New_York 로 읽어 executed_at 을
    '계산된 체결시각' 으로 확정하게 만든다(executed_at_source 태그 없이).
    빈 문자열이어야 그쪽 `and fill_time` 가드가 걸려 received_at 폴백이 된다.
    """
    kwargs = await _capture_as1_fill_kwargs(
        monkeypatch, sExecTime="", sRcptExecTime="", proctm="120000001")
    assert kwargs["fill_time"] == ""


@pytest.mark.asyncio
async def test_absent_fill_time_stays_empty_on_the_wire_but_safe_in_the_ledger(tmp_path):
    """체결시각이 없을 때: 서버로는 빈 문자열, 원장에는 날짜필터 안전한 표식.

    서버 쪽 — pg-worker(app/order_fill_updates.py)는 `order_date + fill_time` 을
    시장 세션 타임존으로 읽어 executed_at 을 확정한다. 빈 문자열이어야
    `and fill_time` 가드가 걸려 received_at 폴백이 된다.

    원장 쪽 — fill_datetime 은 f"{order_date}_{fill_time}" 이고 날짜 필터는
    `fill_datetime >= f"{start_date}_000000000"` 라는 **문자열 비교**다. 빈
    체결시각을 그대로 넣으면 "20260912_" < "20260912_000000000" 이라 그 로트가
    대회 구간 PnL(get_workflow_positions/calculate_pnl)에서 통째로 사라진다.
    그래서 원장에만 비숫자 표식(UNKNOWN_FILL_TIME)을 쓴다.
    """
    from programgarden.context import UNKNOWN_FILL_TIME

    today = datetime.now().strftime("%Y%m%d")
    context = ExecutionContext(job_id="fill-time-absent", workflow_id="offline")
    path = str(tmp_path / "absent.sqlite")
    tracker = WorkflowPositionTracker(path, context.job_id, "broker", product="korea_stock")
    context._workflow_position_tracker = tracker
    tracker.set_fill_classified_callback(context._on_tracker_fill_classified)
    tracker.record_order("4242", today, "005930", "KRX", "buy", 1, 55000,
                         context.job_id, "order-node")

    events = []

    class Capture:
        async def on_order_fill(self, event):
            events.append(event)

        def __getattr__(self, name):
            async def noop(*args, **kwargs):
                return None
            return noop

    context.add_listener(Capture())

    result = await context.record_workflow_fill(
        order_no="4242", order_date=today, symbol="005930", exchange="KRX",
        side="buy", quantity=1, price=55000, fill_time="", commda_code="40",
    )
    assert result == "workflow"

    assert events and events[0].fill_time == "", "서버로 나가는 fill_time 은 비어 있어야 한다"

    with sqlite3.connect(path) as conn:
        stored = conn.execute(
            "SELECT fill_datetime FROM workflow_position_lots"
        ).fetchone()[0]
    assert stored == f"{today}_{UNKNOWN_FILL_TIME}"
    # 날짜 필터(문자열 비교)를 통과해야 대회 구간 PnL 에서 사라지지 않는다.
    assert stored >= f"{today}_000000000"
    assert "005930" in tracker.get_workflow_positions(start_date=today)


@pytest.mark.asyncio
async def test_record_workflow_fill_default_media_code_is_not_a_fabricated_value():
    """commda_code 를 안 넘기면 원장에는 ""(= 프레임이 말하지 않음)가 간다.

    종전 기본값은 "40"(OPEN API)이었다 — 관측되지 않은 값을 원장에 증거처럼
    남기는 조작값이고, tracker.detect_anomalies 가 `WHERE commda_code='40'` 을
    unknown_api 비율의 분모로 써서 trust_score 에 실제로 영향이 간다.
    """
    context = ExecutionContext(job_id="media-default", workflow_id="offline")
    calls = []

    class LegacyTracker:
        async def record_fill(self, **kwargs):
            calls.append(kwargs)
            return "manual"

    context._workflow_position_tracker = LegacyTracker()
    await context.record_workflow_fill(
        "123", "20260909", "SYNTH", "NASDAQ", "buy", 1, 100, "120000001")

    assert calls[0]["commda_code"] == ""


@pytest.mark.asyncio
async def test_as1_zero_order_number_keeps_the_fill_and_drops_execution_id(tmp_path, monkeypatch):
    """sOrdNo=0 프레임도 **체결을 잃지 않는다**(E3 가드 회귀).

    AS1 의 sOrdNo 는 int 다(SDK overseas_stock/real/AS1/blocks.py:374). 0 이 오면
    `str(...)` 이 '0' 이 되고, tracker._normalize_identifier 가 0-패딩을 벗겨
    None 으로 접는다. 그 상태에서 체결번호(sExecNO)를 실으면 _execution_key 가
    ValueError("Explicit execution identity requires an order number and date")
    를 올리고, 그 예외를 context.record_workflow_fill 의 try 가 삼켜 **체결이
    통째로 사라진다**(trade_history rows=0). SC1·TC3 에는 이 가드가 있었는데
    AS1 에만 빠져 있었다.

    기대 동작: 중복방지(execution_id)만 포기하고 체결 자체는 원장에 남는다.
    """
    context = ExecutionContext(job_id="stock-zero-ordno", workflow_id="offline")
    path = str(tmp_path / "zero.sqlite")
    tracker = WorkflowPositionTracker(path, context.job_id, "broker", product="overseas_stock")
    context._workflow_position_tracker = tracker
    today = datetime.now().strftime("%Y%m%d")
    tracker.record_order("0", today, "SYNTH", "NASDAQ", "buy", 1, 100,
                         context.job_id, "order-node")

    callbacks = {}
    real = SimpleNamespace(
        connect=AsyncMock(),
        AS0=lambda: SimpleNamespace(on_as0_message=lambda cb: callbacks.update(as0=cb)),
        AS1=lambda: SimpleNamespace(on_as1_message=lambda cb: callbacks.update(as1=cb)),
    )
    ls = SimpleNamespace(overseas_stock=lambda: SimpleNamespace(real=lambda: real))

    submitted = []
    schedule = asyncio.run_coroutine_threadsafe

    def capture(coroutine, loop):
        future = schedule(coroutine, loop)
        submitted.append(future)
        return future

    monkeypatch.setattr(asyncio, "run_coroutine_threadsafe", capture)
    await BrokerNodeExecutor()._subscribe_overseas_stock_fill_events(ls, "broker", context)

    values = {name: field.examples[0] for name, field in AS1RealResponseBody.model_fields.items()}
    values.update(sOrdNo=0, sExecNO="0001", sExecQty=0.5, sExecPrc=100,
                  sShtnIsuNo="SYNTH", sOrdMktCode="82", sOrdPtnCode="02", sBnsTp="2",
                  sExecTime="093015")
    callbacks["as1"](SimpleNamespace(body=AS1RealResponseBody.model_validate(values)))
    assert submitted, "AS1 callback did not schedule the fill recording"
    await asyncio.wrap_future(submitted.pop())

    rows = ledger_rows(path)
    assert len(rows) == 1, "주문번호가 0 이라고 체결을 통째로 버리면 안 된다"
    assert rows[0][0] is None, "중복방지 키를 만들 수 없으면 체결번호는 싣지 않는다"
    assert rows[0][1] == 0.5
