"""
ProgramGarden - Resource Context

리소스 관리 통합 컨텍스트

Monitor, Limiter, Throttle을 통합하여 단일 인터페이스로 제공합니다.
ExecutionContext에 주입되어 노드별로 리소스 상태 확인 및 조절이 가능합니다.
"""

from typing import Optional, Dict, Any, Callable, Awaitable
from datetime import datetime
import asyncio
import logging

from programgarden_core.models.resource import (
    ResourceUsage,
    ResourceLimits,
    ThrottleLevel,
    ThrottleState,
    ResourceHints,
    get_node_hints,
)
from programgarden.resource.monitor import ResourceMonitor
from programgarden.resource.limiter import ResourceLimiter
from programgarden.resource.throttle import AdaptiveThrottle

logger = logging.getLogger("programgarden.resource.context")


class ResourceContext:
    """
    리소스 관리 통합 컨텍스트
    
    Monitor, Limiter, Throttle을 통합하여 노드 실행 시
    리소스 상태 확인 및 조절을 단일 인터페이스로 제공합니다.
    
    Example:
        >>> # 자동 생성 (권장)
        >>> async with await ResourceContext.create() as ctx:
        ...     usage = ctx.get_usage()
        ...     
        ...     # 작업 전 체크
        ...     check = await ctx.before_task("condition", weight=1.0)
        ...     if check["can_proceed"]:
        ...         await do_work()
        ...     await ctx.after_task("condition", weight=1.0)
        >>> 
        >>> # 명시적 제한
        >>> limits = ResourceLimits(max_cpu_percent=70)
        >>> async with await ResourceContext.create(limits=limits) as ctx:
        ...     state = ctx.get_throttle_state()
    
    Attributes:
        monitor: ResourceMonitor 인스턴스
        limiter: ResourceLimiter 인스턴스
        throttle: AdaptiveThrottle 인스턴스
    """
    
    def __init__(
        self,
        monitor: ResourceMonitor,
        limiter: ResourceLimiter,
        throttle: AdaptiveThrottle,
    ):
        """
        직접 생성보다 create() 팩토리 메서드 사용을 권장합니다.
        """
        self._monitor = monitor
        self._limiter = limiter
        self._throttle = throttle
        self._started = False
    
    @classmethod
    async def create(
        cls,
        limits: Optional[ResourceLimits] = None,
        auto_detect: bool = True,
        poll_interval_sec: float = 1.0,
        throttle_strategy: str = "gradual",
    ) -> "ResourceContext":
        """
        ResourceContext 팩토리 메서드
        
        Args:
            limits: 리소스 제한 (None이면 auto_detect에 따라 결정)
            auto_detect: limits가 None일 때 자동 감지 여부
            poll_interval_sec: 모니터링 주기 (초)
            throttle_strategy: 스로틀링 전략 ("gradual", "aggressive", "conservative")
        
        Returns:
            초기화된 ResourceContext
        
        Example:
            >>> # 자동 감지 (기본)
            >>> ctx = await ResourceContext.create()
            >>> 
            >>> # 명시적 제한
            >>> limits = ResourceLimits(max_cpu_percent=70, max_memory_percent=75)
            >>> ctx = await ResourceContext.create(limits=limits)
            >>> 
            >>> # JSON에서 로드
            >>> config = {"max_cpu_percent": 70, "throttle_strategy": "conservative"}
            >>> limits = ResourceLimits(**config)
            >>> ctx = await ResourceContext.create(limits=limits, throttle_strategy="conservative")
        """
        # Limiter 생성
        if limits:
            limiter = ResourceLimiter(limits)
            strategy = limits.throttle_strategy
        elif auto_detect:
            limiter = ResourceLimiter.from_auto_detect()
            strategy = throttle_strategy
        else:
            limiter = ResourceLimiter(ResourceLimits())
            strategy = throttle_strategy
        
        # Monitor 생성
        monitor = ResourceMonitor(poll_interval_sec=poll_interval_sec)
        
        # Throttle 생성
        throttle = AdaptiveThrottle(
            monitor=monitor,
            limiter=limiter,
            strategy=strategy,
        )
        
        ctx = cls(monitor, limiter, throttle)
        return ctx
    
    async def start(self) -> None:
        """리소스 관리 시작"""
        if self._started:
            return
        
        await self._monitor.start()
        await self._throttle.start()
        self._started = True
        logger.info("ResourceContext started")
    
    async def stop(self) -> None:
        """리소스 관리 중지"""
        if not self._started:
            return
        
        await self._throttle.stop()
        await self._monitor.stop()
        self._started = False
        logger.info("ResourceContext stopped")
    
    async def __aenter__(self) -> "ResourceContext":
        """async with 지원"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """async with 종료"""
        await self.stop()
    
    # === 상태 조회 ===
    
    def get_usage(self) -> ResourceUsage:
        """현재 리소스 사용량"""
        return self._monitor.get_usage()
    
    async def get_usage_async(self) -> ResourceUsage:
        """현재 리소스 사용량 (즉시 측정)"""
        return await self._monitor.get_usage_async()
    
    def get_limits(self) -> ResourceLimits:
        """설정된 제한"""
        return self._limiter.limits
    
    def get_throttle_state(self) -> ThrottleState:
        """현재 스로틀링 상태"""
        return self._throttle.get_state()
    
    def is_healthy(self) -> bool:
        """
        시스템 건강 상태
        
        Returns:
            True: 제한 미초과
            False: 제한 초과
        """
        usage = self._monitor.get_usage()
        return self._limiter.is_within_limits(usage)
    
    def get_health_summary(self) -> Dict[str, Any]:
        """
        건강 상태 요약
        
        Returns:
            {
                "healthy": bool,
                "usage": {...},
                "throttle": {...},
                "violation": str or None,
            }
        """
        usage = self._monitor.get_usage()
        throttle = self._throttle.get_state()
        
        return {
            "healthy": self._limiter.is_within_limits(usage),
            "usage": usage.to_summary(),
            "throttle": throttle.to_summary(),
            "violation": self._limiter.get_violation(usage),
        }
    
    # === 작업 제어 ===
    
    async def before_task(
        self,
        task_type: str,
        weight: float = 1.0,
        is_order: bool = False,
        priority: int = 5,
        timeout: Optional[float] = 30.0,
    ) -> Dict[str, Any]:
        """
        작업 시작 전 호출
        
        리소스 상태를 확인하고 실행 권한을 획득합니다.
        필요 시 대기하거나 권장 설정을 반환합니다.
        
        Args:
            task_type: 작업 유형 (노드 타입)
            weight: 작업 가중치
            is_order: 주문 관련 작업 여부 (True면 우선 처리)
            priority: 우선순위 (1-10)
            timeout: 최대 대기 시간 (초)
        
        Returns:
            {
                "can_proceed": bool,        # 실행 가능 여부
                "waited": float,            # 대기한 시간 (초)
                "recommended_delay": float, # 권장 추가 지연 (초)
                "recommended_batch_size": int,
                "throttle_level": str,
                "reason": str or None,      # 거부 사유
            }
        """
        start_time = asyncio.get_event_loop().time()
        
        # 노드 타입별 힌트 적용
        hints = get_node_hints(task_type)
        effective_weight = weight * hints.weight
        effective_priority = priority if priority != 5 else hints.priority
        
        # 주문 노드는 자동으로 최고 우선순위
        ORDER_NODE_TYPES = {
            "StockNewOrderNode", "StockModifyOrderNode", "StockCancelOrderNode",
            "FuturesNewOrderNode", "FuturesModifyOrderNode", "FuturesCancelOrderNode",
        }
        if task_type in ORDER_NODE_TYPES:
            is_order = True
            effective_priority = 10
        
        # 실행 권한 획득 시도
        acquired = await self._throttle.wait_until_available(
            task_weight=effective_weight,
            timeout=timeout,
            priority=effective_priority,
            is_order=is_order,
        )
        
        waited = asyncio.get_event_loop().time() - start_time
        state = self._throttle.get_state()
        
        if acquired:
            return {
                "can_proceed": True,
                "waited": waited,
                "recommended_delay": self._throttle.get_recommended_delay(),
                "recommended_batch_size": self._throttle.get_recommended_batch_size(),
                "throttle_level": state.level.value,
                "reason": None,
            }
        else:
            return {
                "can_proceed": False,
                "waited": waited,
                "recommended_delay": 0,
                "recommended_batch_size": 1,
                "throttle_level": state.level.value,
                "reason": state.reason or "Resource limit or timeout",
            }
    
    async def after_task(
        self,
        task_type: str,
        weight: float = 1.0,
    ) -> None:
        """
        작업 완료 후 호출
        
        실행 권한을 반환합니다.
        
        Args:
            task_type: 작업 유형
            weight: 작업 가중치 (before_task와 동일해야 함)
        """
        hints = get_node_hints(task_type)
        effective_weight = weight * hints.weight
        self._throttle.release(task_weight=effective_weight)
    
    async def check_can_proceed(
        self,
        task_type: str = "default",
        weight: float = 1.0,
    ) -> bool:
        """
        실행 가능 여부만 빠르게 확인 (권한 획득 안 함)
        
        Args:
            task_type: 작업 유형
            weight: 작업 가중치
        
        Returns:
            True: 실행 가능 예상
            False: 대기 필요
        """
        state = self._throttle.get_state()
        
        # CRITICAL이고 일반 작업이면 불가
        if state.paused_new_tasks:
            hints = get_node_hints(task_type)
            if hints.priority < 10:
                return False
        
        # 리소스 여유 확인
        usage = self._monitor.get_usage()
        headroom = self._limiter.get_headroom(usage)
        
        # CPU나 메모리 여유가 10% 미만이면 경고
        if headroom["cpu"] < 10 or headroom["memory"] < 10:
            return False
        
        return True
    
    # === 표현식 컨텍스트 ===
    
    def get_expression_context(self) -> Dict[str, Any]:
        """
        Expression에서 사용할 리소스 변수 반환
        
        JSON DSL에서 {{ resource.xxx }} 형태로 접근 가능합니다.
        
        Example (JSON DSL):
            {
                "config": {
                    "batch_size": "{{ resource.recommended_batch_size }}",
                    "symbols": "{{ input.symbols[:resource.max_symbols] }}"
                }
            }
        
        Returns:
            {
                "recommended_batch_size": int,
                "max_symbols": int,
                "max_backtest_days": int,
                "throttle_level": str,
                "cpu_percent": float,
                "memory_percent": float,
            }
        """
        state = self._throttle.get_state()
        usage = self._monitor.get_usage()
        limits = self._limiter.limits
        
        return {
            "recommended_batch_size": state.recommended_batch_size,
            "max_symbols": limits.max_symbols_per_condition,
            "max_backtest_days": limits.max_backtest_days,
            "max_workers": state.max_concurrent_tasks,
            "throttle_level": state.level.value,
            "cpu_percent": usage.cpu_percent,
            "memory_percent": usage.memory_percent,
            "is_healthy": self.is_healthy(),
        }
    
    # === 콜백 등록 ===
    
    def on_throttle_change(
        self,
        callback: Callable[[ThrottleState], Awaitable[None]]
    ) -> None:
        """스로틀링 상태 변경 시 콜백"""
        self._throttle.on_level_change(callback)
    
    def on_critical(
        self,
        callback: Callable[[ResourceUsage], Awaitable[None]]
    ) -> None:
        """CRITICAL 상태 진입 시 콜백"""
        self._throttle.on_critical(callback)
    
    # === 속성 접근 ===
    
    @property
    def monitor(self) -> ResourceMonitor:
        """ResourceMonitor 직접 접근"""
        return self._monitor
    
    @property
    def limiter(self) -> ResourceLimiter:
        """ResourceLimiter 직접 접근"""
        return self._limiter
    
    @property
    def throttle(self) -> AdaptiveThrottle:
        """AdaptiveThrottle 직접 접근"""
        return self._throttle
    
    @property
    def is_started(self) -> bool:
        """시작 여부"""
        return self._started
