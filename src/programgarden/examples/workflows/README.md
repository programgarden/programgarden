# ProgramGarden 워크플로우 예제

이 폴더에는 ProgramGarden DSL의 다양한 기능을 테스트하는 워크플로우 예제가 포함되어 있습니다.

## 예제 목록

### 계좌 노드 (Account)
| 번호 | 파일명 | 설명 |
|------|--------|------|
| 01 | account-stock-balance | 해외주식 계좌 잔고 조회 |
| 02 | account-futures-balance | 해외선물 계좌 잔고 조회 |

### 시장 데이터 노드 (Market)
| 번호 | 파일명 | 설명 |
|------|--------|------|
| 03 | market-stock-quote | 해외주식 현재가 조회 |
| 04 | market-futures-quote | 해외선물 현재가 조회 |
| 05 | historical-stock-data | 해외주식 과거 데이터 |
| 06 | historical-futures-data | 해외선물 과거 데이터 |

### 심볼 노드 (Symbol)
| 번호 | 파일명 | 설명 |
|------|--------|------|
| 07 | symbol-watchlist | WatchlistNode + Auto-Iterate |
| 08 | symbol-universe | MarketUniverseNode (DOW30) |
| 09 | symbol-query-stock | 종목 검색 |
| 10 | symbol-filter | SymbolFilterNode 차집합 |

### 조건/로직 노드 (Condition)
| 번호 | 파일명 | 설명 |
|------|--------|------|
| 11 | condition-rsi-filter | RSI 과매도 조건 |
| 12 | condition-macd-chain | MACD 골든크로스 + 메서드 체이닝 |
| 13 | logic-complex | LogicNode AND 복합 조건 |

### 주문 노드 (Order)
| 번호 | 파일명 | 설명 |
|------|--------|------|
| 14 | order-futures-new | 해외선물 신규 주문 |
| 15 | order-futures-modify-cancel | 해외선물 정정/취소 |

### 리스크 관리 노드 (Risk)
| 번호 | 파일명 | 설명 |
|------|--------|------|
| 16 | risk-position-sizing | PositionSizingNode 수량 계산 |
| 17 | risk-portfolio | PortfolioNode 자본 배분 |

### 스케줄/트리거 노드 (Schedule)
| 번호 | 파일명 | 설명 |
|------|--------|------|
| 18 | trigger-schedule | ScheduleNode Cron 표현식 |
| 19 | trigger-trading-hours | TradingHoursFilterNode 거래시간 필터 |

### 데이터 노드 (Data)
| 번호 | 파일명 | 설명 |
|------|--------|------|
| 20 | data-http | HTTPRequestNode 외부 API |
| 21 | data-field-mapping | FieldMappingNode + Auto-Iterate |

### 디스플레이 노드 (Display)
| 번호 | 파일명 | 설명 |
|------|--------|------|
| 22 | display-table | TableDisplayNode 테이블 |
| 23 | display-line-chart | LineChartNode RSI 차트 |
| 24 | display-multi-line | MultiLineChartNode 종목 비교 |
| 25 | display-candlestick | CandlestickChartNode OHLCV |
| 26 | display-bar-chart | BarChartNode 종목별 손익 |
| 27 | display-summary | SummaryDisplayNode 요약 |

### 통합 워크플로우 (Strategy)
| 번호 | 파일명 | 설명 |
|------|--------|------|
| 28 | strategy-rsi-full | RSI 기반 매매 전략 (전체 흐름) |
| 29 | monitor-multi-rsi | 멀티심볼 RSI 모니터링 + 차트 |

## 바인딩 함수 사용 예제

| 함수 | 설명 | 사용 예제 |
|------|------|----------|
| `{{ nodes.X.all() }}` | 전체 배열 | 11, 22 |
| `{{ nodes.X.first() }}` | 첫 번째 아이템 | 15, 21 |
| `{{ nodes.X.filter('condition') }}` | 조건 필터링 | 10, 11, 28 |
| `{{ nodes.X.map('field') }}` | 필드 추출 | 11, 28 |
| `{{ nodes.X.sum('field') }}` | 합계 | 17 |
| `{{ nodes.X.avg('field') }}` | 평균 | 17 |
| `{{ nodes.X.count() }}` | 개수 | 12, 24 |
| `{{ item }}` | 현재 반복 아이템 | 07, 14, 21 |
| `{{ index }}` | 현재 인덱스 | 21 |
| `{{ total }}` | 전체 개수 | 21 |
| `{{ lst.flatten(arr, 'key') }}` | 중첩 배열 평탄화 | 24, 29 |

## 네임스페이스 함수

| 네임스페이스 | 함수 | 사용 예제 |
|-------------|------|----------|
| `date` | `today()`, `ago()`, `later()` | 05, 11, 23 |
| `finance` | `pct_change()`, `discount()` | - |
| `stats` | `mean()`, `median()`, `stdev()` | - |
| `format` | `pct()`, `currency()`, `number()` | - |
| `lst` | `flatten()`, `first()`, `pluck()` | 24, 29 |

## 실행 방법

### 1. 서버 시작
```bash
cd src/programgarden
poetry run python examples/python_server/server.py
```

### 2. 워크플로우 실행
```bash
# cURL로 직접 실행
curl -X POST http://localhost:8766/workflow/execute \
  -H "Content-Type: application/json" \
  -d @examples/workflows/01-account-stock-balance.json
```

### 3. Flutter 앱 실행 (선택)
```bash
cd src/programgarden/examples/workflow_flutter
flutter run -d chrome
```

## 파일 구조

각 예제는 JSON + MD 파일 쌍으로 구성됩니다:

```
workflows/
├── 01-account-stock-balance.json    # 워크플로우 정의
├── 01-account-stock-balance.md      # 상세 설명 문서
├── ...
└── README.md                         # 이 파일
```

## 주의사항

1. **Credential**: 예제의 `credential_id`는 플레이스홀더입니다. 실제 실행 시 유효한 credential로 교체하세요.
2. **장외 시간**: 주문 관련 예제는 장중에만 체결됩니다.
3. **모의투자**: 실제 계좌 연동 전 모의투자로 테스트하세요.
