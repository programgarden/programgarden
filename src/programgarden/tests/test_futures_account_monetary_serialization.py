"""Actual SDK models through initial and tick account outputs; synthetic, offline only."""

import asyncio
from decimal import Decimal
import logging
import socket
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from programgarden.context import ExecutionContext
from programgarden.executor import AccountNodeExecutor, RealAccountNodeExecutor
from programgarden_finance.ls.overseas_futureoption.accno.CIDBQ01500.blocks import CIDBQ01500OutBlock2
from programgarden_finance.ls.overseas_futureoption.extension.models import FuturesPositionItem
from programgarden_finance.ls.overseas_futureoption.extension.symbol_spec_manager import SymbolSpec
from programgarden_finance.ls.overseas_futureoption.extension.tracker import FuturesAccountTracker


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Account serialization tests must remain offline")
    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket.socket, "connect_ex", denied)
    monkeypatch.setattr(socket.socket, "sendto", denied)


def response(rows):
    return SimpleNamespace(rsp_cd="00000", rsp_msg="Synthetic fixture", block2=rows)


def sdk_tracker(currency="HKD", current=25010, with_spec=True):
    row = CIDBQ01500OutBlock2(
        IsuCodeVal="HMH_SYNTHETIC", CrcyCodeVal=currency, BnsTpCode="2",
        PchsPrc=25000, OvrsDrvtNowPrc=current, AbrdFutsEvalPnlAmt=777, BalQty=1,
    )
    account = SimpleNamespace(CIDBQ01500=lambda **kwargs: SimpleNamespace(
        req_async=AsyncMock(return_value=response([row])),
    ))
    tracker = FuturesAccountTracker(account, market_client=None)
    if with_spec:
        tracker._spec_manager._specs[row.IsuCodeVal] = SymbolSpec(
            symbol=row.IsuCodeVal, currency=currency, tick_size=Decimal("1"),
            tick_value=Decimal("10"), exchange_code="SYNTHETIC", decimal_places=0,
        )
    # Keep actual fetch/model/calculator/callback behavior; replace only transport
    # startup so no WebSocket, periodic task, or master request is started.
    tracker.start = tracker._fetch_positions
    return tracker


async def start_account_node(tracker):
    real = SimpleNamespace(is_connected=AsyncMock(return_value=True), connect=AsyncMock())
    account = SimpleNamespace(account_tracker=lambda **kwargs: tracker)
    ls = SimpleNamespace(overseas_futureoption=lambda: SimpleNamespace(
        accno=lambda: account, market=lambda: None, real=lambda: real,
    ))
    context = ExecutionContext(job_id="synthetic-account", workflow_id="synthetic-account")
    context.notify_output_update = AsyncMock()
    context.emit_event = AsyncMock()
    context.register_cleanup_on_flow_end = Mock()
    result = await RealAccountNodeExecutor()._ls_futureoption_with_tracker(
        ls, "account", {"_trigger_on_update_nodes": ["synthetic-display"]}, context,
        sync_interval_sec=60, stay_connected=False,
    )
    # Drain only finite local callback scheduling, without wall-clock sleeps.
    for _ in range(4):
        await asyncio.sleep(0)
    return result, context


@pytest.mark.asyncio
@pytest.mark.parametrize("current", [25010, 25000, 24990])
async def test_actual_sdk_initial_and_tick_keep_native_money_and_broker_raw(current, caplog):
    caplog.set_level(logging.DEBUG, logger="programgarden.executor")
    tracker = sdk_tracker(current=current)
    result, context = await start_account_node(tracker)
    initial = result["positions"][0]
    assert initial["pnl_amount"] == (current - 25000) * 10
    assert initial["pnl_currency"] == initial["currency"] == "HKD"
    assert initial["pnl_basis"] == "estimated_gross_price_change"
    assert initial["pnl_status"] == "available"
    assert initial["broker_pnl_amount"] == 777
    assert initial["broker_pnl_basis"] == "broker_reported_unconfirmed"

    for price, expected in [(current, initial["pnl_amount"]), (25000, 0), (24999, -10)]:
        context.emit_event.reset_mock()
        context.notify_output_update.reset_mock()
        tracker._on_tick_received(SimpleNamespace(body=SimpleNamespace(
            symbol="HMH_SYNTHETIC", curpr=price,
        )))
        for _ in range(4):
            await asyncio.sleep(0)
        context.emit_event.assert_awaited_once()
        emitted = context.emit_event.await_args.kwargs
        assert emitted["trigger_nodes"] == ["synthetic-display"]
        position = emitted["data"]["positions"][0]
        assert position["pnl_amount"] == expected
        assert position["pnl_currency"] == "HKD"
        assert position["pnl_basis"] == initial["pnl_basis"]
        assert position["broker_pnl_amount"] == 777
        assert position == RealAccountNodeExecutor()._get_overseas_futures_tracker_data(tracker)["positions"][0]
        assert context.notify_output_update.await_args.kwargs["outputs"]["positions"] == [position]
    messages = [r.getMessage() for r in caplog.records if r.getMessage().startswith("Futures position ")]
    assert messages and all("$" not in message for message in messages)
    assert any("pnl_currency=HKD" in message for message in messages)


@pytest.mark.asyncio
@pytest.mark.parametrize("currency", ["HKD", ""])
async def test_missing_spec_initial_and_tick_publish_null_without_format_exception(currency, caplog):
    caplog.set_level(logging.DEBUG, logger="programgarden.executor")
    tracker = sdk_tracker(currency=currency, with_spec=False)
    result, context = await start_account_node(tracker)
    initial = result["positions"][0]
    assert initial["pnl_amount"] is None
    assert initial["pnl_currency"] is None and initial["pnl_basis"] is None
    assert initial["pnl_status"] == "unavailable"
    assert initial["pnl_unavailable_reason"]
    assert initial["currency"] == currency
    assert initial["broker_pnl_amount"] == 777
    context.emit_event.reset_mock()
    tracker._on_tick_received(SimpleNamespace(body=SimpleNamespace(symbol="HMH_SYNTHETIC", curpr=25011)))
    for _ in range(4):
        await asyncio.sleep(0)
    context.emit_event.assert_awaited_once()  # The old None formatting swallowed this callback.
    updated = context.emit_event.await_args.kwargs["data"]["positions"][0]
    assert updated["pnl_amount"] is None and updated["current_price"] == 25011
    assert updated["broker_pnl_amount"] == 777
    assert any("pnl_amount=None" in record.getMessage() for record in caplog.records)


@pytest.mark.parametrize("amount", [None, Decimal("0"), Decimal("-12.5")])
def test_actual_model_preserves_nullable_broker_amount(amount):
    pos = FuturesPositionItem(symbol="SYNTHETIC", broker_pnl_amount=amount)
    tracker = SimpleNamespace(get_positions=lambda: {pos.symbol: pos}, get_balance=lambda: {})
    output = RealAccountNodeExecutor()._get_overseas_futures_tracker_data(tracker)["positions"][0]
    assert output["broker_pnl_amount"] == amount
    assert output["pnl_amount"] is None and output["currency"] == ""


@pytest.mark.asyncio
async def test_registered_callback_does_not_raise_for_unavailable_amount():
    tracker = sdk_tracker(with_spec=False)
    _, context = await start_account_node(tracker)
    context.emit_event.reset_mock()
    # Invoke the actual registered callback directly so the SDK's exception
    # swallowing cannot hide a nullable debug-formatting failure.
    callback, = tracker._on_position_change_callbacks
    callback(tracker.get_positions())
    for _ in range(4):
        await asyncio.sleep(0)
    context.emit_event.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("amount", [None, 0, -12.5, 100])
@pytest.mark.parametrize("currency", ["HKD", ""])
async def test_direct_rest_preserves_supplied_raw_amount_without_inventing_estimate(amount, currency):
    fields = dict(IsuCodeVal="SYNTHETIC", CrcyCodeVal=currency, BnsTpCode="2",
                  PchsPrc=25000, OvrsDrvtNowPrc=25010, BalQty=1)
    if amount is not None:
        fields["AbrdFutsEvalPnlAmt"] = amount
    row = CIDBQ01500OutBlock2(**fields)
    account = SimpleNamespace(
        CIDBQ01500=lambda **kwargs: SimpleNamespace(req_async=AsyncMock(return_value=response([row]))),
        CIDBQ05300=lambda **kwargs: SimpleNamespace(req_async=AsyncMock(return_value=SimpleNamespace(block2=[], block3=None))),
    )
    ls = SimpleNamespace(overseas_futureoption=lambda: SimpleNamespace(accno=lambda: account))
    result = await AccountNodeExecutor()._ls_overseas_futureoption(ls, "account", SimpleNamespace(log=Mock()))
    position = result["positions"][0]
    assert position["broker_pnl_amount"] == amount
    assert position["broker_pnl_basis"] == "broker_reported_unconfirmed"
    assert position["pnl_amount"] is None and position["pnl_currency"] is None
    assert position["pnl_basis"] is None and position["pnl_status"] == "unavailable"
    assert position["pnl_unavailable_reason"] == "native_estimate_requires_contract_metadata"
    assert position["currency"] == currency
    assert position["pnl_rate"] == 0.04
