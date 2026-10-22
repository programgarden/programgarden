# CodeNode — 커스텀 파이썬 코드 노드

CodeNode는 기존 노드로 표현하기 어려운 로직을 파이썬 코드로 작성하는 노드입니다.

## 오픈소스 엔진에서의 지원 범위

- 워크플로우 정의에 CodeNode를 넣을 수 있고, 구조 검증(`validate`)도 통과합니다.
- **실행은 ProgramGarden 플랫폼에서만 가능합니다.** 오픈소스 엔진에서 실행하면 해당 노드가
  `CodeNode runs on the ProgramGarden platform only.` 오류로 실패합니다.

## 정의 형식

```json
{
  "id": "momentum",
  "type": "CodeNode",
  "data": "{{ nodes.historical.values }}",
  "params": { "lookback": 20 },
  "outputs": [{ "name": "ranked", "type": "array" }],
  "code": "async def execute(data, params, context):\n    ...\n    return {'ranked': [...]}"
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `code` | string ✅ | `async def execute(data, params, context)` 정의 |
| `outputs` | array | 출력 포트 선언 `[{name, type}]`. 미선언 시 단일 `result` 포트 |
| `params` | object | 코드에 전달되는 파라미터 (표현식 바인딩 허용) |
| `data` | any | 입력 데이터 (상류 값 전체를 바인딩) |

노드 필드 전체 목록은 [노드 레퍼런스](node_reference.md)를 참고하세요.
