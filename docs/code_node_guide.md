# CodeNode — 커스텀 파이썬 코드 노드

## 1. 개요

**CodeNode**는 기존 타입 노드(ConditionNode, FieldMappingNode, IfNode 등)로 표현할 수 없는 커스텀 로직을, 워크플로우 노드 안에 **파이썬 코드 텍스트**로 담아 실행하는 범용 노드입니다.

`programgarden-community`에 플러그인을 기여하지 않고도 나만의 계산(고유 지표, 커스텀 점수 산식, 임시 데이터 가공)을 즉시 워크플로우에 넣을 수 있습니다.

> **구 Dynamic 노드 주입 메커니즘을 대체합니다.** 타입을 등록하고 클래스를 주입하던 방식 대신, 인스턴스 config(JSON)에 코드와 출력 포트를 선언하는 하나의 노드로 단일화되었습니다.

카테고리: `data` (FieldMappingNode / HTTPRequestNode 와 동급 흐름).

## 2. 실행 계약 (함수형)

코드 텍스트에는 **`execute` 함수 하나만** 정의합니다. BaseNode 클래스를 작성할 필요가 없습니다.

```python
async def execute(data, params, context):
    # data:    입력 데이터 바인딩 (상류 값 전체)
    # params:  params 필드로 넘긴 파라미터 dict
    # context: 읽기 전용 스크럽 컨텍스트 (아래 참조)
    ...
    return {"ranked": [...], "count": n}   # dict → 선언한 outputs 포트로 매핑
```

- `async def` 를 권장하며, 일반 `def execute(...)` 도 허용됩니다(자동 래핑).
- 반환한 dict의 키가 선언한 `outputs` 포트로 매핑됩니다.
- 선언한 포트가 반환 dict에 없으면 **경고 로그 + None**(조용한 누락 금지).
- 반환이 dict가 아니면 `result` 포트로 그대로 전달됩니다.

## 3. config 필드

| 필드 | 타입 | 필수 | 설명 |
|------|------|:---:|------|
| `code` | string | ✅ | 파이썬 소스. `async def execute(data, params, context)` 정의 필수 |
| `language` | string | | 기본 `"python"` (향후 확장용) |
| `outputs` | array | | 출력 포트 `[{name, type}]`. **미선언 시 단일 `result` 포트** |
| `params` | object | | 코드에 전달되는 파라미터 (표현식 바인딩 허용) |
| `data` | any | | 입력 데이터 바인딩 (상류 값 전체 — 코드 안에서 반복) |

### 워크플로우 JSON 예시

```json
{
  "id": "momentum",
  "type": "CodeNode",
  "data": "{{ nodes.historical.values }}",
  "params": { "lookback": 20 },
  "outputs": [
    { "name": "ranked", "type": "array" },
    { "name": "count", "type": "number" }
  ],
  "code": "async def execute(data, params, context):\n    lookback = int(params.get('lookback', 20))\n    ranked = []\n    for row in (data or []):\n        ts = row.get('time_series') or []\n        closes = [b.get('close') for b in ts if isinstance(b, dict) and b.get('close') is not None]\n        if len(closes) < 2:\n            continue\n        base = closes[0]\n        momentum = ((closes[-1] - base) / base * 100.0) if base else 0.0\n        ranked.append({'symbol': row.get('symbol'), 'exchange': row.get('exchange'), 'momentum_pct': round(momentum, 2)})\n    ranked.sort(key=lambda r: r['momentum_pct'], reverse=True)\n    return {'ranked': ranked, 'count': len(ranked)}"
}
```

## 4. 출력 소비 — 타입 매칭이 아니다

CodeNode의 출력은 **타입 포트 매칭으로 소비되지 않습니다.** 다운스트림 노드는 자신의 **범용 입력 필드**(예: `TableDisplayNode.data`, `IfNode.left`/`right`, `FieldMappingNode.data`)에 `{{ nodes.<id>.<port> }}` 표현식을 써서 이름으로 값을 꺼냅니다.

- `outputs`를 선언하면 `{{ nodes.<id>.<port> }}` 오타를 정적 검증(`validate()`)이 잡아줍니다.
- 선언한 포트를 아무도 참조하지 않아도 괜찮습니다.

### 소비 패턴 4가지

| 패턴 | 반환 모양 | 예 |
|------|----------|-----|
| **디스플레이/싱크** | 아무 모양 | `CodeNode → TableDisplayNode / Chart / TelegramNode` |
| **타입드 노드(주문/조건)** | **표준 심볼 배열** `[{symbol, exchange, ...}]` | `CodeNode → PositionSizingNode / ConditionNode` |
| **분기/조건** | 스칼라(count/bool/ratio) | `CodeNode → IfNode.left/right` |
| **terminal compute** | (소비자 없음) | 계산·저장만 |

> ⚠️ 타입드 노드(주문·조건)로 흘릴 땐 **반드시 표준 심볼 배열** `[{symbol, exchange, ...}]` 모양을 반환하세요. 모양이 틀리면 CodeNode가 아니라 그걸 읽는 타입드 노드에서 실패합니다. 예제 `88-code-node-symbol-passthrough` 참조.

## 5. context — 읽기 전용 스크럽 컨텍스트

`execute`의 세 번째 인자 `context`는 **읽기 전용**이며, 안전한 것만 노출합니다.

- 노출 O: 안전 헬퍼 네임스페이스 `context.date` / `context.finance` / `context.stats` / `context.format` / `context.lst` (표현식 바인딩과 동일), risk 읽기 스냅샷, 워크플로우 메타(`context.job_id`, `context.dry_run`).
- 노출 X: credential(앱키)·broker·executor·다른 노드의 live 객체. **`context.get_credential(...)` 같은 접근은 존재하지 않습니다.**

```python
async def execute(data, params, context):
    return {"pct": context.finance.pct_change(100, 110), "avg": context.stats.mean(data)}
```

## 6. 보안 (4계층, 항상 강제)

CodeNode 코드는 **항상** 다음 4계층을 거칩니다. 끄는 공개 스위치는 없습니다.

1. **스크럽 컨텍스트** — credential 접근 경로 자체를 제거(§5).
2. **제한 builtins + AST 차단목록** — `eval`/`exec`/`getattr`/`open` 등 제거 + 화이트리스트 `__import__`(순수 계산용 stdlib: math/statistics/json/datetime/…만). AST로 위험 import(`os`/`socket`/`urllib`/`subprocess`/…), introspection dunder(`__class__`/`__globals__`/…), 밑줄 attribute 접근을 차단.
3. **바인딩 봉쇄** — `data`/`params`에 credential/secret 유사 소스를 참조하지 못하게 검증.
4. **subprocess 격리** — 코드는 **앱키 없는 자식 프로세스**에서 실행됩니다. 자식 입력은 credential-free 스냅샷만, 결과는 JSON만 왕복.

> 🔴 **완전 샌드박스가 아닙니다.** 순수 파이썬 AST 스크린은 적대적 CPython 코드를 완벽히 격리할 수 없다는 것이 알려진 결과입니다. 위 계층은 강화된 **defense-in-depth**로 알려진 우회를 전부 차단하고 in-memory 앱키를 물리적으로 격리하지만, **보장은 아닙니다.** 적대적/공유 코드의 진짜 격리는 OS/인프라 계층(사용자별 pod + 네트워크 egress 제한 + 파일권한)의 책임입니다. CodeNode는 "신뢰 코드 실행 + 실수·기회주의 남용 방어"용으로 사용하세요.

### 게이트

- `WorkflowExecutor(allow_code_node=True)` — **기본 ON**. 개인 PC·pod 어디서든 설정 없이 동작.
- `allow_code_node=False` 로 생성하면 CodeNode 포함 워크플로우 실행을 `CODE_NODE_DISABLED`로 거부합니다(코드 실행을 막아야 하는 검증 전용 환경용). `NodeRunner(allow_code_node=...)`도 동일.

## 7. 구조화 에러 (챗봇 소비용)

모든 실패는 구조화된 영어 에러로 반환됩니다.

| 코드 | 시점 | 의미 |
|------|------|------|
| `CODE_NODE_SYNTAX_ERROR` | 실행 전 | 문법 오류 (라인·오프셋 동봉) |
| `CODE_NODE_FORBIDDEN` | 실행 전 | 차단된 import/호출/attribute |
| `CODE_NODE_NO_EXECUTE` | 실행 전 | `execute` 함수 미정의 |
| `CODE_NODE_EXEC_ERROR` | 실행 | 예외·워커 크래시·타임아웃·비직렬화 반환 |
| `CODE_NODE_DISABLED` | 실행 | `allow_code_node=False` 환경 |

`validate()`가 실행 전에 문법/스크리닝/`execute` 존재를 사전검증합니다.

## 8. 단독 실행 (NodeRunner)

```python
from programgarden import NodeRunner

runner = NodeRunner()
out = await runner.run(
    "CodeNode",
    code="async def execute(data, params, context):\n    return {'doubled': [x*2 for x in data]}",
    outputs=[{"name": "doubled", "type": "array"}],
    data=[1, 2, 3],
)
# → {"doubled": [2, 4, 6]}
```

## 9. 언제 쓰고, 언제 쓰지 않나

- ✅ 기존 노드로 표현 못 하는 커스텀 지표/점수 산식, 임시 데이터 가공.
- ❌ 기존 타입 노드로 가능한 로직 — RSI/필드 리네임/주문 사이징/if 분기는 각각 ConditionNode / FieldMappingNode / PositionSizingNode / IfNode 를 쓰세요. CodeNode에 몰아넣으면 워크플로우 그래프와 검증 계층에서 의도가 숨습니다.
- ❌ credential·주문·네트워크 접근 (설계상 불가).

## 10. 예제

- `examples/workflows/87-code-node-momentum.json` — 커스텀 모멘텀 스코어 (선언 outputs).
- `examples/workflows/88-code-node-symbol-passthrough.json` — 표준 심볼 배열 → 타입드 노드 패스스루.

## 관련 문서

- [노드 레퍼런스 — CodeNode](node_reference.md)
- [표현식 문법](expression_guide.md)
- [자동 반복 처리](auto_iterate_guide.md)
- [노드 단독 실행 (NodeRunner)](node_runner_guide.md)
