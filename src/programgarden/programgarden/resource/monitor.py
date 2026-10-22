"""
ProgramGarden - Resource Monitor

실시간 시스템 리소스(CPU/RAM/디스크) 모니터링

로컬 컴퓨터와 K8s 컨테이너 환경 모두에서 동작합니다.
"""

from typing import Optional, List, Deque
from collections import deque
from datetime import datetime, timedelta
import asyncio
import logging

from programgarden_core.models.resource import ResourceUsage

logger = logging.getLogger("programgarden.resource.monitor")


class ResourceMonitor:
    """
    실시간 시스템 리소스 모니터링
    
    백그라운드에서 주기적으로 CPU, RAM, 디스크 사용량을 측정하고
    히스토리를 유지합니다.
    
    Example:
        >>> monitor = ResourceMonitor(poll_interval_sec=1.0)
        >>> await monitor.start()
        >>> 
        >>> usage = monitor.get_usage()
        >>> print(f"CPU: {usage.cpu_percent}%, Memory: {usage.memory_percent}%")
        >>> 
        >>> # 최근 10초 평균
        >>> avg = monitor.get_average_usage(seconds=10)
        >>> 
        >>> await monitor.stop()
    
    Attributes:
        poll_interval_sec: 측정 주기 (초)
        history_size: 히스토리 보관 개수
    """
    
    def __init__(
        self, 
        poll_interval_sec: float = 1.0,
        history_size: int = 300,  # 기본 5분 (1초 간격)
    ):
        """
        Args:
            poll_interval_sec: 측정 주기 (초, 기본 1.0)
            history_size: 히스토리 보관 개수 (기본 300)
        """
        self._poll_interval = poll_interval_sec
        self._history_size = history_size
        
        # 상태
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        # 측정값 저장
        self._current: Optional[ResourceUsage] = None
        self._history: Deque[ResourceUsage] = deque(maxlen=history_size)
        
        # 워커 카운터 (외부에서 관리)
        self._active_workers = 0
        self._pending_tasks = 0
        
        # psutil 사용 가능 여부
        self._psutil_available = self._check_psutil()
    
    def _check_psutil(self) -> bool:
        """psutil 사용 가능 여부 확인"""
        try:
            import psutil
            return True
        except ImportError:
            logger.warning("psutil not available, using fallback monitoring")
            return False
    
    async def start(self) -> None:
        """백그라운드 모니터링 시작"""
        if self._running:
            return
        
        self._running = True
        
        # 초기 측정
        self._current = await self._measure()
        self._history.append(self._current)
        
        # 백그라운드 태스크 시작
        self._task = asyncio.create_task(self._poll_loop())
        logger.info(f"ResourceMonitor started (interval={self._poll_interval}s)")
    
    async def stop(self) -> None:
        """모니터링 중지"""
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        
        logger.info("ResourceMonitor stopped")
    
    async def _poll_loop(self) -> None:
        """주기적 측정 루프"""
        while self._running:
            try:
                await asyncio.sleep(self._poll_interval)
                
                if not self._running:
                    break
                
                usage = await self._measure()
                self._current = usage
                self._history.append(usage)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                await asyncio.sleep(self._poll_interval)
    
    async def _measure(self) -> ResourceUsage:
        """
        현재 리소스 사용량 측정
        
        psutil이 있으면 실제 측정, 없으면 fallback 값 반환
        """
        if self._psutil_available:
            return await self._measure_with_psutil()
        else:
            return self._measure_fallback()
    
    async def _measure_with_psutil(self) -> ResourceUsage:
        """psutil을 사용한 실제 측정"""
        import psutil
        
        # CPU (non-blocking)
        # cpu_percent(interval=None)은 이전 호출 대비 값 반환
        cpu_percent = psutil.cpu_percent(interval=None)
        
        # 첫 호출 시 0.0 반환될 수 있으므로 짧은 측정
        if cpu_percent == 0.0 and len(self._history) == 0:
            cpu_percent = await asyncio.to_thread(
                psutil.cpu_percent, interval=0.1
            )
        
        # Memory
        mem = psutil.virtual_memory()
        memory_percent = mem.percent
        memory_used_mb = mem.used / (1024 * 1024)
        memory_available_mb = mem.available / (1024 * 1024)
        
        # Disk (루트 파티션 또는 현재 작업 디렉토리)
        try:
            disk = psutil.disk_usage("/")
            disk_percent = disk.percent
            disk_used_gb = disk.used / (1024 * 1024 * 1024)
            disk_available_gb = disk.free / (1024 * 1024 * 1024)
        except Exception:
            disk_percent = 0.0
            disk_used_gb = 0.0
            disk_available_gb = 0.0
        
        return ResourceUsage(
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_used_mb=memory_used_mb,
            memory_available_mb=memory_available_mb,
            disk_percent=disk_percent,
            disk_used_gb=disk_used_gb,
            disk_available_gb=disk_available_gb,
            active_workers=self._active_workers,
            pending_tasks=self._pending_tasks,
            timestamp=datetime.utcnow(),
        )
    
    def _measure_fallback(self) -> ResourceUsage:
        """psutil 없을 때 fallback 측정 (보수적 추정)"""
        # 정확한 측정 불가, 안전한 기본값 반환
        return ResourceUsage(
            cpu_percent=50.0,  # 알 수 없으므로 중간값
            memory_percent=50.0,
            memory_used_mb=0.0,
            memory_available_mb=0.0,
            disk_percent=0.0,
            disk_used_gb=0.0,
            disk_available_gb=0.0,
            active_workers=self._active_workers,
            pending_tasks=self._pending_tasks,
            timestamp=datetime.utcnow(),
        )
    
    def get_usage(self) -> ResourceUsage:
        """
        현재 리소스 사용량 반환 (캐시된 값)
        
        Returns:
            마지막 측정된 ResourceUsage
        """
        if self._current is None:
            # 아직 측정 안됨, 즉시 측정 (동기)
            if self._psutil_available:
                import psutil
                mem = psutil.virtual_memory()
                return ResourceUsage(
                    cpu_percent=psutil.cpu_percent(interval=0.1),
                    memory_percent=mem.percent,
                    memory_used_mb=mem.used / (1024 * 1024),
                    memory_available_mb=mem.available / (1024 * 1024),
                    active_workers=self._active_workers,
                    pending_tasks=self._pending_tasks,
                )
            else:
                return self._measure_fallback()
        
        return self._current
    
    async def get_usage_async(self) -> ResourceUsage:
        """
        현재 리소스 사용량 즉시 측정 (비동기)
        
        캐시를 무시하고 새로 측정합니다.
        
        Returns:
            새로 측정된 ResourceUsage
        """
        return await self._measure()
    
    def get_usage_history(self, seconds: int = 60) -> List[ResourceUsage]:
        """
        최근 N초간 사용량 히스토리
        
        Args:
            seconds: 조회할 기간 (초)
        
        Returns:
            해당 기간의 ResourceUsage 리스트 (오래된 순)
        """
        if not self._history:
            return []
        
        cutoff = datetime.utcnow() - timedelta(seconds=seconds)
        return [u for u in self._history if u.timestamp >= cutoff]
    
    def get_average_usage(self, seconds: int = 10) -> ResourceUsage:
        """
        최근 N초간 평균 사용량
        
        Args:
            seconds: 평균 계산 기간 (초)
        
        Returns:
            평균 ResourceUsage
        """
        history = self.get_usage_history(seconds)
        
        if not history:
            return self.get_usage()
        
        count = len(history)
        
        return ResourceUsage(
            cpu_percent=sum(u.cpu_percent for u in history) / count,
            memory_percent=sum(u.memory_percent for u in history) / count,
            memory_used_mb=sum(u.memory_used_mb for u in history) / count,
            memory_available_mb=sum(u.memory_available_mb for u in history) / count,
            disk_percent=sum(u.disk_percent for u in history) / count,
            disk_used_gb=sum(u.disk_used_gb for u in history) / count,
            disk_available_gb=sum(u.disk_available_gb for u in history) / count,
            active_workers=self._active_workers,
            pending_tasks=self._pending_tasks,
            timestamp=datetime.utcnow(),
        )
    
    def get_peak_usage(self, seconds: int = 60) -> ResourceUsage:
        """
        최근 N초간 최대 사용량
        
        Args:
            seconds: 조회 기간 (초)
        
        Returns:
            최대값 기준 ResourceUsage
        """
        history = self.get_usage_history(seconds)
        
        if not history:
            return self.get_usage()
        
        return ResourceUsage(
            cpu_percent=max(u.cpu_percent for u in history),
            memory_percent=max(u.memory_percent for u in history),
            memory_used_mb=max(u.memory_used_mb for u in history),
            memory_available_mb=min(u.memory_available_mb for u in history),
            disk_percent=max(u.disk_percent for u in history),
            disk_used_gb=max(u.disk_used_gb for u in history),
            disk_available_gb=min(u.disk_available_gb for u in history),
            active_workers=self._active_workers,
            pending_tasks=self._pending_tasks,
            timestamp=datetime.utcnow(),
        )
    
    # === 워커 카운터 관리 ===
    
    def increment_workers(self, count: int = 1) -> None:
        """활성 워커 수 증가"""
        self._active_workers += count
    
    def decrement_workers(self, count: int = 1) -> None:
        """활성 워커 수 감소"""
        self._active_workers = max(0, self._active_workers - count)
    
    def increment_pending(self, count: int = 1) -> None:
        """대기 태스크 수 증가"""
        self._pending_tasks += count
    
    def decrement_pending(self, count: int = 1) -> None:
        """대기 태스크 수 감소"""
        self._pending_tasks = max(0, self._pending_tasks - count)
    
    def set_worker_counts(self, active: int, pending: int) -> None:
        """워커 카운트 직접 설정"""
        self._active_workers = max(0, active)
        self._pending_tasks = max(0, pending)
    
    # === 상태 조회 ===
    
    @property
    def is_running(self) -> bool:
        """모니터링 실행 중 여부"""
        return self._running
    
    @property
    def history_count(self) -> int:
        """저장된 히스토리 개수"""
        return len(self._history)
