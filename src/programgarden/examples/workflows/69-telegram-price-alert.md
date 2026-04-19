# 69 - 목표가 도달 텔레그램 알림

> **왕초보 질문**: "엔비디아가 100불 넘으면 알려줘"

특정 종목이 목표가에 도달하면 텔레그램으로 알림을 보냅니다.

## 흐름

```
Start → Broker → Split(NVDA) → MarketData → IfNode(≥100) → Telegram
 시작    로그인    종목1개정의     현재가 조회   목표가체크    알림
```

## 핵심 표현식

- `{{ nodes.market.values.first().price }}` — `values` 리스트 첫 번째 요소의 `price` 필드
- `first()` 메서드 체인은 표현식 엔진의 `lst.first()` 와 동일하게 동작

## 커스터마이징

| 원하는 것 | 변경할 곳 |
|-----------|-----------|
| 다른 종목 | `split_symbol.items` 의 `symbol`/`exchange` |
| 다른 목표가 | `if_price_above.right` 숫자 |
| 하락 알림 | `operator` 를 `<=`, `right` 를 하한가로 |
| 여러 종목 감시 | `items` 배열 확장 + 다운스트림이 auto-iterate |

## 사전 준비

1. LS증권 OpenAPI 키 (`.env` → `APPKEY`, `APPSECRET`)
2. 텔레그램 봇 토큰/Chat ID (#68 참고)

## 왜 SplitNode 를 쓰는가?

`OverseasStockMarketDataNode` 의 `symbols` 필드는 리스트 입력입니다. 바로 `symbols: [...]` 로 쓸 수도 있지만, **확장성**을 위해 SplitNode 로 분리하면 나중에 WatchlistNode 로 대체하기 쉽습니다.

## 주의사항

- `NVDA` 가 현재 $100 미만이면 IfNode 는 `false` 분기 → 텔레그램 미발송 (정상 동작)
- 장 마감 시간대에는 `price` 가 직전 종가로 고정됩니다 (실시간 시세는 `OverseasStockRealMarketDataNode` 사용)

## 확장 아이디어

- **양방향 알림**: `true`/`false` 분기 둘 다 Telegram 연결하여 "도달/미도달" 둘 다 통지
- **여러 종목**: `items` 에 종목 N개 → auto-iterate 로 개별 체크 + 개별 알림
- **스케줄 실행**: 앞에 `ScheduleNode` 추가 → 5분마다 자동 체크
