# Trailing Stop (가격 추적 정정) 플러그인

## 플러그인 ID
`TrailingStop`

## 설명
미체결 주문의 가격을 현재가에 맞춰 추적 정정합니다.

## 파라미터

| 이름 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `price_gap_percent` | float | 0.5 | 현재가 대비 가격 차이 (%) |
| `max_modifications` | int | 5 | 최대 정정 횟수 |

## DSL 예시

```json
{
  "id": "trailing",
  "type": "ModifyOrderNode",
  "plugin": "TrailingStop",
  "fields": {
    "price_gap_percent": 0.5,
    "max_modifications": 5
  }
}
```
