## [Unreleased]

## [1.6.11] - 2026-06-20
### Changed
- **LS증권 2026-06-13 공지(업종TR 필드 자릿수 확대) 반영** — 코드에 실존하는
  TR 2개의 OutBlock 필드 메타데이터(description)만 갱신. 필드 타입은 `float`
  그대로이며 LS size 변경은 직렬화 폭 확대일 뿐이라 런타임/타입 영향 없음(메타데이터-only):
  - `t1511`(업종현재가) `T1511OutBlock` 17개 지수/대비 필드 description 에
    `Length 10.2 (LS scale)` 선언 + audit note 추가(기존 7.2 → 10.2). 대상:
    pricejisu, jniljisu, change, openjisu, highjisu, lowjisu, whjisu, yhjisu,
    yljisu, firstjisu, firchange, secondjisu, secchange, thirdjisu, thrchange,
    fourthjisu, forchange. 모듈 docstring 의 sub-index scale "NOT declared" →
    "10.2 declared" 로 갱신(`value`/`valuechange`/`jnilvalue` 통화단위 미선언 절은 유지).
  - `t1633`(기간별프로그램매매추이) `T1633OutBlock1` `jisu` / `change`
    description 을 `Length 6.2` → `Length 10.2 (LS scale)` 로 갱신 + audit note(6.2 → 10.2).
  - **no-inference**: LS 공지가 `wljisu`(52주최저)를 나열하지 않아 의도적으로 미변경
    (whjisu/yhjisu/yljisu 와 비대칭) — 회귀 가드로 잠금.
  - 회귀 가드: 신규 `tests/test_korea_stock_t1511.py`(61) + 기존
    `tests/test_korea_stock_t1633.py` 에 scale 갱신 가드 클래스 추가(6).
  - **범위 외(미구현)**: t8402(주식선물현재가) 및 업종차트 리네임/삭제
    (t8417/t8418/t8419/t4203→t8408/t8409/t8429)은 finance 패키지에 미구현이라
    이번 변경에 미포함 — 별도 신규 TR 구현 작업으로 분리.
### Dependencies
- `programgarden-core` ^1.14.2 → ^1.15.1 — cross-package alignment (order reject
  diagnostics / empty-order reason 모델, `NotificationCategory.ORDER_REJECTED`).

## [1.6.10] - 2026-06-06
### Added
- **Opt-in `token_provider` callback for server-issued tokens** (Verified League §3.2.3) —
  `LS` accepts a sync/async `token_provider` via `set_token_provider()`; when set,
  the token manager refreshes its access token through the provider instead of
  logging in with credentials. Backward compatible (no provider = unchanged login).

## [1.6.9] - 2026-05-27
### Added
- **A-6: per-connection real-time subscription cap** —
  `RealRequestAbstract._add_message_symbols` rejects subscriptions beyond
  `max_subscribe_symbols` (default `DEFAULT_MAX_SUBSCRIBE_SYMBOLS`=100,
  summed across all TR codes, constructor-configurable, `<=0` disables)
  with a new `SubscriptionLimitExceeded` (RuntimeError subclass). Checked
  before mutation so a rejection leaves subscription state clean; only new
  unique symbols count toward the cap, so reconnect auto-resubscribe never
  trips it. Wired into all 4 product subclasses; adds
  `get_subscription_count()` / `get_subscription_capacity()` helpers.
### Changed
- **A-1: account-scoped rate-limit key composition** —
  `set_tr_header_options()` now namespaces each TR's `rate_limit_key` with
  the logged-in account (`f"{appkey}:{tr_cd}"`), so the same account's
  concurrent connections share a bucket while different accounts in one
  process stay isolated. Single-account deployments are 100%
  behavior-preserving (one appkey → same bucket). The dormant
  `_RateBucket` account-total gate remains opt-in (off by default).

## [1.6.8] - 2026-05-20
### Changed
- Maintenance release — version bump for cross-package alignment. No finance code changes since 1.6.7.

## [1.6.7] - 2026-05-16
### Dependencies
- `programgarden-core` ^1.12.3 → ^1.12.4 — picks up
  `HISTORICAL_VALUE_FIELDS`, 10 node-schema port alignments and the
  3 new validation ErrorCodes (AI/Dynamic). No finance code changes.

## [1.6.6] - 2026-05-14
### Dependencies
- `programgarden-core` ^1.12.2 → ^1.12.3 — picks up the structured
  validation models (ErrorCode / ErrorInfo / Recommendation /
  ValidationResult v2) so downstream consumers that reach into core
  via the finance package see the new shape. No finance code changes.

## [1.6.5] - 2026-05-13
### Fixed
- **11 Korea Stock TR `rate_limit_key` 누락 정정** — `t1665` / `t8452` /
  `t8453` / `t8407` / `t8454` / `t1901` / `t1903` / `t1904` / `t1638` /
  `t1927` / `t1702` 의 `SetupOptions(rate_limit_count=1, rate_limit_seconds=1)`
  설정에 `rate_limit_key` 가 빠져 있어 동일 TR 인스턴스를 여러 개 생성하면
  각자 독립 카운터로 동작 → LS 서버단 `IGW00201` (호출 거래건수 초과)
  발생. `t8451` 패턴 (`on_rate_limit="wait"` + `rate_limit_key="<tr_id>"`)
  으로 통일하여 라이브러리 단일 프로세스 내 자동 직렬화 보장.
- **17 Korea Stock TR `exchgubun` Literal 필드 거짓 docstring 정정** —
  `t8451` / `t1102` / `t1104` / `t1105` / `t1302` / `t1305` / `t1308` /
  `t1310` / `t1486` / `t8450` / `t1631` / `t1632` / `t1633` / `t1636` /
  `t1637` / `t1640` / `t1662` 의 `Literal["K","N","U"]` 필드 description
  에 "Other values are treated as KRX per LS source." 같은 거짓 문구
  산재. Pydantic Literal 은 다른 값을 거부하므로 LS 서버 측 "그외 KRX
  처리" 로직에 도달 불가 → 외부 사용자가 `exchgubun=""` 빈 문자열
  전달 시 `ValidationError` 반복 크래시 원인. "Pydantic validates
  strictly — only 'K', 'N', 'U' are accepted; empty string and other
  values are rejected." 로 정정.
- **CSPAT00601 응답 코드 가시성 향상** — 주문 TR 응답 코드 `00040`
  (매수 접수) / `00039` (매도 접수) 가 docstring 에만 있고 README /
  finance_guide 미게재. 외부 사용자가 `rsp_cd != "00000"` 로 실패
  판정 → 정상 주문 거부로 오분류 → 내부 포지션과 실계좌 불일치 →
  `01478` 매도가능수량 부족 반복 장애 원인. README "응답 코드 참조"
  새 섹션 + finance_guide 상세 (라이브러리 자동 throttle 메커니즘 +
  Redis 공유 패턴 포함) 신규 게재.

### Added
- `example/korea_stock/run_CSPAT00601_with_SC1.py` — CSPAT00601
  `block2.OrdNo` (int) ↔ SC1 `body.ordno` (str) 캐스팅 매칭 + 부분체결
  누적 + 거부 이벤트 처리 + asyncio.Future timeout 참고 예제.
- `docs/alphaworks_ls_response_2026-05-12.md` — AlphaWorks 운영
  보고에 대한 라이브러리 측 답신 (§1~§8 7 개 최종 질문 + 섹션별
  verification 요청 답변).

### Internal
- 회귀 안전망 5 개 신규: `tests/test_setup_options_coverage.py` (3) —
  모든 blocks.py 의 `SetupOptions(...)` 가 `rate_limit_key` +
  `on_rate_limit="wait"` 설정 여부 AST 기반 자동 검증.
  `tests/test_literal_field_docstring_truth.py` (2) — Literal 타입
  필드 description 에 거짓 클레임 자동 검출. `CSPAT00601.MbrNo` 등
  `str` 타입 truthful 클레임은 negative-control 로 통과.
- `tests/test_cspat00601_sc1_mock.py` 신규 (10) — 파서 (4) + OrdNo
  캐스팅 계약 (1) + asyncio Future 매칭 라이프사이클 (5). 실라이브
  검증은 장중 별도 수행 필요.
- 회귀: finance 전체 2563 / 2563 PASS.

### Dependencies
- programgarden-core ^1.12.2 (unchanged).

## [1.6.4] - 2026-05-12
### Added
- **11 Korea Stock Market TR** under `ls.korea_stock().market()` —
  Korea Stock REST TR count 64 → 75, total finance TR blocks.py
  139 → 150 (AI-chatbot field metadata coverage remains 100%):
  - `t1302` 주식분별주가조회 / Stock minute-bar price query —
    intraday minute-aggregated OHLCV rows for a single Korean symbol
    over the trading day, with `cts_time` cursor pagination.
  - `t1305` 기간별주가 / Stock period-bar price query —
    daily/weekly/monthly/yearly bar OHLCV rows over a date range,
    bar interval selectable via `gubun` enum (D/W/M/Y).
  - `t1308` 주식시간대별체결조회챠트 / Stock time-bucket execution chart —
    time-bucketed (1/5/10/30/60-minute) execution aggregates with
    LS-declared `sign` enum (1=상한 / 2=상승 / 3=보합 / 4=하한 / 5=하락).
  - `t1310` 주식당일전일분틱조회 / Stock today-yesterday minute-tick —
    intraday tick-level prints for a symbol, today or yesterday
    selectable via `gubun` enum.
  - `t1410` 초저유동성조회 / Stock ultra-low-liquidity query —
    ranked ultra-low-liquidity rows for a market scope (`gubun`:
    전체/코스피/코스닥) with `cts_shcode` cursor. **sign enum policy**:
    LS spec table does NOT formally declare the mapping; partial
    evidence (LS official example response with `sign='3'` on no-change
    rows + `sign='5'` on down rows, plus live 2026-05-12 calls
    returning `sign='1'` on limit-up rows) supports the sibling
    1=상한 / 2=상승 / 3=보합 / 4=하한 / 5=하락 convention used by
    t1308 / t1422 / t1427 / t1449. `sign='1'`/`'2'`/`'4'` rows are
    unobserved in our 2026-05-12 evidence set and documented as
    partial-evidence in `T1410OutBlock1.sign` description.
    `change` is the absolute price-delta magnitude (unsigned), not
    a percent; pair with `sign` for direction and `diff` for percent.
  - `t1427` 상/하한가직전 / Stock near-limit-up/down —
    symbols approaching 상한가/하한가 threshold, market scope via
    `gubun`, direction via `updnflag`.
  - `t1449` 가격대별매매비중조회 / Price-bucket trade-share query —
    intraday trade volume distribution across price buckets.
  - `t1486` 시간별예상체결가 / Time-of-day expected execution price —
    pre-market / post-market expected execution price per time bucket.
  - `t1488` 예상체결가등락율상위 / Top expected-price percent-movers —
    ranked top movers in expected execution price during the
    pre-market call auction phase.
  - `t1104` 주식현재가시세메모 / Stock quote + memo — current quote
    enriched with KRX memo flags (관리종목 / 투자유의 / 거래정지 etc).
  - `t1105` 주식피봇/디마크조회 / Stock pivot / DeMark query —
    classic pivot R1/R2/R3 + DeMark levels for a symbol.
- Per-TR top-level export + `example/korea_stock/run_*.py` runnable
  scripts for t1104 / t1105 / t1410.

### Internal
- t1410 `sign`-enum partial-evidence policy follows the project
  `feedback_no_inferred_formulas` rule: descriptions explicitly
  separate LS-declared facts (gubun mapping, cts_shcode cursor)
  from partial-evidence claims (sign convention, unobserved values).
- 11 plan documents under `.claude/pg-plans/` covering each TR's
  field-mapping decisions (now untracked per `.gitignore` policy).

### Dependencies
- programgarden-core ^1.12.2 (unchanged).

## [1.6.3] - 2026-05-08
### Added
- AI-chatbot-ready field metadata across every TR `blocks.py` in the LS
  Securities client tree (138/138 TR modules, 100% coverage). Every
  InBlock / OutBlock / OutBlockN field now declares
  `Field(title="한글 (English)", description=<English>, examples=[...])`
  so external workflow-builder chatbots can drive `model_json_schema()`
  directly without reading source. Coverage by domain:
  - `overseas_stock/`: 24 TRs (accno / chart / market / order / real)
  - `overseas_futureoption/`: 35 TRs (accno / chart / market / order /
    real)
  - `korea_stock/`: 67 TRs (accno / chart / etc / etf / frgr_itt /
    investor / market / order / ranking / real / sector)
  - `oauth/` + `common/real`: oauth `generate_token` /
    `revoke_token` + JIF (sector-index real subscribe/unsubscribe
    body) modules.
- Pending-blocks honeypot test (`test_no_pending_blocks_remain`) guards
  against `blocks.py` regressions where new TRs ship without the AI
  metadata field set. Reads
  `.claude/pg-plans/artifacts/20260506-pending-blocks.txt` (currently
  empty).
- No-inferred-formulas description guards across `dan_sign` /
  `jangubun` / `jstatus` / time-suffix fields (LS-undocumented enum
  mappings, formulas, scales, and units are explicitly NOT asserted —
  descriptions carry `"not declared in available source"` /
  `"consume as returned by LS"` qualifiers per the
  `feedback_no_inferred_formulas` policy).

### Changed
- `blocks.py` class docstrings and Field `description=` strings —
  Korean → English across the TR field-metadata scope (blocks.py
  only). Translated: 12 class docstrings + 22 Field descriptions on
  korea_stock/real (IJ_, SC0..SC4), overseas_stock/real (AS0..AS4,
  GSC, GSH), and overseas_futureoption/real (OVC, OVH, WOC, WOH).
  Plus 30 vestigial trailing Korean docstring statements
  (`"""응답 코드"""` etc.) removed from 10 blocks.py modules.
  Korean parenthetical references in established description templates
  ("(상한가)", "(매도)", "(뉴욕)") preserved as the AI
  Korean↔English mapping convention, not a translation gap.
- Field signature uplift: TR `blocks.py` Field declarations migrated
  from positional `Field(<default>, description=...)` shape (where
  applicable) to keyword `Field(<default>, title=..., description=...,
  examples=[...])` shape. Wire formats, default values, types, and
  pydantic aliases preserved — public API behavior unchanged.

### Verification
- `rg '^\s*"""[가-힣]' src/finance/programgarden_finance/ls/ | grep blocks.py | wc -l` → 0
- `rg '^\s*description="[가-힣]' src/finance/programgarden_finance/ls/ | grep blocks.py | wc -l` → 0
- `find src/finance/programgarden_finance/ls -name blocks.py | xargs grep -L "examples=" | wc -l` → 0
- Regression: 1929 passed (Phase 6 baseline maintained, no behavior delta).

## [1.6.2] - 2026-05-08
### Added
- `t1109` (시간외체결량 / Off-hours execution volume) — new TR under
  `programgarden_finance.ls.korea_stock.market.t1109`. Returns
  off-hours per-trade rows (single-price 시간외 단일가 + after-hours
  close 시간외 종가) for a Korean stock symbol with trade time, price,
  previous-day direction code, percent change, trade strength, and
  cumulative volume. Pagination uses the `dan_chetime` + `idx` cursor
  pair echoed back in `T1109OutBlock`. Rate limit: 1/sec.
- `Market.t1109()` + `Market.시간외체결량` Korean alias on the
  `KoreaStock.시세()` domain. Top-level `programgarden_finance.t1109`
  re-export.
- AI metadata field set (Korean↔English title, English description,
  examples) on every t1109 InBlock / OutBlock / OutBlock1 field per
  the `feedback_tr_field_metadata` convention. `dan_sign` description
  follows the no-inferred-formulas policy (no enum mapping asserted).
- `dan_chetime` description documents the observed `HHMMSS` + 4-digit
  suffix structure with an LS-spec disclaimer (suffix unit not
  formally declared — sub-second component or per-second sequence).
- Regression guards in `tests/test_korea_stock_t1109.py` (33 tests):
  Field examples typecheck, model_fields coverage, LS official example
  response round-trip, anti-inference guards for `dan_sign` /
  `dan_price` / `dan_change` / `dan_chetime`.
- Example script `example/korea_stock/run_t1109.py` (single + occurs_req
  smoke test).

## [1.6.1] - 2026-05-04
### Dependencies
- programgarden-core ^1.12.2 (batch sync — no core code changes,
  monorepo coherence with finance 1.6.1).

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
