"""
ProgramGarden - Plugin Sandbox

플러그인 실행 샌드박스
- 타임아웃 기반 실행 시간 제한
- 메모리 사용량 추적 (개발 모드)
- 대량 종목 자동 배치 분할
"""

import asyncio
import logging
from typing import Any, Callable, Optional, List, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from programgarden.resource import ResourceContext

logger = logging.getLogger(__name__)


class PluginError(Exception):
    """플러그인 실행 오류 기본 클래스"""
    pass


class PluginTimeoutError(PluginError):
    """플러그인 실행 시간 초과"""
    
    def __init__(self, plugin_id: str, timeout: float):
        self.plugin_id = plugin_id
        self.timeout = timeout
        super().__init__(f"Plugin '{plugin_id}' exceeded {timeout}s timeout")


class PluginResourceError(PluginError):
    """플러그인 리소스 제한 초과"""
    
    def __init__(self, plugin_id: str, reason: str):
        self.plugin_id = plugin_id
        self.reason = reason
        super().__init__(f"Plugin '{plugin_id}' resource limit: {reason}")


class PluginSandbox:
    """
    플러그인 실행 샌드박스
    
    커뮤니티 플러그인을 안전하게 실행하기 위한 래퍼.
    타임아웃, 메모리 추적, 배치 분할을 제공합니다.
    
    Example:
        ```python
        sandbox = PluginSandbox(resource_context=ctx)
        
        result = await sandbox.execute(
            plugin_id="RSI",
            plugin_callable=rsi_condition,
            args=(symbols, price_data),
            kwargs={"fields": {"period": 14}},
            timeout=30.0,
        )
        ```
    """
    
    def __init__(
        self,
        resource_context: Optional["ResourceContext"] = None,
        default_timeout: float = 30.0,
        default_batch_size: int = 100,
        track_memory: bool = False,
    ):
        """
        Args:
            resource_context: 리소스 컨텍스트 (워크플로우 레벨 제한)
            default_timeout: 기본 타임아웃 (초)
            default_batch_size: 기본 배치 크기
            track_memory: 메모리 추적 여부 (개발 모드)
        """
        self._resource_context = resource_context
        self._default_timeout = default_timeout
        self._default_batch_size = default_batch_size
        self._track_memory = track_memory
        
        # 실행 통계
        self._stats = {
            "total_executions": 0,
            "timeouts": 0,
            "errors": 0,
            "total_time_sec": 0.0,
        }
    
    async def execute(
        self,
        plugin_id: str,
        plugin_callable: Callable,
        args: tuple = (),
        kwargs: Optional[dict] = None,
        timeout: Optional[float] = None,
        weight: float = 1.0,
    ) -> Any:
        """
        샌드박스 내에서 플러그인 실행
        
        Args:
            plugin_id: 플러그인 ID (로깅용)
            plugin_callable: 플러그인 함수
            args: 위치 인자
            kwargs: 키워드 인자
            timeout: 타임아웃 (초), None이면 기본값 사용
            weight: 리소스 체크 가중치
        
        Returns:
            플러그인 실행 결과
        
        Raises:
            PluginTimeoutError: 실행 시간 초과
            PluginResourceError: 리소스 제한 초과
        """
        kwargs = kwargs or {}
        timeout = timeout or self._default_timeout
        
        start_time = datetime.now()
        self._stats["total_executions"] += 1
        
        # 워크플로우 레벨 리소스 체크
        if self._resource_context:
            check = await self._resource_context.before_task(
                task_type=f"Plugin:{plugin_id}",
                weight=weight,
            )
            if not check["can_proceed"]:
                self._stats["errors"] += 1
                raise PluginResourceError(
                    plugin_id=plugin_id,
                    reason=check.get("reason", "Resource limit exceeded"),
                )
        
        try:
            # 타임아웃 적용 실행
            if self._track_memory:
                result = await self._execute_with_memory_tracking(
                    plugin_callable, args, kwargs, timeout, plugin_id
                )
            else:
                result = await asyncio.wait_for(
                    self._call_plugin(plugin_callable, args, kwargs),
                    timeout=timeout,
                )
            
            # 실행 시간 기록
            elapsed = (datetime.now() - start_time).total_seconds()
            self._stats["total_time_sec"] += elapsed
            
            logger.debug(f"Plugin '{plugin_id}' completed in {elapsed:.2f}s")
            return result
            
        except asyncio.TimeoutError:
            self._stats["timeouts"] += 1
            logger.warning(f"Plugin '{plugin_id}' timed out after {timeout}s")
            raise PluginTimeoutError(plugin_id=plugin_id, timeout=timeout)
            
        except Exception as e:
            self._stats["errors"] += 1
            logger.error(f"Plugin '{plugin_id}' error: {e}")
            raise
            
        finally:
            # 리소스 해제
            if self._resource_context:
                await self._resource_context.after_task(
                    task_type=f"Plugin:{plugin_id}",
                    weight=weight,
                )
    
    async def _call_plugin(
        self,
        plugin_callable: Callable,
        args: tuple,
        kwargs: dict,
    ) -> Any:
        """플러그인 호출 (async/sync 모두 지원)"""
        if asyncio.iscoroutinefunction(plugin_callable):
            return await plugin_callable(*args, **kwargs)
        else:
            # 동기 함수는 executor에서 실행
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                lambda: plugin_callable(*args, **kwargs),
            )
    
    async def _execute_with_memory_tracking(
        self,
        plugin_callable: Callable,
        args: tuple,
        kwargs: dict,
        timeout: float,
        plugin_id: str,
    ) -> Any:
        """메모리 사용량 추적하며 실행 (개발 모드)"""
        try:
            import tracemalloc
            tracemalloc.start()
            start_memory = tracemalloc.get_traced_memory()[0]
        except ImportError:
            logger.warning("tracemalloc not available")
            return await asyncio.wait_for(
                self._call_plugin(plugin_callable, args, kwargs),
                timeout=timeout,
            )
        
        try:
            result = await asyncio.wait_for(
                self._call_plugin(plugin_callable, args, kwargs),
                timeout=timeout,
            )
            
            current, peak = tracemalloc.get_traced_memory()
            memory_used_mb = (peak - start_memory) / (1024 * 1024)
            
            if memory_used_mb > 50:  # 50MB 이상이면 경고
                logger.warning(
                    f"Plugin '{plugin_id}' used {memory_used_mb:.1f}MB memory"
                )
            else:
                logger.debug(
                    f"Plugin '{plugin_id}' memory: {memory_used_mb:.1f}MB"
                )
            
            return result
            
        finally:
            tracemalloc.stop()
    
    async def execute_batched(
        self,
        plugin_id: str,
        plugin_callable: Callable,
        symbols: List[str],
        batch_size: Optional[int] = None,
        timeout_per_batch: Optional[float] = None,
        **kwargs,
    ) -> dict:
        """
        대량 종목을 배치로 분할하여 실행
        
        Args:
            plugin_id: 플러그인 ID
            plugin_callable: 플러그인 함수
            symbols: 전체 종목 리스트
            batch_size: 배치 크기 (None이면 자동 결정)
            timeout_per_batch: 배치당 타임아웃
            **kwargs: 플러그인에 전달할 추가 인자
        
        Returns:
            통합된 결과 {"passed_symbols": [...], "failed_symbols": [...], ...}
        """
        # 배치 크기 결정
        if batch_size is None:
            if self._resource_context:
                state = self._resource_context.get_throttle_state()
                batch_size = state.recommended_batch_size
            else:
                batch_size = self._default_batch_size
        
        timeout = timeout_per_batch or self._default_timeout
        
        # 배치 분할 불필요
        if len(symbols) <= batch_size:
            return await self.execute(
                plugin_id=plugin_id,
                plugin_callable=plugin_callable,
                kwargs={"symbols": symbols, **kwargs},
                timeout=timeout,
            )
        
        # 배치 분할 실행
        all_passed = []
        all_failed = []
        all_symbol_results = {}
        
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(symbols) + batch_size - 1) // batch_size
            
            logger.debug(
                f"Plugin '{plugin_id}' batch {batch_num}/{total_batches} "
                f"({len(batch)} symbols)"
            )
            
            try:
                result = await self.execute(
                    plugin_id=f"{plugin_id}:batch{batch_num}",
                    plugin_callable=plugin_callable,
                    kwargs={"symbols": batch, **kwargs},
                    timeout=timeout,
                )
                
                all_passed.extend(result.get("passed_symbols", []))
                all_failed.extend(result.get("failed_symbols", []))
                all_symbol_results.update(result.get("symbol_results", {}))
                
            except PluginTimeoutError:
                # 타임아웃된 배치는 failed로 처리
                all_failed.extend(batch)
                logger.warning(
                    f"Plugin '{plugin_id}' batch {batch_num} timed out, "
                    f"{len(batch)} symbols marked as failed"
                )
            
            # 배치 간 쿨다운 (시스템 안정성)
            if i + batch_size < len(symbols):
                await asyncio.sleep(0.01)
        
        return {
            "passed_symbols": all_passed,
            "failed_symbols": all_failed,
            "symbol_results": all_symbol_results,
            "result": len(all_passed) > 0,
            "batched": True,
            "batch_count": (len(symbols) + batch_size - 1) // batch_size,
        }
    
    def get_stats(self) -> dict:
        """실행 통계 반환"""
        stats = self._stats.copy()
        
        if stats["total_executions"] > 0:
            stats["avg_time_sec"] = stats["total_time_sec"] / stats["total_executions"]
            stats["timeout_rate"] = stats["timeouts"] / stats["total_executions"]
            stats["error_rate"] = stats["errors"] / stats["total_executions"]
        
        return stats
    
    def reset_stats(self) -> None:
        """통계 초기화"""
        self._stats = {
            "total_executions": 0,
            "timeouts": 0,
            "errors": 0,
            "total_time_sec": 0.0,
        }


# 전역 샌드박스 인스턴스 (편의용)
_default_sandbox: Optional[PluginSandbox] = None


def get_sandbox(
    resource_context: Optional["ResourceContext"] = None,
) -> PluginSandbox:
    """
    기본 샌드박스 인스턴스 반환
    
    Args:
        resource_context: 리소스 컨텍스트 (설정 시 새 인스턴스 생성)
    """
    global _default_sandbox
    
    if resource_context is not None:
        # 리소스 컨텍스트가 제공되면 새 인스턴스
        return PluginSandbox(resource_context=resource_context)
    
    if _default_sandbox is None:
        _default_sandbox = PluginSandbox()
    
    return _default_sandbox


__all__ = [
    "PluginError",
    "PluginTimeoutError",
    "PluginResourceError",
    "PluginSandbox",
    "get_sandbox",
]
