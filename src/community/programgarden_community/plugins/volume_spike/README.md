# Volume Spike 플러그인

## 플러그인 ID
`VolumeSpike`

## 설명
거래량이 평균 대비 급증했는지 평가합니다.

## 파라미터

| 이름 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `period` | int | 20 | 평균 거래량 계산 기간 |
| `multiplier` | float | 2.0 | 평균 대비 배수 |

## DSL 예시

```json
{
  "id": "volume",
  "type": "ConditionNode",
  "plugin": "VolumeSpike",
  "fields": {
    "period": 20,
    "multiplier": 2.0
  }
}
```
