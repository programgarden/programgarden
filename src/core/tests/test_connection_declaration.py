"""연결(자격증명) 선언 스키마 테스트 (오너 결정 2026-09-28).

`credential_types` 를 가진 노드는 반드시 잘 형성된 `connection` 선언을 export 해야
한다(챗봇/편집기/검증기가 한곳에서 자격증명 필요를 읽는다). 브로커 연결을 상속하는
시세/계좌/주문 노드나 자격증명이 없는 노드는 `connection` 이 None 이다.
"""

import pytest

from programgarden_core.registry import NodeTypeRegistry

try:  # 커뮤니티 노드(TelegramNode) 등록 — 없으면 관련 케이스만 skip
    import programgarden_community  # noqa: F401
    _COMMUNITY = True
except Exception:  # pragma: no cover
    _COMMUNITY = False

PURPOSES = {"trading", "data", "ai", "notify"}
NEEDS = {"run", "validate", "optional"}
WHENS = {"always", "auth_required", "never"}
MISSINGS = {"draft", "block"}
KEYS = {"types", "purpose", "need", "when", "label_ko", "label_en", "presets", "missing"}


def _reg() -> NodeTypeRegistry:
    return NodeTypeRegistry()


def _credential_types_of(schema) -> list:
    """스키마 config_schema 에서 선언된 credential_types 합집합."""
    out: list = []
    for fcfg in (schema.config_schema or {}).values():
        if not isinstance(fcfg, dict):
            continue
        for c in (fcfg.get("credential_types") or []):
            if c not in out:
                out.append(c)
    return out


def _nodes_with_credential_types() -> list:
    reg = _reg()
    res = []
    for nt in reg.list_types():
        s = reg.get_schema(nt)
        if s is not None and _credential_types_of(s):
            res.append(nt)
    return sorted(res)


def test_expected_credential_nodes_present():
    got = set(_nodes_with_credential_types())
    expected = {
        "OverseasStockBrokerNode", "OverseasFuturesBrokerNode", "KoreaStockBrokerNode",
        "HTTPRequestNode", "LLMModelNode",
    }
    assert expected <= got, f"missing credential nodes: {expected - got}"
    if _COMMUNITY:
        assert "TelegramNode" in got


@pytest.mark.parametrize("node_type", _nodes_with_credential_types(), ids=lambda t: t)
def test_credential_node_has_wellformed_connection(node_type):
    """credential_types 가 있는 모든 노드는 잘 형성된 connection 을 가진다."""
    schema = _reg().get_schema(node_type)
    conn = schema.connection
    assert conn is not None, f"{node_type}: has credential_types but connection is None"
    assert set(conn.keys()) == KEYS, f"{node_type}: keys={set(conn.keys())}"
    assert conn["purpose"] in PURPOSES, f"{node_type}: purpose={conn['purpose']}"
    assert conn["need"] in NEEDS, f"{node_type}: need={conn['need']}"
    assert conn["when"] in WHENS, f"{node_type}: when={conn['when']}"
    assert conn["missing"] in MISSINGS, f"{node_type}: missing={conn['missing']}"
    # types == 노드의 credential_types (드리프트 방지)
    assert conn["types"] == _credential_types_of(schema), node_type
    assert conn["types"], f"{node_type}: empty types"
    # 라벨 두 언어 모두 존재·해석됨(i18n: 접두사도, 원본 키도 아님)
    for lk in ("label_ko", "label_en"):
        assert isinstance(conn[lk], str) and conn[lk], f"{node_type}: {lk} empty"
        assert not conn[lk].startswith("i18n:"), f"{node_type}: {lk} unresolved: {conn[lk]}"
        assert not conn[lk].startswith("connection."), f"{node_type}: {lk} raw key: {conn[lk]}"
    assert isinstance(conn["presets"], list)


def test_http_connection_shape_and_presets():
    conn = _reg().get_schema("HTTPRequestNode").connection
    assert conn["purpose"] == "data"
    assert conn["need"] == "validate"
    assert conn["when"] == "auth_required"
    assert conn["missing"] == "draft"
    assert conn["types"] == ["http_bearer", "http_header", "http_basic", "http_query"]
    assert conn["label_ko"] == "API 키" and conn["label_en"] == "API key"
    ids = [p["id"] for p in conn["presets"]]
    assert ids == ["fmp", "finnhub"], ids
    for p in conn["presets"]:
        assert set(p.keys()) == {"id", "label", "type", "fields"}
        assert p["type"] == "http_query"
    assert conn["presets"][0]["fields"] == {"param_name": "apikey"}
    assert conn["presets"][1]["fields"] == {"param_name": "token"}


def test_http_auth_required_config_field_present():
    """when=auth_required 는 노드의 auth_required 설정을 참조한다 — 필드가 존재해야 한다."""
    schema = _reg().get_schema("HTTPRequestNode")
    assert "auth_required" in schema.config_schema
    # Optional[bool], 기본 None(챗봇 판단) — required 아님
    assert schema.config_schema["auth_required"].get("required") is not True


def test_broker_connections():
    reg = _reg()
    cases = {
        "OverseasStockBrokerNode": ("LS증권 해외주식 계좌", ["broker_ls_overseas_stock"]),
        "OverseasFuturesBrokerNode": ("LS증권 해외선물 계좌", ["broker_ls_overseas_futures"]),
        "KoreaStockBrokerNode": ("LS증권 국내주식 계좌", ["broker_ls_korea_stock"]),
    }
    for nt, (label_ko, types) in cases.items():
        conn = reg.get_schema(nt).connection
        assert conn["purpose"] == "trading" and conn["need"] == "run" and conn["when"] == "always"
        assert conn["missing"] == "draft"
        assert conn["label_ko"] == label_ko
        assert conn["types"] == types
        assert conn["presets"] == []


def test_llm_connection():
    conn = _reg().get_schema("LLMModelNode").connection
    assert conn["purpose"] == "ai" and conn["need"] == "run" and conn["when"] == "always"
    assert conn["label_ko"] == "AI 모델 키" and conn["label_en"] == "AI model key"
    assert conn["presets"] == []
    assert conn["types"] == ["llm_openai", "llm_anthropic", "llm_deepseek", "llm_google"]


@pytest.mark.skipif(not _COMMUNITY, reason="community package not installed")
def test_telegram_connection():
    conn = _reg().get_schema("TelegramNode").connection
    assert conn is not None
    assert conn["purpose"] == "notify" and conn["need"] == "run" and conn["when"] == "always"
    assert conn["label_ko"] == "텔레그램 봇" and conn["label_en"] == "Telegram bot"
    assert conn["presets"] == []


def test_inherited_and_plain_nodes_have_no_connection():
    """브로커 연결을 상속하는 노드·자격증명 없는 노드는 connection=None."""
    reg = _reg()
    for nt in ("OverseasStockMarketDataNode", "OverseasStockAccountNode",
               "AIAgentNode", "WatchlistNode", "ConditionNode"):
        schema = reg.get_schema(nt)
        if schema is None:
            continue
        assert schema.connection is None, f"{nt}: unexpected connection"
        assert reg.connection_declaration(nt) is None


def test_connection_declaration_helper():
    reg = _reg()
    # 헬퍼 == 스키마 필드
    assert reg.connection_declaration("HTTPRequestNode") == reg.get_schema("HTTPRequestNode").connection
    assert reg.connection_declaration("WatchlistNode") is None
    assert reg.connection_declaration("NoSuchNode") is None
    # 복사본 반환 — 호출부가 수정해도 캐시 불변
    d = reg.connection_declaration("HTTPRequestNode")
    d["types"].append("XXX")
    d["presets"].append({"id": "z"})
    fresh = reg.get_schema("HTTPRequestNode").connection
    assert "XXX" not in fresh["types"]
    assert all(p.get("id") != "z" for p in fresh["presets"])


def test_connection_labels_locale_independent():
    """connection 은 get_schema(locale) 와 무관하게 label_ko/en 둘 다 항상 갖는다."""
    reg = _reg()
    en = reg.get_schema("HTTPRequestNode", locale="en").connection
    ko = reg.get_schema("HTTPRequestNode", locale="ko").connection
    assert en["label_ko"] == ko["label_ko"] == "API 키"
    assert en["label_en"] == ko["label_en"] == "API key"
