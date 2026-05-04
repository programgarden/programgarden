## [Unreleased]
### Changed
- `CSPAQ12200OutBlock2` / `CSPAQ22200OutBlock2` / `CSPBQ00200OutBlock2`
  — `MgnRat100pctOrdAbleAmt` field semantic flip applied by LS Securities
  on 2026-04-11 12:00 KST (originally announced for 2026-04-10 17:00 KST,
  rescheduled by LS notice). Until 2026-04-10 the field held
  증거금률 100% 주문가능 금액 (100% margin-rate order-able amount); from
  2026-04-11 onward the same field carries 미수주문 가능 금액
  (credit/missed-payment-eligible order-able amount). Field name and
  Pydantic type are unchanged — only the meaning of the value rotated.
  Title and description on all three OutBlocks were updated to record
  both the pre-2026-04-11 and post-2026-04-11 semantic so AI workflow
  generators do not reuse the old mental model. Migration: callers that
  previously read `MgnRat100pctOrdAbleAmt` for 증거금률 100% semantics
  must switch to `RcvblUablOrdAbleAmt` on CSPAQ12200/22200 (CSPBQ00200
  itself does not expose the legacy value — LS marked CSPBQ00200 as
  semantic-change only, no field addition).
- `CSPAQ12200OutBlock2` / `CSPAQ22200OutBlock2` — `RcvblUablOrdAbleAmt`
  audit-trail date corrected from 2026-04-10 to 2026-04-11 to match the
  rescheduled LS rollout window. Description expanded to note that the
  field carries the legacy 증거금률 100% 주문가능 금액 previously exposed
  by `MgnRat100pctOrdAbleAmt`, so callers understand the swap intent.

### Added
- `CSPAQ12200OutBlock2` / `CSPAQ22200OutBlock2` — new field
  `RcvblUablOrdAbleAmt` (미수불가주문가능금액, KRW Length 16). LS
  Securities applied the addition on 2026-04-11 12:00 KST (originally
  announced for 2026-04-10 17:00 KST, then rescheduled). Inserted right
  after `DpslRestrcAmt` (CSPAQ12200) and `CslLoanAmtdt1` (CSPAQ22200) per
  LS notice. Backward compatible (`default=0` accepts pre-update LS
  responses).
- Regression guards — `tests/test_korea_stock_CSPAQ12200.py` (14) +
  `tests/test_korea_stock_CSPAQ22200.py` (14) +
  `tests/test_korea_stock_CSPBQ00200.py` (9) = 37 tests covering field
  presence, default, decoding, position assertion, 2026-04-11 audit
  trail, semantic-change description (date / old & new meaning /
  replacement field reference), official example response decode,
  CSPBQ00200's "변경 only" asymmetry (no `RcvblUablOrdAbleAmt`
  addition), and `examples=[...]` self-validation.

## [1.6.0] - 2026-05-04
### Dependencies
- programgarden-core ^1.12.1 (batch release sync — no core code changes,
  monorepo coherence).

### Added
- t1631 (프로그램매매종합조회) — Korea Stock program-trading
  comprehensive query. Returns eight scalar order/remainder aggregates
  (sell vs buy × arbitrage vs non-arbitrage × unfilled-remaining vs
  ordered) plus an Object Array of program-trading rows. No
  continuation paging — a single response covers same-day or period
  queries. Korean alias: `프로그램매매종합조회`. Korea Stock REST TR
  count 56 → 57.
- t1632 (시간대별프로그램매매추이) — Korea Stock time-bucketed
  program-trading trend. Returns KP200 / BASIS continuation marker plus
  Object Array of per-time-bucket rows (KP200 / BASIS / total /
  arbitrage / non-arbitrage buy / sell / net-buy). Supports tr_cont
  paging via date + time CTS cursors via `occurs_req()`. Korean alias:
  `시간대별프로그램매매추이`. Korea Stock REST TR count 57 → 58.
- t1633 (기간별프로그램매매추이) — daily / weekly / monthly program-trading
  trend over [fdate, tdate] period on KOSPI / KOSDAQ. Supports tr_cont
  continuation paging via single `date` CTS cursor (unlike t1632 which
  pages by date+time). Korean alias: `기간별프로그램매매추이`. Korea
  Stock REST TR count 58 → 59.
- t1636 (종목별프로그램매매동향) — per-symbol program trading flow.
  Includes the net-buy ratio versus market cap added by LS on
  2026-01-08. Supports IDXCTS-based continuation paging via `cts_idx`.
  Korean alias: `종목별프로그램매매동향`. Korea Stock REST TR count
  59 → 60.
- t1637 (종목별프로그램매매추이) — per-symbol program-trading time series.
  Two display modes selected by `gubun2`: time-bucketed within a trading
  day (`'0'`) or daily across multiple trading days (`'1'`). Supports
  tr_cont continuation paging via a gubun2-aware cursor (time cursor in
  time mode, date cursor in daily mode); `cts_idx` is a chart marker
  fixed at 9999 per LS spec and is NOT used for paging. Korean alias:
  `종목별프로그램매매추이`. Korea Stock REST TR count 60 → 61.
- t1640 (프로그램매매종합조회미니) — single-snapshot program-trading
  aggregates (buy / sell / net-buy quantity, amount, day-over-day
  changes, and basis) for one market + arbitrage combination selected
  by a unique 2-digit `gubun` encoding (`'11'`/`'12'`/`'13'` for
  거래소 total/arbitrage/non-arbitrage, `'21'`/`'22'`/`'23'` for KOSDAQ
  total/arbitrage/non-arbitrage). No continuation paging — a single
  response covers the entire query. xingAPI FUNCTION_MAP type mapping:
  six `*value` / `*valdiff` fields are `double` (float), distinct from
  t1631 / t1636 sibling TRs which declare the same Korean labels as
  `long` (int). Korean alias: `프로그램매매종합조회미니`. Korea Stock
  REST TR count 61 → 62.
- t1662 (시간대별프로그램매매추이차트) — time-chart program-trading
  Object Array. Returns a `List[T1662OutBlock]` of time-bucketed KP200
  index, BASIS, change-sign (LS-published `'1'`=상한 / `'2'`=상승 /
  `'3'`=보합 / `'4'`=하한 / `'5'`=하락), change value, and total /
  arbitrage / non-arbitrage buy / sell / net-buy + volume per row for
  KOSPI (`gubun='0'`) or KOSDAQ (`gubun='1'`). Inputs select market
  (`gubun`), amount/quantity mode (`gubun1`), today/prior-day axis
  (`gubun3`), and exchange (`exchgubun`). Single response — no
  continuation paging (no `occurs_req`). Korean alias:
  `시간대별프로그램매매추이차트` (note `차트` suffix to avoid collision
  with t1632's `시간대별프로그램매매추이`). Field policy: every InBlock
  field is Required (no inferred defaults); OutBlock numeric / string
  fields use defensive zero defaults for parsing LS-omitted fields, and
  `sign` uses `Optional[Literal[...]] = None` (None = LS-omitted
  sentinel, NOT 보합). Korea Stock REST TR count 62 → 63.

### Fixed
- t1632: `time` field length description 6 → 8 (LS xingAPI FUNCTION_MAP
  ground truth: both InBlock and OutBlock declare `time` as char,8).

### Changed
- t1631 ~ t1637: AI chatbot training accuracy — removed inferred
  expressions in field descriptions per xingAPI FUNCTION_MAP metadata:
  - t1636 / t1637: removed unit inferences (`"in KRW"`, `"in shares"`)
    on 9 + 9 = 18 OutBlock fields.
  - t1636: removed `sgta` "Empirically observed to be 억 원" inference,
    `mkcap_cmpr_val` formula / identity inference, OutBlock1 docstring
    identity formula.
  - t1637: removed OutBlock1 docstring sibling-TR identity reference.
  - t1633 / t1636 / t1637: removed `sign` enum mapping
    (`'1'`=상한 / `'2'`=상승 / etc.) — unified with t1632 conservative
    pattern (`"does not publish an enum mapping"`).
  - t1631 / t1632 / t1633 / t1636 InBlock `char,1` fields — appended
    `"Length 1."` for description consistency (13 fields).

## [1.5.1] - 2026-04-18
### Dependencies
- programgarden-core ^1.12.0 (NodeTypeSchema AI metadata — 5 new optional
  fields on every node, AIAgentNode `tool_selection` / `tool_top_k`
  removed).

### Changed
- No code changes. Compatibility release paired with the
  core 1.12.0 / community 1.13.0 / programgarden 1.21.0 publish cycle.

## [1.5.0] - 2026-04-14
### Dependencies
- programgarden-core ^1.11.0 (FieldSchema/OutputPort example 확장 — 노드 스키마에 shape 예시 노출).

### Changed
- 코드 변경 없음. core 의존성 버전 업데이트에 따른 동반 배포.

## [1.4.4] - 2026-04-06
### Dependencies
- programgarden-core ^1.9.9 (expression filter 연산자 매칭 수정)

## [1.4.3] - 2026-03-24
### Fixed
- g3204 (해외주식 차트 일주월년별) rate_limit_seconds 1초 → 3초 (API 호출 초과 방지)

## [1.4.2] - 2026-03-21
### Changed
- GSH(실시간 호가) blocks.py: 미제공 필드 description 마킹 + 클래스 docstring 제약사항 추가
- GSH client.py: RealGSH 클래스 docstring 추가
- g3106(REST 호가) blocks.py: 건수 미제공 필드 마킹 + 클래스 docstring 추가
- real_GSH.py 예제: 제약사항 모듈 docstring 추가

### Dependencies
- programgarden-core ^1.9.5

## [1.4.1] - 2026-03-04
### Dependencies
- programgarden-core ^1.9.0 (국내주식 노드 포함)

## [1.4.0] - 2026-03-01
### Added
- **국내주식(KoreaStock) 69 TR 지원**: `ls.korea_stock()` 진입점
  - 시세 13개: t9945(마스터), t1101(호가), t1102(현재가), t8450, t8407, t8454 등
  - 계좌 10개: CSPAQ22200(예수금), CSPAQ12200(잔고), CSPAQ13700(미체결) 등
  - 주문 3개: CSPAT00601(현물주문), CSPAT00701(정정), CSPAT00801(취소)
  - 랭킹 7개: t1441(등락률), t1444(시가총액), t1452(거래량) 등
  - 차트 4개: t8451(일주월년), t8452(분봉), t8453(틱봉), t1665(종합)
  - 업종/테마 5개, 투자자 7개, ETF 3개, 기타 4개
  - 실시간 13개: S3_(체결), K3_(KOSDAQ), H1_(호가), SC0~SC4(주문이벤트) 등
- **KrStockAccountTracker**: SC1 자동 갱신으로 실시간 잔고 추적
- **Extension 모듈**: `account_tracker()` 확장 메서드

### Fixed
- `_schedule_coroutine()` TOCTOU race condition 수정 (해외주식/국내주식 공통)
- investor 6개 / sector 2개 TR URL 엔드포인트 수정
- 전체 국내주식 TR InBlock Literal 타입 검증 추가 및 버그 수정

### Changed
- deps: programgarden-core ^1.8.0

## [1.3.4] - 2026-02-25
### Changed
- deps: programgarden-core ^1.6.0

## [1.3.3] - 2026-02-24
### Fixed
- **TokenManager race condition 방어 (H-19)**: threading.Lock + asyncio.Lock 이중 잠금, 갱신 실패 시 최대 2회 재시도
- **WebSocket 재구독 (H-15)**: 구독 심볼 추적(_subscribed_symbols) + 재연결 시 자동 재구독
- **WebSocket 메시지 누락 경고 (H-16)**: 재연결 중 수신 불가 경고 로그
- **WebSocket force close 경고 (H-17)**: 다른 노드 영향 경고 로그
- **WebSocket ref_count Lock (C-7/C-8)**: asyncio.Lock으로 race condition 해결
- **WebSocket staleness 감지 (M-13)**: get_staleness_sec(), 120초 무 데이터 경고

### Changed
- deps: programgarden-core ^1.5.1

## [1.3.2] - 2026-02-20
### Fixed
- fix: WebSocket 싱글톤 패턴 적용 - real() 호출마다 새 WebSocket 생성하던 문제 해결
- real()이 동일 token_manager에 대해 싱글톤 Real 인스턴스 반환
- connect() 가드: 이미 연결된 상태에서 중복 WebSocket 생성 방지
- close() 참조 카운트: 다른 구독자가 있으면 WebSocket 유지
- 하나의 WebSocket에서 GSC/AS0/AS1/OVC/TC1~TC3 등 여러 TR 동시 구독 가능

### Added
- tests/test_real_singleton.py: 단위 테스트 19개 추가

## [1.3.1] - 2026-02-19
### Changed
- deps: programgarden-core ^1.4.0 의존성 동기화 (OverseasStockFundamentalNode, PER/EPS 추가)

## [1.3.0] - 2026-02-17
### Changed
- deps: programgarden-core ^1.3.0 의존성 동기화 (IfNode, Edge from_port 추가)

## [1.2.0] - 2026-02-15
### Changed
- release: core ^1.2.0 의존성 동기화, PyPI 첫 프로덕션 배포

## [1.1.8] - 2026-02-10
### Changed
- deps: programgarden-core 1.1.10 버전으로 업데이트 (translate_schema 번역 범위 수정)

## [1.1.7] - 2026-02-10
### Changed
- deps: programgarden-core 1.1.9 버전으로 업데이트 (i18n 957키 완전 동기화, unified node registry)

## [1.1.6] - 2026-02-09
### Changed
- deps: programgarden-core 1.1.8 버전으로 업데이트 (unified node registry, Dynamic_ prefix 통일)

## [1.1.5] - 2026-02-07
### Changed
- deps: programgarden-core 1.1.7 버전으로 업데이트 (credential type overseas 명칭 변경)

## [1.1.4] - 2026-02-06
### Changed
- deps: programgarden-core 1.1.6 버전으로 업데이트 (credential_id 리네이밍)

## [1.1.3] - 2026-02-06
### Changed
- deps: programgarden-core 1.1.5 버전으로 업데이트

## [1.1.2] - 2026-02-05
### Changed
- deps: programgarden-core 1.1.3 버전으로 업데이트

## [1.1.1] - 2026-02-05
### Changed
- feat: programgarden-core 1.1.2 버전 업데이트 (TestPyPI)

## [1.1.0] - 2026-02-04
### Changed
- feat: programgarden-core 1.1.0 버전 업데이트에 따른 종속성 수정

## [1.0.3] - 2026-01-30
## Changed
- feat: programgarden-core 1.0.2 버전 업데이트에 따른 종속성 수정

## [1.0.2] - 2026-01-30
## Changed
- feat: programgarden-core 1.0.1 버전 업데이트에 따른 종속성 수정

## [1.0.1] - 2026-01-30

### Changed
- feat: programgarden-core 1.0.1 버전 업데이트에 따른 종속성 수정

---

## Legacy Changelog (programgarden-finance v0.x)

## [0.1.13] - 2025-12-05
### Changed
- feat: programgarden-core 버전 업데이트에 따른 종속성 수정

## [0.1.12] - 2025-12-05
### Changed
- feat: python 3.10으로 최소 버전 상향

## [0.1.11] - 2025-12-05
### Changed
- programgarden-core 버전 업데이트에 따른 종속성 수정

## [0.1.10] - 2025-12-05
### Changed
- programgarden-core 버전 업데이트에 따른 종속성 수정

## [0.1.9] - 2025-11-27
### Changed
- programgarden-core 버전 업데이트에 따른 종속성 수정

## [0.1.8] - 2025-11-19
### Changed
- Token Manager의 토큰 갱신 로직 수정

## [0.1.7] - 2025-11-15
### Changed
- programgarden-core 버전 업데이트에 따른 종속성 수정

## [0.1.6] - 2025-11-07
### Changed
- 버전 및 일부 변수 타입 변경

## [0.1.5] - 2025-11-02
### Changed
- 모의투자 상태 체크 업데이트
- README.md에 프로젝트 개요, 빠른 시작 가이드, 예제 코드, API 참조 등 추가
- 비개발자 및 개발자 모두를 위한 상세한 문서화 완료

## [0.1.4] - 2025-10-02
### Fixed
- print 제거

## [0.1.1] - 2025-09-27
### Fixed
- COSOQ00201의 변수 타입 수정

## [Unreleased]
- 없음
