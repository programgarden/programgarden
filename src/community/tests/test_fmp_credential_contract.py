"""FMP registration, executor injection and offline validation contracts."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
import json

import pytest
from programgarden_community.nodes.market.fmp import FundamentalDataNode
from programgarden_core.registry import get_credential_type_registry


def test_native_credential_schema_and_secret_serialization():
    schema = get_credential_type_registry().get("fmp_api")
    assert schema is not None
    field = next(f for f in schema.widget_schema["fields"] if f["key"] == "api_key")
    assert field["type"] == "password" and field["required"]
    assert FundamentalDataNode.get_field_schema()["credential_id"].credential_types == ["fmp_api"]
    node = FundamentalDataNode(id="fundamental", api_key="private-fmp-key")
    assert node._api_key == "private-fmp-key"
    assert "private-fmp-key" not in node.model_dump_json() + repr(node)
    assert "api_key" not in node.model_json_schema()["properties"]


@pytest.mark.asyncio
async def test_generic_executor_receives_registered_key_without_exposing_it(monkeypatch):
    from programgarden.executor import GenericNodeExecutor
    from programgarden_core import NodeTypeRegistry
    NodeTypeRegistry().register(FundamentalDataNode)
    received = []
    async def fetch(self, symbols, api_key, timeout, endpoint):
        received.append((symbols, api_key, endpoint))
        return [{"symbol": symbols[0], "exchange": "NASDAQ", "date": "2026-06-30", "revenue": 120}]
    monkeypatch.setattr(FundamentalDataNode, "_fetch_financial_statement", fetch)
    ctx = MagicMock()
    ctx.is_deep_validate = False
    ctx.is_dry_run = False
    ctx.get_workflow_credential.return_value = {"api_key": "private-fmp-key"}
    ctx.get_expression_context.return_value.to_dict.return_value = {"nodes": {}}
    result = await GenericNodeExecutor().execute(
        "fundamental", "FundamentalDataNode",
        {"credential_id": "owned-fmp", "symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}],
         "data_type": "income_statement"}, ctx)
    assert received == [(["AAPL"], "private-fmp-key", "income-statement")]
    assert result["data"][0]["revenue"] == 120
    assert "private-fmp-key" not in json.dumps(result) + str(ctx.log.call_args_list)


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["profile", "key_metrics", "income_statement", "balance_sheet"])
async def test_deep_validation_needs_no_key_and_never_fetches(kind, monkeypatch):
    fetch = AsyncMock(side_effect=AssertionError("Network access forbidden"))
    monkeypatch.setattr(FundamentalDataNode, "_fetch_api", fetch)
    symbols = [{"symbol": "EVGO", "exchange": "NASDAQ"}, {"symbol": "WBX", "exchange": "NYSE"}]
    node = FundamentalDataNode(id="financial", symbols=symbols, data_type=kind, period="quarter", limit=2)
    ctx = SimpleNamespace(is_deep_validate=True, get_deep_fixture=lambda *args: None)
    result = await node.execute(ctx)
    assert result["summary"]["source"] == "synthetic_validation_fixture"
    assert result["summary"]["live_data_verified"] is False
    assert len(result["data"]) == (2 if kind == "profile" else 4)
    assert {r["symbol"] for r in result["data"]} == {"EVGO", "WBX"}
    if kind == "income_statement":
        assert result["data"][0]["date"] > result["data"][1]["date"]
        assert all(r["revenue"] > 0 for r in result["data"])
    fetch.assert_not_awaited()


@pytest.mark.asyncio
async def test_deep_fixture_override_preserves_empty_data_failure_case(monkeypatch):
    fetch = AsyncMock(side_effect=AssertionError("Network access forbidden"))
    monkeypatch.setattr(FundamentalDataNode, "_fetch_api", fetch)
    node = FundamentalDataNode(id="f", symbols=[{"symbol": "AAPL", "exchange": "NASDAQ"}])
    ctx = SimpleNamespace(is_deep_validate=True, get_deep_fixture=lambda *args: {"data": []})
    assert (await node.execute(ctx))["data"] == []
    fetch.assert_not_awaited()
