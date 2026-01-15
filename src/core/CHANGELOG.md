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
