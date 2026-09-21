"""Order and indicator authoring errors must not become simulated successes."""

from unittest.mock import patch

import pytest

from programgarden import ProgramGarden
from programgarden.context import ExecutionContext
from programgarden.executor import NewOrderNodeExecutor, WorkflowJob


def workflow(*nodes):
    all_nodes = [
        {"id": "start", "type": "StartNode"},
        {"id": "broker", "type": "OverseasStockBrokerNode"},
        *nodes,
    ]
    return {
        "id": "authoring-contract", "name": "Authoring contract fixture",
        "nodes": all_nodes,
        "edges": [{"from": a["id"], "to": b["id"]} for a, b in zip(all_nodes, all_nodes[1:])],
    }


@pytest.mark.parametrize("value", ["{{ item.price }}", 123, "LIMIT", None, ["market"]])
def test_order_price_type_requires_literal_enum(value):
    result = ProgramGarden().validate(workflow({
        "id": "order", "type": "OverseasStockNewOrderNode", "price_type": value,
        "order": {"symbol": "XOM", "exchange": "NYSE", "quantity": 1},
    }))
    assert not result.is_valid
    assert any(e.code == "INVALID_FIELD_ENUM" and e.location.field_path == "price_type" for e in result.errors)


@pytest.mark.parametrize("order", [
    "XOM", "{{ item.symbol }}", None, {}, {"symbol": "XOM"},
    {"symbol": "XOM", "quantity": 0},
    {"symbol": "{{ item.symbol }}", "quantity": 1},
    {"symbol": "XOM", "quantity": "{{ item.quantity }}"},
])
async def test_deep_rejects_bad_order_without_network(tmp_path, order):
    context = ExecutionContext("fixture", "fixture", storage_dir=str(tmp_path), context_params={"deep_validate": True})
    with patch("programgarden.executor.ensure_ls_login", side_effect=AssertionError("No network")) as login:
        with pytest.raises(ValueError, match="requires order"):
            await NewOrderNodeExecutor().execute("order", "OverseasStockNewOrderNode", {"order": order}, context)
    login.assert_not_called()


async def test_verified_empty_sizing_alias_is_a_normal_no_signal(tmp_path):
    context = ExecutionContext("fixture", "fixture", storage_dir=str(tmp_path), context_params={"deep_validate": True})
    context.set_output("_input_order", "reason", "no_signal")
    context.set_output("_input_order", "orders", [])
    out = await NewOrderNodeExecutor().execute("order", "OverseasStockNewOrderNode", {"order": None}, context)
    assert out["order_result"]["reason"] == "no_signal"
    assert out["order_id"] == ""


async def test_deep_rejects_sizing_without_symbol_source():
    result = await ProgramGarden().executor.deep_validate(workflow({
        "id": "sizing", "type": "PositionSizingNode", "method": "fixed_quantity", "fixed_quantity": 1,
    }))
    assert not result.is_valid
    assert any(e.location.node_id == "sizing" and e.details.get("stage") == "sizing_inputs" for e in result.errors)


async def test_deep_rejects_disconnected_quote_input():
    result = await ProgramGarden().executor.deep_validate(workflow({
        "id": "sizing", "type": "PositionSizingNode", "method": "fixed_percent",
        "symbols": [{"symbol": "XOM", "exchange": "NYSE"}], "balance": 1000,
    }))
    assert not result.is_valid
    assert any("without usable prices" in e.message for e in result.errors)


@pytest.mark.parametrize("budget", [0, 1])
async def test_deep_allows_zero_balance_or_less_than_one_share(budget):
    definition = workflow({
        "id": "sizing", "type": "PositionSizingNode", "method": "fixed_percent",
        "symbols": [{"symbol": "XOM", "exchange": "NYSE", "price": 150}],
        "balance": {"available": budget}, "max_percent": 10,
    }, {
        "id": "order", "type": "OverseasStockNewOrderNode", "order": "{{ item }}",
    })
    definition["edges"][-1]["from_port"] = "orders"
    result = await ProgramGarden().executor.deep_validate(definition)
    assert result.is_valid, [e.short() for e in result.errors]


def condition_workflow(*, wrappers=False, period=20):
    return workflow({
        "id": "history", "type": "OverseasStockHistoricalDataNode",
        "symbols": [{"symbol": "XOM", "exchange": "NYSE"}],
    }, {
        "id": "condition", "type": "ConditionNode", "plugin": "MovingAverageCross",
        "fields": {"short_period": 5, "long_period": period, "cross_type": "dead"},
        "items": {
            "from": "{{ nodes.history.values }}" if wrappers else "{{ item.time_series }}",
            "extract": {"symbol": "{{ item.symbol }}", "exchange": "{{ item.exchange }}",
                        "date": "{{ row.date }}", "close": "{{ row.close }}"},
        },
    })


async def test_deep_rejects_wrappers_instead_of_bars():
    result = await ProgramGarden().executor.deep_validate(condition_workflow(wrappers=True))
    assert not result.is_valid
    assert any("extracted no values" in e.message for e in result.errors)


async def test_deep_does_not_turn_indicator_failure_into_a_signal():
    result = await ProgramGarden().executor.deep_validate(condition_workflow(period=200))
    assert not result.is_valid
    assert any("insufficient_data" in e.message for e in result.errors)


async def test_longer_fixture_can_validate_long_lookback():
    from programgarden.deep_fixtures import _ohlcv_series

    entry = {"symbol": "XOM", "exchange": "NYSE", "time_series": _ohlcv_series("XOM", n=220)}
    result = await ProgramGarden().executor.deep_validate(
        condition_workflow(period=200),
        fixtures={"history": {"value": entry, "values": [entry]}},
    )
    assert result.is_valid, [e.short() for e in result.errors]


async def test_deep_exercises_healthy_negative_signal():
    result = await ProgramGarden().executor.deep_validate(condition_workflow())
    assert result.is_valid, [e.short() for e in result.errors]


async def test_an_unbound_account_item_is_not_a_simulated_order():
    definition = workflow(
        {"id": "account", "type": "OverseasStockAccountNode"},
        {"id": "order", "type": "OverseasStockNewOrderNode", "order": "{{ item }}"},
    )
    result = await ProgramGarden().executor.deep_validate(definition)
    assert not result.is_valid
    assert any(e.location.node_id == "order" for e in result.errors)


async def test_later_success_does_not_erase_an_earlier_order_failure():
    definition = workflow(
        {"id": "quotes", "type": "OverseasStockMarketDataNode"},
        {"id": "order", "type": "OverseasStockNewOrderNode", "order": "{{ item }}"},
    )
    definition["edges"][-1]["from_port"] = "values"
    result = await ProgramGarden().executor.deep_validate(definition, fixtures={
        "quotes": {"values": [
            {"symbol": "XOM", "exchange": "NYSE", "quantity": 0},
            {"symbol": "CVX", "exchange": "NYSE", "quantity": 1},
        ]},
    })
    assert not result.is_valid
    assert any(e.details.get("stage") == "auto_iteration" and e.details["iteration_index"] == 0 for e in result.errors)


def test_nested_item_fields_are_deferred_until_iteration(tmp_path):
    context = ExecutionContext("fixture", "fixture", storage_dir=str(tmp_path))
    job = object.__new__(WorkflowJob)
    job.context = context
    config = {"order": {"symbol": "{{ item.symbol }}", "quantity": "{{ item.quantity }}"}}
    with patch.object(context, "log") as log:
        assert job._resolve_config_expressions(config) == config
    assert not log.called
    context.set_iteration_context({"symbol": "XOM", "quantity": 2}, 0, 1)
    assert job._resolve_config_expressions(config)["order"] == {"symbol": "XOM", "quantity": 2}


@pytest.mark.parametrize("node_type,override,warns", [
    ("OverseasStockMarketDataNode", None, False),
    ("OverseasStockHistoricalDataNode", None, False),
    ("OverseasStockHistoricalDataNode", {"symbol": "OTHER", "exchange": "NYSE"}, True),
    ("WatchlistNode", None, True),
])
def test_array_warning_matches_executor_selection(tmp_path, node_type, override, warns):
    context = ExecutionContext("fixture", "fixture", storage_dir=str(tmp_path))
    job = object.__new__(WorkflowJob)
    job.context = context
    item = {"symbol": "XOM", "exchange": "NYSE"}
    config = {"symbols": [item, {"symbol": "CVX", "exchange": "NYSE"}]}
    if override:
        config["symbol"] = override
    with patch.object(context, "log") as log:
        assert job._guard_whole_array_reevaluation("node", node_type, config, item, 2) is config
    assert log.called is warns
