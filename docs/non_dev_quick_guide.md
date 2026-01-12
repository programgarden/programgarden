# 자동화매매 빠르게 사용하기

## 1. 개요

아래는 비전공 투자자도 이해하기 쉽게 정리한 구성 가이드입니다. 각 항목이 어떤 의미인지, 투자자가 직접 설정할 때 필요한 부분들을 설명합니다.

문서를 읽다가 헷갈리는 부분은 Issue 페이지 또는 커뮤니티를 통해 언제든지 피드백 주세요.

* 사용자 커뮤니티: https://cafe.naver.com/programgarden
* 카카오톡 오픈톡방: https://open.kakao.com/o/gKVObqUh

---

## 2. 노드 기반 DSL이란?

### 2.1 쉽게 말하면

자동매매를 설정할 때 **레고 블록처럼 기능 조각(노드)을 연결**하는 방식입니다.

| 개념 | 비유 |
|------|------|
| **노드(Node)** | 레고 블록 하나 - 특정 기능을 담당 |
| **엣지(Edge)** | 레고 블록을 연결하는 핀 - 데이터 흐름 |
| **워크플로우** | 완성된 레고 작품 - 전체 자동매매 전략 |

### 2.2 기본 구조

```json
{
  "nodes": [
    {"id": "broker", "type": "BrokerNode", ...},
    {"id": "watchlist", "type": "WatchlistNode", ...},
    {"id": "condition", "type": "ConditionNode", ...},
    {"id": "order", "type": "NewOrderNode", ...}
  ],
  "edges": [
    {"from": "watchlist.symbols", "to": "condition.symbols"},
    {"from": "condition.passed_symbols", "to": "order.symbols"}
  ]
}
```

- **nodes**: 사용할 기능 블록들
- **edges**: 블록 간 연결 (데이터가 어디서 어디로 흐르는지)

---

## 3. 준비 단계

### 3.1 계좌 개설

거래에 필요한 계좌를 개설해 주세요.

> 현재 LS증권을 메인 증권사로 지원하고 있습니다.

투혼앱에서 글로벌 상품 거래가 가능한 계좌를 비대면으로 개설해 주세요. 방법을 모르시면 LS증권 고객센터(1588-2428)에 문의해 주세요.

### 3.2 자동화매매 키 발급

투혼앱에서 API를 신청하고 매매에 필요한 Appkey와 Appsecretkey를 발급 받으세요.

**투혼앱 열기 → 전체 메뉴 → 투자정보 → 투자 파트너 → API 메뉴**

발급 받은 후 프로젝트 루트에 `.env` 파일을 만들어 관리할 수 있습니다.

```bash
APPKEY=your_stock_appkey
APPSECRET=your_stock_appsecret
APPKEY_FUTURE=your_futures_appkey
APPSECRET_FUTURE=your_futures_appsecret
```

---

## 4. 주요 노드 소개

### 4.1 노드 카테고리 한눈에 보기

| 카테고리 | 뭘 하는 건가요? | 예시 |
|----------|----------------|------|
| **infra** | 증권사에 연결합니다 | BrokerNode |
| **symbol** | 매매할 종목을 정합니다 | WatchlistNode |
| **trigger** | 언제 실행할지 정합니다 | ScheduleNode |
| **condition** | 매매 조건을 확인합니다 | ConditionNode, LogicNode |
| **order** | 실제 주문을 냅니다 | NewOrderNode |
| **realtime** | 실시간 데이터를 받습니다 | RealMarketDataNode |
| **risk** | 위험을 관리합니다 | RiskGuardNode |

### 4.2 자주 쓰는 노드 상세 설명

#### BrokerNode (증권사 연결)

증권사에 로그인하고 연결합니다.

```json
{
  "id": "broker",
  "type": "BrokerNode",
  "config": {
    "provider": "ls-sec.co.kr",
    "product": "overseas_stock",
    "credential_id": "cred-001"
  }
}
```

| 설정 | 설명 |
|------|------|
| `provider` | 증권사 (현재 `ls-sec.co.kr` 지원) |
| `product` | 상품 종류: `overseas_stock`(해외주식), `overseas_futures`(해외선물) |
| `credential_id` | 미리 등록한 인증 정보 ID |

#### WatchlistNode (관심 종목)

매매할 종목 목록을 지정합니다.

```json
{
  "id": "watchlist",
  "type": "WatchlistNode",
  "config": {
    "symbols": ["AAPL", "TSLA", "NVDA"]
  }
}
```

#### ScheduleNode (실행 스케줄)

언제 전략을 실행할지 정합니다.

```json
{
  "id": "schedule",
  "type": "ScheduleNode",
  "config": {
    "cron": "0 */15 * * * *",
    "timezone": "Asia/Seoul"
  }
}
```

- `cron`: 실행 주기 ([스케줄 가이드](schedule_guide.md) 참고)
- `timezone`: 기준 시간대

#### TradingHoursFilterNode (거래 시간 필터)

특정 시간대에만 매매합니다.

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

#### ConditionNode (조건 분석)

기술적 지표로 매수/매도 신호를 확인합니다.

```json
{
  "id": "rsi",
  "type": "ConditionNode",
  "plugin": "RSI",
  "fields": {
    "period": 14,
    "oversold": 30
  }
}
```

- `plugin`: 사용할 분석 전략 ([종목추출 전략 목록](strategies/stock_condition.md) 참고)
- `fields`: 전략에 필요한 설정값

#### LogicNode (조건 조합)

여러 조건을 어떻게 조합할지 정합니다.

```json
{
  "id": "logic",
  "type": "LogicNode",
  "config": {
    "operator": "all"
  }
}
```

| operator | 의미 |
|----------|------|
| `all` | 모든 조건 만족 (그리고) |
| `any` | 하나라도 만족 (또는) |
| `at_least` | N개 이상 만족 |
| `weighted` | 가중치 합산 |

자세한 내용은 [Logic 가이드](logic_guide.md)를 참고하세요.

#### NewOrderNode (신규 주문)

조건이 맞으면 주문을 냅니다.

```json
{
  "id": "order",
  "type": "NewOrderNode",
  "plugin": "StockSplitFunds",
  "fields": {
    "percent_balance": 10.0,
    "max_symbols": 5
  }
}
```

- `plugin`: 사용할 주문 전략 ([신규매매전략 목록](strategies/order_condition.md) 참고)

---

## 5. 엣지(Edge) 연결하기

노드끼리 데이터를 주고받으려면 **엣지**로 연결해야 합니다.

### 5.1 기본 형식

```json
{
  "from": "노드ID.출력포트",
  "to": "노드ID.입력포트"
}
```

### 5.2 자주 쓰는 연결 패턴

```json
"edges": [
  // 증권사 연결 → 실시간 데이터
  {"from": "broker.connection", "to": "realMarket"},
  {"from": "broker.connection", "to": "realAccount"},
  
  // 종목 → 시세 데이터
  {"from": "watchlist.symbols", "to": "realMarket.symbols"},
  
  // 스케줄 → 거래시간 필터 → 조건
  {"from": "schedule.trigger", "to": "tradingHours"},
  {"from": "tradingHours.passed", "to": "rsi"},
  
  // 시세 → 조건
  {"from": "realMarket.price", "to": "rsi.price_data"},
  
  // 조건 통과 → 주문
  {"from": "rsi.passed_symbols", "to": "order.symbols"},
  
  // 보유종목 정보 → 주문 (중복 매수 방지용)
  {"from": "realAccount.held_symbols", "to": "order.held_symbols"}
]
```

---

## 6. 완성된 예시

### 6.1 RSI 과매도 매수 전략

RSI가 30 이하면 매수하는 간단한 전략입니다.

```json
{
  "nodes": [
    {
      "id": "broker",
      "type": "BrokerNode",
      "config": {
        "provider": "ls-sec.co.kr",
        "product": "overseas_stock",
        "credential_id": "cred-001"
      }
    },
    {
      "id": "watchlist",
      "type": "WatchlistNode",
      "config": {
        "symbols": ["AAPL", "TSLA", "NVDA"]
      }
    },
    {
      "id": "realAccount",
      "type": "RealAccountNode"
    },
    {
      "id": "realMarket",
      "type": "RealMarketDataNode",
      "config": {
        "fields": ["price", "volume"]
      }
    },
    {
      "id": "schedule",
      "type": "ScheduleNode",
      "config": {
        "cron": "0 */15 * * * *",
        "timezone": "America/New_York"
      }
    },
    {
      "id": "tradingHours",
      "type": "TradingHoursFilterNode",
      "config": {
        "start": "09:30",
        "end": "16:00",
        "timezone": "America/New_York"
      }
    },
    {
      "id": "rsi",
      "type": "ConditionNode",
      "plugin": "RSI",
      "fields": {
        "period": 14,
        "oversold": 30
      }
    },
    {
      "id": "order",
      "type": "NewOrderNode",
      "plugin": "StockSplitFunds",
      "fields": {
        "percent_balance": 10.0,
        "max_symbols": 3
      }
    }
  ],
  "edges": [
    {"from": "broker.connection", "to": "realAccount"},
    {"from": "broker.connection", "to": "realMarket"},
    {"from": "watchlist.symbols", "to": "realMarket.symbols"},
    {"from": "schedule.trigger", "to": "tradingHours"},
    {"from": "tradingHours.passed", "to": "rsi"},
    {"from": "realMarket.price", "to": "rsi.price_data"},
    {"from": "rsi.passed_symbols", "to": "order.symbols"},
    {"from": "realAccount.held_symbols", "to": "order.held_symbols"}
  ]
}
```

### 6.2 복합 조건 (RSI + MACD)

두 가지 조건을 모두 만족할 때만 매수합니다.

```json
{
  "nodes": [
    {"id": "broker", "type": "BrokerNode", "config": {"provider": "ls-sec.co.kr", "product": "overseas_stock"}},
    {"id": "watchlist", "type": "WatchlistNode", "config": {"symbols": ["AAPL", "TSLA"]}},
    {"id": "realMarket", "type": "RealMarketDataNode"},
    {"id": "rsi", "type": "ConditionNode", "plugin": "RSI", "fields": {"period": 14, "oversold": 30}},
    {"id": "macd", "type": "ConditionNode", "plugin": "MACD", "fields": {"fast": 12, "slow": 26, "signal": 9}},
    {
      "id": "logic",
      "type": "LogicNode",
      "config": {
        "operator": "all"
      }
    },
    {"id": "order", "type": "NewOrderNode", "plugin": "StockSplitFunds"}
  ],
  "edges": [
    {"from": "broker.connection", "to": "realMarket"},
    {"from": "watchlist.symbols", "to": "realMarket.symbols"},
    {"from": "realMarket.price", "to": "rsi.price_data"},
    {"from": "realMarket.price", "to": "macd.price_data"},
    {"from": "rsi.result", "to": "logic.input"},
    {"from": "macd.result", "to": "logic.input"},
    {"from": "logic.passed_symbols", "to": "order.symbols"}
  ]
}
```

---

## 7. 실행하기

### 7.1 패키지 설치

```bash
pip install -U programgarden

# poetry 사용 시
poetry add programgarden
```

### 7.2 Python 코드로 실행

```python
from programgarden import Programgarden

pg = Programgarden()

# 콜백 설정
pg.on_condition_evaluated(
    callback=lambda msg: print(f"조건 평가: {msg}")
)
pg.on_order_filled(
    callback=lambda msg: print(f"주문 체결: {msg}")
)
pg.on_error(
    callback=lambda msg: print(f"에러: {msg}")
)

# 워크플로우 실행
pg.run(workflow={
    "nodes": [...],
    "edges": [...]
})
```

---

## 8. 유용한 팁

### 8.1 드라이런 모드

실제 주문 없이 테스트하고 싶을 때:

```json
{
  "id": "broker",
  "type": "BrokerNode",
  "config": {
    "provider": "ls-sec.co.kr",
    "product": "overseas_stock",
    "paper_trading": true
  }
}
```

### 8.2 리스크 관리

일일 손실 한도나 최대 포지션 수를 제한하고 싶을 때:

```json
{
  "id": "riskGuard",
  "type": "RiskGuardNode",
  "config": {
    "max_daily_loss": -500,
    "max_positions": 5
  }
}
```

### 8.3 알림 설정

주문 체결 시 슬랙으로 알림 받기:

```json
{
  "id": "alert",
  "type": "AlertNode",
  "config": {
    "channel": "slack",
    "on": ["order_filled", "risk_triggered"]
  }
}
```

---

## 9. 다음 단계

- [Logic 가이드](logic_guide.md) - 조건 조합 방법 상세
- [스케줄 가이드](schedule_guide.md) - cron 표현식 작성법
- [종목추출 전략 목록](strategies/stock_condition.md) - 사용 가능한 분석 전략
- [신규매매전략 목록](strategies/order_condition.md) - 사용 가능한 주문 전략
- [DSL 커스터마이징](custom_dsl.md) - 직접 플러그인 만들기 (개발자용)
