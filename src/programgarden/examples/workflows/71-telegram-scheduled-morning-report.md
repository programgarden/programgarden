# 71 - 매일 아침 정기 텔레그램 리포트

> **왕초보 질문**: "매일 아침에 내 계좌 상태 텔레그램으로 보내줘"

매일 평일 오전 9시 (KST) 에 자동으로 계좌 요약을 텔레그램으로 보냅니다.

## 흐름

```
ScheduleNode (매일 09:00) → Broker → Account → IfNode → Telegram
  매일 자동 트리거            로그인    조회    게이트     리포트
```

## cron 표현식 가이드

| 표현식 | 의미 |
|--------|------|
| `0 9 * * 1-5` | 평일(월~금) 오전 9시 |
| `0 9,18 * * *` | 매일 오전 9시 + 오후 6시 |
| `*/30 9-16 * * 1-5` | 평일 09-16시 사이 30분마다 |
| `0 22 * * *` | 매일 오후 10시 (장 마감 리포트) |
| `0 9 * * 1` | 매주 월요일 오전 9시 (주간 리포트) |

## 실행 방법

```bash
cd src/programgarden
poetry run python examples/programmer_example/test_beginner_telegram.py
```

⚠️ ScheduleNode 가 포함된 워크플로우는 **장시간 실행됩니다** (`max_duration_hours=720` → 30일). 테스트 러너에서는 짧은 타임아웃으로 강제 종료 후 terminal state 도달만 검증합니다.

## 날짜 헬퍼

`{{ date.today(format='yyyy-mm-dd') }}` → `2026-04-19`

더 많은 날짜 함수:
- `{{ date.today(format='yyyymmdd') }}` → `20260419`
- `{{ date.ago(7, format='yyyy-mm-dd') }}` → 7일 전
- `{{ date.later(30, format='yyyy-mm-dd') }}` → 30일 후

## 확장 아이디어

- **장 마감 리포트**: cron 을 `0 22 * * 1-5` 로 변경 → 미국장 마감 후 요약
- **주간 리포트**: cron `0 9 * * 1` + 보유 종목 테이블 포함
- **위험 알림**: IfNode 조건을 `total_pnl_rate <= -5` 로 → 손실 5% 이상 일 때만 발송
- **시작 알림 + 본 리포트 분기**: ScheduleNode 뒤에 또 다른 Telegram "리포트 시작" 메시지 추가

## 주의사항

- 타임존은 `timezone: "Asia/Seoul"` 명시 필수 (서버 타임존에 의존하지 않음)
- `enabled: false` 로 설정하면 스케줄 비활성화 (디버깅 시 유용)
- 국내 공휴일은 자동 제외되지 않음 → 필요 시 `TradingHoursFilterNode` 추가
