# 동적 노드 주입하기 (Dynamic Node Injection)

## 1. 개요

### 동적 노드란?

**동적 노드(Dynamic Node)**는 `programgarden-community` 패키지에 PR하지 않고도, 런타임에 사용자가 직접 만든 노드를 워크플로우에 주입하여 실행할 수 있는 기능입니다.

기존에는 동적 로직을 추가하려면 `programgarden-community`에 플러그인을 기여해야 했습니다. 동적 노드는 이 과정 없이 **자신만의 노드를 즉시 사용**할 수 있게 해줍니다.

### 기존 플러그인 vs 동적 노드

| 항목 | 커뮤니티 플러그인 | 동적 노드 |
|------|-------------------|-----------|
| 등록 방식 | `programgarden-community`에 PR 제출 | 런타임에 코드로 주입 |
| 배포 | 패키지 릴리스 필요 | 즉시 사용 가능 |
| 사용 범위 | 모든 사용자 공유 | 주입한 세션에서만 사용 |
| 네이밍 | 자유 | `Dynamic_` prefix 필수 |
| credential 접근 | 가능 | 불가 (보안상 차단) |
| 적합한 경우 | 범용 전략/지표 | 개인 전략, 프로토타이핑, 독자 로직 |

### 언제 사용하는가?

- **개인 전략**을 워크플로우에 통합하고 싶을 때
- 새로운 지표나 로직을 **빠르게 프로토타이핑**할 때
- 외부 라이브러리(pandas, numpy 등)를 활용한 **독자적인 분석 노드**가 필요할 때
- 커뮤니티 기여 전에 **로컬에서 먼저 테스트**하고 싶을 때

---

## 2. 핵심 개념

### 스키마와 클래스 분리 (Lazy Loading)

동적 노드는 **스키마(Schema)**와 **클래스(Class)**를 분리하여 관리합니다.

```mermaid
flowchart LR
    A["스키마 등록<br/>(UI 표시용)"] -- "앱 시작 시 ──── 실행 직전" --> B["클래스 주입<br/>(실행용)"]
```

- **스키마**: 노드의 메타정보(타입명, 카테고리, 입출력 포트). UI에 노드 목록을 표시하는 데 사용됩니다. 클래스가 없어도 등록할 수 있습니다.
- **클래스**: 실제 실행 로직이 담긴 Python 클래스. 워크플로우 실행 직전에 주입합니다.

이 분리 덕분에 앱 시작 시에는 가벼운 스키마만 로드하고, 실행에 필요한 클래스만 나중에 다운로드/주입할 수 있습니다.

### Dynamic_ prefix 네이밍 규칙

동적 노드의 타입명은 반드시 `Dynamic_`으로 시작해야 합니다.

```
Dynamic_MyRSI        ✅
Dynamic_MACDCross    ✅
MyCustomNode        ❌ (Dynamic_ prefix 없음)
ConditionNode       ❌ (기존 노드와 충돌 가능)
```

이 규칙은:
- 기존 내장 노드와의 **이름 충돌을 방지**합니다
- 워크플로우에서 동적 노드를 **쉽게 식별**할 수 있게 합니다
- `get_required_dynamic_types()`가 필요한 동적 타입을 자동으로 찾을 수 있게 합니다

### 책임 분리

| 영역 | 라이브러리 (ProgramGarden) | 사용자 |
|------|---------------------------|--------|
| 스키마 저장소 | 제공 (`DynamicNodeRegistry`) | 스키마 정의 및 등록 |
| 클래스 검증 | BaseNode 상속, execute() 존재, 포트 일치 검증 | 클래스 구현 |
| 클래스 저장 | 검증 후 저장 | 다운로드/import 후 주입 |
| 워크플로우 실행 | 주입된 클래스로 실행 | 실행 요청 |

---

## 3. 사용 흐름 (4단계)

```mermaid
flowchart LR
    A["Step 1<br/>스키마 등록<br/>(앱 시작 시)"] --> B["Step 2<br/>워크플로우 정의<br/>(JSON)"] --> C["Step 3<br/>타입 확인 &<br/>클래스 주입"] --> D["Step 4<br/>실행<br/>(Job)"]
```

### Step 1: 스키마 등록

앱 시작 시, 사용자가 정의한 노드 스키마를 등록합니다.

```python
from programgarden import WorkflowExecutor

executor = WorkflowExecutor()

# 스키마를 딕셔너리 리스트로 전달
executor.register_dynamic_schemas([
    {
        "node_type": "Dynamic_RSI",
        "category": "condition",
        "description": "동적 RSI 지표",
        "inputs": [
            {"name": "data", "type": "array", "required": True}
        ],
        "outputs": [
            {"name": "rsi", "type": "number"},
            {"name": "signal", "type": "string"},
        ],
    }
])
```

> 이 시점에서는 클래스가 없어도 됩니다. UI에 노드 목록을 표시하는 용도입니다.

### Step 2: 워크플로우 정의

동적 노드를 포함한 워크플로우를 JSON으로 정의합니다.

```json
{
    "nodes": [
        {"id": "start", "type": "StartNode"},
        {"id": "rsi", "type": "Dynamic_RSI", "period": 14}
    ],
    "edges": [
        {"from": "start", "to": "rsi"}
    ]
}
```

### Step 3: 필요 타입 확인 & 클래스 주입

워크플로우에서 사용되는 동적 타입을 확인하고, 해당 클래스를 주입합니다.

```python
# 필요한 동적 타입 확인
required = executor.get_required_dynamic_types(workflow)
# → ["Dynamic_RSI"]

# 클래스 주입
executor.inject_node_classes({
    "Dynamic_RSI": DynamicRSINode,
})

# 준비 완료 확인 (선택)
assert executor.is_dynamic_node_ready("Dynamic_RSI")
```

### Step 4: 실행 & 정리

```python
# 검증
validation = executor.validate(workflow)
assert validation.is_valid

# 실행
job = await executor.execute(workflow)

# ... 워크플로우 실행 ...

# 정리 (실행 후 메모리 해제)
await job.stop()
executor.clear_injected_classes()
```

---

## 4. 동적 노드 클래스 작성법

### 기본 구조

동적 노드는 `BaseNode`을 상속하고, `execute()` 메서드를 구현해야 합니다.

```python
from typing import Dict, Any, List
from programgarden_core.nodes.base import BaseNode, NodeCategory, OutputPort

class DynamicRSINode(BaseNode):
    # 필수: 타입명 (스키마의 node_type과 일치해야 함)
    type: str = "Dynamic_RSI"

    # 필수: 카테고리
    category: NodeCategory = NodeCategory.CONDITION

    # 선택: 설정 필드 (Pydantic 필드)
    period: int = 14

    # 필수: 출력 포트 정의 (스키마의 outputs와 이름이 일치해야 함)
    _outputs: List[OutputPort] = [
        OutputPort(name="rsi", type="number"),
        OutputPort(name="signal", type="string"),
    ]

    # 필수: 실행 로직
    async def execute(self, context) -> Dict[str, Any]:
        # context에서 입력 데이터 접근 가능
        # 계산 로직 수행 후 출력 포트에 맞는 딕셔너리 반환
        return {
            "rsi": 35.5,
            "signal": "oversold",
        }
```

### BaseNode 상속

모든 동적 노드는 `programgarden_core.nodes.base.BaseNode`을 상속해야 합니다.

```python
from programgarden_core.nodes.base import BaseNode
```

`BaseNode`은 Pydantic `BaseModel` 기반이므로, 설정 필드를 Pydantic 필드로 선언할 수 있습니다.

### _outputs 정의 (OutputPort)

스키마에 정의한 출력 포트와 **이름이 일치하는** `OutputPort`를 클래스에 선언해야 합니다.

```python
from programgarden_core.nodes.base import OutputPort

_outputs: List[OutputPort] = [
    OutputPort(name="rsi", type="number"),
    OutputPort(name="signal", type="string"),
]
```

`OutputPort` 필드:

| 필드 | 타입 | 필수 | 설명 |
|------|------|:----:|------|
| `name` | str | O | 포트 이름 (스키마의 outputs와 일치) |
| `type` | str | O | 데이터 타입 (`number`, `string`, `array`, `object` 등) |
| `display_name` | str | | 사용자 표시용 이름 |
| `description` | str | | 포트 설명 |

### _inputs 정의 (InputPort, 선택)

입력 포트도 선언할 수 있습니다.

```python
from programgarden_core.nodes.base import InputPort

_inputs: List[InputPort] = [
    InputPort(name="data", type="array", required=True),
]
```

`InputPort` 필드:

| 필드 | 타입 | 필수 | 설명 |
|------|------|:----:|------|
| `name` | str | O | 포트 이름 |
| `type` | str | O | 데이터 타입 |
| `required` | bool | | 필수 여부 (기본: `True`) |
| `multiple` | bool | | 여러 엣지 연결 가능 여부 (기본: `False`) |
| `description` | str | | 포트 설명 |

### execute() 메서드 구현

`execute()`는 비동기 메서드(`async def`)로 구현하며, `Dict[str, Any]`를 반환합니다.

```python
async def execute(self, context) -> Dict[str, Any]:
    # 1. 입력 데이터 접근
    # 2. 계산 로직 수행
    # 3. 출력 포트에 맞는 딕셔너리 반환
    return {
        "output_port_name": value,
    }
```

반환 딕셔너리의 **키**는 `_outputs`에 정의한 포트 이름과 일치해야 합니다.

### 설정 필드 추가

Pydantic 필드로 설정값을 선언하면, 워크플로우 JSON에서 값을 전달받을 수 있습니다.

```python
class DynamicRSINode(BaseNode):
    type: str = "Dynamic_RSI"
    category: NodeCategory = NodeCategory.CONDITION

    # 설정 필드
    period: int = 14
    overbought: float = 70.0
    oversold: float = 30.0

    # ...
```

워크플로우 JSON에서:

```json
{
    "id": "rsi",
    "type": "Dynamic_RSI",
    "period": 21,
    "overbought": 75.0,
    "oversold": 25.0
}
```

---

## 5. API 레퍼런스

### WorkflowExecutor 메서드

| 메서드 | 설명 | 반환 |
|--------|------|------|
| `register_dynamic_schemas(schemas)` | 스키마 딕셔너리 리스트 등록 | `None` |
| `get_required_dynamic_types(workflow)` | 워크플로우에 필요한 동적 타입 목록 | `List[str]` |
| `inject_node_classes(node_classes)` | 노드 클래스 주입 (`{타입명: 클래스}`) | `None` |
| `is_dynamic_node_ready(node_type)` | 실행 준비 완료 여부 (스키마 등록 + 클래스 주입) | `bool` |
| `list_dynamic_node_types()` | 등록된 동적 노드 타입 목록 | `List[str]` |
| `clear_injected_classes()` | 주입된 클래스 초기화 (메모리 정리) | `None` |

#### register_dynamic_schemas(schemas)

```python
executor.register_dynamic_schemas([
    {
        "node_type": "Dynamic_RSI",       # 필수, Dynamic_ prefix
        "category": "condition",          # 선택, 기본값: "data"
        "description": "동적 RSI",      # 선택
        "inputs": [...],                  # 선택, 입력 포트 정의
        "outputs": [...],                 # 선택, 출력 포트 정의
        "config_schema": {...},           # 선택, 설정 필드 스키마
        "version": "1.0.0",              # 선택, 기본값: "1.0.0"
        "author": "홍길동",               # 선택
    }
])
```

**Raises:** `ValueError` - `Dynamic_` prefix가 없는 경우

#### get_required_dynamic_types(workflow)

```python
required = executor.get_required_dynamic_types(workflow)
# → ["Dynamic_RSI", "Dynamic_MACD"]
```

워크플로우 JSON의 `nodes` 배열에서 `Dynamic_`으로 시작하는 타입만 추출합니다.

#### inject_node_classes(node_classes)

```python
executor.inject_node_classes({
    "Dynamic_RSI": DynamicRSINode,
    "Dynamic_MACD": DynamicMACDNode,
})
```

**검증 항목 (자동):**
1. 스키마 등록 여부
2. `BaseNode` 상속 여부
3. `execute()` 메서드 존재 여부
4. 스키마와 클래스의 출력 포트 일치 여부

**Raises:**
- `ValueError` - 스키마 미등록, 포트 불일치
- `TypeError` - BaseNode 미상속, execute() 미구현

#### is_dynamic_node_ready(node_type)

```python
if executor.is_dynamic_node_ready("Dynamic_RSI"):
    print("실행 가능!")
```

스키마 등록 **AND** 클래스 주입이 모두 완료되었을 때 `True`를 반환합니다.

#### clear_injected_classes()

```python
executor.clear_injected_classes()
```

주입된 클래스만 제거합니다. **스키마는 유지됩니다.** 워크플로우 실행 후 메모리 정리 용도로 사용합니다.

### DynamicNodeSchema 필드

| 필드 | 타입 | 필수 | 기본값 | 설명 |
|------|------|:----:|--------|------|
| `node_type` | `str` | O | - | 고유 타입명 (`Dynamic_` prefix 필수) |
| `category` | `str` | | `"data"` | 노드 카테고리 |
| `description` | `str` | | `None` | 노드 설명 |
| `inputs` | `List[Dict]` | | `[]` | 입력 포트 `[{name, type, required, description}]` |
| `outputs` | `List[Dict]` | | `[]` | 출력 포트 `[{name, type, description}]` |
| `config_schema` | `Dict` | | `{}` | 설정 필드 스키마 |
| `version` | `str` | | `"1.0.0"` | 노드 버전 |
| `author` | `str` | | `None` | 작성자 |

---

## 6. 완전한 예제 (RSI + MACD)

### 스키마 정의

```python
schemas = [
    {
        "node_type": "Dynamic_RSI",
        "category": "condition",
        "description": "동적 RSI 지표 노드",
        "inputs": [
            {"name": "data", "type": "array", "required": True}
        ],
        "outputs": [
            {"name": "rsi", "type": "number"},
            {"name": "signal", "type": "string"},
        ],
        "config_schema": {
            "period": {"type": "integer", "default": 14, "min": 1, "max": 100}
        },
    },
    {
        "node_type": "Dynamic_MACD",
        "category": "condition",
        "description": "동적 MACD 지표 노드",
        "outputs": [
            {"name": "macd", "type": "number"},
            {"name": "signal_line", "type": "number"},
        ],
        "config_schema": {
            "fast_period": {"type": "integer", "default": 12},
            "slow_period": {"type": "integer", "default": 26},
        },
    },
]
```

### 클래스 구현

```python
from typing import Dict, Any, List
from programgarden_core.nodes.base import BaseNode, NodeCategory, OutputPort, InputPort


class DynamicRSINode(BaseNode):
    """동적 RSI 지표 노드"""
    type: str = "Dynamic_RSI"
    category: NodeCategory = NodeCategory.CONDITION
    period: int = 14

    _inputs: List[InputPort] = [
        InputPort(name="data", type="array", required=True),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="rsi", type="number"),
        OutputPort(name="signal", type="string"),
    ]

    async def execute(self, context) -> Dict[str, Any]:
        # 실제 RSI 계산 로직을 여기에 구현
        rsi_value = 35.5  # 예시 값

        if rsi_value < 30:
            signal = "oversold"
        elif rsi_value > 70:
            signal = "overbought"
        else:
            signal = "neutral"

        return {
            "rsi": rsi_value,
            "signal": signal,
        }


class DynamicMACDNode(BaseNode):
    """동적 MACD 지표 노드"""
    type: str = "Dynamic_MACD"
    category: NodeCategory = NodeCategory.CONDITION
    fast_period: int = 12
    slow_period: int = 26

    _outputs: List[OutputPort] = [
        OutputPort(name="macd", type="number"),
        OutputPort(name="signal_line", type="number"),
    ]

    async def execute(self, context) -> Dict[str, Any]:
        # 실제 MACD 계산 로직을 여기에 구현
        return {
            "macd": 1.23,
            "signal_line": 1.10,
        }
```

### 워크플로우 JSON

```json
{
    "id": "rsi-macd-workflow",
    "name": "RSI + MACD 전략",
    "version": "1.0.0",
    "nodes": [
        {"id": "start", "type": "StartNode"},
        {"id": "rsi", "type": "Dynamic_RSI", "period": 14},
        {"id": "macd", "type": "Dynamic_MACD", "fast_period": 12, "slow_period": 26}
    ],
    "edges": [
        {"from": "start", "to": "rsi"},
        {"from": "start", "to": "macd"}
    ]
}
```

### 실행 코드

```python
import asyncio
from programgarden import WorkflowExecutor

async def main():
    executor = WorkflowExecutor()

    # 1. 스키마 등록
    executor.register_dynamic_schemas(schemas)

    # 2. 워크플로우 정의
    workflow = {
        "id": "rsi-macd-workflow",
        "name": "RSI + MACD 전략",
        "version": "1.0.0",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            {"id": "rsi", "type": "Dynamic_RSI", "period": 14},
            {"id": "macd", "type": "Dynamic_MACD", "fast_period": 12, "slow_period": 26},
        ],
        "edges": [
            {"from": "start", "to": "rsi"},
            {"from": "start", "to": "macd"},
        ],
    }

    # 3. 필요 타입 확인 & 클래스 주입
    required = executor.get_required_dynamic_types(workflow)
    print(f"필요한 동적 타입: {required}")
    # → ["Dynamic_RSI", "Dynamic_MACD"]

    executor.inject_node_classes({
        "Dynamic_RSI": DynamicRSINode,
        "Dynamic_MACD": DynamicMACDNode,
    })

    # 4. 검증
    validation = executor.validate(workflow)
    if not validation.is_valid:
        print(f"검증 실패: {validation.errors}")
        return

    # 5. 실행
    job = await executor.execute(workflow)
    print(f"Job 시작: {job.job_id}")

    # ... 워크플로우 실행 ...

    # 6. 정리
    await job.stop()
    executor.clear_injected_classes()

asyncio.run(main())
```

---

## 7. 제약사항 & 보안

### credential_id 사용 불가

동적 노드에서는 `credential_id`를 사용할 수 없습니다. 이는 보안상 외부 코드가 사용자의 증권사 인증 정보에 접근하는 것을 차단하기 위함입니다.

```json
{
    "id": "custom",
    "type": "Dynamic_RSI",
    "credential_id": "my-cred"
}
```

위와 같이 `credential_id`를 설정하면 **검증 단계에서 실패**합니다.

> 증권사 API 호출이 필요한 경우, 내장 노드(OverseasStockBrokerNode 등)를 사용하고 그 출력을 동적 노드의 입력으로 연결하세요.

### 검증 규칙

클래스 주입 시(`inject_node_classes`) 자동으로 4가지 검증이 수행됩니다.

| # | 검증 항목 | 실패 시 예외 |
|:-:|-----------|-------------|
| 1 | 스키마 등록 여부 | `ValueError`: "스키마가 등록되지 않은 타입: Dynamic_XXX" |
| 2 | `BaseNode` 상속 여부 | `TypeError`: "BaseNode를 상속해야 함: ClassName" |
| 3 | `execute()` 메서드 존재 | `TypeError`: "execute() 메서드가 없음: ClassName" |
| 4 | 출력 포트 일치 (스키마 vs 클래스) | `ValueError`: "스키마에 정의된 output 포트가 클래스에 없음: {포트명}" |

### 에러 메시지 목록

| 상황 | 에러 메시지 |
|------|------------|
| Dynamic_ prefix 없이 스키마 등록 | `동적 노드는 'Dynamic_' prefix 필수: {타입명}` |
| 스키마 없이 클래스 주입 | `스키마가 등록되지 않은 타입: {타입명}` |
| BaseNode 미상속 | `BaseNode를 상속해야 함: {클래스명}` |
| execute() 미구현 | `execute() 메서드가 없음: {클래스명}` |
| 출력 포트 불일치 | `스키마에 정의된 output 포트가 클래스에 없음: {포트명}` |
| credential_id 사용 시도 | `credential_id를 사용할 수 없습니다` |
| 클래스 미주입 상태에서 실행 | `주입되지 않음` |

---

## 8. FAQ

### Q. 스키마 등록과 클래스 주입을 왜 분리했나요?

**Lazy Loading** 패턴입니다. 앱 시작 시 모든 동적 노드의 Python 코드를 로드하면 시작 시간이 길어집니다. 스키마만 먼저 등록하면 UI에 노드 목록을 빠르게 보여줄 수 있고, 실제 실행이 필요할 때만 해당 클래스를 로드합니다.

### Q. 기존 노드 타입명(예: ConditionNode)을 동적 노드 타입으로 사용할 수 있나요?

아니요. 반드시 `Dynamic_` prefix를 사용해야 합니다. 기존 노드와 이름이 충돌하면 예측할 수 없는 동작이 발생할 수 있습니다.

### Q. 동적 노드에서 외부 라이브러리(pandas 등)를 사용할 수 있나요?

네. `execute()` 메서드 안에서 자유롭게 import하여 사용할 수 있습니다. 다만, 해당 라이브러리가 실행 환경에 설치되어 있어야 합니다.

```python
async def execute(self, context) -> Dict[str, Any]:
    import pandas as pd
    import numpy as np

    # pandas/numpy를 활용한 계산
    data = pd.DataFrame(...)
    rsi = ...
    return {"rsi": rsi, "signal": "oversold"}
```

### Q. clear_injected_classes() 후 스키마는 유지되나요?

네. `clear_injected_classes()`는 클래스만 제거합니다. 스키마는 그대로 유지되어 UI에 노드 목록이 계속 표시됩니다. 다음 실행 시 클래스만 다시 주입하면 됩니다.

### Q. 하나의 워크플로우에 동적 노드와 내장 노드를 함께 사용할 수 있나요?

네. 동적 노드는 내장 노드와 동일한 방식으로 워크플로우에 배치됩니다. edges로 연결하고, `{{ }}` 표현식으로 데이터를 바인딩할 수 있습니다.

```json
{
    "nodes": [
        {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "cred-1"},
        {"id": "historical", "type": "OverseasStockHistoricalDataNode"},
        {"id": "custom_rsi", "type": "Dynamic_RSI", "period": 14}
    ],
    "edges": [
        {"from": "broker", "to": "historical"},
        {"from": "historical", "to": "custom_rsi"}
    ]
}
```

### Q. DynamicNodeRegistry를 직접 사용해야 하나요?

대부분의 경우 `WorkflowExecutor`의 래퍼 메서드만으로 충분합니다. `DynamicNodeRegistry`는 내부적으로 싱글톤 패턴으로 관리되며, `WorkflowExecutor`가 이를 자동으로 사용합니다.

직접 사용이 필요한 경우:

```python
from programgarden_core.registry import DynamicNodeRegistry, DynamicNodeSchema

registry = DynamicNodeRegistry()

# Pydantic 모델로 직접 스키마 등록
schema = DynamicNodeSchema(
    node_type="Dynamic_MyRSI",
    category="condition",
    outputs=[{"name": "rsi", "type": "number"}],
)
registry.register_schema(schema)
```
