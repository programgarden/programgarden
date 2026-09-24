"""Order scenarios use an in-memory book; no broker transport exists."""
import pytest
from programgarden.replay_orders import SimulationBook
from programgarden.replay_contracts import ContractViolation

AS_OF="2026-09-22T14:00:00Z"


def book(**changes):
    instrument={"currency":"USD","price":100,"as_of":AS_OF,"session_open":True,
                "tradeable":True,"tick_size":0.01,"max_age_seconds":60,**changes}
    return SimulationBook({"currency":"USD","cash":1000,"max_investment":600},
                          {"TEST:A":instrument},as_of=AS_OF)


def intent(**changes):
    return {"symbol":"A","exchange":"TEST","side":"buy","quantity":5,
            "order_type":"limit","price":100,**changes}


def test_buy_sell_fill_and_snapshot():
    b=book()
    buy=b.submit(intent(),key="buy",response="filled")
    assert buy["filled_quantity"]==5 and b.positions=={"TEST:A":5} and b.cash==500
    sell=b.submit(intent(side="sell"),key="sell",response="filled")
    assert sell["status"]=="filled" and b.positions=={"TEST:A":0} and b.cash==1000
    assert b.snapshot()["live_order_count"]==0


def test_partial_fill_duplicate_event_and_cancel_preserve_state():
    b=book();o=b.submit(intent(),key="buy",response="partial_fill",filled_quantity=2)
    assert o["status"]=="partial_fill" and b.cash==800
    b.fill(o["order_id"],2,event_id="buy:fill")
    assert b.cash==800 and b.positions["TEST:A"]==2
    cancelled=b.cancel(o["order_id"],event_id="cancel")
    assert cancelled["filled_quantity"]==2 and cancelled["status"]=="cancelled"
    assert b.cash==800 and b._reserved_cash()==0


def test_timeout_is_unknown_and_never_resubmitted_until_reconciliation():
    b=book();unknown=b.submit(intent(),key="buy",response="timeout")
    assert unknown["status"]=="unknown" and b._reserved_cash()==500
    again=b.submit(intent(),key="buy",response="filled")
    assert again["status"]=="unknown" and again["duplicate"]
    assert len(b.orders)==1 and b.cash==1000 and not b.positions
    assert b.submit(intent(),key="different")["reason"]=="pending_or_unknown_order"
    with pytest.raises(ContractViolation): b.cancel(unknown["order_id"],event_id="cancel")
    b.reconcile(unknown["order_id"],accepted=True,event_id="reconcile")
    b.fill(unknown["order_id"],5,event_id="fill")
    assert b.cash==500 and b.positions["TEST:A"]==5


@pytest.mark.parametrize("changes,reason", [
    ({"currency":"KRW"},"currency_mismatch"),
    ({"session_open":False},"market_closed"),
    ({"tradeable":False},"instrument_not_tradeable"),
    ({"as_of":"2026-09-22T13:00:00Z"},"stale_market_data"),
    ({"as_of":"2026-09-22T15:00:00Z"},"stale_market_data"),
])
def test_risk_rejections_are_explicit(changes,reason):
    b=book(**changes);o=b.submit(intent(),key="one")
    assert o["status"]=="rejected" and o["reason"]==reason
    assert b.cash==1000 and not b.positions


def test_cash_budget_and_sell_quantity_checks():
    b=book();b.cash=100
    assert b.submit(intent(),key="cash")["reason"]=="insufficient_cash"
    b=book()
    assert b.submit(intent(quantity=7),key="limit")["reason"]=="max_investment_exceeded"
    assert b.submit(intent(side="sell"),key="position")["reason"]=="insufficient_position"
    b.submit(intent(),key="filled",response="filled")
    # A repeat BUY while already holding is NOT refused as "already held" — the live
    # engine has no such rule (only the chatbot CodeNode guard does). It falls through
    # to the ordinary budget check, which trips because 5+5 shares exceed the cap.
    assert b.submit(intent(),key="held")["reason"]=="max_investment_exceeded"


def test_stock_buy_while_holding_is_accepted_when_budget_allows():
    # Mirror LIVE (executor.py NewOrderNode): an additional buy for a held symbol is
    # accepted. "No additional buy by default" is a chatbot CodeNode guard, not an
    # engine rule, so the simulator must let a legitimate add-on buy through.
    b=book()
    opened=b.submit(intent(),key="open",response="filled")           # buy 5 -> hold 5, cash 500
    assert opened["status"]=="filled" and b.positions=={"TEST:A":5}
    added=b.submit(intent(quantity=1),key="add",response="filled")   # buy 1 more while holding
    assert added["reason"] is None and added["status"]=="filled"
    assert b.positions=={"TEST:A":6} and b.cash==400


def test_futures_adding_to_open_position_is_still_refused():
    # Futures semantics are unchanged by the stock fix: adding to an open position
    # (same direction, not closing) still rejects as position_already_held.
    b=book(product="overseas_futures",margin_per_contract=200,multiplier=10)
    entry=b.submit(intent(side="buy",quantity=1),key="entry",response="filled")
    assert entry["status"]=="filled" and b.positions=={"TEST:A":1}
    added=b.submit(intent(side="buy",quantity=1),key="add")
    assert added["reason"]=="position_already_held" and added["status"]=="rejected"


def test_futures_requires_explicit_margin_and_never_assumes_stock_notional():
    b=book(product="overseas_futures")
    with pytest.raises(ContractViolation,match="margin assumptions"):
        b.submit(intent(),key="margin")
    assert not b.orders


def test_conflicting_idempotency_keys_and_event_ids_are_rejected():
    b=book();o=b.submit(intent(),key="one")
    with pytest.raises(ContractViolation): b.submit(intent(quantity=1),key="one")
    b.fill(o["order_id"],1,event_id="fill")
    with pytest.raises(ContractViolation): b.fill(o["order_id"],2,event_id="fill")
    assert b.positions["TEST:A"]==1


@pytest.mark.parametrize("quantity", [0,6,1.5,True])
def test_bad_partial_fill_cannot_mutate_the_book(quantity):
    b=book()
    with pytest.raises(ContractViolation):
        b.submit(intent(),key="partial",response="partial_fill",filled_quantity=quantity)
    assert not b.orders and b.cash==1000


@pytest.mark.parametrize("side,exit_price,expected", [("buy",110,1100),("sell",90,1100),("sell",110,900)])
def test_futures_margin_and_realized_profit_use_explicit_multiplier(side,exit_price,expected):
    b=book(product="overseas_futures",margin_per_contract=200,multiplier=10)
    opened=b.submit(intent(side=side,quantity=1),key="entry",response="filled")
    assert opened["status"]=="filled" and b.cash==800
    closed=b.submit(intent(side="sell" if side=="buy" else "buy",quantity=1,price=exit_price),
                    key="exit",response="filled")
    assert closed["status"]=="filled" and b.cash==expected and b.positions["TEST:A"]==0


def test_duplicate_event_does_not_coerce_boolean_to_integer():
    b=book();o=b.submit(intent(),key="entry")
    b.fill(o["order_id"],1,event_id="fill")
    with pytest.raises(ContractViolation):
        b.fill(o["order_id"],True,event_id="fill")
    assert b.positions["TEST:A"]==1


def test_max_investment_includes_other_positions_and_reserved_orders():
    b=book();b.instruments["TEST:B"]={**b.instruments["TEST:A"]}
    b.positions["TEST:B"]=2
    assert b.submit(intent(),key="too-large")["reason"]=="max_investment_exceeded"


def test_empty_idempotency_key_cannot_mutate_book():
    b=book()
    with pytest.raises(ContractViolation): b.submit(intent(),key="")
    assert not b.orders
