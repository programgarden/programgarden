"""
ProgramGarden Core - Plugin Resource Models

플러그인 리소스 관리를 위한 모델 정의
- PluginResourceHints: 플러그인별 리소스 사용 힌트
- TrustLevel: 플러그인 신뢰 레벨
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class TrustLevel(str, Enum):
    """
    플러그인 신뢰 레벨
    
    레벨에 따라 리소스 제한이 다르게 적용됩니다.
    """
    
    CORE = "core"
    """핵심 노드 (StartNode, BrokerNode 등) - 제한 없음"""
    
    VERIFIED = "verified"
    """검증된 플러그인 (공식 플러그인) - 완화된 제한"""
    
    COMMUNITY = "community"
    """커뮤니티 플러그인 (외부 기여) - 엄격한 제한"""


# 신뢰 레벨별 기본 제한
TRUST_LEVEL_LIMITS = {
    TrustLevel.CORE: {
        "max_execution_sec": None,  # 무제한
        "max_memory_mb": None,
        "max_symbols_per_call": None,
    },
    TrustLevel.VERIFIED: {
        "max_execution_sec": 60.0,
        "max_memory_mb": 500.0,
        "max_symbols_per_call": 500,
    },
    TrustLevel.COMMUNITY: {
        "max_execution_sec": 30.0,
        "max_memory_mb": 100.0,
        "max_symbols_per_call": 100,
    },
}


class PluginResourceHints(BaseModel):
    """
    플러그인 리소스 사용 힌트
    
    플러그인 등록 시 리소스 사용 특성을 명시합니다.
    PR 리뷰어가 검토 후 적절한 값을 설정합니다.
    
    Example:
        ```python
        hints = PluginResourceHints(
            max_execution_sec=30.0,
            max_symbols_per_call=100,
            cpu_intensive=True,
        )
        ```
    """
    
    max_execution_sec: float = Field(
        default=30.0,
        ge=1.0,
        le=300.0,
        description="최대 실행 시간 (초). 이 시간을 초과하면 TimeoutError 발생",
    )
    
    max_memory_mb: float = Field(
        default=100.0,
        ge=10.0,
        le=1000.0,
        description="최대 메모리 사용량 (MB). 개발 모드에서만 추적",
    )
    
    max_symbols_per_call: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="호출당 처리 가능한 최대 종목 수. 초과 시 자동 배치 분할",
    )
    
    cpu_intensive: bool = Field(
        default=False,
        description="CPU 집약적 작업 여부. True면 리소스 체크 가중치 증가",
    )
    
    io_intensive: bool = Field(
        default=False,
        description="I/O 집약적 작업 여부. 외부 API 호출이 많은 경우 True",
    )
    
    requires_historical_data: bool = Field(
        default=False,
        description="히스토리컬 데이터 필요 여부. 백테스트 최적화에 사용",
    )
    
    @classmethod
    def for_trust_level(cls, trust_level: TrustLevel) -> "PluginResourceHints":
        """신뢰 레벨에 맞는 기본 힌트 생성"""
        limits = TRUST_LEVEL_LIMITS.get(trust_level, TRUST_LEVEL_LIMITS[TrustLevel.COMMUNITY])
        
        return cls(
            max_execution_sec=limits["max_execution_sec"] or 300.0,
            max_memory_mb=limits["max_memory_mb"] or 1000.0,
            max_symbols_per_call=limits["max_symbols_per_call"] or 1000,
        )
    
    @classmethod
    def default_for_category(cls, category: str) -> "PluginResourceHints":
        """
        플러그인 카테고리별 기본 힌트
        
        Args:
            category: strategy_condition, new_order, modify_order, cancel_order
        """
        if category == "strategy_condition":
            # 전략 조건은 CPU 집약적일 수 있음
            return cls(
                max_execution_sec=30.0,
                max_symbols_per_call=100,
                cpu_intensive=True,
            )
        elif category in ("new_order", "modify_order", "cancel_order"):
            # 주문 관련은 빠른 응답 필요
            return cls(
                max_execution_sec=10.0,
                max_symbols_per_call=50,
                cpu_intensive=False,
            )
        else:
            return cls()
    
    def get_weight(self) -> float:
        """리소스 체크 가중치 계산"""
        weight = 1.0
        
        if self.cpu_intensive:
            weight += 1.0
        
        if self.io_intensive:
            weight += 0.5
        
        if self.requires_historical_data:
            weight += 0.5
        
        return weight
    
    def to_dict(self) -> dict:
        """딕셔너리 변환"""
        return {
            "max_execution_sec": self.max_execution_sec,
            "max_memory_mb": self.max_memory_mb,
            "max_symbols_per_call": self.max_symbols_per_call,
            "cpu_intensive": self.cpu_intensive,
            "io_intensive": self.io_intensive,
            "requires_historical_data": self.requires_historical_data,
        }


# 노드 타입별 기본 힌트
DEFAULT_PLUGIN_HINTS: dict[str, PluginResourceHints] = {
    # Strategy Conditions
    "RSI": PluginResourceHints(cpu_intensive=True),
    "MACD": PluginResourceHints(cpu_intensive=True),
    "BollingerBands": PluginResourceHints(cpu_intensive=True),
    "MovingAverageCross": PluginResourceHints(cpu_intensive=True, requires_historical_data=True),
    "DualMomentum": PluginResourceHints(cpu_intensive=True, requires_historical_data=True, max_execution_sec=60.0),
    
    # Order Plugins (빠른 응답 필요)
    "MarketOrder": PluginResourceHints(max_execution_sec=10.0),
    "LimitOrder": PluginResourceHints(max_execution_sec=10.0),
    "StopOrder": PluginResourceHints(max_execution_sec=10.0),
}


def get_plugin_hints(plugin_id: str) -> PluginResourceHints:
    """플러그인 ID로 리소스 힌트 조회"""
    return DEFAULT_PLUGIN_HINTS.get(plugin_id, PluginResourceHints())


__all__ = [
    "TrustLevel",
    "TRUST_LEVEL_LIMITS",
    "PluginResourceHints",
    "DEFAULT_PLUGIN_HINTS",
    "get_plugin_hints",
]
