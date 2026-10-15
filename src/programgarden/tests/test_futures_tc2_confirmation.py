"""Overseas futures TC2 (정정/취소 확인) against frames LS actually sent.

Frames: ``fixtures/tc_frames_paper_futures_20261015.json`` — LS paper overseas
futures, 2026-10-15, HMHV26, login id and account number replaced. The chain:

    27  new buy 2 @23000
    35  modify of 27 → 22990, OrdQty 2 (both lots moved)      TC2 HO02 ordr_ccd 2, orgn 27
    38  modify of 35 → 22980, OrdQty 1 (35 keeps 1 lot)       TC2 HO02 ordr_ccd 2, orgn 35
    40  cancel of 38                                          TC2 HO02 ordr_ccd 3, orgn 38
    41  cancel of 35                                          TC2 HO02 ordr_ccd 3, orgn 35
    614 new buy 1 (filled), 615 new sell 1 (filled)            no TC2 at all

Before 2.6.7 the handler used ``ordr_no`` (the modify/cancel's own number) and
mapped ``s_b_ccd "1"`` to buy; the guide and the capture say 1 = sell. It never
ran in practice because finance ≤ 2.0.3 handed it ``body=None`` (TC2 sends
``user_id``; the model required ``userid``).

Bodies are built with the frame's own field names (``SimpleNamespace``), so the
engine logic is tested independently of the installed SDK; the last test runs
the SDK model too when the installed finance can read these frames (≥ 2.0.4).
"""

import asyncio
import json
import logging
import sqlite3
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest

from programgarden.context import ExecutionContext
from programgarden.database.workflow_position_tracker import WorkflowPositionTracker
from programgarden.executor import (
    BrokerNodeExecutor,
    RealOrderEventNodeExecutor,
    _FUTURES_EVENT_SIDE,
    _apply_futures_tc2_confirmation,
)

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "tc_frames_paper_futures_20261015.json").read_text(encoding="utf-8"))
DATE = "20261015"


def frame(code, order_no, service=None):
    for item in FIXTURE["tc_frames"]:
        f = item["frame"]
        if f["header"]["tr_cd"] == code and f["body"]["ordr_no"] == order_no and (service is None or f["body"]["svc_id"] == service):
            return f
    raise KeyError((code, order_no, service))


def tc2(order_no, **overrides):
    return SimpleNamespace(**{**frame("TC2", order_no)["body"], **overrides})


def _context(tmp_path, product="overseas_futures"):
    ctx = ExecutionContext(job_id="tc2-offline", workflow_id="offline")
    tracker = WorkflowPositionTracker(str(tmp_path / "ledger.sqlite"), ctx.job_id, "broker", product=product)
    ctx._workflow_position_tracker = tracker
    ctx._workflow_risk_tracker = MagicMock()
    return ctx, tracker


def _record(ctx, order_no, quantity, price, *, side="buy", symbol="HMHV26", new=True):
    # new=True: NewOrderNode path; new=False: ModifyOrderNodeExecutor._record_modified_order path.
    ctx.record_workflow_order(order_no=order_no, order_date=DATE, symbol=symbol, exchange="HKEX", side=side,
                              quantity=quantity, price=price, node_id="order", register_risk=new)


def _rows(tracker):
    with sqlite3.connect(tracker.db_path) as conn:
        return {r[0]: (r[1], r[2], r[3], r[4]) for r in conn.execute(
            "SELECT order_no, product, side, quantity, price FROM workflow_orders ORDER BY order_no")}


def test_side_codes_follow_the_guide_and_the_capture():
    # Guide apis[30] TC1/TC2/TC3 s_b_ccd: 1 = 매도, 2 = 매수.
    assert _FUTURES_EVENT_SIDE == {"1": "sell", "2": "buy"}
    assert frame("TC1", "615", "HO01")["body"]["s_b_ccd"] == "1"  # CIDBT00100 BnsTpCode "1" (sell)
    assert frame("TC1", "614", "HO01")["body"]["s_b_ccd"] == "2"  # BnsTpCode "2" (buy)


@pytest.mark.asyncio
async def test_cancel_confirmation_cancels_the_original_order_not_the_cancel_number(tmp_path):
    ctx, tracker = _context(tmp_path)
    _record(ctx, "38", 1, 22980.0)
    # An unrelated same-day row numbered like the cancel (another product sharing
    # the database). The old handler cancelled order_no=ordr_no ("40") and the
    # tracker's legacy cancel does not filter by product.
    other = WorkflowPositionTracker(tracker.db_path, ctx.job_id, "broker", product="overseas_stock")
    other.record_order(order_no="40", order_date=DATE, symbol="AAPL", exchange="NASDAQ", side="buy",
                       quantity=1, price=1.0, job_id=ctx.job_id, node_id="order")
    assert await _apply_futures_tc2_confirmation(ctx, tc2("40")) == "cancelled"
    rows = _rows(tracker)
    assert "38" not in rows
    assert rows["40"][0] == "overseas_stock"


@pytest.mark.asyncio
async def test_split_modify_chain_cancels_each_link_separately(tmp_path):
    ctx, tracker = _context(tmp_path)
    _record(ctx, "27", 2, 23000.0)
    _record(ctx, "35", 2, 22990.0, new=False)
    _record(ctx, "38", 1, 22980.0, new=False)
    assert await _apply_futures_tc2_confirmation(ctx, tc2("40")) == "cancelled"   # cancel of 38
    assert set(_rows(tracker)) == {"27", "35"}
    assert await _apply_futures_tc2_confirmation(ctx, tc2("41")) == "cancelled"   # cancel of 35
    assert set(_rows(tracker)) == {"27"}, "the chain head (mthr_ordr_no) is never the cancel target"


@pytest.mark.asyncio
async def test_engine_issued_modify_updates_the_recorded_successor_only(tmp_path):
    ctx, tracker = _context(tmp_path)
    _record(ctx, "27", 2, 23000.0)
    _record(ctx, "35", 2, 22990.0, new=False)
    _record(ctx, "38", 1, 22980.0, new=False)
    assert await _apply_futures_tc2_confirmation(ctx, tc2("35")) == "modified"
    assert await _apply_futures_tc2_confirmation(ctx, tc2("38")) == "modified"
    rows = _rows(tracker)
    assert rows["27"][1:] == ("buy", 2, 23000.0)
    assert rows["35"][1:] == ("buy", 2, 22990.0)
    assert rows["38"][1:] == ("buy", 1, 22980.0)
    ctx._workflow_risk_tracker.register_symbol.assert_called_once()  # only the new order, never a confirmation


@pytest.mark.asyncio
async def test_confirmed_quantity_and_price_are_written_to_the_successor(tmp_path):
    ctx, tracker = _context(tmp_path)
    _record(ctx, "35", 2, 22990.0)
    _record(ctx, "38", 2, 22000.0, new=False)  # recorded with the requested values
    assert await _apply_futures_tc2_confirmation(ctx, tc2("38")) == "modified"
    assert _rows(tracker)["38"][2:] == (1, 22980.0)  # cnfr_q 1, ordr_prc 22980 from the frame
    assert _rows(tracker)["35"][2:] == (2, 22990.0)


@pytest.mark.asyncio
async def test_outside_modify_of_an_owned_order_is_logged_not_recorded(tmp_path, caplog):
    ctx, tracker = _context(tmp_path)
    _record(ctx, "27", 2, 23000.0)
    with caplog.at_level(logging.INFO, logger="programgarden.executor"):
        assert await _apply_futures_tc2_confirmation(ctx, tc2("35")) == "modified_outside"
    assert set(_rows(tracker)) == {"27"}
    assert _rows(tracker)["27"][2:] == (2, 23000.0)
    assert "modified outside this workflow" in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize("order_no", ["35", "38", "40", "41"])
async def test_confirmations_for_orders_this_workflow_does_not_own_change_nothing(tmp_path, order_no):
    ctx, tracker = _context(tmp_path)
    _record(ctx, "614", 1, 24123.0)
    assert await _apply_futures_tc2_confirmation(ctx, tc2(order_no)) == "not_a_workflow_order"
    assert set(_rows(tracker)) == {"614"}


@pytest.mark.asyncio
@pytest.mark.parametrize("row_side, row_symbol", [("sell", "HMHV26"), ("buy", "MNQZ26")])
async def test_side_or_symbol_mismatch_changes_nothing(tmp_path, row_side, row_symbol):
    ctx, tracker = _context(tmp_path)
    # A row under the same number with another side or symbol is not this order.
    _record(ctx, "38", 1, 22980.0, side=row_side, symbol=row_symbol)
    assert await _apply_futures_tc2_confirmation(ctx, tc2("40")) == "mismatch"
    assert set(_rows(tracker)) == {"38"}


@pytest.mark.asyncio
@pytest.mark.parametrize("body, outcome", [
    (None, "unreadable"),
    (tc2("40", svc_id="HO03", rfsl_cd="0001", text="rejected"), "not_a_confirmation"),
    (tc2("40", ordr_ccd="1"), "not_modify_or_cancel"),
    (tc2("40", s_b_ccd=""), "unknown_side"),
    (tc2("40", s_b_ccd="9"), "unknown_side"),
    (tc2("40", ordr_dt=""), "no_order_date"),
    (tc2("40", orgn_ordr_no="0"), "no_order_numbers"),
    (tc2("40", orgn_ordr_no="0000000000"), "no_order_numbers"),
])
async def test_frames_that_cannot_be_applied_change_nothing(tmp_path, body, outcome):
    ctx, tracker = _context(tmp_path)
    _record(ctx, "38", 1, 22980.0)
    assert await _apply_futures_tc2_confirmation(ctx, body) == outcome
    assert set(_rows(tracker)) == {"38"}


@pytest.mark.asyncio
async def test_padded_original_number_matches_the_ledger(tmp_path):
    ctx, tracker = _context(tmp_path)
    _record(ctx, "38", 1, 22980.0)
    assert await _apply_futures_tc2_confirmation(ctx, tc2("40", orgn_ordr_no="0000000038")) == "cancelled"
    assert _rows(tracker) == {}


# ---------------------------------------------------------------------------
# Wiring: the SDK listener thread hands the frame to the event loop
# ---------------------------------------------------------------------------

class _Stream:
    def __init__(self):
        self.callbacks = []

    def __getattr__(self, name):
        if name.startswith("on_") and name.endswith("_message"):
            return self.callbacks.append
        raise AttributeError(name)


async def _subscribed(monkeypatch, ctx):
    tc2_stream, tc3_stream = _Stream(), _Stream()

    async def connect():
        return None

    real = SimpleNamespace(connect=connect, TC2=lambda: tc2_stream, TC3=lambda: tc3_stream)
    ls = SimpleNamespace(overseas_futureoption=lambda: SimpleNamespace(real=lambda: real))
    monkeypatch.setattr(BrokerNodeExecutor, "_active_trackers", {})
    scheduled = []
    original = asyncio.run_coroutine_threadsafe

    def schedule(coroutine, loop):
        future = original(coroutine, loop)
        scheduled.append(future)
        return future

    monkeypatch.setattr(asyncio, "run_coroutine_threadsafe", schedule)
    ctx.log = Mock()
    await BrokerNodeExecutor()._subscribe_overseas_futures_fill_events(ls, "broker", ctx)
    return tc2_stream.callbacks[0], scheduled


async def _deliver(callback, scheduled, response):
    thread = threading.Thread(target=callback, args=(response,))
    thread.start()
    thread.join(timeout=2)
    assert not thread.is_alive()
    return [await asyncio.wait_for(asyncio.wrap_future(f), timeout=2) for f in scheduled]


@pytest.mark.asyncio
async def test_listener_applies_the_confirmation_on_the_event_loop(tmp_path, monkeypatch):
    ctx, tracker = _context(tmp_path)
    _record(ctx, "38", 1, 22980.0)
    callback, scheduled = await _subscribed(monkeypatch, ctx)
    assert await _deliver(callback, scheduled, SimpleNamespace(body=tc2("40"))) == ["cancelled"]
    assert _rows(tracker) == {}


@pytest.mark.asyncio
async def test_listener_ignores_a_frame_the_sdk_could_not_read(tmp_path, monkeypatch):
    # finance ≤ 2.0.3 delivered every TC2 frame like this.
    ctx, tracker = _context(tmp_path)
    _record(ctx, "38", 1, 22980.0)
    callback, scheduled = await _subscribed(monkeypatch, ctx)
    unreadable = SimpleNamespace(header=None, body=None, rsp_cd="", rsp_msg="", error_msg="validation error")
    assert await _deliver(callback, scheduled, unreadable) == ["unreadable"]
    assert set(_rows(tracker)) == {"38"}


# ---------------------------------------------------------------------------
# RealOrderEventNode: unreadable frames no longer fire the node
# ---------------------------------------------------------------------------

class _EventContext:
    is_shutdown = False
    is_deep_validate = False

    def __init__(self):
        self.handlers, self.outputs, self.events = {}, [], []

    def register_order_event_handler(self, product, tr_cd, node_id, event_filter, handler):
        self.handlers[tr_cd] = handler

    def has_order_event_subscription(self, product):
        return True

    def get_order_event_real_client(self, product):
        return Mock()

    def register_persistent(self, node_id, client, metadata=None):
        pass

    def register_cleanup_on_flow_end(self, node_id, client):
        pass

    def set_output(self, node_id, port, data):
        self.outputs.append((port, data))

    async def notify_output_update(self, **kwargs):
        pass

    async def emit_event(self, **kwargs):
        self.events.append(kwargs)

    def log(self, level, message, node_id=None, data=None):
        pass


@pytest.mark.asyncio
async def test_order_event_node_skips_unreadable_frames_and_routes_confirmations():
    context = _EventContext()
    await RealOrderEventNodeExecutor()._ls_futures_order_event(
        ls=Mock(), node_id="evt", config={}, context=context, stay_connected=True, event_filter="all")
    handler = context.handlers["TC2"]
    handler(SimpleNamespace(header=None, body=None, error_msg="validation error"))
    await asyncio.sleep(0)
    assert context.outputs == [] and context.events == []
    handler(SimpleNamespace(body=tc2("35")))
    handler(SimpleNamespace(body=tc2("40")))
    await asyncio.sleep(0)
    assert [(port, data["order_no"], data["orig_order_no"], data["side"]) for port, data in context.outputs] == [
        ("modified", "35", "27", "2"), ("cancelled", "40", "38", "2")]


@pytest.mark.asyncio
async def test_with_the_installed_sdk_model_when_it_reads_ls_frames(tmp_path):
    from programgarden_finance.ls.overseas_futureoption.real.TC2.blocks import TC2RealResponseBody

    raw = frame("TC2", "40")["body"]
    try:
        body = TC2RealResponseBody.model_validate(raw)
    except Exception:
        pytest.skip("installed programgarden-finance cannot read LS TC2 frames (fixed in 2.0.4)")
    ctx, tracker = _context(tmp_path)
    _record(ctx, "38", 1, 22980.0)
    assert await _apply_futures_tc2_confirmation(ctx, body) == "cancelled"
    assert _rows(tracker) == {}
