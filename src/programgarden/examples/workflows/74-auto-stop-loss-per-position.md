# 74 - 포지션별 자동 손절 + 텔레그램 (선물 모의)

> **시나리오**: "5분마다 내 포지션 체크해서 -5% 이상 손실이면 알아서 손절하고 텔레그램 보내줘."

## 흐름

```
Start → Broker(paper) → Schedule(5분) → Account → StopLoss(plugin) → SymbolFilter(union) → Sell → Telegram
```

## 핵심 패턴: Per-position via StopLoss plugin

`ConditionNode(plugin='StopLoss')` 가 각 포지션의 `pnl_rate` 를 평가해 `passed_symbols` 에 손절 대상만 담습니다.
이어지는 `SymbolFilterNode(operation='union', input_b=[])` 가 그 배열을 `symbols` 포트로 노출시키는 어댑터 역할을 하여, `sell_order` 가 auto-iterate 합니다.

```
positions = [
  {"symbol": "HMHJ26", "pnl_rate": -6.2, ...},
  {"symbol": "HMCEJ26", "pnl_rate": -1.5, ...},
]

stop_loss.passed_symbols    → [{"symbol": "HMHJ26", "exchange": "HKEX"}]  (조건 충족만)
triggered_symbols.symbols   → 동일 배열을 symbols 포트로 노출
sell_order                  → triggered_symbols 의 각 item 마다 1회 (= 손절 대상 수만큼)
telegram_stop_loss          → 매도별 발송
```

## 왜 IfNode 가 아닌가

이 워크플로우는 1.21.10 이전 IfNode 로 per-position 분기를 시도했지만, IfNode 는 **단일값 비교 분기**용이고 auto-iterate 대상이 아닙니다.
`{{ item.pnl_rate }}` 를 IfNode.left 에 두면 item 컨텍스트가 비어 항상 false 로 떨어져 모든 손절이 누락됩니다.

| 패턴 | 용도 |
|------|------|
| IfNode | 단일 스칼라 분기 (예: `{{ nodes.account.balance }} >= 1000000`) |
| ConditionNode + 포지션 플러그인 | per-position 평가 (StopLoss / ProfitTarget / TrailingStop / Drawdown) |
| SymbolFilterNode (union, input_b=[]) | passed_symbols → symbols 포트 어댑터 (auto-iterate 유도) |

## 제약과 트레이드오프

- **quantity 고정 (=1)**: 데모 단순화. 실제 전량 청산이 필요하면 `stop_loss.symbol_results` 에서 quantity 매칭하거나, 별도 룩업 노드를 추가하라.
- **롱 포지션 전제** (`side: "sell"`): 숏 포지션 청산은 별도 분기 또는 두 번째 워크플로우로 분리. StopLoss 플러그인은 close_side 를 출력하지 않는다.
- **stop_percent 음수 권장**: `-5.0` 이 -5% 손실 도달.

## 손절 기준 조정

| `stop_percent` | 성향 |
|----------------|------|
| `-3.0` | 매우 보수적 (작은 손실에도 즉시 컷) |
| `-5.0` | 보수적 (기본) |
| `-8.0` | 균형 |
| `-15.0` | 공격적 (큰 반등 기대) |

## 스케줄 주기 조정

| cron | 의미 | 권장 상황 |
|------|------|-----------|
| `*/5 * * * *` | 5분마다 | 기본 (균형) |
| `*/1 * * * *` | 1분마다 | 단기 변동 큰 시장 |
| `*/15 * * * *` | 15분마다 | 장기 포지션 |
| `0 * * * *` | 매 정시 | 저주파 감시 |

## 확장 아이디어

- **트레일링 스탑**: `ConditionNode(plugin='TrailingStop')` 로 HWM 기반 동적 손절 (risk_features={'hwm'})
- **익절 + 손절 동시**: `ConditionNode(plugin='ProfitTarget')` 분기를 같은 account 에서 병렬로
- **VaR/CVaR 기반**: `ConditionNode(plugin='VaRCVaRMonitor')` 로 포트폴리오 단위 위험 감시

## 주의사항

- `paper_trading=true` 모의투자로 안전. 실거래 시 반드시 `false` + 실 APPKEY
- `resilience.fallback.mode: "skip"` — 일부 종목 주문 실패해도 다른 종목 계속 처리
- `max_duration_hours: 1` — 스케줄 최대 유지 시간 (장기 실행 시 720 등으로 증가)
