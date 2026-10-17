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
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from programgarden.executor import BrokerNodeExecutor
from programgarden_finance.ls.overseas_futureoption.accno.CIDBQ01800.blocks import (
    CIDBQ01800OutBlock2,
    CIDBQ01800Response,
)

CAPTURE = json.loads((Path(__file__).resolve().parents[2] / "finance" / "tests" / "fixtures"
                      / "tc_frames_paper_futures_20261015.json").read_text(encoding="utf-8"))
END_OF_RUN = next(s for s in CAPTURE["cidbq01800"] if s["label"].startswith("end of run"))


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
        {"order_no": "614", "order_date": "20261015"},
        {"order_no": "0000000615", "order_date": "20261015"},  # a zero-padded ledger value also matches
        {"order_no": "38", "order_date": "20261015"},          # cancelled, never filled
    ]
    await BrokerNodeExecutor()._sync_overseas_futures_fill_prices(
        _client(_captured_response(), requests), orders, context, "broker")
    assert synced == [
        {"order_no": "614", "order_date": "20261015", "fill_price": 24114.0},
        {"order_no": "0000000615", "order_date": "20261015", "fill_price": 24104.0},
    ]
    assert len(requests) == 1
    body = requests[0]
    assert (body.OrdDt, body.OrdStatCode, body.BnsTpCode, body.IsuCodeVal) == ("20261015", "0", "0", "")
    assert not [entry for entry in logs if entry[0] == "warning"]


@pytest.mark.asyncio
async def test_one_read_per_order_date_and_nothing_for_unknown_rows():
    requests = []
    context, synced, _ = _context()
    orders = [{"order_no": "999", "order_date": "20261014"}, {"order_no": "998", "order_date": "20261015"},
              {"order_no": "", "order_date": "20261015"}, {"order_no": "5", "order_date": "bad"}]
    await BrokerNodeExecutor()._sync_overseas_futures_fill_prices(
        _client(_captured_response(), requests), orders, context, "broker")
    assert sorted(r.OrdDt for r in requests) == ["20261014", "20261015"]
    assert synced == []


@pytest.mark.asyncio
async def test_a_failed_read_is_logged_not_written():
    context, synced, logs = _context()
    failed = CIDBQ01800Response(block2=[], rsp_cd="", rsp_msg="", error_msg="HTTP 500")
    await BrokerNodeExecutor()._sync_overseas_futures_fill_prices(
        _client(failed, []), [{"order_no": "614", "order_date": "20261015"}], context, "broker")
    assert synced == []
    assert any(level == "warning" and "CIDBQ01800" in message for level, message in logs)


@pytest.mark.asyncio
async def test_the_ledger_price_is_updated_through_the_real_tracker(tmp_path):
    from programgarden.database.workflow_position_tracker import WorkflowPositionTracker
    tracker = WorkflowPositionTracker(db_path=str(tmp_path / "ledger.db"), job_id="job", broker_node_id="broker",
                                      product="overseas_futures", provider="ls", trading_mode="paper")
    tracker.record_order(order_no="614", order_date="20261015", symbol="HMHV26", exchange="HKEX",
                         side="buy", quantity=1, price=0, job_id="job", node_id="order")
    context, _, _ = _context()
    context.sync_workflow_fill_prices_from_history = tracker.sync_fill_prices_from_history
    await BrokerNodeExecutor()._sync_overseas_futures_fill_prices(
        _client(_captured_response(), []), tracker.get_orders_without_fill_price(), context, "broker")
    assert tracker.get_orders_without_fill_price() == []
