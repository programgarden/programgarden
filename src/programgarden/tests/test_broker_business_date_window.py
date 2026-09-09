"""The broker's order date is its own business date, not the machine's calendar date.

Measured on 2026-09-10: an HKEX paper futures order accepted at 00:39:25 KST came
back from CIDBQ02400 as OrdDt/ExecDt 20260909, because the overnight session is
filed under the previous business day. Any confirmation query that pins the
window to ``datetime.now()`` therefore cuts away the fill it just placed.

These tests pin the three engine query paths that were narrowing on the local
calendar date. LS's *overseas stock* OrdDt convention was not measured directly,
so the stock paths only widen the search — they never assert a date.
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from programgarden.executor import BrokerNodeExecutor, NewOrderNodeExecutor


class _Req:
    def __init__(self, result):
        self._result = result

    async def req_async(self):
        return self._result


def _context():
    return SimpleNamespace(log=lambda *args, **kwargs: None,
                           sync_workflow_fill_prices_from_history=lambda history: 0,
                           sync_workflow_fills_from_history=lambda history: len(history))


def _futures_ls(recorder, rows):
    def cidbq02400(body):
        recorder.append(body)
        return _Req(SimpleNamespace(error_msg=None, block2=rows))

    accno = SimpleNamespace(CIDBQ02400=cidbq02400)
    return SimpleNamespace(overseas_futureoption=lambda: SimpleNamespace(accno=lambda: accno))


@pytest.mark.asyncio
async def test_futures_same_day_query_sends_no_local_date_window():
    # ThdayTpCode="1" already means "the broker's current session". Sending the
    # ordering machine's date as the window is what discarded the overnight fill.
    sent = []
    row = SimpleNamespace(OvrsFutsOrdNo="3201", ExecQty=1, AbrdFutsExecPrc="25003")
    filled, price = await NewOrderNodeExecutor()._query_overseas_futures_fill(
        _futures_ls(sent, [row]), "3201", _context(), "order")
    assert (filled, price) == (1, 25003.0)
    body, = sent
    assert body.ThdayTpCode == "1"
    assert body.QrySrtDt == "" and body.QryEndDt == ""


@pytest.mark.asyncio
async def test_futures_fill_is_matched_by_order_number_regardless_of_business_date():
    sent = []
    rows = [SimpleNamespace(OvrsFutsOrdNo="999", ExecQty=5, AbrdFutsExecPrc="1"),
            SimpleNamespace(OvrsFutsOrdNo="3201", ExecQty=1, AbrdFutsExecPrc="25003")]
    filled, price = await NewOrderNodeExecutor()._query_overseas_futures_fill(
        _futures_ls(sent, rows), "3201", _context(), "order")
    assert (filled, price) == (1, 25003.0)


@pytest.mark.asyncio
async def test_overseas_stock_confirmation_looks_one_business_day_back_only_when_empty():
    # COSAQ00102 requires an explicit OrdDt, so the widening has to be a second
    # query — and it must cost nothing while the first query still finds the fill.
    executor = NewOrderNodeExecutor()
    executor._query_overseas_stock_fill = AsyncMock(side_effect=[(0, 0.0), (2, 10.5)])
    order_result = {"order_result": {"success": True, "order_id": "77", "quantity": 2,
                                     "symbol": "AAPL", "status": "submitted"}}
    await executor._confirm_order_fill(object(), "overseas_stock", "limit", order_result,
                                       {"fill_confirm_attempts": 1}, _context(), "order")
    assert executor._query_overseas_stock_fill.await_count == 2
    fallback = executor._query_overseas_stock_fill.await_args_list[1]
    assert fallback.kwargs["order_date"], "the retry must name an explicit earlier date"
    assert order_result["order_result"]["status"] == "filled"
    assert order_result["order_result"]["filled_quantity"] == 2


@pytest.mark.asyncio
async def test_overseas_stock_confirmation_does_not_retry_when_the_fill_is_found():
    executor = NewOrderNodeExecutor()
    executor._query_overseas_stock_fill = AsyncMock(return_value=(2, 10.5))
    order_result = {"order_result": {"success": True, "order_id": "77", "quantity": 2,
                                     "symbol": "AAPL", "status": "submitted"}}
    await executor._confirm_order_fill(object(), "overseas_stock", "limit", order_result,
                                       {"fill_confirm_attempts": 1}, _context(), "order")
    assert executor._query_overseas_stock_fill.await_count == 1


@pytest.mark.asyncio
async def test_futures_confirmation_never_takes_the_stock_date_retry():
    executor = NewOrderNodeExecutor()
    executor._query_overseas_futures_fill = AsyncMock(return_value=(0, 0.0))
    executor._query_overseas_stock_fill = AsyncMock(return_value=(1, 1.0))
    order_result = {"order_result": {"success": True, "order_id": "3201", "quantity": 1,
                                     "symbol": "HMHU26", "status": "submitted"}}
    await executor._confirm_order_fill(object(), "overseas_futures", "limit", order_result,
                                       {"fill_confirm_attempts": 1}, _context(), "order")
    assert executor._query_overseas_stock_fill.await_count == 0
    assert order_result["order_result"]["status"] == "open"


@pytest.mark.asyncio
async def test_stock_fill_history_retries_the_previous_date_but_keeps_the_local_identity():
    # Widen the search, never the ledger identity. Fill classification matches
    # `workflow_orders` on (order_no, order_date), and that row is stamped with
    # the local date at order time, so stamping the broker's date here would make
    # the fill "unknown_api" and drop it from the executed-order count entirely.
    row = SimpleNamespace(OrdNo=77, OvrsExecPrc=10.5, ExecQty=2, ShtnIsuNo="AAPL",
                          OrdMktCode="82", BnsTpCode="2", ExecTime="093000000")
    captured = {}

    context = _context()

    def capture(history):
        captured["history"] = history
        return len(history)

    context.sync_workflow_fills_from_history = capture

    dates = []

    def cosaq00102(body):
        dates.append(body.OrdDt)
        return _Req(SimpleNamespace(block3=[row] if len(dates) == 2 else []))

    ls = SimpleNamespace(overseas_stock=lambda: SimpleNamespace(
        accno=lambda: SimpleNamespace(cosaq00102=cosaq00102)))

    await BrokerNodeExecutor()._sync_overseas_stock_fill_prices(
        ls, [], context, "broker")

    assert len(dates) == 2 and dates[0] != dates[1]
    history = captured.get("history") or []
    assert history and history[0]["order_date"] == dates[0], (
        "the ledger keeps the local order date even when an earlier query found the fill")
    assert history[0]["order_no"] == "77" and history[0]["quantity"] == 2


# ---------------------------------------------------------------------------
# 개인 지표 캐시는 시간뿐 아니라 원장 변경도 봐야 한다.
# 실측 2026-09-10: SNDL 실체결이 02:17:31.674 에 원장에 들어갔는데, 저장된 봉투는
# 0.5초 전(02:17:31.189)에 계산된 것이라 원장에 체결 1건이 있는데도 체결 주문 수가
# 0 으로 남았다. 원샷 워크플로우는 곧바로 끝나므로 "다음 틱에 갱신"이 오지 않는다.
# ---------------------------------------------------------------------------


def test_recording_a_fill_advances_the_ledger_revision(tmp_path):
    import asyncio

    from programgarden.database.workflow_position_tracker import WorkflowPositionTracker

    tracker = WorkflowPositionTracker(
        db_path=str(tmp_path / "ledger.db"), job_id="job-1", broker_node_id="broker",
        product="overseas_stock", provider="ls-sec.co.kr", trading_mode="live")
    assert tracker.fill_revision == 0

    async def record():
        tracker.record_order(
            order_no="215", order_date="20260910", symbol="SNDL", exchange="NASDAQ",
            side="buy", quantity=1, price=1.45, job_id="job-1", node_id="order")
        return await tracker.record_fill(
            order_no="215", order_date="20260910", symbol="SNDL", exchange="NASDAQ",
            side="buy", quantity=1, price=1.41, fill_time="021731674", commda_code="40")

    assert asyncio.run(record()) == "workflow"
    assert tracker.fill_revision == 1, "체결이 원장에 들어갔으면 리비전이 올라가야 한다"
    assert tracker.personal_metrics()["executed_order_count"] == 1
