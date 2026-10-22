"""Offline monetary-domain regressions; all account data is synthetic."""
from decimal import Decimal
from types import SimpleNamespace
import socket

import pytest

from programgarden_finance.ls.overseas_futureoption.accno.CIDBQ01500.blocks import CIDBQ01500OutBlock2
from programgarden_finance.ls.overseas_futureoption.market.o3121.blocks import O3121OutBlock
from programgarden_finance.ls.overseas_futureoption.extension.calculator import (
    FuturesPnLCalculator, calculate_futures_pnl, calculate_native_gross_pnl,
)
from programgarden_finance.ls.overseas_futureoption.extension.models import FuturesTradeInput
from programgarden_finance.ls.overseas_futureoption.extension.symbol_spec_manager import SymbolSpec, SymbolSpecManager
from programgarden_finance.ls.overseas_futureoption.extension.tracker import FuturesAccountTracker

D = Decimal


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Offline currency tests must not access the network")
    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket.socket, "connect_ex", denied)
    monkeypatch.setattr(socket.socket, "sendto", denied)


def spec(symbol="HMH_SYNTHETIC", currency="HKD", tick_value="10"):
    return SymbolSpec(symbol=symbol, currency=currency, exchange_code="SYNTHETIC",
        tick_size=D("1"), tick_value=D(tick_value), decimal_places=0)


def position_row(symbol="HMH_SYNTHETIC", currency="HKD", entry=25000, current=25010,
                 broker_pnl=777, quantity=1):
    return CIDBQ01500OutBlock2(IsuCodeVal=symbol, CrcyCodeVal=currency, BnsTpCode="2",
        PchsPrc=entry, OvrsDrvtNowPrc=current, AbrdFutsEvalPnlAmt=broker_pnl,
        BalQty=quantity, CsgnMgn=1000)


def tracker_for(rows, specs):
    async def req_async():
        return SimpleNamespace(rsp_cd="00000", rsp_msg="Synthetic fixture", block2=rows)
    account = SimpleNamespace(CIDBQ01500=lambda **kwargs:SimpleNamespace(req_async=req_async))
    tracker = FuturesAccountTracker(account, market_client=None)
    tracker._spec_manager._specs = {item.symbol:item for item in specs}
    return tracker


def test_legacy_usd_estimator_numbers_remain_compatible():
    trade = FuturesTradeInput(symbol="USD_SYNTHETIC", buy_price=100, sell_price=110, qty=1)
    result = calculate_futures_pnl(trade, spec("USD_SYNTHETIC", "USD"))
    assert result.gross_pl_usd == D("100")
    assert result.total_fees_usd == D("15")
    assert result.net_pl_usd == D("85")
    assert result.net_pl_krw == D("119000")


def test_explicit_usd_manual_estimator_remains_supported():
    trade = FuturesTradeInput(symbol="MANUAL", buy_price=4000, sell_price=4001, qty=1,
        manual_tick_size=D("0.25"), manual_tick_value=D("12.5"), manual_currency="USD",
        custom_fee_usd=D("2"), exchange_rate=D("1300"))
    result = calculate_futures_pnl(trade)
    assert result.gross_pl_usd == D("50")
    assert result.net_pl_usd == D("46")
    assert result.exchange_rate_used == D("1300")


def test_existing_manual_usd_default_is_unchanged():
    trade = FuturesTradeInput(symbol="MANUAL", buy_price=1, sell_price=2, qty=1,
        manual_tick_size=1, manual_tick_value=10, custom_fee_usd=0)
    assert trade.manual_currency == "USD"
    assert calculate_futures_pnl(trade).net_pl_usd == D("10")


def test_realtime_standalone_usd_estimator_is_compatible_and_hkd_is_rejected():
    manager = SymbolSpecManager(None)
    manager._specs = {"USD_SYNTHETIC":spec("USD_SYNTHETIC", "USD"), "HMH_SYNTHETIC":spec()}
    calculator = FuturesPnLCalculator(manager)
    result = calculator.calculate_realtime_pnl("USD_SYNTHETIC", 1, D("100"), D("110"))
    assert result.net_pl_usd == D("85")
    with pytest.raises(ValueError, match="usd_estimator_requires_usd_spec"):
        calculator.calculate_realtime_pnl("HMH_SYNTHETIC", 1, D("25000"), D("25010"))


@pytest.mark.parametrize("currency", ["HKD", "EUR", ""])
def test_usd_estimator_rejects_non_usd_spec(currency):
    trade = FuturesTradeInput(symbol="HMH_SYNTHETIC", buy_price=25000, sell_price=25010, qty=1)
    with pytest.raises(ValueError, match="usd_estimator_requires_usd_spec"):
        calculate_futures_pnl(trade, spec(currency=currency))


def test_usd_estimator_rejects_non_usd_manual_amounts():
    trade = FuturesTradeInput(symbol="MANUAL", buy_price=1, sell_price=2, qty=1,
        manual_tick_size=1, manual_tick_value=10, manual_currency="HKD")
    with pytest.raises(ValueError, match="usd_estimator_requires_usd_manual_values"):
        calculate_futures_pnl(trade)


@pytest.mark.parametrize("current,is_long,quantity,expected", [
    (25010, True, 1, "100"), (24990, True, 1, "-100"), (25000, True, 1, "0"),
    (24990, False, 1, "100"), (25010, False, 1, "-100"), (25010, True, 2, "200"),
])
def test_native_hkd_gross_has_no_fee_tax_or_fx(current, is_long, quantity, expected):
    result = calculate_native_gross_pnl(spec=spec(), quantity=quantity, entry_price=D("25000"),
        current_price=D(current), is_long=is_long)
    assert result.amount == D(expected)
    assert result.currency == "HKD"
    assert result.basis == "estimated_gross_price_change"
    assert not any(key.endswith(("_usd", "_krw")) for key in result.model_dump())


@pytest.mark.parametrize("updates", [{"currency":""}, {"tick_size":D("0")}, {"tick_value":D("0")}])
def test_native_estimate_requires_currency_and_tick_metadata(updates):
    with pytest.raises(ValueError):
        calculate_native_gross_pnl(spec=spec().model_copy(update=updates), quantity=1,
            entry_price=D("25000"), current_price=D("25010"))


@pytest.mark.asyncio
async def test_rest_tick_refresh_keeps_native_basis_and_broker_raw_separate():
    tracker = tracker_for([position_row(broker_pnl=777)], [spec()])
    await tracker._fetch_positions()
    pos = tracker.get_positions()["HMH_SYNTHETIC"]
    assert (pos.pnl_amount, pos.pnl_currency, pos.pnl_basis, pos.pnl_status) == (
        D("100"), "HKD", "estimated_gross_price_change", "available")
    assert pos.broker_pnl_amount == D("777")
    assert pos.broker_pnl_basis == "broker_reported_unconfirmed"
    tracker._on_tick_received(SimpleNamespace(body=SimpleNamespace(symbol=pos.symbol, curpr=25010)))
    assert pos.pnl_amount == D("100")
    assert pos.broker_pnl_amount == D("777")
    assert pos.realtime_pnl is None
    tracker._on_tick_received(SimpleNamespace(body=SimpleNamespace(symbol=pos.symbol, curpr=24990)))
    assert pos.pnl_amount == D("-100")
    assert pos.broker_pnl_amount == D("777")
    await tracker._fetch_positions()
    restored = tracker.get_positions()[pos.symbol]
    assert restored.pnl_amount == D("100")
    assert restored.broker_pnl_amount == D("777")


@pytest.mark.asyncio
async def test_single_currency_total_does_not_invent_margin_or_equity_return():
    tracker = tracker_for([position_row()], [spec()])
    await tracker._fetch_positions()
    total = tracker._calculate_account_pnl()
    assert total.total_pnl_amount == D("100")
    assert total.currency == "HKD" and total.pnl_status == "available"
    assert total.pnl_basis == "estimated_gross_price_change"
    assert total.account_pnl_rate is None and total.total_eval_amount is None and total.total_margin_used is None
    assert tracker.get_positions()["HMH_SYNTHETIC"].opening_margin == D("1000")


@pytest.mark.asyncio
async def test_mixed_currency_totals_remain_separate():
    tracker = tracker_for([position_row(), position_row("USD_SYNTHETIC", "USD", 100, 110)],
        [spec(), spec("USD_SYNTHETIC", "USD", "1")])
    await tracker._fetch_positions()
    total = tracker._calculate_account_pnl()
    assert total.total_pnl_amount is None and total.currency is None
    assert total.pnl_status == "unavailable" and total.pnl_unavailable_reason == "mixed_currencies"
    assert total.pnl_by_currency["HKD"].total_pnl_amount == D("100")
    assert total.pnl_by_currency["USD"].total_pnl_amount == D("10")
    assert total.unavailable_position_count == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("currency,specs,reason", [
    ("", [spec()], "missing_position_currency"),
    ("HKD", [], "missing_symbol_spec"),
    ("HKD", [spec(currency="USD")], "position_spec_currency_mismatch"),
    ("HKD", [spec(currency="")], "position_spec_currency_mismatch"),
])
async def test_unavailable_position_cannot_become_zero_or_usd(currency, specs, reason):
    tracker = tracker_for([position_row(currency=currency)], specs)
    await tracker._fetch_positions()
    pos = tracker.get_positions()["HMH_SYNTHETIC"]
    assert pos.pnl_amount is None and pos.pnl_currency is None and pos.pnl_status == "unavailable"
    assert pos.pnl_unavailable_reason == reason
    total = tracker._calculate_account_pnl()
    assert total.total_pnl_amount is None and total.currency is None
    assert total.unavailable_position_count == 1 and not total.pnl_by_currency


@pytest.mark.asyncio
async def test_missing_broker_value_is_not_the_model_default_zero():
    row = position_row().model_dump()
    row.pop("AbrdFutsEvalPnlAmt")
    tracker = tracker_for([CIDBQ01500OutBlock2(**row)], [spec()])
    await tracker._fetch_positions()
    assert tracker.get_positions()["HMH_SYNTHETIC"].broker_pnl_amount is None


@pytest.mark.asyncio
async def test_missing_entry_price_stays_unavailable_after_tick():
    row = position_row().model_dump()
    row.pop("PchsPrc")
    tracker = tracker_for([CIDBQ01500OutBlock2(**row)], [spec()])
    await tracker._fetch_positions()
    pos = tracker.get_positions()["HMH_SYNTHETIC"]
    tracker._on_tick_received(SimpleNamespace(body=SimpleNamespace(symbol=pos.symbol, curpr=25010)))
    assert pos.pnl_amount is None and pos.pnl_unavailable_reason == "missing_position_entry_price"


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value,reason", [
    ("BalQty", None, "missing_position_quantity"),
    ("BnsTpCode", None, "missing_position_side"),
    ("BnsTpCode", "0", "invalid_position_side"),
    ("BnsTpCode", "9", "invalid_position_side"),
])
async def test_missing_quantity_or_side_cannot_invent_zero_or_direction(field, value, reason):
    row = position_row().model_dump()
    row.pop(field)
    if value is not None:
        row[field] = value
    tracker = tracker_for([CIDBQ01500OutBlock2(**row)], [spec()])
    await tracker._fetch_positions()
    pos = tracker.get_positions()["HMH_SYNTHETIC"]
    for tick in (None, 25010):
        if tick is not None:
            tracker._on_tick_received(SimpleNamespace(body=SimpleNamespace(symbol=pos.symbol, curpr=tick)))
        assert pos.pnl_amount is None and pos.pnl_unavailable_reason == reason
        assert tracker._calculate_account_pnl().total_pnl_amount is None


@pytest.mark.asyncio
async def test_explicit_zero_quantity_remains_distinct_from_missing_quantity():
    tracker = tracker_for([position_row(quantity=0)], [spec()])
    await tracker._fetch_positions()
    pos = tracker.get_positions()["HMH_SYNTHETIC"]
    assert pos.quantity == 0 and pos.pnl_amount == D("0")
    assert pos.pnl_status == "available"


@pytest.mark.asyncio
async def test_missing_current_price_can_be_supplied_by_a_real_tick_shape():
    row = position_row(broker_pnl=-123).model_dump()
    row.pop("OvrsDrvtNowPrc")
    tracker = tracker_for([CIDBQ01500OutBlock2(**row)], [spec()])
    await tracker._fetch_positions()
    pos = tracker.get_positions()["HMH_SYNTHETIC"]
    assert pos.pnl_amount is None and pos.pnl_unavailable_reason == "missing_position_current_price"
    tracker._on_tick_received(SimpleNamespace(body=SimpleNamespace(symbol=pos.symbol, curpr=25010)))
    assert pos.pnl_amount == D("100") and pos.pnl_status == "available"
    assert pos.broker_pnl_amount == D("-123")


@pytest.mark.asyncio
async def test_available_currency_contributions_do_not_hide_an_unknown_position():
    tracker = tracker_for([position_row(), position_row("USD_SYNTHETIC", "USD", 100, 110)],
        [spec("USD_SYNTHETIC", "USD", "1")])
    await tracker._fetch_positions()
    total = tracker._calculate_account_pnl()
    assert total.total_pnl_amount is None and total.currency is None
    assert total.unavailable_position_count == 1 and total.position_count == 2
    assert total.pnl_by_currency["USD"].position_count == 1
    assert total.pnl_by_currency["USD"].total_pnl_amount == D("10")


@pytest.mark.asyncio
async def test_zero_and_negative_estimates_are_available_amounts():
    for price, expected in ((25000, D("0")), (24990, D("-100"))):
        tracker = tracker_for([position_row(current=price, broker_pnl=0)], [spec()])
        await tracker._fetch_positions()
        pos = tracker.get_positions()["HMH_SYNTHETIC"]
        total = tracker._calculate_account_pnl()
        assert pos.broker_pnl_amount == D("0")
        assert total.pnl_status == "available" and total.total_pnl_amount == expected


@pytest.mark.asyncio
async def test_incompatible_basis_does_not_enter_scalar_or_subtotal():
    tracker = tracker_for([position_row()], [spec()])
    await tracker._fetch_positions()
    tracker._positions["HMH_SYNTHETIC"] = tracker._positions["HMH_SYNTHETIC"].model_copy(
        update={"pnl_basis":"broker_reported_unconfirmed"})
    total = tracker._calculate_account_pnl()
    assert total.total_pnl_amount is None and not total.pnl_by_currency
    assert total.pnl_unavailable_reason == "incompatible_monetary_basis"


def test_empty_account_is_unavailable_not_zero_usd():
    total = tracker_for([], [])._calculate_account_pnl()
    assert total.total_pnl_amount is None and total.currency is None
    assert total.pnl_unavailable_reason == "no_positions"


@pytest.mark.asyncio
async def test_actual_master_blank_currency_is_preserved_while_manual_default_stays_usd():
    item = SimpleNamespace(Symbol="MISSING", SymbolNm="Synthetic", ExchCd="HKEX", UntPrc=1,
        MnChgAmt=10, CrncyCd="", CtrtPrAmt=0, OpngMgn=0, MntncMgn=0, DotGb=0, BscGdsCd="HMH")
    async def req_async():
        return SimpleNamespace(rsp_cd="00000", block=[item])
    manager = SymbolSpecManager(SimpleNamespace(o3121=lambda **kwargs:SimpleNamespace(req_async=req_async)))
    await manager._fetch_specs()
    assert manager.get_spec("MISSING").currency == ""
    assert SymbolSpec(symbol="MANUAL_USD", tick_size=1, tick_value=10).currency == "USD"


@pytest.mark.asyncio
@pytest.mark.parametrize("missing", ["CrncyCd", "UntPrc", "MnChgAmt"])
async def test_missing_actual_master_metadata_is_not_fabricated_for_native_estimates(missing):
    fields = {"Symbol":"HMH_SYNTHETIC", "SymbolNm":"Synthetic", "ExchCd":"HKEX",
              "CrncyCd":"HKD", "UntPrc":1, "MnChgAmt":10}
    fields.pop(missing)
    row = O3121OutBlock(**fields)
    async def req_async():
        return SimpleNamespace(rsp_cd="00000", block=[row])
    manager = SymbolSpecManager(SimpleNamespace(o3121=lambda **kwargs:SimpleNamespace(req_async=req_async)))
    await manager._fetch_specs()
    actual_spec = manager.get_spec("HMH_SYNTHETIC")
    with pytest.raises(ValueError):
        calculate_native_gross_pnl(spec=actual_spec, quantity=1, entry_price=D("25000"), current_price=D("25010"))
    tracker = tracker_for([position_row()], [actual_spec])
    await tracker._fetch_positions()
    assert tracker.get_positions()["HMH_SYNTHETIC"].pnl_amount is None
    assert tracker._calculate_account_pnl().total_pnl_amount is None


@pytest.mark.asyncio
async def test_valid_actual_master_metadata_is_preserved():
    row = O3121OutBlock(Symbol="HMH_SYNTHETIC", SymbolNm="Synthetic", ExchCd="HKEX",
        CrncyCd="HKD", UntPrc=1, MnChgAmt=10)
    async def req_async():
        return SimpleNamespace(rsp_cd="00000", block=[row])
    manager = SymbolSpecManager(SimpleNamespace(o3121=lambda **kwargs:SimpleNamespace(req_async=req_async)))
    await manager._fetch_specs()
    result = calculate_native_gross_pnl(spec=manager.get_spec("HMH_SYNTHETIC"), quantity=1,
        entry_price=D("25000"), current_price=D("25010"))
    assert result.currency == "HKD" and result.amount == D("100")
