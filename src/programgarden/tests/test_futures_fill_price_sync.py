"""Futures fill-price recovery reads CIDBQ01800 order rows (engine 2.7.0).

Before 2.7.0, ``BrokerNodeExecutor._sync_overseas_futures_fill_prices`` called a
method the finance client does not have, sent ``CIDBQ01800InBlock`` (the model is
``CIDBQ01800InBlock1``) and read ``OrdNo``/``ExecPrc`` (the rows carry
``OvrsFutsOrdNo``/``AbrdFutsExecPrc``): every attempt ended in a logged warning
and no price was recovered. The rows here are the LS paper capture of
2026-10-15 (finance ``tests/fixtures/tc_frames_paper_futures_20261015.json``):
orders 614 and 615 were filled at 24114 and 24104; 27/35/38 were modified or
cancelled without a fill.
"""
import json
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from programgarden.executor import BrokerNodeExecutor
from programgarden_finance.ls.overseas_futureoption.accno.CIDBQ01800.blocks import (
    CIDBQ01800OutBlock2,
    CIDBQ01800Response,
)

CAPTURE = json.loads((Path(__file__).resolve().parents[2] / "finance" / "tests" / "fixtures"
                      / "tc_frames_paper_futures_20261015.json").read_text(encoding="utf-8"))
END_OF_RUN = next(s for s in CAPTURE["cidbq01800"] if s["label"].startswith("end of run"))
# The recovery reads only today's and yesterday's orders (local dates, the
# clock the order path stamps the ledger with), so the captured rows are
# answered for orders dated today.
TODAY = date.today().strftime("%Y%m%d")
YESTERDAY = (date.today() - timedelta(days=1)).strftime("%Y%m%d")
LONG_AGO = (date.today() - timedelta(days=5)).strftime("%Y%m%d")


def _client(response, requests):
    def CIDBQ01800(body):
        requests.append(body)
        return SimpleNamespace(req_async=AsyncMock(return_value=response))
    return SimpleNamespace(overseas_futureoption=lambda: SimpleNamespace(
        accno=lambda: SimpleNamespace(CIDBQ01800=CIDBQ01800)))


def _context():
    synced, logs = [], []

    def sync(history):
        synced.extend(history)
        return len(history)
    return SimpleNamespace(sync_workflow_fill_prices_from_history=sync,
                           log=lambda level, message, *a, **k: logs.append((level, message))), synced, logs


def _captured_response():
    return CIDBQ01800Response(
        block2=[CIDBQ01800OutBlock2.model_validate(row) for row in END_OF_RUN["rows"]],
        rsp_cd=END_OF_RUN["rsp_cd"], rsp_msg=END_OF_RUN["rsp_msg"])


@pytest.mark.asyncio
async def test_filled_orders_get_the_captured_execution_price():
    requests = []
    context, synced, logs = _context()
    orders = [
        {"order_no": "614", "order_date": TODAY},
        {"order_no": "0000000615", "order_date": TODAY},  # a zero-padded ledger value also matches
        {"order_no": "38", "order_date": TODAY},          # cancelled, never filled
    ]
    await BrokerNodeExecutor()._sync_overseas_futures_fill_prices(
        _client(_captured_response(), requests), orders, context, "broker")
    assert synced == [
        {"order_no": "614", "order_date": TODAY, "fill_price": 24114.0},
        {"order_no": "0000000615", "order_date": TODAY, "fill_price": 24104.0},
    ]
    assert len(requests) == 1
    body = requests[0]
    assert (body.OrdDt, body.OrdStatCode, body.BnsTpCode, body.IsuCodeVal) == (TODAY, "0", "0", "")
    assert not [entry for entry in logs if entry[0] == "warning"]


@pytest.mark.asyncio
async def test_one_read_per_order_date_and_nothing_for_unknown_rows():
    requests = []
    context, synced, _ = _context()
    orders = [{"order_no": "999", "order_date": YESTERDAY}, {"order_no": "998", "order_date": TODAY},
              {"order_no": "", "order_date": TODAY}, {"order_no": "5", "order_date": "bad"}]
    await BrokerNodeExecutor()._sync_overseas_futures_fill_prices(
        _client(_captured_response(), requests), orders, context, "broker")
    assert sorted(r.OrdDt for r in requests) == sorted([YESTERDAY, TODAY])
    assert synced == []


@pytest.mark.asyncio
async def test_a_failed_read_is_logged_not_written():
    context, synced, logs = _context()
    failed = CIDBQ01800Response(block2=[], rsp_cd="", rsp_msg="", error_msg="HTTP 500")
    await BrokerNodeExecutor()._sync_overseas_futures_fill_prices(
        _client(failed, []), [{"order_no": "614", "order_date": TODAY}], context, "broker")
    assert synced == []
    assert any(level == "warning" and "CIDBQ01800" in message for level, message in logs)


@pytest.mark.asyncio
async def test_the_ledger_price_is_updated_through_the_real_tracker(tmp_path):
    from programgarden.database.workflow_position_tracker import WorkflowPositionTracker
    tracker = WorkflowPositionTracker(db_path=str(tmp_path / "ledger.db"), job_id="job", broker_node_id="broker",
                                      product="overseas_futures", provider="ls", trading_mode="paper")
    tracker.record_order(order_no="614", order_date=TODAY, symbol="HMHV26", exchange="HKEX",
                         side="buy", quantity=1, price=0, job_id="job", node_id="order")
    context, _, _ = _context()
    context.sync_workflow_fill_prices_from_history = tracker.sync_fill_prices_from_history
    await BrokerNodeExecutor()._sync_overseas_futures_fill_prices(
        _client(_captured_response(), []), tracker.get_orders_without_fill_price(), context, "broker")
    assert tracker.get_orders_without_fill_price() == []


# ---------------------------------------------------------------------------
# 2.7.0 review M1: the recovery is bounded. The broker node re-runs every
# scheduled cycle and starts this background read again, while the ledger keeps
# unpriced rows forever (orders cancelled before a fill, any date, any product).
# The read must not become one CIDBQ01800 call per date per cycle.
# ---------------------------------------------------------------------------


def _run_context(orders):
    """A context object that keeps attributes between calls, like one run."""
    context, synced, logs = _context()
    context.get_workflow_orders_without_fill_price = lambda: list(orders)
    return context, synced, logs


@pytest.mark.asyncio
async def test_orders_older_than_yesterday_cause_no_read_and_no_login():
    requests = []
    context, synced, _ = _run_context([
        {"order_no": "38", "order_date": LONG_AGO, "product": "overseas_futures", "symbol": "HMHV26"},
    ])
    logins = []

    def fake_login(*args, **kwargs):
        logins.append(args)
        return _client(_captured_response(), requests), True, None

    with patch("programgarden.executor.ensure_ls_login", fake_login):
        await BrokerNodeExecutor()._sync_fill_prices_from_history(
            node_id="broker", product="overseas_futures", appkey="k", appsecret="s",
            paper_trading=True, context=context)
    assert logins == [] and requests == [] and synced == []


@pytest.mark.asyncio
async def test_the_same_unpriced_order_is_read_once_per_run():
    requests = []
    context, synced, _ = _run_context([])
    orders = [{"order_no": "38", "order_date": TODAY, "product": "overseas_futures", "symbol": "HMHV26"}]
    executor = BrokerNodeExecutor()
    for _cycle in range(3):  # three scheduled cycles of the same run
        await executor._sync_overseas_futures_fill_prices(
            _client(_captured_response(), requests), orders, context, "broker")
    assert len(requests) == 1
    assert synced == []


@pytest.mark.asyncio
async def test_a_new_unpriced_order_on_a_read_date_gets_one_more_read():
    requests = []
    context, synced, _ = _run_context([])
    executor = BrokerNodeExecutor()
    first = [{"order_no": "38", "order_date": TODAY, "product": "overseas_futures", "symbol": "HMHV26"}]
    await executor._sync_overseas_futures_fill_prices(
        _client(_captured_response(), requests), first, context, "broker")
    second = first + [{"order_no": "614", "order_date": TODAY, "product": "overseas_futures", "symbol": "HMHV26"}]
    await executor._sync_overseas_futures_fill_prices(
        _client(_captured_response(), requests), second, context, "broker")
    await executor._sync_overseas_futures_fill_prices(
        _client(_captured_response(), requests), second, context, "broker")
    assert len(requests) == 2
    assert synced == [{"order_no": "614", "order_date": TODAY, "fill_price": 24114.0}]


@pytest.mark.asyncio
async def test_rows_of_other_products_are_not_read():
    requests = []
    context, synced, _ = _run_context([])
    orders = [{"order_no": "614", "order_date": TODAY, "product": "overseas_stock", "symbol": "AAPL"},
              {"order_no": "615", "order_date": TODAY, "product": "korea_stock", "symbol": "005930"}]
    await BrokerNodeExecutor()._sync_overseas_futures_fill_prices(
        _client(_captured_response(), requests), orders, context, "broker")
    assert requests == [] and synced == []


@pytest.mark.asyncio
async def test_a_price_is_written_only_when_order_number_and_symbol_match():
    requests = []
    context, synced, _ = _run_context([])
    orders = [{"order_no": "614", "order_date": TODAY, "product": "overseas_futures", "symbol": "NQZ26"},
              {"order_no": "615", "order_date": TODAY, "product": "overseas_futures", "symbol": "HMHV26"}]
    await BrokerNodeExecutor()._sync_overseas_futures_fill_prices(
        _client(_captured_response(), requests), orders, context, "broker")
    assert synced == [{"order_no": "615", "order_date": TODAY, "fill_price": 24104.0}]


@pytest.mark.asyncio
async def test_repeated_read_failures_warn_once_then_log_at_debug():
    context, synced, logs = _run_context([])
    failed = CIDBQ01800Response(block2=[], rsp_cd="", rsp_msg="", error_msg="HTTP 500")
    executor = BrokerNodeExecutor()
    for order_no in ("614", "615", "616"):
        await executor._sync_overseas_futures_fill_prices(
            _client(failed, []),
            [{"order_no": order_no, "order_date": TODAY, "product": "overseas_futures", "symbol": "HMHV26"}],
            context, "broker")
    failures = [level for level, message in logs if "CIDBQ01800" in message]
    assert failures == ["warning", "debug", "debug"]
    assert synced == []
