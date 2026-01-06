# Limit Order (지정가 주문) 플러그인

## 플러그인 ID
`LimitOrder`

## 설명
지정가로 주문을 실행합니다.

## 파라미터

| 이름 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `side` | string | - | "buy" 또는 "sell" (필수) |
| `price_type` | string | "fixed" | 가격 방식 |
| `price` | float | - | 주문 가격 |

## DSL 예시

```json
{
  "id": "limitOrder",
  "type": "NewOrderNode",
  "plugin": "LimitOrder",
  "fields": {
    "side": "buy",
    "price_type": "percent_from_current",
    "price": -1.0
  }
}
```
