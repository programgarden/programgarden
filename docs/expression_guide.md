# Expression 가이드

ProgramGarden의 Expression 시스템은 Jinja2 스타일의 `{{ }}` 문법을 사용하여 동적 값을 계산합니다.

## 기본 문법

```python
# 노드 출력 참조
"symbols": "{{ nodes.watchlist.symbols }}"

# 워크플로우 입력 참조
"symbols": "{{ input.symbols }}"

# 산술 연산
"quantity": "{{ balance * 0.1 }}"

# 함수 호출
"start_date": "{{ days_ago(30) }}"

# 조건 표현식
"action": "{{ 'buy' if rsi < 30 else 'hold' }}"
```

> ⚠️ **중요**: `$input.xxx` 문법은 **사용하지 않습니다**. 반드시 `{{ input.xxx }}` 형식을 사용하세요.

## 변수

### `nodes` 변수 (노드 출력 참조)

이전 노드의 출력값을 `nodes.노드ID.필드` 형식으로 참조합니다.

```python
"price": "{{ nodes.marketData.price }}"
"quantity": "{{ nodes.sizing.calculated_quantity }}"
"symbols": "{{ nodes.watchlist.symbols }}"
```

### `input` 변수

워크플로우의 `inputs` 섹션에서 정의된 값을 참조합니다.

```python
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
            "symbols": "{{ input.symbols }}"  # ["AAPL", "NVDA"]
        },
        {
            "id": "rsi",
            "type": "ConditionNode",
            "plugin": "RSI",
            "fields": {
                "period": "{{ input.rsi_period }}"  # 14
            }
        }
    ]
}
```

### `context` 변수

실행 컨텍스트에서 전달된 런타임 파라미터를 참조합니다.

```python
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

### 통계 함수 (statistics 모듈)

| 함수 | 설명 | 예시 |
|------|------|------|
| `mean(list)` | 산술평균 | `{{ mean([1,2,3,4,5]) }}` → `3.0` |
| `avg(list)` | 산술평균 (alias) | `{{ avg(prices) }}` |
| `median(list)` | 중앙값 | `{{ median([1,3,5,7,9]) }}` → `5` |
| `stdev(list)` | 표준편차 | `{{ stdev([1,2,3,4,5]) }}` → `1.58...` |
| `variance(list)` | 분산 | `{{ variance([1,2,3,4,5]) }}` → `2.5` |

### 날짜/시간 함수

| 함수 | 설명 | 예시 |
|------|------|------|
| `today()` | 오늘 날짜 | `{{ today() }}` → `"2025-01-15"` |
| `now()` | 현재 시간 | `{{ now() }}` → `"2025-01-15T10:30:00"` |
| `days_ago(n)` | n일 전 | `{{ days_ago(7) }}` → `"2025-01-08"` |
| `days_later(n)` | n일 후 | `{{ days_later(30) }}` → `"2025-02-14"` |
| `year_start()` | 올해 1월 1일 | `{{ year_start() }}` → `"2025-01-01"` |
| `year_end()` | 올해 12월 31일 | `{{ year_end() }}` → `"2025-12-31"` |
| `month_start()` | 이번 달 1일 | `{{ month_start() }}` → `"2025-01-01"` |

### 금융 계산 함수

| 함수 | 설명 | 예시 |
|------|------|------|
| `pct_change(old, new)` | 변화율 (%) | `{{ pct_change(100, 110) }}` → `10.0` |
| `pct(part, total)` | 비율 (%) | `{{ pct(25, 100) }}` → `25.0` |
| `discount(price, pct)` | 할인가 계산 | `{{ discount(100, 10) }}` → `90.0` |
| `markup(price, pct)` | 인상가 계산 | `{{ markup(100, 10) }}` → `110.0` |
| `annualize(ret, days)` | 연환산 수익률 | `{{ annualize(5, 30) }}` → `연 53.25%` |
| `compound(principal, rate, periods)` | 복리 계산 | `{{ compound(1000, 5, 3) }}` → `1157.63` |

### 리스트 유틸리티

| 함수 | 설명 | 예시 |
|------|------|------|
| `first(list)` | 첫 번째 요소 | `{{ first(symbols) }}` → `"AAPL"` |
| `last(list)` | 마지막 요소 | `{{ last(symbols) }}` → `"NVDA"` |
| `count(list)` | 요소 개수 (len alias) | `{{ count(trades) }}` |

### 포맷팅 함수

| 함수 | 설명 | 예시 |
|------|------|------|
| `format_pct(v, decimals)` | 퍼센트 포맷 | `{{ format_pct(12.345, 1) }}` → `"12.3%"` |
| `format_currency(v, symbol)` | 통화 포맷 | `{{ format_currency(1234.5) }}` → `"$1,234.50"` |
| `format_number(v, decimals)` | 숫자 포맷 | `{{ format_number(1234567.89, 0) }}` → `"1,234,568"` |

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

```python
{
    "inputs": {
        "backtest_months": {
            "type": "integer",
            "default": 6,
            "description": "백테스트 기간 (월)"
        }
    },
    "nodes": [
        {
            "id": "historicalData",
            "type": "HistoricalDataNode",
            "start_date": "{{ days_ago(input.backtest_months * 30) }}",
            "end_date": "{{ today() }}"
        }
    ]
}
```

### 동적 포지션 사이징

```python
{
    "id": "sizing",
    "type": "PositionSizingNode",
    "method": "percent_balance",
    "percent": "{{ min(input.max_position_pct, 100 / len(input.symbols)) }}"
}
```

### 성과 조건 검증

```python
{
    "id": "performanceCheck",
    "type": "PerformanceConditionNode",
    "conditions": {
        "total_return": ">{{ input.min_return }}",
        "max_drawdown": "<{{ input.max_mdd }}",
        "sharpe_ratio": ">{{ input.min_sharpe }}"
    }
}
```

### 알림 메시지 포맷팅

```python
{
    "id": "alert",
    "type": "AlertNode",
    "template": "수익률: {{ format_pct(pnl_rate, 2) }}\n자산: {{ format_currency(equity) }}"
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

```python
# 정의되지 않은 변수
"{{ undefined_variable }}"  # ExpressionError: 정의되지 않은 변수: undefined_variable

# 지원하지 않는 연산
"{{ x @ y }}"  # ExpressionError: 지원하지 않는 연산자

# 0으로 나누기
"{{ 10 / 0 }}"  # ExpressionError: division by zero
```

---

## 마이그레이션 가이드

### `$input.xxx` → `{{ input.xxx }}`

기존의 `$input.xxx` 문법은 더 이상 지원되지 않습니다.

```python
# ❌ 잘못된 예 (지원 안 함)
"symbols": "$input.symbols"

# ✅ 올바른 예
"symbols": "{{ input.symbols }}"
```

### `dynamic:` 접두사 제거

`dynamic:` 접두사는 불필요합니다. 직접 함수를 호출하세요.

```python
# ❌ 이전 방식
"start_date": "dynamic:months_ago($input.backtest_months)"

# ✅ 새 방식
"start_date": "{{ days_ago(input.backtest_months * 30) }}"
```

---

## 참고

- Expression 엔진: [evaluator.py](../src/core/programgarden_core/expression/evaluator.py)
- 실행 컨텍스트: [context.py](../src/programgarden/programgarden/context.py)
