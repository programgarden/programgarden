# 백테스트 → 성과 검증 → 실전 배포 전략

## 전략 ID
`backtest_to_live`

## 버전
1.0.0

## 기여자
ProgramGarden Team

## 간단한 설명
6개월 백테스트를 실행하고, 성과가 기준을 충족하면 자동으로 실계좌에 배포하는 전략입니다.

## 이 전략이 필요한 이유

### 문제점
- 백테스트 결과를 수동으로 검토하고 배포하는 것이 번거로움
- 감정적으로 백테스트 결과를 해석하여 잘못된 배포 결정
- 객관적인 기준 없이 전략을 실계좌에 적용

### 해결책
- 백테스트 실행 → 성과 검증 → 배포를 자동화
- 수치 기반 객관적 판단 (수익률, MDD, 승률, 샤프비율)
- 기준 미달 시 Paper Trading으로 안전하게 유지

## 워크플로우 단계

```
┌─────────────────────────────────────────────────────────────┐
│  Phase A: 백테스트 실행                                      │
│  HistoricalData → ConditionNodes → BacktestExecutor         │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  Phase B: 성과 검증                                          │
│  BacktestResult → PerformanceConditionNode                  │
│  • 수익률 > 0%                                              │
│  • MDD < 10%                                                │
│  • 승률 > 40%                                               │
│  • 샤프비율 > 0.3                                           │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  Phase C: 배포 결정                                          │
│  ├── 통과 → DeployNode (실계좌)                             │
│  └── 실패 → DeployNode (Paper Trading)                      │
└─────────────────────────────────────────────────────────────┘
```

## 성과 기준

| 지표 | 기준 | 설명 |
|------|------|------|
| 총 수익률 | > 0% | 최소 손실 없이 종료 |
| 최대 낙폭 (MDD) | < 10% | 감당 가능한 리스크 |
| 승률 | > 40% | 최소한의 일관성 |
| 샤프비율 | > 0.3 | 리스크 대비 수익 |

## 파라미터

| 이름 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `symbols` | list | ["SOXS","SQQQ","FAZ"] | 대상 종목 |
| `backtest_months` | int | 6 | 백테스트 기간 (개월) |
| `min_return` | float | 0 | 최소 수익률 (%) |
| `max_mdd` | float | 10 | 최대 MDD (%) |
| `min_win_rate` | float | 40 | 최소 승률 (%) |
| `min_sharpe` | float | 0.3 | 최소 샤프비율 |

## 사용법

```python
from programgarden_community.strategies import get_strategy
from programgarden import ProgramGarden

strategy = get_strategy("overseas_stock", "backtest_to_live")

pg = ProgramGarden()
result = pg.validate(strategy)

if result.is_valid:
    job = pg.run(strategy)
```

## 알림 설정

Slack 웹훅 URL을 환경 변수로 설정하면 배포 결과를 알림 받을 수 있습니다:

```
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

## 배포 결과 예시

### 성공 시
```
✅ 백테스트 통과! 실계좌 배포 완료
수익률: 8.5%
MDD: 6.2%
승률: 52%
샤프비율: 0.85
```

### 실패 시
```
⚠️ 백테스트 기준 미달
수익률: -2.3%
MDD: 15.4%
→ Paper Trading 유지
```

## 주의사항

- 백테스트 결과는 과거 데이터 기반이며, 미래 수익을 보장하지 않습니다
- 실계좌 배포 전 Paper Trading으로 충분히 검증하세요
- 시장 상황에 따라 성과 기준을 조정할 수 있습니다
