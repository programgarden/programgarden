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
