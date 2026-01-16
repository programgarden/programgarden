# Phase 4: ConditionNode/BacktestEngineNode 구조 리팩토링

## 현황 분석

### 문제점

#### 1. ConditionNode가 두 가지 역할을 함

| 모드 | 역할 | 출력 |
|------|------|------|
| 실시간 | 단일 시점 평가 | `passed_symbols`, `values` |
| 백테스트 | 시계열 순회 + 시그널 생성 | `signals`, `values_timeseries` |

**→ 출력 타입 불일치로 후속 노드 바인딩이 혼란스러움**

#### 2. symbols 형식 불일치

```python
# 입력 시 (WatchlistNode)
[{"exchange": "NASDAQ", "symbol": "AAPL"}]

# 출력 시 (ConditionNode.passed_symbols)
["AAPL"]  # ❌ 거래소 정보 누락!
```

**→ 해외주식/선물에서 거래소 구분이 필수인데 정보 손실**

#### 3. values 출력 사용처

현재 `{{ nodes.xxx.values }}` 바인딩 사용처:
- DisplayNode에서 테이블/차트 표시용

---

## 목표 구조

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ConditionNode: 항상 "단일 시점" 평가만                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  입력:                                                                       │
│   - symbols: [{exchange, symbol}, ...]                                      │
│   - price_data: {symbol: {close, volume, ...}}  (단일 시점)                 │
│                                                                             │
│  출력 (항상 동일한 구조):                                                     │
│   - result: bool                                                            │
│   - passed_symbols: [{exchange, symbol}, ...]  ← 거래소 포함!               │
│   - failed_symbols: [{exchange, symbol}, ...]                               │
│   - values: {symbol: {rsi: 28.5, ...}}                                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  BacktestEngineNode: 시계열 순회 + 조건 평가 + 시뮬레이션                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  입력:                                                                       │
│   - ohlcv_data: {symbol: [{date, open, high, low, close, volume}, ...]}    │
│   - condition_nodes: ["rsi", "macd"]  (조건 노드 ID 목록)                   │
│   - logic: "all" | "any"  (조건 조합 방식)                                   │
│                                                                             │
│  동작:                                                                       │
│   1. 각 날짜별로 해당 시점 데이터 추출                                        │
│   2. 각 ConditionNode의 플러그인을 호출하여 조건 평가                         │
│   3. 조건 충족 시 매수/매도 시뮬레이션                                        │
│                                                                             │
│  출력:                                                                       │
│   - equity_curve: [{date, value}, ...]                                      │
│   - trades: [{date, symbol, action, price, qty}, ...]                       │
│   - signals: [{date, signal, symbols, values}, ...]  ← 기존 ConditionNode것│
│   - metrics: {total_return, sharpe_ratio, max_drawdown, ...}                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Symbol 표준 형식

### SymbolInfo 타입 (core/models)

```python
class SymbolInfo(TypedDict):
    exchange: str   # "NASDAQ", "NYSE", "CME" 등
    symbol: str     # "AAPL", "TSLA", "ESH5" 등
    name: str       # (선택) "Apple Inc."
```

### 변환 규칙

| 입력 형식 | 변환 결과 |
|----------|----------|
| `"AAPL"` | 에러 또는 기본 거래소 추정 |
| `{"symbol": "AAPL"}` | 에러 (exchange 필수) |
| `{"exchange": "NASDAQ", "symbol": "AAPL"}` | ✅ 그대로 사용 |

### 영향받는 노드 출력

| 노드 | 포트 | 기존 | 변경 |
|------|------|------|------|
| WatchlistNode | symbols | `[{exchange, symbol}]` | 유지 ✅ |
| MarketUniverseNode | symbols | `[{exchange, symbol, name}]` | 유지 ✅ |
| ScreenerNode | symbols | `[{exchange, symbol, ...}]` | 유지 ✅ |
| ConditionNode | passed_symbols | `["AAPL"]` ❌ | `[{exchange, symbol}]` |
| ConditionNode | failed_symbols | `["AAPL"]` ❌ | `[{exchange, symbol}]` |
| LogicNode | passed_symbols | `["AAPL"]` ❌ | `[{exchange, symbol}]` |
| SymbolFilterNode | symbols | `["AAPL"]` ❌ | `[{exchange, symbol}]` |

---

## 작업 목록

### Phase 4.1: Core 타입 정의 (core-developer) ✅ 완료

- [x] `SymbolEntry` Pydantic 모델 정의 (`core/models/exchange.py`)
- [x] `normalize_symbol()`, `normalize_symbols()` 유틸리티 함수
- [x] `symbols_to_dict_list()`, `extract_symbol_codes()` 유틸리티 함수

### Phase 4.2: ConditionNode 리팩토링 (programgarden-executor) ✅ 완료

- [x] 백테스트 모드 로직 제거 (단일 시점 평가만)
- [x] 시계열 데이터 입력 시 마지막 시점만 평가
- [x] `_execute_backtest_mode` 메서드 삭제
- [x] passed_symbols, failed_symbols 출력에 거래소 정보 포함 `[{exchange, symbol}]`
- [x] values 출력 유지 (DisplayNode 호환)

### Phase 4.3: BacktestEngineNode 확장 (programgarden-executor) ✅ 완료

- [x] signals 출력 추가 (기존 ConditionNode 백테스트 출력 이동)
- [ ] condition_nodes 입력 추가 (조건 노드 ID 목록) - 추후 확장
- [ ] logic 입력 추가 (all/any 조건 조합) - 추후 확장

### Phase 4.4: DisplayNode signal 차트 타입 (programgarden-executor) ✅ 완료

- [x] chart_type: "signal" 구현
- [x] ConditionNode 출력(passed_symbols, failed_symbols, values, result)을 테이블 형식으로 변환
- [x] 콘솔 출력: 종목별 통과/실패 + 지표값 표시
- [x] 프론트엔드 데이터 구조 정의 (signal_data)

### Phase 4.5: 기타 노드 symbols 형식 통일 (programgarden-executor)

- [ ] SymbolFilterNode 출력 수정
- [ ] LogicNode 출력 수정
- [ ] 기타 symbols 포트 사용 노드 확인

### Phase 4.6: 예제 워크플로우 업데이트 (qa-inspector) ✅ 완료

- [x] 01-condition-rsi-historical-stock.json 수정 (chart_type: signal)
- [x] 테스트 실행 성공 (3/3 종목 통과)

---

## 완료 (2026-01-16)

모든 Phase 완료. Phase 4 리팩토링 작업이 성공적으로 마무리되었습니다.

### 주요 변경 사항

1. **ConditionNode**: 백테스트 모드 제거, 단일 시점 평가만 수행
2. **Symbol 형식 통일**: 모든 노드에서 `[{exchange, symbol}]` 형식 출력
3. **DisplayNode**: `chart_type: "signal"` 추가 - 조건 결과 시각화
4. **LogicNode/SymbolFilterNode**: 거래소 정보 보존

### 테스트 결과

```
📊 RSI 조건 결과 [2026-01-16 19:11:09]
================================================================================
조건 결과: PASSED
통과: 3/3 종목
--------------------------------------------------------------------------------
Exchange   Symbol     Status     result      
--------------------------------------------------------------------------------
NASDAQ     AAPL       ✅ PASS     True        
NASDAQ     NVDA       ✅ PASS     True        
NASDAQ     TSLA       ✅ PASS     True        
================================================================================
```

---

## DisplayNode `signal` 차트 데이터 구조

### 입력 (BacktestEngineNode 출력)

```json
{
  "signals": [
    {"date": "20260116", "signal": "buy", "symbols": [{"exchange": "NASDAQ", "symbol": "AAPL"}], "values": {"AAPL": {"rsi": 28.5}}}
  ],
  "values_timeseries": {
    "AAPL": [{"date": "20260102", "rsi": 31.11}, ...]
  }
}
```

### 프론트엔드 전달 형식

```json
{
  "chart_type": "signal",
  "data": {
    "series": [
      {"name": "AAPL", "data": [{"date": "2026-01-02", "value": 31.11}, ...]},
      {"name": "TSLA", "data": [...]},
    ],
    "markers": [
      {"date": "2026-01-16", "symbol": "AAPL", "type": "buy"},
      {"date": "2026-01-14", "symbol": "TSLA", "type": "buy"},
    ],
    "threshold": {"value": 30, "label": "Oversold"}
  }
}
```

---

## 마이그레이션 전략

### 하위 호환성

1. **symbols 문자열 배열 처리**
   - 기존 `["AAPL"]` 형식도 임시로 허용
   - 경고 로그 출력 + 기본 거래소 추정 시도
   - 1.0 릴리즈 전까지 완전 마이그레이션

2. **ConditionNode 백테스트 모드**
   - 기존 동작 유지하되 deprecated 경고
   - BacktestEngineNode 사용 권장 메시지 출력

---

## 우선순위

1. **즉시 필요**: Phase 4.2 (ConditionNode symbols 형식)
2. **중요**: Phase 4.3 (BacktestEngineNode 확장)
3. **사용성**: Phase 4.4 (signal 차트)
4. **완성도**: Phase 4.1, 4.5, 4.6

---

## 예상 영향

| 패키지 | 변경 파일 | 작업량 |
|--------|----------|--------|
| core | models/symbol.py (신규) | 작음 |
| programgarden | executor.py | 중간 |
| community | 플러그인 수정 없음 | 없음 |
| examples | condition/*.json | 작음 |
