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
    {"id": "broker", "type": "BrokerNode", "credential_id": "my-broker-cred", ...},
    {"id": "rsi", "type": "ConditionNode", ...},
    {"id": "order", "type": "NewOrderNode", ...}
  ],
  "edges": [
    {"from": "broker", "to": "rsi"},
    {"from": "rsi", "to": "order"}
  ],
  "credentials": [
    {"id": "my-broker-cred", "type": "broker_ls", "name": "LS증권 API", "data": {"appkey": "", "appsecret": ""}}
  ]
}
```

- **nodes**: 각 기능을 담당하는 노드들의 배열
- **edges**: 노드 간 실행 순서를 정의하는 연결 (데이터 바인딩은 노드 config에서 표현식으로 처리)
- **credentials**: 워크플로우에서 사용하는 인증 정보 (공유 시 값은 빈 문자열)
- **inputs**: 워크플로우 입력 파라미터 (선택)

### Credentials 형식

워크플로우 JSON에 포함되는 credentials 섹션은 배열 형태입니다:

```json
{
  "credentials": [
    {
      "id": "broker-cred",
      "type": "broker_ls",
      "name": "LS증권 API",
      "data": {
        "appkey": "",
        "appsecret": "",
        "paper_trading": false
      }
    },
    {
      "id": "custom-api-cred",
      "type": "http_custom",
      "name": "외부 API 인증",
      "data": [
        {"type": "headers", "key": "Authorization", "value": "", "label": "API 토큰"},
        {"type": "query_params", "key": "api_key", "value": "", "label": "API Key"}
      ]
    }
  ]
}
```

**Credential 타입:**

| 타입 | 설명 | data 필드 |
|------|------|----------|
| `broker_ls` | LS증권 API | `appkey`, `appsecret`, `paper_trading` |
| `telegram` | 텔레그램 봇 | `bot_token`, `chat_id` |
| `postgres` | PostgreSQL DB | `host`, `port`, `database`, `username`, `password` |
| `http_custom` | 커스텀 HTTP 인증 | 배열: `[{type, key, value, label}, ...]` |
| `http_bearer` | Bearer Token | `token` |
| `http_header` | HTTP Header | `header_name`, `header_value` |
| `http_basic` | Basic Auth | `username`, `password` |

**공유용 vs 실행용:**
- **공유용 JSON**: `data` 필드에 키만 포함 (값은 빈 문자열)
- **실행용 JSON**: 서버에서 암호화된 값을 복호화하여 주입


### Expression 문법

노드 설정값을 동적으로 계산하거나 다른 노드의 데이터를 참조할 때 `{{ }}` 문법을 사용합니다:

```json
{
  "inputs": {
    "symbols": {"type": "symbol_list", "default": ["AAPL"]}
  },
  "nodes": [
    {
      "id": "watchlist",
      "symbols": "{{ input.symbols }}"
    },
    {
      "id": "marketData",
      "symbols": "{{ nodes.watchlist.symbols }}"
    },
    {
      "id": "condition",
      "price_data": "{{ nodes.marketData.price }}"
    },
    {
      "id": "order",
      "symbol": "{{ nodes.condition.passed_symbols[0] }}",
      "price": "{{ nodes.marketData.price * 0.99 }}"
    }
  ],
  "edges": [
    {"from": "watchlist", "to": "marketData"},
    {"from": "marketData", "to": "condition"},
    {"from": "condition", "to": "order"}
  ]
}
```

> 📖 **상세 가이드**: [Expression 가이드](expression_guide.md)

---

## 4. 노드 카테고리 (10개 - 금융 도메인 기준)

투자자가 직관적으로 이해할 수 있는 금융 용어 기반 분류입니다.

| Category | 용도 | 주요 노드 |
|----------|------|----------|
| `infra` | 워크플로우 시작점, 브로커 연결, 흐름 제어 | StartNode, BrokerNode, ThrottleNode |
| `account` | 잔고, 포지션, 체결 내역 | AccountNode, RealAccountNode, RealOrderEventNode |
| `market` | 시세, 종목 목록, 과거 데이터 | WatchlistNode, ScreenerNode, MarketDataNode, HistoricalDataNode, RealMarketDataNode |
| `condition` | 매매 조건 판단, 논리 연산 | ConditionNode, LogicNode |
| `order` | 신규/정정/취소 주문, 포지션 사이징 | NewOrderNode, ModifyOrderNode, CancelOrderNode, LiquidateNode, PositionSizingNode |
| `risk` | 리스크 관리, 포트폴리오 배분 | RiskGuardNode, RiskConditionNode, PortfolioNode |
| `schedule` | 시간 기반 트리거, 거래시간 필터 | ScheduleNode, TradingHoursFilterNode, ExchangeStatusNode |
| `data` | 외부 DB 및 API 연동 | SQLiteNode, PostgresNode, HTTPRequestNode |
| `analysis` | 백테스트, 차트, 성과 계산 | BacktestEngineNode, BenchmarkCompareNode, DisplayNode, CustomPnLNode |
| `system` | Job 제어, 알림, 서브플로우 | DeployNode, TradingHaltNode, JobControlNode |

---

## 5. 주요 노드 설명

### 5.1 인프라 노드 (infra)

| 노드 | 설명 |
|------|------|
| `StartNode` | 워크플로우 진입점 (Definition당 1개 필수) |
| `BrokerNode` | 증권사 연결 (provider, product, account) |
| `ThrottleNode` | 실시간 데이터 흐름 제어 (mode, interval_sec) |

### Connection 필수 노드

브로커 연결이 필요한 노드는 **반드시** `connection` 필드를 명시해야 합니다:

```json
{
  "id": "account",
  "type": "AccountNode",
  "connection": "{{ nodes.broker.connection }}"
}
```

| 카테고리 | 노드 |
|----------|------|
| account | `AccountNode`, `RealAccountNode`, `RealOrderEventNode` |
| market | `MarketDataNode`, `HistoricalDataNode`, `RealMarketDataNode` |
| order | `NewOrderNode`, `ModifyOrderNode`, `CancelOrderNode`, `LiquidateNode` |

> **중요**: 자동 브로커 감지 없음. 사용자가 명시적으로 connection 필드를 설정해야 합니다.

### 5.2 계좌 노드 (account)

| 노드 | 설명 |
|------|------|
| `AccountNode` | REST API 1회성 계좌 조회 (보유종목, 예수금, 미체결) |
| `RealAccountNode` | 실시간 계좌 정보 (보유종목, 예수금, 미체결, 실시간 수익률) |
| `RealOrderEventNode` | 실시간 주문 체결/거부/취소 이벤트 |

#### stay_connected 옵션

실시간 노드는 `stay_connected` 옵션으로 연결 유지 여부를 제어합니다:

| 옵션값 | 동작 |
|--------|------|
| `true` (기본값) | WebSocket 연결 유지, 플로우 끝나도 계속 살아있음 (Job.stop() 전까지) |
| `false` | WebSocket 연결, 플로우 끝나면 연결 종료 |

> ⚠️ **1회성 REST API 조회가 필요하면 `AccountNode`를 사용하세요.**

**ScheduleNode와 함께 사용 시:**
- `stay_connected: true`: 스케줄 사이에도 WebSocket 연결 유지, 틱마다 후속 노드 트리거
- `stay_connected: false`: 스케줄마다 WebSocket 연결 후 플로우 끝나면 종료, 다음 스케줄에 재연결

```json
{
  "id": "account",
  "type": "RealAccountNode",
  "category": "account",
  "stay_connected": true,
  "sync_interval_sec": 60
}
```

**RealAccountNode vs AccountNode:**

| 항목 | RealAccountNode | AccountNode |
|------|-----------------|-------------|
| 연결 방식 | WebSocket (실시간) | REST API (1회) |
| 사용 시점 | 실시간 수익률 모니터링 | 잔고 스냅샷 조회 |

**에러 처리:**

> ⚠️ **API 에러 발생 시 플로우가 즉시 중단됩니다.**
> - 보유종목/예수금 조회 실패 시 `RuntimeError` 발생
> - 빈 데이터로 플로우가 진행되면 잘못된 매매 의사결정 위험이 있어 이를 방지합니다
> - 에러 메시지는 실행 로그에 표시됩니다

```json
// 실시간 수익률 모니터링
{"id": "realAccount", "type": "RealAccountNode", "category": "account", "stay_connected": true}

// 1회성 잔고 조회
{"id": "account", "type": "AccountNode", "category": "account"}
```

### 5.3 시장 노드 (market)

| 노드 | 설명 |
|------|------|
| `WatchlistNode` | 사용자 정의 관심종목 리스트 |
| `MarketUniverseNode` | 시장/지수 구성 종목 (NASDAQ100, S&P500 등) |
| `ScreenerNode` | 조건부 종목 스크리닝 |
| `SymbolFilterNode` | 종목 리스트 집합 연산 |
| `MarketDataNode` | REST API 시세 조회 (일회성) |
| `HistoricalDataNode` | 과거 데이터 조회 (OHLCV) |
| `RealMarketDataNode` | WebSocket 실시간 시세 스트림 |

### 5.4 데이터 노드 (data)

| 노드 | 설명 |
|------|------|
| `SQLiteNode` | 로컬 SQLite DB 저장/조회 (트레일링스탑 최고점 추적 등) |
| `PostgresNode` | 외부 PostgreSQL DB 연결 ({{ secrets.xxx }} 참조) |
| `HTTPRequestNode` | 외부 REST API 호출 |

### 5.5 조건 노드 (condition)

| 노드 | 설명 |
|------|------|
| `ConditionNode` | 조건 플러그인 실행 (RSI, MACD 등) |
| `LogicNode` | 조건 조합 (all/any/xor/at_least/weighted) |

### 5.6 분석 노드 (analysis)

| 노드 | 설명 |
|------|------|
| `BacktestEngineNode` | OHLCV 데이터 기반 백테스트 시뮬레이션 실행 |
| `BenchmarkCompareNode` | 여러 백테스트 결과 비교 분석 (전략 vs 전략, 전략 vs Buy&Hold) |
| `DisplayNode` | 차트/테이블 시각화 (실시간 노드 연동 지원) |
| `CustomPnLNode` | 커스텀 손익 계산 (멀티계좌, 벤치마크 비교 등) |

**DisplayNode 차트 타입:**

| 차트 타입 | 필수 필드 | 설명 |
|----------|----------|------|
| `line` | `x_field`, `y_field` | 단일 라인 차트 |
| `multi_line` | `x_field`, `y_field`, `series_key` | 다중 라인 차트 (종목별) |
| `candlestick` | `x_field`, `open/high/low/close_field` | 캔들스틱 차트 |
| `bar` | `x_field`, `y_field` | 바 차트 |
| `equity_curve` | `x_field`, `y_field` | 자산곡선 |
| `table` | - | 테이블 (columns 지정) |

> ⚠️ **중요**: `line`, `multi_line`, `bar` 차트는 `x_field`와 `y_field`를 **명시적으로 지정**해야 합니다.

**DisplayNode 실시간 연동:**
- `RealMarketDataNode` → `DisplayNode`: 실시간 시세 테이블
- `RealAccountNode` → `DisplayNode`: 실시간 포지션/잔고 테이블
- 체결 발생 시 DisplayNode가 자동으로 재실행되어 최신 데이터 표시

**BacktestEngineNode 기능:**
- OHLCV 데이터 기반 수익률 시뮬레이션
- signals 없을 시 Buy & Hold 전략 자동 적용
- equity_curve (자산 곡선) 출력
- summary (성과 요약: 수익률, MDD 등) 출력

**확장 옵션:**

| 옵션 | 설명 | 예시 |
|------|------|------|
| `position_sizing` | 포지션 사이징 방법 | `equal_weight`, `kelly`, `fixed_percent`, `atr_based` |
| `position_sizing_config` | 사이징 세부 설정 | `{"kelly_fraction": 0.25, "max_position_percent": 10}` |
| `exit_rules` | 자동 청산 규칙 | `{"stop_loss_percent": 5, "take_profit_percent": 15}` |
| `allow_short` | 공매도 허용 | `true/false` |

```json
{
  "id": "backtest",
  "type": "BacktestEngineNode",
  "initial_capital": 10000,
  "commission_rate": 0.001,
  "position_sizing": "kelly",
  "position_sizing_config": {
    "kelly_fraction": 0.25,
    "max_position_percent": 10
  },
  "exit_rules": {
    "stop_loss_percent": 5,
    "take_profit_percent": 15,
    "trailing_stop_percent": 3
  }
}
```

### 5.6 포트폴리오 노드 (risk)

| 노드 | 설명 |
|------|------|
| `PortfolioNode` | 멀티 전략 자본 배분 및 리밸런싱 관리 |

**PortfolioNode 기능:**
- 여러 BacktestEngineNode 또는 PortfolioNode 결과 합산
- 자본 배분 방법 선택 (균등, 커스텀, 리스크 패리티, 모멘텀)
- 리밸런싱 규칙 설정 (주기적, 드리프트 기반)
- 계층적 포트폴리오 구성 (Portfolio of Portfolios)

**배분 방법:**

| 방법 | 설명 |
|------|------|
| `equal` | 균등 배분 |
| `custom` | 사용자 지정 비율 |
| `risk_parity` | 변동성 역비례 배분 |
| `momentum` | 최근 수익률 비례 배분 |

**리밸런싱 규칙:**

| 규칙 | 설명 |
|------|------|
| `none` | 리밸런싱 없음 |
| `periodic` | 주기적 (daily/weekly/monthly/quarterly) |
| `drift` | 드리프트 임계값 초과 시 |
| `both` | 주기적 + 드리프트 모두 적용 |

```json
{
  "id": "portfolio",
  "type": "PortfolioNode",
  "total_capital": 100000,
  "allocation_method": "risk_parity",
  "rebalance_rule": "drift",
  "drift_threshold": 5.0,
  "capital_sharing": true,
  "reserve_percent": 5.0
}
```

**계층적 포트폴리오 구조:**

```
BacktestEngine₁ ──┐
                  ├──▶ PortfolioNode (미국주식) ──┐
BacktestEngine₂ ──┘                               │
                                                  ├──▶ MasterPortfolio
BacktestEngine₃ ──┐                               │
                  ├──▶ PortfolioNode (해외선물) ──┘
BacktestEngine₄ ──┘
```

> ⚠️ **자본 상속**: 상위 PortfolioNode에서 배분을 받으면 하위의 `total_capital` 설정은 자동으로 무시됩니다.

### 5.7 주문 노드 (order)

| 노드 | 설명 |
|------|------|
| `NewOrderNode` | 신규 주문 실행 |
| `ModifyOrderNode` | 정정 주문 실행 |
| `CancelOrderNode` | 취소 주문 실행 |
| `LiquidateNode` | 포지션 청산 |
| `PositionSizingNode` | 포지션 크기 계산 (Kelly, 고정, ATR 기반) |

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
  "fields": {"period": 14, "oversold": 30}
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

## 8. 리소스 관리 시스템

ProgramGarden은 자동매매의 안정성을 위해 **적응형 리소스 관리 시스템**을 제공합니다.

### 8.1 개요

```
┌─────────────────────────────────────────────────────────────┐
│                ResourceContext (통합 관리)                  │
├─────────────────────────────────────────────────────────────┤
│  ResourceMonitor ──▶ ResourceLimiter ──▶ AdaptiveThrottle  │
│  (CPU/RAM/Disk)      (제한 검사)         (5-Level 조절)    │
└─────────────────────────────────────────────────────────────┘
```

### 8.2 JSON DSL에서 사용

```json
{
  "resource_limits": {
    "max_cpu_percent": 70,
    "max_memory_percent": 75,
    "max_workers": 2,
    "throttle_strategy": "conservative"
  },
  "nodes": [...],
  "edges": [...]
}
```

| 필드 | 기본값 | 설명 |
|------|--------|------|
| `max_cpu_percent` | 80 | 최대 CPU 사용률 (%) |
| `max_memory_percent` | 80 | 최대 메모리 사용률 (%) |
| `max_disk_percent` | 90 | 최대 디스크 사용률 (%) |
| `max_workers` | 4 | 동시 작업 수 |
| `throttle_strategy` | "gradual" | 스로틀 전략 (gradual, aggressive, conservative) |

### 8.3 5-Level 적응형 스로틀링

리소스 사용량에 따라 자동으로 실행 속도를 조절합니다:

| 레벨 | 트리거 | 동작 |
|------|--------|------|
| **NONE** | < 60% | 정상 실행 |
| **LIGHT** | 60-75% | 배치 크기 20% 감소 |
| **MODERATE** | 75-85% | 배치 크기 50% 감소, 지연 추가 |
| **HEAVY** | 85-95% | 동시 작업 50% 제한 |
| **CRITICAL** | > 95% | 신규 작업 일시 중지 (주문만 허용) |

> ⚠️ **주문 노드(NewOrderNode 등)는 CRITICAL 상태에서도 항상 우선 실행됩니다.**

### 8.4 플러그인 샌드박스

커뮤니티 플러그인은 **타임아웃 보호**를 받습니다:

```python
# 플러그인 리소스 힌트 (PR 리뷰어가 설정)
RSI_SCHEMA = PluginSchema(
    id="RSI",
    # ... 기존 필드 ...
    resource_hints={
        "max_execution_sec": 30.0,      # 30초 타임아웃
        "max_symbols_per_call": 100,    # 배치당 최대 100종목
        "cpu_intensive": True,          # CPU 집약적 작업
    },
    trust_level="verified",  # core, verified, community
)
```

| 신뢰 레벨 | 타임아웃 | 메모리 제한 | 종목 수 |
|----------|----------|------------|---------|
| `core` | 무제한 | 무제한 | 무제한 |
| `verified` | 60초 | 500MB | 500 |
| `community` | 30초 | 100MB | 100 |

### 8.5 자동 감지

`resource_limits`를 생략하면 시스템 리소스를 자동 감지합니다:

```python
import programgarden as pg

# 자동 감지 (권장)
job = pg.run(workflow)

# 또는 명시적 설정
from programgarden_core.models import ResourceLimits

job = pg.run(
    workflow,
    resource_limits=ResourceLimits(
        max_cpu_percent=70,
        max_memory_percent=75,
    )
)
```

---

## 9. 패키지 관계도

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

## 10. 다음 단계

- [노드 레퍼런스 가이드](node_reference.md) - 모든 노드의 상세 설명
- [비개발자 빠른 시작 가이드](non_dev_quick_guide.md) - 코딩 없이 자동매매 설정하기
- [DSL 커스터마이징 가이드](custom_dsl.md) - 개발자용 플러그인 제작
- [Logic 가이드](logic_guide.md) - 조건 조합 방법
- [Finance 가이드](finance_guide.md) - 증권사 API 직접 사용
- [오픈소스 기여 가이드](contribution_guide.md) - 플러그인 공유하기
