# 03. Portfolio Backtest 예제

**PortfolioNode를 활용한 계층적 멀티 전략 백테스트**

## 개요

이 예제는 새로 추가된 `PortfolioNode`와 확장된 `BacktestEngineNode`를 사용하여:
- 여러 전략을 자본 배분하여 통합 관리
- 계층적 포트폴리오 구성 (Portfolio of Portfolios)
- 리밸런싱 시뮬레이션
- 포지션 사이징 및 손절/익절 규칙 적용

## 워크플로우 구조

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Master Portfolio ($100,000)                       │
│                        allocation: risk_parity                           │
│                        rebalance: drift (5%)                            │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
        ┌───────────▼───────────┐       ┌───────────▼───────────┐
        │  Tech Portfolio (60%)  │       │  Value Portfolio (40%) │
        │  allocation: momentum  │       │  allocation: equal     │
        └───────────┬───────────┘       └───────────┬───────────┘
                    │                               │
            ┌───────┴───────┐               ┌───────┴───────┐
            │               │               │               │
    ┌───────▼───────┐ ┌─────▼─────┐ ┌───────▼───────┐ ┌─────▼─────┐
    │ RSI Strategy  │ │MA Strategy│ │ Value Strategy│ │Momentum   │
    │ (NVDA, AAPL)  │ │(MSFT,GOOGL)│ │ (JNJ, PG)    │ │(AMZN)     │
    │ kelly 0.25    │ │ equal     │ │ fixed 10%    │ │ kelly 0.5 │
    │ SL:5% TP:15%  │ │ SL:3%     │ │ SL:5% TP:10% │ │ SL:7%     │
    └───────────────┘ └───────────┘ └───────────────┘ └───────────┘
```

## 실행 방법

```bash
cd src/programgarden/examples/10_ui/03_portfolio_backtest
poetry run python run.py
```

## 주요 기능

### 1. BacktestEngineNode 확장 옵션
- `position_sizing`: kelly, fixed_percent, atr_based 등
- `exit_rules`: stop_loss, take_profit, trailing_stop

### 2. PortfolioNode 옵션
- `allocation_method`: equal, custom, risk_parity, momentum
- `rebalance_rule`: periodic, drift, both
- 계층적 자본 상속

### 3. 시각화
- 전략별 Equity Curve 비교
- 포트폴리오별 배분 비중
- 통합 성과 지표
