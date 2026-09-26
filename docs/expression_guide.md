# Expression 가이드

워크플로우 JSON의 필드 값에 `{{ ... }}` 를 쓰면 실행 시점에 동적으로 계산됩니다.

> **중요**: `{{ }}` 안은 **Jinja2 가 아니라** 파이썬 `eval` 식의 아주 작은 부분집합입니다.
> Jinja 의 파이프 필터(`| length`), `~` 문자열 이어붙이기, `{% if %}`/`{% for %}` 블록은
> **모두 동작하지 않습니다.** 아래 표에 있는 변수·함수만 쓸 수 있습니다.
> 기계가 읽는 정본 레퍼런스는 `programgarden_core.expression.expression_reference()` 이며,
> 이 문서는 그것을 사람이 읽기 쉽게 풀어 쓴 것입니다.

---

## 1. 두 가지 계산 방식 (전체 vs 삽입)

| 값 | 결과 |
|----|------|
| 값 전체가 **딱 하나의** `{{ 식 }}` | 식의 **타입 그대로** 반환 (리스트/딕셔너리/숫자/불리언/None) |
| 텍스트 안에 `{{ 식 }}` 가 섞여 있음 | 각 식을 `str(결과)` 로 바꿔 **문자열로 치환** |

```json
"symbols": "{{ nodes.watchlist.symbols }}"          // 리스트 그대로
"title":   "가격: {{ nodes.md.price }} 원"           // "가격: 185.5 원" (문자열)
```

> **함정**: 앞뒤 텍스트 없이 식 두 개를 붙이면(`{{ a }}-{{ b }}`) 하나의 식으로 잘못 파싱되어
> 구문 오류가 납니다. `가격 {{ a }} / {{ b }}` 처럼 사이에 텍스트를 두거나, 한 식으로 합치세요
> (`{{ str(a) + '-' + str(b) }}`).

---

## 2. 쓸 수 있는 변수(루트)

**아래 이름만** 정의돼 있습니다. 그 밖의 맨이름(`balance`, `rsi`, `price`, `symbols`,
그리고 `nodes.` 를 붙이지 않은 노드 ID)은 전부 **`정의되지 않은 변수` 오류**입니다.

| 루트 | 설명 | 예시 |
|------|------|------|
| `nodes.<id>.<port>` | 이전 노드의 출력 포트 값 | `{{ nodes.account.balance.orderable_amount }}` |
| `input.<name>` | 워크플로우 `inputs` 값(기본값+사용자 입력 병합) | `{{ input.rsi_period }}` |
| `context.<key>` | 실행 시 전달된 런타임 파라미터 딕셔너리 | `{{ context.mode }}` |
| `item` | 자동 반복/Split 브랜치의 현재 요소 (**반복 중에만** 존재) | `{{ item.symbol }}` |
| `index` | 0부터 시작하는 반복 인덱스 (**반복 밖에서는 항상 0**) | `{{ index }}` |
| `total` | 전체 아이템 개수 (반복 밖에서는 0) | `{{ total }}` |
| `row.<field>` | **ConditionNode/BacktestEngineNode 의 `items.extract` 안에서만** | `{{ row.rsi < 30 }}` |

> - `{{ nodeId.port }}` 처럼 `nodes.` 를 **빼면 안 됩니다** — `nodeId` 는 변수로 정의돼 있지 않아
>   오류입니다. 항상 `nodes.<id>` 로 씁니다.
> - `item` 은 반복 밖에서 쓰면 오류(`정의되지 않은 변수: item`)입니다. 반면 `index`/`total` 은
>   반복 밖에서도 오류 없이 `0` 입니다.
> - `context.available_balance` 같은 값은 **엔진이 채우지 않습니다.** 잔고는
>   `nodes.<account>.balance...` 로 계좌 노드에서 읽으세요.
> - `current_symbol`/`current_index` 는 레거시 변수입니다. 새 워크플로우는 `item` 을 쓰세요.

### 노드 ID 규칙

`nodes.<id>` 의 점 접근은 `<id>` 가 **올바른 파이썬 식별자**여야 합니다.

- 하이픈은 뺄셈으로 해석됩니다 — `nodes.if-balance.x` 는 깨집니다.
- 파이썬 예약어(`if`, `in`, `for`, `is`, `and`, `or`, `not`, `class`, `return` …)는 구문 오류입니다.
  `{{ nodes.if.result }}` 는 **오류**입니다.

이런 ID 는 **대괄호 형태**로만 접근할 수 있습니다(엔진이 정적 검증하지는 않습니다):

```
{{ nodes['if'].result }}          // OK
{{ nodes['my-node'].data }}       // OK (하이픈 ID)
```

가급적 노드 ID 를 `snake_case`/`camelCase`(예: `if_balance`, `ifBalance`)로 지어 이 문제를 피하세요.

---

## 3. 노드 출력 다루기 (NodeOutputProxy)

`nodes.<id>` 와 리스트형 출력 포트는 **NodeOutputProxy** 로 감싸져 체이닝 메서드를 제공합니다.

- 맨 `{{ nodes.<id> }}` 는 **리스트**로 풀립니다: `positions, symbols, values, data, items, array, results`
  중 첫 번째 리스트형 키, 없으면 출력 딕셔너리를 `[dict]`(1개짜리 리스트)로 감쌉니다.

### 체이닝 메서드 (이게 전부입니다)

| 메서드 | 뜻 | 예시 |
|--------|-----|------|
| `.all()` | 전체 배열 | `{{ nodes.account.positions.all() }}` |
| `.first()` | 첫 요소(없으면 None) | `{{ nodes.account.positions.first().symbol }}` |
| `.last()` | 마지막 요소 | `{{ nodes.account.positions.last() }}` |
| `.count()` | 개수(int) | `{{ nodes.account.positions.count() }}` |
| `.filter('필드 연산 값')` | 조건 필터 | `{{ nodes.account.positions.filter('pnl > 0') }}` |
| `.map('필드')` | 필드만 뽑기 | `{{ nodes.account.positions.map('symbol') }}` |
| `.sum('필드')` | 필드 합계 | `{{ nodes.account.positions.sum('quantity') }}` |
| `.avg('필드')` | 필드 평균 | `{{ nodes.account.positions.avg('pnl') }}` |
| `.flatten('중첩키')` | 부모 필드 유지하며 평탄화 | `{{ nodes.scan.symbols.flatten('bars') }}` |
| `[i]` / `['key']` | 인덱스/키 접근 | `{{ nodes.account.positions[0]['symbol'] }}` |

> `.filter()` 는 **딱 하나**의 `필드 연산 값` 비교만 받습니다(`> < >= <= == !=`).
> `and`/`or`/괄호는 안 됩니다 — `.filter('pnl > 0').filter('symbol == AAPL')` 처럼 **두 번 체이닝**하세요.
> 값은 따옴표를 붙이면 문자열, `true`/`false`/`none` 은 리터럴, 숫자는 숫자, 그 외에는 문자열로 파싱되어
> `symbol == AAPL` 처럼 따옴표 없이도 됩니다. 문법에 안 맞는 조건은 **배열을 그대로 반환**(오류 아님)합니다.

### 포트 vs 헬퍼 이름 충돌

노드에 헬퍼와 같은 이름의 출력 포트(`count`, `sum`, `first` …)가 있으면:

- 맨 속성 `{{ nodes.x.count }}` → **포트 값**(있으면), 없으면 헬퍼 메서드 객체
- 호출 `{{ nodes.x.count() }}` → **항상 헬퍼**

> 그래서 `{{ nodes.x.first }}`(포트가 없는 노드에서)는 **메서드 객체**를 반환하며 JSON 직렬화가 안 됩니다.
> 개수를 원하면 `.count()`, 첫 요소를 원하면 `.first()` 처럼 **괄호를 붙이세요.**

### ⚠️ 프록시의 함정 (자주 틀림)

NodeOutputProxy 는 `__len__`/`__iter__`/`__bool__` 이 **없습니다**:

- `len(nodes.x.positions)` → **오류**(`no len()`). → `.count()` 또는 `len(nodes.x.positions.all())`
- `x in proxy`, `sorted(proxy)`, `list(proxy)`, `tuple(proxy)`, `max(proxy)` → **무한 루프로 멈춥니다.**
  → 먼저 `.all()` 로 리스트로 바꾸세요: `{{ 'AAPL' in nodes.x.positions.all() }}`
- 빈 결과라도 **항상 truthy** → `{{ 'yes' if nodes.c.passed_symbols else 'no' }}` 는 빈데도 `'yes'`.
  비어있는지 확인은 `{{ nodes.c.passed_symbols.count() == 0 }}` 로 하세요.
- `stats.*` 는 프록시를 자동으로 풀지 **않습니다**(`lst.*` 만 풉니다).
  `stats.mean(nodes.x.values)` 는 멈추거나 오류 → `stats.mean(nodes.x.values.all())`.

---

## 4. 네임스페이스 함수

### 날짜 `date.*`

| 함수 | 뜻 |
|------|-----|
| `date.today(format=None)` | 오늘 |
| `date.now()` | 현재 시각 |
| `date.ago(n, format=None)` | n일 전 |
| `date.later(n, format=None)` | n일 후 |
| `date.months_ago(n, format=None)` | **30일 × n** 전 (달력상 개월이 아님) |
| `date.year_start()` / `date.year_end()` | 올해 1/1 · 12/31 |
| `date.month_start()` | 이번 달 1일 |

`format` 규칙 (**중요**):

- 생략 → ISO `YYYY-MM-DD`
- `'yyyymmdd'` → `%Y%m%d` (예: `20260101`)
- `'iso'` → `%Y-%m-%d`
- **그 밖의 문자열은 그대로 strftime 패턴**으로 씁니다. `'%Y/%m/%d'` 는 되지만,
  `'yyyy-mm-dd'` 같은 자리표시자는 **그 글자 그대로** 돌아옵니다(변환 안 됨). ISO 를 원하면 생략하거나 `'iso'`.

```
{{ date.ago(30, format='yyyymmdd') }}      // "20260826"
{{ date.today(format='iso') }}             // "2026-09-25"
```

- `month_end`, 요일 헬퍼, 날짜 파싱/차이 헬퍼는 **없습니다.**
- 검증 리플레이에서는 `date.*` 가 픽스처의 `as_of` 시각에 고정됩니다(라이브는 로컬 시계).

### 금융 `finance.*`

| 함수 | 뜻 | 예시 |
|------|-----|------|
| `finance.pct_change(old, new)` | 변화율 % `((new-old)/old*100)` | `{{ finance.pct_change(100, 110) }}` → `10.0` |
| `finance.pct(part, total)` | **part 가 total 의 몇 %인지** `(part/total*100)` | `{{ finance.pct(50, 200) }}` → `25.0` |
| `finance.discount(price, pct)` | 할인가 `price*(1-pct/100)` | `{{ finance.discount(1000, 20) }}` → `800.0` |
| `finance.markup(price, pct)` | 인상가 `price*(1+pct/100)` | `{{ finance.markup(1000, 20) }}` → `1200.0` |
| `finance.annualize(ret, days)` | 연환산 수익률(252일 기준) | `{{ finance.annualize(5, 30) }}` |
| `finance.compound(principal, rate, periods)` | 복리 | `{{ finance.compound(1000, 10, 3) }}` → `1331.0` |

> **⚠️ `finance.pct` 오해 주의**: 이건 "값의 몇 %"가 **아닙니다.**
> `finance.pct(1000, 10)` 은 `1000` 을 `10` 으로 나눠 **`10000.0`** 이 됩니다.
> "잔고의 10%"를 원하면 `finance.pct` 가 아니라 **곱셈**을 쓰세요:
> `{{ nodes.account.balance.orderable_amount * 0.1 }}`.

### 통계 `stats.*`

`stats.mean` · `stats.avg`(mean 별칭) · `stats.median` · `stats.stdev` · `stats.variance`.
**평범한 리스트**를 받습니다(프록시 자동 언랩 안 함 — 위 함정 참고).

```
{{ stats.mean([1, 2, 3, 4, 5]) }}                       // 3.0
{{ stats.mean(nodes.account.positions.map('pnl').all()) }}   // 프록시는 .all() 로
```

### 포맷 `format.*`

| 함수 | 예시 |
|------|------|
| `format.pct(value, decimals=2)` — **이미 % 값**이라 가정(×100 안 함) | `{{ format.pct(12.34) }}` → `"12.34%"` |
| `format.currency(value, symbol='$', decimals=2)` | `{{ format.currency(1234.56) }}` → `"$1,234.56"` |
| `format.number(value, decimals=2)` | `{{ format.number(1234567.89) }}` → `"1,234,567.89"` |

### 리스트 `lst.*`

`list` 은 타입 변환 내장이라 리스트 유틸은 **`lst`** 네임스페이스입니다(`list.first(...)` 는 실패).

| 함수 | 예시 |
|------|------|
| `lst.first(items)` / `lst.last(items)` / `lst.count(items)` | `{{ lst.first([1,2,3]) }}` → `1` |
| `lst.pluck(items, 'a.b')` — 점 경로 지원, 프록시 언랩 | `{{ lst.pluck(nodes.account.positions, 'symbol') }}` |
| `lst.flatten(items, nested_key)` — **인자 2개 필수** | `{{ lst.flatten(nodes.scan.symbols, 'bars') }}` |

> **⚠️ `lst.flatten` 인자**: `nested_key` 는 **필수**입니다. `lst.flatten(items)` 처럼 하나만 주면
> "필수 인자 누락" 오류입니다. 반드시 `lst.flatten(items, '중첩키')`.

`pluck` vs `flatten` — 입력이 아래일 때:
```json
[{"symbol":"AAPL","bars":[{"rsi":33.5}]}, {"symbol":"TSLA","bars":[{"rsi":62.1}]}]
```
- `lst.pluck(values, 'symbol')` → `["AAPL","TSLA"]`
- `lst.flatten(values, 'bars')` → `[{"symbol":"AAPL","rsi":33.5}, {"symbol":"TSLA","rsi":62.1}]`

---

## 5. 내장 함수 · 상수

- 타입 변환: `bool int float str list dict tuple`
- 수학: `abs min max sum pow round len range sorted zip all any`
  (`range` 는 100,000 개 초과 시 오류, `pow` 지수는 1000 초과 시 오류 — DoS 방어)
- math: `sqrt log log10 exp ceil floor` · 상수 `pi e`
- 리터럴: `True False None` 과 **JSON 스타일 별칭** `true false null`
  (워크플로우가 JSON 이라 `{{ x != null }}` 도 유효)

---

## 6. 지원되지 않는 것

허용된 AST: 상수 · 이름 · 이항/단항/비교(연쇄)/논리 연산 · `a if c else b` · 속성/인덱스 접근 ·
함수 호출 · 리스트/딕셔너리/튜플 리터럴. **그 밖은 전부 오류**입니다:

- ❌ Jinja 파이프 필터 `{{ x | length }}` (`|` 는 비트연산 → `length` 미정의 변수)
- ❌ `~` 문자열 이어붙이기(구문 오류), 슬라이스 `[1:]`, 람다, 컴프리헨션, f-string, 별표/월러스
- ❌ `{% if %}` / `{% for %}` 블록
- ❌ `import` / `exec` / `eval` / 파일 I/O / 네트워크 / 클래스·함수 정의
- ✅ 문자열 메서드는 됩니다: `'AAPL'.lower()`

---

## 7. 오류가 나면 어떻게 되나 (라이브 vs 리플레이)

| 환경 | 동작 |
|------|------|
| **라이브(실행)** | 식이 실패해도 **노드를 중단하지 않습니다.** 원본 `{{ ... }}` 리터럴을 **그대로 두고 경고 로그**만 남깁니다. (정상/dry_run 모드에서는 한 필드라도 실패하면 그 노드의 **설정 전체**를 리터럴로 유지합니다.) 그래서 하위 노드가 `{{ ... }}` 문자열을 그대로 받는 **조용한 오작동**이 생길 수 있으니, 잘못된 바인딩은 미리 잡아야 합니다. |
| **검증 리플레이** | 같은 평가기를 쓰지만 미해결 바인딩이 하나라도 있으면 **`ContractViolation` 로 즉시 중단**합니다(리터럴 유지 안 함). `date.*` 는 픽스처 시각으로 고정됩니다. |

실행 **전** 정적 리졸버가 `nodes.<id>.<port>` 형태만 검사합니다(알 수 없는 노드 ID → `INVALID_EXPRESSION_REF`).
대괄호 형태와 `{{ item }}`/`{{ row }}` 는 정적 검사 대상이 아니며, 체인 메서드 화이트리스트는
실제 프록시가 구현한 것보다 넓어서 `.mean`/`.min`/`.unique` 등은 정적으로는 통과해도 **런타임에서 실패**합니다.

---

## 8. 실전 예제

### 백테스트 날짜 범위
```json
{
  "id": "historicalData",
  "type": "OverseasStockHistoricalDataNode",
  "start_date": "{{ date.months_ago(input.backtest_months, format='yyyymmdd') }}",
  "end_date": "{{ date.today(format='yyyymmdd') }}"
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
> `input.symbols` 는 워크플로우 입력(리스트)이라 `len(...)` 이 됩니다. 노드 출력 개수는
> `len(...)` 대신 `nodes.<id>.<port>.count()` 를 쓰세요(프록시엔 len 이 없습니다).

### 요약 표시
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

자동 반복(`item`/`index`/`total`)의 자세한 규칙은 [auto_iterate_guide.md](./auto_iterate_guide.md) 를 보세요.
