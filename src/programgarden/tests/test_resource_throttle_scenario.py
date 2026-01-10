"""
리소스 급증 시 자동 속도 조절 시나리오 테스트

이 테스트는 다음을 검증합니다:
1. 리소스 사용량에 따른 자동 Throttle 레벨 조절
2. 각 레벨별 속도 감속 (delay_multiplier)
3. 동시 작업 수 자동 제한 (max_concurrent_tasks)
4. 위기 상황에서 주문 실행 보장
5. 플러그인 실행 + 리소스 관리 통합
"""

import asyncio
import time
from datetime import datetime, timezone

import pytest
import pytest_asyncio

from programgarden.plugin import PluginSandbox, PluginTimeoutError
from programgarden.resource import ResourceContext
from programgarden.resource.monitor import ResourceMonitor
from programgarden.resource.limiter import ResourceLimiter
from programgarden.resource.throttle import AdaptiveThrottle, THROTTLE_CONFIG, THROTTLE_STRATEGIES
from programgarden_core.models import ResourceLimits, ResourceUsage
from programgarden_core.models.resource import ThrottleLevel


def make_usage(cpu: float, memory: float) -> ResourceUsage:
    """테스트용 ResourceUsage 생성"""
    return ResourceUsage(
        cpu_percent=cpu,
        memory_percent=memory,
        memory_used_mb=memory * 100,
        memory_available_mb=(100 - memory) * 100,
        disk_percent=30.0,
        disk_used_gb=100.0,
        disk_available_gb=400.0,
        active_workers=3,
        pending_tasks=0,
        timestamp=datetime.now(timezone.utc),
    )


class TestThrottleLevelProgression:
    """Throttle 레벨 진행 테스트"""
    
    @pytest_asyncio.fixture
    async def throttle_components(self):
        """테스트용 Throttle 컴포넌트 생성"""
        limits = ResourceLimits(
            max_cpu_percent=100.0,
            max_memory_percent=100.0,
            max_workers=10,
        )
        monitor = ResourceMonitor()
        await monitor.start()
        limiter = ResourceLimiter(limits)
        throttle = AdaptiveThrottle(monitor, limiter, strategy="conservative")
        await throttle.start()
        
        yield throttle, limiter, limits
        
        await throttle.stop()
        await monitor.stop()
    
    @pytest.mark.asyncio
    async def test_level_none_on_low_resource(self, throttle_components):
        """낮은 리소스 사용 시 NONE 레벨"""
        throttle, _, _ = throttle_components
        
        usage = make_usage(cpu=50, memory=55)
        level = throttle._calculate_level(usage)
        
        assert level == ThrottleLevel.NONE
    
    @pytest.mark.asyncio
    async def test_level_light_on_70_percent(self, throttle_components):
        """70% 리소스 사용 시 LIGHT 레벨"""
        throttle, _, _ = throttle_components
        
        usage = make_usage(cpu=72, memory=68)
        level = throttle._calculate_level(usage)
        
        assert level == ThrottleLevel.LIGHT
    
    @pytest.mark.asyncio
    async def test_level_moderate_on_80_percent(self, throttle_components):
        """80% 리소스 사용 시 MODERATE 레벨"""
        throttle, _, _ = throttle_components
        
        usage = make_usage(cpu=82, memory=78)
        level = throttle._calculate_level(usage)
        
        assert level == ThrottleLevel.MODERATE
    
    @pytest.mark.asyncio
    async def test_level_heavy_on_90_percent(self, throttle_components):
        """90% 리소스 사용 시 HEAVY 레벨"""
        throttle, _, _ = throttle_components
        
        usage = make_usage(cpu=92, memory=88)
        level = throttle._calculate_level(usage)
        
        assert level == ThrottleLevel.HEAVY
    
    @pytest.mark.asyncio
    async def test_level_critical_on_100_percent(self, throttle_components):
        """100% 리소스 사용 시 CRITICAL 레벨"""
        throttle, _, _ = throttle_components
        
        usage = make_usage(cpu=100, memory=95)
        level = throttle._calculate_level(usage)
        
        assert level == ThrottleLevel.CRITICAL


class TestThrottleStateApplication:
    """Throttle 상태 적용 테스트"""
    
    @pytest_asyncio.fixture
    async def throttle_components(self):
        limits = ResourceLimits(
            max_cpu_percent=100.0,
            max_memory_percent=100.0,
            max_workers=10,
        )
        monitor = ResourceMonitor()
        await monitor.start()
        limiter = ResourceLimiter(limits)
        throttle = AdaptiveThrottle(monitor, limiter, strategy="conservative")
        await throttle.start()
        
        yield throttle, limiter, limits
        
        await throttle.stop()
        await monitor.stop()
    
    @pytest.mark.asyncio
    async def test_delay_multiplier_increases_with_level(self, throttle_components):
        """레벨이 올라갈수록 delay_multiplier 증가"""
        throttle, _, _ = throttle_components
        
        delays = {}
        for cpu, level_name in [(50, "none"), (72, "light"), (82, "moderate"), (92, "heavy"), (100, "critical")]:
            usage = make_usage(cpu=cpu, memory=cpu - 5)
            level = throttle._calculate_level(usage)
            await throttle._change_level(level, usage)
            state = throttle.get_state()
            delays[level_name] = state.delay_multiplier
        
        # 레벨별 delay_multiplier 확인
        assert delays["none"] == 1.0
        assert delays["light"] == 1.1
        assert delays["moderate"] == 1.3
        assert delays["heavy"] == 1.5
        assert delays["critical"] == 1.7
    
    @pytest.mark.asyncio
    async def test_concurrent_tasks_decreases_with_level(self, throttle_components):
        """레벨이 올라갈수록 동시 작업 수 감소"""
        throttle, _, limits = throttle_components
        
        # NONE 레벨
        usage = make_usage(cpu=50, memory=55)
        await throttle._change_level(ThrottleLevel.NONE, usage)
        assert throttle.get_state().max_concurrent_tasks == limits.max_workers  # 100%
        
        # HEAVY 레벨
        usage = make_usage(cpu=92, memory=88)
        await throttle._change_level(ThrottleLevel.HEAVY, usage)
        assert throttle.get_state().max_concurrent_tasks == limits.max_workers // 2  # 50%
        
        # CRITICAL 레벨
        usage = make_usage(cpu=100, memory=95)
        await throttle._change_level(ThrottleLevel.CRITICAL, usage)
        assert throttle.get_state().max_concurrent_tasks == 3  # 30%


class TestCriticalModeProtection:
    """CRITICAL 모드 보호 테스트"""
    
    @pytest_asyncio.fixture
    async def throttle_in_critical(self):
        limits = ResourceLimits(
            max_cpu_percent=100.0,
            max_memory_percent=100.0,
            max_workers=10,
        )
        monitor = ResourceMonitor()
        await monitor.start()
        limiter = ResourceLimiter(limits)
        throttle = AdaptiveThrottle(monitor, limiter, strategy="conservative")
        await throttle.start()
        
        # CRITICAL 레벨로 설정
        usage = make_usage(cpu=100, memory=95)
        await throttle._change_level(ThrottleLevel.CRITICAL, usage)
        
        yield throttle
        
        await throttle.stop()
        await monitor.stop()
    
    @pytest.mark.asyncio
    async def test_critical_pauses_new_tasks(self, throttle_in_critical):
        """CRITICAL 모드에서 신규 작업 중단"""
        state = throttle_in_critical.get_state()
        assert state.paused_new_tasks is True
    
    @pytest.mark.asyncio
    async def test_critical_allows_orders(self, throttle_in_critical):
        """CRITICAL 모드에서 주문은 허용"""
        can_order = await throttle_in_critical.acquire(is_order=True, priority=10)
        assert can_order is True
        if can_order:
            throttle_in_critical.release()
    
    @pytest.mark.asyncio
    async def test_critical_allows_high_priority(self, throttle_in_critical):
        """CRITICAL 모드에서 최우선순위 작업 허용"""
        can_high_priority = await throttle_in_critical.acquire(is_order=False, priority=10)
        assert can_high_priority is True
        if can_high_priority:
            throttle_in_critical.release()
    
    @pytest.mark.asyncio
    async def test_critical_blocks_normal_tasks(self, throttle_in_critical):
        """CRITICAL 모드에서 일반 작업 차단"""
        can_normal = await throttle_in_critical.acquire(is_order=False, priority=5)
        assert can_normal is False


class TestResourceRecovery:
    """리소스 복구 테스트"""
    
    @pytest_asyncio.fixture
    async def throttle_components(self):
        limits = ResourceLimits(
            max_cpu_percent=100.0,
            max_memory_percent=100.0,
            max_workers=10,
        )
        monitor = ResourceMonitor()
        await monitor.start()
        limiter = ResourceLimiter(limits)
        throttle = AdaptiveThrottle(monitor, limiter, strategy="conservative")
        await throttle.start()
        
        yield throttle, limits
        
        await throttle.stop()
        await monitor.stop()
    
    @pytest.mark.asyncio
    async def test_recovery_from_critical_to_none(self, throttle_components):
        """CRITICAL에서 NONE으로 복구"""
        throttle, limits = throttle_components
        
        # CRITICAL로 설정
        usage = make_usage(cpu=100, memory=95)
        await throttle._change_level(ThrottleLevel.CRITICAL, usage)
        assert throttle.get_state().paused_new_tasks is True
        
        # 리소스 복구
        usage = make_usage(cpu=50, memory=55)
        level = throttle._calculate_level(usage)
        await throttle._change_level(level, usage)
        
        state = throttle.get_state()
        assert state.level == ThrottleLevel.NONE
        assert state.paused_new_tasks is False
        assert state.max_concurrent_tasks == limits.max_workers


class TestPluginWithResourceThrottling:
    """플러그인 + 리소스 관리 통합 테스트"""
    
    @pytest.mark.asyncio
    async def test_plugin_executes_with_resource_context(self):
        """ResourceContext와 함께 플러그인 실행"""
        limits = ResourceLimits(
            max_cpu_percent=100.0,
            max_memory_percent=100.0,
            max_workers=10,
        )
        ctx = await ResourceContext.create(limits=limits)
        
        async with ctx:
            sandbox = PluginSandbox(resource_context=ctx, default_timeout=10.0)
            
            async def test_plugin(symbols, **kwargs):
                await asyncio.sleep(0.01)
                return {"passed_symbols": symbols, "analysis": {}}
            
            result = await sandbox.execute(
                plugin_id="TestPlugin",
                plugin_callable=test_plugin,
                kwargs={"symbols": ["AAPL", "NVDA"]},
            )
            
            assert "passed_symbols" in result
            assert len(result["passed_symbols"]) == 2
    
    @pytest.mark.asyncio
    async def test_plugin_timeout_in_throttled_mode(self):
        """Throttle 모드에서도 타임아웃 작동"""
        limits = ResourceLimits(
            max_cpu_percent=100.0,
            max_memory_percent=100.0,
            max_workers=10,
        )
        ctx = await ResourceContext.create(limits=limits)
        
        async with ctx:
            sandbox = PluginSandbox(resource_context=ctx, default_timeout=0.5)
            
            async def slow_plugin(**kwargs):
                await asyncio.sleep(5.0)
                return {"passed_symbols": []}
            
            with pytest.raises(PluginTimeoutError):
                await sandbox.execute(
                    plugin_id="SlowPlugin",
                    plugin_callable=slow_plugin,
                    kwargs={},
                    timeout=0.2,
                )
    
    @pytest.mark.asyncio
    async def test_batch_processing_respects_throttle(self):
        """배치 처리가 Throttle 상태 반영"""
        limits = ResourceLimits(
            max_cpu_percent=100.0,
            max_memory_percent=100.0,
            max_workers=10,
        )
        ctx = await ResourceContext.create(limits=limits)
        
        async with ctx:
            sandbox = PluginSandbox(resource_context=ctx, default_timeout=10.0)
            
            execution_count = 0
            
            async def counting_plugin(symbols, **kwargs):
                nonlocal execution_count
                execution_count += 1
                await asyncio.sleep(0.01)
                return {"passed_symbols": symbols, "analysis": {}}
            
            symbols = [f"SYM{i}" for i in range(30)]
            result = await sandbox.execute_batched(
                plugin_id="CountingPlugin",
                plugin_callable=counting_plugin,
                symbols=symbols,
                batch_size=10,
                base_kwargs={},
            )
            
            # 30개 종목을 10개씩 → 3번 실행
            assert execution_count == 3
            assert len(result["passed_symbols"]) == 30


# 시나리오 테스트 함수 (pytest로 실행 가능)
@pytest.mark.asyncio
async def test_full_resource_throttle_scenario():
    """
    전체 리소스 급증 → 속도 조절 → 정상화 시나리오
    
    이 테스트는 실제 운영 시나리오를 시뮬레이션합니다:
    1. 정상 상태에서 시작
    2. 리소스 사용량 점진적 증가
    3. 각 단계에서 적절한 속도 감속 적용
    4. 위기 상황에서 주문 실행 보장
    5. 리소스 정상화 후 전속력 복귀
    """
    limits = ResourceLimits(
        max_cpu_percent=100.0,
        max_memory_percent=100.0,
        max_workers=10,
    )
    
    monitor = ResourceMonitor()
    await monitor.start()
    limiter = ResourceLimiter(limits)
    throttle = AdaptiveThrottle(monitor, limiter, strategy="conservative")
    await throttle.start()
    
    try:
        # Stage 1: 정상 (50%)
        usage = make_usage(cpu=50, memory=55)
        level = throttle._calculate_level(usage)
        await throttle._change_level(level, usage)
        assert level == ThrottleLevel.NONE
        assert throttle.get_state().delay_multiplier == 1.0
        
        # Stage 2: LIGHT (72%)
        usage = make_usage(cpu=72, memory=68)
        level = throttle._calculate_level(usage)
        await throttle._change_level(level, usage)
        assert level == ThrottleLevel.LIGHT
        assert throttle.get_state().delay_multiplier == 1.1
        
        # Stage 3: MODERATE (82%)
        usage = make_usage(cpu=82, memory=78)
        level = throttle._calculate_level(usage)
        await throttle._change_level(level, usage)
        assert level == ThrottleLevel.MODERATE
        assert throttle.get_state().max_concurrent_tasks == 7  # 70%
        
        # Stage 4: HEAVY (92%)
        usage = make_usage(cpu=92, memory=88)
        level = throttle._calculate_level(usage)
        await throttle._change_level(level, usage)
        assert level == ThrottleLevel.HEAVY
        assert throttle.get_state().max_concurrent_tasks == 5  # 50%
        
        # Stage 5: CRITICAL (100%)
        usage = make_usage(cpu=100, memory=95)
        level = throttle._calculate_level(usage)
        await throttle._change_level(level, usage)
        assert level == ThrottleLevel.CRITICAL
        assert throttle.get_state().paused_new_tasks is True
        
        # 주문은 여전히 실행 가능
        can_order = await throttle.acquire(is_order=True, priority=10)
        assert can_order is True
        if can_order:
            throttle.release()
        
        # Stage 6: 복구 (50%)
        usage = make_usage(cpu=50, memory=55)
        level = throttle._calculate_level(usage)
        await throttle._change_level(level, usage)
        assert level == ThrottleLevel.NONE
        assert throttle.get_state().paused_new_tasks is False
        assert throttle.get_state().max_concurrent_tasks == 10  # 100%
        
    finally:
        await throttle.stop()
        await monitor.stop()


if __name__ == "__main__":
    # 직접 실행 시 시나리오 테스트
    print("=" * 70)
    print("🧪 리소스 급증 시 자동 속도 조절 시나리오 테스트")
    print("=" * 70)
    asyncio.run(test_full_resource_throttle_scenario())
    print("\n✅ 모든 시나리오 테스트 통과!")
