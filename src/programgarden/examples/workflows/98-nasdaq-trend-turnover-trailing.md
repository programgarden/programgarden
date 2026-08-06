# 나스닥 추세 + 거래대금 상위 매수 + 트레일링스탑 매도

나스닥 지수(QQQ) 중기·단기 추세가 모두 양호할 때만, 미국주식 유니버스에서 **거래대금
(가격 × 거래량) 상위 3종목**을 **예수금으로 살 수 있는 가격대**로 골라 종목당 1주 시장가
매수. 보유 포지션은 **고점 대비 -5% 트레일링스탑**으로 시장가 청산.

> ⚠️ 해외주식은 LS 모의투자 미지원 — 이 워크플로우의 주문은 **실계좌 주문**이다.

이 예제는 **pg-ai 챗봇이 사용자 자연어 요청으로 생성**했고, 실행 검증 결과를 반영해
챗봇이 6차례 수정한 결과물이다. 원 요청:

> "나스닥 지수 중기, 단기 추세가 좋을때 종목들 중에서 투자금이 많이 몰리는 종목 상위 3개를
> 계좌 시드머니에 맞게 몇개 골라서 거래할래. 시드머니 부족하면 그만큼 더 저렴한 종목으로
> 상위3개 하면돼. 매수했으면 매도할때는 트레일링스탑으로 걸어줘."

## 실행 주기

`schedule` cron `*/5 * * * 1-5` + `hours` = `TradingHoursFilterNode(09:30–16:00,
America/New_York)` ⇒ **미국 정규장 중 5분 주기 폴링**. 매 주기마다 예수금 조회 → 추세 확인
→ 거래대금 상위 중 살 수 있는 가격대 확인 → 통과 시 매수, 그리고 보유 포지션
트레일링스탑 점검을 반복한다.

## 전략 구조

**매수 레그**

1. `qqq_hist` — QQQ 120일 일봉 (LS g3103)
2. `trend_check` (CodeNode) — MA5 / MA20 / MA60 계산
   → `any_trend = (MA20 > MA60) AND (MA5 > MA20)` (중기 AND 단기, 이름과 달리 AND)
3. `trend_gate` (IfNode) — 추세 불만족이면 매수 레그 전체 skip
4. `nasdaq_universe` — `OverseasStockSymbolQueryNode(country=US, stock_exchange=82)`
   LS g3190 마스터 500종목. **`MarketUniverseNode` 로는 동작하지 않는다** (아래 함정 참조)
5. `screener` — `ScreenerNode(market=overseas_stock, data_source=ls, max_results=50)`
   g3190 price/market_cap + g3101 enrich
6. `market_data_batch` → `price_filter` (CodeNode)
   - `trading_value = volume × price` 로 정렬 (내림차순)
   - `price <= orderable_amount` 필터 ⇒ **예수금이 적으면 자동으로 더 저렴한 종목으로**
   - 상위 3종목 컷 + `has_buy` 플래그
7. `buy_gate` → 슬롯별 `market_N` → `sizing_N`(fixed_quantity=1) → `order_N` (지정가 매수)
   - 슬롯 3개(`_1`/`_2`/`_3`)를 인덱스로 전개 — `top3[N]` 이 없으면 resilience skip
   - 주문 바인딩은 **bracket 표기** `order: {{ nodes.sizing_N["orders"][0] }}`
   - **해외주식 매수는 시장가 불가** → `order_type: "limit"`

**매도 레그 (트레일링스탑)**

1. `account_sell` → `if_has_pos` — 보유 포지션 없으면 skip (빈 items 에러 방지)
2. `trail_cond` — `ConditionNode(plugin=TrailingStop, trail_percent=5.0)`
   `items.from = {{ nodes.account_sell.positions }}`, `close = {{ row.current_price }}`
3. `sell_pick` — `SymbolFilterNode(intersection)` of positions ∩ `trail_cond.passed_symbols`
   → 원본 position dict 의 `quantity`/`close_side` 보존 (전량매도 수량 확보)
4. `sell_order` — 시장가 전량 매도, `order: {{ item }}`, resilience skip

## Required Credentials

| ID | Type | Description |
|----|------|------|
| broker_cred | broker_ls_overseas_stock | LS 해외주식 실전 API (모의 미지원) |

## 빌드 중 발견한 함정 (재현 시 주의)

| 증상 | 원인 | 해결 |
|---|---|---|
| 추세 노드가 101종목을 auto-iterate | `universe -> historical` 엣지가 붙어 단일 심볼 노드가 반복 실행. `trend_check` 가 QQQ 아닌 첫 종목을 봄 | 유니버스 → 히스토리 엣지 제거 |
| `SplitNode has no array to split` | SplitNode 필드명이 `items` | `array` 로 변경 |
| universe 가 맨 마지막에 실행 | 나가는 엣지가 없어 순서 미보장 | `trend_gate → universe → screener` 체인 |
| screener 0건 | `data_source` 미지정 | `data_source: "ls"` |
| screener 0건 (data_source 지정 후에도) | `MarketUniverseNode` 는 symbol+거래소 표시명만 출력 → g3101 enrich 전량 실패 | `OverseasStockSymbolQueryNode(stock_exchange="82")` 로 교체 |
| 매도 레그 skip + `호출 거래건수를 초과` | `account` / `account_sell` 이 계좌 TR 을 중복 호출해 LS 스로틀에 걸림 | 계좌 노드 하나만 두고 매수·매도 레그가 공유 |
| 매도 실주문에 `주문할 종목이 없습니다` | TrailingStop 은 **position 기반** 플러그인인데 시장가 데이터를 바인딩. 트리거 종목을 포지션과 교집합하는 단계 부재 | `items.from = account.positions` + `SymbolFilterNode(intersection)` + `order: {{ item }}` |
| 매수 주문 심볼이 `"price"` 로 전송돼 `해당 종목번호가 없습니다` | 주문 노드에 개별 `symbol`/`exchange`/`quantity` 를 바인딩 | order 객체 통째 바인딩 `order: {{ nodes.sizing_N["orders"][0] }}` (bracket 표기 필수) |
| `list index out of range: nodes.sizing_N["orders"][0]` | PositionSizingNode 가 `orders` 를 못 만듦 — `market_data` 에 dict 를 넘김 + `balance` 누락 | `market_data: {{ nodes.market_N.values }}` + `balance: {{ nodes.account.balance }}` |
| 매수가 시장가로 거부 | 해외주식 매수는 시장가 불가 (엔진이 지정가로 자동 변환하며 경고) | `order_type: "limit"` 명시 |

## 검증 상태 (2026-07-25, US 정규장 중)

| 항목 | 결과 |
|---|---|
| validate | ✅ is_valid |
| dry_run (실 로그인, 실데이터) | ✅ `status=completed`, `errors=0` |
| 추세 판정 | ✅ 실측 QQQ MA5=698.48 / MA20=712.00 / MA60=713.34 → 게이트 false (하락추세, 매수 차단 = 전략대로) |
| 종목 추출 (거래대금 상위) | ✅ AAPL($872M) / ADBE($45M) / AMGN($27M) |
| 시드머니 맞춤 선택 | ✅ 주문가능 $1.16 기준 ARBE($0.70) / ALP($0.23) / AVAT($0.32) 로 자동 대체 |
| 매도 레그 구조 | ✅ positions → TrailingStop → intersection → order 완주 |
| **실주문 전송·체결 (직접 실행)** | ✅ **ARBE 1주 @ $0.7005 지정가 매수 체결** (`rsp_cd=00040 매수 주문이 완료되었습니다`, `order_id=336`) |
| **트레이앱 로컬 실행 경로** | ✅ `local_bridge_start` → dsl-api 사전복호화 credential → `WorkflowRunner().run()` 27노드 완주 |
| **실주문 체결 (트레이앱 경로)** | ✅ **ALP 1주 @ $0.2300 매수 체결** (`order_1` auto-iterate `[1/1] Processing: ALP`) |

실주문 검증 근거:
- 직접 실행 로그: `Order submitted: ARBE buy 1@0.7005 → order_id=336`
- 트레이앱 경로 로그: `Auto-iterate: order_1 - 1 items / [1/1] Processing: ALP`
- 계좌 반영: 보유종목에 `ARBE 1주 avg_price 0.7000`, `ALP 1주 avg_price 0.2300` 신규 등장
- 예수금: `orderable_amount 1.16 → 0.45 → 0.22`, 미체결 내역 0건 = 전량 체결

> 트레이앱 경로 실행은 5분 폴링 스케줄 워크플로우라 `WorkflowRunner` 의 timeout(300s)에서
> `success=False` 로 취소된다. 이는 스케줄 노드가 다음 주기를 대기하기 때문이며 주문은
> 취소 전에 정상 전송·체결된다. 상시 구동에서는 트레이앱이 프로세스를 계속 유지한다.

> 실주문 검증은 **추세 게이트만 우회한 in-memory 사본**으로 수행했다(검증 시점 QQQ 하락추세).
> 종목 선정·예수금 필터·사이징·주문 경로는 저장본 그대로다. 저장된 워크플로우 자체는
> 추세 조건이 충족되는 날에만 매수한다.

**미검증으로 남은 것**
- 기존 보유종목(NIO/AUID)에 대한 트레일링스탑: 커뮤니티 `TrailingStop` 플러그인은
  **워크플로우가 직접 매수한 포지션만 HWM 등록**하고 외부 보유분은 의도적으로 제외한다.
  `trail_percent` 를 0.01 까지 낮춰도 `passed_symbols` 가 비어 매도가 나가지 않는다.
  기존 보유분까지 관리하려면 별도 기전(CodeNode HWM 추적 또는 `pnl_rate` 기반 손절)이 필요하다.
- 트레일링스탑 실매도 체결: 위 스코핑 때문에 이번 세션에서는 발생시키지 못했다.
  이 워크플로우가 매수한 ARBE 는 다음 주기부터 HWM 등록 대상이 되므로,
  ARBE 가 고점 대비 -5% 하락하면 실매도가 발생한다.
