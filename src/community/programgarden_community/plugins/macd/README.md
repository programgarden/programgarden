# MACD (Moving Average Convergence Divergence) 플러그인

## 플러그인 ID
`MACD`

## 설명
MACD 지표를 이용한 크로스오버 신호를 평가합니다.

## 파라미터

| 이름 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `fast_period` | int | 12 | 빠른 EMA 기간 |
| `slow_period` | int | 26 | 느린 EMA 기간 |
| `signal_period` | int | 9 | 시그널 EMA 기간 |
| `signal_type` | string | "bullish_cross" | 신호 유형 |

## DSL 예시

```json
{
  "id": "macd",
  "type": "ConditionNode",
  "plugin": "MACD",
  "fields": {
    "fast_period": 12,
    "slow_period": 26,
    "signal_period": 9,
    "signal_type": "bullish_cross"
  }
}
```
