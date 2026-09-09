"""Exercise the real broker callback and listeners without network access."""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from programgarden.context import ExecutionContext
from programgarden.executor import BrokerNodeExecutor
from programgarden.futures_pnl import GROSS_BASIS, futures_pnl_metadata


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    import socket

    def denied(*args, **kwargs):
        raise AssertionError("Currency integration tests must remain offline")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket.socket, "connect_ex", denied)
    monkeypatch.setattr(socket.socket, "sendto", denied)


def position(currency="HKD", amount=Decimal("100"), **changes):
    values = dict(
        quantity=1, entry_price=25000, current_price=25010, pnl_rate=0.04,
        pnl_amount=amount, currency=currency, pnl_currency=currency,
        pnl_basis=GROSS_BASIS, pnl_status="available",
        pnl_unavailable_reason=None, broker_pnl_amount=Decimal("97"),
        broker_pnl_basis="broker_reported_unconfirmed", is_long=True,
    )
    return SimpleNamespace(**(values | changes))


async def callback_event(positions):
    events = []

    async def observe(event):
        events.append(event)

    context = ExecutionContext(job_id="currency-test", workflow_id="currency-workflow")
    context.add_listener(SimpleNamespace(on_workflow_pnl_update=observe))
    context.add_listener(SimpleNamespace(on_workflow_pnl_update=observe, pnl_start_date="20260909"))
    callback = None

    def register(value):
        nonlocal callback
        callback = value

    tracker = SimpleNamespace(
        start=AsyncMock(), stop=AsyncMock(), get_positions=lambda: positions,
        on_account_pnl_change=register,
    )
    real = SimpleNamespace(connect=AsyncMock(), close=AsyncMock())
    account = SimpleNamespace(account_tracker=lambda **kwargs: tracker)
    ls = SimpleNamespace(overseas_futureoption=lambda: SimpleNamespace(
        accno=lambda: account, real=lambda: real, market=lambda: object(),
    ))
    executor = BrokerNodeExecutor()
    await executor._start_overseas_futures_tracker(ls, "broker", "overseas_futures", "ls", context)
    callback(SimpleNamespace(currency="USD"))  # A stale aggregate label must not win.
    await executor.cleanup_fill_subscriptions(context.job_id)
    assert len(events) == 2
    assert events[1].competition_start_date == "20260909"
    return events


@pytest.mark.asyncio
@pytest.mark.parametrize("amount", [Decimal("100"), Decimal("0"), Decimal("-25")])
async def test_native_estimate_reaches_actual_listener_without_workflow_money(amount):
    events = await callback_event({"HMH_SYNTHETIC": position(amount=amount)})
    for event in events:
        assert event.currency == "HKD"
        assert event.monetary_status == "estimated"
        assert event.pnl_by_currency["HKD"]["total_pnl_amount"] == amount
        assert event.monetary_positions["HMH_SYNTHETIC"]["broker_pnl_amount"] == 97
        assert event.workflow_pnl_amount is None and event.total_pnl_amount is None
        assert event.workflow_pnl_rate is None and event.account_total_pnl_rate is None
        assert event.account_total_pnl_amount is None
        assert event.competition_workflow_pnl_amount is None
        assert event.workflow_positions == [] and event.other_positions == []


@pytest.mark.asyncio
async def test_mixed_currencies_remain_separate_through_callback():
    events = await callback_event({
        "HMH_SYNTHETIC": position(),
        "USD_SYNTHETIC": position("USD", Decimal("10")),
    })
    for event in events:
        assert event.currency is None
        assert event.pnl_by_currency["HKD"]["total_pnl_amount"] == 100
        assert event.pnl_by_currency["USD"]["total_pnl_amount"] == 10
        assert event.total_pnl_amount is None


@pytest.mark.asyncio
async def test_missing_or_incompatible_evidence_never_uses_price_fallback():
    events = await callback_event({"HMH_SYNTHETIC": position(
        pnl_amount=None, pnl_currency=None, pnl_basis=None, pnl_status="unavailable",
    )})
    for event in events:
        assert event.currency is None and event.monetary_status == "unavailable"
        assert event.pnl_by_currency == {}
        assert event.unavailable_position_count == 1
        assert event.total_pnl_amount is None and event.account_total_pnl_amount is None


@pytest.mark.parametrize("bad_amount", [None, True, "NaN", "Infinity", "not-a-number"])
def test_unavailable_scalar_cannot_become_a_currency_bucket(bad_amount):
    evidence = vars(position(amount=bad_amount))
    result = futures_pnl_metadata({"synthetic": evidence})
    assert result["pnl_by_currency"] == {}
    assert result["currency"] is None


@pytest.mark.parametrize("position_currency", [None, "", "USD"])
def test_estimate_currency_must_match_reported_position_currency(position_currency):
    evidence = vars(position(currency=position_currency, pnl_currency="HKD"))
    result = futures_pnl_metadata({"synthetic": evidence})
    assert result["pnl_by_currency"] == {}
    assert result["unavailable_position_count"] == 1


@pytest.mark.asyncio
async def test_fill_notification_without_account_currency_stays_unavailable():
    events = []

    async def observe(event):
        events.append(event)

    context = ExecutionContext(job_id="fill-test", workflow_id="fill-workflow")
    context.add_listener(SimpleNamespace(on_workflow_pnl_update=observe))
    context._workflow_position_tracker = SimpleNamespace(record_fill=AsyncMock(return_value="workflow"))
    context._workflow_broker_node_id = "broker"
    context._workflow_product = "overseas_futures"
    await context.record_workflow_fill(
        order_no="synthetic", order_date="20260909", symbol="HMH_SYNTHETIC", exchange="HKEX",
        side="buy", quantity=1, price=25247, fill_time="120932213", commda_code="40",
    )
    assert len(events) == 1
    assert events[0].currency is None and events[0].total_pnl_amount is None
    assert events[0].monetary_unavailable_reason == "account_positions_unavailable"


@pytest.mark.asyncio
async def test_stock_listener_keeps_existing_numeric_contract():
    events = []

    async def observe(event):
        events.append(event)

    context = ExecutionContext(job_id="stock-test", workflow_id="stock-workflow")
    context.add_listener(SimpleNamespace(on_workflow_pnl_update=observe))
    await context.notify_workflow_pnl(
        "broker", "overseas_stock", "ls", {"synthetic": 110},
        {"synthetic": {"quantity": 1, "buy_price": 100, "current_price": 110,
                       "pnl_rate": 10, "product": "overseas_stock"}}, currency="USD",
    )
    assert events[0].total_pnl_amount == 10
    assert events[0].currency == "USD" and events[0].monetary_status is None


@pytest.mark.asyncio
@pytest.mark.parametrize("hkd_current", [25010, 25000, 24990])
async def test_actual_sdk_rest_and_tick_reach_listeners_in_native_currency(hkd_current):
    from programgarden_finance.ls.overseas_futureoption.accno.CIDBQ01500.blocks import CIDBQ01500OutBlock2
    from programgarden_finance.ls.overseas_futureoption.extension.symbol_spec_manager import SymbolSpec
    from programgarden_finance.ls.overseas_futureoption.extension.tracker import FuturesAccountTracker

    rows = [CIDBQ01500OutBlock2(
        IsuCodeVal="HMH_SYNTHETIC", CrcyCodeVal="HKD", BnsTpCode="2",
        PchsPrc=25000, OvrsDrvtNowPrc=hkd_current, AbrdFutsEvalPnlAmt=777,
        BalQty=1, CsgnMgn=1000,
    )]
    account = SimpleNamespace(CIDBQ01500=lambda **kwargs: SimpleNamespace(
        req_async=AsyncMock(return_value=SimpleNamespace(
            rsp_cd="00000", rsp_msg="Synthetic fixture", block2=rows,
        )),
    ))
    sdk = FuturesAccountTracker(account, market_client=None)
    sdk._spec_manager._specs["HMH_SYNTHETIC"] = SymbolSpec(
        symbol="HMH_SYNTHETIC", currency="HKD", tick_size=Decimal("1"),
        tick_value=Decimal("10"), exchange_code="SYNTHETIC", decimal_places=0,
    )
    await sdk._fetch_positions()
    for expected, tick in [((hkd_current - 25000) * 10, None), (-50, 24995)]:
        if tick is not None:
            sdk._on_tick_received(SimpleNamespace(body=SimpleNamespace(
                symbol="HMH_SYNTHETIC", curpr=tick,
            )))
        for event in await callback_event(sdk.get_positions()):
            assert event.currency == "HKD"
            assert event.pnl_by_currency["HKD"]["total_pnl_amount"] == expected
            assert event.monetary_positions["HMH_SYNTHETIC"]["broker_pnl_amount"] == 777
            assert event.total_pnl_amount is None and event.account_total_pnl_rate is None
            assert event.competition_account_pnl_rate is None


@pytest.mark.asyncio
async def test_futures_product_guard_does_not_require_repeated_position_product():
    events = []

    async def observe(event):
        events.append(event)

    context = ExecutionContext(job_id="product-guard", workflow_id="product-guard")
    context.add_listener(SimpleNamespace(on_workflow_pnl_update=observe, pnl_start_date="20260909"))
    await context.notify_workflow_pnl("broker", "overseas_futures", "ls", {"synthetic": 110}, {
        "synthetic": {"quantity": 1, "buy_price": 100, "current_price": 110},
    })
    assert events[0].account_total_pnl_amount is None
    assert events[0].competition_account_pnl_amount is None
    assert events[0].currency is None
