"""
ProgramGarden - Adaptive Throttle

동적 속도 조절 시스템

리소스 사용량에 따라 5단계로 실행 속도를 조절합니다:
- NONE: 정상 속도
- LIGHT: 10% 감속
- MODERATE: 30% 감속
- HEAVY: 50% 감속  
- CRITICAL: 70% 감속 + 신규 작업 중단

자동매매 안정성을 위해 주문 실행은 CRITICAL에서도 허용됩니다.
"""

from typing import Optional, Callable, Awaitable, Dict, Any
from datetime import datetime
import asyncio
import logging

from programgarden_core.models.resource import (
    ResourceUsage,
    ResourceLimits,
    ThrottleLevel,
    ThrottleState,
)
from programgarden.resource.monitor import ResourceMonitor
from programgarden.resource.limiter import ResourceLimiter

logger = logging.getLogger("programgarden.resource.throttle")


# 스로틀 레벨별 설정
THROTTLE_CONFIG = {
    ThrottleLevel.NONE: {
        "delay_multiplier": 1.0,
        "concurrent_ratio": 1.0,     # max_workers의 100%
        "batch_size_ratio": 1.0,     # 기본 배치 크기의 100%
        "pause_new": False,
    },
    ThrottleLevel.LIGHT: {
        "delay_multiplier": 1.1,     # 10% 느리게
        "concurrent_ratio": 0.9,     # 90%
        "batch_size_ratio": 0.9,
        "pause_new": False,
    },
    ThrottleLevel.MODERATE: {
        "delay_multiplier": 1.3,     # 30% 느리게
        "concurrent_ratio": 0.7,     # 70%
        "batch_size_ratio": 0.7,
        "pause_new": False,
    },
    ThrottleLevel.HEAVY: {
        "delay_multiplier": 1.5,     # 50% 느리게
        "concurrent_ratio": 0.5,     # 50%
        "batch_size_ratio": 0.5,
        "pause_new": False,
    },
    ThrottleLevel.CRITICAL: {
        "delay_multiplier": 1.7,     # 70% 느리게
        "concurrent_ratio": 0.3,     # 30%
        "batch_size_ratio": 0.3,
        "pause_new": True,           # 신규 작업 중단
    },
}


# 스로틀 전략별 임계값 (limit 대비 사용률)
THROTTLE_STRATEGIES = {
    "gradual": {
        # 점진적 조절 (기본)
        ThrottleLevel.NONE: 0.0,
        ThrottleLevel.LIGHT: 0.60,
        ThrottleLevel.MODERATE: 0.75,
        ThrottleLevel.HEAVY: 0.90,
        ThrottleLevel.CRITICAL: 1.0,
    },
    "aggressive": {
        # 공격적 조절 (빠른 대응)
        ThrottleLevel.NONE: 0.0,
        ThrottleLevel.LIGHT: 0.50,
        ThrottleLevel.MODERATE: 0.65,
        ThrottleLevel.HEAVY: 0.80,
        ThrottleLevel.CRITICAL: 0.95,
    },
    "conservative": {
        # 보수적 조절 (여유 확보)
        ThrottleLevel.NONE: 0.0,
        ThrottleLevel.LIGHT: 0.70,
        ThrottleLevel.MODERATE: 0.80,
        ThrottleLevel.HEAVY: 0.90,
        ThrottleLevel.CRITICAL: 1.0,
    },
}


class AdaptiveThrottle:
    """
    적응형 속도 조절기
    
    리소스 사용량을 모니터링하여 자동으로 실행 속도를 조절합니다.
    세마포어 기반으로 동시 실행 작업 수를 제한합니다.
    
    Example:
        >>> throttle = AdaptiveThrottle(monitor, limiter)
        >>> await throttle.start()
        >>> 
        >>> # 작업 실행 전
        >>> if await throttle.acquire(task_weight=1.0):
        ...     try:
        ...         await do_work()
        ...     finally:
        ...         throttle.release(task_weight=1.0)
        >>> 
        >>> # 또는 대기 방식
        >>> await throttle.wait_until_available(task_weight=1.0)
        >>> 
        >>> await throttle.stop()
    
    Attributes:
        monitor: 리소스 모니터
        limiter: 리소스 제한자
        strategy: 스로틀링 전략
    """
    
    def __init__(
        self,
        monitor: ResourceMonitor,
        limiter: ResourceLimiter,
        strategy: str = "gradual",
        adjust_interval_sec: float = 2.0,
    ):
        """
        Args:
            monitor: ResourceMonitor 인스턴스
            limiter: ResourceLimiter 인스턴스
            strategy: 스로틀링 전략 ("gradual", "aggressive", "conservative")
            adjust_interval_sec: 레벨 조정 주기 (초)
        """
        self._monitor = monitor
        self._limiter = limiter
        self._strategy = strategy
        self._adjust_interval = adjust_interval_sec
        
        # 현재 상태
        self._state = ThrottleState(
            level=ThrottleLevel.NONE,
            max_concurrent_tasks=limiter.limits.max_workers,
            recommended_batch_size=10,
        )
        
        # 세마포어 (동시 작업 제한)
        self._semaphore = asyncio.Semaphore(limiter.limits.max_workers)
        self._current_weight = 0.0
        self._weight_lock = asyncio.Lock()
        
        # 조정 태스크
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        # 콜백
        self._on_level_change: Optional[Callable[[ThrottleState], Awaitable[None]]] = None
        self._on_critical: Optional[Callable[[ResourceUsage], Awaitable[None]]] = None
        
        # 임계값
        self._thresholds = THROTTLE_STRATEGIES.get(strategy, THROTTLE_STRATEGIES["gradual"])
    
    async def start(self) -> None:
        """적응형 조절 시작"""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._adjust_loop())
        logger.info(f"AdaptiveThrottle started (strategy={self._strategy})")
    
    async def stop(self) -> None:
        """조절 중지"""
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        
        logger.info("AdaptiveThrottle stopped")
    
    async def _adjust_loop(self) -> None:
        """주기적 스로틀 레벨 조정"""
        while self._running:
            try:
                await asyncio.sleep(self._adjust_interval)
                
                if not self._running:
                    break
                
                # 평균 사용량 기준으로 레벨 결정
                usage = self._monitor.get_average_usage(seconds=5)
                new_level = self._calculate_level(usage)
                
                if new_level != self._state.level:
                    await self._change_level(new_level, usage)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Throttle adjust error: {e}")
    
    def _calculate_level(self, usage: ResourceUsage) -> ThrottleLevel:
        """
        리소스 사용량 기반 스로틀 레벨 결정
        
        CPU와 메모리 중 더 높은 사용률 기준
        """
        _, max_ratio = self._limiter.get_max_utilization(usage)
        
        # 임계값 역순으로 체크 (CRITICAL부터)
        for level in [
            ThrottleLevel.CRITICAL,
            ThrottleLevel.HEAVY,
            ThrottleLevel.MODERATE,
            ThrottleLevel.LIGHT,
        ]:
            if max_ratio >= self._thresholds[level]:
                return level
        
        return ThrottleLevel.NONE
    
    async def _change_level(self, new_level: ThrottleLevel, usage: ResourceUsage) -> None:
        """스로틀 레벨 변경"""
        old_level = self._state.level
        config = THROTTLE_CONFIG[new_level]
        limits = self._limiter.limits
        
        # 새 상태 계산
        max_concurrent = max(1, int(limits.max_workers * config["concurrent_ratio"]))
        batch_size = max(1, int(10 * config["batch_size_ratio"]))  # 기본 10
        
        self._state = ThrottleState(
            level=new_level,
            delay_multiplier=config["delay_multiplier"],
            max_concurrent_tasks=max_concurrent,
            recommended_batch_size=batch_size,
            paused_new_tasks=config["pause_new"],
            reason=f"Resource ratio: {self._limiter.get_max_utilization(usage)[1]:.1%}",
            since=datetime.utcnow(),
        )
        
        logger.info(f"Throttle level changed: {old_level.value} -> {new_level.value}")
        
        # 콜백 호출
        if self._on_level_change:
            try:
                await self._on_level_change(self._state)
            except Exception as e:
                logger.error(f"Level change callback error: {e}")
        
        # CRITICAL 콜백
        if new_level == ThrottleLevel.CRITICAL and self._on_critical:
            try:
                await self._on_critical(usage)
            except Exception as e:
                logger.error(f"Critical callback error: {e}")
    
    def get_state(self) -> ThrottleState:
        """현재 스로틀링 상태"""
        return self._state
    
    async def acquire(
        self, 
        task_weight: float = 1.0,
        priority: int = 5,
        is_order: bool = False,
    ) -> bool:
        """
        작업 실행 권한 획득 (non-blocking)
        
        Args:
            task_weight: 작업 가중치 (1.0=일반, 2.0=무거움)
            priority: 우선순위 (1-10, 높을수록 우선)
            is_order: 주문 관련 작업 여부 (True면 CRITICAL에서도 허용)
        
        Returns:
            True: 즉시 실행 가능
            False: 실행 불가 (세마포어 부족 또는 CRITICAL)
        """
        # CRITICAL 상태에서 주문은 허용
        if self._state.paused_new_tasks and not is_order:
            if priority < 10:  # 최고 우선순위가 아니면 거부
                return False
        
        # 세마포어 시도
        # asyncio.Semaphore는 _value 속성으로 남은 슬롯 확인 가능
        # non-blocking으로 시도하기 위해 wait_for + timeout 사용
        try:
            await asyncio.wait_for(self._semaphore.acquire(), timeout=0.001)
            acquired = True
        except asyncio.TimeoutError:
            acquired = False
        
        if acquired:
            async with self._weight_lock:
                self._current_weight += task_weight
            self._monitor.increment_workers()
        
        return acquired
    
    def release(self, task_weight: float = 1.0) -> None:
        """작업 완료 후 권한 반환"""
        self._semaphore.release()
        
        # weight 감소 (비동기 불필요)
        asyncio.create_task(self._decrease_weight(task_weight))
        self._monitor.decrement_workers()
    
    async def _decrease_weight(self, weight: float) -> None:
        """가중치 감소 (async)"""
        async with self._weight_lock:
            self._current_weight = max(0, self._current_weight - weight)
    
    async def wait_until_available(
        self,
        task_weight: float = 1.0,
        timeout: Optional[float] = None,
        priority: int = 5,
        is_order: bool = False,
    ) -> bool:
        """
        실행 가능할 때까지 대기
        
        Args:
            task_weight: 작업 가중치
            timeout: 최대 대기 시간 (초, None=무제한)
            priority: 우선순위
            is_order: 주문 관련 작업 여부
        
        Returns:
            True: 실행 가능
            False: 타임아웃 또는 CRITICAL로 인한 중단
        """
        start = asyncio.get_event_loop().time()
        
        while True:
            # CRITICAL 체크 (주문 제외)
            if self._state.paused_new_tasks and not is_order and priority < 10:
                # 잠시 대기 후 재확인
                await asyncio.sleep(0.5)
                
                if timeout:
                    elapsed = asyncio.get_event_loop().time() - start
                    if elapsed >= timeout:
                        return False
                continue
            
            # 세마포어 획득 시도
            try:
                if timeout:
                    remaining = timeout - (asyncio.get_event_loop().time() - start)
                    if remaining <= 0:
                        return False
                    await asyncio.wait_for(self._semaphore.acquire(), timeout=remaining)
                else:
                    await self._semaphore.acquire()
                
                async with self._weight_lock:
                    self._current_weight += task_weight
                self._monitor.increment_workers()
                return True
                
            except asyncio.TimeoutError:
                return False
    
    def get_recommended_delay(self) -> float:
        """
        현재 상태에서 권장 지연 시간 (초)
        
        Returns:
            권장 지연 시간 (0.0 ~ 2.0)
        """
        base_delay = 0.1  # 기본 100ms
        return base_delay * (self._state.delay_multiplier - 1.0)
    
    def get_recommended_batch_size(self, default: int = 10) -> int:
        """
        현재 상태에서 권장 배치 크기
        
        Args:
            default: 기본 배치 크기
        
        Returns:
            권장 배치 크기
        """
        config = THROTTLE_CONFIG[self._state.level]
        return max(1, int(default * config["batch_size_ratio"]))
    
    def get_effective_workers(self) -> int:
        """현재 허용되는 동시 워커 수"""
        return self._state.max_concurrent_tasks
    
    async def force_level(self, level: ThrottleLevel, reason: str = "Manual override") -> None:
        """
        스로틀 레벨 강제 설정 (테스트/디버깅용)
        
        Args:
            level: 설정할 레벨
            reason: 이유
        """
        usage = self._monitor.get_usage()
        config = THROTTLE_CONFIG[level]
        limits = self._limiter.limits
        
        self._state = ThrottleState(
            level=level,
            delay_multiplier=config["delay_multiplier"],
            max_concurrent_tasks=max(1, int(limits.max_workers * config["concurrent_ratio"])),
            recommended_batch_size=max(1, int(10 * config["batch_size_ratio"])),
            paused_new_tasks=config["pause_new"],
            reason=reason,
            since=datetime.utcnow(),
        )
        
        logger.warning(f"Throttle level forced to {level.value}: {reason}")
    
    # === 콜백 등록 ===
    
    def on_level_change(
        self, 
        callback: Callable[[ThrottleState], Awaitable[None]]
    ) -> None:
        """스로틀링 레벨 변경 시 콜백"""
        self._on_level_change = callback
    
    def on_critical(
        self, 
        callback: Callable[[ResourceUsage], Awaitable[None]]
    ) -> None:
        """CRITICAL 상태 진입 시 콜백"""
        self._on_critical = callback
    
    # === 상태 조회 ===
    
    @property
    def is_running(self) -> bool:
        """조절 실행 중 여부"""
        return self._running
    
    @property
    def current_level(self) -> ThrottleLevel:
        """현재 스로틀 레벨"""
        return self._state.level
    
    @property
    def is_paused(self) -> bool:
        """신규 작업 중단 여부"""
        return self._state.paused_new_tasks
