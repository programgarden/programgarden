"""
Rate Limit Guard 테스트

노드의 _rate_limit ClassVar 기반 실행 간격/동시 실행 제한이
올바르게 동작하는지 검증.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch

from programgarden_core.models.connection_rule import RateLimitConfig


class MockContext:
    """rate limit 테스트용 mock ExecutionContext"""

    def __init__(self):
        self._node_states = {}
        self.is_running = True
        self.logs = []

    def get_node_state(self, node_id, key):
        return self._node_states.get(f"{node_id}:{key}")

    def set_node_state(self, node_id, key, value):
        self._node_states[f"{node_id}:{key}"] = value

    def log(self, level, message, node_id=None):
        self.logs.append({"level": level, "message": message, "node_id": node_id})

    async def notify_node_state(self, **kwargs):
        pass

    def set_output(self, node_id, port_name, value):
        pass

    def get_all_outputs(self, node_id):
        return {}


class MockWorkflowJob:
    """WorkflowJob._apply_rate_limit_guard를 테스트하기 위한 mock"""

    def __init__(self, context=None):
        self.context = context or MockContext()

    # WorkflowJob의 메서드를 직접 바인딩
    from programgarden.executor import WorkflowJob
    _apply_rate_limit_guard = WorkflowJob._apply_rate_limit_guard
    _release_rate_limit_guard = WorkflowJob._release_rate_limit_guard


class TestRateLimitMinInterval:
    """min_interval_sec (최소 실행 간격) 테스트"""

    @pytest.mark.asyncio
    async def test_first_execution_always_passes(self):
        """첫 실행은 항상 통과"""
        job = MockWorkflowJob()
        result = await job._apply_rate_limit_guard(
            node_id="order1",
            node_type="OverseasStockNewOrderNode",
            config={},
        )
        assert result is None  # 통과

    @pytest.mark.asyncio
    async def test_rapid_reexecution_within_interval_is_skipped(self):
        """min_interval_sec 이내 재실행은 스킵"""
        job = MockWorkflowJob()

        # 첫 실행 (통과 + 시작 마킹)
        result1 = await job._apply_rate_limit_guard(
            node_id="order1",
            node_type="OverseasStockNewOrderNode",
            config={},
        )
        assert result1 is None

        # 첫 실행 완료 (executing_count 해제)
        job._release_rate_limit_guard("order1")

        # 즉시 재실행 (5초 이내이므로 interval 체크에서 스킵)
        result2 = await job._apply_rate_limit_guard(
            node_id="order1",
            node_type="OverseasStockNewOrderNode",
            config={},
        )
        assert result2 is not None
        assert result2["_skipped"] is True
        assert result2["reason"] == "rate_limit_interval"

    @pytest.mark.asyncio
    async def test_execution_after_interval_passes(self):
        """min_interval_sec 경과 후 실행은 통과"""
        job = MockWorkflowJob()

        # 상태에 과거 시간 직접 설정 (5초 전)
        past_time = (datetime.now() - timedelta(seconds=10)).isoformat()
        job.context.set_node_state("order1", "_rate_limit_state", {
            "last_executed_at": past_time,
            "executing_count": 0,
        })

        result = await job._apply_rate_limit_guard(
            node_id="order1",
            node_type="OverseasStockNewOrderNode",
            config={},
        )
        assert result is None  # 5초 이상 경과했으므로 통과


class TestRateLimitMaxConcurrent:
    """max_concurrent (동시 실행 제한) 테스트"""

    @pytest.mark.asyncio
    async def test_concurrent_execution_within_limit_passes(self):
        """max_concurrent 이내 동시 실행은 통과"""
        job = MockWorkflowJob()

        # 첫 실행 통과
        result = await job._apply_rate_limit_guard(
            node_id="order1",
            node_type="OverseasStockNewOrderNode",
            config={},
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_concurrent_execution_exceeding_limit_is_skipped(self):
        """max_concurrent 초과 시 스킵"""
        job = MockWorkflowJob()

        # executing_count를 max_concurrent(1)까지 채움
        job.context.set_node_state("order1", "_rate_limit_state", {
            "executing_count": 1,
            "last_executed_at": (datetime.now() - timedelta(seconds=100)).isoformat(),
        })

        result = await job._apply_rate_limit_guard(
            node_id="order1",
            node_type="OverseasStockNewOrderNode",
            config={},
        )
        assert result is not None
        assert result["_skipped"] is True
        assert result["reason"] == "rate_limit_concurrent"

    @pytest.mark.asyncio
    async def test_release_decreases_executing_count(self):
        """_release_rate_limit_guard 호출 시 executing_count 감소"""
        job = MockWorkflowJob()

        # 실행 시작
        await job._apply_rate_limit_guard(
            node_id="order1",
            node_type="OverseasStockNewOrderNode",
            config={},
        )

        state_before = job.context.get_node_state("order1", "_rate_limit_state")
        assert state_before["executing_count"] == 1

        # 실행 완료
        job._release_rate_limit_guard("order1")

        state_after = job.context.get_node_state("order1", "_rate_limit_state")
        assert state_after["executing_count"] == 0


class TestRateLimitOnThrottleAction:
    """on_throttle 동작 모드 테스트"""

    @pytest.mark.asyncio
    async def test_on_throttle_error_raises_runtime_error(self):
        """on_throttle='error'일 때 RuntimeError 발생"""
        job = MockWorkflowJob()

        # executing_count를 max_concurrent까지 채움
        job.context.set_node_state("order1", "_rate_limit_state", {
            "executing_count": 1,
            "last_executed_at": (datetime.now() - timedelta(seconds=100)).isoformat(),
        })

        with pytest.raises(RuntimeError, match="rate limit exceeded"):
            await job._apply_rate_limit_guard(
                node_id="order1",
                node_type="OverseasStockNewOrderNode",
                config={"rate_limit_action": "error"},
            )

    @pytest.mark.asyncio
    async def test_on_throttle_error_for_interval_raises_runtime_error(self):
        """on_throttle='error'일 때 간격 미달도 RuntimeError 발생"""
        job = MockWorkflowJob()

        # 최근 실행 기록 설정
        job.context.set_node_state("order1", "_rate_limit_state", {
            "executing_count": 0,
            "last_executed_at": datetime.now().isoformat(),
        })

        with pytest.raises(RuntimeError, match="rate limit"):
            await job._apply_rate_limit_guard(
                node_id="order1",
                node_type="OverseasStockNewOrderNode",
                config={"rate_limit_action": "error"},
            )


class TestRateLimitUserConfigOverride:
    """사용자 config 오버라이드 테스트"""

    @pytest.mark.asyncio
    async def test_user_interval_overrides_class_default(self):
        """사용자 rate_limit_interval이 ClassVar 기본값보다 우선"""
        job = MockWorkflowJob()

        # 3초 전 실행 기록 (ClassVar 기본 5초 이내이므로 원래 차단)
        job.context.set_node_state("order1", "_rate_limit_state", {
            "executing_count": 0,
            "last_executed_at": (datetime.now() - timedelta(seconds=3)).isoformat(),
        })

        # 사용자가 rate_limit_interval=2로 설정 (3초 > 2초이므로 통과)
        result = await job._apply_rate_limit_guard(
            node_id="order1",
            node_type="OverseasStockNewOrderNode",
            config={"rate_limit_interval": 2},
        )
        assert result is None  # 사용자 설정 2초 < 경과 3초이므로 통과

    @pytest.mark.asyncio
    async def test_user_interval_stricter_than_default(self):
        """사용자가 더 긴 간격 설정 시 해당 값 적용"""
        job = MockWorkflowJob()

        # 8초 전 실행 기록 (ClassVar 기본 5초 이므로 원래 통과)
        job.context.set_node_state("order1", "_rate_limit_state", {
            "executing_count": 0,
            "last_executed_at": (datetime.now() - timedelta(seconds=8)).isoformat(),
        })

        # 사용자가 rate_limit_interval=10으로 설정 (8초 < 10초이므로 차단)
        result = await job._apply_rate_limit_guard(
            node_id="order1",
            node_type="OverseasStockNewOrderNode",
            config={"rate_limit_interval": 10},
        )
        assert result is not None
        assert result["_skipped"] is True


class TestRateLimitNoConfigNode:
    """_rate_limit이 없는 노드는 제한 없음"""

    @pytest.mark.asyncio
    async def test_node_without_rate_limit_always_passes(self):
        """StartNode 등 _rate_limit이 없는 노드는 항상 통과"""
        job = MockWorkflowJob()

        result = await job._apply_rate_limit_guard(
            node_id="start1",
            node_type="StartNode",
            config={},
        )
        assert result is None  # 제한 없음

    @pytest.mark.asyncio
    async def test_condition_node_without_rate_limit_always_passes(self):
        """ConditionNode은 _rate_limit이 없으므로 항상 통과"""
        job = MockWorkflowJob()

        result = await job._apply_rate_limit_guard(
            node_id="cond1",
            node_type="ConditionNode",
            config={},
        )
        assert result is None


class TestRateLimitHTTPRequestNode:
    """HTTPRequestNode의 rate limit 테스트 (max_concurrent=3, queue 모드)"""

    @pytest.mark.asyncio
    async def test_http_allows_multiple_concurrent(self):
        """HTTPRequestNode은 동시 3개까지 허용"""
        job = MockWorkflowJob()

        # executing_count=2 (max_concurrent=3 미만)
        job.context.set_node_state("http1", "_rate_limit_state", {
            "executing_count": 2,
            "last_executed_at": (datetime.now() - timedelta(seconds=5)).isoformat(),
        })

        result = await job._apply_rate_limit_guard(
            node_id="http1",
            node_type="HTTPRequestNode",
            config={"url": "https://example.com"},
        )
        assert result is None  # 3개 미만이므로 통과

    @pytest.mark.asyncio
    async def test_http_blocks_at_max_concurrent(self):
        """HTTPRequestNode 동시 3개 초과 시 스킵"""
        job = MockWorkflowJob()

        # executing_count=3 (max_concurrent=3 도달)
        job.context.set_node_state("http1", "_rate_limit_state", {
            "executing_count": 3,
            "last_executed_at": (datetime.now() - timedelta(seconds=5)).isoformat(),
        })

        result = await job._apply_rate_limit_guard(
            node_id="http1",
            node_type="HTTPRequestNode",
            config={"url": "https://example.com"},
        )
        assert result is not None
        assert result["_skipped"] is True


class TestRateLimitCooldownSecFallback:
    """AIAgentNode의 cooldown_sec config가 rate_limit_interval 대신 사용되는지 테스트"""

    @pytest.mark.asyncio
    async def test_cooldown_sec_used_as_interval_override(self):
        """cooldown_sec config가 rate_limit_interval 대신 적용"""
        job = MockWorkflowJob()

        # 30초 전 실행 기록 (기본 60초 이내이므로 원래 차단)
        job.context.set_node_state("agent1", "_rate_limit_state", {
            "executing_count": 0,
            "last_executed_at": (datetime.now() - timedelta(seconds=30)).isoformat(),
        })

        # cooldown_sec=20 설정 → 30초 > 20초이므로 통과해야 함
        result = await job._apply_rate_limit_guard(
            node_id="agent1",
            node_type="AIAgentNode",
            config={"cooldown_sec": 20},
        )
        assert result is None  # 통과

    @pytest.mark.asyncio
    async def test_cooldown_sec_stricter_blocks_execution(self):
        """cooldown_sec이 기본값보다 길면 해당 값으로 차단"""
        job = MockWorkflowJob()

        # 70초 전 실행 기록 (기본 60초 경과 → 원래 통과)
        job.context.set_node_state("agent1", "_rate_limit_state", {
            "executing_count": 0,
            "last_executed_at": (datetime.now() - timedelta(seconds=70)).isoformat(),
        })

        # cooldown_sec=120 설정 → 70초 < 120초이므로 차단
        result = await job._apply_rate_limit_guard(
            node_id="agent1",
            node_type="AIAgentNode",
            config={"cooldown_sec": 120},
        )
        assert result is not None
        assert result["_skipped"] is True
        assert result["reason"] == "rate_limit_interval"

    @pytest.mark.asyncio
    async def test_rate_limit_interval_takes_priority_over_cooldown_sec(self):
        """rate_limit_interval이 있으면 cooldown_sec보다 우선"""
        job = MockWorkflowJob()

        # 3초 전 실행 기록
        job.context.set_node_state("order1", "_rate_limit_state", {
            "executing_count": 0,
            "last_executed_at": (datetime.now() - timedelta(seconds=3)).isoformat(),
        })

        # rate_limit_interval=2 (통과) + cooldown_sec=10 (차단)
        # → rate_limit_interval이 우선이므로 통과
        result = await job._apply_rate_limit_guard(
            node_id="order1",
            node_type="OverseasStockNewOrderNode",
            config={"rate_limit_interval": 2, "cooldown_sec": 10},
        )
        assert result is None  # rate_limit_interval=2가 우선, 3초 > 2초 → 통과
