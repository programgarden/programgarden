"""
ProgramGarden - Plugin Sandbox Tests

플러그인 샌드박스 테스트
- 타임아웃 테스트
- 배치 처리 테스트
- 리소스 제한 테스트
"""

import pytest
import asyncio
from typing import List, Dict, Any

from programgarden.plugin import (
    PluginSandbox,
    PluginTimeoutError,
    PluginResourceError,
    get_sandbox,
)
from programgarden_core.models.plugin_resource import (
    TrustLevel,
    PluginResourceHints,
    get_plugin_hints,
    TRUST_LEVEL_LIMITS,
)


class TestPluginResourceHints:
    """PluginResourceHints 모델 테스트"""
    
    def test_default_hints(self):
        """기본 힌트 생성"""
        hints = PluginResourceHints()
        
        assert hints.max_execution_sec == 30.0
        assert hints.max_memory_mb == 100.0
        assert hints.max_symbols_per_call == 100
        assert hints.cpu_intensive is False
    
    def test_custom_hints(self):
        """커스텀 힌트 생성"""
        hints = PluginResourceHints(
            max_execution_sec=60.0,
            max_symbols_per_call=200,
            cpu_intensive=True,
        )
        
        assert hints.max_execution_sec == 60.0
        assert hints.max_symbols_per_call == 200
        assert hints.cpu_intensive is True
    
    def test_weight_calculation(self):
        """가중치 계산"""
        # 기본
        hints = PluginResourceHints()
        assert hints.get_weight() == 1.0
        
        # CPU 집약적
        hints = PluginResourceHints(cpu_intensive=True)
        assert hints.get_weight() == 2.0
        
        # CPU + I/O 집약적
        hints = PluginResourceHints(cpu_intensive=True, io_intensive=True)
        assert hints.get_weight() == 2.5
    
    def test_for_trust_level(self):
        """신뢰 레벨별 힌트"""
        # CORE: 완화된 제한
        core_hints = PluginResourceHints.for_trust_level(TrustLevel.CORE)
        assert core_hints.max_execution_sec == 300.0
        
        # COMMUNITY: 엄격한 제한
        community_hints = PluginResourceHints.for_trust_level(TrustLevel.COMMUNITY)
        assert community_hints.max_execution_sec == 30.0
    
    def test_default_for_category(self):
        """카테고리별 기본 힌트"""
        # 전략 조건
        strategy_hints = PluginResourceHints.default_for_category("strategy_condition")
        assert strategy_hints.cpu_intensive is True
        
        # 주문
        order_hints = PluginResourceHints.default_for_category("new_order")
        assert order_hints.max_execution_sec == 10.0
    
    def test_get_plugin_hints(self):
        """플러그인 ID로 힌트 조회"""
        # 알려진 플러그인
        rsi_hints = get_plugin_hints("RSI")
        assert rsi_hints.cpu_intensive is True
        
        # 알려지지 않은 플러그인
        unknown_hints = get_plugin_hints("UnknownPlugin")
        assert unknown_hints.max_execution_sec == 30.0


class TestTrustLevel:
    """TrustLevel enum 테스트"""
    
    def test_trust_levels(self):
        """신뢰 레벨 값"""
        assert TrustLevel.CORE.value == "core"
        assert TrustLevel.VERIFIED.value == "verified"
        assert TrustLevel.COMMUNITY.value == "community"
    
    def test_trust_level_limits(self):
        """신뢰 레벨별 제한"""
        # CORE는 무제한
        assert TRUST_LEVEL_LIMITS[TrustLevel.CORE]["max_execution_sec"] is None
        
        # COMMUNITY는 제한적
        assert TRUST_LEVEL_LIMITS[TrustLevel.COMMUNITY]["max_execution_sec"] == 30.0


class TestPluginSandbox:
    """PluginSandbox 테스트"""
    
    @pytest.mark.asyncio
    async def test_normal_execution(self):
        """정상 실행"""
        sandbox = PluginSandbox()
        
        async def good_plugin(symbols, price_data, fields):
            return {
                "passed_symbols": symbols[:1],
                "failed_symbols": symbols[1:],
                "values": {s: {"result": True} for s in symbols},
            }
        
        result = await sandbox.execute(
            plugin_id="TestPlugin",
            plugin_callable=good_plugin,
            kwargs={
                "symbols": ["AAPL", "NVDA"],
                "price_data": {},
                "fields": {},
            },
        )
        
        assert result["passed_symbols"] == ["AAPL"]
        assert result["failed_symbols"] == ["NVDA"]
    
    @pytest.mark.asyncio
    async def test_timeout_execution(self):
        """타임아웃 테스트"""
        sandbox = PluginSandbox(default_timeout=0.1)
        
        async def slow_plugin(symbols, price_data, fields):
            await asyncio.sleep(1.0)  # 1초 대기
            return {"passed_symbols": symbols}
        
        with pytest.raises(PluginTimeoutError) as exc_info:
            await sandbox.execute(
                plugin_id="SlowPlugin",
                plugin_callable=slow_plugin,
                kwargs={"symbols": [], "price_data": {}, "fields": {}},
            )
        
        assert "SlowPlugin" in str(exc_info.value)
        assert "0.1s" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_sync_plugin_execution(self):
        """동기 플러그인 실행"""
        sandbox = PluginSandbox()
        
        def sync_plugin(symbols, price_data, fields):
            # 동기 함수
            return {"passed_symbols": symbols}
        
        result = await sandbox.execute(
            plugin_id="SyncPlugin",
            plugin_callable=sync_plugin,
            kwargs={"symbols": ["AAPL"], "price_data": {}, "fields": {}},
        )
        
        assert result["passed_symbols"] == ["AAPL"]
    
    @pytest.mark.asyncio
    async def test_batched_execution(self):
        """배치 실행 테스트"""
        sandbox = PluginSandbox(default_batch_size=3)
        
        call_count = 0
        
        async def counting_plugin(symbols, **kwargs):
            nonlocal call_count
            call_count += 1
            return {
                "passed_symbols": symbols,
                "failed_symbols": [],
                "values": {},
            }
        
        symbols = ["AAPL", "NVDA", "GOOGL", "MSFT", "META", "AMZN", "TSLA"]
        
        result = await sandbox.execute_batched(
            plugin_id="CountingPlugin",
            plugin_callable=counting_plugin,
            symbols=symbols,
        )
        
        # 7개 종목 / 3개 배치 = 3번 호출
        assert call_count == 3
        assert result["batched"] is True
        assert result["batch_count"] == 3
        assert len(result["passed_symbols"]) == 7
    
    @pytest.mark.asyncio
    async def test_batched_timeout_handling(self):
        """배치 타임아웃 처리"""
        sandbox = PluginSandbox(default_batch_size=2, default_timeout=0.1)
        
        call_count = 0
        
        async def intermittent_slow_plugin(symbols, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:  # 두 번째 배치만 느림
                await asyncio.sleep(1.0)
            return {"passed_symbols": symbols, "failed_symbols": [], "values": {}}
        
        symbols = ["AAPL", "NVDA", "GOOGL", "MSFT"]
        
        result = await sandbox.execute_batched(
            plugin_id="IntermittentPlugin",
            plugin_callable=intermittent_slow_plugin,
            symbols=symbols,
        )
        
        # 첫 번째 배치: passed, 두 번째: failed (timeout), 세 번째: passed
        # 실제로 타임아웃된 배치는 failed로 처리됨
        assert "AAPL" in result["passed_symbols"]
        assert "NVDA" in result["passed_symbols"]
    
    @pytest.mark.asyncio
    async def test_stats_tracking(self):
        """통계 추적"""
        sandbox = PluginSandbox()
        
        async def quick_plugin(**kwargs):
            return {"passed_symbols": []}
        
        await sandbox.execute(
            plugin_id="QuickPlugin",
            plugin_callable=quick_plugin,
            kwargs={},
        )
        await sandbox.execute(
            plugin_id="QuickPlugin",
            plugin_callable=quick_plugin,
            kwargs={},
        )
        
        stats = sandbox.get_stats()
        assert stats["total_executions"] == 2
        assert stats["timeouts"] == 0
        assert stats["errors"] == 0
        assert "avg_time_sec" in stats
    
    @pytest.mark.asyncio
    async def test_stats_reset(self):
        """통계 초기화"""
        sandbox = PluginSandbox()
        
        async def quick_plugin(**kwargs):
            return {}
        
        await sandbox.execute(
            plugin_id="Test",
            plugin_callable=quick_plugin,
            kwargs={},
        )
        
        sandbox.reset_stats()
        stats = sandbox.get_stats()
        assert stats["total_executions"] == 0


class TestGetSandbox:
    """get_sandbox 함수 테스트"""
    
    def test_default_sandbox(self):
        """기본 샌드박스 반환"""
        sandbox1 = get_sandbox()
        sandbox2 = get_sandbox()
        
        # 동일한 인스턴스 (싱글톤)
        assert sandbox1 is sandbox2
    
    @pytest.mark.asyncio
    async def test_sandbox_with_resource_context(self):
        """리소스 컨텍스트와 함께 생성"""
        from programgarden.resource import ResourceContext
        
        ctx = await ResourceContext.create()
        
        async with ctx:
            sandbox = get_sandbox(resource_context=ctx)
            
            # 새 인스턴스 (리소스 컨텍스트가 다름)
            assert sandbox._resource_context is ctx


class TestPluginSandboxIntegration:
    """PluginSandbox 통합 테스트"""
    
    @pytest.mark.asyncio
    async def test_with_resource_context(self):
        """리소스 컨텍스트와 통합"""
        from programgarden.resource import ResourceContext
        
        ctx = await ResourceContext.create()
        
        async with ctx:
            sandbox = PluginSandbox(resource_context=ctx)
            
            async def resource_aware_plugin(**kwargs):
                return {"passed_symbols": ["AAPL"]}
            
            result = await sandbox.execute(
                plugin_id="ResourceAwarePlugin",
                plugin_callable=resource_aware_plugin,
                kwargs={},
            )
            
            assert result["passed_symbols"] == ["AAPL"]
    
    @pytest.mark.asyncio
    async def test_memory_tracking(self):
        """메모리 추적 (개발 모드)"""
        sandbox = PluginSandbox(track_memory=True)
        
        async def memory_plugin(**kwargs):
            # 약간의 메모리 사용
            data = [i for i in range(10000)]
            return {"passed_symbols": [], "data_size": len(data)}
        
        result = await sandbox.execute(
            plugin_id="MemoryPlugin",
            plugin_callable=memory_plugin,
            kwargs={},
        )
        
        assert result["data_size"] == 10000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
