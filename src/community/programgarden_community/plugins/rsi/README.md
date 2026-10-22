# RSI (Relative Strength Index) 플러그인

## 플러그인 ID
`RSI`

## 버전
1.0.0

## 설명
RSI(상대강도지수)를 이용한 과매수/과매도 조건을 평가합니다.

## 지원 상품
- 해외주식 (overseas_stock)
- 해외선물 (overseas_futures)
- 코인 (crypto)

## 파라미터

| 이름 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `period` | int | 14 | RSI 계산 기간 (2~100) |
| `threshold` | float | 30 | 과매도/과매수 판단 임계값 (0~100) |
| `direction` | string | "below" | "below": 과매도, "above": 과매수 |

## DSL 사용 예시

### 과매도 매수 조건
```json
{
  "id": "rsi_oversold",
  "type": "ConditionNode",
  "plugin": "RSI",
  "fields": {
    "period": 14,
    "threshold": 30,
    "direction": "below"
  }
}
```

### 과매수 매도 조건
```json
{
  "id": "rsi_overbought",
  "type": "ConditionNode",
  "plugin": "RSI",
  "fields": {
    "period": 14,
    "threshold": 70,
    "direction": "above"
  }
}
```

## 엣지 연결

```json
{
  "edges": [
    {"from": "marketData.price", "to": "rsi_oversold.price_data"},
    {"from": "rsi_oversold.passed_symbols", "to": "buyOrder.trigger"}
  ]
}
```

## 반환 값

```json
{
  "passed_symbols": ["AAPL", "TSLA"],
  "failed_symbols": ["NVDA"],
  "values": {
    "AAPL": {"rsi": 28.5},
    "TSLA": {"rsi": 25.3},
    "NVDA": {"rsi": 45.2}
  },
  "result": true,
  "analysis": {
    "indicator": "RSI",
    "period": 14,
    "threshold": 30,
    "direction": "below",
    "comparison": "RSI < 30"
  }
}
```

## 투자 논리

- **RSI < 30**: 과매도 상태 → 반등 가능성 → 매수 신호
- **RSI > 70**: 과매수 상태 → 조정 가능성 → 매도 신호
- **RSI 50 근처**: 중립 상태
