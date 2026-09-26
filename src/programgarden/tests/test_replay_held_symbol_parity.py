"""Held-symbol parity: replay must mirror the LIVE NewOrderNode for a symbol the
account already holds.

The live executor (programgarden/executor.py) has NO rule that refuses a BUY
because the account already holds the symbol. Its only pre-submit gates are:
  * the ExclusionListNode safety check — ``_check_exclusion_list`` at
    executor.py:17171, gated by the node config ``ignore_exclusion`` at
    executor.py:15590-15604 (a blocked buy returns ``_order_result(success=False,
    error="Blocked by exclusion list…")`` — a *skip-shaped* failed result, NOT a
    broker rejection);
  * the drawdown guard (executor.py:15606);
  * the idempotency registry.
LS accepts additional buys; the product's "no additional buy by default" is
enforced by the chatbot's own CodeNode GUARD, never by the engine.

The replay adapter (``replay_order_adapter.ReplayOrders``) only simulates order
intents against a fixture book; it never executes an ExclusionListNode and so
never sees an exclusion list (grep: ``ignore_exclusion`` / ``exclusion`` appear
nowhere in ``replay_order_adapter.py`` / ``replay_orders.py``). These tests
therefore lock in the one rule the replay CAN mirror: a stock buy for a held
symbol is accepted, subject only to the ordinary cash/investment budget — exactly
as live — instead of the former, stricter ``position_already_held`` rejection.
"""
from copy import deepcopy

import pytest

from programgarden.validation_replay import replay
from programgarden.replay_external import recording

AS_OF = "2026-09-22T14:00:00Z"


def _held_case(*, held, cash=1000, max_investment=600, quantity=2):
    """A minimal overseas-stock buy graph whose account already holds NASDAQ:A."""
    node = {"id": "order", "type": "OverseasStockNewOrderNode", "side": "buy",
            "order_type": "limit",
            "order": {"symbol": "A", "exchange": "NASDAQ", "quantity": quantity, "price": 100}}
    graph = {"id": "orders", "name": "Orders",
             "nodes": [{"id": "start", "type": "StartNode"},
                       {"id": "broker", "type": "OverseasStockBrokerNode"}, node],
             "edges": [{"from": "start", "to": "broker"}, {"from": "broker", "to": "order"}]}
    account = {"cash": cash, "currency": "USD", "max_investment": max_investment,
               "positions": {"NASDAQ:A": held}}
    fixture = {"nodes": {"broker": {
                   "output": {"connection": {"product": "overseas_stock", "provider": "ls-sec.co.kr"}},
                   "contract": {"type": "object", "required": ["connection"],
                                "properties": {"connection": {"type": "object"}}}}},
               "broker": {"as_of": AS_OF, "account": account,
                   "instruments": {"NASDAQ:A": {"product": "overseas_stock", "currency": "USD",
                       "price": 100, "as_of": AS_OF, "session_open": True, "tradeable": True,
                       "tick_size": 0.01, "max_age_seconds": 60}}},
               "orders": {"order": {"response": "filled"}}}
    record = fixture["nodes"]["broker"]
    fixture["nodes"]["broker"] = recording("OverseasStockBrokerNode", {}, record["output"], record["contract"], as_of=AS_OF)
    return graph, fixture


@pytest.mark.asyncio
async def test_additional_buy_while_holding_is_accepted_like_live():
    # The exact scenario a lifecycle probe found wrongly rejected: the account
    # already holds NASDAQ:A and an independent branch buys more. Live accepts it,
    # so the simulator must too — no ``position_already_held``.
    graph, fixture = _held_case(held=2)
    result = await replay(graph, fixture)
    assert result.passed, result.errors
    assert result.outputs["order"]["result"][0]["filled_quantity"] == 2
    assert result.outputs["order"]["order_result"]["risk_decision"] == "allowed"
    assert result.simulation["positions"] == {"NASDAQ:A": 4}   # 2 held + 2 bought
    assert result.simulation["cash"] == 800


@pytest.mark.asyncio
async def test_additional_buy_still_obeys_the_ordinary_investment_budget():
    # Dropping the held refusal does NOT drop the budget check: a held position
    # large enough that the add-on would exceed max_investment is still refused,
    # now for the correct reason (the live cash/exposure limit, not a blanket
    # "already held" block).
    graph, fixture = _held_case(held=5)   # 5*100 held = 500 exposure; +2*100 = 700 > 600
    result = await replay(graph, fixture)
    assert not result.passed
    assert result.outputs["order"]["order_result"]["risk_decision"] == "max_investment_exceeded"
    assert result.simulation["positions"] == {"NASDAQ:A": 5}   # unchanged; order not filled
    assert result.simulation["cash"] == 1000
