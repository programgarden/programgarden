# 72 - 손실/수익 양방향 텔레그램 경고

> **왕초보 질문**: "내 계좌 손실 나면 알려주고, 수익 5% 넘으면도 알려줘"

수익률이 특정 임계값을 벗어나면 **손실 경고** 또는 **수익 알림**을 텔레그램으로 보냅니다.

## 흐름

```
                        ┌─(if_loss ≤-3%)──► telegram_loss
Start → Broker → Account┤
                        └─(if_profit ≥+5%)─► telegram_profit
```

## 핵심 패턴: **병렬 분기**

하나의 AccountNode 에서 두 개의 IfNode 로 엣지를 내보내면 **병렬 실행**됩니다.
- `if_loss`: 수익률 ≤ -3%
- `if_profit`: 수익률 ≥ +5%

두 IfNode 가 동시에 `true` 가 되는 경우는 논리적으로 불가능하므로 중복 발송 걱정이 없습니다.

## 임계값 조정 가이드

| 성향 | 손실 임계값 | 수익 임계값 |
|------|------------|------------|
| 매우 보수적 | -1% | +2% |
| 보수적 (기본) | -3% | +5% |
| 공격적 | -5% | +10% |
| 장기 투자 | -10% | +20% |

## 스케줄화

단독 실행이 아닌 **주기적 감시**로 만들려면 `StartNode` 를 `ScheduleNode` 로 교체:

```json
{
  "id": "schedule",
  "type": "ScheduleNode",
  "cron": "*/30 9-16 * * 1-5",
  "timezone": "America/New_York"
}
```

→ 미국장 시간대 평일 30분마다 체크

## 확장 아이디어

- **손절 자동화**: `if_loss` → `telegram_loss` + `OverseasStockNewOrderNode` (sell)
- **분할매도**: `if_profit` → 보유 수량의 50%만 매도하는 주문 추가
- **여러 단계 경고**: IfNode 3단 (-3%, -5%, -10%) 각각 다른 메시지
- **실시간 연동**: `OverseasStockRealAccountNode` + `ThrottleNode` 로 실시간 감시

## 주의사항

- `total_pnl_rate` 는 **전일 대비 수익률** 이 아니라 **누적 평가 수익률** 입니다
- 장 마감 후 호출 시 직전 종가 기준 수익률로 고정됩니다
- 보유 종목이 없으면 수익률이 0 이 되어 두 IfNode 모두 `false` 분기 → 메시지 미발송 (정상)
