"""
연결 규칙(Connection Rules) 검증 테스트

실시간 노드 → 위험 노드 직접 연결 차단이 올바르게 동작하는지 검증.
"""

import pytest
from programgarden.resolver import WorkflowResolver


BASE_WORKFLOW = {"id": "test-wf", "name": "Connection Rules Test"}


def make_workflow(nodes, edges):
    """테스트용 워크플로우 생성 헬퍼"""
    return {**BASE_WORKFLOW, "nodes": nodes, "edges": edges}


class TestRealtimeToOrderConnectionBlocking:
    """실시간 → 주문 노드 직결 차단 테스트"""

    def setup_method(self):
        self.resolver = WorkflowResolver()

    def test_realtime_market_to_order_direct_is_blocked(self):
        """실시간 시세 → 주문 직결 시 validation error"""
        workflow = make_workflow(
            nodes=[
                {"id": "start", "type": "StartNode"},
                {"id": "broker", "type": "OverseasStockBrokerNode"},
                {"id": "realtime", "type": "OverseasStockRealMarketDataNode"},
                {"id": "order", "type": "OverseasStockNewOrderNode"},
            ],
            edges=[
                {"from": "start", "to": "broker"},
                {"from": "broker", "to": "realtime"},
                {"from": "realtime", "to": "order"},
            ],
        )
        result = self.resolver.validate(workflow)
        assert not result.is_valid
        assert any("직접 연결이 차단" in e for e in result.errors)

    def test_realtime_account_to_order_direct_is_blocked(self):
        """실시간 계좌 → 주문 직결 시 validation error"""
        workflow = make_workflow(
            nodes=[
                {"id": "start", "type": "StartNode"},
                {"id": "broker", "type": "OverseasStockBrokerNode"},
                {"id": "realtime_acct", "type": "OverseasStockRealAccountNode"},
                {"id": "order", "type": "OverseasStockNewOrderNode"},
            ],
            edges=[
                {"from": "start", "to": "broker"},
                {"from": "broker", "to": "realtime_acct"},
                {"from": "realtime_acct", "to": "order"},
            ],
        )
        result = self.resolver.validate(workflow)
        assert not result.is_valid
        assert any("ThrottleNode" in e for e in result.errors)

    def test_realtime_order_event_to_order_direct_is_blocked(self):
        """실시간 주문이벤트 → 주문 직결 시 validation error (무한 루프 위험)"""
        workflow = make_workflow(
            nodes=[
                {"id": "start", "type": "StartNode"},
                {"id": "broker", "type": "OverseasStockBrokerNode"},
                {"id": "event", "type": "OverseasStockRealOrderEventNode"},
                {"id": "order", "type": "OverseasStockNewOrderNode"},
            ],
            edges=[
                {"from": "start", "to": "broker"},
                {"from": "broker", "to": "event"},
                {"from": "event", "to": "order"},
            ],
        )
        result = self.resolver.validate(workflow)
        assert not result.is_valid

    def test_realtime_to_throttle_to_order_is_allowed(self):
        """실시간 → ThrottleNode → 주문은 정상 통과"""
        workflow = make_workflow(
            nodes=[
                {"id": "start", "type": "StartNode"},
                {"id": "broker", "type": "OverseasStockBrokerNode"},
                {"id": "realtime", "type": "OverseasStockRealMarketDataNode"},
                {"id": "throttle", "type": "ThrottleNode"},
                {"id": "order", "type": "OverseasStockNewOrderNode"},
            ],
            edges=[
                {"from": "start", "to": "broker"},
                {"from": "broker", "to": "realtime"},
                {"from": "realtime", "to": "throttle"},
                {"from": "throttle", "to": "order"},
            ],
        )
        result = self.resolver.validate(workflow)
        assert result.is_valid, f"Unexpected errors: {result.errors}"

    def test_realtime_to_condition_to_order_is_allowed(self):
        """실시간 → 조건 → 주문은 정상 통과 (조건 노드는 차단 대상 아님)"""
        workflow = make_workflow(
            nodes=[
                {"id": "start", "type": "StartNode"},
                {"id": "broker", "type": "OverseasStockBrokerNode"},
                {"id": "realtime", "type": "OverseasStockRealMarketDataNode"},
                {"id": "condition", "type": "ConditionNode", "plugin": "RSI"},
                {"id": "order", "type": "OverseasStockNewOrderNode"},
            ],
            edges=[
                {"from": "start", "to": "broker"},
                {"from": "broker", "to": "realtime"},
                {"from": "realtime", "to": "condition"},
                {"from": "condition", "to": "order"},
            ],
        )
        result = self.resolver.validate(workflow)
        # ConditionNode에서 OrderNode으로의 직접 연결은 허용
        connection_rule_errors = [e for e in result.errors if "직접 연결이 차단" in e]
        assert len(connection_rule_errors) == 0


class TestRealtimeToAIAgentConnectionBlocking:
    """실시간 → AI Agent 직결 차단 테스트"""

    def setup_method(self):
        self.resolver = WorkflowResolver()

    def test_realtime_to_ai_agent_direct_is_blocked(self):
        """실시간 시세 → AI Agent 직결 시 validation error"""
        workflow = make_workflow(
            nodes=[
                {"id": "start", "type": "StartNode"},
                {"id": "broker", "type": "OverseasStockBrokerNode"},
                {"id": "realtime", "type": "OverseasStockRealMarketDataNode"},
                {"id": "llm", "type": "LLMModelNode"},
                {"id": "agent", "type": "AIAgentNode"},
            ],
            edges=[
                {"from": "start", "to": "broker"},
                {"from": "broker", "to": "realtime"},
                {"from": "realtime", "to": "agent"},
                {"from": "llm", "to": "agent", "type": "ai_model"},
            ],
        )
        result = self.resolver.validate(workflow)
        assert not result.is_valid
        assert any("AIAgentNode" in e for e in result.errors)

    def test_tool_edge_from_realtime_is_not_blocked(self):
        """tool 엣지는 검증 대상 아님 (실행 순서가 아닌 도구 등록)"""
        workflow = make_workflow(
            nodes=[
                {"id": "start", "type": "StartNode"},
                {"id": "broker", "type": "OverseasStockBrokerNode"},
                {"id": "realtime", "type": "OverseasStockRealMarketDataNode"},
                {"id": "llm", "type": "LLMModelNode"},
                {"id": "agent", "type": "AIAgentNode"},
            ],
            edges=[
                {"from": "start", "to": "broker"},
                {"from": "broker", "to": "realtime"},
                {"from": "realtime", "to": "agent", "type": "tool"},
                {"from": "llm", "to": "agent", "type": "ai_model"},
            ],
        )
        result = self.resolver.validate(workflow)
        # tool 엣지는 connection_rules 검증 대상 아님
        connection_rule_errors = [e for e in result.errors if "직접 연결이 차단" in e]
        assert len(connection_rule_errors) == 0


class TestRealtimeToHTTPConnectionWarning:
    """실시간 → HTTP 직결 경고 테스트"""

    def setup_method(self):
        self.resolver = WorkflowResolver()

    def test_realtime_to_http_direct_is_warning_only(self):
        """실시간 → HTTP 직결은 WARNING만 (is_valid=True)"""
        workflow = make_workflow(
            nodes=[
                {"id": "start", "type": "StartNode"},
                {"id": "broker", "type": "OverseasStockBrokerNode"},
                {"id": "realtime", "type": "OverseasStockRealMarketDataNode"},
                {"id": "http", "type": "HTTPRequestNode", "url": "https://example.com"},
            ],
            edges=[
                {"from": "start", "to": "broker"},
                {"from": "broker", "to": "realtime"},
                {"from": "realtime", "to": "http"},
            ],
        )
        result = self.resolver.validate(workflow)
        assert result.is_valid, f"Expected valid but got errors: {result.errors}"
        assert len(result.warnings) > 0
        assert any("직접 연결이 차단" in w for w in result.warnings)


class TestNonRealtimeConnectionsAllowed:
    """실시간이 아닌 노드 간 연결은 자유"""

    def setup_method(self):
        self.resolver = WorkflowResolver()

    def test_schedule_to_order_is_allowed(self):
        """ScheduleNode → 주문은 자유 연결"""
        workflow = make_workflow(
            nodes=[
                {"id": "start", "type": "StartNode"},
                {"id": "broker", "type": "OverseasStockBrokerNode"},
                {"id": "schedule", "type": "ScheduleNode"},
                {"id": "order", "type": "OverseasStockNewOrderNode"},
            ],
            edges=[
                {"from": "start", "to": "broker"},
                {"from": "broker", "to": "schedule"},
                {"from": "schedule", "to": "order"},
            ],
        )
        result = self.resolver.validate(workflow)
        assert result.is_valid, f"Unexpected errors: {result.errors}"

    def test_no_connection_rules_nodes_are_free(self):
        """connection_rules가 없는 노드들은 자유 연결"""
        workflow = make_workflow(
            nodes=[
                {"id": "start", "type": "StartNode"},
                {"id": "broker", "type": "OverseasStockBrokerNode"},
                {"id": "market", "type": "OverseasStockMarketDataNode"},
                {"id": "condition", "type": "ConditionNode", "plugin": "RSI"},
            ],
            edges=[
                {"from": "start", "to": "broker"},
                {"from": "broker", "to": "market"},
                {"from": "market", "to": "condition"},
            ],
        )
        result = self.resolver.validate(workflow)
        connection_rule_errors = [e for e in result.errors if "직접 연결이 차단" in e]
        assert len(connection_rule_errors) == 0


class TestFuturesRealtimeConnectionBlocking:
    """해외선물 실시간 노드도 동일하게 차단"""

    def setup_method(self):
        self.resolver = WorkflowResolver()

    def test_futures_realtime_to_order_is_blocked(self):
        """해외선물 실시간 → 해외선물 주문 직결 차단"""
        workflow = make_workflow(
            nodes=[
                {"id": "start", "type": "StartNode"},
                {"id": "broker", "type": "OverseasFuturesBrokerNode"},
                {"id": "realtime", "type": "OverseasFuturesRealMarketDataNode"},
                {"id": "order", "type": "OverseasFuturesNewOrderNode"},
            ],
            edges=[
                {"from": "start", "to": "broker"},
                {"from": "broker", "to": "realtime"},
                {"from": "realtime", "to": "order"},
            ],
        )
        result = self.resolver.validate(workflow)
        assert not result.is_valid
        assert any("직접 연결이 차단" in e for e in result.errors)

    def test_futures_realtime_to_modify_order_is_blocked(self):
        """해외선물 실시간 → 정정 주문 직결 차단"""
        workflow = make_workflow(
            nodes=[
                {"id": "start", "type": "StartNode"},
                {"id": "broker", "type": "OverseasFuturesBrokerNode"},
                {"id": "realtime", "type": "OverseasFuturesRealMarketDataNode"},
                {"id": "modify", "type": "OverseasFuturesModifyOrderNode"},
            ],
            edges=[
                {"from": "start", "to": "broker"},
                {"from": "broker", "to": "realtime"},
                {"from": "realtime", "to": "modify"},
            ],
        )
        result = self.resolver.validate(workflow)
        assert not result.is_valid
