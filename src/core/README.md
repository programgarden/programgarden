# ProgramGarden Core

ProgramGarden은 AI 시대에 맞춰 파이썬을 모르는 투자자도 개인화된 시스템 트레이딩을 자동으로 수행할 수 있게 돕는 오픈소스입니다. 본 저장소는 노드 기반 DSL의 핵심 타입, 베이스 클래스, 레지스트리, i18n을 정의하는 "코어" 모듈입니다.

- 문서(비개발자 빠른 시작): https://programgarden.gitbook.io/docs/invest/non_dev_quick_guide
- 문서(개발자 구조 안내): https://programgarden.gitbook.io/docs/develop/structure
- 유튜브: https://www.youtube.com/@programgarden
- 실시간소통 오픈톡방: https://open.kakao.com/o/gKVObqUh

## 주요 특징

- **노드 기반 DSL**: 73 core nodes를 조합하여 워크플로우를 정의하는 도메인 특화 언어
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

## Node categories (11 categories, 71 core nodes)

| 카테고리 | 노드 수 | 대표 노드 |
|----------|---------|----------|
| infra | 8 | StartNode, BrokerNode, ThrottleNode, SplitNode, AggregateNode, IfNode, KoreaStockBrokerNode |
| account | 13 | AccountNode, OpenOrdersNode, RealAccountNode, RealOrderEventNode (해외주식/선물 + 국내주식) |
| market | 20 | MarketDataNode, HistoricalDataNode, RealMarketDataNode, WatchlistNode, ExclusionListNode, KoreaStock* |
| condition | 2 | ConditionNode, LogicNode |
| order | 10 | NewOrderNode, ModifyOrderNode, CancelOrderNode, PositionSizingNode (해외주식/선물 + 국내주식) |
| risk | 1 | PortfolioNode |
| schedule | 3 | ScheduleNode, TradingHoursFilterNode, SessionGateNode |
| data | 4 | SQLiteNode, HTTPRequestNode, FieldMappingNode, CodeNode |
| display | 6 | TableDisplayNode, LineChartNode, CandlestickChartNode, SummaryDisplayNode |
| analysis | 2 | BacktestEngineNode, BenchmarkCompareNode |
| ai | 2 | LLMModelNode, AIAgentNode |

> Community adds two nodes: TelegramNode and PerformanceReportNode, for 73 total.

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
├── nodes/          # 73 core node definitions
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

## Workflow PnL event contract

Futures workflow PnL events preserve native gross estimates separately from
accounting results. `workflow_*`, `other_*`, `total_*`, account and competition
monetary/rate scalars remain null when accounting evidence is unavailable.
`pnl_by_currency` contains gross price-change subtotals by contract currency;
`monetary_positions` retains their basis/status and unmodified, unconfirmed
`broker_pnl_amount`. No fee, FX, margin/equity return or verified contest score
is inferred from these estimates. Actual zero and negative amounts are retained.
`currency` is null for mixed or unavailable currencies. Consumers must handle
nullable monetary fields and must not coerce them to zero.

`WorkflowPnLEvent.personal_metrics` is an optional versioned envelope for retained
local workflow executions. Version 1 includes `scope` (kind, product, provider,
trading mode), timezone-aware `as_of`, `basis`, executed-order count/status,
per-symbol/exchange/currency realized amounts/status, and unavailable MDD.
It is unverified personal evidence, independent of whole-account contest results.
Stock realized amounts are stored long-only FIFO gross values excluding fees;
unknown currency stays null. Futures monetary values and portfolio MDD require
accounting evidence absent from this ledger and remain null. Consumers must
preserve null/status and use the latest cumulative observation, not sum dates.

## Workflow account boundary

Each workflow allows one account and one product through at most one broker
connection. Additional connections produce `DUPLICATE_BROKER_NODE`, including
unbound or cross-product nodes. Reuse one broker for all consumers. Account-free
workflows and unrelated credentials remain supported. See
[the shared contract](../../docs/workflow_account_policy.md).


## Cancellation result contract (unreleased P4)

CancelOrder metadata describes request acknowledgement (`accepted`,
`confirmation_pending=true`), not final cancellation. Replacement orders require
separate matching completion evidence. See
[the cancellation contract](../../docs/cancellation-acknowledgements.md).

Session windows and IfNode routing inside Split are described in
[Session gates and guarded Split](../../docs/session-gates-and-guarded-split.md).
