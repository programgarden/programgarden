# Market Order (시장가 주문) 플러그인

## 플러그인 ID
`MarketOrder`

## 설명
시장가로 즉시 주문을 실행합니다.

## 파라미터

| 이름 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `side` | string | - | "buy" 또는 "sell" (필수) |
| `amount_type` | string | "fixed" | 수량 계산 방식 |
| `amount` | float | 10 | 수량 또는 비율 |

## DSL 예시

```json
{
  "id": "buyOrder",
  "type": "NewOrderNode",
  "plugin": "MarketOrder",
  "fields": {
    "side": "buy",
    "amount_type": "percent_balance",
    "amount": 10
  }
}
```
