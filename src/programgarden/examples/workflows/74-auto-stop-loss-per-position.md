# 74 - 포지션별 자동 손절 + 텔레그램 (선물 모의)

> **시나리오**: "5분마다 내 포지션 체크해서 -5% 이상 손실이면 알아서 손절하고 텔레그램 보내줘."

## 흐름

```
Start → Broker(paper) → Schedule(5분) → Account → IfNode(≤-5%) → Sell → Telegram
```

## 핵심 패턴: Per-position Auto-iterate

AccountNode 의 `positions` 리스트가 다운스트림 체인 전체에 **자동 반복** 됩니다:

```
positions = [
  {"symbol": "HMHJ26", "pnl_rate": -6.2, "quantity": 1, "close_side": "sell"},
  {"symbol": "HMCEJ26", "pnl_rate": -1.5, "quantity": 2, "close_side": "sell"},
]

IfNode     → 2번 실행 (각 포지션마다)
sell_order → 손절 조건 충족한 포지션에만 실행 (조건부 iterate)
telegram   → 매도 체결별 발송
```

## close_side 자동 결정

AccountNode 의 positions 출력에 `close_side` 필드가 자동 계산되어 있습니다:

| 보유 포지션 | close_side |
|-------------|-----------|
| 롱 (long) | `"sell"` |
| 숏 (short) | `"buy"` |

이 덕분에 `sell_order` 노드의 `side` 필드를 `{{ item.close_side }}` 로 바인딩하면 롱/숏 무관하게 청산됩니다.

## 스케줄 주기 조정

| cron | 의미 | 권장 상황 |
|------|------|-----------|
| `*/5 * * * *` | 5분마다 | 기본 (균형) |
| `*/1 * * * *` | 1분마다 | 단기 변동 큰 시장 |
| `*/15 * * * *` | 15분마다 | 장기 포지션 |
| `0 * * * *` | 매 정시 | 저주파 감시 |

## 손절 기준 조정

| right 값 | 성향 |
|----------|------|
| `-3` | 매우 보수적 (작은 손실에도 즉시 컷) |
| `-5` | 보수적 (기본) |
| `-8` | 균형 |
| `-15` | 공격적 (큰 반등 기대) |

## 확장 아이디어

- **트레일링 스탑 추가**: `trailing_stop` 플러그인으로 HWM 기반 동적 손절
- **익절도 함께**: 같은 워크플로우에 `if_big_profit` (pnl_rate >= 10%) 브랜치 추가
- **부분 청산**: `partial_take_profit` 플러그인으로 50% 만 매도
- **loss 크기 단계화**: IfNode 3단 (-3/-5/-10) 각각 다른 수량 매도

## 주의사항

- `paper_trading=true` 모의투자로 안전. 실거래 시 반드시 `false` + 실 APPKEY
- `resilience.fallback.mode: "skip"` — 일부 종목 주문 실패해도 다른 종목 계속 처리
- `max_duration_hours: 1` — 스케줄 최대 유지 시간 (장기 실행 시 720 등으로 증가)
