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
