# ProgramGarden Core

ProgramGarden은 AI 시대에 맞춰 파이썬을 모르는 투자자도 개인화된 시스템 트레이딩을 자동으로 수행할 수 있게 돕는 오픈소스입니다. 본 저장소는 노드 기반 DSL의 핵심 타입, 베이스 클래스, 레지스트리, i18n을 정의하는 "코어" 모듈입니다.

- 문서(비개발자 빠른 시작): https://programgarden.gitbook.io/docs/invest/non_dev_quick_guide
- 문서(개발자 구조 안내): https://programgarden.gitbook.io/docs/develop/structure
- 유튜브: https://www.youtube.com/@programgarden
- 실시간소통 오픈톡방: https://open.kakao.com/o/gKVObqUh

## 주요 특징

- **노드 기반 DSL**: 55개 내장 노드를 조합하여 워크플로우를 정의하는 도메인 특화 언어
- **타입 안전한 스키마**: Pydantic 모델 기반의 FieldSchema, 입출력 포트 정의로 IDE 친화적이고 안전한 개발
- **레지스트리 시스템**: NodeTypeRegistry와 PluginRegistry로 노드/플러그인 메타데이터 관리
- **다국어 지원(i18n)**: 한국어/영어 번역 파일을 통한 노드 설명, 필드명 자동 번역
- **상품별 분리**: 해외주식(`overseas_stock`)과 해외선물(`overseas_futures`)을 독립된 노드로 지원
- **플러그인 확장**: ConditionNode에 커뮤니티 전략 플러그인(RSI, MACD 등)을 연결하여 확장

## 설치

```bash
pip install programgarden-core

# Poetry 사용 시 (개발 환경)
poetry add programgarden-core
```

요구 사항: Python 3.12+

## 노드 카테고리 (11개, 55개 노드)

| 카테고리 | 노드 수 | 대표 노드 |
|----------|---------|----------|
| infra | 7 | StartNode, BrokerNode, ThrottleNode, SplitNode, AggregateNode, IfNode |
| account | 8 | AccountNode, OpenOrdersNode, RealAccountNode, RealOrderEventNode |
| market | 15 | MarketDataNode, HistoricalDataNode, RealMarketDataNode, WatchlistNode, ExclusionListNode, CurrencyRateNode |
| condition | 2 | ConditionNode, LogicNode |
| order | 7 | NewOrderNode, ModifyOrderNode, CancelOrderNode, PositionSizingNode |
| risk | 1 | PortfolioNode |
| schedule | 2 | ScheduleNode, TradingHoursFilterNode |
| data | 3 | SQLiteNode, HTTPRequestNode, FieldMappingNode |
| display | 6 | TableDisplayNode, LineChartNode, CandlestickChartNode, SummaryDisplayNode |
| analysis | 2 | BacktestEngineNode, BenchmarkCompareNode |
| ai | 2 | LLMModelNode, AIAgentNode |

## 사용 예시

```python
from programgarden_core import (
    # 노드
    StartNode, ConditionNode, LogicNode,
    OverseasStockBrokerNode, OverseasStockAccountNode,

    # 모델
    Edge, WorkflowDefinition, WorkflowJob, JobState,

    # 레지스트리
    NodeTypeRegistry, PluginRegistry,
)

# 레지스트리에서 노드 스키마 조회
registry = NodeTypeRegistry()
schema = registry.get_schema("OverseasStockBrokerNode")
print(schema.config_schema)
```

## 패키지 구조

```
programgarden_core/
├── nodes/          # 55개 노드 정의 (base.py, infra.py, account.py, ...)
├── bases/          # Finance 베이스 클래스
├── models/         # Pydantic 모델 (FieldSchema, Edge, WorkflowDefinition 등)
├── registry/       # NodeTypeRegistry, PluginRegistry
├── i18n/locales/   # 번역 파일 (ko.json, en.json)
└── exceptions/     # DSL/Finance 예외 클래스
```

## 기여하기

이슈/토론/PR 환영합니다. 버그 리포트 시 재현 단계와 최소 예시를 함께 제공해 주시면 빠르게 대응할 수 있습니다.

## 변경 로그

자세한 변경 사항은 `CHANGELOG.md`를 참고하세요.
