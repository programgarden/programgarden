## [Unreleased]

## [1.21.0] - 2026-04-18
### Added
- `tests/test_examples_validation.py` (203 pass + 1 xfail + 1 skip):
  - `TestWorkflowStaticValidation` — every bundled `examples/workflows/*.json`
    (67 files) passes `WorkflowExecutor.validate()`.
  - `TestWorkflowDryRunCycle` — `dry_run=True` + mocked `ensure_ls_login`
    runs one cycle per workflow; long-running realtime/bot workflows are
    stopped after 5s and asserted to reach a terminal state.
  - `TestProgrammerExamples` — import-smoke for every script in
    `examples/programmer_example/`.
- `pytest.ini` — `testpaths=tests` so `examples/programmer_example` scripts
  are not collected as test suites.

### Fixed
- `examples/workflows/09-symbol-query-stock.json` — missing
  `paper_trading: false` on the broker node. Overseas-stock brokers reject
  paper mode, so SymbolQueryNode crashed on `None` connection under
  dry_run. Added the flag; the workflow now completes cleanly.

### Removed
- **AIAgentNode semantic tool selection infrastructure** — end-to-end removal:
  - `AIAgentNode.tool_selection` / `tool_top_k` fields deleted (every
    connected tool is always forwarded to the LLM).
  - `AIAgentToolExecutor._build_embedding_index` / `select_tools`
    methods deleted.
  - `fastembed>=0.4.0` dependency removed — also prunes `onnxruntime`,
    `rank-bm25`, `pillow`, `sympy`, `py-rust-stemmers`.
  - `tests/test_vector_tool_selection.py` deleted (19 tests).
  - Vector search on a 73-node / ~dozens-of-tools registry was
    over-engineering; richer node descriptions in core 1.12.0 make direct
    LLM tool selection sufficient.

### Dependencies
- programgarden-core ^1.12.0 (NodeTypeSchema AI metadata)
- programgarden-finance ^1.5.1 (compatibility)
- programgarden-community ^1.13.0 (AI metadata on 4 community nodes)

## [1.20.1] - 2026-04-17
### Fixed
- 해외선물 RealAccountNode `on_position_change` 콜백의 `serialized_positions` 직렬화를 dict에서 list로 통일 (해외주식/국내주식 producer와 동일 포맷)
  - position 기반 ConditionNode 플러그인이 `AttributeError: 'list' object has no attribute 'items'` 로 실패하던 버그 해결
  - `quantity`/`price` 필드를 NewOrderNode 호환 형식으로 추가
- 초기 데이터 debug 로그의 `result.get('positions', {}).items()` → list 순회로 수정 (해외주식/해외선물/국내주식 3곳)
- `_fetch_overseas_stock`의 positions dict-keyed 접근을 list 기반 `position_market_code` 매핑으로 치환 (HistoricalDataNode)
- `tools/job_tools.py` `get_job_state()` snapshot의 positions 기본값 `{}` → `[]`

### Changed
- `binding_validator.py`: `position_data` 타입 검증 엄격화 — `isinstance(v, (dict, list))` → `isinstance(v, list) and all(isinstance(i, dict) for i in v)`
- `examples/dynamic_plugins/` 예제 3종 (simple_stop_loss, simple_profit_target, simple_trailing_stop): positions list 순회로 변경

### Dependencies
- programgarden-core ^1.11.1
- programgarden-community ^1.12.1

## [1.20.0] - 2026-04-16

### Changed
- **경로 결정 로직 단순화** (`_resolve_data_dir`, `get_programgarden_data_path`,
  `_resolve_db_path`): storage_dir > /app/data (mkdir 시도) > ./app/data (권한
  부재 시 폴백) 3단 우선순위. 기존 `/.dockerenv` 체크 + OSError raise 제거 —
  /app/data 가 없는 Docker 컨테이너에서도 크래시 대신 자동 mkdir 또는 로컬
  폴백. storage_dir 전달 시에도 mkdir 자동 생성.

### Fixed (dry_run DB 쓰기 차단)
- `ExecutionContext.init_workflow_position_tracker()` — `is_dry_run` True 시
  트래커 초기화 skip (DB 파일 생성 방지).
- `ExecutionContext.init_risk_tracker()` — 동일하게 dry_run skip.
- `SQLiteNodeExecutor.execute()` — dry_run 모드에서 SELECT 만 허용. INSERT
  /UPDATE/DELETE/UPSERT 쿼리는 시뮬레이션 응답(`{rows:[], affected_count:0,
  last_insert_id:None}`)으로 대체. `execute_query` 모드는 SQL 첫 키워드로,
  `simple` 모드는 `action == "select"` 여부로 판정.

### Docs
- `ProgramGarden.run/run_async`, `WorkflowExecutor.execute` 의 `storage_dir`
  docstring 갱신 — 기본값 설명을 새 로직에 맞게 명시.

## [1.19.0] - 2026-04-14
### Dependencies
- programgarden-core ^1.11.0 — FieldSchema/OutputPort example 확장
- programgarden-finance ^1.5.0 — core 동반 버전업
- programgarden-community ^1.12.0 — TelegramNode 포트 example 노출

### Added (from core 1.11.0)
- `OutputPort.example: Optional[Any]` 필드 — 15개 critical 노드 shape 노출.
- Order/Schedule/Broker/Historical/Condition/Logic/If 노드 FieldSchema `example`
  100% 커버리지 — `get_node_schema` 응답에서 필드별 예시 값 제공.
- Broker 노드 credential_id help_text 에 `<credentials_context>` verbatim 규칙 명시.

### Added (from community 1.12.0)
- `TelegramNode.sent` / `TelegramNode.message_id` 출력 포트 example shape.

### Changed
- 코드 변경 없음. 의존 패키지 버전업에 따른 동반 배포.

## [1.18.0] - 2026-04-13
### Added
- **dry_run 모드**: `pg.run(workflow, context={"dry_run": True})`로 워크플로우 실행 검증 (`ExecutionContext.is_dry_run` property)
  - `ScheduleNode` / `TradingHoursFilterNode`: 1 cycle 후 즉시 종료 (또는 대기 없이 통과)
  - 주문 노드 (`NewOrder` / `ModifyOrder` / `CancelOrder`): LS API 미호출, `{"order_id": "DRYRUN-<uuid>", "status": "simulated", ...}` 반환
  - Realtime 노드 (`RealAccount` / `RealMarketData` / `RealOrderEvent`): WebSocket 미개방, `{"status": "skipped_dry_run"}` 반환
  - Messaging 노드 (TelegramNode 등): no-op, `{"status": "simulated"}` 반환
  - 조회/백테스트 노드: 기존 동작 유지 (실제 API 경로)

## [1.17.0] - 2026-04-09
### Added
- 워크플로우 예제 5개 추가 (63~67번): RSI Divergence, KDJ+Aroon, Heikin-Ashi+Vortex, Hurst Regime, Performance Ratios

### Dependencies
- programgarden-community ^1.11.0 (플러그인 10종 추가)

## [1.16.2] - 2026-04-06
### Dependencies
- programgarden-core ^1.9.9 (expression filter 연산자 매칭 수정)
- programgarden-finance ^1.4.4
- programgarden-community ^1.10.5

## [1.16.1] - 2026-04-02
### Fixed
- `load_dynamic_nodes()`: Pydantic v2 model_fields 기반 type 매칭으로 수정 (getattr → model_fields.get)

### Dependencies
- programgarden-core ^1.9.8

## [1.16.0] - 2026-04-02
### Added
- `WorkflowExecutor.load_dynamic_nodes(dynamic_nodes)`: 코드 문자열로부터 Dynamic_ 노드 스키마 등록 + 클래스 주입을 한 번에 처리
- `WorkflowExecutor.execute()` 자동 감지: definition에 `dynamic_nodes` 키가 있으면 자동으로 `load_dynamic_nodes()` 호출
- 실행서버(pg-worker, 데스크톱 앱) 코드 변경 없이 payload에 `dynamic_nodes` 포함만으로 Dynamic_ 노드 실행 가능

## [1.15.9] - 2026-03-26
### Dependencies
- programgarden-core ^1.9.7, programgarden-community ^1.10.4
- 미사용 cdn.programgarden.io `_img_url` 제거 반영

## [1.15.8] - 2026-03-24
### Added
- validate() 검증 3종 추가 (AI 워크플로우 빌더 대응)
  - _validate_edge_references: 엣지→존재하지 않는 노드 참조 에러
  - _validate_expression_references: {{ nodes.xxx }} 존재하지 않는 노드 참조 에러
  - _validate_credential_references: credential_id 미정의 에러
  - 모든 에러를 한번에 반환 (early return 제거), Available nodes 목록 포함
- context.py notify_node_state에 warnings 파라미터 추가
- hkex_futures_bot 예제 (HKEX 미니선물 모의투자)
- bollinger_reversion_bot 예제 (Bollinger Bands 역추세)

### Changed
- resolver.py 에러 메시지 전체 영어 통일

### Dependencies
- programgarden-core ^1.9.6

## [1.15.7] - 2026-03-24
### Fixed
- HistoricalDataNode: positions를 리스트로 처리 (account에서 list 반환 시 dict TypeError 수정)
- NewOrderNode: quantity/price 타입 캐스팅 추가 (API에서 string 반환 시 int/float 자동 변환)
- NewOrderNode: _get_current_price 미해석 표현식 가드 (`{{ item.xxx }}` → g3101 호출 차단)

### Dependencies
- programgarden-finance ^1.4.3

## [1.15.6] - 2026-03-21
### Changed
- executor.py: _execute_stock() docstring에 GSH(호가) 미구독 사유 상세 기재
  - LS증권 해외주식 API 제약: 개별 호가단계 잔량 미제공, 건수 미제공

### Dependencies
- programgarden-core ^1.9.5, programgarden-finance ^1.4.2

## [1.15.5] - 2026-03-12
### Fixed
- DisplayNode executor 등록 누락 수정: TableDisplayNode 등 6개 display 서브타입이 GenericNodeExecutor로 fallback되던 문제
  - `_init_executors()`에 TableDisplayNode, LineChartNode, MultiLineChartNode, CandlestickChartNode, BarChartNode, SummaryDisplayNode 등록
  - node_type → chart_type 자동 매핑 로직 추가 (DisplayNodeExecutor)
- BrokerNode credential 미주입 시 "Broker connected" → "Broker initialized without credentials" 로그 명확화
### Added
- `cycle_completed` job state 이벤트: 실시간 워크플로우에서 사이클 완료 시 알림
  - `on_job_state_change`에서 running/cycle_completed/completed/failed/cancelled 구분 가능
  - realtime_update, order_event, market_data, schedule_tick 완료 시 발생
  - 초기 main flow 완료 시에도 발생

## [1.15.4] - 2026-03-11
### Fixed
- emit_realtime_update() 리스너 버그 3건 수정
  - `self._listener`(미존재) → `self._listeners` 변수명 수정
  - `extra=data` → `data=data` (LogEvent 스키마 준수)
  - `job_id` 누락 필드 추가 + 전체 리스너 루프 순회
### Added
- 리스너 타입 16개 re-export: `from programgarden import RetryEvent, BaseExecutionListener, ...`
  - NodeState, EdgeState, NodeStateEvent, EdgeStateEvent, LogEvent, JobStateEvent
  - DisplayDataEvent, WorkflowPnLEvent, RiskEvent, LLMStreamEvent, TokenUsageEvent
  - AIToolCallEvent, RestartEvent, RetryEvent, ExecutionListener, BaseExecutionListener
### Dependencies
- programgarden-core: ^1.9.3 → ^1.9.4

## [1.15.3] - 2026-03-10
### Added
- DeepSeek LLM provider executor 매핑 (`llm_deepseek` → deepseek provider)
- FileReaderNode executor 통합 (GenericNodeExecutor fallback)
- FileReaderNode 통합 테스트 18개 (디스패치, 워크플로우 JSON, AIAgentNode tool)
### Dependencies
- programgarden-core: ^1.9.2 → ^1.9.3
- programgarden-community: ^1.10.2 → ^1.10.3

## [1.15.2] - 2026-03-06
### Added
- **국내주식 WorkflowPnL FIFO 추적**: KrStockAccountTracker + SC1 체결 이벤트 연동
  - `_start_korea_stock_tracker`: AccountTracker → notify_workflow_pnl (currency=KRW)
  - `_subscribe_korea_stock_fill_events`: SC1 체결/정정/취소 → FIFO 포지션 추적
  - `_get_korea_stock_tracker_data`: 국내주식 전용 tracker 데이터 추출
- context.py `record_workflow_fill`: product별 currency 동적 결정 (KRW/USD)
- `_calculate_account_pnl`: korea_stock 포지션 분류 추가
### Changed
- 기존 메서드 overseas 접두사 rename (8개)
  - `_start_stock_tracker` → `_start_overseas_stock_tracker` 등
- WorkflowPnLEvent 필드명 overseas/korea 분리 (context.py notify_workflow_pnl)

### Dependencies
- programgarden-core: ^1.9.1 → ^1.9.2

## [1.15.1] - 2026-03-04
### Changed
- **AIAgent 도구 선택**: BM25 키워드 매칭 → FastEmbed 벡터 유사도 검색 전환
  - 임베딩 모델: BAAI/bge-small-en-v1.5 (ONNX, ~80MB)
  - Warm 쿼리 평균 5ms, 정확도 100% (15개 도구 Top-3 기준)
  - fastembed ImportError 시 전체 도구 전달 fallback 유지
- `tool_selection` 기본값: `"all"` → `"semantic"`

### Dependencies
- 추가: `fastembed>=0.4.0`
- 제거: `rank-bm25>=0.2.2`

## [1.15.0] - 2026-03-04
### Added
- **국내주식(KoreaStock) Executor**: 12개 korea_stock 분기 구현
  - BrokerNodeExecutor, AccountNodeExecutor, OpenOrdersNodeExecutor
  - MarketDataNodeExecutor, HistoricalDataNodeExecutor, FundamentalNodeExecutor
  - SymbolQueryNodeExecutor, RealMarketDataNodeExecutor
  - RealAccountNodeExecutor, RealOrderEventNodeExecutor
  - NewOrderNodeExecutor, ModifyOrderNodeExecutor, CancelOrderNodeExecutor
- NodeRunner: 국내주식 `broker_ls_korea_stock` credential 타입 지원
- 테스트 259개 추가 (core 220 + executor 22 + workflow 5 + node_runner 12)

### Fixed
- **실시간 콜백 누수 수정**: 워크플로우 종료 후 WebSocket 콜백 계속 실행되는 문제
  - shutdown flag + 16개 콜백 guard 추가
  - GSC/OVC/S3_/K3_ 구독 해제 순서 최적화
  - SDK 레벨 master_callback 제거 (AS0/TC1-3/SC0)
  - BrokerNode fill subscription cleanup
  - stop/cancel/force_stop 모든 종료 경로 통일

### Changed
- deps: programgarden-core ^1.9.0, programgarden-finance ^1.4.1, programgarden-community ^1.10.2

## [1.14.0] - 2026-03-01
### Added
- **Graceful Restart (C-1)**: 워크플로우 상태 저장/복구 구현
  - CheckpointManager: `checkpoint_meta` + `checkpoint_outputs` 테이블
  - 복구 전략: 일회성=완료 노드 스킵, 실시간=Main Flow 전체 재실행
  - 저장 트리거: stop/pause 즉시, 일회성 노드 완료마다, 실시간 30초 주기
  - 안전장치: 10분 만료, 워크플로우 해시 변경 감지, checkpoint 미존재 거부
  - API: `executor.restore()`, `restore_job()`, `has_checkpoint()`, `get_checkpoint_info()`
  - python_server 통합 64개 테스트

### Fixed
- LLM provider 테스트 api_key assertion을 set_secret 검증으로 수정

### Changed
- executor.py: `domestic_stock` → `korea_stock` 리네임 (stub)
- deps: programgarden-core ^1.8.0, programgarden-finance ^1.4.0, programgarden-community ^1.10.1

## [1.13.0] - 2026-02-27
### Changed
- deps: programgarden-core ^1.7.0, programgarden-community ^1.10.0

## [1.12.0] - 2026-02-25
### Added
- **ExclusionListNodeExecutor**: 거래 제외 종목 노드 실행 로직
  - 수동/동적 종목 합산, symbol 기준 중복 제거, reason 매핑
  - `input_symbols` 필터링 (차집합) 지원
  - `NO_AUTO_ITERATE_NODE_TYPES` 등록 (배열 생성 노드)
- **주문 노드 안전장치**: ExclusionListNode 출력 기반 제외 종목 주문 차단
  - `_check_exclusion_list()`: context에서 ExclusionListNode 출력 자동 조회
  - 제외 종목 주문 시 경고 로그 + 주문 스킵 (에러 아닌 정상 종료)
  - `ignore_exclusion: true` 설정으로 우회 가능
  - 적용 대상: OverseasStockNewOrderNode, OverseasFuturesNewOrderNode

### Fixed
- **SymbolFilterNode**: auto-iterate 버그 수정

### Removed
- executor: VIXDataNode, FearGreedIndexNode 전용 executor 제거 (GenericNodeExecutor fallback 사용)

### Changed
- deps: programgarden-core ^1.6.0, programgarden-finance ^1.3.4, programgarden-community ^1.9.0

## [1.11.1] - 2026-02-24
### Fixed
- **금융 안전성 감사 47건 완료** (CRITICAL 8 + HIGH 21 + MEDIUM 14 + LOW 7)
  - Kill Switch: WorkflowJob.force_stop + WorkflowExecutor.emergency_stop_all
  - 중복주문 방지: C-2 모의투자 자동 전환 제거, C-3 빈 OrderNo 차단
  - AI 비용 보호: C-4 max_total_tokens 한도, H-7 스트리밍 토큰 추정, H-9 비용 계산 경고
  - drawdown 연동: C-6 매수 전 drawdown 임계치 체크
  - API 키 보호: H-8 context._secrets 이동 (connection 출력에서 제거)
  - HWM flush 복구: H-10 연속 실패 시 sync fallback
  - SQLite WAL: H-11 멀티 워크플로우 SQLITE_BUSY 방지
  - 네트워크 복구: H-13 ReconnectHandler 콜백 + 끊김 시간 추적
  - risk_halt 연동: M-10 RiskEvent action_hint + 주문 실행 차단
  - OHLCV 메모리: M-11 콜백 클로저 → node_state 메모리 관리
  - 표현식 DoS 방어: M-9 AST 깊이/지수/range 제한

### Changed
- deps: programgarden-core ^1.5.1, programgarden-finance ^1.3.3

## [1.11.0] - 2026-02-23
### Added
- **외부 시장 데이터 노드 executor 매핑**: CurrencyRateNode, FearGreedIndexNode, VIXDataNode → GenericNodeExecutor
- **통합 테스트 12개**: executor 디스패치 3개 + 워크플로우 통합 9개 (IfNode 분기 포함)

### Changed
- deps: programgarden-core ^1.5.0

## [1.10.0] - 2026-02-22
### Added
- **커뮤니티 플러그인 Tier 1 - 퀀트 전략 7개 추가** (community 1.8.0, 총 55개)
  - TECHNICAL 5개: ZScore, SqueezeMomentum, MomentumRank, MarketInternals, PairTrading
  - POSITION 2개: DynamicStopLoss, MaxPositionLimit

### Changed
- deps: programgarden-community ^1.8.0

## [1.9.1] - 2026-02-21
### Fixed
- **ProgramGarden.run() timeout 제거**: 기본값 60초 → None (무제한)
  - ScheduleNode, 실시간 구독 등 장기 실행 워크플로우가 강제 중단되던 문제 해결
  - timeout을 명시적으로 지정하면 기존처럼 제한 가능 (하위 호환)

## [1.9.0] - 2026-02-21
### Added
- **커뮤니티 플러그인 Phase 6 - 퀀트 위험관리 5개 추가** (community 1.7.0, 총 48개)
  - KellyCriterion(켈리기준), RiskParity(리스크패리티), VarCvarMonitor(VaR/CVaR모니터링)
  - CorrelationGuard(상관관계가드), BetaHedge(베타헷지)

### Changed
- deps: programgarden-community ^1.7.0

## [1.8.0] - 2026-02-20
### Added
- **커뮤니티 플러그인 Phase 5 - 9개 추가** (community 1.6.0, 총 43개)
  - 시장분석: RegimeDetection(시장국면탐지), RelativeStrength(상대강도), CorrelationAnalysis(상관관계분석)
  - 멀티타임프레임: MultiTimeframeConfirmation(멀티타임프레임 확인)
  - 선물전용: ContangoBackwardation(콘탱고/백워데이션), CalendarSpread(캘린더스프레드), RollManagement(롤오버관리)
  - 포지션관리: DrawdownProtection(드로다운보호), VolatilityPositionSizing(변동성포지션사이징)

### Changed
- deps: programgarden-community ^1.6.0

## [1.7.1] - 2026-02-20
### Fixed
- deps: programgarden-finance ^1.3.2 (WebSocket 싱글톤 패턴 적용 - 실시간 세션 충돌 해결)

## [1.7.0] - 2026-02-19
### Added
- **NodeRunner API**: 워크플로우 없이 개별 노드를 단독 실행하는 경량 API
  - `run()`: 노드 타입과 설정만 전달하면 자동으로 credential 주입, LS 로그인, connection 생성
  - `list_node_types()`: 사용 가능한 노드 타입 목록 반환 (실시간/BrokerNode 제외)
  - `get_node_schema()`: 노드 설정 스키마 반환
  - `async with` 패턴 지원, 브로커 세션 재사용
  - `raise_on_error` 옵션 (기본 True)
  - 실시간 WebSocket 노드 실행 차단 (ValueError)

## [1.6.0] - 2026-02-19
### Added
- **OverseasStockFundamentalNode**: 해외주식 종목 펀더멘털 조회 노드
  - g3104 API: PER, EPS, 시가총액, 발행주식수, 52주 고/저가, 업종, 환율 등 16개 필드
  - FundamentalNodeExecutor: g3104 API 호출 및 필드 매핑
  - `is_tool_enabled=True`: AIAgentNode 도구(tool)로 사용 가능
- **MarketDataNode PER/EPS**: g3101 응답의 `perv`/`epsv` → `per`/`eps` 매핑 추가
- **AccountNode 잔고 확장**: 외화예수금, 증거금, 마진콜율 필드 추가

### Changed
- deps: programgarden-core ^1.4.0, programgarden-finance ^1.3.1, programgarden-community ^1.5.1

## [1.5.0] - 2026-02-17
### Added
- **IfNode**: 범용 조건 분기 노드 (12종 연산자, true/false/result 출력)
  - IfNodeExecutor: 조건 평가, upstream 데이터 pass-through
  - BFS 기반 캐스케이딩 스킵: 비활성 브랜치 하위 노드 자동 스킵
  - Edge `from_port` 전파: ResolvedEdge에 from_port 필드 추가

### Changed
- deps: programgarden-core ^1.3.0, programgarden-finance ^1.3.0, programgarden-community ^1.5.0

## [1.4.0] - 2026-02-16
### Added
- **퀀트 전략 플러그인 Phase 4 - 15개 추가** (community 1.4.0, 총 34개)
  - 추세/모멘텀 확장: IchimokuCloud(일목균형표), VWAP(거래량가중평균), ParabolicSAR, WilliamsR, CCI(상품채널지수)
  - 변동성/추세 확장: Supertrend(슈퍼트렌드), KeltnerChannel(켈트너채널), TRIX(삼중지수이동평균), CMF(차이킨자금흐름)
  - 캔들스틱 패턴: Engulfing(장악형), HammerShootingStar(망치/유성형), Doji(도지), MorningEveningStar(샛별/석별형)
  - 포지션 관리 확장: PartialTakeProfit(분할익절), TimeBasedExit(시간기반청산)
- **통합 테스트**: test_phase4_plugins.py (71개 테스트 케이스)

### Changed
- deps: programgarden-community ^1.4.0

## [1.3.0] - 2026-02-16
### Added
- **퀀트 전략 플러그인 5개 추가** (community 1.3.0)
  - GoldenRatio: 피보나치 되돌림 레벨 (23.6%~78.6%) 기반 지지/저항 시그널
  - PivotPoint: 피봇 포인트 (Standard/Fibonacci/Camarilla) S1~S3, R1~R3 레벨
  - MeanReversion: 이평선 대비 z-score 이격도 기반 과매수/과매도
  - BreakoutRetest: 지지/저항선 돌파 후 리테스트 매매
  - ThreeLineStrike: 3연속 동일 방향 캔들 후 반전 패턴 인식
- **auto-iterate 체이닝 테스트** 18개 추가 (test_auto_iterate_chain.py)

### Fixed
- executor auto-iterate input 해석 개선: symbols가 string 배열(merged)이면 value 포트로 폴백
- ExpressionContext row 바인딩: `to_dict()` + 별도 ExpressionContext 생성으로 수정
- plugin context 선택적 전달: `inspect.signature()`로 context 파라미터 유무 확인 후 전달
- items 표현식 deferred 평가: iteration context 없을 때 `{{ item }}` 지연
- items 키 config 평가에서 제외: `{{ row.xxx }}` 조기 평가 방지

### Changed
- deps: programgarden-community ^1.3.0

## [1.2.1] - 2026-02-15
### Fixed
- ConditionNodeExecutor.execute()에 `**kwargs` 누락으로 workflow 인자 전달 시 TypeError 발생하는 버그 수정

### Added
- executor **kwargs 호환성 테스트 추가 (모든 등록 executor가 `**kwargs`를 수용하는지 검증)

## [1.2.0] - 2026-02-15
### Added
- **AI Agent 실행 엔진**: LLM Provider, AIAgentNodeExecutor, Tool 실행, 적응형 다운샘플링
  - LLMModelNodeExecutor: 멀티 프로바이더 (OpenAI, Anthropic, Google 등) litellm 기반
  - AIAgentNodeExecutor: ReAct 루프, 도구 호출, output_schema 검증
  - 프리셋 시스템 4종 (risk_manager, technical_analyst, news_analyst, strategist)
  - on_token_usage, on_ai_tool_call, on_llm_stream 리스너 콜백
- **WorkflowRiskTracker**: Feature-gated 위험관리 데이터 인프라
  - 인메모리 Hot Layer + SQLite Cold Layer (30초 flush) 2-Layer 아키텍처
  - on_risk_event 리스너 콜백
- **Connection Rules 검증**: 실시간 노드 → 주문/AI Agent 직접 연결 차단 (ERROR)
- **Rate Limit Guard**: 런타임 노드 실행 간격/동시 실행 제한
- **서버 API 확장**: connection_rules, rate_limit 노출 + validate 통합

### Fixed
- 워크플로우 stop/cancel 시 리스너 미정리 문제 수정
- LLMModelNode 로그 메시지 개선 (provider/model 중복 표시 수정)

### Changed
- deps: programgarden-core ^1.2.0, community ^1.2.0

## [1.1.11] - 2026-02-10
### Changed
- deps: programgarden-core 1.1.10, finance 1.1.8, community 1.1.8 버전으로 업데이트

## [1.1.10] - 2026-02-10
### Changed
- feat: `list_node_types()`에 동적 노드 통합 쿼리 지원 (`is_dynamic` 플래그, `include_dynamic` 파라미터)
- feat: `get_node_schema()`에 동적 노드 fallback 추가
- feat: `list_categories()`에 동적 노드 카운트 포함
- refactor: `get_required_custom_types()` → `get_required_dynamic_types()` 메서드명 변경
- refactor: python_server에 동적 노드 통합 API 적용
- deps: programgarden-core 1.1.9, finance 1.1.7, community 1.1.7 버전으로 업데이트

## [1.1.8] - 2026-02-07
### Changed
- deps: programgarden-core 1.1.7, finance 1.1.5, community 1.1.5 버전으로 업데이트 (credential type overseas 명칭 변경)

## [1.1.7] - 2026-02-06
### Changed
- refactor: credentials 배열의 `id` → `credential_id` 필드명 통일
  - context.py credential 매칭 로직 수정
  - server.py API 응답 필드명 수정
  - 테스트/예제 코드 일괄 업데이트
- deps: programgarden-core 1.1.6, finance 1.1.4, community 1.1.4

## [1.1.6] - 2026-02-06
### Changed
- deps: programgarden-core 1.1.5 버전으로 업데이트 (StickyNote 모델 추가)

## [1.1.5] - 2026-02-06
### Added
- feat: paper_trading 모드 전환 시 수익률 기록 자동 초기화
  - 모의투자 ↔ 실전투자 전환 시 워크플로우 수익률 데이터 리셋
  - "대회 재참가" 개념으로 모드 변경 시 처음부터 다시 시작

### Changed
- refactor: `broker_metadata` 테이블을 `product+provider` 복합키로 관리
  - 사용자가 변경할 수 없는 시스템 식별자 사용으로 신뢰성 향상
- deps: programgarden-core 1.1.4 버전으로 업데이트

## [1.1.4] - 2026-02-05
### Changed
- deps: programgarden-core 1.1.3 버전으로 업데이트 (config_schema i18n 번역 지원)

## [1.1.3] - 2026-02-05
### Changed
- deps: programgarden-core 1.1.2, programgarden-finance 1.1.1, programgarden-community 1.1.1 버전으로 업데이트

## [1.1.2] - 2026-02-05
### Added
- feat: `registry_tools`에 `locale` 파라미터 추가
  - `list_node_types(category, locale)`: 노드 목록 조회 시 i18n 지원
  - `get_node_schema(node_type, locale)`: 노드 스키마 조회 시 i18n 지원
  - `list_categories(locale)`: 카테고리 목록 조회 시 i18n 지원
  - locale 미전달 시 i18n 키 반환, 전달 시 번역된 값 반환

### Changed
- deps: programgarden-core 1.1.2 버전으로 업데이트

## [1.1.1] - 2026-02-04
### Added
- `execute()` 메서드에 job_id 중복 체크 로직 추가
  - 이미 사용 중인 job_id로 실행 시 `DuplicateJobIdError` 발생
  - 실행 중인 job 덮어쓰기 방지로 안전성 향상

### Changed
- deps: programgarden-core 1.1.1 버전으로 업데이트

## [1.1.0] - 2026-02-04
### Added
- feat: Dynamic Node Injection API 지원
  - `register_dynamic_schemas()`: 스키마 등록
  - `get_required_dynamic_types()`: 필요한 동적 노드 타입 조회
  - `inject_node_classes()`: 노드 클래스 주입
  - `is_dynamic_node_ready()`: 실행 준비 완료 확인
  - `clear_injected_classes()`: 주입된 클래스 초기화

### Changed
- deps: programgarden-core 1.1.0 버전으로 업데이트

## [1.0.3] - 2026-01-30
### Changed
- deps: programgarden-finance 1.0.3, programgarden-community 1.0.3 버전으로 업데이트

## [1.0.2] - 2026-01-30
### Changed
- deps: programgarden-finance 1.0.2, programgarden-community 1.0.2 버전으로 업데이트

## [1.0.1] - 2026-01-30

### Changed
- deps: programgarden-core 1.0.1, programgarden-finance 1.0.1, programgarden-community 1.0.1 버전으로 업데이트

## [2.6.0] - 2026-01-22

### Added
- feat(tools): `sqlite_tools.py` 모듈 추가 (~320줄)
  - `list_database_files()`: programgarden_data/ 폴더의 DB 파일 목록
  - `delete_database_file()`: DB 파일 삭제 (경로 탈출 방지)
  - `list_tables()`: DB의 테이블 목록 조회
  - `list_columns()`: 테이블의 컬럼 정보 조회
  - `create_table()`: 새 테이블 생성
- feat(server): SQLite 동적 API 엔드포인트 추가
  - `DELETE /api/files/{source}/{filename}`: DB 파일 삭제
  - `GET /api/sqlite/{db_name}/tables`: 테이블 목록 조회
  - `GET /api/sqlite/{db_name}/tables/{table}/columns`: 컬럼 목록 조회
  - `POST /api/sqlite/{db_name}/tables`: 테이블 생성
- feat(frontend): SQLiteNode UI 개선
  - creatable_select: `deletable` 옵션 (삭제 버튼 + 확인 다이얼로그)
  - creatable_select/multi_select: `source_api` 동적 옵션 로딩
  - depends_on 필드 변경 시 옵션 자동 재로드
- feat(tests): SQLiteTools 테스트 10개 추가
  - 파일 목록, 삭제, 경로 탈출 방지, 테이블/컬럼 조회, 테이블 생성
- feat(tests): Server SQLite API 테스트 6개 추가
  - 엔드포인트 동작 검증, 경로 탈출 방지, 에러 처리

## [2.5.0] - 2026-01-20

### Added
- feat(executor): `SQLiteNodeExecutor` 구현 (~210줄)
  - 두 가지 모드: `execute_query` (직접 SQL), `simple` (자동 쿼리 생성)
  - 5개 액션: select, insert, update, delete, upsert
  - SQL Injection 방지 (식별자 검증, 파라미터 바인딩)
  - `programgarden_data/` 폴더 자동 생성
- feat(database): `SQLQueryBuilder` 유틸리티 클래스 추가 (database/query_builder.py)
  - `validate_identifier()`: 테이블/컬럼명 검증 (SQL Injection 방지)
  - `build_select()`, `build_insert()`, `build_update()`, `build_delete()`, `build_upsert()`
  - `extract_params_from_where()`: WHERE 절 파라미터 추출
- feat(tests): SQLiteNode 단위 테스트 22개 추가
  - SQLQueryBuilder 14개: 식별자 검증, 각 쿼리 빌드 함수, SQL Injection 방지
  - SQLiteNodeExecutor 8개: 두 모드 및 5개 액션 테스트

### Dependencies
- deps: `aiosqlite ^0.20.0` 추가 (비동기 SQLite 작업)

## [2.4.0] - 2026-01-19

### Removed
- refactor(executor): `PerformanceConditionNodeExecutor` 삭제 (~280줄)
  - 노드 복잡성 감소를 위해 제거
  - 필요시 향후 재추가 예정

## [2.3.0] - 2026-01-16

### Added
- feat(executor): `LogicNodeExecutor` 구현 (~206줄)
  - 8개 연산자 지원: all, any, not, xor, at_least, at_most, exactly, weighted
  - 종목별 교집합 계산 (`evaluate_intersection_for_symbols`)
- feat(executor): `PerformanceConditionNodeExecutor` 구현 (~280줄)
  - 12개 지표: pnl_rate, pnl_amount, mdd, win_rate, sharpe_ratio 등
  - 6개 비교 연산자 지원
- feat(workflows): Condition 카테고리 예제 워크플로우 42개 추가
  - ConditionNode: 01~18 (RSI, MACD, Bollinger, VolumeSpike, ProfitTarget, StopLoss)
  - LogicNode: 19~34 (all, any, not, xor, at_least, at_most, exactly, weighted)
  - PerformanceConditionNode: 35~42 (pnl_rate, mdd, win_rate, sharpe 등)
- feat(frontend): DisplayNode 차트 데이터 SSE 연동 개선

### Changed
- refactor(workflows): Python 워크플로우 파일을 JSON 포맷으로 마이그레이션

## [2.2.0] - 2026-01-16
### Fixed
- fix(executor): SymbolFilterNode NoneType 에러 수정
  - `input_a`, `input_b`가 None일 때 빈 리스트로 처리
  - `extract_symbols()`, `build_symbol_map()` None 체크 추가
- fix(expression): `ExpressionContext.to_dict()` 단일 출력 평탄화 제거
  - `nodes.nodeId.port` 표현식이 항상 정상 작동하도록 수정

### Added
- feat(i18n): SymbolQueryNode 다국어 지원 추가
- feat(workflow): 11.symbol-filter-example.json 예제 추가
- feat(frontend): nodeLabels.ts에 SymbolQueryNode 라벨 추가

## [2.1.0] - 2026-01-15
### Fixed
- fix: SSE 실시간 이벤트 지연 문제 해결 (13초 → 0.5초)
  - `context.py`: 모든 `notify_*` 메서드에 `await asyncio.sleep(0)` 추가
  - `executor.py`: yfinance 호출을 `asyncio.to_thread()`로 감싸 비동기 처리

### Changed
- feat: ScreenerNode 거래소 매핑 추가 (NMS→NASDAQ, NYQ→NYSE 등)
- feat: ScreenerNode sector 정규화 (대소문자, 띄어쓰기 무시)
- feat: 노드 스키마 ENUM 필드를 STRING 타입으로 변경 (expression 바인딩 지원)

## [2.0.0] - 2026-01-06
### Changed
- feat: 노드 기반 DSL 아키텍처로 전면 재설계
- feat: Python 3.12 최소 버전으로 상향
- feat: Poetry 빌드 시스템으로 통합

---

## Legacy Changelog (programgarden v0.x)

## [0.1.28] - 2025-12-06
### Changed
- feat: programgarden-community 0.1.15 버전으로 업데이트

## [0.1.27] - 2025-12-06
### Changed
- feat: programgarden-community 0.1.14 버전으로 업데이트

## [0.1.26] - 2025-12-06
### Changed
- feat: 해외선물 neutral 방향성 조건 타입 추가

## [0.1.25] - 2025-12-05
### Changed
- feat: python 3.10으로 최소 버전 상향

## [0.1.24] - 2025-12-05
### Updated
- programgarden-core 0.1.10 버전으로 업데이트
- programgarden-finance 0.1.11 버전으로 업데이트

## [0.1.23] - 2025-12-05
### Updated
- programgarden-core 0.1.9 버전으로 업데이트
- programgarden-finance 0.1.10 버전으로 업데이트

## [0.1.22] - 2025-11-27
### Updated
- programgarden-core 0.1.8 버전으로 업데이트
- programgarden-finance 0.1.9 버전으로 업데이트
- programgarden-community 0.1.12 버전으로 업데이트

## [0.1.21] - 2025-11-26
### Fixed
- 비동기 종료 시 이벤트 루프 참조 오류 수정

## [0.1.20] - 2025-11-26
### Updated
- programgarden-community 0.1.11 버전으로 업데이트

## [0.1.18] - 2025-11-25
### Fixed
- DSL 퍼포먼스 함수 추가

## [0.1.17] - 2025-11-19
### Updated
- programgarden-finance 0.1.8, programgarden-community 0.1.10 버전으로 업데이트

## [0.1.16] - 2025-11-19
### Fixed
- 보유종목, 미체결 종목은 관심종목 여부와 상관없이 처리하도록 수정

## [0.1.14] - 2025-11-18
### Fixed
- 해외선물 양방향 중복주문 방지 로직 수정

## [0.1.13] - 2025-11-17
### Fixed
- 해외주식 자동매매 예제 코드에 가중치 옵션 누락 수정

## [0.1.12] - 2025-11-15
### update
- 한글 타입 변환에서 thread.lock 에러 수정
- 관심종목 배제되는 에러 수정

## [0.1.11] - 2025-11-07
### update
- 일부 변수의 타입 NotRequired로 변경

## [0.1.10] - 2025-11-06
### update
- Window 운영체제 timezone 에러 수정

## [0.1.9] - 2025-11-06
- 버전 업데이트 및 최근 코드 수정 반영

## [0.1.8] - 2025-11-02
- 버전 업데이트 및 최근 코드 수정 반영
- 기타 버그 수정 및 개선

## [0.1.5] - 2025-10-02
### Added
- 신규매수 주문 기능 추가
- 매도 조건 기능 추가
- 정정, 취소 주문 기능 추가

## [0.1.3] - 2025-09-27
### Fixed
- 매도 조건 및 신규매도 주문 버그 수정
