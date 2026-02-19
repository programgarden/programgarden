"""
NodeRunner 단위 테스트

워크플로우 없이 개별 노드를 단독 실행하는 NodeRunner API 테스트.
LS 로그인 및 외부 API 호출은 mock 처리.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, Any, List

from programgarden.node_runner import (
    NodeRunner,
    _REALTIME_NODE_TYPES,
    _BROKER_NODE_TYPES,
    _BROKER_DEPENDENT_NODE_TYPES,
)
from programgarden_core.nodes.base import BaseNode, NodeCategory, OutputPort


# ─────────────────────────────────────────────────
# 테스트용 노드 클래스
# ─────────────────────────────────────────────────

class DummyNode(BaseNode):
    """단순 테스트 노드 (외부 의존 없음)"""
    type: str = "Dynamic_Dummy"
    category: NodeCategory = NodeCategory.DATA
    message: str = "hello"

    _outputs: List[OutputPort] = [
        OutputPort(name="result", type="string"),
    ]

    async def execute(self, context) -> Dict[str, Any]:
        return {"result": f"echo: {self.message}"}


# ─────────────────────────────────────────────────
# Phase 1: 기본 실행 테스트
# ─────────────────────────────────────────────────

class TestNodeRunnerBasic:
    """단순 노드 실행 테스트"""

    @pytest.mark.asyncio
    async def test_run_simple_node(self):
        """동적 노드를 NodeRunner로 단독 실행"""
        from programgarden.executor import WorkflowExecutor

        executor = WorkflowExecutor()
        executor.register_dynamic_schemas([{
            "node_type": "Dynamic_Dummy",
            "category": "data",
            "outputs": [{"name": "result", "type": "string"}],
        }])
        executor.inject_node_classes({"Dynamic_Dummy": DummyNode})

        runner = NodeRunner()
        result = await runner.run("Dynamic_Dummy", message="world")

        assert result["result"] == "echo: world"
        await runner.cleanup()
        executor.clear_injected_classes()

    @pytest.mark.asyncio
    async def test_run_with_custom_node_id(self):
        """커스텀 node_id 지정"""
        from programgarden.executor import WorkflowExecutor

        executor = WorkflowExecutor()
        executor.register_dynamic_schemas([{
            "node_type": "Dynamic_Dummy",
            "category": "data",
            "outputs": [{"name": "result", "type": "string"}],
        }])
        executor.inject_node_classes({"Dynamic_Dummy": DummyNode})

        runner = NodeRunner()
        result = await runner.run("Dynamic_Dummy", node_id="my-node-1", message="test")

        assert result["result"] == "echo: test"
        await runner.cleanup()
        executor.clear_injected_classes()

    @pytest.mark.asyncio
    async def test_run_unknown_node_type(self):
        """존재하지 않는 노드 타입 → RuntimeError"""
        runner = NodeRunner()
        with pytest.raises(RuntimeError, match="Unknown node type"):
            await runner.run("NonExistentNode")
        await runner.cleanup()


# ─────────────────────────────────────────────────
# Phase 2: Credential 테스트
# ─────────────────────────────────────────────────

class TestNodeRunnerCredential:
    """Credential 관련 테스트"""

    def test_credential_type_parsing_overseas_stock(self):
        """broker_ls_overseas_stock → product=overseas_stock"""
        runner = NodeRunner(credentials=[{
            "credential_id": "broker",
            "type": "broker_ls_overseas_stock",
            "data": {"appkey": "test_key", "appsecret": "test_secret"},
        }])

        info = runner._parse_broker_credential("broker")
        assert info is not None
        assert info["product"] == "overseas_stock"
        assert info["appkey"] == "test_key"
        assert info["paper_trading"] is False  # overseas_stock은 모의투자 강제 비활성

    def test_credential_type_parsing_overseas_futures(self):
        """broker_ls_overseas_futures → product=overseas_futures"""
        runner = NodeRunner(credentials=[{
            "credential_id": "broker",
            "type": "broker_ls_overseas_futures",
            "data": {"appkey": "key", "appsecret": "secret", "paper_trading": True},
        }])

        info = runner._parse_broker_credential("broker")
        assert info is not None
        assert info["product"] == "overseas_futures"
        assert info["paper_trading"] is True  # futures는 모의투자 지원

    def test_credential_type_parsing_non_broker(self):
        """non-broker credential → None"""
        runner = NodeRunner(credentials=[{
            "credential_id": "telegram",
            "type": "telegram",
            "data": {"bot_token": "xxx", "chat_id": "yyy"},
        }])

        info = runner._parse_broker_credential("telegram")
        assert info is None

    def test_credential_type_parsing_not_found(self):
        """존재하지 않는 credential_id → None"""
        runner = NodeRunner(credentials=[])
        info = runner._parse_broker_credential("nonexistent")
        assert info is None

    def test_credential_type_parsing_list_data(self):
        """data가 list 형태인 경우도 정상 파싱"""
        runner = NodeRunner(credentials=[{
            "credential_id": "broker",
            "type": "broker_ls_overseas_stock",
            "data": [
                {"key": "appkey", "value": "list_key"},
                {"key": "appsecret", "value": "list_secret"},
            ],
        }])

        info = runner._parse_broker_credential("broker")
        assert info is not None
        assert info["appkey"] == "list_key"
        assert info["appsecret"] == "list_secret"

    def test_overseas_stock_paper_trading_forced_real(self):
        """overseas_stock + paper_trading=True → 강제 실전 모드"""
        runner = NodeRunner(credentials=[{
            "credential_id": "broker",
            "type": "broker_ls_overseas_stock",
            "data": {"appkey": "k", "appsecret": "s", "paper_trading": True},
        }])

        info = runner._parse_broker_credential("broker")
        assert info["paper_trading"] is False

    @pytest.mark.asyncio
    async def test_run_missing_credential(self):
        """브로커 노드에 credential 없이 실행 → ValueError"""
        runner = NodeRunner()
        with pytest.raises(ValueError, match="not found"):
            await runner.run(
                "OverseasStockMarketDataNode",
                credential_id="nonexistent",
            )
        await runner.cleanup()


# ─────────────────────────────────────────────────
# Phase 2: 브로커 자동 로그인 테스트
# ─────────────────────────────────────────────────

class TestNodeRunnerBroker:
    """브로커 자동 로그인 + connection 주입 테스트"""

    @pytest.mark.asyncio
    async def test_broker_auto_login_and_connection_inject(self):
        """브로커 노드 실행 시 자동 로그인 + connection 주입"""
        runner = NodeRunner(credentials=[{
            "credential_id": "broker",
            "type": "broker_ls_overseas_stock",
            "data": {"appkey": "test_key", "appsecret": "test_secret"},
        }])

        mock_ls = MagicMock()
        with patch(
            "programgarden.executor.ensure_ls_login",
            return_value=(mock_ls, True, None),
        ):
            # execute_node을 mock하여 config에 connection이 주입되었는지 확인
            captured_config = {}
            original_execute_node = runner._workflow_executor.execute_node

            async def mock_execute_node(node_id, node_type, config, context, **kw):
                captured_config.update(config)
                return {"positions": [], "count": 0}

            runner._workflow_executor.execute_node = mock_execute_node

            result = await runner.run(
                "OverseasStockAccountNode",
                credential_id="broker",
            )

            # connection이 자동 주입되었는지 확인
            assert "connection" in captured_config
            conn = captured_config["connection"]
            assert conn["provider"] == "ls-sec.co.kr"
            assert conn["product"] == "overseas_stock"
            assert conn["appkey"] == "test_key"
            assert conn["paper_trading"] is False

            # credential_id도 config에 포함
            assert captured_config["credential_id"] == "broker"

        await runner.cleanup()

    @pytest.mark.asyncio
    async def test_broker_login_failure(self):
        """LS 로그인 실패 → RuntimeError"""
        runner = NodeRunner(credentials=[{
            "credential_id": "broker",
            "type": "broker_ls_overseas_stock",
            "data": {"appkey": "bad_key", "appsecret": "bad_secret"},
        }])

        with patch(
            "programgarden.executor.ensure_ls_login",
            return_value=(None, False, "Invalid credentials"),
        ):
            with pytest.raises(RuntimeError, match="LS login failed"):
                await runner.run(
                    "OverseasStockAccountNode",
                    credential_id="broker",
                )

        await runner.cleanup()

    @pytest.mark.asyncio
    async def test_broker_session_reuse(self):
        """동일 product에 대해 LS 로그인은 1회만 수행"""
        runner = NodeRunner(credentials=[{
            "credential_id": "broker",
            "type": "broker_ls_overseas_stock",
            "data": {"appkey": "k", "appsecret": "s"},
        }])

        call_count = 0
        mock_ls = MagicMock()

        def counting_login(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return (mock_ls, True, None)

        with patch("programgarden.executor.ensure_ls_login", side_effect=counting_login):
            runner._workflow_executor.execute_node = AsyncMock(return_value={"data": []})

            await runner.run("OverseasStockAccountNode", credential_id="broker")
            await runner.run("OverseasStockMarketDataNode", credential_id="broker",
                           symbols=[{"symbol": "AAPL", "exchange": "NASDAQ"}])

            # ensure_ls_login은 1회만 호출되어야 함
            assert call_count == 1

        await runner.cleanup()

    @pytest.mark.asyncio
    async def test_missing_appkey_appsecret(self):
        """appkey/appsecret 누락 → ValueError"""
        runner = NodeRunner(credentials=[{
            "credential_id": "broker",
            "type": "broker_ls_overseas_stock",
            "data": {},
        }])

        with pytest.raises(ValueError, match="appkey/appsecret not found"):
            await runner.run("OverseasStockAccountNode", credential_id="broker")

        await runner.cleanup()


# ─────────────────────────────────────────────────
# Phase 3: 편의 기능 테스트
# ─────────────────────────────────────────────────

class TestNodeRunnerConvenience:
    """편의 기능 테스트"""

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """async with 패턴"""
        from programgarden.executor import WorkflowExecutor

        executor = WorkflowExecutor()
        executor.register_dynamic_schemas([{
            "node_type": "Dynamic_Dummy",
            "category": "data",
            "outputs": [{"name": "result", "type": "string"}],
        }])
        executor.inject_node_classes({"Dynamic_Dummy": DummyNode})

        async with NodeRunner() as runner:
            result = await runner.run("Dynamic_Dummy", message="ctx_mgr")
            assert result["result"] == "echo: ctx_mgr"

        # cleanup 호출 확인 (context가 None으로 정리됨)
        assert runner._context is None
        executor.clear_injected_classes()

    @pytest.mark.asyncio
    async def test_raise_on_error_true(self):
        """raise_on_error=True → error 결과 시 RuntimeError"""
        runner = NodeRunner(raise_on_error=True)
        runner._workflow_executor.execute_node = AsyncMock(
            return_value={"error": "something went wrong"}
        )

        with pytest.raises(RuntimeError, match="something went wrong"):
            await runner.run("FieldMappingNode")

        await runner.cleanup()

    @pytest.mark.asyncio
    async def test_raise_on_error_false(self):
        """raise_on_error=False → error 결과를 그대로 반환"""
        runner = NodeRunner(raise_on_error=False)
        runner._workflow_executor.execute_node = AsyncMock(
            return_value={"error": "something went wrong"}
        )

        result = await runner.run("FieldMappingNode")
        assert result["error"] == "something went wrong"

        await runner.cleanup()

    @pytest.mark.asyncio
    async def test_realtime_node_blocked(self):
        """실시간 노드 실행 시도 → ValueError"""
        runner = NodeRunner()
        for rt_type in _REALTIME_NODE_TYPES:
            with pytest.raises(ValueError, match="실시간"):
                await runner.run(rt_type)
        await runner.cleanup()

    @pytest.mark.asyncio
    async def test_broker_node_blocked(self):
        """BrokerNode 직접 실행 시도 → ValueError"""
        runner = NodeRunner()
        for bt_type in _BROKER_NODE_TYPES:
            with pytest.raises(ValueError, match="직접 실행할 필요 없습니다"):
                await runner.run(bt_type)
        await runner.cleanup()

    def test_list_node_types(self):
        """사용 가능한 노드 타입 목록 조회"""
        runner = NodeRunner()
        types = runner.list_node_types()

        # 실시간/브로커 노드는 제외되어야 함
        for rt in _REALTIME_NODE_TYPES:
            assert rt not in types
        for bt in _BROKER_NODE_TYPES:
            assert bt not in types

        # 기본 노드는 포함되어야 함
        assert "FieldMappingNode" in types
        assert "ConditionNode" in types

    def test_get_node_schema(self):
        """노드 스키마 조회"""
        runner = NodeRunner()
        schema = runner.get_node_schema("FieldMappingNode")
        assert schema is not None
        assert isinstance(schema, dict)

    def test_get_node_schema_unknown(self):
        """존재하지 않는 노드 스키마 조회 → None"""
        runner = NodeRunner()
        schema = runner.get_node_schema("NonExistentNode")
        assert schema is None

    @pytest.mark.asyncio
    async def test_cleanup_resets_state(self):
        """cleanup() 호출 후 상태 초기화"""
        runner = NodeRunner(credentials=[{
            "credential_id": "broker",
            "type": "broker_ls_overseas_stock",
            "data": {"appkey": "k", "appsecret": "s"},
        }])

        # context 생성
        runner._get_or_create_context()
        runner._broker_logged_in["overseas_stock"] = True

        assert runner._context is not None
        assert len(runner._broker_logged_in) == 1

        await runner.cleanup()

        assert runner._context is None
        assert len(runner._broker_logged_in) == 0
