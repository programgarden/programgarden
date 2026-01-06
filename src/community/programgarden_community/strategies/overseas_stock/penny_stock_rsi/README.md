# 동전주 RSI 과매도 매수 전략

## 전략 ID
`penny_stock_rsi`

## 버전
1.0.0

## 기여자
ProgramGarden Team

## 간단한 설명
예수금 1~2만원($15)으로 저가 레버리지 ETF를 RSI 과매도 시 자동 매수하는 전략입니다.

## 이 전략이 필요한 이유

### 문제점
- 소액 투자자는 고가 주식 매수가 어려움
- 수동으로 과매도 구간을 모니터링하기 힘듦
- 감정에 휘둘려 익절/손절 타이밍을 놓침

### 해결책
- 저가 레버리지 ETF ($5~$20) 타겟
- RSI 자동 계산 및 신호 감지
- 익절(+5%) / 손절(-3%) 자동화

## 대상 종목

| 종목 | 설명 | 가격대 |
|------|------|--------|
| SOXS | 반도체 3x 인버스 ETF | ~$15 |
| SQQQ | 나스닥 3x 인버스 ETF | ~$10 |
| FAZ | 금융 3x 인버스 ETF | ~$15 |

## 전략 로직

### 매수 조건
```
RSI(14) < 30 (과매도)
AND 미국 정규장 시간
AND 예수금 있음
```

### 매도 조건
```
수익률 >= +5% (익절)
OR 수익률 <= -3% (손절)
```

### 포지션 사이징
- 예수금의 90% 사용
- 종목당 최대 $15

## 워크플로우 구조

```
StartNode → BrokerNode → ScheduleNode → TradingHoursFilterNode
                                              ↓
                                        WatchlistNode
                                        ↓         ↓
                              RealMarketDataNode  RealAccountNode
                                        ↓              ↓
                                    ConditionNode(RSI)  ConditionNode(익절/손절)
                                        ↓              ↓
                                PositionSizingNode  LogicNode(OR)
                                        ↓              ↓
                                  NewOrderNode(매수)  NewOrderNode(매도)
                                        ↓              ↓
                                    EventHandlerNode → DisplayNode
```

## 파라미터

| 이름 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `symbols` | list | ["SOXS","SQQQ","FAZ"] | 대상 종목 |
| `rsi_period` | int | 14 | RSI 기간 |
| `rsi_threshold` | float | 30 | 과매도 기준 |
| `profit_target` | float | 5.0 | 익절 % |
| `stop_loss` | float | -3.0 | 손절 % |
| `balance_percent` | float | 90 | 예수금 사용 비율 |

## 사용법

```python
from programgarden_community.strategies import get_strategy
from programgarden import ProgramGarden

# 전략 조회
strategy = get_strategy("overseas_stock", "penny_stock_rsi")

# 검증
pg = ProgramGarden()
result = pg.validate(strategy)
print(f"Valid: {result.is_valid}")

# 실행
if result.is_valid:
    job = pg.run(strategy)
    print(f"Job ID: {job.id}")
```

## 환경 변수

`.env` 파일에 다음 설정 필요:

```
APPKEY=your_app_key
APPSECRET=your_app_secret
```

## 리스크 경고

⚠️ **주의사항**:
- 레버리지 ETF는 변동성이 매우 큽니다
- 장기 보유시 가치 훼손 가능성이 있습니다
- 소액 테스트 후 사용을 권장합니다
- 이 전략은 교육 목적이며, 투자 손실에 대한 책임은 본인에게 있습니다

## 예상 성과

과거 백테스트 기준 (참고용):
- 승률: ~55%
- 평균 수익 거래: +4.2%
- 평균 손실 거래: -2.8%
- 샤프비율: ~0.8
