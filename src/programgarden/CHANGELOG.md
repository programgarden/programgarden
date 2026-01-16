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
