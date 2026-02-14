# 종목조건 플러그인

종목 매수/매도 조건을 판단하는 플러그인들입니다. `ConditionNode`에서 `plugin` 필드로 지정하여 사용합니다.

원하는 플러그인이 없다면:
- 카페에 요청: [요청하기](https://cafe.naver.com/f-e/cafes/30041992/menus/204?viewType=L)
- 직접 개발: [플러그인 개발 가이드](../custom_dsl.md)

---

## 사용 방법

```json
{
  "id": "rsi",
  "type": "ConditionNode",
  "plugin": "RSI",
  "data": "{{ nodes.history.values }}",
  "fields": {
    "period": 14,
    "threshold": 30,
    "direction": "below"
  }
}
```

- `plugin`: 사용할 플러그인 이름
- `data`: 분석할 OHLCV 데이터 (HistoricalDataNode의 출력)
- `fields`: 플러그인별 파라미터

> **주의**: `data`에는 반드시 OHLCV 시계열 데이터가 필요합니다. 보통 `HistoricalDataNode`의 출력(`{{ nodes.history.values }}`)을 연결합니다. 데이터가 부족하면 정확한 판단이 어렵습니다.

---

## 전체 플러그인 목록

### 기술적 지표 (17개)

| 분류 | 플러그인 | 설명 |
|------|---------|------|
| **모멘텀** | RSI | RSI 과매수/과매도 |
| | MACD | MACD 골든/데드크로스 |
| | Stochastic | 스토캐스틱 %K/%D 크로스 |
| | OBV | 거래량 기반 매매 압력 |
| **추세** | ADX | 추세 강도 측정 |
| | MovingAverageCross | 이동평균 골든/데드크로스 |
| | DualMomentum | 듀얼모멘텀 (절대+상대) |
| | BreakoutRetest | 돌파 후 되돌림 매매 |
| **변동성** | BollingerBands | 볼린저밴드 이탈 |
| | ATR | ATR 변동성 돌파 |
| | PriceChannel | 돈치안 채널 돌파 |
| | GoldenRatio | 피보나치 되돌림 |
| **거래량** | VolumeSpike | 거래량 급증 감지 |
| **평균회귀** | MeanReversion | 이평선 이탈 회귀 |
| **포지션 관리** | ProfitTarget | 목표 수익률 익절 |
| | StopLoss | 손절 조건 |
| | TrailingStop | 추적 손절 (비율 기반) |

---

## 모멘텀 지표

### RSI (Relative Strength Index)

**과매도/과매수 상태**를 판단합니다. RSI가 30 이하이면 "너무 많이 떨어졌으니 반등할 수 있다", 70 이상이면 "너무 많이 올랐으니 조정이 올 수 있다"는 신호입니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `period` | int | 14 | RSI 계산 기간 (2~100) |
| `threshold` | float | 30 | 임계값 (0~100) |
| `direction` | string | "below" | `below`: 과매도(매수 신호), `above`: 과매수(매도 신호) |

```json
{
  "id": "rsiBuy",
  "type": "ConditionNode",
  "plugin": "RSI",
  "data": "{{ nodes.history.values }}",
  "fields": {"period": 14, "threshold": 30, "direction": "below"}
}
```

> **팁**: `period`가 짧을수록 민감하게 반응합니다. 단타는 7~9, 중장기는 14~21을 추천합니다.

> **필요 데이터**: 최소 `period + 1`일의 종가(close) 데이터

---

### MACD (Moving Average Convergence Divergence)

두 이동평균선의 **교차(크로스)**를 감지합니다. 빠른 선이 느린 선을 위로 뚫으면 매수(골든크로스), 아래로 뚫으면 매도(데드크로스) 신호입니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `fast_period` | int | 12 | 빠른 EMA 기간 |
| `slow_period` | int | 26 | 느린 EMA 기간 |
| `signal_period` | int | 9 | 시그널 기간 |
| `signal_type` | string | "bullish_cross" | `bullish_cross`: 골든크로스, `bearish_cross`: 데드크로스 |

```json
{
  "id": "macdBuy",
  "type": "ConditionNode",
  "plugin": "MACD",
  "data": "{{ nodes.history.values }}",
  "fields": {"fast_period": 12, "slow_period": 26, "signal_period": 9, "signal_type": "bullish_cross"}
}
```

> **필요 데이터**: 최소 35일(`slow_period` + `signal_period`)의 종가 데이터

---

### Stochastic (스토캐스틱)

현재 가격이 최근 N일간의 가격 범위에서 **어디에 위치**하는지 판단합니다. %K가 %D를 위로 교차하면서 20 이하에 있으면 매수, 80 이상에서 아래로 교차하면 매도 신호입니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `k_period` | int | 14 | %K 기간 (1~100) |
| `d_period` | int | 3 | %D 기간 (1~50) |
| `threshold` | float | 20 | 과매도 임계값 (0~50) |
| `direction` | string | "oversold" | `oversold`: 과매도(매수), `overbought`: 과매수(매도) |

```json
{
  "id": "stochastic",
  "type": "ConditionNode",
  "plugin": "Stochastic",
  "data": "{{ nodes.history.values }}",
  "fields": {"k_period": 14, "d_period": 3, "threshold": 20, "direction": "oversold"}
}
```

> **필요 데이터**: 고가(high), 저가(low), 종가(close)

---

### OBV (On-Balance Volume)

**거래량의 흐름**으로 매수/매도 압력을 파악합니다. OBV가 이동평균 위에 있으면 매수 세력이 강한 것, 아래에 있으면 매도 세력이 강한 것으로 판단합니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `ma_period` | int | 20 | OBV 이동평균 기간 (5~100) |
| `direction` | string | "bullish" | `bullish`: 매수 압력, `bearish`: 매도 압력 |

```json
{
  "id": "obv",
  "type": "ConditionNode",
  "plugin": "OBV",
  "data": "{{ nodes.history.values }}",
  "fields": {"ma_period": 20, "direction": "bullish"}
}
```

> **필요 데이터**: 종가(close), 거래량(volume)

---

## 추세 지표

### ADX (Average Directional Index)

**추세의 강도**를 측정합니다. 방향이 아니라 "추세가 얼마나 강한가"를 알려줍니다. ADX가 25 이상이면 강한 추세, 20 이하이면 횡보(추세 없음)입니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `period` | int | 14 | ADX 기간 (5~50) |
| `threshold` | float | 25.0 | 추세 강도 임계값 (15~50) |
| `direction` | string | "strong_trend" | `strong_trend`: 강한 추세, `uptrend`: 상승추세, `downtrend`: 하락추세 |

```json
{
  "id": "adx",
  "type": "ConditionNode",
  "plugin": "ADX",
  "data": "{{ nodes.history.values }}",
  "fields": {"period": 14, "threshold": 25, "direction": "uptrend"}
}
```

> **팁**: ADX는 방향을 알려주지 않으므로, RSI나 MACD와 함께 사용하면 더 정확합니다. `LogicNode`로 조합하세요.

> **필요 데이터**: 고가, 저가, 종가. 최소 `period x 2`일 데이터

---

### MovingAverageCross (이동평균 크로스)

**두 이동평균선의 교차**를 감지합니다. 단기 이동평균이 장기 이동평균을 위로 뚫으면 골든크로스(매수), 아래로 뚫으면 데드크로스(매도)입니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `short_period` | int | 5 | 단기 이동평균 기간 |
| `long_period` | int | 20 | 장기 이동평균 기간 |
| `cross_type` | string | "golden" | `golden`: 골든크로스(매수), `dead`: 데드크로스(매도) |

```json
{
  "id": "maCross",
  "type": "ConditionNode",
  "plugin": "MovingAverageCross",
  "data": "{{ nodes.history.values }}",
  "fields": {"short_period": 5, "long_period": 20, "cross_type": "golden"}
}
```

> **팁**: 5일/20일 크로스는 단기, 50일/200일 크로스는 장기 추세에 적합합니다.

---

### DualMomentum (듀얼모멘텀)

게리 안토나치의 **듀얼모멘텀 전략**입니다. 절대모멘텀(최근 수익률이 양수인가)과 상대모멘텀(벤치마크보다 나은가)을 동시에 확인합니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `lookback_period` | int | 252 | 수익률 계산 기간 (일) |
| `absolute_threshold` | float | 0.0 | 절대모멘텀 기준 수익률 (%) |
| `use_relative` | bool | true | 상대모멘텀 사용 여부 |
| `relative_benchmark` | string | "SHY" | 벤치마크 (`SHY`, `BIL`, `CASH`) |

```json
{
  "id": "dualMom",
  "type": "ConditionNode",
  "plugin": "DualMomentum",
  "data": "{{ nodes.history.values }}",
  "fields": {"lookback_period": 252, "absolute_threshold": 0, "use_relative": true}
}
```

> **주의**: 252일(약 1년)의 데이터가 필요합니다. 충분한 과거 데이터를 조회하세요.

---

### BreakoutRetest (돌파 후 되돌림)

가격이 주요 지지/저항선을 **돌파한 뒤 되돌아와서 지지를 확인**하는 패턴을 감지합니다. 매수 기회로 활용합니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `lookback` | int | 20 | 돌파 수준 탐색 기간 (5~100) |
| `retest_threshold` | float | 0.02 | 되돌림 근접 허용 범위 (0.005~0.1) |
| `direction` | string | "bullish" | `bullish`: 상방 돌파 후 매수, `bearish`: 하방 돌파 후 매도 |

```json
{
  "id": "breakout",
  "type": "ConditionNode",
  "plugin": "BreakoutRetest",
  "data": "{{ nodes.history.values }}",
  "fields": {"lookback": 20, "retest_threshold": 0.02, "direction": "bullish"}
}
```

---

## 변동성 지표

### BollingerBands (볼린저밴드)

가격이 이동평균에서 **얼마나 벗어났는지** 측정합니다. 하단밴드 아래로 내려가면 과매도(매수 기회), 상단밴드 위로 올라가면 과매수(매도 기회)로 판단합니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `period` | int | 20 | 이동평균 기간 (5~100) |
| `std_dev` | float | 2.0 | 표준편차 배수 (0.5~4.0) |
| `position` | string | "below_lower" | `below_lower`: 하단 이탈(매수), `above_upper`: 상단 이탈(매도) |

```json
{
  "id": "bb",
  "type": "ConditionNode",
  "plugin": "BollingerBands",
  "data": "{{ nodes.history.values }}",
  "fields": {"period": 20, "std_dev": 2.0, "position": "below_lower"}
}
```

> **팁**: `std_dev`가 클수록 밴드가 넓어져 신호가 줄어들고, 작을수록 신호가 잦아집니다.

---

### ATR (Average True Range)

**변동성의 크기**를 측정하여 돌파 매매에 활용합니다. ATR 밴드를 넘어서면 강한 모멘텀으로 판단합니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `period` | int | 14 | ATR 기간 (1~100) |
| `multiplier` | float | 2.0 | ATR 배수 (0.5~5.0) |
| `direction` | string | "breakout_up" | `breakout_up`: 상방 돌파, `breakout_down`: 하방 돌파 |

```json
{
  "id": "atr",
  "type": "ConditionNode",
  "plugin": "ATR",
  "data": "{{ nodes.history.values }}",
  "fields": {"period": 14, "multiplier": 2.0, "direction": "breakout_up"}
}
```

> **필요 데이터**: 고가, 저가, 종가

---

### PriceChannel (돈치안 채널)

**N일 최고가/최저가**로 채널을 만듭니다. 최고가 돌파 시 매수, 최저가 하회 시 매도합니다. 추세추종 전략의 기본입니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `period` | int | 20 | 채널 기간 (5~100) |
| `direction` | string | "breakout_high" | `breakout_high`: 상단 돌파(매수), `breakout_low`: 하단 돌파(매도) |

```json
{
  "id": "donchian",
  "type": "ConditionNode",
  "plugin": "PriceChannel",
  "data": "{{ nodes.history.values }}",
  "fields": {"period": 20, "direction": "breakout_high"}
}
```

---

### GoldenRatio (피보나치 되돌림)

**피보나치 비율**(23.6%, 38.2%, 50%, 61.8%, 78.6%)의 지지/저항선을 활용합니다. 가격이 되돌림 수준에 근접하면 매매 신호를 발생시킵니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `lookback` | int | 50 | 고저점 탐색 기간 (10~200) |
| `level` | string | "0.618" | 피보나치 수준 (`0.236`, `0.382`, `0.5`, `0.618`, `0.786`) |
| `direction` | string | "support" | `support`: 지지선 근접(매수), `resistance`: 저항선 근접(매도) |
| `tolerance` | float | 0.02 | 근접 허용 범위 (0.005~0.1) |

```json
{
  "id": "fib",
  "type": "ConditionNode",
  "plugin": "GoldenRatio",
  "data": "{{ nodes.history.values }}",
  "fields": {"lookback": 50, "level": "0.618", "direction": "support", "tolerance": 0.02}
}
```

> **팁**: 61.8% 되돌림은 "황금비율"로 가장 많이 사용됩니다. 50%와 함께 확인하면 더 정확합니다.

---

## 거래량 지표

### VolumeSpike (거래량 급증)

**평균 거래량 대비** 급격히 증가한 종목을 찾습니다. 거래량 급증은 큰 관심이 몰리고 있다는 신호이며, 추세 전환의 시작일 수 있습니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `period` | int | 20 | 평균 계산 기간 (5 이상) |
| `multiplier` | float | 2.0 | 평균 대비 배수 (1.0 이상) |

```json
{
  "id": "volumeSpike",
  "type": "ConditionNode",
  "plugin": "VolumeSpike",
  "data": "{{ nodes.history.values }}",
  "fields": {"period": 20, "multiplier": 2.0}
}
```

---

## 평균회귀 지표

### MeanReversion (평균회귀)

가격이 이동평균에서 **크게 벗어나면 다시 돌아온다**는 원리를 이용합니다. 이동평균 아래로 크게 벗어나면 매수, 위로 크게 벗어나면 매도합니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `ma_period` | int | 20 | 이동평균 기간 (5~200) |
| `deviation` | float | 2.0 | 표준편차 배수 (1.0~4.0) |
| `direction` | string | "oversold" | `oversold`: 과매도(매수), `overbought`: 과매수(매도) |

```json
{
  "id": "meanRev",
  "type": "ConditionNode",
  "plugin": "MeanReversion",
  "data": "{{ nodes.history.values }}",
  "fields": {"ma_period": 20, "deviation": 2.0, "direction": "oversold"}
}
```

> **주의**: 평균회귀는 횡보장에서 효과적이지만, 강한 추세장에서는 손실이 커질 수 있습니다. ADX와 함께 사용하여 추세가 약할 때만 적용하는 것을 권장합니다.

---

## 포지션 관리 지표

이 플러그인들은 보유 포지션의 수익률을 기반으로 매도 시점을 판단합니다. OHLCV 시계열 데이터가 아닌 **계좌 포지션 데이터**를 사용합니다.

### ProfitTarget (익절)

보유 종목의 수익률이 **목표에 도달**하면 매도합니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `target_percent` | float | 5.0 | 목표 수익률 (%) |

```json
{
  "id": "takeProfit",
  "type": "ConditionNode",
  "plugin": "ProfitTarget",
  "fields": {"target_percent": 5.0}
}
```

> **주의**: `data` 필드가 아닌 계좌 포지션 데이터를 사용합니다. AccountNode 또는 RealAccountNode의 출력이 필요합니다.

---

### StopLoss (손절)

보유 종목의 손실이 **한도에 도달**하면 매도합니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `stop_percent` | float | -3.0 | 손절 비율 (%, 음수) |

```json
{
  "id": "stopLoss",
  "type": "ConditionNode",
  "plugin": "StopLoss",
  "fields": {"stop_percent": -3.0}
}
```

---

### TrailingStop (추적 손절)

가격이 오르면 손절 기준도 따라 올라가는 **비율 기반 추적 손절**입니다. 수익을 최대한 보존하면서 하락 시 빠져나옵니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `price_gap_percent` | float | 0.5 | 현재가 대비 주문가 차이 (%) |
| `max_modifications` | int | 5 | 최대 정정 횟수 |
| `trail_ratio` | float | 0.3 | 추적 비율 (수익% x 비율 = 허용 하락%) |

```json
{
  "id": "trailingStop",
  "type": "ConditionNode",
  "plugin": "TrailingStop",
  "fields": {"price_gap_percent": 0.5, "max_modifications": 5, "trail_ratio": 0.3}
}
```

> **예시**: `trail_ratio`가 0.3일 때, 수익률 5% → 허용 하락 1.5%, 수익률 10% → 허용 하락 3%. 수익이 커질수록 더 많은 하락을 허용하여 이익을 극대화합니다.

---

## 여러 조건 조합하기

여러 플러그인의 결과를 **LogicNode**로 조합할 수 있습니다.

```json
{
  "nodes": [
    {"id": "rsi", "type": "ConditionNode", "plugin": "RSI", "data": "{{ nodes.history.values }}", "fields": {"period": 14, "threshold": 30, "direction": "below"}},
    {"id": "macd", "type": "ConditionNode", "plugin": "MACD", "data": "{{ nodes.history.values }}", "fields": {"signal_type": "bullish_cross"}},
    {"id": "adx", "type": "ConditionNode", "plugin": "ADX", "data": "{{ nodes.history.values }}", "fields": {"threshold": 25, "direction": "uptrend"}},
    {
      "id": "logic",
      "type": "LogicNode",
      "operator": "all",
      "inputs": ["{{ nodes.rsi }}", "{{ nodes.macd }}", "{{ nodes.adx }}"]
    }
  ],
  "edges": [
    {"from": "history", "to": "rsi"},
    {"from": "history", "to": "macd"},
    {"from": "history", "to": "adx"},
    {"from": "rsi", "to": "logic"},
    {"from": "macd", "to": "logic"},
    {"from": "adx", "to": "logic"}
  ]
}
```

이 예시는 **RSI 과매도 + MACD 골든크로스 + ADX 상승추세** 세 조건이 모두 만족할 때만 매수합니다.

> 자세한 조합 방법은 [조건 조합 가이드](../logic_guide.md)를 참고하세요.
