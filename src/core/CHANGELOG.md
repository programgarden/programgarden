## [Unreleased]

## [1.12.0] - 2026-04-18
### Added
- **NodeTypeSchema AI metadata** — 5 new optional fields (`usage`, `features`,
  `anti_patterns`, `examples`, `node_guide`) feed the workflow-generation AI
  chatbot directly. Each node class exposes them as flat ClassVars
  (`_usage` / `_features` / `_anti_patterns` / `_examples` / `_node_guide`),
  mirroring the existing `_img_url` / `_connection_rules` / `_rate_limit`
  convention. All 73 registered nodes (69 core + 4 community) filled.
  - English-only authoring — no i18n bridge.
  - Every `examples[].workflow_snippet` is a full workflow JSON that passes
    `WorkflowExecutor.validate()` — enforced by
    `test_metadata_workflow_snippets_validate` (146 tests) so snippets serve
    as executable ground truth for downstream consumers.
- `test_node_schema_completeness.py` (624 parametrized tests) — every
  registered node exposes resolved i18n descriptions for top-level / ports /
  config_schema in both ko and en.
- `test_node_schema_ai_fields.py` — 148 assertions (73 shape + 73
  snippet-validate + 2 coverage). `test_metadata_coverage_full` enforces
  strict equality; any new node must ship AI metadata at introduction time.

### Removed
- **AIAgentNode `tool_selection` / `tool_top_k` fields** — simplified so
  every connected tool is always forwarded to the LLM. Description-based
  selection is left to the model.
  - i18n keys `fields.AIAgentNode.tool_selection*` / `tool_top_k*` (ko/en)
    removed alongside the fields.
  - Part of the FastEmbed vector-search rollback — the downstream
    `programgarden` package drops its semantic tool-selection infrastructure
    entirely in 1.21.0.

## [1.11.1] - 2026-04-17
### Changed
- `ConditionNode.positions` field example을 dict 형태에서 list[dict] 형태로 변경 (position_data 컨벤션 통일)

## [1.11.0] - 2026-04-14
### Added
- `OutputPort.example: Optional[Any]` 필드 신설 — 노드 출력 shape 을 LLM/클라이언트에 예시로 노출.
- 15개 critical 노드 출력 포트에 example shape 채움:
  StartNode, OverseasStockBrokerNode(connection), OverseasStockMarketDataNode(value),
  OverseasStockHistoricalDataNode(value), OverseasStockAccountNode(held_symbols/balance/positions),
  BaseOrderNode(result, 모든 Order 노드 상속), WatchlistNode(symbols),
  IfNode(true/false/result), ConditionNode(result), LogicNode(result/passed_symbols),
  ScheduleNode(trigger), TradingHoursFilterNode(passed/blocked),
  SplitNode(item/index/total), AggregateNode(array/value/count).
- FieldSchema `example` 값 채움 — Order/Schedule/Broker/Historical/Condition/Logic/If 노드
  critical 필드 100% 커버리지:
  - `OverseasStockNewOrderNode`/`OverseasFuturesNewOrderNode`: side, order_type, price_type
  - `BaseOrderNode`: rate_limit_interval, rate_limit_action
  - `OverseasStockHistoricalDataNode`/`OverseasFuturesHistoricalDataNode`: adjust
  - `OverseasStockBrokerNode`/`OverseasFuturesBrokerNode`: provider, credential_id, paper_trading
  - `IfNode`: operator
  - `ConditionNode`: plugin
  - `LogicNode`: operator, threshold
  - `ScheduleNode`: enabled, max_duration_hours
  - `TradingHoursFilterNode`: max_wait_hours

### Changed
- broker 노드 credential_id help_text 추가 — LLM 이 `<credentials_context>` 블록의 id 를
  그대로 사용하고 `pending_*` placeholder 환각을 억제하도록 지침 명시.

## [1.10.0] - 2026-04-13
### Added
- `TradingHoursFilterNode`: `context.is_dry_run=True` 시 대기 없이 즉시 통과 (`{"passed": True, "reason": "dry_run_bypass"}`)

## [1.9.9] - 2026-04-06
### Fixed
- `_filter_data()` regex 연산자 매칭 순서 수정: `>=|<=` 를 `>|<` 보다 앞으로 이동 (longest match first)

## [1.9.8] - 2026-04-02
### Added
- `PluginRegistry.register_dynamic()`: 동적 플러그인 등록 메서드 (기존 ID 충돌 방지)

## [1.9.7] - 2026-03-26
### Changed
- 미사용 cdn.programgarden.io `_img_url` 제거 (빈값으로 초기화) — 노드 25개 정리

## [1.9.6] - 2026-03-24
### Added
- NodeStateEvent에 `warnings: Optional[List[str]]` 필드 추가 (후향 호환)

### Changed
- validate_structure() 에러 메시지 전체 영어 통일
  - 중복 노드 ID 에러에 실제 중복 ID 표시
  - 순환 참조, StartNode, 엣지 참조 에러 영문화

## [1.9.5] - 2026-03-21
### Changed
- OverseasStockRealMarketDataNode description 정정: "호가" → "체결 데이터", GSH 미포함 명시
- MARKET_DATA_FULL_FIELDS의 bid_price/ask_price에 "해외주식 실시간 미제공" 표시
- i18n(ko/en) OverseasStockRealMarketDataNode description 정정

## [1.9.4] - 2026-03-11
### Fixed
- RetryEvent를 `programgarden_core.bases.listener`에서 직접 import 가능하도록 수정
  - 기존: `TYPE_CHECKING` 블록 안에서만 import → 런타임 ImportError 발생
  - 수정: 런타임 import로 변경

## [1.9.3] - 2026-03-10
### Added
- DeepSeek LLM provider credential 스키마 추가 (`llm_deepseek`)
- LLMModelNode credential_types에 `llm_deepseek` 추가
- FileReaderNode i18n 번역 키 33개 (ko/en) — 노드명, 필드 설명, 출력 포트

## [1.9.2] - 2026-03-06
### Changed
- WorkflowPnLEvent 필드명 overseas/korea 명확 분리 (v2.0)
  - `workflow_stock_pnl_rate` → `workflow_overseas_stock_pnl_rate`
  - `account_stock_pnl_rate` → `account_overseas_stock_pnl_rate`
  - `workflow_futures_pnl_rate` → `workflow_overseas_futures_pnl_rate`
  - 동일 패턴으로 competition_* 필드도 overseas_ 접두사 적용
### Added
- WorkflowPnLEvent 국내주식(korea_stock) 전용 필드 추가
  - `workflow_korea_stock_pnl_rate/amount`
  - `account_korea_stock_pnl_rate/amount`
  - `competition_workflow_korea_stock_pnl_rate/amount`
  - `competition_account_korea_stock_pnl_rate/amount`

## [1.9.1] - 2026-03-04
### Changed
- AIAgentNode: `tool_selection` 필드 `bm25` → `semantic` 변경, 기본값 `"semantic"`
- AIAgentNode: `tool_top_k` visible_when 조건 `semantic`으로 변경
- i18n: tool_selection/tool_top_k 번역 BM25 → 벡터 검색 업데이트 (ko/en)

## [1.9.0] - 2026-03-04
### Added
- **국내주식(KoreaStock) 노드 13개**: broker 1, account 4, market 5, order 3
  - KoreaStockBrokerNode, KoreaStockAccountNode, KoreaStockOpenOrdersNode
  - KoreaStockMarketDataNode, KoreaStockFundamentalNode, KoreaStockHistoricalDataNode
  - KoreaStockSymbolQueryNode, KoreaStockRealMarketDataNode
  - KoreaStockRealAccountNode, KoreaStockRealOrderEventNode
  - KoreaStockNewOrderNode, KoreaStockModifyOrderNode, KoreaStockCancelOrderNode
- i18n: 국내주식 94키 추가 (ko/en)
- NodeTypeRegistry: 국내주식 13개 노드 등록
- core 노드 수: 55 → 68개 (총 71개 = core 68 + community 3)

## [1.8.0] - 2026-03-01
### Added
- **Graceful Restart (C-1)**: CheckpointManager를 통한 워크플로우 상태 저장/복구
  - `checkpoint_meta` + `checkpoint_outputs` 테이블 (기존 workflow.db에 추가)
  - 복구 전략: 일회성=완료 노드 스킵, 실시간=Main Flow 전체 재실행
  - 안전장치: 10분 만료, 워크플로우 해시 변경 감지
  - RestartEvent 리스너 콜백 + i18n (ko/en)
- 노드 description 58개 VectorDB 검색용 상세 확장 (en/ko)

## [1.7.0] - 2026-02-27
### Added
- i18n: SupportResistanceLevels, LevelTouch 플러그인 번역 키 추가 (ko/en)

## [1.6.0] - 2026-02-25
### Added
- **ExclusionListNode**: 거래 제외 종목 관리 노드 (`market` 카테고리)
  - 수동 입력(`symbols`) + 동적 입력(`dynamic_symbols`) 합산, 중복 제거
  - `input_symbols` 연결 시 차집합 필터링 결과 출력
  - 종목별 제외 사유(`reason`) 관리 + `default_reason` 지원
  - `is_tool_enabled() = True` (AI Agent 도구 사용 가능)
- i18n: ExclusionListNode, FundamentalDataNode 번역 키 추가 (ko/en)

### Changed
- **FearGreedIndexNode**: core → community 패키지로 이동 (core에서 제거)

### Removed
- **VIXDataNode**: Yahoo Finance CDN 차단 위험으로 삭제
  - i18n 키 제거, registry 등록 해제
- core 노드 수: 57 → 55개

## [1.5.1] - 2026-02-24
### Fixed
- **금융 안전성 감사 (47건 중 core 해당분)**
  - ResilienceConfig: retry.enabled=True + max_retries=0 교차 검증 경고
  - FallbackConfig: mode=DEFAULT_VALUE 시 default_value 필수 검증 (model_validator)
  - 주문 노드: retry max_retries 3 이하 강제, 시장가 전환 warning 로그 상향
  - AIAgentNode: max_total_tokens 한도, BM25 도구 선택, output 검증 error 상향, cooldown 스킵 추적
  - 표현식 DoS 방어: AST 깊이 20, 지수 1000, range 100K 제한
  - ScheduleNode: max_duration_hours + count 1000 제한
  - TradingHoursFilterNode: max_wait_hours 타임아웃
  - HTTPRequestNode: 기본 retry.enabled=True, 실시간 연결 ERROR 강화

### Added
- **외부 API fallback provider**: CurrencyRateNode → open.er-api.com, VIXDataNode → query2 Yahoo CDN
- **Rate limit API별 최적화**: CurrencyRate 30초, FearGreed 300초, VIX 120초
- **timeout_seconds 필드**: 3개 외부 API 노드 (기본 30초, 5~120초)
- i18n: timeout_seconds 필드 번역 (ko/en)

## [1.5.0] - 2026-02-23
### Added
- **CurrencyRateNode**: 환율 조회 노드 (`market` 카테고리, credential 불필요)
  - frankfurter.app API 기반, 기본 통화 + 대상 통화 목록 지정
  - KRW 환율 자동 포함, `rates`(배열) + `krw_rate`(숫자) 출력
- **FearGreedIndexNode**: CNN 공포/탐욕 지수 조회 (`market` 카테고리, credential 불필요)
  - CNN dataviz API 기반, 0~100 점수 + 라벨(Extreme Fear~Extreme Greed)
- **VIXDataNode**: VIX 변동성 지수 조회 (`market` 카테고리, credential 불필요)
  - Yahoo Finance API 기반, 현재 VIX + 수준 분류(low/moderate/high/extreme)
  - `include_history` 옵션으로 과거 데이터 조회 가능
- **ExternalAPIError 예외 계층**: RateLimitError, NetworkError, TimeoutError 등 외부 API 전용 예외
- i18n: CurrencyRateNode, FearGreedIndexNode, VIXDataNode 번역 키 추가 (ko/en)

## [1.4.0] - 2026-02-19
### Added
- **OverseasStockFundamentalNode**: 해외주식 종목 펀더멘털 조회 (`market` 카테고리)
  - g3104 API: PER, EPS, 시가총액, 발행주식수, 52주 고/저가, 업종, 환율 등 16개 필드
  - `is_tool_enabled=True`: AIAgentNode 도구(tool)로 사용 가능
- **FUNDAMENTAL_DATA_FIELDS**: 16개 펀더멘털 출력 필드 상수
- **PRICE_DATA_FIELDS 확장**: `per`, `eps` 필드 추가 (MarketDataNode 출력에 포함)
- **AccountNode 잔고 확장**: 외화예수금, 증거금, 마진콜율 필드 추가
- i18n: FundamentalNode, AccountNode 확장 필드 번역 (ko/en)

### Fixed
- LLM provider 정리 및 기존 테스트 실패/에러 수정

## [1.3.0] - 2026-02-17
### Added
- **IfNode**: 범용 조건 분기 노드 (`infra` 카테고리)
  - 12종 비교 연산자: `==`, `!=`, `>`, `>=`, `<`, `<=`, `in`, `not_in`, `contains`, `not_contains`, `is_empty`, `is_not_empty`
  - `true`/`false`/`result` 3개 출력 포트, upstream 데이터 pass-through
  - 문자열↔숫자 타입 자동 변환
- **Edge `from_port`**: 분기 경로 지정을 위한 `Optional[str]` 필드 추가
  - dot notation 지원: `"if1.true"` → `from_port="true"` 자동 파싱
- i18n: IfNode 관련 번역 키 추가 (ko/en)

## [1.2.0] - 2026-02-15
### Added
- **AI Agent 노드**: LLMModelNode + AIAgentNode 2종 (`ai` 카테고리)
  - `ai_model` / `tool` 엣지 타입, 프리셋 4종 (risk_manager, technical_analyst, news_analyst, strategist)
  - text / json / structured 출력 형식, output_schema 기반 Pydantic 검증
  - cooldown_sec 실시간 보호, ThrottleNode 없이 직접 실시간 노드 연결 차단
- **WorkflowRiskTracker**: Feature-gated 위험관리 데이터 인프라
  - 노드/플러그인 `_risk_features` 선언으로 자동 활성화 (hwm, window, events, state)
  - 인메모리 Hot Layer + SQLite Cold Layer (30초 flush) 2-Layer 아키텍처
- **Connection Rules 시스템**: 실시간 노드 → 위험 노드 직접 연결 차단
  - `ConnectionRule`, `ConnectionSeverity`, `RateLimitConfig` 모델 (`connection_rule.py`)
  - `REALTIME_SOURCE_NODE_TYPES`: 6개 실시간 WebSocket 노드 상수
  - `BaseNode._connection_rules` / `_rate_limit` ClassVar 추가
  - `WorkflowResolver._validate_connection_rules()`: 프론트/백엔드 공통 검증
  - 실시간 → 주문 노드: ERROR (차단), 실시간 → AI Agent: ERROR (차단), 실시간 → HTTP: WARNING (경고)
- **BaseNode Rate Limit Guard**: 런타임 최후 방어선
  - 주문 노드: 5초 간격 / 동시 1개, AI Agent: 60초 간격 / 동시 1개, HTTP: 1초 간격 / 동시 3개
  - 사용자 `rate_limit_interval`, `rate_limit_action` 오버라이드 지원
- i18n: `connection_rules.*`, `fields.BaseOrderNode.rate_limit_*`, `enums.rate_limit_action.*` 키 추가 (ko/en)

### Fixed
- AI Agent 프로덕션 버그 3건 수정 및 디버그 코드 정리

## [1.1.10] - 2026-02-10
### Fixed
- fix: `translate_schema()` 포트 display_name, config_schema sub_fields/ui_options 번역 누락 수정
  - `_translate_port()`: description + display_name 모두 번역 (326개 미번역 해소)
  - `_translate_config_schema()`: sub_fields, ui_options 재귀 번역 추가

## [1.1.9] - 2026-02-10
### Changed
- refactor: `NodeTypeRegistry` 명칭 변경 (`register_external` → `register_community`, `is_external` → `is_community` 등)
  - community 노드와 dynamic 노드의 개념 분리를 위해 "external" → "community"로 명칭 통일
- refactor: `DYNAMIC_NODE_PREFIX` 변경 (`Custom_` → `Dynamic_`)
  - DynamicNodeRegistry API 전체와 prefix 네이밍 일관성 통일
- refactor: `DynamicNodeRegistry` docstring "커스텀" → "동적"으로 통일

### Fixed
- fix: i18n fieldNames 번역 키 누락 보완 (ko/en 212키 동기화)
- fix: i18n 번역 키 누락 전면 보완 (ko/en 957키 완전 동기화)
  - 코드 참조 459키 100% 커버리지 달성
  - fields, ports, enums, nodes 등 전 영역 누락 해소

## [1.1.7] - 2026-02-07
### Changed
- refactor: credential type 명칭 변경 (`broker_ls_stock` → `broker_ls_overseas_stock`, `broker_ls_futures` → `broker_ls_overseas_futures`)
  - 해외 상품임을 명확히 하기 위해 `overseas` 접두사 추가
  - `BUILTIN_CREDENTIAL_SCHEMAS` dict key 및 `type_id` 변경
  - `OverseasStockBrokerNode`, `OverseasFuturesBrokerNode`의 `credential_types` 필터 업데이트

## [1.1.6] - 2026-02-06
### Changed
- `CredentialReference.id` → `credential_id` 필드명 변경 (워크플로우 JSON 일관성)
- `Credential.id` → `credential_id` 필드명 변경
- `CredentialStore` 구현체들의 `.id` → `.credential_id` 참조 수정

## [1.1.5] - 2026-02-06
### Added
- `StickyNote`, `NotePosition` 모델 추가 — 워크플로우 캔버스 메모 기능
- `WorkflowDefinition.notes` 필드 추가 (노드 시스템과 분리된 비실행 주석)

### Fixed
- `PluginCategory.STRATEGY_CONDITION` → `TECHNICAL` 테스트 수정

## [1.1.4] - 2026-02-06
### Added
- `WorkflowPnLEvent`에 `paper_trading` 필드 추가 (모의/실전 투자 구분)

## [1.1.3] - 2026-02-05
### Added
- `config_schema` i18n 번역 지원 추가
  - `translate_schema()`에서 config_schema 내부 필드 자동 번역
  - `_translate_config_schema()` 함수 구현 (enum_labels, description, placeholder, help_text)
  - 노드 파일의 하드코딩된 enum_labels를 i18n 키 형식으로 변경
  - ko.json, en.json에 62개의 새로운 enum 번역 키 추가
  - 대상 노드: BrokerNode, MarketUniverseNode, ScreenerNode, SymbolFilterNode, SymbolQueryNode, OrderNode

## [1.1.2] - 2026-02-05
### Added
- feat: `NodeTypeSchema`에 `display_name` 필드 추가
  - 기본값: `i18n:nodes.{NodeType}.name` (i18n 키)
  - locale 파라미터 전달 시 번역된 값 반환
  - 외부 앱에서 자체 i18n 시스템 사용 가능

## [1.1.1] - 2026-02-04
### Added
- `DuplicateJobIdError` 예외 클래스 추가 - 중복 job_id 사용 시 발생

## [1.1.0] - 2026-02-04
### Added
- feat: Dynamic Node Injection 시스템 구현
  - `dynamic_node_registry.py`: 동적 노드 스키마/클래스 관리
  - 외부 사용자가 런타임에 동적 노드 주입 가능
  - `Dynamic_` prefix 네이밍 규칙 적용
- feat: Retry/Fallback 공통 시스템 구현
  - `ResilienceConfig`, `RetryConfig`, `FallbackConfig` 모델 추가
  - 외부 API 호출 노드에서 재시도 및 실패 처리 설정 지원

### Changed
- refactor: HTTPRequestNode resilience UI 단순화

### Fixed
- fix: RetryEvent import 오류 수정

## [1.0.2] - 2026-01-30
### Fixed
- plugin 타입 수정

## [1.0.1] - 2026-01-30

### Changed
- refactor(nodes): 노드 스키마 단순화 - `widget_schema`를 `config_schema`로 통합
- refactor(models): Credential data 구조를 list 형태로 통일
- refactor: 데이터 저장 경로 변경 및 Flutter 예제 제거

## [2.7.0] - 2026-01-22

### Changed
- feat(nodes): `SQLiteNode` UI 개선 스키마 (data.py)
  - `db_name`: `deletable`, `delete_confirm` 옵션 추가 (파일 삭제 기능)
  - `table`: `creatable_select` + 동적 API (`source_api`, `depends_on`)
  - `columns`: `multi_select` + 동적 API (테이블 의존)
  - `where_clause`: 상세 설명 (`where_clause_detailed`)
- feat(i18n): SQLiteNode UI 번역 추가 (ko.json, en.json)
  - `ui.create_new_table`, `ui.confirm_delete_database` 등 6개 키
  - `fields.SQLiteNode.where_clause_detailed` 상세 예시 포함

## [2.6.0] - 2026-01-20

### Added
- feat(bases): `BaseStorageNode` 베이스 클래스 추가 (bases/storage.py)
  - 모든 저장소 노드의 공통 입출력 포트 (trigger, rows, affected_count)
- feat(bases): `BaseSQLNode` 베이스 클래스 추가 (bases/sql.py)
  - SQL 데이터베이스 노드의 공통 스키마 (operation, query, parameters, action, table 등)
- feat(models): `UIComponent.CREATABLE_SELECT` 추가 (field_binding.py)
  - 기존 목록에서 선택하거나 새로 생성 가능한 드롭다운

### Changed
- refactor(nodes): `SQLiteNode` 스키마 완전 재설계 (data.py)
  - 기존 필드 제거: key_fields, save_fields, aggregations, sync_interval_ms, sync_on_change_count
  - 새 필드 추가: db_name, operation, query, parameters, table, action, columns, where_clause, values, on_conflict
  - 두 가지 모드 지원: `execute_query` (직접 쿼리), `simple` (GUI 기반 CRUD)
  - 5개 액션: select, insert, update, delete, upsert
- feat(i18n): SQLiteNode 새 스키마 번역 추가 (ko.json, en.json)
  - 노드명: "단순 DB" / "Simple DB"
  - 모든 필드/enum 레이블 다국어 지원

## [2.5.0] - 2026-01-19

### Removed
- refactor(nodes): `PerformanceConditionNode` 삭제
  - 노드 복잡성 감소를 위해 제거
  - 필요시 향후 재추가 예정
  - 익절/손절 조건은 ConditionNode + ProfitTarget/StopLoss 플러그인으로 대체
- refactor(i18n): PerformanceConditionNode 관련 번역 키 제거

## [2.4.0] - 2026-01-16

### Added
- feat(nodes): `LogicNode` 스키마 구현 (condition.py)
  - 8개 연산자: all, any, not, xor, at_least, at_most, exactly, weighted
  - conditions, threshold, weights 필드 지원
- feat(nodes): `PerformanceConditionNode` 스키마 구현 (condition.py)
  - 12개 지표: pnl_rate, mdd, win_rate, sharpe_ratio, profit_factor 등
  - 6개 비교 연산자: gt, lt, gte, lte, eq, ne
- feat(i18n): LogicNode, PerformanceConditionNode 다국어 지원 (ko.json, en.json)
- feat(nodes): DisplayNode에 chart_data 출력 포트 추가

### Changed
- refactor(nodes): PerformanceConditionNode를 backtest.py에서 condition.py로 이전

## [2.3.0] - 2026-01-16
### Fixed
- fix(expression): `ExpressionContext.to_dict()` 수정
  - 단일 출력 노드도 dict 형식 유지 (평탄화 제거)
  - `{{ nodes.watchlist.symbols }}` 표현식 정상 작동

### Added
- feat(i18n): SymbolQueryNode 번역 키 추가
  - ko: "전체 종목 조회"
  - en: "All Symbols"

## [2.2.0] - 2026-01-15
### Changed
- feat(nodes): ScreenerNode 필드 구조 변경 (filters 객체 → 개별 필드)
  - `market_cap_min`, `market_cap_max`, `volume_min`, `sector`, `exchange`, `max_results`
- feat(nodes): ENUM 타입 필드들을 STRING 타입으로 변경 (expression 바인딩 지원)
  - `HistoricalDataNode.interval`, `ScheduleNode.mode` 등

## [2.1.0] - 2026-01-13
### Changed
- feat(nodes): 브로커 연결(connection) 필드 표준화 - 모든 노드에서 명시적 바인딩 필수
  - `RealMarketDataNode`, `RealAccountNode`, `RealOrderEventNode` (realtime.py)
  - `MarketDataNode` (data.py)
  - `WatchlistNode`, `MarketUniverseNode`, `ScreenerNode` (symbol.py)
  - `ExchangeStatusNode` (trigger.py)
- feat(nodes): `WatchlistNode`의 InputPort 이름 변경 (`broker` → `connection`)
- feat(nodes): 모든 connection InputPort를 `required=True`로 변경

### Removed
- remove(nodes): `WatchlistNode`의 `product` 필드 제거 (connection에서 자동 감지)

## [2.0.0] - 2026-01-06
### Changed
- feat: 노드 기반 DSL 핵심 타입으로 전면 재설계
- feat: Python 3.12 최소 버전으로 상향
- feat: Poetry 빌드 시스템으로 통합

---

## Legacy Changelog (programgarden-core v0.x)

## [0.1.12] - 2025-12-06
### Changed
- feat: 해외선물 데이터 일부 수정

## [0.1.11] - 2025-12-05
### Changed
- feat: python 3.10으로 최소 버전 상향

## [0.1.10] - 2025-12-05
### Added
- feat: 주문 정정,취소 타입 코드 튜닝

## [0.1.9] - 2025-12-05
### Added
- feat: import 일부 수정

## [0.1.8] - 2025-11-27
### Changed
- build: Poetry 빌드 시스템 설정 업데이트

##  [0.1.7] - 2025-11-25
### Added
- feat: 성능 점유율 퍼포먼스 추가

## [0.1.6] - 2025-11-15
### Fixed
- fix: deepcopy가 읽지 못하는 객체 문제 해결

## [0.1.5] - 2025-11-06
### Changed
- type: Optional 타입들 일부는 NotRequired로 변경

## [0.1.4] - 2025-11-06
### Changed
- build: Poetry 빌드 시스템 설정 업데이트

## [0.1.3] - 2025-11-02
### Added
- docs: 코어 `README.md` 추가

## [0.1.2] - 2025-10-02
- 신규매수와 신규매도 통합, 정정매수와 정정매도 통합, 취소매수와 취소매도 통합하여 코드 튜닝

## [0.1.1] - 2025-09-27
### Added
- 주문 타입 세분화
