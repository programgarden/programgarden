"""
국내주식(KoreaStock) 노드 13개 단위 테스트

테스트 대상:
1. 노드 모델 생성 및 타입/카테고리/ProductScope 검증
2. 입출력 포트 검증
3. FieldSchema 검증
4. NodeTypeRegistry 등록 확인
5. i18n 키 존재 확인

실행:
    cd src/core && poetry run pytest tests/test_korea_stock_nodes.py -v
"""

import pytest

from programgarden_core.nodes.base import NodeCategory, ProductScope, BrokerProvider
from programgarden_core.nodes.broker import KoreaStockBrokerNode
from programgarden_core.nodes.account_korea_stock import KoreaStockAccountNode
from programgarden_core.nodes.open_orders_korea_stock import KoreaStockOpenOrdersNode
from programgarden_core.nodes.data_korea_stock import KoreaStockMarketDataNode
from programgarden_core.nodes.fundamental_korea_stock import KoreaStockFundamentalNode
from programgarden_core.nodes.backtest_korea_stock import KoreaStockHistoricalDataNode
from programgarden_core.nodes.symbol_korea_stock import KoreaStockSymbolQueryNode
from programgarden_core.nodes.realtime_korea_stock import (
    KoreaStockRealMarketDataNode,
    KoreaStockRealAccountNode,
    KoreaStockRealOrderEventNode,
)
from programgarden_core.nodes.order import (
    KoreaStockNewOrderNode,
    KoreaStockModifyOrderNode,
    KoreaStockCancelOrderNode,
)

# 모든 국내주식 노드 클래스
ALL_KOREA_STOCK_NODES = [
    KoreaStockBrokerNode,
    KoreaStockAccountNode,
    KoreaStockOpenOrdersNode,
    KoreaStockMarketDataNode,
    KoreaStockFundamentalNode,
    KoreaStockHistoricalDataNode,
    KoreaStockSymbolQueryNode,
    KoreaStockRealMarketDataNode,
    KoreaStockRealAccountNode,
    KoreaStockRealOrderEventNode,
    KoreaStockNewOrderNode,
    KoreaStockModifyOrderNode,
    KoreaStockCancelOrderNode,
]


# ============================================================
# 1. 모델 기본 검증
# ============================================================


class TestKoreaStockNodeModels:
    """13개 노드 인스턴스 생성 및 기본 속성 검증"""

    @pytest.mark.parametrize("node_cls", ALL_KOREA_STOCK_NODES, ids=lambda c: c.__name__)
    def test_instantiation(self, node_cls):
        node = node_cls(id="test1")
        assert node.id == "test1"

    @pytest.mark.parametrize("node_cls", ALL_KOREA_STOCK_NODES, ids=lambda c: c.__name__)
    def test_type_matches_class_name(self, node_cls):
        node = node_cls(id="test1")
        assert node.type == node_cls.__name__

    @pytest.mark.parametrize("node_cls", ALL_KOREA_STOCK_NODES, ids=lambda c: c.__name__)
    def test_product_scope_is_korea_stock(self, node_cls):
        assert node_cls._product_scope == ProductScope.KOREA_STOCK

    @pytest.mark.parametrize("node_cls", ALL_KOREA_STOCK_NODES, ids=lambda c: c.__name__)
    def test_broker_provider_is_ls(self, node_cls):
        assert node_cls._broker_provider == BrokerProvider.LS

    @pytest.mark.parametrize("node_cls", ALL_KOREA_STOCK_NODES, ids=lambda c: c.__name__)
    def test_description_is_i18n(self, node_cls):
        node = node_cls(id="test1")
        assert node.description.startswith("i18n:")

    def test_broker_category_is_infra(self):
        node = KoreaStockBrokerNode(id="b")
        assert node.category == NodeCategory.INFRA

    @pytest.mark.parametrize("node_cls", [
        KoreaStockAccountNode, KoreaStockOpenOrdersNode,
        KoreaStockRealAccountNode, KoreaStockRealOrderEventNode,
    ], ids=lambda c: c.__name__)
    def test_account_category(self, node_cls):
        node = node_cls(id="a")
        assert node.category == NodeCategory.ACCOUNT

    @pytest.mark.parametrize("node_cls", [
        KoreaStockMarketDataNode, KoreaStockFundamentalNode,
        KoreaStockHistoricalDataNode, KoreaStockSymbolQueryNode,
        KoreaStockRealMarketDataNode,
    ], ids=lambda c: c.__name__)
    def test_market_category(self, node_cls):
        node = node_cls(id="m")
        assert node.category == NodeCategory.MARKET

    @pytest.mark.parametrize("node_cls", [
        KoreaStockNewOrderNode, KoreaStockModifyOrderNode, KoreaStockCancelOrderNode,
    ], ids=lambda c: c.__name__)
    def test_order_category(self, node_cls):
        node = node_cls(id="o")
        assert node.category == NodeCategory.ORDER


# ============================================================
# 2. 포트 검증
# ============================================================


class TestKoreaStockNodePorts:
    """입출력 포트 검증"""

    def test_account_outputs(self):
        node = KoreaStockAccountNode(id="a")
        names = [p.name for p in node._outputs]
        assert "held_symbols" in names
        assert "balance" in names
        assert "positions" in names

    def test_account_has_trigger_input(self):
        node = KoreaStockAccountNode(id="a")
        names = [p.name for p in node._inputs]
        assert "trigger" in names

    def test_open_orders_outputs(self):
        node = KoreaStockOpenOrdersNode(id="o")
        names = [p.name for p in node._outputs]
        assert "open_orders" in names
        assert "count" in names

    def test_market_data_output_is_value(self):
        node = KoreaStockMarketDataNode(id="m")
        names = [p.name for p in node._outputs]
        assert "value" in names

    def test_market_data_has_symbol_input(self):
        node = KoreaStockMarketDataNode(id="m")
        names = [p.name for p in node._inputs]
        assert "symbol" in names

    def test_fundamental_output_is_value(self):
        node = KoreaStockFundamentalNode(id="f")
        names = [p.name for p in node._outputs]
        assert "value" in names

    def test_historical_output_is_value(self):
        node = KoreaStockHistoricalDataNode(id="h")
        names = [p.name for p in node._outputs]
        assert "value" in names

    def test_symbol_query_outputs(self):
        node = KoreaStockSymbolQueryNode(id="s")
        names = [p.name for p in node._outputs]
        assert "symbols" in names
        assert "count" in names

    def test_real_market_data_outputs(self):
        node = KoreaStockRealMarketDataNode(id="r")
        names = [p.name for p in node._outputs]
        assert "ohlcv_data" in names
        assert "data" in names

    def test_real_account_outputs(self):
        node = KoreaStockRealAccountNode(id="r")
        names = [p.name for p in node._outputs]
        assert "held_symbols" in names
        assert "balance" in names
        assert "open_orders" in names
        assert "positions" in names

    def test_real_order_event_outputs(self):
        node = KoreaStockRealOrderEventNode(id="r")
        names = [p.name for p in node._outputs]
        assert set(names) == {"accepted", "filled", "modified", "cancelled", "rejected"}

    def test_new_order_has_order_result(self):
        node = KoreaStockNewOrderNode(id="n")
        names = [p.name for p in node._outputs]
        assert "result" in names

    def test_modify_order_outputs(self):
        node = KoreaStockModifyOrderNode(id="m")
        names = [p.name for p in node._outputs]
        assert "modify_result" in names
        assert "modified_order_id" in names

    def test_cancel_order_outputs(self):
        node = KoreaStockCancelOrderNode(id="c")
        names = [p.name for p in node._outputs]
        assert "cancel_result" in names
        assert "cancelled_order_id" in names


# ============================================================
# 3. FieldSchema 검증
# ============================================================


class TestKoreaStockFieldSchema:
    """FieldSchema 정합성 검증"""

    def test_broker_has_provider_and_credential(self):
        schema = KoreaStockBrokerNode.get_field_schema()
        assert "provider" in schema
        assert "credential_id" in schema
        assert schema["credential_id"].credential_types == ["broker_ls_korea_stock"]

    def test_account_has_no_fields(self):
        schema = KoreaStockAccountNode.get_field_schema()
        assert schema == {}

    def test_open_orders_has_no_fields(self):
        schema = KoreaStockOpenOrdersNode.get_field_schema()
        assert schema == {}

    def test_market_data_has_symbol_field(self):
        schema = KoreaStockMarketDataNode.get_field_schema()
        assert "symbol" in schema
        assert schema["symbol"].description.startswith("i18n:")

    def test_market_data_symbol_has_no_exchange(self):
        """국내주식 심볼에는 exchange 필드가 불필요"""
        schema = KoreaStockMarketDataNode.get_field_schema()
        obj_schema = schema["symbol"].object_schema
        field_names = [f["name"] for f in obj_schema]
        assert "exchange" not in field_names
        assert "symbol" in field_names

    def test_fundamental_symbol_has_no_exchange(self):
        schema = KoreaStockFundamentalNode.get_field_schema()
        obj_schema = schema["symbol"].object_schema
        field_names = [f["name"] for f in obj_schema]
        assert "exchange" not in field_names

    def test_historical_has_4_fields(self):
        schema = KoreaStockHistoricalDataNode.get_field_schema()
        assert "symbol" in schema
        assert "start_date" in schema
        assert "end_date" in schema
        assert "interval" in schema
        assert "adjust" in schema

    def test_historical_interval_is_day_week_month(self):
        schema = KoreaStockHistoricalDataNode.get_field_schema()
        assert set(schema["interval"].enum_values) == {"1d", "1w", "1M"}

    def test_symbol_query_market_enum(self):
        schema = KoreaStockSymbolQueryNode.get_field_schema()
        assert "market" in schema
        assert set(schema["market"].enum_values) == {"all", "KOSPI", "KOSDAQ"}

    def test_real_market_data_fields(self):
        schema = KoreaStockRealMarketDataNode.get_field_schema()
        assert "symbol" in schema
        assert "stay_connected" in schema

    def test_real_account_fields(self):
        schema = KoreaStockRealAccountNode.get_field_schema()
        assert "commission_rate" in schema
        assert "market" in schema
        assert "stay_connected" in schema
        assert "sync_interval_sec" in schema

    def test_real_account_market_enum_no_all(self):
        """RealAccountNode은 all 없이 KOSPI/KOSDAQ만"""
        schema = KoreaStockRealAccountNode.get_field_schema()
        assert set(schema["market"].enum_values) == {"KOSPI", "KOSDAQ"}

    def test_real_order_event_filter_enum(self):
        schema = KoreaStockRealOrderEventNode.get_field_schema()
        assert "event_filter" in schema
        assert set(schema["event_filter"].enum_values) == {"all", "SC0", "SC1", "SC2", "SC3", "SC4"}

    def test_new_order_has_price_type(self):
        schema = KoreaStockNewOrderNode.get_field_schema()
        assert "price_type" in schema
        assert set(schema["price_type"].enum_values) == {"limit", "market", "conditional_limit"}

    def test_new_order_has_side_and_order_type(self):
        schema = KoreaStockNewOrderNode.get_field_schema()
        assert "side" in schema
        assert "order_type" in schema
        assert "order" in schema

    def test_modify_order_fields(self):
        schema = KoreaStockModifyOrderNode.get_field_schema()
        assert "original_order_id" in schema
        assert "symbol" in schema
        assert "new_quantity" in schema
        assert "new_price" in schema

    def test_cancel_order_fields(self):
        schema = KoreaStockCancelOrderNode.get_field_schema()
        assert "original_order_id" in schema
        assert "symbol" in schema


# ============================================================
# 4. NodeTypeRegistry 등록 확인
# ============================================================


class TestKoreaStockRegistry:
    """NodeTypeRegistry 등록 확인"""

    @pytest.mark.parametrize("node_cls", ALL_KOREA_STOCK_NODES, ids=lambda c: c.__name__)
    def test_node_registered(self, node_cls):
        from programgarden_core.registry.node_registry import NodeTypeRegistry
        registry = NodeTypeRegistry()
        assert registry.get(node_cls.__name__) is not None

    @pytest.mark.parametrize("node_cls", ALL_KOREA_STOCK_NODES, ids=lambda c: c.__name__)
    def test_registry_schema_product_scope(self, node_cls):
        from programgarden_core.registry.node_registry import NodeTypeRegistry
        registry = NodeTypeRegistry()
        schema = registry.get_schema(node_cls.__name__)
        assert schema is not None
        assert schema.product_scope == "korea_stock"


# ============================================================
# 5. is_tool_enabled 검증
# ============================================================


class TestKoreaStockToolEnabled:
    """AI Agent 도구 활성화 검증"""

    @pytest.mark.parametrize("node_cls", [
        KoreaStockAccountNode,
        KoreaStockOpenOrdersNode,
        KoreaStockMarketDataNode,
        KoreaStockFundamentalNode,
        KoreaStockHistoricalDataNode,
        KoreaStockNewOrderNode,
    ], ids=lambda c: c.__name__)
    def test_tool_enabled_nodes(self, node_cls):
        assert node_cls.is_tool_enabled() is True

    @pytest.mark.parametrize("node_cls", [
        KoreaStockBrokerNode,
        KoreaStockSymbolQueryNode,
        KoreaStockRealMarketDataNode,
        KoreaStockRealAccountNode,
        KoreaStockRealOrderEventNode,
        KoreaStockModifyOrderNode,
        KoreaStockCancelOrderNode,
    ], ids=lambda c: c.__name__)
    def test_tool_disabled_nodes(self, node_cls):
        assert node_cls.is_tool_enabled() is False


# ============================================================
# 6. i18n 키 존재 확인
# ============================================================


class TestKoreaStockI18n:
    """i18n 번역 키 존재 확인"""

    @pytest.fixture(scope="class")
    def ko_translations(self):
        import json
        from pathlib import Path
        path = Path(__file__).parent.parent / "programgarden_core" / "i18n" / "locales" / "ko.json"
        with open(path) as f:
            return json.load(f)

    @pytest.fixture(scope="class")
    def en_translations(self):
        import json
        from pathlib import Path
        path = Path(__file__).parent.parent / "programgarden_core" / "i18n" / "locales" / "en.json"
        with open(path) as f:
            return json.load(f)

    @pytest.mark.parametrize("node_cls", ALL_KOREA_STOCK_NODES, ids=lambda c: c.__name__)
    def test_ko_node_name_exists(self, ko_translations, node_cls):
        key = f"nodes.{node_cls.__name__}.name"
        assert key in ko_translations, f"Missing ko.json key: {key}"

    @pytest.mark.parametrize("node_cls", ALL_KOREA_STOCK_NODES, ids=lambda c: c.__name__)
    def test_ko_node_description_exists(self, ko_translations, node_cls):
        key = f"nodes.{node_cls.__name__}.description"
        assert key in ko_translations, f"Missing ko.json key: {key}"

    @pytest.mark.parametrize("node_cls", ALL_KOREA_STOCK_NODES, ids=lambda c: c.__name__)
    def test_en_node_name_exists(self, en_translations, node_cls):
        key = f"nodes.{node_cls.__name__}.name"
        assert key in en_translations, f"Missing en.json key: {key}"

    @pytest.mark.parametrize("node_cls", ALL_KOREA_STOCK_NODES, ids=lambda c: c.__name__)
    def test_en_node_description_exists(self, en_translations, node_cls):
        key = f"nodes.{node_cls.__name__}.description"
        assert key in en_translations, f"Missing en.json key: {key}"

    def test_ko_kr_market_enums(self, ko_translations):
        assert "enums.kr_market.all" in ko_translations
        assert "enums.kr_market.KOSPI" in ko_translations
        assert "enums.kr_market.KOSDAQ" in ko_translations

    def test_ko_kr_price_type_enums(self, ko_translations):
        assert "enums.kr_price_type.limit" in ko_translations
        assert "enums.kr_price_type.market" in ko_translations
        assert "enums.kr_price_type.conditional_limit" in ko_translations

    def test_ko_sc_event_filter_enums(self, ko_translations):
        for i in range(5):
            key = f"enums.event_filter.SC{i}"
            assert key in ko_translations, f"Missing ko.json key: {key}"


# ============================================================
# 7. 직렬화 (JSON round-trip)
# ============================================================


class TestKoreaStockSerialization:
    """Pydantic 직렬화/역직렬화"""

    @pytest.mark.parametrize("node_cls", ALL_KOREA_STOCK_NODES, ids=lambda c: c.__name__)
    def test_json_round_trip(self, node_cls):
        node = node_cls(id="ser1")
        data = node.model_dump()
        restored = node_cls(**data)
        assert restored.id == "ser1"
        assert restored.type == node_cls.__name__

    def test_historical_custom_fields(self):
        node = KoreaStockHistoricalDataNode(
            id="h1",
            start_date="20240101",
            end_date="20241231",
            interval="1w",
            adjust=False,
        )
        data = node.model_dump()
        assert data["start_date"] == "20240101"
        assert data["interval"] == "1w"
        assert data["adjust"] is False

    def test_new_order_price_type_default(self):
        node = KoreaStockNewOrderNode(id="o1")
        assert node.price_type == "limit"

    def test_real_account_defaults(self):
        node = KoreaStockRealAccountNode(id="ra1")
        assert node.stay_connected is True
        assert node.sync_interval_sec == 60
        assert node.commission_rate == 0.015
        assert node.market == "KOSPI"

    def test_real_order_event_defaults(self):
        node = KoreaStockRealOrderEventNode(id="re1")
        assert node.event_filter == "all"
        assert node.stay_connected is True
