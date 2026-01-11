"""
ProgramGarden Core - 노드 기반 DSL 핵심 타입 정의

5-Layer Architecture:
    1. Registry Layer - 노드/플러그인 메타데이터
    2. Credential Layer - 인증/보안
    3. Definition Layer - 워크플로우 정의
    4. Job Layer - 실행 인스턴스
    5. Event Layer - 이벤트 히스토리

Finance 패키지 지원:
    - korea_alias: 한글 별칭 강제 유틸리티
    - bases: Finance 베이스 클래스들
    - exceptions: Finance 전용 예외들
"""

from programgarden_core.nodes import *
from programgarden_core.nodes.base import BaseNotificationNode
from programgarden_core.models import *
from programgarden_core.registry import *
from programgarden_core.exceptions import *

# Finance 패키지용 모듈들
from programgarden_core import korea_alias
from programgarden_core import bases

__version__ = "2.0.0"
__all__ = [
    # Nodes
    "BaseNode",
    "BaseNotificationNode",  # 커뮤니티 알림 노드용 베이스
    "StartNode",
    "BrokerNode",
    "RealMarketDataNode",
    "RealAccountNode",
    "RealOrderEventNode",
    "MarketDataNode",
    "AccountNode",
    "WatchlistNode",
    "MarketUniverseNode",
    "ScreenerNode",
    "SymbolFilterNode",
    "ScheduleNode",
    "TradingHoursFilterNode",
    "ExchangeStatusNode",
    "ConditionNode",
    "LogicNode",
    "PositionSizingNode",
    "RiskGuardNode",
    "PortfolioNode",
    "NewOrderNode",
    "ModifyOrderNode",
    "CancelOrderNode",
    # Event 노드는 커뮤니티 노드(TelegramNode 등)로 대체됨
    "DisplayNode",
    # Models
    "Edge",
    "WorkflowDefinition",
    "WorkflowJob",
    "JobState",
    "BrokerCredential",
    "Event",
    # Registry
    "NodeTypeRegistry",
    "PluginRegistry",
    # Exceptions (DSL)
    "ProgramGardenError",
    "ValidationError",
    "ExecutionError",
    # Exceptions (Finance)
    "FinanceError",
    "AppKeyException",
    "LoginException",
    "TokenException",
    "TokenNotFoundException",
    "TrRequestDataNotFoundException",
    # Finance modules
    "korea_alias",
    "bases",
]
