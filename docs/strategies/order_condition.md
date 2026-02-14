# 주문 플러그인

매수/매도 주문 실행 및 주문 관리 플러그인들입니다. `NewOrderNode`, `ModifyOrderNode`, `CancelOrderNode`에서 `plugin` 필드로 지정하여 사용합니다.

원하는 플러그인이 없다면:
- 카페에 요청: [요청하기](https://cafe.naver.com/f-e/cafes/30041992/menus/204?viewType=L)
- 직접 개발: [플러그인 개발 가이드](../custom_dsl.md)

---

## 신규 주문 플러그인 (NewOrderNode용)

| 플러그인 | 설명 | 상품 |
|---------|------|------|
| **MarketOrder** | 시장가 즉시 체결 | 해외주식, 해외선물 |
| **LimitOrder** | 지정가 주문 | 해외주식, 해외선물 |

---

### MarketOrder (시장가 주문)

**현재 시장 가격**으로 즉시 체결됩니다. 빠르게 매매하고 싶을 때 사용합니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `side` | string | - | `buy`: 매수, `sell`: 매도 (필수) |
| `amount_type` | string | "fixed" | 수량 계산 방식 (아래 표 참고) |
| `amount` | float | 10 | 수량 또는 비율 |

**수량 계산 방식 (`amount_type`):**

| 값 | 설명 | `amount` 의미 |
|----|------|--------------|
| `fixed` | 고정 수량 | 주문 주수 (예: 10주) |
| `percent_balance` | 예수금 비율 | 예수금의 N% 사용 (예: 90 → 예수금의 90%) |
| `all` | 전량 | 보유 전량 매도 (`amount` 무시) |

```json
{
  "id": "buyOrder",
  "type": "OverseasStockNewOrderNode",
  "plugin": "MarketOrder",
  "fields": {
    "side": "buy",
    "amount_type": "percent_balance",
    "amount": 90
  }
}
```

> **주의**: `percent_balance`로 90%를 지정하면 예수금의 90%를 사용합니다. 수수료와 환율 변동을 고려하여 100%보다 낮게 설정하세요.

> **주의 - 주간거래**: 정규장 외 시간(주간거래, 프리마켓, 애프터마켓)에는 시장가 주문이 불가능할 수 있습니다. 이 시간에는 `LimitOrder`를 사용하세요.

---

### LimitOrder (지정가 주문)

**지정한 가격**에 주문을 걸어둡니다. 원하는 가격에 도달해야 체결됩니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `side` | string | - | `buy`: 매수, `sell`: 매도 (필수) |
| `price_type` | string | "fixed" | 가격 계산 방식 |
| `price` | float | - | 주문 가격 (필수) |
| `amount_type` | string | "fixed" | 수량 계산 방식 |
| `amount` | float | 10 | 수량 또는 비율 |

**가격 계산 방식 (`price_type`):**

| 값 | 설명 | `price` 의미 |
|----|------|-------------|
| `fixed` | 고정 가격 | 절대 가격 (예: 150.00) |
| `percent_from_current` | 현재가 대비 % | 변화율 (예: -1.0 → 현재가의 1% 아래) |

```json
{
  "id": "limitBuy",
  "type": "OverseasStockNewOrderNode",
  "plugin": "LimitOrder",
  "fields": {
    "side": "buy",
    "price_type": "percent_from_current",
    "price": -1.0,
    "amount_type": "fixed",
    "amount": 5
  }
}
```

> **팁**: `price_type: "percent_from_current"`과 `price: -1.0`을 사용하면 현재가보다 1% 낮은 가격에 매수 주문이 들어갑니다. 살짝 저렴하게 사고 싶을 때 유용합니다.

---

## 정정 주문 플러그인 (ModifyOrderNode용)

미체결 주문의 가격/수량을 수정합니다.

| 플러그인 | 설명 | 상품 |
|---------|------|------|
| **TrailingStop** | 현재가 추적 가격 정정 | 해외주식 |

---

### TrailingStop (가격 추적 정정)

미체결 주문의 가격을 **현재가에 맞춰 자동으로 정정**합니다. 가격이 오르면 주문 가격도 따라 올려서 더 높은 가격에 매도할 수 있습니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `price_gap_percent` | float | 0.5 | 현재가 대비 주문가 차이 (%) |
| `max_modifications` | int | 5 | 최대 정정 횟수 |

```json
{
  "id": "trailingModify",
  "type": "OverseasStockModifyOrderNode",
  "plugin": "TrailingStop",
  "fields": {
    "price_gap_percent": 0.5,
    "max_modifications": 5
  }
}
```

> **예시**: 현재가가 100달러이고 `price_gap_percent`가 0.5이면, 99.50달러에 매도 주문을 걸어둡니다. 현재가가 105달러로 오르면 주문도 104.475달러로 자동 정정됩니다.

---

## 취소 주문 플러그인 (CancelOrderNode용)

미체결 주문을 자동으로 취소합니다.

| 플러그인 | 설명 | 상품 |
|---------|------|------|
| **TimeStop** | 시간 초과 자동 취소 | 해외주식 |

---

### TimeStop (시간 초과 취소)

주문 후 **지정 시간 내에 체결되지 않으면** 자동으로 취소합니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `timeout_minutes` | int | 30 | 타임아웃 (분, 1 이상) |

```json
{
  "id": "timeCancel",
  "type": "OverseasStockCancelOrderNode",
  "plugin": "TimeStop",
  "fields": {"timeout_minutes": 30}
}
```

> **팁**: 지정가 주문(`LimitOrder`)과 함께 사용하면 좋습니다. 30분 동안 체결되지 않으면 자동으로 취소하여 자금이 묶이는 것을 방지합니다.

---

## 주문 흐름 예시

### 매수 → 익절/손절 자동화

```
RSI 조건 충족 → PositionSizingNode → NewOrderNode (MarketOrder, 매수)

ProfitTarget 충족 → NewOrderNode (MarketOrder, 매도)  ← 익절
StopLoss 충족   → NewOrderNode (MarketOrder, 매도)  ← 손절
```

```json
{
  "nodes": [
    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "my-broker"},
    {"id": "rsi", "type": "ConditionNode", "plugin": "RSI", "data": "{{ nodes.history.values }}", "fields": {"threshold": 30, "direction": "below"}},
    {"id": "buyOrder", "type": "OverseasStockNewOrderNode", "plugin": "MarketOrder", "fields": {"side": "buy", "amount_type": "percent_balance", "amount": 10}},
    {"id": "profit", "type": "ConditionNode", "plugin": "ProfitTarget", "fields": {"target_percent": 5.0}},
    {"id": "stop", "type": "ConditionNode", "plugin": "StopLoss", "fields": {"stop_percent": -3.0}},
    {"id": "exitLogic", "type": "LogicNode", "operator": "any"},
    {"id": "sellOrder", "type": "OverseasStockNewOrderNode", "plugin": "MarketOrder", "fields": {"side": "sell", "amount_type": "all"}}
  ],
  "edges": [
    {"from": "broker", "to": "rsi"},
    {"from": "rsi", "to": "buyOrder"},
    {"from": "broker", "to": "profit"},
    {"from": "broker", "to": "stop"},
    {"from": "profit", "to": "exitLogic"},
    {"from": "stop", "to": "exitLogic"},
    {"from": "exitLogic", "to": "sellOrder"}
  ]
}
```

> **주의**: 실제 주문이 실행되므로 반드시 **모의투자 계좌**로 먼저 테스트하세요. `credential`의 `paper_trading`을 `true`로 설정하면 모의투자 모드로 동작합니다.
