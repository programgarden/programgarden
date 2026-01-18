"""
ThrottleNode 테스트

ThrottleNode의 두 가지 모드(skip, latest)와 
다양한 설정 옵션을 검증합니다.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from programgarden.executor import ThrottleNodeExecutor
from programgarden.context import ExecutionContext


class MockExecutionContext:
    """테스트용 ExecutionContext Mock"""
    
    def __init__(self):
        self._node_states = {}
        self._outputs = {}
        self._logs = []
        self._workflow_edges = []
        self._notify_calls = []
    
    def get_node_state(self, node_id: str, key: str):
        return self._node_states.get(f"{node_id}:{key}")
    
    def set_node_state(self, node_id: str, key: str, value):
        self._node_states[f"{node_id}:{key}"] = value
    
    def get_all_outputs(self, node_id: str):
        return self._outputs.get(node_id, {})
    
    def set_output(self, node_id: str, port_name: str, value):
        if node_id not in self._outputs:
            self._outputs[node_id] = {}
        self._outputs[node_id][port_name] = value
    
    def log(self, level: str, message: str, node_id: str = None):
        self._logs.append({"level": level, "message": message, "node_id": node_id})
    
    async def notify_node_state(self, **kwargs):
        self._notify_calls.append(kwargs)


@pytest.fixture
def executor():
    return ThrottleNodeExecutor()


@pytest.fixture
def context():
    return MockExecutionContext()


class TestThrottleNodeSkipMode:
    """skip 모드 테스트"""
    
    @pytest.mark.asyncio
    async def test_first_data_passes_through_with_pass_first_true(self, executor, context):
        """pass_first=True일 때 첫 데이터는 즉시 통과"""
        config = {
            "mode": "skip",
            "interval_sec": 5.0,
            "pass_first": True,
        }
        
        # 상위 노드 출력 설정
        context._outputs["upstream"] = {"positions": {"AAPL": {"qty": 10}}}
        context._workflow_edges = [{"from": "upstream", "to": "throttle1"}]
        
        result = await executor.execute("throttle1", "ThrottleNode", config, context)
        
        assert result.get("_throttled") is not True
        assert "positions" in result
        assert result["_throttle_stats"]["passed"] is True
    
    @pytest.mark.asyncio
    async def test_first_data_blocked_with_pass_first_false(self, executor, context):
        """pass_first=False일 때 첫 데이터도 쿨다운 적용"""
        config = {
            "mode": "skip",
            "interval_sec": 5.0,
            "pass_first": False,
        }
        
        result = await executor.execute("throttle1", "ThrottleNode", config, context)
        
        assert result.get("_throttled") is True
        assert result["_throttle_stats"]["countdown_sec"] == 5.0
    
    @pytest.mark.asyncio
    async def test_skip_mode_ignores_data_during_cooldown(self, executor, context):
        """skip 모드: 쿨다운 중 데이터 무시"""
        config = {
            "mode": "skip",
            "interval_sec": 5.0,
            "pass_first": True,
        }
        
        # 첫 번째 실행 - 통과
        result1 = await executor.execute("throttle1", "ThrottleNode", config, context)
        assert result1.get("_throttled") is not True
        
        # 두 번째 실행 - 쿨다운 중, 스킵
        result2 = await executor.execute("throttle1", "ThrottleNode", config, context)
        assert result2.get("_throttled") is True
        assert result2["_throttle_stats"]["skipped_count"] == 1
        
        # 세 번째 실행 - 여전히 쿨다운 중
        result3 = await executor.execute("throttle1", "ThrottleNode", config, context)
        assert result3.get("_throttled") is True
        assert result3["_throttle_stats"]["skipped_count"] == 2
    
    @pytest.mark.asyncio
    async def test_skip_mode_no_pending_data(self, executor, context):
        """skip 모드: pending_data를 저장하지 않음"""
        config = {
            "mode": "skip",
            "interval_sec": 5.0,
            "pass_first": True,
        }
        
        context._outputs["upstream"] = {"price": 100}
        context._workflow_edges = [{"from": "upstream", "to": "throttle1"}]
        
        # 첫 번째 실행
        await executor.execute("throttle1", "ThrottleNode", config, context)
        
        # 두 번째 실행 - 새 데이터로
        context._outputs["upstream"] = {"price": 200}
        await executor.execute("throttle1", "ThrottleNode", config, context)
        
        # pending_data가 None인지 확인 (skip 모드)
        state = context.get_node_state("throttle1", "_throttle_state")
        assert state.get("pending_data") is None


class TestThrottleNodeLatestMode:
    """latest 모드 테스트"""
    
    @pytest.mark.asyncio
    async def test_latest_mode_keeps_newest_data(self, executor, context):
        """latest 모드: 최신 데이터를 보관"""
        config = {
            "mode": "latest",
            "interval_sec": 5.0,
            "pass_first": True,
        }
        
        context._outputs["upstream"] = {"price": 100}
        context._workflow_edges = [{"from": "upstream", "to": "throttle1"}]
        
        # 첫 번째 실행
        await executor.execute("throttle1", "ThrottleNode", config, context)
        
        # 두 번째 실행 - 새 데이터
        context._outputs["upstream"] = {"price": 150}
        await executor.execute("throttle1", "ThrottleNode", config, context)
        
        # 세 번째 실행 - 더 새 데이터
        context._outputs["upstream"] = {"price": 200}
        await executor.execute("throttle1", "ThrottleNode", config, context)
        
        # pending_data에 최신 값이 저장됨
        state = context.get_node_state("throttle1", "_throttle_state")
        assert state.get("pending_data", {}).get("price") == 200
    
    @pytest.mark.asyncio
    async def test_latest_mode_uses_pending_after_cooldown(self, executor, context):
        """latest 모드: 쿨다운 후 pending 데이터 사용"""
        config = {
            "mode": "latest",
            "interval_sec": 0.1,  # 짧은 쿨다운
            "pass_first": True,
        }
        
        context._outputs["upstream"] = {"price": 100}
        context._workflow_edges = [{"from": "upstream", "to": "throttle1"}]
        
        # 첫 번째 실행
        result1 = await executor.execute("throttle1", "ThrottleNode", config, context)
        assert result1.get("price") == 100
        
        # 두 번째 실행 - 쿨다운 중
        context._outputs["upstream"] = {"price": 200}
        result2 = await executor.execute("throttle1", "ThrottleNode", config, context)
        assert result2.get("_throttled") is True
        
        # 쿨다운 대기
        await asyncio.sleep(0.15)
        
        # 세 번째 실행 - 쿨다운 끝, pending 데이터(200) 사용
        context._outputs["upstream"] = {"price": 300}  # 새 데이터지만 pending이 우선
        result3 = await executor.execute("throttle1", "ThrottleNode", config, context)
        
        # latest 모드에서는 pending_data를 사용
        assert result3.get("_throttled") is not True
        assert result3.get("price") == 200  # pending data


class TestThrottleNodeIntervalSec:
    """interval_sec 설정 테스트"""
    
    @pytest.mark.asyncio
    async def test_short_interval(self, executor, context):
        """짧은 interval (0.1초)"""
        config = {
            "mode": "skip",
            "interval_sec": 0.1,
            "pass_first": True,
        }
        
        # 첫 실행
        result1 = await executor.execute("throttle1", "ThrottleNode", config, context)
        assert result1.get("_throttled") is not True
        
        # 즉시 두 번째 - 쿨다운 중
        result2 = await executor.execute("throttle1", "ThrottleNode", config, context)
        assert result2.get("_throttled") is True
        
        # 대기 후 세 번째 - 통과
        await asyncio.sleep(0.15)
        result3 = await executor.execute("throttle1", "ThrottleNode", config, context)
        assert result3.get("_throttled") is not True
    
    @pytest.mark.asyncio
    async def test_countdown_decreases(self, executor, context):
        """countdown_sec이 시간에 따라 감소"""
        config = {
            "mode": "skip",
            "interval_sec": 1.0,
            "pass_first": True,
        }
        
        # 첫 실행
        await executor.execute("throttle1", "ThrottleNode", config, context)
        
        # 즉시 두 번째
        result1 = await executor.execute("throttle1", "ThrottleNode", config, context)
        countdown1 = result1["_throttle_stats"]["countdown_sec"]
        
        # 0.3초 대기 후
        await asyncio.sleep(0.3)
        result2 = await executor.execute("throttle1", "ThrottleNode", config, context)
        countdown2 = result2["_throttle_stats"]["countdown_sec"]
        
        # countdown이 감소해야 함
        assert countdown2 < countdown1


class TestThrottleNodeSSENotification:
    """SSE 알림 테스트"""
    
    @pytest.mark.asyncio
    async def test_notify_throttling_state(self, executor, context):
        """쿨다운 중 THROTTLING 상태 알림"""
        config = {
            "mode": "skip",
            "interval_sec": 5.0,
            "pass_first": True,
        }
        
        # 첫 실행
        await executor.execute("throttle1", "ThrottleNode", config, context)
        
        # 두 번째 실행 - THROTTLING 상태
        await executor.execute("throttle1", "ThrottleNode", config, context)
        
        # notify_node_state가 호출되었는지 확인
        throttling_calls = [
            c for c in context._notify_calls 
            if c.get("state") and c["state"].value == "throttling"
        ]
        assert len(throttling_calls) > 0
    
    @pytest.mark.asyncio
    async def test_notify_completed_state_on_pass(self, executor, context):
        """통과 시 COMPLETED 상태 알림"""
        config = {
            "mode": "skip",
            "interval_sec": 5.0,
            "pass_first": True,
        }
        
        # 첫 실행 - 통과
        await executor.execute("throttle1", "ThrottleNode", config, context)
        
        # notify_node_state가 COMPLETED로 호출되었는지 확인
        completed_calls = [
            c for c in context._notify_calls 
            if c.get("state") and c["state"].value == "completed"
        ]
        assert len(completed_calls) > 0


class TestThrottleNodeInputData:
    """입력 데이터 처리 테스트"""
    
    @pytest.mark.asyncio
    async def test_pass_through_all_input_data(self, executor, context):
        """모든 입력 데이터가 그대로 출력으로 전달됨"""
        config = {
            "mode": "skip",
            "interval_sec": 5.0,
            "pass_first": True,
        }
        
        # 복잡한 입력 데이터
        context._outputs["upstream"] = {
            "positions": {"AAPL": {"qty": 10, "price": 150}},
            "balance": {"available": 10000},
            "symbols": ["AAPL", "NVDA"],
        }
        context._workflow_edges = [{"from": "upstream", "to": "throttle1"}]
        
        result = await executor.execute("throttle1", "ThrottleNode", config, context)
        
        # 모든 데이터가 출력에 포함되어야 함
        assert "positions" in result
        assert result["positions"]["AAPL"]["qty"] == 10
        assert "balance" in result
        assert "symbols" in result
    
    @pytest.mark.asyncio
    async def test_realtime_data_from_event(self, executor, context):
        """_realtime_data로 전달된 데이터 처리"""
        config = {
            "mode": "skip",
            "interval_sec": 5.0,
            "pass_first": True,
            "_realtime_data": {"price": 999, "volume": 1000},
        }
        
        result = await executor.execute("throttle1", "ThrottleNode", config, context)
        
        # _realtime_data가 출력에 포함되어야 함
        assert result.get("price") == 999
        assert result.get("volume") == 1000


class TestThrottleNodeStateManagement:
    """상태 관리 테스트"""
    
    @pytest.mark.asyncio
    async def test_cumulative_skipped_count(self, executor, context):
        """skipped_count가 누적됨"""
        config = {
            "mode": "skip",
            "interval_sec": 5.0,
            "pass_first": True,
        }
        
        # 첫 실행 - 통과
        await executor.execute("throttle1", "ThrottleNode", config, context)
        
        # 여러 번 스킵
        for i in range(5):
            result = await executor.execute("throttle1", "ThrottleNode", config, context)
            assert result["_throttle_stats"]["skipped_count"] == i + 1
    
    @pytest.mark.asyncio
    async def test_skipped_count_persists_after_pass(self, executor, context):
        """통과 후에도 skipped_count가 유지됨 (누적 통계)"""
        config = {
            "mode": "skip",
            "interval_sec": 0.1,
            "pass_first": True,
        }
        
        # 첫 실행
        await executor.execute("throttle1", "ThrottleNode", config, context)
        
        # 스킵
        await executor.execute("throttle1", "ThrottleNode", config, context)
        await executor.execute("throttle1", "ThrottleNode", config, context)
        
        # 쿨다운 대기
        await asyncio.sleep(0.15)
        
        # 통과
        result = await executor.execute("throttle1", "ThrottleNode", config, context)
        
        # skipped_count가 유지되어야 함
        assert result["_throttle_stats"]["skipped_count"] == 2


class TestThrottleNodeMultipleInstances:
    """여러 ThrottleNode 인스턴스 테스트"""
    
    @pytest.mark.asyncio
    async def test_independent_state_per_node(self, executor, context):
        """각 노드가 독립적인 상태를 가짐"""
        config = {
            "mode": "skip",
            "interval_sec": 5.0,
            "pass_first": True,
        }
        
        # 노드 1 첫 실행
        result1 = await executor.execute("throttle1", "ThrottleNode", config, context)
        assert result1.get("_throttled") is not True
        
        # 노드 2 첫 실행 - 노드 1과 독립적으로 통과
        result2 = await executor.execute("throttle2", "ThrottleNode", config, context)
        assert result2.get("_throttled") is not True
        
        # 노드 1 두 번째 실행 - 쿨다운 중
        result1_2 = await executor.execute("throttle1", "ThrottleNode", config, context)
        assert result1_2.get("_throttled") is True
        
        # 노드 2 두 번째 실행 - 역시 쿨다운 중
        result2_2 = await executor.execute("throttle2", "ThrottleNode", config, context)
        assert result2_2.get("_throttled") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
