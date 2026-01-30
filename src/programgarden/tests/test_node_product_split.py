"""
Phase 6.3: 노드 상품별 분리 검증 테스트

테스트 항목:
1. Resolver: 브로커 자동 매칭 검증
2. Executor: 분리된 노드 타입 executor 등록 검증
3. 노드 스키마: product_scope, broker_provider 정상 출력

실행:
    cd src/programgarden && poetry run pytest tests/test_node_product_split.py -v
"""

import pytest
from programgarden.resolver import WorkflowResolver, ResolvedNode


class TestResolverBrokerMatching:
    """Resolver 자동 브로커 매칭 검증"""

    def test_stock_broker_matching_valid(self):
        """해외주식 브로커 + 해외주식 노드 → 검증 통과"""
        resolver = WorkflowResolver()
        workflow = {
            "id": "test-stock-valid",
            "name": "해외주식 브로커 매칭 테스트",
            "nodes": [
                {"id": "start", "type": "StartNode"},
                {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "cred"},
                {"id": "market", "type": "OverseasStockMarketDataNode",
                 "symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}]},
            ],
            "edges": [
                {"from": "start", "to": "broker"},
                {"from": "broker", "to": "market"},
            ],
            "credentials": [{"id": "cred", "type": "broker_ls_stock", "data": []}],
        }
        result = resolver.validate(workflow)
        assert result.is_valid, f"검증 실패: {result.errors}"

    def test_futures_broker_matching_valid(self):
        """해외선물 브로커 + 해외선물 노드 → 검증 통과"""
        resolver = WorkflowResolver()
        workflow = {
            "id": "test-futures-valid",
            "name": "해외선물 브로커 매칭 테스트",
            "nodes": [
                {"id": "start", "type": "StartNode"},
                {"id": "broker", "type": "OverseasFuturesBrokerNode", "credential_id": "cred"},
                {"id": "market", "type": "OverseasFuturesMarketDataNode",
                 "symbols": [{"symbol": "NQH25", "exchange": "CME"}]},
            ],
            "edges": [
                {"from": "start", "to": "broker"},
                {"from": "broker", "to": "market"},
            ],
            "credentials": [{"id": "cred", "type": "broker_ls_futures", "data": []}],
        }
        result = resolver.validate(workflow)
        assert result.is_valid, f"검증 실패: {result.errors}"

    def test_missing_stock_broker_error(self):
        """해외주식 노드만 있고 브로커 없음 → 에러"""
        resolver = WorkflowResolver()
        workflow = {
            "id": "test-missing-broker",
            "name": "브로커 누락 테스트",
            "nodes": [
                {"id": "start", "type": "StartNode"},
                {"id": "market", "type": "OverseasStockMarketDataNode",
                 "symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}]},
            ],
            "edges": [
                {"from": "start", "to": "market"},
            ],
            "credentials": [],
        }
        result = resolver.validate(workflow)
        assert not result.is_valid
        assert any("브로커" in e or "BrokerNode" in e for e in result.errors)

    def test_wrong_broker_scope_error(self):
        """해외선물 브로커 + 해외주식 노드 → 에러"""
        resolver = WorkflowResolver()
        workflow = {
            "id": "test-wrong-scope",
            "name": "잘못된 브로커 스코프 테스트",
            "nodes": [
                {"id": "start", "type": "StartNode"},
                {"id": "broker", "type": "OverseasFuturesBrokerNode", "credential_id": "cred"},
                {"id": "market", "type": "OverseasStockMarketDataNode",
                 "symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}]},
            ],
            "edges": [
                {"from": "start", "to": "broker"},
                {"from": "broker", "to": "market"},
            ],
            "credentials": [{"id": "cred", "type": "broker_ls_futures", "data": []}],
        }
        result = resolver.validate(workflow)
        assert not result.is_valid
        assert any("브로커" in e or "BrokerNode" in e for e in result.errors)

    def test_duplicate_stock_broker_error(self):
        """같은 상품 브로커 중복 → 에러"""
        resolver = WorkflowResolver()
        workflow = {
            "id": "test-dup-broker",
            "name": "중복 브로커 테스트",
            "nodes": [
                {"id": "start", "type": "StartNode"},
                {"id": "broker1", "type": "OverseasStockBrokerNode", "credential_id": "cred"},
                {"id": "broker2", "type": "OverseasStockBrokerNode", "credential_id": "cred"},
            ],
            "edges": [
                {"from": "start", "to": "broker1"},
                {"from": "start", "to": "broker2"},
            ],
            "credentials": [{"id": "cred", "type": "broker_ls_stock", "data": []}],
        }
        result = resolver.validate(workflow)
        assert not result.is_valid
        assert any("중복" in e for e in result.errors)

    def test_mixed_brokers_valid(self):
        """해외주식 + 해외선물 브로커 공존 → 검증 통과"""
        resolver = WorkflowResolver()
        workflow = {
            "id": "test-mixed-valid",
            "name": "혼합 브로커 테스트",
            "nodes": [
                {"id": "start", "type": "StartNode"},
                {"id": "stock_broker", "type": "OverseasStockBrokerNode", "credential_id": "cred1"},
                {"id": "futures_broker", "type": "OverseasFuturesBrokerNode", "credential_id": "cred2"},
                {"id": "stock_market", "type": "OverseasStockMarketDataNode",
                 "symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}]},
                {"id": "futures_market", "type": "OverseasFuturesMarketDataNode",
                 "symbols": [{"symbol": "NQH25", "exchange": "CME"}]},
            ],
            "edges": [
                {"from": "start", "to": "stock_broker"},
                {"from": "start", "to": "futures_broker"},
                {"from": "stock_broker", "to": "stock_market"},
                {"from": "futures_broker", "to": "futures_market"},
            ],
            "credentials": [
                {"id": "cred1", "type": "broker_ls_stock", "data": []},
                {"id": "cred2", "type": "broker_ls_futures", "data": []},
            ],
        }
        result = resolver.validate(workflow)
        assert result.is_valid, f"검증 실패: {result.errors}"


class TestExecutorNodeTypeMapping:
    """Executor 분리 노드 타입 매핑 검증"""

    def test_all_split_nodes_have_executors(self):
        """분리된 노드 타입이 모두 executor 맵에 등록되어 있는지 확인"""
        from programgarden import WorkflowExecutor

        executor = WorkflowExecutor()
        executors = executor._executors

        # 분리된 노드 타입 목록
        split_node_types = [
            # BrokerNode
            "OverseasStockBrokerNode",
            "OverseasFuturesBrokerNode",
            # AccountNode
            "OverseasStockAccountNode",
            "OverseasFuturesAccountNode",
            # RealAccountNode
            "OverseasStockRealAccountNode",
            "OverseasFuturesRealAccountNode",
            # MarketDataNode
            "OverseasStockMarketDataNode",
            "OverseasFuturesMarketDataNode",
            # RealMarketDataNode
            "OverseasStockRealMarketDataNode",
            "OverseasFuturesRealMarketDataNode",
            # RealOrderEventNode
            "OverseasStockRealOrderEventNode",
            "OverseasFuturesRealOrderEventNode",
            # HistoricalDataNode
            "OverseasStockHistoricalDataNode",
            "OverseasFuturesHistoricalDataNode",
            # SymbolQueryNode
            "OverseasStockSymbolQueryNode",
            "OverseasFuturesSymbolQueryNode",
            # OrderNode (이미 Phase 3에서 등록됨)
            "OverseasStockNewOrderNode",
            "OverseasStockModifyOrderNode",
            "OverseasStockCancelOrderNode",
            "OverseasFuturesNewOrderNode",
            "OverseasFuturesModifyOrderNode",
            "OverseasFuturesCancelOrderNode",
        ]

        missing = [t for t in split_node_types if t not in executors]
        assert not missing, f"Executor 맵에 등록되지 않은 노드 타입: {missing}"


class TestNodeSchemaProductScope:
    """노드 스키마 product_scope, broker_provider 검증"""

    def test_stock_nodes_have_stock_scope(self):
        """해외주식 노드들의 product_scope가 overseas_stock인지 확인"""
        from programgarden_core.registry import NodeTypeRegistry

        registry = NodeTypeRegistry()
        stock_types = [
            "OverseasStockBrokerNode",
            "OverseasStockMarketDataNode",
            "OverseasStockHistoricalDataNode",
            "OverseasStockRealMarketDataNode",
            "OverseasStockAccountNode",
            "OverseasStockNewOrderNode",
        ]

        for node_type in stock_types:
            schema = registry.get_schema(node_type)
            assert schema is not None, f"스키마를 찾을 수 없음: {node_type}"
            assert schema.product_scope == "overseas_stock", \
                f"{node_type}의 product_scope가 {schema.product_scope} (expected: overseas_stock)"

    def test_futures_nodes_have_futures_scope(self):
        """해외선물 노드들의 product_scope가 overseas_futures인지 확인"""
        from programgarden_core.registry import NodeTypeRegistry

        registry = NodeTypeRegistry()
        futures_types = [
            "OverseasFuturesBrokerNode",
            "OverseasFuturesMarketDataNode",
            "OverseasFuturesHistoricalDataNode",
            "OverseasFuturesRealMarketDataNode",
            "OverseasFuturesAccountNode",
            "OverseasFuturesNewOrderNode",
        ]

        for node_type in futures_types:
            schema = registry.get_schema(node_type)
            assert schema is not None, f"스키마를 찾을 수 없음: {node_type}"
            assert schema.product_scope == "overseas_futures", \
                f"{node_type}의 product_scope가 {schema.product_scope} (expected: overseas_futures)"

    def test_generic_nodes_have_all_scope(self):
        """범용 노드들의 product_scope가 all인지 확인"""
        from programgarden_core.registry import NodeTypeRegistry

        registry = NodeTypeRegistry()
        generic_types = [
            "StartNode",
            "WatchlistNode",
            "ConditionNode",
            "LogicNode",
            "TableDisplayNode",
        ]

        for node_type in generic_types:
            schema = registry.get_schema(node_type)
            assert schema is not None, f"스키마를 찾을 수 없음: {node_type}"
            assert schema.product_scope == "all", \
                f"{node_type}의 product_scope가 {schema.product_scope} (expected: all)"

    def test_broker_nodes_have_ls_provider(self):
        """브로커 노드들의 broker_provider가 ls-sec.co.kr인지 확인"""
        from programgarden_core.registry import NodeTypeRegistry

        registry = NodeTypeRegistry()
        broker_types = [
            "OverseasStockBrokerNode",
            "OverseasFuturesBrokerNode",
        ]

        for node_type in broker_types:
            schema = registry.get_schema(node_type)
            assert schema is not None, f"스키마를 찾을 수 없음: {node_type}"
            assert schema.broker_provider == "ls-sec.co.kr", \
                f"{node_type}의 broker_provider가 {schema.broker_provider} (expected: ls-sec.co.kr)"

    def test_schema_list_includes_product_scope(self):
        """NodeTypeRegistry.list_schemas()에 product_scope 필터링이 동작하는지 확인"""
        from programgarden_core.registry import NodeTypeRegistry

        registry = NodeTypeRegistry()

        stock_schemas = registry.list_schemas(product_scope="overseas_stock")
        futures_schemas = registry.list_schemas(product_scope="overseas_futures")
        all_schemas = registry.list_schemas()

        # 주식 스키마에는 선물 전용 노드가 포함되지 않아야 함
        stock_types = {s.node_type for s in stock_schemas}
        futures_types = {s.node_type for s in futures_schemas}

        assert "OverseasStockBrokerNode" in stock_types
        assert "OverseasFuturesBrokerNode" not in stock_types
        assert "OverseasFuturesBrokerNode" in futures_types
        assert "OverseasStockBrokerNode" not in futures_types

        # 범용 노드는 양쪽 모두에 포함
        assert "StartNode" in stock_types
        assert "StartNode" in futures_types

        # 전체 목록은 가장 많아야 함
        assert len(all_schemas) >= len(stock_schemas)
        assert len(all_schemas) >= len(futures_schemas)
