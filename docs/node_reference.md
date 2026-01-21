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

### ThrottleNode

실시간 데이터 흐름을 제어하여 하위 노드의 과도한 실행을 방지합니다.

```json
{
  "id": "throttle",
  "type": "ThrottleNode",
  "mode": "latest",
  "interval_sec": 5,
  "pass_first": true
}
```

| 필드 | 타입 | 필수 | 기본값 | 설명 |
|------|------|------|--------|------|
| `mode` | `"skip"` \| `"latest"` | ❌ | `"latest"` | 쿨다운 중 데이터 처리 방식 |
| `interval_sec` | number | ❌ | `5` | 최소 실행 간격 (초), 범위: 0.1~300 |
| `pass_first` | boolean | ❌ | `true` | 첫 번째 데이터 즉시 통과 여부 |

**모드 설명**:

| 모드 | 동작 | 사용 케이스 |
|------|------|------------|
| `skip` | 쿨다운 중 들어오는 데이터 무시 | 단순히 실행 빈도만 줄이고 싶을 때 |
| `latest` | 쿨다운 중 최신 데이터만 보관, 쿨다운 끝나면 실행 | 항상 최신 상태 반영이 중요할 때 (권장) |

**입력**: 상위 노드의 모든 출력 (투명 전달)

**출력**:
- 입력받은 데이터 그대로 출력 (투명 프록시)
- `_throttle_stats` - 쓰로틀 통계 `{skipped_count, countdown_sec, last_passed_at}`

**사용 예시**:

```
RealAccountNode ──(빈번한 이벤트)──▶ ThrottleNode ──(5초마다)──▶ ConditionNode ──▶ OrderNode
```

> ⚠️ **주의**: `_throttled: true`가 반환되면 하위 노드 실행이 중단됩니다.

**latest 모드 동작**:
```
시간 →  0s    1s    2s    3s    4s    5s    6s
이벤트    A     B     C     D     -     E     F
통과     A    skip  skip  skip         D*    E
              (최신 보관)              쿨다운 끝나면 D 실행
```

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
- `price` - 현재가 `{symbol: price}`
- `volume` - 거래량 `{symbol: volume}`
- `data` - 전체 데이터 `{symbol: {symbol, exchange, price, volume, bid, ask}}`
- `bid` - 매수호가
- `ask` - 매도호가

**실시간 업데이트**: 체결 발생 시 출력 데이터가 자동으로 업데이트되며, 연결된 DisplayNode도 함께 갱신됩니다.

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

**에러 처리**:

> ⚠️ **중요**: API 에러 발생 시 플로우가 즉시 중단됩니다.
>
> - 보유종목/예수금 조회 실패 시 `RuntimeError` 발생
> - 빈 데이터로 플로우가 진행되면 잘못된 매매 의사결정 위험이 있어 이를 방지합니다
> - 에러 메시지는 실행 로그에 표시됩니다

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

### MarketDataNode (현재가조회)

REST API로 **당일 현재가/거래량**을 조회합니다. 과거 N일 데이터가 필요하면 **HistoricalDataNode**를 사용하세요.

```json
{
  "id": "market",
  "type": "MarketDataNode",
  "connection": "{{ nodes.broker.connection }}",
  "symbols": [
    {"exchange": "NASDAQ", "symbol": "AAPL"},
    {"exchange": "NYSE", "symbol": "IBM"}
  ]
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `connection` | object | ✅ | BrokerNode의 connection 출력 바인딩 |
| `symbols` | array | ✅ | 종목 리스트 (거래소 + 심볼) |

> ⚠️ **MarketDataNode vs HistoricalDataNode**
> - **MarketDataNode**: 당일 현재가 1개 (g3101 API)
> - **HistoricalDataNode**: N일치 일봉/주봉/월봉 (g3103 API)

**출력**: 
- `values` - 종목별 시세 데이터 배열

```json
{
  "values": [
    {
      "symbol": "AAPL",
      "exchange": "NASDAQ",
      "price": 192.30,
      "change": 1.50,
      "change_pct": 0.79,
      "volume": 45123456,
      "open": 190.50,
      "high": 193.20,
      "low": 189.80,
      "close": 192.30
    }
  ]
}
```

---

### HistoricalDataNode (과거차트조회)

과거 N일치 OHLCV 차트 데이터를 조회합니다. **BrokerNode의 connection 출력을 반드시 연결해야 합니다.**

```json
{
  "id": "history",
  "type": "HistoricalDataNode",
  "connection": "{{ nodes.broker.connection }}",
  "symbols": ["AAPL"],
  "interval": "1d",
  "start_date": "{{ days_ago_yyyymmdd(500) }}",
  "end_date": "{{ today_yyyymmdd() }}"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `connection` | object | ✅ | BrokerNode의 connection 출력 바인딩 |
| `interval` | "1d" \| "1w" \| "1M" | - | 데이터 주기 (일봉/주봉/월봉) |
| `start_date` | string | - | 시작일 (YYYY-MM-DD 또는 {{ days_ago_yyyymmdd(N) }}) |
| `end_date` | string | - | 종료일 (YYYY-MM-DD 또는 {{ today_yyyymmdd() }}) |

**입력** (엣지 연결):
- BrokerNode → HistoricalDataNode: `connection` 자동 전달

**출력**: `ohlcv_data` - N개 OHLCV 리스트 `{symbol: [{date, open, high, low, close, volume}, ...]}`

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

글로벌 대표 지수의 구성 종목을 가져옵니다.

> ⚠️ **해외주식(overseas_stock) 전용** 노드입니다. 해외선물은 지원하지 않습니다.
>
> 💡 **Broker 연결 불필요**: pytickersymbols 라이브러리를 사용하여 독립적으로 실행됩니다.

```json
{
  "id": "universe",
  "type": "MarketUniverseNode",
  "universe": "NASDAQ100"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `universe` | string | ✅ | 인덱스 이름 |

**지원 인덱스 (미국 거래소):**

| 인덱스 | 설명 |
|--------|------|
| `NASDAQ100` | 나스닥 100 (~101개) |
| `SP500` | S&P 500 (~503개) |
| `SP100` | S&P 100 |
| `DOW30` | 다우존스 30 |

> 💡 pytickersymbols 라이브러리는 유럽/아시아 인덱스도 지원하지만, LS증권에서 거래 가능한 미국 인덱스만 권장합니다.

**출력**:
- `symbols` - 종목 리스트 `[{exchange, symbol, name}, ...]`
- `count` - 종목 수

---

### ScreenerNode

조건부 종목 스크리닝입니다.

> ⚠️ **해외주식(overseas_stock) 전용** 노드입니다. 해외선물은 `SymbolQueryNode`를 사용하세요.
>
> 💡 **Broker 연결 불필요**: yfinance 라이브러리를 사용하여 독립적으로 실행됩니다.

```json
{
  "id": "screener",
  "type": "ScreenerNode",
  "market_cap_min": 100000000000,
  "volume_min": 1000000,
  "sector": "Technology",
  "exchange": "NASDAQ",
  "max_results": 10,
  "symbols": "{{ nodes.watchlist.symbols }}"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `symbols` | expression | ❌ | 입력 종목 리스트 (예: `{{ nodes.watchlist.symbols }}`) |
| `market_cap_min` | number | ❌ | 최소 시가총액 (USD) |
| `market_cap_max` | number | ❌ | 최대 시가총액 (USD) |
| `volume_min` | number | ❌ | 최소 거래량 |
| `sector` | string | ❌ | 섹터 필터 (Technology, Healthcare 등) |
| `exchange` | string | ❌ | 거래소 필터 (NASDAQ, NYSE, AMEX) |
| `max_results` | number | ❌ | 최대 결과 수 (기본: 20) |

**거래소 매핑** (yfinance 코드 → 표준 이름):
| yfinance | 표준명 |
|----------|--------|
| NMS, NGM, NCM | NASDAQ |
| NYQ | NYSE |
| ASE | AMEX |

**출력**:
- `symbols` - 조건을 만족하는 종목 리스트 `[{exchange, symbol, market_cap, volume, sector}, ...]`
- `count` - 결과 종목 수

> 📦 **의존성**: yfinance 라이브러리 사용 (`pip install yfinance`)

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

## 7. condition - 조건 평가

### ConditionNode

플러그인 기반 조건을 평가합니다.

```json
{
  "id": "rsi",
  "type": "ConditionNode",
  "plugin": "RSI",
  "data": "{{ flatten(nodes.historicaldata_1.values, 'time_series') }}",
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
| `data` | expression | 조건부 | OHLCV 데이터 바인딩 (시계열 플러그인용) |
| `positions` | expression | 조건부 | 포지션 데이터 바인딩 (익절/손절 플러그인용) |
| `fields` | object | ❌ | 플러그인 파라미터 |

**플러그인별 필수 입력**:

| 플러그인 타입 | 필수 입력 | 예시 플러그인 |
|--------------|----------|--------------|
| 시계열 기반 | `data` | RSI, MACD, BollingerBands, VolumeSpike |
| 포지션 기반 | `positions` | ProfitTarget (v3.0.0), StopLoss (v3.0.0) |

**출력**:
- `passed` - 조건 통과 여부
- `passed_symbols` - 조건을 통과한 종목 리스트
- `analysis` - 분석 데이터 (플러그인별 상이)

**시계열 기반 플러그인** (`data` 필수):
| 플러그인 | 설명 | 주요 파라미터 |
|----------|------|---------------|
| `RSI` | 상대강도지수 | period, oversold, overbought |
| `MACD` | 이동평균수렴확산 | fast, slow, signal |
| `BollingerBands` | 볼린저밴드 | period, num_std |
| `VolumeSpike` | 거래량 급증 | threshold_ratio |

**포지션 기반 플러그인** (`positions` 필수) - v3.0.0:
| 플러그인 | 설명 | 주요 파라미터 |
|----------|------|---------------|
| `ProfitTarget` | 익절 조건 | target_percent |
| `StopLoss` | 손절 조건 | loss_percent |

> **v3.0.0**: ProfitTarget/StopLoss는 `positions` 데이터만 필요합니다. positions에 `pnl_rate` 필드가 포함되어 있어야 합니다.

**익절/손절 조건 예시**:
```json
{
  "id": "profitTarget",
  "type": "ConditionNode",
  "plugin": "ProfitTarget",
  "positions": "{{ nodes.realAccount.positions }}",
  "fields": {
    "target_percent": 5.0
  }
}
```

> 📖 전체 플러그인 목록: [조건 플러그인 목록](strategies/stock_condition.md)

---

### LogicNode

여러 조건을 조합합니다.

```json
{
  "id": "logic",
  "type": "LogicNode",
  "operator": "all",
  "conditions": [
    {
      "is_condition_met": "{{ nodes.rsiCondition.result }}",
      "passed_symbols": "{{ nodes.rsiCondition.passed_symbols }}"
    },
    {
      "is_condition_met": "{{ nodes.macdCondition.result }}",
      "passed_symbols": "{{ nodes.macdCondition.passed_symbols }}"
    }
  ]
}
```

| 필드 | 타입 | 필수 | 기본값 | 표시 조건 | 설명 |
|------|------|:----:|--------|----------|------|
| `operator` | enum | ✅ | `"all"` | 항상 | 논리 연산자 |
| `threshold` | number | ❌ | - | `at_least`, `at_most`, `exactly`, `weighted` 선택 시 | 임계값 |
| `conditions` | array | ✅ | `[]` | 항상 | 조건 목록 (객체 배열) |

**conditions 배열 항목 구조:**

| 필드 | 타입 | 필수 | 설명 |
|------|------|:----:|------|
| `is_condition_met` | expression | ✅ | 조건 통과 여부 (`{{ nodes.xxx.result }}`) |
| `passed_symbols` | expression | ✅ | 통과한 종목 목록 (`{{ nodes.xxx.passed_symbols }}`) |
| `weight` | number | ❌ | 가중치 (기본: 1.0, `weighted` 연산자에서만 사용) |

**연산자별 설명:**

| 연산자 | 설명 | threshold 필요 |
|--------|------|:--------------:|
| `all` | 모든 조건 만족 (AND) | ❌ |
| `any` | 하나 이상 만족 (OR) | ❌ |
| `not` | 모든 조건 불만족 | ❌ |
| `xor` | 정확히 하나만 만족 | ❌ |
| `at_least` | N개 이상 만족 | ✅ (정수) |
| `at_most` | N개 이하 만족 | ✅ (정수) |
| `exactly` | 정확히 N개 만족 | ✅ (정수) |
| `weighted` | 가중치 합이 threshold 이상 | ✅ (0~1 소수) |

**weighted 연산자 사용 시 conditions에 weight 포함:**

```json
{
  "id": "logic",
  "type": "LogicNode",
  "operator": "weighted",
  "threshold": 0.6,
  "conditions": [
    {
      "is_condition_met": "{{ nodes.rsiCondition.result }}",
      "passed_symbols": "{{ nodes.rsiCondition.passed_symbols }}",
      "weight": 0.4
    },
    {
      "is_condition_met": "{{ nodes.macdCondition.result }}",
      "passed_symbols": "{{ nodes.macdCondition.passed_symbols }}",
      "weight": 0.35
    },
    {
      "is_condition_met": "{{ nodes.bollingerCondition.result }}",
      "passed_symbols": "{{ nodes.bollingerCondition.passed_symbols }}",
      "weight": 0.25
    }
  ]
}
```

- `weight` 값: 0~1 사이 소수 (0.4 = 40%)
- 가중치 합계를 1.0으로 맞추면 threshold를 백분율로 해석 가능
- `weight` 미지정 시 기본값 1.0

> 📖 상세 가이드: [Logic 가이드](logic_guide.md#weighted-가중치-합산)

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

차트/테이블을 생성합니다. **실시간 노드(RealMarketDataNode, RealAccountNode)와 연결하면 데이터가 실시간으로 업데이트됩니다.**

```json
{
  "id": "chart",
  "type": "DisplayNode",
  "chart_type": "line",
  "title": "RSI 시계열",
  "data": "{{ flatten(nodes.rsiCondition.values, 'time_series') }}",
  "x_field": "date",
  "y_field": "rsi"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `chart_type` | string | ❌ | 차트 유형 (기본: table) |
| `title` | string | ❌ | 차트 제목 |
| `data` | expression | ✅ | 차트 데이터 (배열) |
| `x_field` | string | ⚠️ | X축 필드명 (line/multi_line/bar **필수**) |
| `y_field` | string | ⚠️ | Y축 필드명 (line/multi_line/bar **필수**) |
| `series_key` | string | ❌ | multi_line에서 시리즈 구분 키 |
| `columns` | string[] | ❌ | table에서 표시할 컬럼 |

| 차트 타입 | 필수 필드 | 설명 |
|----------|----------|------|
| `line` | `x_field`, `y_field` | 단일 라인 차트 |
| `multi_line` | `x_field`, `y_field`, `series_key` | 다중 라인 차트 (종목별) |
| `candlestick` | `x_field`, `open_field`, `high_field`, `low_field`, `close_field` | 캔들스틱 차트 |
| `bar` | `x_field`, `y_field` | 바 차트 |
| `equity_curve` | `x_field`, `y_field` | 자산곡선 (benchmark_field 선택) |
| `table` | - | 테이블 (columns로 컬럼 지정) |

> ⚠️ **중요**: `line`, `multi_line`, `bar` 차트는 `x_field`와 `y_field`를 **명시적으로 지정**해야 합니다. 자동 추론은 지원하지 않습니다.

**실시간 데이터 연동**:

DisplayNode는 실시간 노드와 연결 시 자동으로 데이터를 갱신합니다:

```
RealMarketDataNode ──data──▶ DisplayNode (실시간 시세 테이블)
RealAccountNode ──positions──▶ DisplayNode (실시간 포지션 테이블)
```

| 소스 노드 | 지원 출력 포트 | 용도 |
|----------|---------------|------|
| `RealMarketDataNode` | `data`, `price`, `volume` | 실시간 시세 표시 |
| `RealAccountNode` | `positions`, `balance` | 실시간 포지션/잔고 표시 |
| `BacktestEngineNode` | `equity_curve`, `summary` | 백테스트 결과 차트 |

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

### BenchmarkCompareNode

여러 백테스트 결과를 비교 분석합니다.

```json
{
  "id": "compare",
  "type": "BenchmarkCompareNode",
  "strategies": [
    "{{ nodes.backtestRSI }}",
    "{{ nodes.backtestSPY }}"
  ],
  "ranking_metric": "sharpe"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `strategies` | array | ✅ | BacktestEngineNode 출력 배열 (바인딩) |
| `ranking_metric` | string | ❌ | 순위 기준 지표 (기본: sharpe) |

**ranking_metric 옵션**:

| 값 | 설명 |
|-----|------|
| `sharpe` | 샤프 비율 (높을수록 좋음) |
| `return` | 총 수익률 (높을수록 좋음) |
| `mdd` | 최대 낙폭 (낮을수록 좋음) |
| `calmar` | Calmar 비율 (높을수록 좋음) |

**출력**:
- `combined_curve` - 통합 자산 곡선 `[{date, values: [전략1값, 전략2값, ...]}, ...]`
- `comparison_metrics` - 전략별 비교 지표 `[{index, id, label, return, sharpe, mdd, calmar}, ...]`
- `ranking` - 순위 `[{rank, index, id, label, <metric>}, ...]`
- `strategies_meta` - 전략 메타 정보 `[{index, id, label}, ...]`

**사용 예시**:

```
BacktestEngineNode (RSI 전략) ──┐
                               ├──▶ BenchmarkCompareNode ──▶ DisplayNode
BacktestEngineNode (SPY Buy&Hold) ──┘
```

> 💡 **SPY Buy&Hold 설정**: BacktestEngineNode의 `signals` 입력 없이 `data`만 제공하면 자동으로 Buy & Hold 전략이 적용됩니다.

---

## 14. calculation - 계산

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
| `risk` | 리스크 관리 | PositionSizingNode, PortfolioNode |
| `order` | 주문 실행 | NewOrderNode, ModifyOrderNode, CancelOrderNode |
| `display` | 시각화 | DisplayNode |
| `backtest` | 백테스트 | BacktestEngineNode, BenchmarkCompareNode |
| `calculation` | 계산 | PnLCalculatorNode |

---

## 다음 단계

- [구조 문서](structure.md) - 5-Layer 아키텍처 이해하기
- [플러그인 개발](custom_dsl.md) - 커스텀 플러그인 만들기
- [Logic 가이드](logic_guide.md) - 조건 조합 방법
- [스케줄 가이드](schedule_guide.md) - 크론 표현식 작성법
