# 73 - 볼린저 하단 자동 매수 + 텔레그램 (선물 모의)

> **시나리오**: "볼린저밴드 하단에 닿은 선물 종목 있으면 알아서 매수하고, 체결되면 텔레그램으로 알려줘."

## 흐름

```
Start → Broker(paper) ─┬─► Watchlist → Historical → BollingerBands(below_lower) ─┐
                       │                                                          ▼
                       └─► Account ─────────────────────────────► SymbolFilter (차집합)
                                                                        │
                                                              buy_order → Telegram
```

## 핵심 자동화 패턴

| 단계 | 목적 |
|------|------|
| **WatchlistNode → HistoricalData** | 종목별 auto-iterate (2종목 → 2번 실행) |
| **ConditionNode(BollingerBands)** | `below_lower` 포지션의 종목만 `passed_symbols` 으로 통과 |
| **SymbolFilterNode(difference)** | `passed_symbols - held_symbols` 로 미보유 신규 종목만 |
| **NewOrderNode(auto-iterate)** | 필터링된 각 종목마다 시장가 1계약 매수 |
| **TelegramNode** | 체결별 알림 (auto-iterate 전파) |

## 안전 장치

- `paper_trading: true` — 모의투자 (APPKEY_FUTURE_FAKE 사용)
- `resilience.fallback.mode: "skip"` — 한 종목 주문 실패 시 다음 종목 진행
- **SymbolFilter 차집합** — 이미 보유 중인 종목은 재매수 안함 (중복 방지)

## BollingerBands 플러그인 파라미터

| 필드 | 값 | 의미 |
|------|-----|------|
| `period` | 20 | 이동평균 기간 |
| `std_dev` | 2.0 | 표준편차 밴드 |
| `position` | `"below_lower"` | 현재가가 하단 밴드 아래인 종목만 통과 |

다른 모드: `above_upper`, `within_bands`, `at_lower`, `at_upper`

## 확장 아이디어

- **매도 청산 추가**: 같은 워크플로우에 `position: "above_upper"` 브랜치 추가 → BB 상단 터치 시 청산
- **주기적 자동화**: StartNode를 ScheduleNode(30분)로 교체 → 지속적 감시+매수
- **ATR 기반 사이징**: `PositionSizingNode` 추가하여 변동성 기반 수량 계산
- **실전 전환**: `paper_trading: false` + 실계좌 credential — 실돈 거래 (주의!)

## 주의사항

- HKEX 미니선물 심볼 `HMHJ26` 은 **2026년 4월 만기** → 다음 달 계약(`HMHK26` 5월)으로 업데이트 필요
- 주말/휴장일에는 체결 0건 (정상 동작)
- 첫 실행 시 텔레그램 0 건일 수 있음 (BB 하단 터치 종목이 없는 경우)
