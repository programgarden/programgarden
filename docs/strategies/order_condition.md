# **주문 플러그인**

매수/매도 주문 실행 및 주문 관리 플러그인들입니다. `NewOrderNode`, `ModifyOrderNode`, `CancelOrderNode`에서 `plugin` 필드로 지정하여 사용합니다.

원하는 플러그인이 없다면:
- 카페에 요청: [요청하기](https://cafe.naver.com/f-e/cafes/30041992/menus/204?viewType=L)
- 직접 개발: [플러그인 개발 가이드](../custom_dsl.md)

---

## 신규 주문 플러그인 (new_order_conditions)

| 플러그인 ID | 설명 | 상품 |
|------------|------|------|
| **MarketOrder** | 시장가 즉시 체결 | 해외주식 |
| **LimitOrder** | 지정가 주문 | 해외주식 |

---

## MarketOrder (시장가 주문)

시장가로 즉시 체결됩니다.

### 파라미터

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `side` | string | - | `buy`: 매수, `sell`: 매도 (필수) |
| `amount_type` | string | "fixed" | `percent_balance`: 예수금 비율, `fixed`: 고정 수량, `all`: 전량 |
| `amount` | float | 10 | 수량 또는 비율 |

### 사용 예시

```json
{
  "id": "buyOrder",
  "type": "NewOrderNode",
  "plugin": "MarketOrder",
  "fields": {
    "side": "buy",
    "amount_type": "percent_balance",
    "amount": 90
  }
}
```

---

## LimitOrder (지정가 주문)

지정한 가격에 주문을 걸어둡니다.

### 파라미터

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `side` | string | - | `buy`: 매수, `sell`: 매도 (필수) |
| `price_type` | string | "fixed" | `fixed`: 고정가, `percent_from_current`: 현재가 대비 % |
| `price` | float | - | 주문 가격 (필수) |

### 사용 예시

```json
{
  "id": "limitBuy",
  "type": "NewOrderNode",
  "plugin": "LimitOrder",
  "fields": {
    "side": "buy",
    "price_type": "percent_from_current",
    "price": -1.0
  }
}
```

---

## 정정 주문 플러그인 (modify_order_conditions)

| 플러그인 ID | 설명 | 상품 |
|------------|------|------|
| **TrailingStop** | 현재가 추적 정정 | 해외주식 |

---

## TrailingStop (가격 추적 정정)

미체결 주문의 가격을 현재가에 맞춰 자동 정정합니다.

### 파라미터

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `price_gap_percent` | float | 0.5 | 현재가 대비 주문가 차이 (%) |
| `max_modifications` | int | 5 | 최대 정정 횟수 |

### 사용 예시

```json
{
  "id": "trailingModify",
  "type": "ModifyOrderNode",
  "plugin": "TrailingStop",
  "fields": {
    "price_gap_percent": 0.5,
    "max_modifications": 5
  }
}
```

---

## 취소 주문 플러그인 (cancel_order_conditions)

| 플러그인 ID | 설명 | 상품 |
|------------|------|------|
| **TimeStop** | 시간 초과 취소 | 해외주식 |

---

## TimeStop (시간 초과 취소)

지정 시간 내 미체결 시 주문을 자동 취소합니다.

### 파라미터

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `timeout_minutes` | int | 30 | 타임아웃 (분, 1 이상) |

### 사용 예시

```json
{
  "id": "timeCancel",
  "type": "CancelOrderNode",
  "plugin": "TimeStop",
  "fields": {"timeout_minutes": 30}
}
```

---

## 완성된 전략에서의 주문 플러그인 사용

`penny_stock_rsi` 전략의 주문 흐름:

```
RSI 조건 충족 → PositionSizingNode → NewOrderNode (MarketOrder)
                                          ↓
ProfitTarget/StopLoss 충족 → NewOrderNode (MarketOrder, sell)
```

```python
from programgarden_community.strategies import get_strategy

strategy = get_strategy("overseas_stock", "penny_stock_rsi")

# 주문 노드 확인
order_nodes = [n for n in strategy["nodes"] if "Order" in n["type"]]
for node in order_nodes:
    print(f'{node["id"]}: {node.get("plugin")} - {node.get("fields", {}).get("side")}')
```

---

## 버전 정보

| 플러그인 | 버전 | 최종 수정 |
|----------|------|----------|
| MarketOrder | 1.0.0 | 2026-01-06 |
| LimitOrder | 1.0.0 | 2026-01-06 |
| TrailingStop | 1.0.0 | 2026-01-06 |
| TimeStop | 1.0.0 | 2026-01-06 |
