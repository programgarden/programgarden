"""Run native mapping, report calculations and display envelopes in real chains."""

import pytest

from programgarden.validation_replay import replay
from tests.test_validation_replay import workflow, code


@pytest.mark.asyncio
@pytest.mark.parametrize("destination,passed", [("close", True), ("close_price", False)])
async def test_actual_mapping_name_controls_downstream_calculation(destination, passed):
    mapping = {"id": "map", "type": "FieldMappingNode", "data": {"lastPrice": 5, "symbol": "A"},
               "mappings": [{"from": "lastPrice", "to": destination}]}
    result = await replay(workflow(mapping, code(data="{{ nodes.map.mapped_data.close }}", value="data * 2")), {})
    assert result.passed is passed, result.errors
    if passed:
        assert result.outputs["map"]["mapped_data"] == {"close": 5, "symbol": "A"}
        assert result.outputs["calc"]["result"] == 10
    else:
        assert result.node_states["calc"] == "failed"
        assert not result.outputs.get("calc")


@pytest.mark.asyncio
@pytest.mark.parametrize("node_type,fields", [
    ("TableDisplayNode", {"columns": ["date", "close"]}),
    ("SummaryDisplayNode", {}),
    ("LineChartNode", {"x_field": "date", "y_field": "close"}),
    ("BarChartNode", {"x_field": "date", "y_field": "close"}),
    ("MultiLineChartNode", {"x_field": "date", "y_field": "close", "series_key": "symbol"}),
    ("CandlestickChartNode", {"date_field": "date", "open_field": "open", "high_field": "high",
                               "low_field": "low", "close_field": "close"}),
])
async def test_display_prepares_actual_data_without_claiming_browser_rendering(node_type, fields):
    rows = [{"date": "2026-09-22", "symbol": "A", "open": 9, "high": 11, "low": 8, "close": 10}]
    result = await replay(workflow({"id": "view", "type": node_type, "data": rows, **fields}), {})
    assert result.passed, result.errors
    assert result.outputs["view"]["rendered"] is True
    assert result.outputs["view"]["data"] == rows
    assert result.live_authorized is False


@pytest.mark.asyncio
async def test_report_computes_drawdown_from_actual_equity_series():
    values = [100, 110, 90, 120, 108]
    result = await replay(workflow({"id": "report", "type": "PerformanceReportNode", "data_kind": "equity",
        "value_field": "value", "data": [{"date": f"2026-09-{i+1:02}", "value": v}
                                             for i, v in enumerate(values)]}), {})
    assert result.passed, result.errors
    assert result.outputs["report"]["metrics"]["max_drawdown"] == pytest.approx(-0.1818)
    assert result.outputs["report"]["summary"]["observations"] == 5


@pytest.mark.asyncio
async def test_insufficient_report_data_does_not_satisfy_required_numeric_metrics():
    node = {"id": "report", "type": "PerformanceReportNode", "data_kind": "equity", "data": [100]}
    result = await replay(workflow(node), {"contracts": {"report": {"output": {
        "type": "object", "required": ["metrics"], "properties": {"metrics": {
            "type": "object", "required": ["max_drawdown"], "properties": {
                "max_drawdown": {"type": "number"}}}}}}}})
    assert not result.passed
    assert any(e["code"] == "REPLAY_CONTRACT_FAILED" for e in result.errors)
