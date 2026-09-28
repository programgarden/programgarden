"""연결(자격증명) 선언이 AI catalog(get_node_schema / list_node_types)로 export 되는지.

`load_catalog`(pg-ai) 와 dsl-api `/get_node_types` 는 이 도구가 돌려주는 model_dump
JSON 을 읽는다. `connection` 은 NodeTypeSchema 필드라 자동으로 실린다.
"""

from programgarden.tools.registry_tools import get_node_schema, list_node_types


def test_http_connection_in_catalog():
    schema = get_node_schema("HTTPRequestNode")
    assert schema is not None
    conn = schema.get("connection")
    assert conn is not None, "connection missing from catalog JSON"
    assert conn["purpose"] == "data"
    assert conn["when"] == "auth_required"
    assert conn["need"] == "validate"
    assert [p["id"] for p in conn["presets"]] == ["fmp", "finnhub"]
    assert conn["label_ko"] == "API 키" and conn["label_en"] == "API key"
    # auth_required 설정 필드도 catalog config_schema 에 있다
    assert "auth_required" in schema.get("config_schema", {})
    preset = schema["config_schema"]["credential_preset"]
    assert preset["enum_values"] == [p["id"] for p in conn["presets"]]


def test_http_provider_preset_survives_native_model_roundtrip():
    import pytest
    from pydantic import ValidationError
    from programgarden_core.nodes.data import HTTPRequestNode

    for provider in ("fmp", "finnhub"):
        node = HTTPRequestNode(id="h", url="https://example.invalid/data", credential_preset=provider)
        assert HTTPRequestNode.model_validate(node.model_dump()).credential_preset == provider
        assert node.credential_id is None
    with pytest.raises(ValidationError):
        HTTPRequestNode(id="h", url="https://example.invalid/data", credential_preset="unknown")


def test_connection_in_list_catalog():
    schemas = {s["node_type"]: s for s in list_node_types()}
    broker = schemas["OverseasStockBrokerNode"].get("connection")
    assert broker is not None
    assert broker["types"] == ["broker_ls_overseas_stock"]
    assert broker["purpose"] == "trading"
    # 브로커 연결을 상속하는 노드는 자기 connection 이 없다
    assert schemas["OverseasStockMarketDataNode"].get("connection") is None
    assert schemas["WatchlistNode"].get("connection") is None


def test_llm_connection_in_catalog():
    schema = get_node_schema("LLMModelNode")
    conn = schema.get("connection")
    assert conn is not None and conn["purpose"] == "ai"
    assert conn["label_en"] == "AI model key"
