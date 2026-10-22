"""
ProgramGarden - Resource Limiter

리소스 제한 관리 및 위반 감지

JSON DSL의 resource_limits 설정을 파싱하고,
현재 사용량이 제한을 초과하는지 확인합니다.
"""

from typing import Optional, Dict, Any, List, Tuple
import logging

from programgarden_core.models.resource import ResourceUsage, ResourceLimits

logger = logging.getLogger("programgarden.resource.limiter")


class ResourceLimiter:
    """
    리소스 제한 관리자
    
    리소스 사용 제한을 설정하고, 현재 사용량이 제한 내인지 확인합니다.
    제한 미설정 시 시스템 리소스를 자동 감지하여 80%를 기본값으로 사용합니다.
    
    Example:
        >>> # 자동 감지
        >>> limiter = ResourceLimiter.from_auto_detect()
        >>> 
        >>> # 명시적 설정
        >>> limits = ResourceLimits(max_cpu_percent=70)
        >>> limiter = ResourceLimiter(limits)
        >>> 
        >>> # 제한 체크
        >>> usage = monitor.get_usage()
        >>> if limiter.is_within_limits(usage):
        ...     print("OK")
        >>> else:
        ...     print(f"Violation: {limiter.get_violation(usage)}")
    
    Attributes:
        limits: 현재 적용된 ResourceLimits
    """
    
    def __init__(self, limits: Optional[ResourceLimits] = None):
        """
        Args:
            limits: 제한 설정 (None이면 자동 감지)
        """
        if limits is None:
            self._limits = ResourceLimits.auto_detect()
            logger.info(f"Auto-detected limits: workers={self._limits.max_workers}")
        else:
            self._limits = limits
            logger.info(f"Using provided limits: cpu={limits.max_cpu_percent}%, mem={limits.max_memory_percent}%")
    
    @classmethod
    def from_auto_detect(cls) -> "ResourceLimiter":
        """
        시스템 리소스 기반 자동 제한 설정
        
        Returns:
            자동 감지된 제한이 적용된 ResourceLimiter
        """
        return cls(limits=ResourceLimits.auto_detect())
    
    @classmethod
    def from_json(cls, config: Dict[str, Any]) -> "ResourceLimiter":
        """
        JSON 설정에서 제한 로드
        
        Args:
            config: resource_limits JSON 객체
        
        Returns:
            설정이 적용된 ResourceLimiter
        
        Example:
            >>> config = {"max_cpu_percent": 70, "max_memory_percent": 75}
            >>> limiter = ResourceLimiter.from_json(config)
        """
        if not config:
            return cls.from_auto_detect()
        
        limits = ResourceLimits(**config)
        return cls(limits)
    
    @property
    def limits(self) -> ResourceLimits:
        """현재 적용된 제한"""
        return self._limits
    
    def is_within_limits(self, usage: ResourceUsage) -> bool:
        """
        현재 사용량이 제한 내인지 확인
        
        Args:
            usage: 현재 리소스 사용량
        
        Returns:
            True: 제한 내
            False: 제한 초과
        """
        return self.get_violation(usage) is None
    
    def get_violation(self, usage: ResourceUsage) -> Optional[str]:
        """
        제한 초과 시 위반 내용 반환
        
        Args:
            usage: 현재 리소스 사용량
        
        Returns:
            위반 내용 문자열 (위반 없으면 None)
        """
        violations = []
        
        # CPU 체크
        if usage.cpu_percent > self._limits.max_cpu_percent:
            violations.append(
                f"CPU {usage.cpu_percent:.1f}% > {self._limits.max_cpu_percent}%"
            )
        
        # Memory 체크 (퍼센트)
        if usage.memory_percent > self._limits.max_memory_percent:
            violations.append(
                f"Memory {usage.memory_percent:.1f}% > {self._limits.max_memory_percent}%"
            )
        
        # Memory 체크 (절대값)
        if self._limits.max_memory_mb is not None:
            if usage.memory_used_mb > self._limits.max_memory_mb:
                violations.append(
                    f"Memory {usage.memory_used_mb:.0f}MB > {self._limits.max_memory_mb}MB"
                )
        
        # Disk 체크
        if usage.disk_percent > self._limits.max_disk_percent:
            violations.append(
                f"Disk {usage.disk_percent:.1f}% > {self._limits.max_disk_percent}%"
            )
        
        # Worker 체크
        if usage.active_workers > self._limits.max_workers:
            violations.append(
                f"Workers {usage.active_workers} > {self._limits.max_workers}"
            )
        
        # Pending 체크
        if usage.pending_tasks > self._limits.max_pending_tasks:
            violations.append(
                f"Pending {usage.pending_tasks} > {self._limits.max_pending_tasks}"
            )
        
        if violations:
            return "; ".join(violations)
        return None
    
    def get_violations_detailed(self, usage: ResourceUsage) -> List[Dict[str, Any]]:
        """
        상세한 위반 정보 목록 반환
        
        Args:
            usage: 현재 리소스 사용량
        
        Returns:
            위반 정보 리스트 (각 항목: resource, current, limit, severity)
        """
        violations = []
        
        # CPU
        if usage.cpu_percent > self._limits.max_cpu_percent:
            violations.append({
                "resource": "cpu",
                "current": usage.cpu_percent,
                "limit": self._limits.max_cpu_percent,
                "severity": self._calculate_severity(
                    usage.cpu_percent, self._limits.max_cpu_percent
                ),
            })
        
        # Memory (percent)
        if usage.memory_percent > self._limits.max_memory_percent:
            violations.append({
                "resource": "memory_percent",
                "current": usage.memory_percent,
                "limit": self._limits.max_memory_percent,
                "severity": self._calculate_severity(
                    usage.memory_percent, self._limits.max_memory_percent
                ),
            })
        
        # Memory (absolute)
        if self._limits.max_memory_mb and usage.memory_used_mb > self._limits.max_memory_mb:
            violations.append({
                "resource": "memory_mb",
                "current": usage.memory_used_mb,
                "limit": self._limits.max_memory_mb,
                "severity": self._calculate_severity(
                    usage.memory_used_mb, self._limits.max_memory_mb
                ),
            })
        
        # Disk
        if usage.disk_percent > self._limits.max_disk_percent:
            violations.append({
                "resource": "disk",
                "current": usage.disk_percent,
                "limit": self._limits.max_disk_percent,
                "severity": self._calculate_severity(
                    usage.disk_percent, self._limits.max_disk_percent
                ),
            })
        
        # Workers
        if usage.active_workers > self._limits.max_workers:
            violations.append({
                "resource": "workers",
                "current": usage.active_workers,
                "limit": self._limits.max_workers,
                "severity": "high",  # 워커 초과는 항상 심각
            })
        
        return violations
    
    def _calculate_severity(self, current: float, limit: float) -> str:
        """위반 심각도 계산"""
        if limit <= 0:
            return "critical"
        
        ratio = current / limit
        if ratio >= 1.2:
            return "critical"
        elif ratio >= 1.1:
            return "high"
        elif ratio >= 1.05:
            return "medium"
        else:
            return "low"
    
    def get_headroom(self, usage: ResourceUsage) -> Dict[str, float]:
        """
        각 리소스별 여유 공간 (%) 반환
        
        양수: 여유 있음
        음수: 초과
        
        Args:
            usage: 현재 리소스 사용량
        
        Returns:
            리소스별 여유율 dict
        
        Example:
            >>> headroom = limiter.get_headroom(usage)
            >>> # {"cpu": 15.5, "memory": -5.2, "disk": 40.0, ...}
            >>> if headroom["memory"] < 0:
            ...     print("Memory limit exceeded!")
        """
        return {
            "cpu": self._limits.max_cpu_percent - usage.cpu_percent,
            "memory": self._limits.max_memory_percent - usage.memory_percent,
            "disk": self._limits.max_disk_percent - usage.disk_percent,
            "workers": self._limits.max_workers - usage.active_workers,
            "pending": self._limits.max_pending_tasks - usage.pending_tasks,
        }
    
    def get_utilization_ratio(self, usage: ResourceUsage) -> Dict[str, float]:
        """
        각 리소스별 제한 대비 사용률 반환
        
        0.0 ~ 1.0: 정상
        > 1.0: 초과
        
        Args:
            usage: 현재 리소스 사용량
        
        Returns:
            리소스별 사용률 dict
        """
        def safe_ratio(current: float, limit: float) -> float:
            if limit <= 0:
                return float('inf') if current > 0 else 0.0
            return current / limit
        
        return {
            "cpu": safe_ratio(usage.cpu_percent, self._limits.max_cpu_percent),
            "memory": safe_ratio(usage.memory_percent, self._limits.max_memory_percent),
            "disk": safe_ratio(usage.disk_percent, self._limits.max_disk_percent),
            "workers": safe_ratio(usage.active_workers, self._limits.max_workers),
            "pending": safe_ratio(usage.pending_tasks, self._limits.max_pending_tasks),
        }
    
    def get_max_utilization(self, usage: ResourceUsage) -> Tuple[str, float]:
        """
        가장 높은 사용률의 리소스와 값 반환
        
        Args:
            usage: 현재 리소스 사용량
        
        Returns:
            (리소스명, 사용률) 튜플
        
        Example:
            >>> resource, ratio = limiter.get_max_utilization(usage)
            >>> print(f"Highest: {resource} at {ratio:.1%}")
        """
        ratios = self.get_utilization_ratio(usage)
        max_resource = max(ratios, key=ratios.get)
        return max_resource, ratios[max_resource]
    
    def can_accept_task(
        self, 
        usage: ResourceUsage,
        task_weight: float = 1.0,
        cpu_estimate: float = 5.0,
        memory_estimate_mb: float = 50.0,
    ) -> Tuple[bool, Optional[str]]:
        """
        새 태스크를 수용할 수 있는지 확인
        
        예상 리소스 사용량을 고려하여 판단합니다.
        
        Args:
            usage: 현재 리소스 사용량
            task_weight: 태스크 가중치
            cpu_estimate: 예상 CPU 사용량 증가 (%)
            memory_estimate_mb: 예상 메모리 사용량 (MB)
        
        Returns:
            (수용 가능 여부, 거부 사유)
        """
        # 워커 제한 체크
        if usage.active_workers >= self._limits.max_workers:
            return False, f"Max workers reached ({self._limits.max_workers})"
        
        # 대기 태스크 제한 체크
        if usage.pending_tasks >= self._limits.max_pending_tasks:
            return False, f"Max pending tasks reached ({self._limits.max_pending_tasks})"
        
        # 예상 CPU 체크
        estimated_cpu = usage.cpu_percent + (cpu_estimate * task_weight)
        if estimated_cpu > self._limits.max_cpu_percent * 1.1:  # 10% 버퍼
            return False, f"Estimated CPU too high ({estimated_cpu:.1f}%)"
        
        # 예상 메모리 체크
        estimated_memory_mb = usage.memory_used_mb + (memory_estimate_mb * task_weight)
        if self._limits.max_memory_mb and estimated_memory_mb > self._limits.max_memory_mb:
            return False, f"Estimated memory too high ({estimated_memory_mb:.0f}MB)"
        
        # 메모리 퍼센트 체크 (대략적)
        if usage.memory_available_mb > 0:
            total_mb = usage.memory_used_mb + usage.memory_available_mb
            estimated_percent = (estimated_memory_mb / total_mb) * 100
            if estimated_percent > self._limits.max_memory_percent * 1.1:
                return False, f"Estimated memory percent too high ({estimated_percent:.1f}%)"
        
        return True, None
    
    def update_limits(self, **kwargs) -> None:
        """
        제한 값 동적 업데이트
        
        Args:
            **kwargs: 업데이트할 필드 (max_cpu_percent, max_memory_percent 등)
        """
        for key, value in kwargs.items():
            if hasattr(self._limits, key):
                setattr(self._limits, key, value)
                logger.info(f"Updated limit: {key}={value}")
            else:
                logger.warning(f"Unknown limit field: {key}")
