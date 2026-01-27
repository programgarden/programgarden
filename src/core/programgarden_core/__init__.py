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
from programgarden_core.nodes.base import BaseMessagingNode
from programgarden_core.models import *
from programgarden_core.registry import *
from programgarden_core.exceptions import *

# Finance 패키지용 모듈들
from programgarden_core import korea_alias
from programgarden_core import bases

__version__ = "2.0.0"
__all__ = [
    # Nodes - Base
    "BaseNode",
    "BaseMessagingNode",  # 커뮤니티 메시징 노드용 베이스
    # Nodes - Infra
    "StartNode",
    "ThrottleNode",
    # Nodes - Broker (상품별 분리)
    "OverseasStockBrokerNode",
    "OverseasFuturesBrokerNode",
    # Nodes - Market (해외주식)
    "OverseasStockMarketDataNode",
    "OverseasStockHistoricalDataNode",
    "OverseasStockRealMarketDataNode",
    "OverseasStockSymbolQueryNode",
    # Nodes - Market (해외선물)
    "OverseasFuturesMarketDataNode",
    "OverseasFuturesHistoricalDataNode",
    "OverseasFuturesRealMarketDataNode",
    "OverseasFuturesSymbolQueryNode",
    # Nodes - Account (해외주식)
    "OverseasStockAccountNode",
    "OverseasStockRealAccountNode",
    "OverseasStockRealOrderEventNode",
    # Nodes - Account (해외선물)
    "OverseasFuturesAccountNode",
    "OverseasFuturesRealAccountNode",
    "OverseasFuturesRealOrderEventNode",
    # Nodes - Symbol (상품 무관)
    "WatchlistNode",
    "MarketUniverseNode",
    "ScreenerNode",
    "SymbolFilterNode",
    # Nodes - Data (상품 무관)
    "SQLiteNode",
    "PostgresNode",
    "HTTPRequestNode",
    "FieldMappingNode",
    # Nodes - Trigger
    "ScheduleNode",
    "TradingHoursFilterNode",
    # Nodes - Condition
    "ConditionNode",
    "LogicNode",
    # Nodes - Risk
    "PositionSizingNode",
    "PortfolioNode",
    # Nodes - Order (해외주식)
    "OverseasStockNewOrderNode",
    "OverseasStockModifyOrderNode",
    "OverseasStockCancelOrderNode",
    # Nodes - Order (해외선물)
    "OverseasFuturesNewOrderNode",
    "OverseasFuturesModifyOrderNode",
    "OverseasFuturesCancelOrderNode",
    # Nodes - Display
    "DisplayNode",
    # Nodes - Backtest/Analysis
    "BacktestEngineNode",
    "BenchmarkCompareNode",
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
