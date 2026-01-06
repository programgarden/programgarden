# ProgramGarden 오픈소스 구조

**강력하면서도 쉽게 쓸 수 있는 자동화매매 플랫폼**에 대해서 간략하게 설명합니다.

---

## 1. 구성 요소

* **ProgramGarden**\
  → 노드 기반 DSL(Domain Specific Language)을 제공하는 자동화 매매 라이브러리입니다.
* **ProgramGarden Core**\
  → 노드 타입, 플러그인 베이스 클래스, 레지스트리, 타입 정의, 에러 처리를 제공합니다.
* **ProgramGarden Finance**\
  → 증권사 API를 간편하게 사용할 수 있도록 지원하는 라이브러리입니다.
* **ProgramGarden Community**\
  → 시스템 트레이딩 생태계 발전에 기여하고자 하는 개발자들이 모여 만드는 커뮤니티 플러그인 공간입니다.

---

## 2. 5-Layer 아키텍처

ProgramGarden은 5개의 레이어로 구성된 아키텍처를 사용합니다:

```
┌─────────────────────────────────────────────────────────────────────────┐
│  1. REGISTRY LAYER (메타데이터)                                         │
│     "무엇을 쓸 수 있어?"                                                │
├─────────────────────────────────────────────────────────────────────────┤
│  • NodeTypeRegistry: BrokerNode, ConditionNode 등 노드 타입 스키마      │
│  • PluginRegistry: RSI, MACD, MarketOrder 등 플러그인 스키마            │
│  • AI가 "어떤 조건 노드 있어?" 질의 가능                                │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│  2. CREDENTIAL LAYER (인증/보안)                                        │
│     "어떤 계좌로 연결해?"                                               │
├─────────────────────────────────────────────────────────────────────────┤
│  • BrokerCredential: OpenAPI 앱키/시크릿키, 계좌번호                    │
│  • DBCredential: 외부 DB 연결 정보 (PostgreSQL, MySQL)               │
│  • Definition에서 직접 참조 안 함 → credential_id로만 참조              │
│  • 암호화 저장, AI에게 키 값은 노출 안 됨                               │
│  • secrets 네임스페이스로 참조: {{ secrets.mydb.password }}          │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│  3. DEFINITION LAYER (전략 정의)                                        │
│     "무엇을 할 건데?"                                                   │
├─────────────────────────────────────────────────────────────────────────┤
│  • WorkflowDefinition: 노드 + 엣지 구조                                 │
│  • 버전 관리, 재사용 가능                                               │
│  • AI가 생성/수정/검증                                                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│  4. JOB LAYER (실행 인스턴스)                                           │
│     "지금 뭘 하고 있어?"                                                │
├─────────────────────────────────────────────────────────────────────────┤
│  • WorkflowJob: 실행 상태, 런타임 컨텍스트                              │
│  • start/pause/resume/cancel 제어                                       │
│  • 같은 Definition으로 여러 Job 동시 실행 가능                          │
│  • Stateful: 포지션/잔고 상태 유지                                      │
│  • Graceful Restart: 상태 보존하며 전략 변경 가능                       │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│  5. EVENT LAYER (이벤트 히스토리)                                       │
│     "뭐가 일어났어?"                                                    │
├─────────────────────────────────────────────────────────────────────────┤
│  • 조건 평가 결과, 주문 체결, 에러 등 모든 이벤트 저장                  │
│  • AI가 "어제 왜 매수 안 했어?" 분석 가능                               │
│  • 백테스팅, 성과 분석 기반 데이터                                      │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. 노드 기반 DSL 개념

ProgramGarden은 **JSON 직렬화 가능한 노드 그래프** 기반의 DSL을 사용합니다.

### 핵심 구조

```json
{
  "nodes": [
    {"id": "broker", "type": "BrokerNode", ...},
    {"id": "rsi", "type": "ConditionNode", ...},
    {"id": "order", "type": "NewOrderNode", ...}
  ],
  "edges": [
    {"from": "broker.connection", "to": "rsi"},
    {"from": "rsi.passed_symbols", "to": "order.symbols"}
  ]
}
```

- **nodes**: 각 기능을 담당하는 노드들의 배열
- **edges**: 노드 간 데이터 흐름을 정의하는 연결

---

## 4. 노드 카테고리 (13개)

| Category | 용도 | 주요 노드 |
|----------|------|----------|
| `infra` | 시작점/증권사 연결 | StartNode, BrokerNode |
| `realtime` | WebSocket 실시간 | RealMarketDataNode, RealAccountNode, RealOrderEventNode |
| `data` | REST API/DB 조회·저장 | MarketDataNode, HistoricalDataNode, SQLiteNode, PostgresNode |
| `symbol` | 종목 소스/필터 | WatchlistNode, MarketUniverseNode, ScreenerNode |
| `trigger` | 스케줄/시간 필터 | ScheduleNode, TradingHoursFilterNode, ExchangeStatusNode |
| `condition` | 조건 평가/조합 | ConditionNode, LogicNode, PerformanceConditionNode |
| `risk` | 리스크 관리 | PositionSizingNode, RiskGuardNode |
| `order` | 주문 실행 | NewOrderNode, ModifyOrderNode, CancelOrderNode |
| `event` | 이벤트/알림 | EventHandlerNode, ErrorHandlerNode, AlertNode |
| `display` | 시각화 | DisplayNode |
| `group` | 서브플로우 | GroupNode |
| `backtest` | 백테스트 | BacktestExecutorNode, BacktestResultNode |
| `job` | Job 제어/배포 | DeployNode, JobControlNode |

---

## 5. 주요 노드 설명

### 5.1 인프라 노드 (infra)

| 노드 | 설명 |
|------|------|
| `StartNode` | 워크플로우 진입점 (Definition당 1개 필수) |
| `BrokerNode` | 증권사 연결 (provider, product, account) |

### 5.2 실시간 노드 (realtime)

| 노드 | 설명 |
|------|------|
| `RealMarketDataNode` | WebSocket 시세 스트림 (price, volume, bid/ask) |
| `RealAccountNode` | 실시간 계좌 정보 (보유종목, 예수금, 미체결, 실시간 수익률) |
| `RealOrderEventNode` | 실시간 주문 체결/거부/취소 이벤트 |

### 5.3 데이터 노드 (data)

| 노드 | 설명 |
|------|------|
| `MarketDataNode` | REST API 시세 조회 (일회성) |
| `HistoricalDataNode` | 과거 데이터 조회 (OHLCV) |
| `SQLiteNode` | 로컬 SQLite DB 저장/조회 (트레일링스탑 최고점 추적 등) |
| `PostgresNode` | 외부 PostgreSQL DB 연결 ({{ secrets.xxx }} 참조) |

### 5.4 조건 노드 (condition)

| 노드 | 설명 |
|------|------|
| `ConditionNode` | 조건 플러그인 실행 (RSI, MACD 등) |
| `LogicNode` | 조건 조합 (all/any/xor/at_least/weighted) |
| `PerformanceConditionNode` | 성과 기반 조건 (수익률, MDD, 승률 등) |

### 5.4 주문 노드 (order)

| 노드 | 설명 | Community 카테고리 |
|------|------|-------------------|
| `NewOrderNode` | 신규 주문 플러그인 실행 | `new_order_conditions/` |
| `ModifyOrderNode` | 정정 주문 플러그인 실행 | `modify_order_conditions/` |
| `CancelOrderNode` | 취소 주문 플러그인 실행 | `cancel_order_conditions/` |

---

## 6. 커뮤니티 플러그인

`programgarden_community` 패키지에서 50개 이상의 플러그인을 제공합니다.

### 플러그인 카테고리

| 카테고리 | 용도 | 예시 |
|----------|------|------|
| `strategy_conditions/` | 종목 조건 분석 | RSI, MACD, BollingerBands |
| `new_order_conditions/` | 신규 주문 전략 | MarketOrder, StockSplitFunds |
| `modify_order_conditions/` | 정정 주문 전략 | TrackingPriceModifier |
| `cancel_order_conditions/` | 취소 주문 전략 | PriceRangeCanceller, TimeStop |

### 플러그인 사용 방법

```json
{
  "id": "rsi",
  "type": "ConditionNode",
  "plugin": "RSI",
  "params": {"period": 14, "oversold": 30}
}
```

버전 지정이 필요한 경우:
```json
"plugin": "RSI@1.2.0"
```

---

## 7. 데이터 흐름

```
[WatchlistNode] ──symbols──▶ [RealMarketDataNode] ──price_data──▶ [ConditionNode]
                                                                        │
                                                                   passed_symbols
                                                                        ▼
[RealAccountNode] ──held_symbols──▶ [NewOrderNode] ◀──approved_symbols── [RiskGuardNode]
       │
  open_orders
       ▼
[ModifyOrderNode] / [CancelOrderNode]
```

모든 데이터 흐름은 **명시적 엣지로 통일**되어 그래프에서 한눈에 확인할 수 있습니다.

---

## 8. 패키지 관계도

```
┌─────────────────────────────────────────────────────────────┐
│                     programgarden                           │
│  (DSL 실행 엔진, 노드 오케스트레이터)                       │
└─────────────────────────────────────────────────────────────┘
              │                    │
              ▼                    ▼
┌─────────────────────┐  ┌─────────────────────────────────┐
│  programgarden_core │  │  programgarden_community        │
│  (노드/플러그인     │  │  (50+ 플러그인)                 │
│   베이스 클래스,    │  │  - strategy_conditions          │
│   레지스트리, 타입) │  │  - new_order_conditions         │
└─────────────────────┘  │  - modify_order_conditions      │
              │          │  - cancel_order_conditions      │
              ▼          └─────────────────────────────────┘
┌─────────────────────┐
│ programgarden_finance│
│ (LS증권 API 래퍼)   │
└─────────────────────┘
```

---

## 9. 다음 단계

- [비개발자 빠른 시작 가이드](non_dev_quick_guide.md) - 코딩 없이 자동매매 설정하기
- [DSL 커스터마이징 가이드](custom_dsl.md) - 개발자용 플러그인 제작
- [Logic 가이드](logic_guide.md) - 조건 조합 방법
- [Finance 가이드](finance_guide.md) - 증권사 API 직접 사용
- [오픈소스 기여 가이드](contribution_guide.md) - 플러그인 공유하기
