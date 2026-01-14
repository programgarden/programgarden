# 노드 레퍼런스 가이드

ProgramGarden에서 사용할 수 있는 모든 노드의 상세 설명입니다.

---

## 목차

1. [infra - 인프라/연결](#1-infra---인프라연결)
2. [realtime - 실시간 스트림](#2-realtime---실시간-스트림)
3. [data - 데이터 조회/저장](#3-data---데이터-조회저장)
4. [account - 계좌 조회](#4-account---계좌-조회)
5. [symbol - 종목 소스](#5-symbol---종목-소스)
6. [trigger - 스케줄/시간 필터](#6-trigger---스케줄시간-필터)
7. [condition - 조건 평가](#7-condition---조건-평가)
8. [risk - 리스크 관리](#8-risk---리스크-관리)
9. [order - 주문 실행](#9-order---주문-실행)
10. [event - 이벤트/알림](#10-event---이벤트알림)
11. [display - 시각화](#11-display---시각화)
12. [group - 서브플로우](#12-group---서브플로우)
13. [backtest - 백테스트](#13-backtest---백테스트)
14. [job - Job 제어](#14-job---job-제어)
15. [calculation - 계산](#15-calculation---계산)

---

## 1. infra - 인프라/연결

워크플로우의 시작점과 증권사 연결을 담당합니다.

### StartNode

워크플로우의 진입점입니다. 모든 워크플로우에 **반드시 1개** 있어야 합니다.

```json
{
  "id": "start",
  "type": "StartNode"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `id` | string | ✅ | 노드 고유 식별자 |
| `type` | "StartNode" | ✅ | 노드 타입 |

**출력**: `trigger` - 워크플로우 시작 신호

---

### BrokerNode

증권사 API에 연결합니다.

```json
{
  "id": "broker",
  "type": "BrokerNode",
  "provider": "ls-sec.co.kr",
  "product": "overseas_stock",
  "credential_id": "my-broker-cred"
}
```

| 필드 | 타입 | 필수 | 기본값 | 설명 |
|------|------|------|--------|------|
| `provider` | string | - | "ls-sec.co.kr" | 증권사 도메인 (현재 LS증권만 지원) |
| `product` | "overseas_stock" \| "overseas_futures" | - | "overseas_stock" | 상품 유형 (해외주식/해외선물) |
| `credential_id` | string | - | - | credentials 섹션의 ID 참조 |

> 💡 **상품별 특성**:
> - `overseas_stock`: 해외주식 (모의투자 미지원)
> - `overseas_futures`: 해외선물 (모의투자 지원)
>
> **모의투자 설정**: `paper_trading`은 credential의 `broker_ls.paper_trading`에서 관리됩니다.

**출력**: `connection` - 증권사 연결 객체

---

## 2. realtime - 실시간 스트림

WebSocket을 통한 실시간 데이터 스트림입니다.

### RealMarketDataNode

실시간 시세 데이터를 수신합니다. **BrokerNode의 connection 출력을 반드시 연결해야 합니다.**

```json
{
  "id": "realMarket",
  "type": "RealMarketDataNode",
  "connection": "{{ nodes.broker.connection }}",
  "symbols": "{{ nodes.watchlist.symbols }}",
  "stay_connected": true
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `connection` | object | ✅ | BrokerNode의 connection 출력 바인딩 |
| `symbols` | string[] | ✅ | 구독할 종목 코드 목록 |
| `stay_connected` | boolean | ❌ | 플로우 종료 후에도 연결 유지 (기본: true) |

**입력** (엣지 연결):
- BrokerNode → RealMarketDataNode: `connection` 자동 전달

**출력**:
- `price` - 현재가
- `volume` - 거래량
- `bid_ask` - 호가 정보

**stay_connected 동작**:
| 값 | 동작 |
|-----|------|
| `true` (기본) | 플로우 끝나도 WebSocket 유지 |
| `false` | 플로우 끝나면 WebSocket 종료 |

---

### RealAccountNode

실시간 계좌 정보를 수신합니다. **BrokerNode의 connection 출력을 반드시 연결해야 합니다.**

```json
{
  "id": "realAccount",
  "type": "RealAccountNode",
  "connection": "{{ nodes.broker.connection }}",
  "stay_connected": true,
  "sync_interval_sec": 60
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `connection` | object | ✅ | BrokerNode의 connection 출력 바인딩 |
| `stay_connected` | boolean | ❌ | 연결 유지 여부 (기본: true) |
| `sync_interval_sec` | number | ❌ | REST API 동기화 주기 (기본: 60초) |

**입력** (엣지 연결):
- BrokerNode → RealAccountNode: `connection` 자동 전달

**출력**:
- `held_symbols` - 보유종목 코드 리스트
- `balance` - 예수금/매수가능금액
- `open_orders` - 미체결 주문 목록
- `positions` - 보유종목 상세 (실시간 수익률 포함)

**positions 구조 예시**:
```json
{
  "AAPL": {
    "symbol": "AAPL",
    "quantity": 10,
    "buy_price": 185.50,
    "current_price": 190.25,
    "pnl_rate": 2.29
  }
}
```

---

### RealOrderEventNode

실시간 주문 이벤트를 수신합니다. **BrokerNode의 connection 출력을 반드시 연결해야 합니다.**

```json
{
  "id": "orderEvents",
  "type": "RealOrderEventNode",
  "connection": "{{ nodes.broker.connection }}",
  "product_type": "overseas_stock"
}
```

| 필드 | 타입 | 필수 | 기본값 | 설명 |
|------|------|------|--------|------|
| `connection` | object | ✅ | - | BrokerNode의 connection 출력 바인딩 |
| `product_type` | enum | ❌ | "overseas_stock" | 상품 유형 (overseas_stock, overseas_futures) |
| `event_filter` | enum | ❌ | "all" | 해외주식 이벤트 필터 (all, AS0~AS4) |
| `event_filter_futures` | enum | ❌ | "all" | 해외선물 이벤트 필터 (all, TC1~TC3) |
| `stay_connected` | boolean | ❌ | true | WebSocket 연결 유지 여부 |

**출력 (5개 포트)**:

| 포트 | 설명 | 이벤트 |
|------|------|--------|
| `accepted` | 주문 접수됨 | 신규/정정/취소 접수 |
| `filled` | 체결됨 | 주문 체결 |
| `modified` | 정정 완료 | 주문 정정 완료 |
| `cancelled` | 취소 완료 | 주문 취소 완료 |
| `rejected` | 거부됨 | 주문 거부 |

**이벤트 코드 매핑 (AS0 - 해외주식)**:
| sOrdxctPtnCode | 이벤트 | 출력 포트 |
|----------------|--------|----------|
| 01, 02, 03 | 접수 | `accepted` |
| 11 | 체결 | `filled` |
| 12 | 정정완료 | `modified` |
| 13 | 취소완료 | `cancelled` |
| 14 | 거부 | `rejected` |

**이벤트 코드 매핑 (TC2/TC3 - 해외선물)**:
| svc_id | ordr_ccd | 출력 포트 |
|--------|----------|----------|
| HO02 | 1 | `accepted` |
| HO02 | 2 | `modified` |
| HO02 | 3 | `cancelled` |
| HO03 | - | `rejected` |

---

## 3. data - 데이터 조회/저장

REST API와 데이터베이스 연동입니다.

### MarketDataNode

REST API로 1회성 시세 데이터를 조회합니다.

```json
{
  "id": "market",
  "type": "MarketDataNode",
  "config": {
    "symbols": ["AAPL", "NVDA"],
    "fields": ["price", "volume", "change"]
  }
}
```

**출력**: `data` - 요청한 시세 데이터

---

### HistoricalDataNode

과거 OHLCV 데이터를 조회합니다. **BrokerNode의 connection 출력을 반드시 연결해야 합니다.**

```json
{
  "id": "history",
  "type": "HistoricalDataNode",
  "connection": "{{ nodes.broker.connection }}",
  "symbols": ["AAPL"],
  "data_type": "daily",
  "count": 100
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `connection` | object | ✅ | BrokerNode의 connection 출력 바인딩 |
| `data_type` | "minute" \| "daily" \| "weekly" | ✅ | 데이터 주기 |
| `count` | number | ✅ | 가져올 데이터 개수 |

**입력** (엣지 연결):
- BrokerNode → HistoricalDataNode: `connection` 자동 전달

**출력**: `ohlcv` - OHLCV 데이터프레임

---

### SQLiteNode

로컬 SQLite 데이터베이스에 데이터를 저장/조회합니다.

```json
{
  "id": "sqlite",
  "type": "SQLiteNode",
  "config": {
    "table": "peak_tracker",
    "key_fields": ["symbol"],
    "save_fields": ["symbol", "peak_price"],
    "aggregations": {"peak_price": "max"}
  }
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `table` | string | ✅ | 테이블 이름 |
| `key_fields` | string[] | ✅ | 기본 키 필드 |
| `save_fields` | string[] | ✅ | 저장할 필드 |
| `aggregations` | object | ❌ | 집계 함수 (max, min, sum, avg) |

**사용 사례**: 트레일링 스탑의 최고점 추적

---

### PostgresNode

외부 PostgreSQL 데이터베이스에 연결합니다.

```json
{
  "id": "postgres",
  "type": "PostgresNode",
  "config": {
    "credential_id": "my-postgres-cred",
    "table": "trade_history",
    "key_fields": ["trade_id"]
  }
}
```

> ⚠️ 연결 정보는 credentials 섹션에 정의하고 `credential_id`로 참조합니다.

---

## 4. account - 계좌 조회

### AccountNode

REST API로 1회성 계좌 정보를 조회합니다. **BrokerNode의 connection 출력을 반드시 연결해야 합니다.**

```json
{
  "id": "account",
  "type": "AccountNode",
  "connection": "{{ nodes.broker.connection }}"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `connection` | object | ✅ | BrokerNode의 connection 출력 바인딩 |

**입력** (엣지 연결):
- BrokerNode → AccountNode: `connection` 자동 전달

**출력**:
- `held_symbols` - 보유종목 코드
- `balance` - 예수금
- `open_orders` - 미체결 주문

**RealAccountNode vs AccountNode**:
| 항목 | RealAccountNode | AccountNode |
|------|-----------------|-------------|
| 연결 방식 | WebSocket (실시간) | REST API (1회) |
| 사용 시점 | 실시간 모니터링 | 스냅샷 조회 |

---

## 5. symbol - 종목 소스

### WatchlistNode

사용자 정의 관심종목 리스트입니다. **BrokerNode의 connection 출력을 반드시 연결해야 합니다.**

```json
{
  "id": "watchlist",
  "type": "WatchlistNode",
  "connection": "{{ nodes.broker.connection }}",
  "symbols": [
    {"exchange": "NASDAQ", "symbol": "AAPL"},
    {"exchange": "NASDAQ", "symbol": "NVDA"}
  ]
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `connection` | object | ✅ | BrokerNode의 connection 출력 바인딩 |
| `symbols` | object[] | ✅ | 종목 목록 ({exchange, symbol}) |

**출력**: `symbols` - 종목 코드 리스트

---

### MarketUniverseNode

시장 전체 종목을 가져옵니다. **BrokerNode의 connection 출력을 반드시 연결해야 합니다.**

```json
{
  "id": "universe",
  "type": "MarketUniverseNode",
  "connection": "{{ nodes.broker.connection }}",
  "universe": "NASDAQ100"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `connection` | object | ✅ | BrokerNode의 connection 출력 바인딩 |
| `universe` | string | ✅ | 시장/인덱스 이름 |

| 지원 마켓 | 설명 |
|----------|------|
| `NASDAQ100` | 나스닥 100 종목 |
| `SP500` | S&P 500 종목 |
| `DOW30` | 다우존스 30 종목 |

---

### ScreenerNode

조건부 종목 스크리닝입니다. **BrokerNode의 connection 출력을 반드시 연결해야 합니다.**

```json
{
  "id": "screener",
  "type": "ScreenerNode",
  "connection": "{{ nodes.broker.connection }}",
  "filters": {
    "market_cap_min": 10000000000,
    "volume_min": 1000000
  },
  "universe": "ALL"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `connection` | object | ✅ | BrokerNode의 connection 출력 바인딩 |
| `filters` | object | ❌ | 스크리닝 조건 |
| `universe` | string | ❌ | 대상 시장 (기본: ALL) |

**출력**: `symbols` - 조건을 만족하는 종목 리스트

---

## 6. trigger - 스케줄/시간 필터

### ScheduleNode

크론 스케줄에 따라 워크플로우를 트리거합니다.

```json
{
  "id": "schedule",
  "type": "ScheduleNode",
  "config": {
    "cron": "0 */15 9-16 * * mon-fri",
    "timezone": "America/New_York"
  }
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `cron` | string | ✅ | 크론 표현식 (5/6/7 필드) |
| `timezone` | string | ✅ | 타임존 |
| `enabled` | boolean | ❌ | 활성화 여부 (기본: true) |

**크론 표현식 예시**:
| 표현식 | 설명 |
|--------|------|
| `0 30 9 * * *` | 매일 09:30 |
| `0 */15 9-16 * * mon-fri` | 평일 9-16시 15분마다 |
| `0 0 9 * * mon` | 매주 월요일 09:00 |

> 📖 상세 가이드: [스케줄 설정 가이드](schedule_guide.md)

---

### TradingHoursFilterNode

거래시간 필터입니다. **거래시간 외에는 대기하다가 거래시간 시작 시 통과**합니다.

```json
{
  "id": "tradingHours",
  "type": "TradingHoursFilterNode",
  "config": {
    "start": "09:30",
    "end": "16:00",
    "timezone": "America/New_York",
    "days": ["mon", "tue", "wed", "thu", "fri"]
  }
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `start` | string | ✅ | 시작 시간 (HH:MM) |
| `end` | string | ✅ | 종료 시간 (HH:MM) |
| `timezone` | string | ✅ | 타임존 |
| `days` | string[] | ✅ | 활성 요일 |

**동작 방식**:

```
┌─────────────────────────────────────────────────────────────┐
│  TradingHoursFilterNode 동작                                │
├─────────────────────────────────────────────────────────────┤
│  1. 거래시간 내: 즉시 통과 ({"passed": true})               │
│                                                             │
│  2. 거래시간 외:                                            │
│     • 1분마다 체크하며 blocking 대기                        │
│     • 거래시간 시작 시 통과                                 │
│                                                             │
│  3. shutdown 요청 시:                                       │
│     • graceful 종료 ({"passed": false, "reason": "shutdown"})│
└─────────────────────────────────────────────────────────────┘
```

| 상황 | 반환값 |
|------|--------|
| 거래시간 내 | `{"passed": true}` |
| 거래시간 시작 후 | `{"passed": true}` |
| shutdown 요청 | `{"passed": false, "reason": "shutdown"}` |

> ⚠️ **주의**: 거래시간 외에 워크플로우 시작 시 **blocking으로 대기**합니다. ScheduleNode와 조합 사용을 권장합니다.

---

### ExchangeStatusNode

거래소 상태를 체크합니다. **BrokerNode의 connection 출력을 반드시 연결해야 합니다.**

```json
{
  "id": "exchangeStatus",
  "type": "ExchangeStatusNode",
  "connection": "{{ nodes.broker.connection }}",
  "exchange": "NYSE"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `connection` | object | ✅ | BrokerNode의 connection 출력 바인딩 |
| `exchange` | string | ✅ | 거래소 코드 (NYSE, NASDAQ 등) |

**출력**: `status` - 거래소 상태 (open, closed, holiday)

---

## 7. condition - 조건 평가

### ConditionNode

플러그인 기반 조건을 평가합니다.

```json
{
  "id": "rsi",
  "type": "ConditionNode",
  "plugin": "RSI",
  "fields": {
    "period": 14,
    "oversold": 30,
    "overbought": 70
  }
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `plugin` | string | ✅ | 플러그인 ID |
| `fields` | object | ❌ | 플러그인 파라미터 |

**출력**:
- `passed` - 조건 통과 여부
- `passed_symbols` - 조건을 통과한 종목 리스트
- `analysis` - 분석 데이터 (플러그인별 상이)

**사용 가능한 플러그인**:
| 플러그인 | 설명 | 주요 파라미터 |
|----------|------|---------------|
| `RSI` | 상대강도지수 | period, oversold, overbought |
| `MACD` | 이동평균수렴확산 | fast, slow, signal |
| `BollingerBands` | 볼린저밴드 | period, num_std |
| `VolumeSpike` | 거래량 급증 | threshold_ratio |
| `ProfitTarget` | 익절 조건 | target_percent |
| `StopLoss` | 손절 조건 | loss_percent |

> 📖 전체 플러그인 목록: [조건 플러그인 목록](strategies/stock_condition.md)

---

### LogicNode

여러 조건을 조합합니다.

```json
{
  "id": "logic",
  "type": "LogicNode",
  "config": {
    "operator": "all",
    "conditions": ["rsi", "macd"]
  }
}
```

| 연산자 | 설명 | threshold |
|--------|------|-----------|
| `all` | 모든 조건 만족 (AND) | ❌ |
| `any` | 하나 이상 만족 (OR) | ❌ |
| `not` | 모든 조건 불만족 | ❌ |
| `xor` | 정확히 하나만 만족 | ❌ |
| `at_least` | N개 이상 만족 | ✅ |
| `at_most` | N개 이하 만족 | ✅ |
| `exactly` | 정확히 N개 만족 | ✅ |
| `weighted` | 가중치 합이 threshold 이상 | ✅ |

> 📖 상세 가이드: [Logic 가이드](logic_guide.md)

---

## 8. risk - 리스크 관리

### PositionSizingNode

포지션 크기를 계산합니다.

```json
{
  "id": "sizing",
  "type": "PositionSizingNode",
  "config": {
    "method": "percent",
    "value": 10
  }
}
```

| 방법 | 설명 |
|------|------|
| `fixed` | 고정 금액 |
| `percent` | 총 자산의 N% |
| `kelly` | 켈리 공식 |
| `atr` | ATR 기반 |

---

### RiskGuardNode

리스크 한도를 체크합니다.

```json
{
  "id": "guard",
  "type": "RiskGuardNode",
  "config": {
    "max_loss_percent": 5,
    "max_positions": 10,
    "max_consecutive_losses": 3
  }
}
```

**출력**: `approved` - 리스크 한도 내 여부

---

### PortfolioNode

멀티 전략 포트폴리오를 관리합니다.

```json
{
  "id": "portfolio",
  "type": "PortfolioNode",
  "config": {
    "total_capital": 100000,
    "allocation_method": "risk_parity",
    "rebalance_rule": "drift",
    "drift_threshold": 5.0
  }
}
```

| 배분 방법 | 설명 |
|----------|------|
| `equal` | 균등 배분 |
| `custom` | 사용자 지정 |
| `risk_parity` | 변동성 역비례 |
| `momentum` | 수익률 비례 |

---

## 9. order - 주문 실행

### NewOrderNode

신규 주문을 실행합니다.

```json
{
  "id": "order",
  "type": "NewOrderNode",
  "plugin": "StockSplitFunds",
  "fields": {
    "percent_balance": 10
  }
}
```

| 플러그인 | 설명 |
|----------|------|
| `MarketOrder` | 시장가 주문 |
| `LimitOrder` | 지정가 주문 |
| `StockSplitFunds` | 분할 매수 |

> 📖 전체 플러그인 목록: [주문 플러그인 목록](strategies/order_condition.md)

---

### ModifyOrderNode

미체결 주문을 정정합니다.

```json
{
  "id": "modify",
  "type": "ModifyOrderNode",
  "plugin": "TrackingPriceModifier"
}
```

---

### CancelOrderNode

미체결 주문을 취소합니다.

```json
{
  "id": "cancel",
  "type": "CancelOrderNode",
  "plugin": "TimeStopCanceller"
}
```

---

## 10. event - 이벤트/알림

### EventHandlerNode

주문 이벤트를 처리합니다.

```json
{
  "id": "handler",
  "type": "EventHandlerNode",
  "config": {
    "event": "onOrderFilled",
    "action": "log"
  }
}
```

---

### AlertNode

알림을 발송합니다.

```json
{
  "id": "alert",
  "type": "AlertNode",
  "config": {
    "channel": "telegram",
    "credential_id": "my-telegram-cred",
    "message": "{{ nodes.order.symbol }} 체결 완료"
  }
}
```

| 채널 | 설명 |
|------|------|
| `telegram` | 텔레그램 봇 |
| `slack` | 슬랙 웹훅 |
| `discord` | 디스코드 웹훅 |
| `email` | 이메일 |

---

## 11. display - 시각화

### DisplayNode

차트/테이블을 생성합니다.

```json
{
  "id": "chart",
  "type": "DisplayNode",
  "config": {
    "chart_type": "candlestick",
    "data": "{{ nodes.history.ohlcv }}"
  }
}
```

| 차트 타입 | 설명 |
|----------|------|
| `line` | 라인 차트 |
| `candlestick` | 캔들스틱 차트 |
| `bar` | 바 차트 |
| `table` | 테이블 |

---

## 12. group - 서브플로우

### GroupNode

재사용 가능한 서브플로우를 정의합니다.

```json
{
  "id": "subflow",
  "type": "GroupNode",
  "config": {
    "nodes": [...],
    "edges": [...],
    "inputs": ["symbols"],
    "outputs": ["passed_symbols"]
  }
}
```

**사용 사례**: 반복되는 조건 로직을 모듈화

---

## 13. backtest - 백테스트

### BacktestEngineNode

백테스트를 실행합니다.

```json
{
  "id": "backtest",
  "type": "BacktestEngineNode",
  "config": {
    "initial_capital": 10000,
    "commission_rate": 0.001,
    "position_sizing": "kelly",
    "exit_rules": {
      "stop_loss_percent": 5,
      "take_profit_percent": 15
    }
  }
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `initial_capital` | number | 초기 자본 |
| `commission_rate` | number | 수수료율 |
| `position_sizing` | string | 포지션 사이징 방법 |
| `exit_rules` | object | 자동 청산 규칙 |

**출력**:
- `equity_curve` - 자산 곡선
- `summary` - 성과 요약 (수익률, MDD, 승률 등)

---

## 14. job - Job 제어

### DeployNode

워크플로우를 배포합니다.

```json
{
  "id": "deploy",
  "type": "DeployNode",
  "config": {
    "environment": "production"
  }
}
```

---

### JobControlNode

실행 중인 Job을 제어합니다.

```json
{
  "id": "control",
  "type": "JobControlNode",
  "config": {
    "action": "pause"
  }
}
```

| 액션 | 설명 |
|------|------|
| `pause` | 일시 정지 |
| `resume` | 재개 |
| `stop` | 종료 |

---

## 15. calculation - 계산

### PnLCalculatorNode

손익을 계산합니다.

```json
{
  "id": "pnl",
  "type": "PnLCalculatorNode",
  "config": {
    "mode": "realtime"
  }
}
```

| 모드 | 설명 |
|------|------|
| `realtime` | 실시간 계산 |
| `snapshot` | 스냅샷 기준 |

---

## 부록: 노드 카테고리 요약

| 카테고리 | 용도 | 주요 노드 |
|----------|------|----------|
| `infra` | 시작/연결 | StartNode, BrokerNode |
| `realtime` | 실시간 스트림 | RealMarketDataNode, RealAccountNode |
| `data` | 조회/저장 | MarketDataNode, HistoricalDataNode, SQLiteNode |
| `account` | 계좌 조회 | AccountNode |
| `symbol` | 종목 소스 | WatchlistNode, ScreenerNode |
| `trigger` | 스케줄/시간 | ScheduleNode, TradingHoursFilterNode |
| `condition` | 조건 평가 | ConditionNode, LogicNode |
| `risk` | 리스크 관리 | PositionSizingNode, RiskGuardNode, PortfolioNode |
| `order` | 주문 실행 | NewOrderNode, ModifyOrderNode, CancelOrderNode |
| `event` | 이벤트/알림 | EventHandlerNode, AlertNode |
| `display` | 시각화 | DisplayNode |
| `group` | 서브플로우 | GroupNode |
| `backtest` | 백테스트 | BacktestEngineNode |
| `job` | Job 제어 | DeployNode, JobControlNode |
| `calculation` | 계산 | PnLCalculatorNode |

---

## 다음 단계

- [구조 문서](structure.md) - 5-Layer 아키텍처 이해하기
- [플러그인 개발](custom_dsl.md) - 커스텀 플러그인 만들기
- [Logic 가이드](logic_guide.md) - 조건 조합 방법
- [스케줄 가이드](schedule_guide.md) - 크론 표현식 작성법
