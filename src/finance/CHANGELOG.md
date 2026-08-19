## [1.9.0] - 2026-08-19
> LS 토큰 경합 대응 — 만료시각만 보던 토큰 판정을 **사용 중 실패**까지 보도록 넓힌다.
> 죽은 토큰을 만료 전까지 계속 재사용하던 구조를 끊는 릴리즈다.
> 동반 릴리즈: `programgarden` **1.32.0**(provider 계약 확장 — 이 버전과 lockstep).

### Added
- **실측 `rsp_cd` 등재** — `IGW00121`(`유효하지 않은 token` 과 함께 오는 코드). 문구가
  바뀌어도 코드로 잡힌다(`error_msg` 가 빈 문자열인 경로가 있다).
- **`ls/token_errors.py` — 토큰 실패 단일 판정기.** LS 는 죽은 토큰을 한 가지 모양으로
  알려주지 않는다: 401/403 을 주는 경로, **HTTP 500 + `rsp_msg`** 만 주는 경로
  (국내 만료 토큰, 해외선물 시세 `o3101` 의 `유효하지 않은 token 입니다`), `error_msg` 는
  비고 `rsp_cd` 에만 원인이 담기는 주문 경로가 섞여 있다. 응답을
  `TOKEN_INVALID`(토큰이 죽었다고 **말해 준** 경우) / `TRANSIENT`(토큰인지 알 수 없는 일시
  실패) / `NONE` 으로 가른다.
- **`TokenManager.force_reissue()` / `force_reissue_async()`** — 만료 전이라도 재발급한다.
  세대 번호(`token_generation`)를 함께 받아, 관측 이후 다른 호출자가 이미 재발급했으면
  발급을 또 내지 않고 그 결과에 **합류**한다(시간 heuristic 없는 single-flight).
- **`TokenManager.set_on_token_refreshed()`** — 자체 발급으로 갱신된 토큰을 공유 저장소에
  되쓰기(write-through)할 수 있게 하는 훅. 저장소가 죽은 토큰을 계속 내주는 창을 없앤다.

### Fixed
- **`ensure_fresh_token(force_refresh=True)` 가 강제 갱신을 무시하던 결함.**
  `_refresh_token()` 이 `force` 를 인자로 받지 않아, Lock 획득 후 `if not self.is_expired():
  return True` 에서 **만료 전이면 그대로 성공 반환**했다. 그래서 401/403 재시도 경로가
  "재발급했다"고 믿고 **같은 죽은 토큰으로** 재시도했다. force 를 끝까지 전달한다.
- **`GenericTR` 이 죽은 토큰을 알아보지 못하던 문제.** 종전 판정은 401/403 과 만료 문구
  3종뿐이라 실측 문구 `유효하지 않은 token`(HTTP 500)이 걸리지 않았다. 새 판정기로 교체하고,
  **토큰 무효는 재시도 없이 즉시 재발급**, 일시 실패만 간격(0.5·1.5·3초)을 두고 재시도한다.

### Changed
- **`login()` 은 더 이상 `force_refresh=True` 를 쓰지 않는다.** 이 플래그가 "서버 캐시를
  무시하고 새로 발급하라"는 뜻이 됐으므로, 로그인마다 켜면 앱키 하나에 토큰이 계속 새로
  발급돼 "1 앱키 = 1 토큰"이 깨진다. 토큰이 없으면 `is_expired()` 가 True 라 발급은 그대로 된다.
- **주문 엔드포인트(`/order`)는 일시 실패를 재시도하지 않는다** — 5xx·타임아웃은 주문 접수
  여부를 알 수 없어 재시도가 곧 중복 주문이다. 반대로 토큰 무효는 인증 단계 거부라 주문이
  나가지 않았음이 보장되므로 재발급 후 재시도한다.
- **재발급 상한** — 롤링 10분 창에 3회(`FORCED_REISSUE_MAX`), 요청당 2회
  (`TOKEN_REISSUE_RETRY_MAX`), 연속 재발급 최소 간격 2초. 초과 시 조용한 `False` 가 아니라
  `TokenReissueLimitExceeded` 로 사유를 올린다.
- **토큰 provider 계약 확장(하위 호환)** — provider 가 받는 경우에만
  `force_reissue: bool` / `stale_token: str | None` 키워드를 넘긴다. 구판 provider 는
  시그니처 검사로 걸러 그대로 동작하고, force 를 못 넘기는 경우 경고를 남긴다.
- `acquired_at` 을 `ClassVar` 에서 일반 필드로 바꿨다(인스턴스마다 독립).

## [1.8.0] - 2026-08-19
> **소스 변경 없음.** `core` 1.24.0 동반 릴리즈에 맞춘 lockstep 버전 정렬이다
> (3서비스가 서로 다른 core 를 물지 않도록 하는 저장소 규율).

### Dependencies
- `programgarden-core` 하한을 `^1.24.0` 으로 올린다.

## [1.7.0] - 2026-08-15
### Added
- **`compute_futures_pnl_rate` 공유 헬퍼** (`ls/overseas_futureoption/extension/calculator.py`)
  — 진입가·현재가·`is_long` 으로 해외선물 수익률(%)을 계산하는 단일 공식을 신설. 두 가격
  인자를 방어적으로 `float` 로 강제하고 항상 `float` 를 반환해 Decimal/float 혼합 호출의
  `TypeError` 와 반환 타입 비일관을 제거한다.

### Changed
- **모의선물 계좌 추적기(`extension/tracker.py`) 수익률을 공유 헬퍼로 일원화** —
  `FuturesPositionItem` 의 `pnl_rate` 를 자체 계산 대신 `compute_futures_pnl_rate` 로 산출해
  REST 계좌 경로와 동일 공식을 쓴다.
- **실시간 포지션 side 표기 정정** — 존재하지 않는 `.side` 참조 대신 `is_long` 기준으로
  long/short 을 표기한다.

`core` 1.23.0 · `programgarden` 1.31.0 · `community` 1.15.0 과 동반 릴리즈.

## [1.6.16] - 2026-08-06
### Fixed
- **모의선물 계좌 추적기 예수금·잔고 오분류 (L11)** — 해외선물 모의계좌 추적기
  (`ls/overseas_futureoption/extension/tracker.py`)가 잔고/포지션/미체결 응답을
  `rsp_cd` 로만 에러 판정해, 모의계좌가 정상 데이터를 비표준 응답코드(예: 00136)와
  함께 돌려주면 조회 실패로 오분류했다. **실데이터(block2) 존재를 우선** 보고,
  데이터가 없을 때만 응답코드로 에러를 판정하도록 재구성.
- **TC1 실시간 구독 시 access token 로그 유출 (보안)** —
  `ls/overseas_futureoption/real/__init__.py` 가 구독 요청 전문을 access token
  포함 그대로 `print` 하던 것을 token 제외 + `logger.debug` 로 전환.

## [1.6.15] - 2026-07-10
### Fixed
- **README 해외주식 계좌 TR 라벨 정정 (docs-only)** — `README.md` "해외 주식 › 계좌"
  줄의 TR 4종 설명이 서로 어긋나 있던 것을 소스(각 TR `blocks.py` / `accno` 메서드
  docstring) 및 `docs/finance_guide.md` 기준으로 정정. 라이브러리 코드·동작 변경 없음.
  - `COSAQ00102`: 예수금 → **주문체결내역** (Account Order History)
  - `COSAQ01400`: 해외잔고 → **예약주문 처리결과** (Reservation-Order History)
  - `COSOQ00201`: 체결내역 → **해외주식 종합잔고평가** (Balance Evaluation)
  - `COSOQ02701`: 미체결 → **외화예수금/주문가능금액**
  - 해외주식 잔고 조회는 `COSOQ00201` 이 맞으며 `COSAQ01400` 은 예약주문 처리결과
    TR 임을 명확히 함(사용자 제보 반영). 코드블록 예시의 계좌 TR 주석도 동일 정정.

## [1.6.14] - 2026-07-07
### Added
- **t8409 업종차트(N분) TR 추가 (sector index N-minute chart)** — 신규 국내주식
  업종(indtp) TR. 업종코드로 해당 업종 지수의 N분(`ncnt` 0=30초 / 1=1분 / n=n분)
  차트 시계열을 조회한다. REST 엔드포인트는 t8408 과 **동일**한 차트 전용
  `POST /indtp/chart`(`KOREA_STOCK_INDTP_CHART_URL`). 응답 봉투는 t8408 과 동형:
  `cont_block`(=`t8409OutBlock`, 17필드 — t8408 대비 당일거래대금 `disvalue` 추가) +
  `block`(=`t8409OutBlock1`, 8필드 — t8408 대비 봉 거래대금 `value` 추가). `.req()`
  단건 / `.occurs_req()` 전체 연속조회(`cts_date`/`cts_time`) 지원. 노출 경로
  `ls.indtp().업종차트분(...)` / `ls.업종().업종차트분(...)` 및 최상위
  `from programgarden_finance import t8409`.
  - **챗봇 대비 필드 명료화(핵심)** — OHLC 는 업종 **지수(index points)** 이며 KRW
    가격이 아님을 description 에서 명시("NOT a price"). LS 가 지수 OHLC 를 JSON
    string 으로 직렬화하는 값은 Pydantic v2 가 `float` 로 auto-coerce.
  - **거래대금/거래량 단위 교차검증(정직성)** — LS 명세가 `disvalue`/`value`(거래대금)·
    `jivolume`/`jdiff_vol`(거래량) 단위를 **공식 선언하지 않음**. 샘플 응답 정합성
    교차검증(value÷volume ⇒ ~1만~1.4만 KRW/주 가중평균, 일 거래대금 ~7.5조)으로
    거래대금=**백만원(million KRW)**, 거래량=**천주(thousand shares)** 으로 확정하고,
    description 에 "cross-checked … not formally declared by LS" 병기.
  - 회귀 가드 `tests/test_korea_stock_t8409.py`(필드셋 11/17/8·examples·URL=
    `/indtp/chart`·string→float 강제변환·연속조회 updater·단위 표기) + 예제
    `example/indtp/run_t8409.py`(단건+연속).
- **최상위 `__all__` indtp 노출 보정** — import 만 되고 `__all__` 에서 누락됐던
  `t1511`/`t1514`/`t1516`/`t8408` 를 t8409 와 함께 `__all__` 에 정식 등재
  (`from programgarden_finance import *` 회귀 방지).

### Changed
- **업종(indtp) 예제 폴더 재정리** — `example/korea_stock/run_t1511|run_t1514|
  run_t1516|run_t8408.py` 4건을 `example/indtp/` 로 이동(git mv, 히스토리 보존)하고
  t8409 예제를 같은 폴더에 신설. 실행 코드는 `from programgarden_finance import LS`
  절대 import 라 경로 변경 영향 없음.

## [1.6.13] - 2026-06-28
### Added
- **t8408 업종차트(틱/n틱) TR 추가 (sector index tick/N-tick chart)** — 신규
  국내주식 업종(indtp) TR. 업종코드로 해당 업종 지수의 틱/n틱 차트 시계열을
  조회한다. REST 엔드포인트는 시세계열 업종 TR(t1511/t1514/t1516)의
  `/indtp/market-data`(`KOREA_STOCK_INDTP_URL`)와 **다른** 차트 전용
  `POST /indtp/chart`(`KOREA_STOCK_INDTP_CHART_URL`). 응답 봉투는 t8453 차트
  패턴과 동형: `cont_block`(=`t8408OutBlock`, `cts_date`/`cts_time` 연속커서) +
  `block`(=`t8408OutBlock1`, 틱 행). `.req()` 단건 / `.occurs_req()` 전체
  연속조회 지원. 노출 경로 `ls.indtp().업종차트틱(...)` / `ls.업종().업종차트틱(...)`
  및 최상위 `from programgarden_finance import t8408`(import-only).
  - **챗봇 대비 필드 명료화(핵심)** — OHLC 는 업종 **지수(index points)** 이며
    KRW 가격이 아님을 description 에서 명시("NOT a price"). LS 가 지수 OHLC 를
    JSON string 으로 직렬화하는 값은 Pydantic v2 가 `float` 로 auto-coerce.
  - 회귀 가드 `tests/test_korea_stock_t8408.py`(필드셋/examples/URL=`/indtp/chart`/
    string→float 강제변환/연속조회 updater) + 예제 `example/korea_stock/run_t8408.py`
    (단건+연속).

### Changed
- **업종(indtp) TR t1511/t1514/t1516 을 `ls.indtp()`/`ls.업종()` 신규 최상위
  도메인으로 이전** — LS 게이트웨이가 이미 `/indtp/` 를 `/stock/` 의 형제 최상위
  URL 네임스페이스로 분리해 둔 것에 맞춰, 업종 3 TR 을 `korea_stock/sector/` 에서
  신규 `ls/indtp/` 패키지로 이동하고 `Indtp` 클래스(`ls.indtp()`/`ls.업종()`)로
  승격. URL 라우팅(`KOREA_STOCK_INDTP_URL`, `/indtp/market-data`)·블록 스키마는
  불변. 테마(t1531/t1532/t1537)는 `/stock/sector` 의 `Sector` 클래스에 그대로 잔류.
  - **하위호환(clean break 아님)**: 기존 `ls.국내주식().업종테마().업종현재가()`
    등 fluent 경로 및 최상위 `from programgarden_finance import t1511` 경로는
    DeprecationWarning 위임 shim 으로 동일 객체를 반환(finance 2.0 에서 제거 예정).

## [1.6.12] - 2026-06-24
### Added
- **t1514 (업종기간별추이 / sector period trend)** — 신규 국내주식 업종 TR.
  업종코드로 해당 업종 지수의 기간별(일/주/월) 추이 시계열을 조회한다. REST
  엔드포인트는 다른 업종 TR(t1511/t1516)과 동일한 `POST /indtp/market-data`
  (`KOREA_STOCK_INDTP_URL`). 응답 봉투는 t8451 차트 패턴과 동형:
  `block`(=`t1514OutBlock`, `cts_date` 연속커서) + `block1`(=`t1514OutBlock1`,
  기간 행 24필드). `cts_date` 기반 `.req()` 단건 / `.occurs_req()` 전체
  연속조회 지원. 한글 별칭 경로 `LS().국내주식().업종테마().업종기간별추이(...)`.
  - **챗봇 대비 필드 명료화(핵심)** — Korean 라벨이 가격처럼 보이지만 실제로는
    업종 내 **종목 수(breadth count)** 인 필드를 description 에서 "NOT a price"
    로 명시: `high`(상승)/`unchg`(보합)/`low`(하락)/`up`(상한)/`down`(하한)/
    `totjo`(종목수). 업종 지수 OHLC 는 `jisu`/`openjisu`/`highjisu`/`lowjisu`
    (`...jisu` 접미사)로 분리. 모든 필드 `Field(title 한영병기, description,
    examples)` — OutBlock1 examples 는 LS 공식 샘플 응답(upcode 001, 20230605) 값.
  - **에러 명료화** — `_build_response` 가 HTTP≥400(`error_msg="HTTP {status}: {rsp_msg}"`)
    및 예외(`error_msg=str(exc)`) 시 명확한 사유를 채움(silent 실패 없음).
  - **no-inference**: `gubun2` 의 '분'(분기?) 코드 / `value1`·`value2` 구분 /
    통화단위 / `frgs`·`orgs` 부호 컨벤션 등 소스 미선언 항목은 추측하지 않고
    "not declared in the available source" 로 명시.
  - 패키지 export(`from programgarden_finance import t1514`) + `Sector` 메서드 +
    예제 `example/korea_stock/run_t1514.py`(단건+연속) + 회귀 가드
    `tests/test_korea_stock_t1514.py`(필드셋/examples/breadth-vs-OHLC/URL/에러/연속/
    string→float 강제변환/종단페이지 block=None/연속 updater raise — 36 케이스).

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
