## [1.12.1] - 2026-04-17
### Fixed
- position 기반 플러그인 10종의 `positions` 파라미터를 `list[dict]` 포맷으로 통일 (해외선물 RealAccountNode dict 출력 사용 시 `AttributeError: 'list' object has no attribute 'items'` 오류 수정)
  - stop_loss, profit_target, partial_take_profit, drawdown_protection, max_position_limit, time_based_exit, dynamic_stop_loss, roll_management: `positions.items()` → list 순회
  - var_cvar_monitor, beta_hedge: 내부에서 `positions` list를 symbol→dict 매핑으로 재구성 (`positions[symbol]` 접근 패턴 유지)
- 각 플러그인 docstring `{symbol: {...}}` 예시를 `[{symbol, ...}, ...]` 로 업데이트
- `exchange` 필드 우선 사용, `market_code` 폴백으로 정합성 개선
### Dependencies
- programgarden-core ^1.11.1

## [1.12.0] - 2026-04-14
### Added
- `TelegramNode` 출력 포트 example shape 노출:
  - `sent`: `{"sent": True, "chat_id": "123456789"}`
  - `message_id`: `"1234"`
- LLM 이 `{{ nodes.telegram.sent }}` expression 작성 시 출력 shape 즉시 파악 가능.

### Dependencies
- programgarden-core ^1.11.0 (OutputPort.example 신설 지원).

## [1.11.0] - 2026-04-09
### Added
- TECHNICAL 플러그인 7종: RSIDivergence, UltimateOscillator, KDJ, Aroon, HeikinAshi, VortexIndicator, HurstExponent
- POSITION 플러그인 3종: SharpeRatioMonitor, SortinoRatio, CalmarRatio
- 총 플러그인: 67 → 77개 (TECHNICAL 59 + POSITION 18)
- 테스트 174개 추가 (총 1203개)

## [1.10.5] - 2026-04-06
### Dependencies
- programgarden-core ^1.9.9 (expression filter 연산자 매칭 수정)

## [1.10.4] - 2026-03-26
### Changed
- 미사용 cdn.programgarden.io `_img_url` 제거 (빈값으로 초기화) — 노드 3개 정리
### Dependencies
- programgarden-core ^1.9.7

## [1.10.3] - 2026-03-10
### Added
- FileReaderNode 신규 추가 (community 4번째 노드, data 카테고리)
  - 지원 포맷: PDF(pypdf), TXT, CSV, JSON, MD, DOCX(python-docx), XLSX(openpyxl)
  - PDF 테이블 추출: pdfplumber (extract_tables=True)
  - 복수 파일 일괄 처리, auto-iterate 호환 배열 출력
  - 보안: /app/data/ 경로 제한, max_file_size_mb, 최대 20개
  - is_tool_enabled=True (AIAgentNode 도구로 사용 가능)
- extras 설정: docx, xlsx, pdf-tables, all-parsers
- 테스트 108개 추가 (총 1018개)
### Dependencies
- programgarden-core ^1.9.3
- pypdf >=4.0.0 (기본), python-docx/openpyxl/pdfplumber (extras)

## [1.10.2] - 2026-03-04
### Dependencies
- programgarden-core ^1.9.0 (국내주식 노드 포함)

## [1.10.1] - 2026-03-01
### Changed
- deps: programgarden-core ^1.8.0

## [1.10.0] - 2026-02-27
### Added
- S/R 레벨 플러그인 2종 추가 (65→67 플러그인)
  - TECHNICAL 2개: SupportResistanceLevels(Swing 기반 지지/저항 레벨 감지+클러스터링), LevelTouch(레벨 터치/돌파/역할전환 감지+state 이력 추적)
- 테스트 101개 추가 (총 910개)

### Changed
- deps: programgarden-core ^1.7.0

## [1.9.0] - 2026-02-25
### Added
- 퀀트 전략 플러그인 10종 추가 (55→65 플러그인)
  - TECHNICAL 10개: TimeSeriesMomentum, ConnorsRSI, MFI, CoppockCurve, ElderRay, TurtleBreakout, VolatilityBreakout, SeasonalFilter, TacticalAssetAllocation, MagicFormula
- **FundamentalDataNode**: FMP API 기반 해외주식 재무 데이터 조회 노드 (community/nodes/market/)
  - 4가지 data_type: profile, income_statement, balance_sheet, key_metrics
  - credential 기반 API 키 관리, L-2 rate limit (60초)
- **FearGreedIndexNode**: core에서 community 패키지로 이동
- 테스트 239개 추가 (총 809개)

### Changed
- deps: programgarden-core ^1.6.0

## [1.8.0] - 2026-02-22
### Added
- Tier 1 퀀트 전략 플러그인 7개 추가 (48→55 플러그인)
  - TECHNICAL 5개: ZScore(Z-Score정규화), SqueezeMomentum(BB+KC스퀴즈), MomentumRank(모멘텀순위선별), MarketInternals(시장내부지표), PairTrading(페어트레이딩)
  - POSITION 2개: DynamicStopLoss(ATR동적손절), MaxPositionLimit(포지션한도관리)
- 테스트 81개 추가 (총 570개)

## [1.7.0] - 2026-02-21
### Added
- Phase 6 퀀트 위험관리 플러그인 5개 추가 (43→48 플러그인)
  - POSITION 5개: KellyCriterion(켈리기준), RiskParity(리스크패리티), VarCvarMonitor(VaR/CVaR모니터링), CorrelationGuard(상관관계가드), BetaHedge(베타헷지)
- 테스트 추가 (총 489개)

## [1.6.0] - 2026-02-20
### Added
- Phase 5 커뮤니티 플러그인 9개 추가 (34→43 플러그인)
  - TECHNICAL 6개: RegimeDetection(시장국면탐지), RelativeStrength(상대강도), MultiTimeframeConfirmation(멀티타임프레임), CorrelationAnalysis(상관관계분석), ContangoBackwardation(콘탱고/백워데이션), CalendarSpread(캘린더스프레드)
  - POSITION 3개: DrawdownProtection(드로다운보호), VolatilityPositionSizing(변동성포지션사이징), RollManagement(롤오버관리)
- 테스트 116개 추가 (총 406개)

## [1.5.1] - 2026-02-19
### Changed
- deps: programgarden-core ^1.4.0 의존성 동기화 (OverseasStockFundamentalNode, PER/EPS 추가)

## [1.5.0] - 2026-02-17
### Changed
- deps: programgarden-core ^1.3.0 의존성 동기화 (IfNode, Edge from_port 추가)

## [1.4.0] - 2026-02-15
### Added
- Phase 4 퀀트 플러그인 15개 추가 (19→34 플러그인)
  - TECHNICAL: IchimokuCloud, VWAP, ParabolicSAR, WilliamsR, CCI, Supertrend, KeltnerChannel, TRIX, CMF, Engulfing, HammerShootingStar, Doji, MorningEveningStar
  - POSITION: PartialTakeProfit, TimeBasedExit

## [1.2.0] - 2026-02-15
### Added
- trailing_stop 플러그인: `risk_features` 선언 추가 (`{"hwm"}`)

### Changed
- deps: programgarden-core ^1.2.0 (AI Agent, RiskTracker, Rate Limit 등)

## [1.1.8] - 2026-02-10
### Changed
- deps: programgarden-core 1.1.10 버전으로 업데이트 (translate_schema 번역 범위 수정)

## [1.1.7] - 2026-02-10
### Changed
- deps: programgarden-core 1.1.9 버전으로 업데이트 (i18n 957키 완전 동기화, unified node registry)

## [1.1.6] - 2026-02-09
### Changed
- refactor: `register_external()` → `register_community()` 명칭 변경
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
- feat: programgarden-core 1.1.2 버전 업데이트에 따른 종속성 수정

## [1.1.0] - 2026-02-04
### Changed
- feat: programgarden-core 1.1.0 버전 업데이트에 따른 종속성 수정

## [1.0.3] - 2026-01-30
### Changed
- feat: programgarden-core 1.0.2 버전 업데이트에 따른 종속성 수정

## [1.0.2] - 2026-01-30
### Changed
- feat: programgarden-core 1.0.1 버전 업데이트에 따른 종속성 수정

## [1.0.1] - 2026-01-30

### Added
- 초기 릴리스
- programgarden-core 1.0.1 종속성 설정
