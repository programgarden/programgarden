# Stop Loss (손절) 플러그인

## 플러그인 ID
`StopLoss`

## 설명
보유 포지션의 손실이 한계에 도달했는지 평가합니다.

## 파라미터

| 이름 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `percent` | float | -3.0 | 손절 비율 (%, 음수) |

## DSL 예시

```json
{
  "id": "stop_loss",
  "type": "ConditionNode",
  "plugin": "StopLoss",
  "fields": {
    "percent": -3.0
  }
}
```
