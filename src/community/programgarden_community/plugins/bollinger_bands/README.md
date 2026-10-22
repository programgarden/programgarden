# Bollinger Bands 플러그인

## 플러그인 ID
`BollingerBands`

## 설명
볼린저밴드 하단/상단 이탈 조건을 평가합니다.

## 파라미터

| 이름 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `period` | int | 20 | 이동평균 기간 |
| `std_dev` | float | 2.0 | 표준편차 배수 |
| `position` | string | "below_lower" | 조건 위치 |

## DSL 예시

```json
{
  "id": "bb",
  "type": "ConditionNode",
  "plugin": "BollingerBands",
  "fields": {
    "period": 20,
    "std_dev": 2.0,
    "position": "below_lower"
  }
}
```
