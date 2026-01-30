# MovingAverageCross 플러그인

## 개요

이동평균선 크로스오버 조건을 평가하는 플러그인입니다.

- **골든크로스**: 단기 MA가 장기 MA를 상향 돌파 → 매수 신호
- **데드크로스**: 단기 MA가 장기 MA를 하향 돌파 → 매도 신호

## 파라미터

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `short_period` | int | 5 | 단기 이동평균선 기간 |
| `long_period` | int | 20 | 장기 이동평균선 기간 |
| `cross_type` | string | "golden" | 크로스 유형 (golden/dead) |

## 사용 예시

### DSL에서 사용

```json
{
  "id": "goldenCross",
  "type": "ConditionNode",
  "category": "condition",
  "plugin": "MovingAverageCross",
  "fields": {
    "short_period": 5,
    "long_period": 20,
    "cross_type": "golden"
  }
}
```

### 출력

```json
{
  "passed_symbols": ["AAPL", "NVDA"],
  "failed_symbols": ["MSFT", "GOOGL"],
  "values": {
    "AAPL": {
      "short_ma": 185.50,
      "long_ma": 180.25,
      "ma_gap": 2.91,
      "status": "bullish",
      "crossover_count": 3
    }
  },
  "signals": [
    {"date": "2025-03-15", "symbol": "AAPL", "signal": "buy", "price": 182.50}
  ]
}
```

## 동작 방식

1. **실시간 모드**: 현재 단기MA > 장기MA 여부로 조건 평가
2. **백테스트 모드**: 과거 데이터에서 크로스오버 시점을 감지하여 `signals` 리스트 생성
