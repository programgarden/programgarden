# ProgramGarden Examples

노드 기반 DSL 워크플로우 예제 모음 (30개)

## 카테고리

### 🟢 Basic Examples (01-05)
| # | 파일 | 설명 |
|---|------|------|
| 01 | [01_start_only.py](01_start_only.py) | StartNode만 있는 최소 워크플로우 |
| 02 | [02_start_schedule.py](02_start_schedule.py) | Start → Schedule 연결 |
| 03 | [03_start_schedule_trading_hours.py](03_start_schedule_trading_hours.py) | 거래시간 필터 추가 |
| 04 | [04_broker_connection.py](04_broker_connection.py) | 증권사 연결 (LS) |
| 05 | [05_watchlist_realmarket.py](05_watchlist_realmarket.py) | 관심종목 + 실시간 시세 |

### 🔵 Condition Examples (06-10)
| # | 파일 | 설명 |
|---|------|------|
| 06 | [06_single_condition.py](06_single_condition.py) | RSI < 30 단일 조건 |
| 07 | [07_multi_condition.py](07_multi_condition.py) | RSI AND MACD 복합 조건 |
| 08 | [08_weighted_condition.py](08_weighted_condition.py) | 가중치 조합 (40%+30%+30%) |
| 09 | [09_at_least_condition.py](09_at_least_condition.py) | 3개 중 2개 이상 만족 |
| 10 | [10_nested_logic.py](10_nested_logic.py) | (A AND B) OR (C AND D) 중첩 |

### 🟠 Order Examples (11-15)
| # | 파일 | 설명 |
|---|------|------|
| 11 | [11_market_order.py](11_market_order.py) | 시장가 매수 |
| 12 | [12_limit_order.py](12_limit_order.py) | 지정가 매수 (현재가 -1%) |
| 13 | [13_position_sizing.py](13_position_sizing.py) | 1% 리스크 기반 수량 계산 |
| 14 | [14_modify_order.py](14_modify_order.py) | 가격 추적 정정 |
| 15 | [15_cancel_order.py](15_cancel_order.py) | 30분 초과 주문 취소 |

### 🟣 Integration Examples (16-22)
| # | 파일 | 설명 |
|---|------|------|
| 16 | [16_buy_sell_basic.py](16_buy_sell_basic.py) | 기본 매수/매도 흐름 |
| 17 | [17_screener_to_order.py](17_screener_to_order.py) | 스크리너 → 주문 |
| 18 | [18_event_handler.py](18_event_handler.py) | 체결 이벤트 알림 |
| 19 | [19_error_handler.py](19_error_handler.py) | 에러 재시도 및 알림 |
| 20 | [20_risk_guard.py](20_risk_guard.py) | 일일 손실 제한 |
| 21 | [21_group_node.py](21_group_node.py) | 전략 그룹화 |
| 22 | [22_trading_hours.py](22_trading_hours.py) | 정규장 시간 필터 |

### 🔴 24H Automation Examples (23-27)
| # | 파일 | 설명 |
|---|------|------|
| 23 | [23_pause_resume.py](23_pause_resume.py) | 일시정지/재개 지원 |
| 24 | [24_state_snapshot.py](24_state_snapshot.py) | 상태 스냅샷 및 복구 |
| 25 | [25_multi_market.py](25_multi_market.py) | 주식 + 선물 동시 운영 |
| 26 | [26_long_running.py](26_long_running.py) | 24시간 연속 + 일별 리포트 |
| 27 | [27_24h_full_autonomous.py](27_24h_full_autonomous.py) | 완전 자율 트레이딩 (22개 노드) |

### 🟡 Backtest Examples (28-30)
| # | 파일 | 설명 |
|---|------|------|
| 28 | [28_backtest_simple.py](28_backtest_simple.py) | 단순 RSI 백테스트 |
| 29 | [29_backtest_with_deploy.py](29_backtest_with_deploy.py) | 백테스트 → 성과 조건 → 자동 배포 |
| 30 | [30_scheduled_backtest_job_control.py](30_scheduled_backtest_job_control.py) | 주간 백테스트 → Job 자동 제어 |

## 사용법

```python
from programgarden import ProgramGarden

# 클라이언트 생성
pg = ProgramGarden()

# 예제 워크플로우 로드
from programgarden.examples import get_example
workflow = get_example("16_buy_sell_basic")

# 검증
result = pg.validate(workflow)
print(f"Valid: {result.is_valid}")

# 실행
job = await pg.start(workflow)
print(f"Job ID: {job.id}")
```

## 노드 타입 분포

| 카테고리 | 노드 타입 | 예제 |
|----------|-----------|------|
| Infra | StartNode, BrokerNode | 01-04 |
| Trigger | ScheduleNode, TradingHoursFilterNode, ExchangeStatusNode | 02-03, 22 |
| Symbol | WatchlistNode, MarketUniverseNode, ScreenerNode, SymbolFilterNode | 05, 17 |
| Realtime | RealMarketDataNode, RealAccountNode, RealOrderEventNode | 05, 14-15 |
| Condition | ConditionNode, LogicNode | 06-10 |
| Risk | PositionSizingNode, RiskGuardNode | 13, 20 |
| Order | NewOrderNode, ModifyOrderNode, CancelOrderNode | 11-15 |
| Event | EventHandlerNode, ErrorHandlerNode, AlertNode | 18-19 |
| Display | DisplayNode | 전체 |
| Group | GroupNode | 21 |
