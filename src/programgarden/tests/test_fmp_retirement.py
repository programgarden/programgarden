"""Retired provider admission and the maintained LS replacement contract."""
from copy import deepcopy

import pytest
import programgarden_community  # noqa: F401
from programgarden import ProgramGarden
from programgarden_core import NodeTypeRegistry
from programgarden_core.models.credential import BUILTIN_CREDENTIAL_SCHEMAS
from programgarden_finance.ls.overseas_stock.market.g3104.blocks import G3104OutBlock
from programgarden.validation_replay import replay


def test_removed_provider_is_not_discoverable_or_accepted():
    assert NodeTypeRegistry().get("FundamentalDataNode") is None
    assert "fmp_api" not in BUILTIN_CREDENTIAL_SCHEMAS
    assert NodeTypeRegistry().get("OverseasStockFundamentalNode") is not None
    graph = {"id": "old-import", "name": "Old import", "nodes": [
        {"id": "start", "type": "StartNode"},
        {"id": "old", "type": "FundamentalDataNode"}],
        "edges": [{"from": "start", "to": "old"}]}
    before = deepcopy(graph)
    result = ProgramGarden().validate(graph)
    assert not result.is_valid
    errors = [e for e in result.errors if e.code == "UNKNOWN_NODE_TYPE"]
    assert errors and "OverseasStockFundamentalNode" in str(errors[0])
    assert graph == before


def test_consumed_ls_fields_exist_in_the_actual_sdk_model():
    assert {"engname", "induname", "nation_name", "exchange_name", "pcls", "clos",
            "volume", "perv", "epsv", "shareprc", "share", "high52p", "low52p",
            "exrate"} <= G3104OutBlock.model_fields.keys()


@pytest.mark.asyncio
@pytest.mark.parametrize("per,expected", [(15.5, ["XOM"]), (25.0, []), (0, []), (-2, []), (None, [])])
async def test_ls_positive_per_filter_uses_recorded_data_without_broker(per, expected):
    graph = {"id": "ls-per-replay", "name": "LS PER replay", "nodes": [
        {"id": "start", "type": "StartNode"},
        {"id": "broker", "type": "OverseasStockBrokerNode"},
        {"id": "fundamental", "type": "OverseasStockFundamentalNode",
         "symbols": [{"symbol": "XOM", "exchange": "NYSE"}]},
        {"id": "filter", "type": "CodeNode", "data": "{{ nodes.fundamental.values }}",
         "outputs": [{"name": "symbols", "type": "array"}],
         "code": "def execute(data, params, context):\n return {'symbols': [r['symbol'] for r in data if isinstance(r.get('per'), (int, float)) and 0 < r['per'] <= 20]}"}],
        "edges": [{"from": "start", "to": "broker"},
                  {"from": "broker", "to": "fundamental"},
                  {"from": "fundamental", "to": "filter"}]}
    fixture = {"nodes": {"broker": {"output": {"connection": {"product": "overseas_stock"}},
                                  "contract": {"type": "object"}},
        "fundamental": {"output": {"values": [
        {"symbol": "XOM", "exchange": "NYSE", "per": per}]},
        "contract": {"type": "object", "required": ["values"]}}}}
    result = await replay(graph, fixture)
    assert result.passed, result.errors
    assert result.outputs["filter"]["symbols"] == expected
    assert not result.live_authorized
