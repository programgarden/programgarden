"""
ProgramGarden Core - Resource 모델

리소스 관리 및 적응형 스로틀링을 위한 데이터 모델
- 로컬 컴퓨터 및 K8s 컨테이너 환경 모두 지원
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class ThrottleLevel(str, Enum):
    """
    스로틀링 수준
    
    리소스 사용량에 따라 5단계로 조절:
    - NONE: 정상 (사용률 < 60%)
    - LIGHT: 경량 제한 (60% ~ 75%)
    - MODERATE: 중간 제한 (75% ~ 90%)
    - HEAVY: 강한 제한 (90% ~ 100%)
    - CRITICAL: 최대 제한 (100% 이상, 신규 작업 중단)
    """
    NONE = "none"
    LIGHT = "light"
    MODERATE = "moderate"
    HEAVY = "heavy"
    CRITICAL = "critical"


class ResourceUsage(BaseModel):
    """
    현재 시스템 리소스 사용량
    
    CPU, RAM, 디스크 사용량과 워커 상태를 추적합니다.
    로컬 환경과 K8s 컨테이너 환경 모두에서 동작합니다.
    """
    cpu_percent: float = Field(
        ..., 
        ge=0, 
        le=100,
        description="CPU 사용률 (0.0 ~ 100.0)"
    )
    memory_percent: float = Field(
        ..., 
        ge=0, 
        le=100,
        description="메모리 사용률 (0.0 ~ 100.0)"
    )
    memory_used_mb: float = Field(
        ..., 
        ge=0,
        description="사용 중인 메모리 (MB)"
    )
    memory_available_mb: float = Field(
        ..., 
        ge=0,
        description="사용 가능한 메모리 (MB)"
    )
    disk_percent: float = Field(
        default=0.0, 
        ge=0, 
        le=100,
        description="디스크 사용률 (0.0 ~ 100.0)"
    )
    disk_used_gb: float = Field(
        default=0.0,
        ge=0,
        description="사용 중인 디스크 (GB)"
    )
    disk_available_gb: float = Field(
        default=0.0,
        ge=0,
        description="사용 가능한 디스크 (GB)"
    )
    active_workers: int = Field(
        default=0, 
        ge=0,
        description="현재 활성 워커 수"
    )
    pending_tasks: int = Field(
        default=0, 
        ge=0,
        description="대기 중인 태스크 수"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="측정 시간"
    )

    def to_summary(self) -> Dict[str, Any]:
        """요약 정보 반환"""
        return {
            "cpu": f"{self.cpu_percent:.1f}%",
            "memory": f"{self.memory_percent:.1f}% ({self.memory_used_mb:.0f}MB used)",
            "disk": f"{self.disk_percent:.1f}%",
            "workers": f"{self.active_workers} active, {self.pending_tasks} pending",
        }


class ResourceLimits(BaseModel):
    """
    리소스 제한 설정
    
    워크플로우 또는 전역 레벨에서 리소스 사용량을 제한합니다.
    미설정 시 자동 감지된 시스템 리소스의 80%를 기본값으로 사용합니다.
    
    Example:
        >>> limits = ResourceLimits(max_cpu_percent=70, max_memory_percent=75)
        >>> # 또는 자동 감지
        >>> limits = ResourceLimits.auto_detect()
    """
    # 시스템 리소스 제한
    max_cpu_percent: float = Field(
        default=80.0, 
        ge=0, 
        le=100,
        description="최대 CPU 사용률 (%)"
    )
    max_memory_percent: float = Field(
        default=80.0, 
        ge=0, 
        le=100,
        description="최대 메모리 사용률 (%)"
    )
    max_memory_mb: Optional[float] = Field(
        default=None, 
        ge=0,
        description="최대 메모리 사용량 (MB, None=무제한)"
    )
    max_disk_percent: float = Field(
        default=90.0, 
        ge=0, 
        le=100,
        description="최대 디스크 사용률 (%)"
    )
    
    # 워커 제한
    max_workers: int = Field(
        default=4, 
        ge=1,
        description="최대 동시 워커 수"
    )
    max_pending_tasks: int = Field(
        default=100, 
        ge=1,
        description="최대 대기 태스크 수"
    )
    
    # 노드별 제한
    max_symbols_per_condition: int = Field(
        default=100, 
        ge=1,
        description="조건 노드당 최대 처리 종목 수"
    )
    max_backtest_days: int = Field(
        default=1095,  # 3년
        ge=1,
        description="백테스트 최대 기간 (일)"
    )
    max_parallel_backtests: int = Field(
        default=2, 
        ge=1,
        description="최대 동시 백테스트 수"
    )
    
    # 스로틀링 전략
    throttle_strategy: str = Field(
        default="gradual",
        description="스로틀링 전략 (gradual, aggressive, conservative)"
    )

    @classmethod
    def auto_detect(cls) -> "ResourceLimits":
        """
        시스템 리소스 기반 자동 제한 설정
        
        로컬 컴퓨터와 K8s 컨테이너 환경 모두에서 동작합니다.
        
        Returns:
            시스템에 맞게 조정된 ResourceLimits
        """
        try:
            import psutil
            
            # 메모리 기반 워커 수 결정
            mem = psutil.virtual_memory()
            total_memory_mb = mem.total / (1024 * 1024)
            
            # CPU 코어 수 기반 워커 수 결정
            cpu_count = psutil.cpu_count(logical=False) or 2
            
            # 메모리 기준: 워커당 최소 512MB 필요
            memory_based_workers = max(1, int(total_memory_mb / 512))
            
            # CPU 기준: 코어 수의 2배 (I/O 대기 고려)
            cpu_based_workers = cpu_count * 2
            
            # 더 작은 값 선택
            max_workers = min(memory_based_workers, cpu_based_workers, 8)
            
            # 백테스트 동시 실행 수 (메모리 집약적이므로 보수적)
            max_parallel_backtests = max(1, min(max_workers // 2, 4))
            
            return cls(
                max_cpu_percent=80.0,
                max_memory_percent=80.0,
                max_disk_percent=90.0,
                max_workers=max_workers,
                max_parallel_backtests=max_parallel_backtests,
            )
        except ImportError:
            # psutil 없으면 기본값 사용
            return cls()

    def to_json(self) -> Dict[str, Any]:
        """JSON 직렬화 가능한 dict 반환"""
        return self.model_dump(exclude_none=True)


class ThrottleState(BaseModel):
    """
    현재 스로틀링 상태
    
    AdaptiveThrottle에 의해 관리되며, 현재 리소스 상태에 따른
    실행 제한 정보를 제공합니다.
    """
    level: ThrottleLevel = Field(
        default=ThrottleLevel.NONE,
        description="현재 스로틀링 레벨"
    )
    delay_multiplier: float = Field(
        default=1.0, 
        ge=1.0,
        description="지연 배수 (1.0=정상, 2.0=2배 느리게)"
    )
    max_concurrent_tasks: int = Field(
        default=4, 
        ge=1,
        description="현재 허용 동시 작업 수"
    )
    recommended_batch_size: int = Field(
        default=10,
        ge=1,
        description="권장 배치 크기"
    )
    paused_new_tasks: bool = Field(
        default=False,
        description="신규 작업 일시 중단 여부"
    )
    reason: Optional[str] = Field(
        default=None,
        description="스로틀링 이유"
    )
    since: datetime = Field(
        default_factory=datetime.utcnow,
        description="현재 레벨 시작 시간"
    )

    def to_summary(self) -> Dict[str, Any]:
        """요약 정보 반환"""
        return {
            "level": self.level.value,
            "delay": f"{self.delay_multiplier:.1f}x",
            "max_tasks": self.max_concurrent_tasks,
            "batch_size": self.recommended_batch_size,
            "paused": self.paused_new_tasks,
            "reason": self.reason,
        }


class ResourceHints(BaseModel):
    """
    노드별 리소스 힌트
    
    각 노드의 리소스 사용 특성을 명시하여 스케줄러가 최적 결정을 내릴 수 있게 합니다.
    
    Example (JSON DSL):
        {
            "id": "backtest",
            "type": "BacktestEngineNode",
            "resource_hints": {
                "weight": 2.0,
                "memory_intensive": true,
                "max_parallel": 1
            }
        }
    """
    weight: float = Field(
        default=1.0,
        ge=0.1,
        le=10.0,
        description="작업 가중치 (1.0=일반, 2.0=2배 무거움)"
    )
    memory_intensive: bool = Field(
        default=False,
        description="메모리 집약적 작업 여부"
    )
    cpu_intensive: bool = Field(
        default=False,
        description="CPU 집약적 작업 여부"
    )
    max_parallel: Optional[int] = Field(
        default=None,
        ge=1,
        description="이 노드 타입의 최대 동시 실행 수"
    )
    batch_size: Optional[int] = Field(
        default=None,
        ge=1,
        description="권장 배치 크기 (None=자동)"
    )
    priority: int = Field(
        default=5,
        ge=1,
        le=10,
        description="우선순위 (1=최저, 10=최고, 주문 노드는 10 권장)"
    )


# 노드 타입별 기본 리소스 힌트
DEFAULT_NODE_HINTS: Dict[str, ResourceHints] = {
    # 고우선순위 (주문 관련)
    "NewOrderNode": ResourceHints(weight=0.5, priority=10),
    "ModifyOrderNode": ResourceHints(weight=0.5, priority=10),
    "CancelOrderNode": ResourceHints(weight=0.5, priority=10),
    
    # 일반
    "StartNode": ResourceHints(weight=0.1, priority=5),
    # Broker (상품별 분리)
    "OverseasStockBrokerNode": ResourceHints(weight=0.5, priority=8),
    "OverseasFuturesBrokerNode": ResourceHints(weight=0.5, priority=8),
    "WatchlistNode": ResourceHints(weight=0.2, priority=5),
    "ConditionNode": ResourceHints(weight=1.0, cpu_intensive=True, priority=5),
    "LogicNode": ResourceHints(weight=0.5, priority=5),

    # 데이터 집약적 (상품별 분리)
    "OverseasStockHistoricalDataNode": ResourceHints(weight=1.5, memory_intensive=True, priority=4),
    "OverseasFuturesHistoricalDataNode": ResourceHints(weight=1.5, memory_intensive=True, priority=4),
    "OverseasStockMarketDataNode": ResourceHints(weight=1.0, priority=5),
    "OverseasFuturesMarketDataNode": ResourceHints(weight=1.0, priority=5),

    # 실시간 (지속 연결, 상품별 분리)
    "OverseasStockRealMarketDataNode": ResourceHints(weight=1.0, priority=7),
    "OverseasFuturesRealMarketDataNode": ResourceHints(weight=1.0, priority=7),
    "OverseasStockRealAccountNode": ResourceHints(weight=1.0, priority=7),
    "OverseasFuturesRealAccountNode": ResourceHints(weight=1.0, priority=7),
    "OverseasStockRealOrderEventNode": ResourceHints(weight=0.5, priority=8),
    "OverseasFuturesRealOrderEventNode": ResourceHints(weight=0.5, priority=8),

    # 무거운 작업
    "BacktestEngineNode": ResourceHints(
        weight=3.0,
        memory_intensive=True,
        cpu_intensive=True,
        max_parallel=2,
        priority=3
    ),
    "ScreenerNode": ResourceHints(weight=2.0, cpu_intensive=True, priority=4),

    # 계정 (상품별 분리)
    "OverseasStockAccountNode": ResourceHints(weight=0.5, priority=6),
    "OverseasFuturesAccountNode": ResourceHints(weight=0.5, priority=6),

    # 기타
    "ScheduleNode": ResourceHints(weight=0.1, priority=5),
    "TableDisplayNode": ResourceHints(weight=0.2, priority=2),
    "LineChartNode": ResourceHints(weight=0.2, priority=2),
    "MultiLineChartNode": ResourceHints(weight=0.2, priority=2),
    "CandlestickChartNode": ResourceHints(weight=0.2, priority=2),
    "BarChartNode": ResourceHints(weight=0.2, priority=2),
    "SummaryDisplayNode": ResourceHints(weight=0.2, priority=2),
    "AlertNode": ResourceHints(weight=0.3, priority=6),
}


def get_node_hints(node_type: str) -> ResourceHints:
    """
    노드 타입에 대한 기본 리소스 힌트 반환
    
    Args:
        node_type: 노드 타입 (예: "ConditionNode", "BacktestEngineNode")
    
    Returns:
        해당 노드의 ResourceHints (없으면 기본값)
    """
    return DEFAULT_NODE_HINTS.get(node_type, ResourceHints())
