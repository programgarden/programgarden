# 종목조건 플러그인

종목 매수/매도 조건을 판단하는 플러그인들입니다. `ConditionNode`에서 `plugin` 필드로 지정하여 사용합니다.

원하는 플러그인이 없다면:
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

### 전체 플러그인 (77개)

| 분류 | 플러그인 | 설명 |
|------|---------|------|
| **모멘텀** | RSI | RSI 과매수/과매도 |
| | MACD | MACD 골든/데드크로스 |
| | Stochastic | 스토캐스틱 %K/%D 크로스 |
| | OBV | 거래량 기반 매매 압력 |
| | WilliamsR | 윌리엄스 %R 오실레이터 |
| | CCI | 상품채널지수 (과매수/과매도) |
| | TRIX | 삼중지수이동평균 노이즈 제거 |
| | ConnorsRSI | RSI + 연속등락 + 이격률 결합 모멘텀 |
| | MFI | 자금흐름지수 (가격+거래량 기반) |
| | CoppockCurve | 장기 바닥 탐지 (ROC 평활화) |
| | TimeSeriesMomentum | 시계열 모멘텀 (절대/상대/위험조정) |
| **추세** | ADX | 추세 강도 측정 |
| | MovingAverageCross | 이동평균 골든/데드크로스 |
| | DualMomentum | 듀얼모멘텀 (절대+상대) |
| | BreakoutRetest | 돌파 후 되돌림 매매 |
| | IchimokuCloud | 일목균형표 (구름대) |
| | ParabolicSAR | 파라볼릭 SAR 추세 반전 |
| | Supertrend | ATR 기반 슈퍼트렌드 |
| | ElderRay | 엘더레이 (Bull/Bear Power + EMA) |
| **변동성** | BollingerBands | 볼린저밴드 이탈 |
| | ATR | ATR 변동성 돌파 |
| | PriceChannel | 돈치안 채널 돌파 |
| | GoldenRatio | 피보나치 되돌림 |
| | KeltnerChannel | 켈트너 채널 (스퀴즈) |
| | SqueezeMomentum | BB+KC 스퀴즈 발화 + 선형회귀 모멘텀 |
| | TurtleBreakout | 터틀 채널 돌파 (20/55일 고가/저가) |
| | VolatilityBreakout | 변동성 돌파 전략 (레인지 대비 돌파) |
| **가격 레벨** | PivotPoint | 피봇 포인트 (S/R 레벨) |
| | VWAP | 거래량가중평균가격 |
| | SupportResistanceLevels | Swing 기반 지지/저항 레벨 감지+클러스터링 |
| | LevelTouch | 레벨 터치/돌파/역할전환 감지 |
| **패턴** | ThreeLineStrike | 삼선 타격 (4봉 반전) |
| | Engulfing | 장악형 (불리시/베어리시) |
| | HammerShootingStar | 망치/유성형 (반전) |
| | Doji | 도지 (추세 전환 경고) |
| | MorningEveningStar | 샛별/석별형 (3봉 반전) |
| **거래량** | VolumeSpike | 거래량 급증 감지 |
| | CMF | 차이킨 자금흐름 (매집/분산) |
| **평균회귀** | MeanReversion | 이평선 이탈 회귀 |
| | ZScore | 표준편차 정규화 과매수/과매도 (종목 간 비교 가능) |
| | PairTrading | 페어 스프레드 Z-Score 기반 평균회귀 매매신호 |
| **시장 분석** | RegimeDetection | 시장 레짐 감지 (bull/bear/sideways) |
| | RelativeStrength | 벤치마크 대비 상대 강도 |
| | CorrelationAnalysis | 자산 간 상관관계 분석 |
| | MomentumRank | 유니버스 전체 모멘텀 순위 기반 상위/하위 선별 |
| | MarketInternals | 시장 내부 건강도 (AD비율, MA위 비율, 복합점수) |
| | SeasonalFilter | 계절성 패턴 필터 (월별/요일별) |
| | TacticalAssetAllocation | 전술적 자산배분 (모멘텀+SMA 기반) |
| **복합 전략** | MagicFormula | 마법공식 (수익률+모멘텀 결합 순위) |
| **멀티타임프레임** | MultiTimeframeConfirmation | 다중 시간프레임 MA 정렬 확인 |
| **다이버전스** | RSIDivergence | 가격-RSI 괴리 감지 (강세/약세 다이버전스) |
| **아시아 지표** | KDJ | K/D/J 라인 (스토캐스틱 확장, 한중일 인기) |
| **추세 감지** | Aroon | 아룬 Up/Down 추세 방향+강도 |
| | HeikinAshi | 하이킨아시 캔들 노이즈 제거+추세 신호 |
| | VortexIndicator | +VI/-VI 크로스 추세 방향 판단 |
| **멀티 기간** | UltimateOscillator | Larry Williams 3기간(7,14,28) 가중 오실레이터 |
| **레짐 분석** | HurstExponent | 허스트 지수 (추세/평균회귀/랜덤워크 분류) |
| **선물 전용** | ContangoBackwardation | 콘탱고/백워데이션 감지 |
| | CalendarSpread | 캘린더 스프레드 Z-score |
| **포지션 관리** | ProfitTarget | 목표 수익률 익절 |
| | StopLoss | 손절 조건 |
| | TrailingStop | 추적 손절 (비율 기반) |
| | PartialTakeProfit | 분할 익절 (다단계 매도) |
| | TimeBasedExit | 시간 기반 청산 (보유일 관리) |
| **포지션 보호** | DrawdownProtection | 낙폭 보호 (HWM 연동) |
| | VolatilityPositionSizing | 변동성 기반 포지션 사이징 |
| | RollManagement | 선물 롤오버 관리 |
| | DynamicStopLoss | ATR 기반 동적 손절 (변동성 적응형) |
| | MaxPositionLimit | 종목 수/비중/총가치 한도 관리 |
| **퀀트 위험관리** | KellyCriterion | 켈리 기준 포지션 사이징 |
| | RiskParity | 리스크 패리티 배분 (역변동성) |
| | VarCvarMonitor | VaR/CVaR 모니터링 |
| | CorrelationGuard | 상관관계 가드 (레짐 감시) |
| | BetaHedge | 베타 헷지 (포트폴리오 베타 관리) |
| **성과 비율** | SharpeRatioMonitor | 연율화 샤프비율 실시간 모니터링 |
| | SortinoRatio | 소르티노 비율 (하방 위험 조정 수익률) |
| | CalmarRatio | 칼마 비율 (CAGR / 최대낙폭) |

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

## 가격 레벨 지표

### PivotPoint (피봇 포인트)

전일 고가/저가/종가를 이용해 **오늘의 지지선(S1~S3)과 저항선(R1~R3)**을 계산합니다. 데이 트레이더와 스윙 트레이더가 가장 많이 사용하는 가격 레벨 도구입니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `pivot_type` | string | "standard" | 계산 방식 (`standard`, `fibonacci`, `camarilla`) |
| `direction` | string | "support" | `support`: 지지선 근접(매수), `resistance`: 저항선 근접(매도) |
| `tolerance` | float | 0.01 | 레벨 근접 허용 범위 (0.005~0.05) |

```json
{
  "id": "pivot",
  "type": "ConditionNode",
  "plugin": "PivotPoint",
  "data": "{{ nodes.history.values }}",
  "fields": {"pivot_type": "standard", "direction": "support", "tolerance": 0.01}
}
```

**계산 방식:**
- **Standard**: PP=(H+L+C)/3, S1=2×PP-H, R1=2×PP-L
- **Fibonacci**: PP 기준 피보나치 비율(38.2%, 61.8%) 적용
- **Camarilla**: 레인지(H-L) 기반으로 더 촘촘한 레벨 생성

> **팁**: Standard가 가장 보편적입니다. Camarilla는 단기 트레이딩에 적합합니다.

> **필요 데이터**: 최소 2일의 고가(high), 저가(low), 종가(close)

---

## 패턴 지표

### ThreeLineStrike (삼선 타격)

**3연속 동일 방향 캔들 후 반전 캔들**을 감지합니다. 예를 들어 3일 연속 하락 후 이를 전부 되돌리는 대형 양봉이 나오면 강한 반등 신호입니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `pattern` | string | "bullish" | `bullish`: 하락 후 반전(매수), `bearish`: 상승 후 반전(매도) |
| `min_body_pct` | float | 0.3 | 캔들 몸통 최소 비율 (0.1~1.0) |

```json
{
  "id": "threeLineStrike",
  "type": "ConditionNode",
  "plugin": "ThreeLineStrike",
  "data": "{{ nodes.history.values }}",
  "fields": {"pattern": "bullish", "min_body_pct": 0.3}
}
```

**패턴 설명:**
- **Bullish**: 3연속 음봉 + 4번째 양봉이 3개 음봉 전체를 감싸는 패턴 → 매수
- **Bearish**: 3연속 양봉 + 4번째 음봉이 전체를 감싸는 패턴 → 매도
- `min_body_pct`: 캔들 몸통이 전체 범위(고가-저가) 대비 최소 비율. 작은 값은 도지/스피닝탑 허용

> **필요 데이터**: 최소 4일의 시가(open), 고가(high), 저가(low), 종가(close)

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
      "conditions": [
        {"is_condition_met": "{{ nodes.rsi.result }}", "passed_symbols": "{{ nodes.rsi.passed_symbols }}"},
        {"is_condition_met": "{{ nodes.macd.result }}", "passed_symbols": "{{ nodes.macd.passed_symbols }}"},
        {"is_condition_met": "{{ nodes.adx.result }}", "passed_symbols": "{{ nodes.adx.passed_symbols }}"}
      ]
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

---

## 추세 지표 (확장)

### IchimokuCloud (일목균형표)

**텐칸센, 기준선, 구름대**를 종합적으로 분석합니다. 가격이 구름대 위에 있으면 상승 추세, 아래에 있으면 하락 추세입니다. 텐칸센/기준선 크로스도 매매 신호로 활용합니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `tenkan_period` | int | 9 | 전환선 기간 (1~50) |
| `kijun_period` | int | 26 | 기준선 기간 (1~100) |
| `senkou_b_period` | int | 52 | 선행스팬B 기간 (1~200) |
| `signal_type` | string | "price_above_cloud" | 시그널 타입 |

**signal_type 옵션:**
- `price_above_cloud`: 가격이 구름대 위 (상승 추세 확인)
- `price_below_cloud`: 가격이 구름대 아래 (하락 추세 확인)
- `tk_cross_bullish`: 텐칸센이 기준선 상향 돌파 (매수)
- `tk_cross_bearish`: 텐칸센이 기준선 하향 돌파 (매도)
- `cloud_bullish`: 선행스팬A > B (구름 상승 전환)
- `cloud_bearish`: 선행스팬A < B (구름 하락 전환)

```json
{
  "id": "ichimoku",
  "type": "ConditionNode",
  "plugin": "IchimokuCloud",
  "items": {
    "from": "{{ item.time_series }}",
    "extract": {
      "symbol": "{{ item.symbol }}", "exchange": "{{ item.exchange }}",
      "date": "{{ row.date }}", "high": "{{ row.high }}",
      "low": "{{ row.low }}", "close": "{{ row.close }}"
    }
  },
  "fields": {"tenkan_period": 9, "kijun_period": 26, "senkou_b_period": 52, "signal_type": "price_above_cloud"}
}
```

> **팁**: 일목균형표는 단독으로 사용해도 충분한 종합 지표입니다. 구름대 위 + 텐칸/기준 골든크로스가 동시에 발생하면 강력한 매수 신호입니다.

> **필요 데이터**: 최소 52일(senkou_b_period)의 고가, 저가, 종가

---

### ParabolicSAR (파라볼릭 SAR)

가격 위/아래에 점(SAR)을 찍어 **추세 방향과 반전점**을 표시합니다. SAR이 가격 아래에 있으면 상승 추세, 위에 있으면 하락 추세입니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `af_start` | float | 0.02 | 가속인자 초기값 (0.01~0.05) |
| `af_step` | float | 0.02 | 가속인자 증가분 (0.01~0.05) |
| `af_max` | float | 0.20 | 가속인자 최대값 (0.1~0.5) |
| `signal_type` | string | "bullish_reversal" | 시그널 타입 |

**signal_type 옵션:**
- `bullish_reversal`: SAR이 가격 아래로 전환 (하락→상승 반전, 매수)
- `bearish_reversal`: SAR이 가격 위로 전환 (상승→하락 반전, 매도)
- `uptrend`: 현재 상승 추세 (SAR < 가격)
- `downtrend`: 현재 하락 추세 (SAR > 가격)

```json
{
  "id": "sar",
  "type": "ConditionNode",
  "plugin": "ParabolicSAR",
  "items": {
    "from": "{{ item.time_series }}",
    "extract": {
      "symbol": "{{ item.symbol }}", "exchange": "{{ item.exchange }}",
      "date": "{{ row.date }}", "high": "{{ row.high }}",
      "low": "{{ row.low }}", "close": "{{ row.close }}"
    }
  },
  "fields": {"af_start": 0.02, "af_step": 0.02, "af_max": 0.20, "signal_type": "bullish_reversal"}
}
```

> **필요 데이터**: 고가, 저가, 종가. 최소 10일 데이터

---

### Supertrend (슈퍼트렌드)

**ATR(평균진폭) 기반**의 추세 추종 지표입니다. 가격이 Supertrend 위에 있으면 상승, 아래에 있으면 하락 추세입니다. 시그널이 명확하여 초보자도 쉽게 활용 가능합니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `atr_period` | int | 10 | ATR 계산 기간 (1~50) |
| `multiplier` | float | 3.0 | ATR 배수 (1.0~5.0) |
| `signal_type` | string | "bullish" | 시그널 타입 |

**signal_type 옵션:**
- `bullish`: 하락→상승 전환 (매수)
- `bearish`: 상승→하락 전환 (매도)
- `uptrend`: 현재 상승 추세
- `downtrend`: 현재 하락 추세

```json
{
  "id": "supertrend",
  "type": "ConditionNode",
  "plugin": "Supertrend",
  "items": {
    "from": "{{ item.time_series }}",
    "extract": {
      "symbol": "{{ item.symbol }}", "exchange": "{{ item.exchange }}",
      "date": "{{ row.date }}", "high": "{{ row.high }}",
      "low": "{{ row.low }}", "close": "{{ row.close }}"
    }
  },
  "fields": {"atr_period": 10, "multiplier": 3.0, "signal_type": "uptrend"}
}
```

> **팁**: `multiplier`가 클수록 노이즈가 줄어 신호가 적지만 정확도가 높습니다. 단타는 2.0, 중장기는 3.0~4.0을 추천합니다.

---

## 모멘텀 지표 (확장)

### WilliamsR (윌리엄스 %R)

Stochastic과 유사하나 **역전된 스케일(-100~0)**을 사용합니다. -80 이하이면 과매도(매수 기회), -20 이상이면 과매수(매도 기회)입니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `period` | int | 14 | 계산 기간 (2~100) |
| `threshold` | float | -80 | 과매도/과매수 기준값 (-100~0) |
| `direction` | string | "below" | `below`: 과매도(매수), `above`: 과매수(매도) |

```json
{
  "id": "williams",
  "type": "ConditionNode",
  "plugin": "WilliamsR",
  "items": {
    "from": "{{ item.time_series }}",
    "extract": {
      "symbol": "{{ item.symbol }}", "exchange": "{{ item.exchange }}",
      "date": "{{ row.date }}", "high": "{{ row.high }}",
      "low": "{{ row.low }}", "close": "{{ row.close }}"
    }
  },
  "fields": {"period": 14, "threshold": -80, "direction": "below"}
}
```

> **팁**: RSI와 함께 사용하면 과매도 신호의 정확도가 높아집니다. `LogicNode(all)`로 두 조건을 동시에 확인하세요.

> **필요 데이터**: 고가, 저가, 종가. 최소 `period`일 데이터

---

### CCI (Commodity Channel Index)

**전형적인 가격(TP)**의 이동평균으로부터의 편차를 측정합니다. +100 이상이면 과매수, -100 이하이면 과매도입니다. 해외선물 트레이더에게 핵심 지표입니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `period` | int | 20 | CCI 계산 기간 (5~100) |
| `threshold` | float | 100 | 과매수/과매도 기준값 (50~300) |
| `direction` | string | "below" | `below`: 과매도(-100 이하, 매수), `above`: 과매수(+100 이상, 매도) |

```json
{
  "id": "cci",
  "type": "ConditionNode",
  "plugin": "CCI",
  "items": {
    "from": "{{ item.time_series }}",
    "extract": {
      "symbol": "{{ item.symbol }}", "exchange": "{{ item.exchange }}",
      "date": "{{ row.date }}", "high": "{{ row.high }}",
      "low": "{{ row.low }}", "close": "{{ row.close }}"
    }
  },
  "fields": {"period": 20, "threshold": -100, "direction": "below"}
}
```

> **필요 데이터**: 고가, 저가, 종가. 최소 `period`일 데이터

---

### TRIX (삼중지수이동평균)

EMA를 3번 적용하여 **노이즈를 제거**하고 중장기 추세를 파악합니다. TRIX 값과 시그널선 교차로 매매 신호를 발생시킵니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `period` | int | 15 | EMA 기간 (5~50) |
| `signal_period` | int | 9 | 시그널선 기간 (3~20) |
| `signal_type` | string | "bullish_cross" | 시그널 타입 |

**signal_type 옵션:**
- `bullish_cross`: TRIX가 시그널선 상향 돌파 (매수)
- `bearish_cross`: TRIX가 시그널선 하향 돌파 (매도)
- `above_zero`: TRIX > 0 (상승 추세)
- `below_zero`: TRIX < 0 (하락 추세)

```json
{
  "id": "trix",
  "type": "ConditionNode",
  "plugin": "TRIX",
  "items": {
    "from": "{{ item.time_series }}",
    "extract": {
      "symbol": "{{ item.symbol }}", "exchange": "{{ item.exchange }}",
      "date": "{{ row.date }}", "close": "{{ row.close }}"
    }
  },
  "fields": {"period": 15, "signal_period": 9, "signal_type": "bullish_cross"}
}
```

> **팁**: TRIX는 MACD보다 노이즈에 강합니다. 중장기 추세를 확인할 때 유용합니다.

---

## 변동성 지표 (확장)

### KeltnerChannel (켈트너 채널)

**EMA + ATR 기반** 채널입니다. 볼린저밴드와 함께 사용하면 "스퀴즈" 전략이 가능합니다. 볼린저밴드가 켈트너 채널 안으로 들어오면 변동성 축소 → 큰 움직임 예고입니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `ema_period` | int | 20 | EMA 기간 (5~50) |
| `atr_period` | int | 10 | ATR 기간 (5~50) |
| `atr_multiplier` | float | 2.0 | ATR 배수 (1.0~4.0) |
| `direction` | string | "above_upper" | 시그널 방향 |

**direction 옵션:**
- `above_upper`: 가격이 상단 밴드 위 (강한 상승 돌파)
- `below_lower`: 가격이 하단 밴드 아래 (강한 하락 돌파)
- `squeeze`: 변동성 축소 (볼린저밴드와 조합 시 폭발적 움직임 예고)

```json
{
  "id": "keltner",
  "type": "ConditionNode",
  "plugin": "KeltnerChannel",
  "items": {
    "from": "{{ item.time_series }}",
    "extract": {
      "symbol": "{{ item.symbol }}", "exchange": "{{ item.exchange }}",
      "date": "{{ row.date }}", "high": "{{ row.high }}",
      "low": "{{ row.low }}", "close": "{{ row.close }}"
    }
  },
  "fields": {"ema_period": 20, "atr_period": 10, "atr_multiplier": 2.0, "direction": "squeeze"}
}
```

> **팁**: BollingerBands + KeltnerChannel `squeeze` 조합은 TTM Squeeze 전략의 핵심입니다.

---

## 가격 레벨 지표 (확장)

### VWAP (거래량가중평균가격)

**거래량 가중 평균가격**입니다. 기관투자자가 가장 많이 참고하는 지표로, 가격이 VWAP 위에 있으면 매수 우위, 아래에 있으면 매도 우위입니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `direction` | string | "above" | `above`: VWAP 위(매수 우위), `below`: VWAP 아래(매도 우위) |
| `band_multiplier` | float | 0.0 | VWAP 밴드 표준편차 배수 (0=밴드 없음, 1.0~3.0) |

```json
{
  "id": "vwap",
  "type": "ConditionNode",
  "plugin": "VWAP",
  "items": {
    "from": "{{ item.time_series }}",
    "extract": {
      "symbol": "{{ item.symbol }}", "exchange": "{{ item.exchange }}",
      "date": "{{ row.date }}", "high": "{{ row.high }}",
      "low": "{{ row.low }}", "close": "{{ row.close }}", "volume": "{{ row.volume }}"
    }
  },
  "fields": {"direction": "above", "band_multiplier": 0}
}
```

> **팁**: `band_multiplier: 2.0`으로 설정하면 VWAP ± 2표준편차 밴드가 생성됩니다. 밴드 하단 터치 시 매수, 상단 터치 시 매도 전략에 활용합니다.

> **필요 데이터**: 종가, 거래량 (고가/저가는 선택)

---

## 거래량 지표 (확장)

### CMF (Chaikin Money Flow)

**매집(accumulation)과 분산(distribution)**을 거래량으로 측정합니다. CMF가 양수이면 매수세 유입(매집), 음수이면 매도세 유입(분산)입니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `period` | int | 20 | CMF 계산 기간 (5~50) |
| `direction` | string | "accumulation" | `accumulation`: 매집(CMF > 0), `distribution`: 분산(CMF < 0) |

```json
{
  "id": "cmf",
  "type": "ConditionNode",
  "plugin": "CMF",
  "items": {
    "from": "{{ item.time_series }}",
    "extract": {
      "symbol": "{{ item.symbol }}", "exchange": "{{ item.exchange }}",
      "date": "{{ row.date }}", "high": "{{ row.high }}",
      "low": "{{ row.low }}", "close": "{{ row.close }}", "volume": "{{ row.volume }}"
    }
  },
  "fields": {"period": 20, "direction": "accumulation"}
}
```

> **팁**: OBV와 함께 사용하면 거래량 분석의 정확도가 높아집니다. CMF(매집) + OBV(상승) 동시 충족 시 강한 매수 신호입니다.

> **필요 데이터**: 고가, 저가, 종가, 거래량

---

## 캔들스틱 패턴

### Engulfing (장악형)

이전 캔들을 완전히 감싸는 **반전 패턴**입니다. 캔들스틱 패턴 중 가장 신뢰도가 높습니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `direction` | string | "bullish" | `bullish`: 불리시 장악(매수), `bearish`: 베어리시 장악(매도) |
| `min_body_ratio` | float | 0.3 | 캔들 몸통 최소 비율 (0.1~1.0) |

```json
{
  "id": "engulfing",
  "type": "ConditionNode",
  "plugin": "Engulfing",
  "items": {
    "from": "{{ item.time_series }}",
    "extract": {
      "symbol": "{{ item.symbol }}", "exchange": "{{ item.exchange }}",
      "date": "{{ row.date }}", "open": "{{ row.open }}", "high": "{{ row.high }}",
      "low": "{{ row.low }}", "close": "{{ row.close }}"
    }
  },
  "fields": {"direction": "bullish", "min_body_ratio": 0.3}
}
```

**패턴 설명:**
- **Bullish Engulfing**: 음봉 → 큰 양봉이 전체를 감싸는 패턴 → 매수
- **Bearish Engulfing**: 양봉 → 큰 음봉이 전체를 감싸는 패턴 → 매도

> **필요 데이터**: 시가, 고가, 저가, 종가. 최소 2일 데이터

---

### HammerShootingStar (망치/유성형)

**긴 꼬리**를 가진 반전 캔들 패턴입니다. 망치형은 하락 후 반등, 유성형은 상승 후 하락 전환을 예고합니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `direction` | string | "hammer" | `hammer`: 망치형(매수), `shooting_star`: 유성형(매도) |
| `shadow_ratio` | float | 2.0 | 꼬리/몸통 최소 비율 (1.5~5.0) |
| `body_position` | float | 0.33 | 몸통이 전체 범위 상단/하단 N% 이내 |

```json
{
  "id": "hammer",
  "type": "ConditionNode",
  "plugin": "HammerShootingStar",
  "items": {
    "from": "{{ item.time_series }}",
    "extract": {
      "symbol": "{{ item.symbol }}", "exchange": "{{ item.exchange }}",
      "date": "{{ row.date }}", "open": "{{ row.open }}", "high": "{{ row.high }}",
      "low": "{{ row.low }}", "close": "{{ row.close }}"
    }
  },
  "fields": {"direction": "hammer", "shadow_ratio": 2.0, "body_position": 0.33}
}
```

**패턴 설명:**
- **Hammer**: 긴 아래꼬리 + 작은 몸통이 상단에 위치. 하락 후 반등 신호
- **Shooting Star**: 긴 위꼬리 + 작은 몸통이 하단에 위치. 상승 후 하락 신호

---

### Doji (도지)

시가와 종가가 거의 같은 **십자형 캔들**입니다. 매수와 매도 세력이 균형을 이루며, 추세 전환의 경고 신호입니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `body_pct` | float | 10.0 | 몸통/전체범위 최대 비율 (%, 5~20) |
| `doji_type` | string | "any" | 도지 유형 |

**doji_type 옵션:**
- `any`: 모든 도지
- `standard`: 일반 도지 (십자형)
- `long_legged`: 장다리 도지 (긴 위아래 꼬리)
- `dragonfly`: 잠자리 도지 (긴 아래꼬리, 위꼬리 거의 없음)
- `gravestone`: 비석 도지 (긴 위꼬리, 아래꼬리 거의 없음)

```json
{
  "id": "doji",
  "type": "ConditionNode",
  "plugin": "Doji",
  "items": {
    "from": "{{ item.time_series }}",
    "extract": {
      "symbol": "{{ item.symbol }}", "exchange": "{{ item.exchange }}",
      "date": "{{ row.date }}", "open": "{{ row.open }}", "high": "{{ row.high }}",
      "low": "{{ row.low }}", "close": "{{ row.close }}"
    }
  },
  "fields": {"body_pct": 10.0, "doji_type": "any"}
}
```

> **팁**: 도지 단독으로는 방향 판단이 어렵습니다. RSI 과매도 + 도지 출현 시 반등 가능성이 높습니다.

---

### MorningEveningStar (샛별/석별형)

**3봉 반전 패턴**입니다. 큰 음봉 → 작은 봉 → 큰 양봉이 나오면 샛별형(매수), 반대이면 석별형(매도)입니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `direction` | string | "morning_star" | `morning_star`: 샛별형(매수), `evening_star`: 석별형(매도) |
| `star_body_max` | float | 30.0 | 가운데 봉 몸통 최대 비율 (%, 10~50) |
| `confirmation_ratio` | float | 0.5 | 3번째 봉이 1번째 봉 몸통의 N% 이상 회복 |

```json
{
  "id": "morningStar",
  "type": "ConditionNode",
  "plugin": "MorningEveningStar",
  "items": {
    "from": "{{ item.time_series }}",
    "extract": {
      "symbol": "{{ item.symbol }}", "exchange": "{{ item.exchange }}",
      "date": "{{ row.date }}", "open": "{{ row.open }}", "high": "{{ row.high }}",
      "low": "{{ row.low }}", "close": "{{ row.close }}"
    }
  },
  "fields": {"direction": "morning_star", "star_body_max": 30.0, "confirmation_ratio": 0.5}
}
```

> **필요 데이터**: 시가, 고가, 저가, 종가. 최소 3일 데이터

---

## 포지션 관리 지표 (확장)

### PartialTakeProfit (분할 익절)

**여러 단계에서 분할 매도**하여 리스크를 줄이면서 수익을 확보합니다. 수익률 5%에서 50% 매도, 10%에서 30% 매도처럼 단계별 매도를 자동 실행합니다. `strategy_state`로 완료된 단계를 추적합니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `levels` | string/array | `[{"pnl_pct":5,"sell_pct":50},{"pnl_pct":10,"sell_pct":30},{"pnl_pct":20,"sell_pct":20}]` | 익절 단계 배열 (JSON) |

**levels 배열 항목:**
- `pnl_pct`: 트리거 수익률 (%)
- `sell_pct`: 해당 단계에서 매도할 비율 (%, 최초 수량 기준)

```json
{
  "id": "partialTP",
  "type": "ConditionNode",
  "plugin": "PartialTakeProfit",
  "positions": "{{ nodes.account.positions }}",
  "fields": {
    "levels": [
      {"pnl_pct": 5, "sell_pct": 50},
      {"pnl_pct": 10, "sell_pct": 30},
      {"pnl_pct": 20, "sell_pct": 20}
    ]
  }
}
```

**동작 방식:**
1. 수익률 5% 도달 → 보유량의 50% 매도 (1단계 완료 저장)
2. 수익률 10% 도달 → 최초 수량의 30% 매도 (2단계 완료 저장)
3. 수익률 20% 도달 → 최초 수량의 20% 매도 (3단계 완료 저장)
4. 포지션 전량 청산 시 → 상태 자동 삭제

> **주의**: `positions` 기반 플러그인입니다. `RealAccountNode`의 출력을 연결하세요.

---

### TimeBasedExit (시간 기반 청산)

보유 기간이 설정된 일수를 초과하면 **자동 청산 시그널**을 발생시킵니다. 진입일을 자동 추적하며, `strategy_state`에 저장합니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `max_hold_days` | int | 5 | 최대 보유 일수 (1~365) |
| `warn_days` | int | 0 | 경고 시작 일수 (0=비활성, 1~365) |

```json
{
  "id": "timeExit",
  "type": "ConditionNode",
  "plugin": "TimeBasedExit",
  "positions": "{{ nodes.account.positions }}",
  "fields": {"max_hold_days": 10, "warn_days": 3}
}
```

**동작 방식:**
1. 포지션 최초 감지 시 → 오늘 날짜를 진입일로 저장
2. 매 실행마다 보유 일수 계산 (오늘 - 진입일)
3. `max_hold_days` 초과 → `passed_symbols`에 포함 (청산 시그널)
4. `warn_days` 설정 시 → 만기 N일 전부터 경고 (action: "warn")
5. 포지션 청산 시 → 상태 자동 삭제

> **팁**: 스윙 트레이딩에서 5~10일, 단기 트레이딩에서 2~3일로 설정합니다. `warn_days`로 미리 경고를 받으면 수동 판단도 가능합니다.

> **주의**: `positions` 기반 플러그인입니다. `RealAccountNode`의 출력을 연결하세요.

---

## 시장 분석 지표

### RegimeDetection (시장 레짐 감지)

MA 기울기, ADX, 변동성 백분위를 조합하여 현재 시장 상태를 **bull/bear/sideways로 분류**합니다. 적응형 전략에서 시장 환경에 따라 다른 플러그인을 선택할 때 활용합니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `ma_period` | int | 20 | 이동평균 기간 (5~200) |
| `adx_period` | int | 14 | ADX 기간 (5~50) |
| `adx_threshold` | float | 25.0 | 추세 강도 임계값 (15~50) |
| `vol_lookback` | int | 60 | 변동성 백분위 계산 기간 (20~252) |

```json
{
  "id": "regime",
  "type": "ConditionNode",
  "plugin": "RegimeDetection",
  "data": "{{ nodes.history.values }}",
  "fields": {"ma_period": 20, "adx_period": 14, "adx_threshold": 25, "vol_lookback": 60}
}
```

**레짐 분류 기준:**
- **bull**: 가격 > MA & ADX > 임계값 (강한 상승 추세)
- **bear**: 가격 < MA & ADX > 임계값 (강한 하락 추세)
- **sideways**: ADX < 임계값 (추세 없음, 횡보)

> **필요 데이터**: 종가(close), 고가(high), 저가(low). 최소 `vol_lookback`일 데이터

---

### RelativeStrength (상대 강도)

벤치마크(SPY 등) 대비 종목별 **상대 수익률을 계산하고 순위를 매깁니다**. 아웃퍼포머와 언더퍼포머를 식별하여 모멘텀 전략에 활용합니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `lookback` | int | 60 | 수익률 계산 기간 |
| `benchmark_symbol` | string | "SPY" | 벤치마크 종목 |
| `rank_method` | string | "raw" | 순위 방법 (`raw`, `percentile`, `z_score`) |
| `threshold` | float | 0.0 | 임계값 |
| `direction` | string | "above" | `above`: 아웃퍼포머, `below`: 언더퍼포머 |

```json
{
  "id": "rs",
  "type": "ConditionNode",
  "plugin": "RelativeStrength",
  "data": "{{ nodes.history.values }}",
  "fields": {"lookback": 60, "benchmark_symbol": "SPY", "rank_method": "percentile", "threshold": 50, "direction": "above"}
}
```

> **필요 데이터**: 벤치마크와 종목들의 종가(close). 최소 `lookback`일 데이터

---

### CorrelationAnalysis (상관관계 분석)

포트폴리오 내 종목들 간 **Pearson 또는 Spearman 상관관계를 계산**합니다. 분산 투자 효과를 확인할 때 활용합니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `lookback` | int | 60 | 상관 계산 기간 |
| `method` | string | "pearson" | `pearson` 또는 `spearman` |
| `threshold` | float | 0.7 | 상관 임계값 (0~1) |
| `direction` | string | "above" | `above`: 높은 상관 감지, `below`: 낮은 상관 감지 |

```json
{
  "id": "corr",
  "type": "ConditionNode",
  "plugin": "CorrelationAnalysis",
  "data": "{{ nodes.history.values }}",
  "fields": {"lookback": 60, "method": "pearson", "threshold": 0.7, "direction": "above"}
}
```

> **필요 데이터**: 2개 이상 종목의 종가(close). 최소 `lookback`일 데이터

---

## 멀티타임프레임 지표

### MultiTimeframeConfirmation (다중 시간프레임 확인)

단기/중기/장기 **3개 시간프레임의 MA 정렬을 확인**합니다. 모든 시간프레임이 같은 방향이면 강한 추세 신호입니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `short_period` | int | 5 | 단기 MA 기간 |
| `medium_period` | int | 20 | 중기 MA 기간 |
| `long_period` | int | 60 | 장기 MA 기간 |
| `direction` | string | "bullish" | `bullish`: 상승 정렬, `bearish`: 하락 정렬 |
| `require_all` | bool | true | `true`: 3/3 정렬 필수, `false`: 2/3 정렬 허용 |

```json
{
  "id": "mtf",
  "type": "ConditionNode",
  "plugin": "MultiTimeframeConfirmation",
  "data": "{{ nodes.history.values }}",
  "fields": {"short_period": 5, "medium_period": 20, "long_period": 60, "direction": "bullish", "require_all": true}
}
```

> **필요 데이터**: 종가(close). 최소 `long_period`일 데이터

---

## 선물 전용 지표

> **참고**: 이 플러그인들은 **해외선물 전용**입니다. 월물 코드(F=1월~Z=12월)를 심볼에서 파싱합니다.

### ContangoBackwardation (콘탱고/백워데이션)

선물 월물 간 가격 차이로 **콘탱고/백워데이션 상태를 감지**합니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `structure` | string | "contango" | `contango` 또는 `backwardation` |
| `spread_threshold` | float | 0.5 | 스프레드 임계값 (%) |

```json
{
  "id": "contango",
  "type": "ConditionNode",
  "plugin": "ContangoBackwardation",
  "positions": "{{ nodes.account.positions }}",
  "fields": {"structure": "contango", "spread_threshold": 0.5}
}
```

> **주의**: `positions` 기반. 최소 2개 이상의 서로 다른 만기 월물이 필요합니다.

---

### CalendarSpread (캘린더 스프레드)

두 만기 월물 간 **스프레드의 Z-score를 계산**합니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `lookback` | int | 20 | Z-score 계산 기간 |
| `z_threshold` | float | 2.0 | Z-score 임계값 |
| `strategy` | string | "mean_revert" | `mean_revert` 또는 `momentum` |

```json
{
  "id": "calendar",
  "type": "ConditionNode",
  "plugin": "CalendarSpread",
  "positions": "{{ nodes.account.positions }}",
  "fields": {"lookback": 20, "z_threshold": 2.0, "strategy": "mean_revert"}
}
```

> **주의**: `positions` 기반. 최소 2개 이상의 서로 다른 만기 월물이 필요합니다.

---

## 포지션 보호 지표

### DrawdownProtection (낙폭 보호)

보유 종목의 **낙폭이 임계값을 초과하면 보호 행동을 트리거**합니다. WorkflowRiskTracker HWM 연동.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `max_drawdown_pct` | float | 10.0 | 최대 허용 낙폭 (%) |
| `action` | string | "exit_all" | `exit_all`, `reduce_half`, `stop_new_orders` |

```json
{
  "id": "ddProtect",
  "type": "ConditionNode",
  "plugin": "DrawdownProtection",
  "positions": "{{ nodes.account.positions }}",
  "fields": {"max_drawdown_pct": 10.0, "action": "exit_all"}
}
```

> **주의**: `positions` 기반. `risk_features: hwm, events` 사용.

---

### VolatilityPositionSizing (변동성 포지션 사이징)

각 종목의 실현 변동성을 기반으로 **최적 포지션 비중을 계산**합니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `vol_lookback` | int | 20 | 변동성 계산 기간 |
| `target_volatility` | float | 15.0 | 목표 변동성 (%) |
| `scaling_method` | string | "inverse_vol" | `inverse_vol`, `vol_target`, `equal_risk` |
| `max_position_pct` | float | 40.0 | 최대 비중 (%) |
| `min_position_pct` | float | 5.0 | 최소 비중 (%) |

```json
{
  "id": "volSizing",
  "type": "ConditionNode",
  "plugin": "VolatilityPositionSizing",
  "data": "{{ nodes.history.values }}",
  "fields": {"vol_lookback": 20, "scaling_method": "inverse_vol", "max_position_pct": 40, "min_position_pct": 5}
}
```

> **필요 데이터**: 시계열 종가(close). 최소 `vol_lookback + 1`일 데이터

---

### RollManagement (롤오버 관리)

선물 **만기일을 추적하여 롤오버 시점을 알려줍니다**. 해외선물 전용.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `days_before_expiry` | int | 5 | 만기 N일 전부터 알림 |

```json
{
  "id": "roll",
  "type": "ConditionNode",
  "plugin": "RollManagement",
  "positions": "{{ nodes.account.positions }}",
  "fields": {"days_before_expiry": 5}
}
```

> **주의**: `positions` 기반. `risk_features: state` 사용. 다음 월물 자동 계산 (예: HMCEG26 → HMCEH26).

---

## Tier 1 퀀트 전략

### ZScore (Z-Score 정규화)

가격이 평균에서 **몇 표준편차만큼 벗어났는지** 측정합니다. MeanReversion과 달리 표준편차 기반이라 종목 간 비교가 가능합니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `lookback` | int | 20 | 계산 기간 |
| `entry_threshold` | float | 2.0 | 진입 시그마 |
| `exit_threshold` | float | 0.5 | 청산 시그마 |
| `direction` | string | "below" | `below`: 과매도(매수), `above`: 과매수(매도) |

```json
{
  "id": "zscore",
  "type": "ConditionNode",
  "plugin": "ZScore",
  "data": "{{ nodes.history.values }}",
  "fields": {"lookback": 20, "entry_threshold": 2.0, "direction": "below"}
}
```

> **필요 데이터**: 최소 `lookback`일의 종가(close) 데이터

---

### SqueezeMomentum (스퀴즈 모멘텀)

볼린저밴드(BB)가 켈트너 채널(KC) 안쪽으로 들어가면 **변동성 수축(squeeze)**, 밖으로 나오면 **폭발적 움직임(fire)** 신호입니다. 선형회귀 모멘텀으로 방향을 판단합니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `bb_period` | int | 20 | 볼린저밴드 기간 |
| `bb_std` | float | 2.0 | 볼린저밴드 표준편차 |
| `kc_period` | int | 20 | 켈트너 채널 기간 |
| `kc_atr_period` | int | 10 | KC ATR 기간 |
| `kc_multiplier` | float | 1.5 | KC 배수 |
| `momentum_period` | int | 12 | 선형회귀 모멘텀 기간 |
| `direction` | string | "squeeze_fire_long" | `squeeze_on`/`squeeze_off`/`squeeze_fire_long`/`squeeze_fire_short` |

```json
{
  "id": "squeeze",
  "type": "ConditionNode",
  "plugin": "SqueezeMomentum",
  "data": "{{ nodes.history.values }}",
  "fields": {"direction": "squeeze_fire_long"}
}
```

> **필요 데이터**: 종가(close), 고가(high), 저가(low). 최소 `max(bb_period, kc_period) + kc_atr_period`일 데이터

---

### MomentumRank (모멘텀 순위)

유니버스 전체 종목의 **모멘텀(수익률)을 계산하고 순위를 매겨** 상위/하위 N개를 선별합니다. DualMomentum과 달리 유니버스 전체를 비교합니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `lookback` | int | 63 | 모멘텀 계산 기간 (거래일) |
| `top_n` | int | 5 | 선별 종목 수 (0이면 top_pct 사용) |
| `top_pct` | float | 0 | 선별 비율 (%) |
| `selection` | string | "top" | `top`: 상위, `bottom`: 하위 |
| `momentum_type` | string | "simple" | `simple`/`log`/`risk_adjusted` |

```json
{
  "id": "rank",
  "type": "ConditionNode",
  "plugin": "MomentumRank",
  "data": "{{ nodes.history.values }}",
  "fields": {"lookback": 63, "top_n": 3, "selection": "top"}
}
```

> **다중 종목 플러그인**: 모든 종목 데이터를 한번에 전달해야 합니다.

---

### MarketInternals (시장 내부 지표)

유니버스 전체의 **시장 건강도를 측정**합니다. 상승/하락 비율, MA 위 종목 비율, 신고/신저가 비율을 복합적으로 분석합니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `lookback` | int | 1 | 상승/하락 판단 기간 |
| `ma_period` | int | 50 | 이동평균 기간 |
| `high_low_period` | int | 52 | 신고/신저가 기간 |
| `metric` | string | "advance_decline_ratio" | `advance_decline_ratio`/`above_ma_pct`/`new_high_low_ratio`/`composite` |
| `threshold` | float | 60 | 임계값 (%) |
| `direction` | string | "above" | `above`/`below` |

```json
{
  "id": "market",
  "type": "ConditionNode",
  "plugin": "MarketInternals",
  "data": "{{ nodes.history.values }}",
  "fields": {"metric": "composite", "threshold": 50, "direction": "above"}
}
```

> **다중 종목 플러그인**: 유니버스 전체 데이터 필요. `market_health` 추가 필드로 시장 집계 반환.

---

### PairTrading (페어 트레이딩)

2종목의 **스프레드 Z-Score**로 평균회귀 매매신호를 생성합니다. CorrelationAnalysis와 달리 진입/청산 신호를 직접 제공합니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `symbol_a` | string | "" | 종목 A (미지정 시 자동 감지) |
| `symbol_b` | string | "" | 종목 B |
| `lookback` | int | 60 | 스프레드 계산 기간 |
| `entry_z` | float | 2.0 | 진입 Z-Score |
| `exit_z` | float | 0.5 | 청산 Z-Score |
| `spread_method` | string | "ratio" | `ratio`/`log_ratio`/`difference` |
| `correlation_min` | float | 0.5 | 최소 상관계수 |

```json
{
  "id": "pair",
  "type": "ConditionNode",
  "plugin": "PairTrading",
  "data": "{{ nodes.history.values }}",
  "fields": {"symbol_a": "AAPL", "symbol_b": "MSFT", "entry_z": 2.0}
}
```

> **risk_features**: `state` (페어 상태 추적). 2종목 데이터 필요.

---

### DynamicStopLoss (동적 손절)

**ATR(평균진폭)**을 기반으로 변동성에 적응하는 손절가를 산출합니다. StopLoss의 고정% 대신 변동성이 높으면 손절폭을 확대하고, 낮으면 축소합니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `atr_period` | int | 14 | ATR 계산 기간 |
| `atr_multiplier` | float | 2.0 | ATR 배수 (손절폭) |
| `trailing` | bool | false | 트레일링 모드 |

```json
{
  "id": "dynStop",
  "type": "ConditionNode",
  "plugin": "DynamicStopLoss",
  "data": "{{ nodes.history.values }}",
  "positions": "{{ nodes.account.positions }}",
  "fields": {"atr_period": 14, "atr_multiplier": 2.0}
}
```

> **필요 데이터**: 시계열(close, high, low) + 포지션 정보. 데이터 없으면 현재가 * 2% fallback.

---

### MaxPositionLimit (최대 포지션 한도)

보유 **종목 수, 총금액, 개별 비중**이 한도를 초과하는지 점검합니다. 초과 시 경고/신규매수 차단/초과분 청산 중 선택 가능합니다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `max_positions` | int | 10 | 최대 보유 종목 수 (0=무제한) |
| `max_total_value` | float | 0 | 최대 총 포지션 가치 (0=무제한) |
| `max_single_weight_pct` | float | 20 | 개별 종목 최대 비중 (%) |
| `action` | string | "warn" | `warn`/`block_new`/`exit_excess` |

```json
{
  "id": "posLimit",
  "type": "ConditionNode",
  "plugin": "MaxPositionLimit",
  "positions": "{{ nodes.account.positions }}",
  "fields": {"max_positions": 5, "max_single_weight_pct": 30, "action": "warn"}
}
```

> **포지션 기반**: `data` 없이 `positions`만 필요.
