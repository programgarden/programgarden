# **종목조건 플러그인**

종목 매수/매도 조건을 판단하는 플러그인들입니다. `ConditionNode`에서 `plugin` 필드로 지정하여 사용합니다.

원하는 플러그인이 없다면:
- 카페에 요청: [요청하기](https://cafe.naver.com/f-e/cafes/30041992/menus/204?viewType=L)
- 직접 개발: [플러그인 개발 가이드](../custom_dsl.md)

---

## 사용 방법

```python
from programgarden_community.strategies import get_strategy
from programgarden import ProgramGarden

# 완성된 전략 바로 실행
strategy = get_strategy("overseas_stock", "penny_stock_rsi")
pg = ProgramGarden()
job = pg.run(strategy)
```

또는 직접 워크플로우에서 플러그인 참조:

```json
{
  "nodes": [
    {
      "id": "rsi",
      "type": "ConditionNode",
      "plugin": "RSI",
      "fields": {
        "period": 14,
        "threshold": 30,
        "direction": "below"
      }
    }
  ]
}
```

---

## 전략 조건 플러그인 (strategy_conditions)

| 플러그인 ID | 설명 | 상품 |
|------------|------|------|
| **RSI** | RSI 과매수/과매도 조건 | 해외주식, 해외선물 |
| **MACD** | MACD 크로스오버 조건 | 해외주식, 해외선물 |
| **BollingerBands** | 볼린저밴드 상단/하단 이탈 | 해외주식, 해외선물 |
| **VolumeSpike** | 거래량 급증 감지 | 해외주식, 해외선물 |
| **ProfitTarget** | 목표 수익률 익절 | 해외주식, 해외선물 |
| **StopLoss** | 손절 조건 | 해외주식, 해외선물 |

---

## RSI (Relative Strength Index)

과매도/과매수 상태를 판단합니다.

### 파라미터

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `period` | int | 14 | RSI 계산 기간 (2~100) |
| `threshold` | float | 30 | 임계값 (0~100) |
| `direction` | string | "below" | `below`: 과매도, `above`: 과매수 |

### 사용 예시

```json
{
  "id": "rsiBuy",
  "type": "ConditionNode",
  "plugin": "RSI",
  "fields": {
    "period": 14,
    "threshold": 30,
    "direction": "below"
  }
}
```

---

## MACD

MACD 선과 시그널 선의 교차를 감지합니다.

### 파라미터

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `fast_period` | int | 12 | 빠른 EMA 기간 |
| `slow_period` | int | 26 | 느린 EMA 기간 |
| `signal_period` | int | 9 | 시그널 기간 |
| `signal_type` | string | "bullish_cross" | `bullish_cross`: 골든크로스, `bearish_cross`: 데드크로스 |

### 사용 예시

```json
{
  "id": "macdBuy",
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

---

## BollingerBands

가격이 볼린저밴드 상단/하단을 이탈하는지 확인합니다.

### 파라미터

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `period` | int | 20 | 이동평균 기간 |
| `std_dev` | float | 2.0 | 표준편차 배수 (0.5~4.0) |
| `position` | string | "below_lower" | `below_lower`: 하단 이탈, `above_upper`: 상단 이탈 |

---

## VolumeSpike

평균 거래량 대비 급증을 감지합니다.

### 파라미터

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `period` | int | 20 | 평균 계산 기간 |
| `multiplier` | float | 2.0 | 평균 대비 배수 (1.0 이상) |

---

## ProfitTarget (익절)

보유 포지션이 목표 수익률에 도달하면 매도 신호를 발생시킵니다.

### 파라미터

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `percent` | float | 5.0 | 목표 수익률 (%) |

### 사용 예시

```json
{
  "id": "takeProfit",
  "type": "ConditionNode",
  "plugin": "ProfitTarget",
  "fields": {"percent": 5.0}
}
```

---

## StopLoss (손절)

보유 포지션이 손절 기준에 도달하면 매도 신호를 발생시킵니다.

### 파라미터

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `percent` | float | -3.0 | 손절 비율 (%, 음수 값) |

### 사용 예시

```json
{
  "id": "stopLoss",
  "type": "ConditionNode",
  "plugin": "StopLoss",
  "fields": {"percent": -3.0}
}
```

---

## 완성된 전략 목록

바로 사용 가능한 해외주식 전략:

| 전략 ID | 설명 | 노드 수 |
|---------|------|--------|
| `penny_stock_rsi` | 동전주 RSI 과매도 매수 (예수금 1~2만원용) | 16 |
| `backtest_to_live` | 백테스트 → 성과 검증 → 실계좌 배포 | 15 |
| `realtime_risk_monitor` | 실시간 P&L 모니터링 + 위험관리 | 18 |

```python
from programgarden_community.strategies import get_strategy, list_strategies

# 전체 전략 목록
print(list_strategies())
# {'overseas_stock': ['penny_stock_rsi', 'backtest_to_live', 'realtime_risk_monitor'], ...}

# 전략 조회 및 실행
strategy = get_strategy("overseas_stock", "penny_stock_rsi")
```

---

## 버전 정보

| 플러그인 | 버전 | 최종 수정 |
|----------|------|----------|
| RSI | 1.0.0 | 2026-01-06 |
| MACD | 1.0.0 | 2026-01-06 |
| BollingerBands | 1.0.0 | 2026-01-06 |
| VolumeSpike | 1.0.0 | 2026-01-06 |
| ProfitTarget | 1.0.0 | 2026-01-06 |
| StopLoss | 1.0.0 | 2026-01-06 |
