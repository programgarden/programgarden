"""Workflow open-position money cannot borrow account or realized amounts."""
from copy import deepcopy
from datetime import datetime, timezone

import pytest

from programgarden.valuation import workflow_valuation_snapshot

NOW = datetime(2026, 9, 15, tzinfo=timezone.utc)


def sample():
    return {"workflow_pnl_rate": 1, "workflow_positions": [
        {"symbol": "ONE", "quantity": 2, "avg_price": 10, "current_price": 15, "pnl_amount": 10},
        {"symbol": "TWO", "quantity": 1, "avg_price": 10, "current_price": 6, "pnl_amount": -4},
        {"symbol": "THREE", "quantity": 1, "avg_price": 10, "current_price": 11, "pnl_amount": 1},
    ]}


ACCOUNTS = {"ONE": {"currency": "USD"}, "TWO": {"currency": "USD"}, "THREE": {"currency": "HKD"}}


def test_currency_groups_and_own_cost_basis():
    value = workflow_valuation_snapshot(sample(), ACCOUNTS, NOW, "overseas_stock")
    assert value["groups"] == [
        {"currency": "HKD", "earned": 1, "lost": 0, "net": 1},
        {"currency": "USD", "earned": 10, "lost": 4, "net": 6}]


@pytest.mark.parametrize("case", ["currency", "account", "basis", "amount", "price", "future"])
def test_unavailable_basis_never_fills_money(case):
    result, accounts = sample(), deepcopy(ACCOUNTS)
    if case == "currency": accounts["ONE"]["currency"] = None
    elif case == "account": accounts.pop("ONE")
    elif case == "basis": result["workflow_pnl_rate"] = None
    elif case == "amount": result["workflow_positions"][0]["pnl_amount"] = 1000
    elif case == "price": result["workflow_positions"][0]["current_price"] = None
    assert workflow_valuation_snapshot(result, accounts, NOW,
        "overseas_futures" if case == "future" else "overseas_stock") is None


def test_unknown_and_explicit_empty_positions_differ():
    result = {"workflow_positions": []}
    assert workflow_valuation_snapshot(result, None, NOW, "overseas_stock") is None
    assert workflow_valuation_snapshot(result, {}, NOW, "overseas_stock")["groups"] == []


@pytest.mark.asyncio
async def test_actual_context_event_preserves_both_valuation_scopes():
    import json
    from dataclasses import asdict
    from decimal import Decimal
    from unittest.mock import Mock
    from programgarden.context import ExecutionContext
    from programgarden_core.bases.listener import BaseExecutionListener

    class Capture(BaseExecutionListener):
        def __init__(self): self.events = []
        async def on_workflow_pnl_update(self, event): self.events.append(event)

    ctx = ExecutionContext(job_id='valuation-test', workflow_id='valuation-workflow')
    ctx._calculate_workflow_pnl = Mock(return_value=sample())
    capture = Capture()
    ctx.add_listener(capture)
    account = {'version': 1, 'basis': 'broker_open_positions', 'product': 'overseas_stock',
               'source': 'COSOQ00201', 'observed_at': NOW.isoformat(),
               'groups': [{'currency': 'USD', 'earned': Decimal(20), 'lost': Decimal(4), 'net': Decimal(16)}]}
    await ctx.notify_workflow_pnl(broker_node_id='broker', product='overseas_stock',
        provider='ls-sec.co.kr', current_prices={}, account_positions=ACCOUNTS,
        account_valuation=account)
    assert len(capture.events) == 1
    wire = json.loads(json.dumps(asdict(capture.events[0]), default=lambda value:
        float(value) if isinstance(value, Decimal) else value.isoformat()))
    assert wire['account_valuation']['groups'][0]['net'] == 16
    assert wire['workflow_valuation']['groups'][1]['net'] == 6
    assert wire['personal_metrics'] is None


def test_domestic_workflow_money_requires_krw_and_its_own_cost():
    accounts = {symbol: {'currency': 'KRW'} for symbol in ACCOUNTS}
    value = workflow_valuation_snapshot(sample(), accounts, NOW, 'korea_stock')
    assert value['groups'] == [{'currency': 'KRW', 'earned': 11, 'lost': 4, 'net': 7}]
    accounts['ONE']['currency'] = 'USD'
    assert workflow_valuation_snapshot(sample(), accounts, NOW, 'korea_stock') is None


def test_domestic_unknown_average_does_not_become_a_zero_cost_return():
    from programgarden.context import ExecutionContext
    context = ExecutionContext(job_id='domestic-evidence', workflow_id='domestic-evidence')
    assert context._calculate_account_pnl({'001500': {'product': 'korea_stock',
        'quantity': 1, 'buy_price': None, 'current_price': 7980}}) == {}


def test_domestic_observed_zero_pnl_is_not_replaced_by_price_arithmetic():
    from programgarden.context import ExecutionContext
    context = ExecutionContext(job_id='domestic-evidence', workflow_id='domestic-evidence')
    row = {'product': 'korea_stock', 'quantity': 1, 'buy_price': 7980,
           'current_price': 7981, 'pnl_amount': 0}
    assert context._calculate_account_pnl({'001500': row})['account_total_pnl_amount'] == 0
    row['pnl_amount'] = None
    assert context._calculate_account_pnl({'001500': row}) == {}


@pytest.mark.asyncio
@pytest.mark.parametrize("positions", [None, {'001500': {'product': 'korea_stock',
    'quantity': 1, 'buy_price': None, 'current_price': None, 'pnl_amount': None}}])
async def test_real_context_reports_missing_domestic_observation_without_losing_event(positions):
    from programgarden.context import ExecutionContext
    from programgarden_core.bases.listener import BaseExecutionListener

    class Capture(BaseExecutionListener):
        def __init__(self): self.events = []
        async def on_workflow_pnl_update(self, event): self.events.append(event)

    context = ExecutionContext(job_id='domestic-evidence', workflow_id='domestic-evidence')
    listener = Capture()
    context.add_listener(listener)
    await context.notify_workflow_pnl(broker_node_id='broker', product='korea_stock',
        provider='ls-sec.co.kr', current_prices={}, account_positions=positions,
        currency='KRW', account_valuation=None)
    assert len(listener.events) == 1
    event = listener.events[0]
    assert event.workflow_pnl_rate is None and event.account_total_pnl_rate is None
    assert event.workflow_valuation is None and event.account_valuation is None
