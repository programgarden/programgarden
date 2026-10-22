"""
ProgramGarden - Resource Management Package

리소스 모니터링 및 적응형 스로틀링 시스템

- ResourceMonitor: 실시간 CPU/RAM/디스크 모니터링
- ResourceLimiter: 리소스 제한 관리
- AdaptiveThrottle: 동적 속도 조절
- ResourceContext: 통합 컨텍스트

Usage:
    >>> from programgarden.resource import ResourceContext
    >>> 
    >>> # 자동 감지 모드
    >>> async with await ResourceContext.create() as ctx:
    ...     usage = ctx.get_usage()
    ...     print(f"CPU: {usage.cpu_percent}%")
    >>> 
    >>> # 명시적 제한 설정
    >>> from programgarden_core.models import ResourceLimits
    >>> limits = ResourceLimits(max_cpu_percent=70, max_memory_percent=75)
    >>> async with await ResourceContext.create(limits=limits) as ctx:
    ...     state = ctx.get_throttle_state()
    ...     print(f"Throttle level: {state.level}")
"""

from programgarden.resource.monitor import ResourceMonitor
from programgarden.resource.limiter import ResourceLimiter
from programgarden.resource.throttle import AdaptiveThrottle
from programgarden.resource.context import ResourceContext

__all__ = [
    "ResourceMonitor",
    "ResourceLimiter",
    "AdaptiveThrottle",
    "ResourceContext",
]
