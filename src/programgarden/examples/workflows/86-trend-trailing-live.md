# 추세 상위 매수 + 고정 5% 트레일링스탑 (NASDAQ, 주간거래)

NASDAQ 대형주 유니버스에서 TSMOM 60일 상승추세 종목을 선별해 예수금 한도 내
최대 2종목 매수, 보유 포지션은 고점(HWM) 대비 -5% 고정 트레일링스탑으로
시장가 청산. 매수/매도 시 텔레그램 알림.

> ⚠️ 해외주식은 LS 모의투자 미지원 — 이 워크플로우의 주문은 **실계좌 주문**이다.
> 라이브 실행은 `examples/programmer_example/test_86_trend_trailing_live.py` 의
> `--live --confirm` 게이트로만 수행한다.

## 전략 구조

**매수 레그 (5분 주기, 09:30-16:30 KST 주간거래 게이트)**

1. `universe` — NASDAQ g3190 마스터 500종목 (`stock_exchange: "82"`)
2. `screener1` — 시총 $10B+ / 주가 $20+ 대형주 10종목 (LS data_source)
3. `historical` → `tsmom` — 120일 일봉 → TimeSeriesMomentum 60일 binary 필터
   (auto-iterate 종목별 실행, `passed_symbols` 누적)
4. `trend_pick` — screener1 결과(시총 enrich 보존) ∩ 추세통과 종목
5. `dedup_held` / `dedup_open` — 보유종목·미체결 주문 종목 제외
6. `top2` — ScreenerNode `max_results: 2` 로 시총순 상위 최대 2종목 컷
7. 슬롯 가드 — `if_slot1`(보유 ≤1 → 1번째 매수), `if_slot2`(보유 0 → 2번째 매수)
   ⇒ 보유 종목 수가 2를 넘지 않도록 차등 게이트
8. `sizing_a/b` — 종목당 `orderable_amount`(USD 외화주문가능금액)의 45% 지정가
   (복수 `symbols` + `{{ nodes.sizing["orders"][0] }}` bracket 바인딩 — 런타임 검증된 패턴)
9. `order_a/b` — 지정가 매수 (US 주식 매수는 시장가 불가 → 지정가 정책)

**매도 레그 (5분 주기 폴링)**

1. `account_sell` → `if_has_pos` — 보유 포지션 없으면 skip (빈 items 에러 방지)
2. `trailing` — community `TrailingStop` v2.1 플러그인, `trail_percent: 5.0`
   - 이 워크플로우가 매수한 포지션만 HWM 등록 (`record_workflow_order` →
     `register_symbol`) — **외부 보유 종목은 절대 매도하지 않음**
   - 플러그인이 positions 스냅샷의 `current_price` 로 HWM 을 직접 갱신
     (P&L 틱 리스너 없이도 트레일링 동작)
   - HWM 은 `{workflow_id}_workflow.db` 에 영속화 — 재시작 간 유지
3. `sell_pick` — positions ∩ 트리거 종목 (intersection 이 원본 position dict 의
   `quantity`/`close_side` 를 보존 → 전량 매도 수량 확보)
4. `sell_order` — 시장가 전량 매도 (US 주식 매도는 시장가 허용)

## 안전장치

| 장치 | 내용 |
|------|------|
| `cash_guard` | `orderable_amount >= $100` + partial-failure 시 resilience skip |
| 슬롯 가드 | 보유 0→최대 2종목, 보유 1→1종목만 추가 (합계 ≤2) |
| `dedup_held`/`dedup_open` | 중복 매수·미체결 중복 주문 방지 |
| sizing 45%×2 | 2종목 합산 예수금의 90% 이내 (체결 변동 여유 10%) |
| HWM 스코핑 | 워크플로우가 매수한 종목만 트레일링 매도 대상 |
| resilience skip | 주문/사이징/텔레그램 실패가 잡 전체를 중단시키지 않음 |
| NASDAQ 전용 | positions 의 exchange 한글 표시명 → 주문코드 매핑 이슈 회피 |

## Required Credentials

| ID | Type | Description |
|----|------|------|
| broker_cred | broker_ls_overseas_stock | LS 해외주식 실전 API (모의 미지원) |
| telegram_cred | telegram | 텔레그램 봇 (없으면 러너가 자동 strip) |

## 검증 상태

- L1 static `validate()`: PASS (errors/warnings 0)
- L2 mocked dry_run 사이클: PASS (`tests/test_examples_validation.py`)
- 플러그인 단위테스트: `src/community/tests/test_trailing_stop_plugin.py` 15건 PASS
- L3/L4 라이브: 호스트 러너(`test_86_trend_trailing_live.py`)로 수행

## 알려진 한계 (개선 백로그)

- 슬롯 가드가 **계좌 전체 positions 수** 기준 — 계좌에 다른 보유 종목이 있으면
  매수가 차단됨 (워크플로우 단위 포지션 레지스트리 필요)
- 미체결 지정가 매수 주문의 자동 취소/재호가 없음 (다음 사이클에서 dedup_open
  이 중복만 방지)
- 주간거래 시간창(09:30-16:30 KST)은 LS 공지와 대조 필요 — 코드베이스에
  주간거래 세션 파라미터 자체가 없어 LS 서버 수용 여부는 라이브로만 확인 가능
- 매도 트리거가 5분 폴링 — 실시간(WebSocket) 손절은 예제 82 패턴 참고
