# 68 - 내 계좌 포트폴리오 텔레그램 요약

> **왕초보 질문**: "내 계좌 상태를 텔레그램으로 보내줘"

가장 기본적인 텔레그램 알림 워크플로우입니다. 해외주식 계좌를 조회하고 잔고/수익률을 텔레그램 봇으로 전송합니다.

## 흐름

```
StartNode → BrokerNode → AccountNode → IfNode → TelegramNode
   시작       LS 로그인     계좌조회    잔고게이트   메시지전송
```

## 핵심 노드

| 노드 | 역할 |
|------|------|
| `StartNode` | 워크플로우 시작점 |
| `OverseasStockBrokerNode` | LS증권 실전 계좌 로그인 (paper_trading=false) |
| `OverseasStockAccountNode` | 잔고/보유종목/포지션 조회 |
| `IfNode` | `balance.total_eval_krw > 0` 체크 — auto-iterate 방지 겸 빈 계좌 필터 |
| `TelegramNode` | 텔레그램 Bot API로 메시지 전송 |

## 템플릿 변수

```
💰 해외주식 계좌 현황
📊 평가 총액: ₩{{ nodes.account.balance.total_eval_krw }}
💵 주문가능금액: ${{ nodes.account.balance.orderable_amount }}
💴 외화현금: ${{ nodes.account.balance.foreign_cash }}
📈 수익률: {{ nodes.account.balance.total_pnl_rate }}%
💹 평가손익: ₩{{ nodes.account.balance.total_pnl_krw }}
```

모든 `{{ nodes.X.Y }}` 표현식은 **노드 실행 직전** 자동 바인딩됩니다.

## 사전 준비

1. **LS증권 OpenAPI 키** (`.env` → `APPKEY`, `APPSECRET`)
2. **텔레그램 봇 토큰**:
   - [@BotFather](https://t.me/BotFather) 에서 봇 생성 → 토큰 발급
   - 내 봇에게 `/start` 후 `https://api.telegram.org/bot<TOKEN>/getUpdates` 로 chat_id 확인

## 실행

```bash
cd src/programgarden
poetry run python examples/programmer_example/test_beginner_telegram.py
```

## 왜 IfNode 가 필요한가?

`OverseasStockAccountNode` 의 첫 번째 출력 포트는 `held_symbols` (리스트) 입니다. 엣지로 직접 `TelegramNode` 에 연결하면 보유 종목 수만큼 텔레그램이 발송되는 auto-iterate 가 발동합니다.

**IfNode** 는 `NO_AUTO_ITERATE` 목록에 포함된 인프라 노드라, 리스트 입력을 **단일 트리거**로 변환하는 브레이커 역할을 합니다. 동시에 "잔고가 0 이상인지" 라는 의미 있는 게이트도 겸합니다.

## 확장 아이디어

- **정기 리포트**: 앞에 `ScheduleNode` 추가 → 매일 자동 실행 (#71 참고)
- **보유 종목 테이블**: `TableDisplayNode` 로 포지션 표 표시 후 텔레그램
- **손실 알림**: IfNode 조건을 `total_pnl_rate <= -3` 으로 바꾸면 손실 경고 봇 (#72 참고)
