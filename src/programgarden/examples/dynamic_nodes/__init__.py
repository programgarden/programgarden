"""
Dynamic Node 예제 10종

ProgramGarden의 Dynamic Node Injection 시스템을 활용한 예제 모음.
community 패키지 기여 없이 런타임에 커스텀 노드를 주입하여 워크플로우에서 사용할 수 있습니다.

카테고리별 구성:
- condition (4종): SimpleRSI, MACross, PriceAlert, SignalAggregator
- data (2종): DataNormalizer, CSVParser
- order (2종): PositionSizer, ProfitTaker
- risk (1종): RiskScorer
- analysis (1종): PerformanceTracker
"""

from examples.dynamic_nodes.nodes import (
    # condition
    DynamicSimpleRSINode,
    DynamicMACrossNode,
    DynamicPriceAlertNode,
    DynamicSignalAggregatorNode,
    # data
    DynamicDataNormalizerNode,
    DynamicCSVParserNode,
    # order
    DynamicPositionSizerNode,
    DynamicProfitTakerNode,
    # risk
    DynamicRiskScorerNode,
    # analysis
    DynamicPerformanceTrackerNode,
    # schemas
    ALL_SCHEMAS,
    ALL_NODE_CLASSES,
)

__all__ = [
    "DynamicSimpleRSINode",
    "DynamicMACrossNode",
    "DynamicPriceAlertNode",
    "DynamicSignalAggregatorNode",
    "DynamicDataNormalizerNode",
    "DynamicCSVParserNode",
    "DynamicPositionSizerNode",
    "DynamicProfitTakerNode",
    "DynamicRiskScorerNode",
    "DynamicPerformanceTrackerNode",
    "ALL_SCHEMAS",
    "ALL_NODE_CLASSES",
]
