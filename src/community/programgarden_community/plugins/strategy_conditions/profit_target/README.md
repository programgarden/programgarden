# Profit Target (익절) 플러그인

## 플러그인 ID
`ProfitTarget`

## 설명
보유 포지션의 수익률이 목표에 도달했는지 평가합니다.

## 파라미터

| 이름 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `percent` | float | 5.0 | 목표 수익률 (%) |

## DSL 예시

```json
{
  "id": "take_profit",
  "type": "ConditionNode",
  "plugin": "ProfitTarget",
  "fields": {
    "percent": 5.0
  }
}
```
