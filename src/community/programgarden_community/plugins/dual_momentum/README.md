# DualMomentum 플러그인

## 개요

Gary Antonacci의 듀얼 모멘텀(Dual Momentum) 전략을 구현한 플러그인입니다.

- **절대 모멘텀**: 자산의 과거 수익률이 양수(또는 임계값 이상)인지 확인
- **상대 모멘텀**: 기준 자산(채권, 현금) 대비 우수한지 확인

두 조건을 모두 만족해야 매수 신호가 발생합니다.

## 파라미터

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `lookback_period` | int | 252 | 모멘텀 계산 기간 (252일 ≈ 12개월) |
| `absolute_threshold` | float | 0 | 절대 모멘텀 임계값 (%) |
| `use_relative` | bool | true | 상대 모멘텀 사용 여부 |
| `relative_benchmark` | string | "SHY" | 벤치마크 (SHY/BIL/CASH) |

## 사용 예시

### DSL에서 사용

```json
{
  "id": "dualMomentum",
  "type": "ConditionNode",
  "category": "condition",
  "plugin": "DualMomentum",
  "fields": {
    "lookback_period": 252,
    "absolute_threshold": 0,
    "use_relative": true,
    "relative_benchmark": "SHY"
  }
}
```

### 출력

```json
{
  "passed_symbols": ["AAPL", "MSFT"],
  "failed_symbols": ["COIN", "PYPL"],
  "values": {
    "AAPL": {
      "momentum": 25.5,
      "benchmark_momentum": 3.2,
      "absolute_pass": true,
      "relative_pass": true,
      "status": "passed"
    }
  },
  "ranking": [
    {"symbol": "AAPL", "momentum": 25.5},
    {"symbol": "MSFT", "momentum": 18.3}
  ]
}
```

## 전략 로직

1. **절대 모멘텀**: `12개월 수익률 > 0%`
2. **상대 모멘텀**: `12개월 수익률 > SHY 12개월 수익률`
3. **매수 조건**: 절대 AND 상대 모두 충족
4. **리밸런싱**: 월간 (21거래일마다)

## 참고

- Gary Antonacci, "Dual Momentum Investing" (2014)
- 원전략은 SPY vs 해외주식 vs 채권 중 선택하는 자산배분 전략
- 이 플러그인은 개별 종목 선별용으로 단순화
