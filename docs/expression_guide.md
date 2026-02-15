# Expression 가이드

ProgramGarden의 Expression 시스템은 Jinja2 스타일의 `{{ }}` 문법을 사용하여 동적 값을 계산합니다.

## 기본 문법

```json
"symbols": "{{ nodes.watchlist.symbols }}"

"symbols": "{{ input.symbols }}"

"quantity": "{{ balance * 0.1 }}"

"start_date": "{{ date.ago(30) }}"

"action": "{{ 'buy' if rsi < 30 else 'hold' }}"
```

| 표현식 | 설명 |
|--------|------|
| `{{ nodes.노드ID.필드 }}` | 이전 노드의 출력값 참조 |
| `{{ input.이름 }}` | 워크플로우 입력 파라미터 참조 |
| `{{ 산술연산 }}` | 덧셈, 뺄셈, 곱셈, 나눗셈 |
| `{{ 네임스페이스.함수(인자) }}` | 네임스페이스 함수 호출 (date., finance., stats., format., lst.) |
| `{{ 조건 if 참 else 거짓 }}` | 조건 표현식 |

> **주의**: `$input.xxx` 문법은 **사용하지 않습니다**. 반드시 `{{ input.xxx }}` 형식을 사용하세요.

## 변수

### `nodes` 변수 (노드 출력 참조)

이전 노드의 출력값을 `nodes.노드ID.필드` 형식으로 참조합니다.

```json
"price": "{{ nodes.marketData.price }}"
"quantity": "{{ nodes.sizing.calculated_quantity }}"
"symbols": "{{ nodes.watchlist.symbols }}"
```

### `input` 변수

워크플로우의 `inputs` 섹션에서 정의된 값을 참조합니다.

```json
{
  "inputs": {
    "symbols": {
      "type": "symbol_list",
      "default": ["AAPL", "NVDA"],
      "description": "대상 종목"
    },
    "rsi_period": {
      "type": "integer",
      "default": 14,
      "description": "RSI 기간"
    }
  },
  "nodes": [
    {
      "id": "watchlist",
      "type": "WatchlistNode",
      "symbols": "{{ input.symbols }}"
    },
    {
      "id": "rsi",
      "type": "ConditionNode",
      "plugin": "RSI",
      "fields": {
        "period": "{{ input.rsi_period }}"
      }
    }
  ]
}
```

### `context` 변수

실행 컨텍스트에서 전달된 런타임 파라미터를 참조합니다.

```json
"balance": "{{ context.available_balance }}"
```

### 예약어 (노드 ID로 사용 불가)

다음 이름은 **노드 ID로 사용할 수 없습니다**:
- `nodes` - 노드 출력 참조용
- `input` - 워크플로우 입력 참조용  
- `context` - 런타임 컨텍스트 참조용

---

## 내장 함수 레퍼런스

### 타입 변환

| 함수 | 설명 | 예시 |
|------|------|------|
| `bool(x)` | 불리언 변환 | `{{ bool(value) }}` |
| `int(x)` | 정수 변환 | `{{ int(price) }}` |
| `float(x)` | 실수 변환 | `{{ float("3.14") }}` |
| `str(x)` | 문자열 변환 | `{{ str(quantity) }}` |
| `list(x)` | 리스트 변환 | `{{ list(range(5)) }}` |
| `dict()` | 딕셔너리 생성 | `{{ dict() }}` |
| `tuple(x)` | 튜플 변환 | `{{ tuple(items) }}` |

### 기본 수학 함수

| 함수 | 설명 | 예시 |
|------|------|------|
| `abs(x)` | 절대값 | `{{ abs(-5) }}` → `5` |
| `min(a, b, ...)` | 최솟값 | `{{ min(10, 5, 8) }}` → `5` |
| `max(a, b, ...)` | 최댓값 | `{{ max(10, 5, 8) }}` → `10` |
| `sum(list)` | 합계 | `{{ sum([1, 2, 3]) }}` → `6` |
| `pow(x, y)` | 거듭제곱 | `{{ pow(2, 3) }}` → `8` |
| `round(x, n)` | 반올림 | `{{ round(3.14159, 2) }}` → `3.14` |
| `len(x)` | 길이 | `{{ len(symbols) }}` |
| `range(n)` | 범위 생성 | `{{ list(range(5)) }}` → `[0,1,2,3,4]` |
| `sorted(list)` | 정렬 | `{{ sorted([3,1,2]) }}` → `[1,2,3]` |
| `all(list)` | 모두 참 | `{{ all([True, True]) }}` → `True` |
| `any(list)` | 하나라도 참 | `{{ any([False, True]) }}` → `True` |

### 고급 수학 함수 (math 모듈)

| 함수 | 설명 | 예시 |
|------|------|------|
| `sqrt(x)` | 제곱근 | `{{ sqrt(16) }}` → `4.0` |
| `log(x)` | 자연로그 | `{{ log(e) }}` → `1.0` |
| `log10(x)` | 상용로그 | `{{ log10(100) }}` → `2.0` |
| `exp(x)` | e^x | `{{ exp(1) }}` → `2.718...` |
| `ceil(x)` | 올림 | `{{ ceil(3.2) }}` → `4` |
| `floor(x)` | 내림 | `{{ floor(3.8) }}` → `3` |
| `pi` | 원주율 (상수) | `{{ pi }}` → `3.14159...` |
| `e` | 자연상수 (상수) | `{{ e }}` → `2.71828...` |

### 통계 함수 (`stats` 네임스페이스)

| 함수 | 설명 | 예시 |
|------|------|------|
| `stats.mean(list)` | 산술평균 | `{{ stats.mean([1,2,3,4,5]) }}` → `3.0` |
| `stats.avg(list)` | 산술평균 (alias) | `{{ stats.avg(prices) }}` |
| `stats.median(list)` | 중앙값 | `{{ stats.median([1,3,5,7,9]) }}` → `5` |
| `stats.stdev(list)` | 표준편차 | `{{ stats.stdev([1,2,3,4,5]) }}` → `1.58...` |
| `stats.variance(list)` | 분산 | `{{ stats.variance([1,2,3,4,5]) }}` → `2.5` |

### 날짜/시간 함수 (`date` 네임스페이스)

| 함수 | 설명 | 예시 |
|------|------|------|
| `date.today()` | 오늘 날짜 | `{{ date.today() }}` → `"2025-01-15"` |
| `date.now()` | 현재 시간 | `{{ date.now() }}` → `"2025-01-15T10:30:00"` |
| `date.ago(n)` | n일 전 | `{{ date.ago(7) }}` → `"2025-01-08"` |
| `date.later(n)` | n일 후 | `{{ date.later(30) }}` → `"2025-02-14"` |
| `date.year_start()` | 올해 1월 1일 | `{{ date.year_start() }}` → `"2025-01-01"` |
| `date.year_end()` | 올해 12월 31일 | `{{ date.year_end() }}` → `"2025-12-31"` |
| `date.month_start()` | 이번 달 1일 | `{{ date.month_start() }}` → `"2025-01-01"` |

> **팁**: `format` 파라미터를 지정하면 출력 형식을 변경할 수 있습니다. 예: `{{ date.ago(30, format='yyyymmdd') }}` → `"20250101"`

### 금융 계산 함수 (`finance` 네임스페이스)

| 함수 | 설명 | 예시 |
|------|------|------|
| `finance.pct_change(old, new)` | 변화율 (%) | `{{ finance.pct_change(100, 110) }}` → `10.0` |
| `finance.pct(part, total)` | 비율 (%) | `{{ finance.pct(25, 100) }}` → `25.0` |
| `finance.discount(price, pct)` | 할인가 계산 | `{{ finance.discount(100, 10) }}` → `90.0` |
| `finance.markup(price, pct)` | 인상가 계산 | `{{ finance.markup(100, 10) }}` → `110.0` |
| `finance.annualize(ret, days)` | 연환산 수익률 | `{{ finance.annualize(5, 30) }}` → `연 53.25%` |
| `finance.compound(principal, rate, periods)` | 복리 계산 | `{{ finance.compound(1000, 5, 3) }}` → `1157.63` |

### 리스트 유틸리티 (`lst` 네임스페이스)

| 함수 | 설명 | 예시 |
|------|------|------|
| `lst.first(list)` | 첫 번째 요소 | `{{ lst.first(symbols) }}` → `"AAPL"` |
| `lst.last(list)` | 마지막 요소 | `{{ lst.last(symbols) }}` → `"NVDA"` |
| `lst.count(list)` | 요소 개수 (len alias) | `{{ lst.count(trades) }}` |
| `lst.pluck(list, path)` | 배열에서 특정 경로 값 추출 | `{{ lst.pluck(items, "name") }}` → `["AAPL", "TSLA"]` |
| `lst.flatten(list, key)` | 중첩 배열 평탄화 (부모 필드 유지) | 아래 예시 참조 |

#### pluck vs flatten

입력 데이터 예시:
```json
[
  {"symbol": "AAPL", "time_series": [{"date": "20251224", "rsi": 33.5}]},
  {"symbol": "TSLA", "time_series": [{"date": "20251224", "rsi": 62.1}]}
]
```

| 함수 | 결과 | 설명 |
|------|------|------|
| `{{ lst.pluck(values, "symbol") }}` | `["AAPL", "TSLA"]` | 특정 키만 추출 |
| `{{ lst.flatten(values, "time_series") }}` | `[{"symbol": "AAPL", "date": "20251224", "rsi": 33.5}, ...]` | 부모 필드 유지하며 평탄화 |

> **팁**: `lst.flatten`은 차트 노드에 데이터를 전달할 때 유용합니다. 종목별 시계열 데이터를 하나의 배열로 합칩니다.

#### 다중 중첩 경로 (pluck 전용)

점 표기법으로 깊은 경로에 접근할 수 있습니다:

```
{{ lst.pluck(positions, "details.sector") }}   →   ["Tech", "Auto", "Finance"]
```

### 포맷팅 함수 (`format` 네임스페이스)

| 함수 | 설명 | 예시 |
|------|------|------|
| `format.pct(v, decimals)` | 퍼센트 포맷 | `{{ format.pct(12.345, 1) }}` → `"12.3%"` |
| `format.currency(v, symbol)` | 통화 포맷 | `{{ format.currency(1234.5) }}` → `"$1,234.50"` |
| `format.number(v, decimals)` | 숫자 포맷 | `{{ format.number(1234567.89, 0) }}` → `"1,234,568"` |

### 상수

| 상수 | 값 |
|------|------|
| `True` | `True` |
| `False` | `False` |
| `None` | `None` |
| `pi` | `3.14159...` |
| `e` | `2.71828...` |

---

## 실전 예제

### 백테스트 날짜 범위

```json
{
  "id": "historicalData",
  "type": "OverseasStockHistoricalDataNode",
  "start_date": "{{ date.ago(input.backtest_months * 30) }}",
  "end_date": "{{ date.today() }}"
}
```

### 동적 포지션 사이징

```json
{
  "id": "sizing",
  "type": "PositionSizingNode",
  "method": "percent_balance",
  "percent": "{{ min(input.max_position_pct, 100 / len(input.symbols)) }}"
}
```

### 포맷팅 활용

```json
{
  "id": "summary",
  "type": "SummaryDisplayNode",
  "title": "포트폴리오 현황",
  "items": [
    {"label": "수익률", "value": "{{ format.pct(nodes.account.pnl_rate, 2) }}"},
    {"label": "총 자산", "value": "{{ format.currency(nodes.account.total_eval) }}"}
  ]
}
```

---

## 지원되지 않는 기능

보안상 다음 기능은 **사용할 수 없습니다**:

- ❌ `import` 문
- ❌ `exec()`, `eval()` 함수
- ❌ 파일 I/O (`open()`, `read()`, `write()`)
- ❌ 네트워크 접근
- ❌ 시스템 명령어 실행
- ❌ 클래스 정의
- ❌ 함수 정의

---

## 오류 처리

표현식 평가 중 오류 발생 시 `ExpressionError`가 발생합니다:

| 표현식 | 오류 |
|--------|------|
| `{{ undefined_variable }}` | 정의되지 않은 변수 |
| `{{ x @ y }}` | 지원하지 않는 연산자 |
| `{{ 10 / 0 }}` | 0으로 나누기 |

> **주의**: 표현식 오류가 발생하면 해당 노드의 실행이 중단됩니다. 노드 ID와 필드 이름을 확인하세요.

