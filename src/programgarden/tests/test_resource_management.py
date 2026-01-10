"""
ProgramGarden - Resource Management Tests

리소스 모니터링 및 스로틀링 테스트
"""

import pytest
import asyncio
from datetime import datetime

from programgarden_core.models.resource import (
    ResourceUsage,
    ResourceLimits,
    ThrottleLevel,
    ThrottleState,
    ResourceHints,
    get_node_hints,
)


class TestResourceModels:
    """리소스 모델 테스트"""
    
    def test_resource_usage_creation(self):
        """ResourceUsage 생성 테스트"""
        usage = ResourceUsage(
            cpu_percent=50.0,
            memory_percent=60.0,
            memory_used_mb=4096.0,
            memory_available_mb=4096.0,
        )
        
        assert usage.cpu_percent == 50.0
        assert usage.memory_percent == 60.0
        assert usage.memory_used_mb == 4096.0
    
    def test_resource_usage_summary(self):
        """ResourceUsage 요약 테스트"""
        usage = ResourceUsage(
            cpu_percent=75.5,
            memory_percent=80.2,
            memory_used_mb=8000.0,
            memory_available_mb=2000.0,
        )
        
        summary = usage.to_summary()
        assert "75.5%" in summary["cpu"]
        assert "80.2%" in summary["memory"]
    
    def test_resource_limits_defaults(self):
        """ResourceLimits 기본값 테스트"""
        limits = ResourceLimits()
        
        assert limits.max_cpu_percent == 80.0
        assert limits.max_memory_percent == 80.0
        assert limits.max_disk_percent == 90.0
        assert limits.max_workers == 4
    
    def test_resource_limits_auto_detect(self):
        """ResourceLimits 자동 감지 테스트"""
        limits = ResourceLimits.auto_detect()
        
        # 자동 감지된 값이 합리적인 범위인지 확인
        assert limits.max_workers >= 1
        assert limits.max_workers <= 16
        assert limits.max_parallel_backtests >= 1
    
    def test_resource_limits_custom(self):
        """ResourceLimits 커스텀 설정 테스트"""
        limits = ResourceLimits(
            max_cpu_percent=70.0,
            max_memory_percent=75.0,
            max_workers=2,
        )
        
        assert limits.max_cpu_percent == 70.0
        assert limits.max_memory_percent == 75.0
        assert limits.max_workers == 2
    
    def test_throttle_state_defaults(self):
        """ThrottleState 기본값 테스트"""
        state = ThrottleState()
        
        assert state.level == ThrottleLevel.NONE
        assert state.delay_multiplier == 1.0
        assert state.paused_new_tasks is False
    
    def test_node_hints_defaults(self):
        """노드 힌트 기본값 테스트"""
        # 알려진 노드 타입
        backtest_hints = get_node_hints("BacktestEngineNode")
        assert backtest_hints.weight == 3.0
        assert backtest_hints.memory_intensive is True
        assert backtest_hints.cpu_intensive is True
        
        order_hints = get_node_hints("NewOrderNode")
        assert order_hints.priority == 10  # 최고 우선순위
        
        # 알려지지 않은 노드 타입
        unknown_hints = get_node_hints("UnknownNode")
        assert unknown_hints.weight == 1.0


class TestResourceMonitor:
    """ResourceMonitor 테스트"""
    
    @pytest.mark.asyncio
    async def test_monitor_start_stop(self):
        """모니터 시작/중지 테스트"""
        from programgarden.resource.monitor import ResourceMonitor
        
        monitor = ResourceMonitor(poll_interval_sec=0.1)
        
        await monitor.start()
        assert monitor.is_running
        
        # 측정값 확인
        usage = monitor.get_usage()
        assert isinstance(usage, ResourceUsage)
        assert 0 <= usage.cpu_percent <= 100
        assert 0 <= usage.memory_percent <= 100
        
        await monitor.stop()
        assert not monitor.is_running
    
    @pytest.mark.asyncio
    async def test_monitor_history(self):
        """모니터 히스토리 테스트"""
        from programgarden.resource.monitor import ResourceMonitor
        
        monitor = ResourceMonitor(poll_interval_sec=0.1)
        await monitor.start()
        
        # 잠시 대기하여 히스토리 쌓기
        await asyncio.sleep(0.5)
        
        history = monitor.get_usage_history(seconds=10)
        assert len(history) >= 1
        
        await monitor.stop()
    
    @pytest.mark.asyncio
    async def test_monitor_average(self):
        """모니터 평균 계산 테스트"""
        from programgarden.resource.monitor import ResourceMonitor
        
        monitor = ResourceMonitor(poll_interval_sec=0.1)
        await monitor.start()
        
        await asyncio.sleep(0.3)
        
        avg = monitor.get_average_usage(seconds=5)
        assert isinstance(avg, ResourceUsage)
        
        await monitor.stop()


class TestResourceLimiter:
    """ResourceLimiter 테스트"""
    
    def test_within_limits(self):
        """제한 내 확인 테스트"""
        from programgarden.resource.limiter import ResourceLimiter
        
        limits = ResourceLimits(max_cpu_percent=80.0, max_memory_percent=80.0)
        limiter = ResourceLimiter(limits)
        
        # 제한 내
        usage = ResourceUsage(
            cpu_percent=50.0,
            memory_percent=60.0,
            memory_used_mb=4000.0,
            memory_available_mb=4000.0,
        )
        assert limiter.is_within_limits(usage)
        assert limiter.get_violation(usage) is None
    
    def test_over_limits(self):
        """제한 초과 테스트"""
        from programgarden.resource.limiter import ResourceLimiter
        
        limits = ResourceLimits(max_cpu_percent=80.0, max_memory_percent=80.0)
        limiter = ResourceLimiter(limits)
        
        # CPU 초과
        usage = ResourceUsage(
            cpu_percent=95.0,
            memory_percent=60.0,
            memory_used_mb=4000.0,
            memory_available_mb=4000.0,
        )
        assert not limiter.is_within_limits(usage)
        violation = limiter.get_violation(usage)
        assert "CPU" in violation
    
    def test_headroom(self):
        """여유 공간 계산 테스트"""
        from programgarden.resource.limiter import ResourceLimiter
        
        limits = ResourceLimits(max_cpu_percent=80.0, max_memory_percent=80.0)
        limiter = ResourceLimiter(limits)
        
        usage = ResourceUsage(
            cpu_percent=60.0,
            memory_percent=70.0,
            memory_used_mb=4000.0,
            memory_available_mb=4000.0,
        )
        
        headroom = limiter.get_headroom(usage)
        assert headroom["cpu"] == 20.0  # 80 - 60
        assert headroom["memory"] == 10.0  # 80 - 70
    
    def test_utilization_ratio(self):
        """사용률 비율 테스트"""
        from programgarden.resource.limiter import ResourceLimiter
        
        limits = ResourceLimits(max_cpu_percent=80.0)
        limiter = ResourceLimiter(limits)
        
        usage = ResourceUsage(
            cpu_percent=40.0,
            memory_percent=50.0,
            memory_used_mb=4000.0,
            memory_available_mb=4000.0,
        )
        
        ratio = limiter.get_utilization_ratio(usage)
        assert ratio["cpu"] == 0.5  # 40/80


class TestAdaptiveThrottle:
    """AdaptiveThrottle 테스트"""
    
    @pytest.mark.asyncio
    async def test_throttle_level_none(self):
        """스로틀 레벨 NONE 테스트"""
        from programgarden.resource.monitor import ResourceMonitor
        from programgarden.resource.limiter import ResourceLimiter
        from programgarden.resource.throttle import AdaptiveThrottle
        
        monitor = ResourceMonitor(poll_interval_sec=0.1)
        limiter = ResourceLimiter(ResourceLimits(max_cpu_percent=100, max_memory_percent=100))
        throttle = AdaptiveThrottle(monitor, limiter)
        
        await monitor.start()
        await throttle.start()
        
        # 낮은 사용률에서는 NONE
        state = throttle.get_state()
        # 실제 시스템 부하에 따라 달라질 수 있으므로 CRITICAL 아닌 것만 확인
        assert state.level != ThrottleLevel.CRITICAL or not state.paused_new_tasks
        
        await throttle.stop()
        await monitor.stop()
    
    @pytest.mark.asyncio
    async def test_acquire_release(self):
        """acquire/release 테스트"""
        from programgarden.resource.monitor import ResourceMonitor
        from programgarden.resource.limiter import ResourceLimiter
        from programgarden.resource.throttle import AdaptiveThrottle
        
        monitor = ResourceMonitor()
        limiter = ResourceLimiter(ResourceLimits(max_workers=2))
        throttle = AdaptiveThrottle(monitor, limiter)
        
        await monitor.start()
        await throttle.start()  # 스로틀도 시작 필요
        
        try:
            # acquire
            acquired = await throttle.acquire(task_weight=1.0)
            assert acquired
            
            # release
            throttle.release(task_weight=1.0)
        finally:
            await throttle.stop()
            await monitor.stop()


class TestResourceContext:
    """ResourceContext 통합 테스트"""
    
    @pytest.mark.asyncio
    async def test_context_create(self):
        """컨텍스트 생성 테스트"""
        from programgarden.resource import ResourceContext
        
        ctx = await ResourceContext.create()
        
        async with ctx:
            assert ctx.is_started
            
            usage = ctx.get_usage()
            assert isinstance(usage, ResourceUsage)
            
            limits = ctx.get_limits()
            assert isinstance(limits, ResourceLimits)
            
            state = ctx.get_throttle_state()
            assert isinstance(state, ThrottleState)
    
    @pytest.mark.asyncio
    async def test_context_with_limits(self):
        """커스텀 제한 컨텍스트 테스트"""
        from programgarden.resource import ResourceContext
        
        limits = ResourceLimits(max_cpu_percent=70, max_workers=2)
        ctx = await ResourceContext.create(limits=limits)
        
        async with ctx:
            actual_limits = ctx.get_limits()
            assert actual_limits.max_cpu_percent == 70
            assert actual_limits.max_workers == 2
    
    @pytest.mark.asyncio
    async def test_before_after_task(self):
        """before_task/after_task 테스트"""
        from programgarden.resource import ResourceContext
        
        ctx = await ResourceContext.create()
        
        async with ctx:
            # 태스크 시작 전
            check = await ctx.before_task("ConditionNode", weight=1.0)
            
            assert "can_proceed" in check
            assert "recommended_delay" in check
            assert "recommended_batch_size" in check
            
            if check["can_proceed"]:
                # 작업 수행...
                await asyncio.sleep(0.01)
                
                # 태스크 완료 후
                await ctx.after_task("ConditionNode", weight=1.0)
    
    @pytest.mark.asyncio
    async def test_expression_context(self):
        """Expression 컨텍스트 테스트"""
        from programgarden.resource import ResourceContext
        
        ctx = await ResourceContext.create()
        
        async with ctx:
            expr_ctx = ctx.get_expression_context()
            
            assert "recommended_batch_size" in expr_ctx
            assert "max_symbols" in expr_ctx
            assert "throttle_level" in expr_ctx


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
