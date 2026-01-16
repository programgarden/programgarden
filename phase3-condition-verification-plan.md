# Phase 3: Condition Category 노드 검증 계획서

## 상태: ✅ 완료 (2025-01-xx)

---

## 1. 개요

| 항목 | 내용 |
|------|------|
| 대상 노드 | ConditionNode, LogicNode, PerformanceConditionNode |
| 테스트 범위 | 모든 플러그인, 모든 연산자, 모든 지표 |
| 상품 유형 | overseas_stock, overseas_futures |
| 모드 | realtime, backtest |

---

## 2. 구현 완료 항목

### 2.1 ConditionNode (기존 구현 검증)
- ✅ Executor: `ConditionNodeExecutor` (executor.py lines 3757-4188)
- ✅ Schema: `ConditionNode` (condition.py)
- ✅ 6개 플러그인 테스트 완료

### 2.2 LogicNode (신규 구현)
- ✅ Executor: `LogicNodeExecutor` (executor.py lines 4190-4396, ~206줄)
- ✅ 8개 연산자 모두 구현:
  - `all` (AND): 모든 조건 만족
  - `any` (OR): 하나 이상 만족
  - `not`: 모든 조건 불만족
  - `xor`: 정확히 하나만 만족
  - `at_least`: N개 이상 만족
  - `at_most`: N개 이하 만족
  - `exactly`: 정확히 N개 만족
  - `weighted`: 가중치 합산 >= threshold

### 2.3 PerformanceConditionNode (신규 구현)
- ✅ Schema: `PerformanceConditionNode` (condition.py, ~240줄)
  - backtest.py에서 condition.py로 이전 (더 풍부한 필드 지원)
- ✅ Executor: `PerformanceConditionNodeExecutor` (executor.py, ~280줄)
- ✅ 12개 지표 구현:
  - `pnl_rate`: 수익률 (%)
  - `pnl_amount`: 손익 금액
  - `mdd`: 최대 낙폭 (%)
  - `win_rate`: 승률 (%)
  - `sharpe_ratio`: 샤프 비율
  - `profit_factor`: 수익 팩터
  - `avg_win`: 평균 수익
  - `avg_loss`: 평균 손실
  - `consecutive_wins`: 연속 수익 횟수
  - `consecutive_losses`: 연속 손실 횟수
  - `total_trades`: 총 거래 횟수
  - `daily_pnl`: 일일 손익
- ✅ 6개 연산자: gt, lt, gte, lte, eq, ne

---

## 3. 워크플로우 파일 (42개)

### 3.1 ConditionNode 워크플로우 (#01-#18)

| # | 파일명 | 플러그인 | 모드 | 상품 |
|---|--------|----------|------|------|
| 01 | `01-rsi-realtime-stock.json` | RSI | realtime | overseas_stock |
| 02 | `02-rsi-backtest-stock.json` | RSI | backtest | overseas_stock |
| 03 | `03-macd-realtime-stock.json` | MACD | realtime | overseas_stock |
| 04 | `04-macd-backtest-stock.json` | MACD | backtest | overseas_stock |
| 05 | `05-bollinger-realtime-stock.json` | BollingerBands | realtime | overseas_stock |
| 06 | `06-bollinger-backtest-stock.json` | BollingerBands | backtest | overseas_stock |
| 07 | `07-volumespike-realtime-stock.json` | VolumeSpike | realtime | overseas_stock |
| 08 | `08-volumespike-backtest-stock.json` | VolumeSpike | backtest | overseas_stock |
| 09 | `09-profittarget-realtime-stock.json` | ProfitTarget | realtime | overseas_stock |
| 10 | `10-profittarget-backtest-stock.json` | ProfitTarget | backtest | overseas_stock |
| 11 | `11-stoploss-realtime-stock.json` | StopLoss | realtime | overseas_stock |
| 12 | `12-stoploss-backtest-stock.json` | StopLoss | backtest | overseas_stock |
| 13 | `13-rsi-realtime-futures.json` | RSI | realtime | overseas_futures |
| 14 | `14-macd-realtime-futures.json` | MACD | realtime | overseas_futures |
| 15 | `15-bollinger-realtime-futures.json` | BollingerBands | realtime | overseas_futures |
| 16 | `16-volumespike-realtime-futures.json` | VolumeSpike | realtime | overseas_futures |
| 17 | `17-profittarget-realtime-futures.json` | ProfitTarget | realtime | overseas_futures |
| 18 | `18-stoploss-realtime-futures.json` | StopLoss | realtime | overseas_futures |

### 3.2 LogicNode 워크플로우 (#19-#34)

| # | 파일명 | 연산자 | 상품 |
|---|--------|--------|------|
| 19 | `19-logic-all-stock.json` | all (AND) | overseas_stock |
| 20 | `20-logic-any-stock.json` | any (OR) | overseas_stock |
| 21 | `21-logic-not-stock.json` | not | overseas_stock |
| 22 | `22-logic-xor-stock.json` | xor | overseas_stock |
| 23 | `23-logic-atleast-stock.json` | at_least | overseas_stock |
| 24 | `24-logic-atmost-stock.json` | at_most | overseas_stock |
| 25 | `25-logic-exactly-stock.json` | exactly | overseas_stock |
| 26 | `26-logic-weighted-stock.json` | weighted | overseas_stock |
| 27 | `27-logic-all-futures.json` | all (AND) | overseas_futures |
| 28 | `28-logic-any-futures.json` | any (OR) | overseas_futures |
| 29 | `29-logic-not-futures.json` | not | overseas_futures |
| 30 | `30-logic-xor-futures.json` | xor | overseas_futures |
| 31 | `31-logic-atleast-futures.json` | at_least | overseas_futures |
| 32 | `32-logic-atmost-futures.json` | at_most | overseas_futures |
| 33 | `33-logic-exactly-futures.json` | exactly | overseas_futures |
| 34 | `34-logic-weighted-futures.json` | weighted | overseas_futures |

### 3.3 PerformanceConditionNode 워크플로우 (#35-#42)

| # | 파일명 | 지표 | 상품 |
|---|--------|------|------|
| 35 | `35-perf-pnlrate-stock.json` | pnl_rate | overseas_stock |
| 36 | `36-perf-mdd-stock.json` | mdd | overseas_stock |
| 37 | `37-perf-winrate-stock.json` | win_rate | overseas_stock |
| 38 | `38-perf-sharpe-stock.json` | sharpe_ratio | overseas_stock |
| 39 | `39-perf-pnlrate-futures.json` | pnl_rate | overseas_futures |
| 40 | `40-perf-consecutive-futures.json` | consecutive_losses | overseas_futures |
| 41 | `41-perf-profitfactor-futures.json` | profit_factor | overseas_futures |
| 42 | `42-perf-totaltrades-futures.json` | total_trades | overseas_futures |

---

## 4. 파일 위치

```
src/
├── core/programgarden_core/nodes/
│   └── condition.py         # ConditionNode, LogicNode, PerformanceConditionNode 스키마
├── programgarden/programgarden/
│   └── executor.py          # ConditionNodeExecutor, LogicNodeExecutor, PerformanceConditionNodeExecutor
└── programgarden/examples/workflows/condition/
    ├── 01-rsi-realtime-stock.json ~ 18-stoploss-realtime-futures.json
    ├── 19-logic-all-stock.json ~ 34-logic-weighted-futures.json
    └── 35-perf-pnlrate-stock.json ~ 42-perf-totaltrades-futures.json
```

---

## 5. 다음 단계

- [ ] 실제 API 연동 테스트 실행
- [ ] i18n 번역 추가 (ko.json, en.json)
- [ ] 문서 업데이트 (node_reference.md)
