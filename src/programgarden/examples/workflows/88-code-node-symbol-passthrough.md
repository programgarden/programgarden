# 88 · CodeNode 표준 심볼 배열 → 타입드 노드 패스스루 (pattern 2)

`CodeNode` 가 **표준 Symbol Data Format `[{symbol, exchange, ...}]`** 을 반환해 다운스트림
**typed 노드**(여기서는 `PositionSizingNode`)가 그대로 소비하는 패턴을 시연합니다. AI 챗봇이
"CodeNode 출력을 타입드 노드로 흘릴 때는 표준 심볼 배열 모양을 반환해야 한다"는 규칙을
정확히 이해하도록 하는 ground-truth 예제입니다.

## 파이프라인

```
StartNode → OverseasStockBrokerNode → OverseasStockHistoricalDataNode
          → CodeNode(rank, 표준 심볼 배열 반환)
              ├─→ PositionSizingNode(fixed_quantity, symbol={{ item }})   # typed 노드가 배열 소비 (auto-iterate)
              └─→ TableDisplayNode(ranked 배열 표시)
```

- `CodeNode` 는 종목별 모멘텀을 계산하고 상위 N개를 **`[{symbol, exchange, momentum_pct}]`**
  (표준 심볼 모양)으로 반환 → `ranked` 포트.
- `PositionSizingNode` 가 `ranked` 배열을 **auto-iterate** 하며 각 심볼을 `symbol: "{{ item }}"`
  로 받아 `fixed_quantity` 로 사이즈만 계산합니다. **주문 노드가 없어 실주문은 발사되지 않습니다**
  (무인 실행 안전).
- `TableDisplayNode` 는 `{{ nodes.rank.ranked }}` 로 표준 심볼 배열을 표시합니다.

## 핵심 — pattern 2 (typed 노드로 흘리기)

CodeNode 출력은 **타입 매칭이 아니라** 소비자 노드가 `{{ nodes.rank.ranked }}` / `{{ item }}`
표현식으로 꺼내 씁니다. typed 노드(주문/조건/사이징)로 흘릴 땐 반드시 **표준 `[{symbol, exchange, ...}]`
모양**을 반환해야 합니다 — 모양이 틀리면 CodeNode 가 아니라 그걸 읽는 typed 노드에서 실패합니다.
(디스플레이/싱크나 If 스칼라로 흘릴 땐 아무 모양이나 됩니다 — 예제 87 참조.)

## CodeNode 코드

```python
async def execute(data, params, context):
    top_n = int(params.get('top_n', 2))
    ranked = []
    for row in (data or []):
        ts = row.get('time_series') or []
        closes = [b.get('close') for b in ts if isinstance(b, dict) and b.get('close') is not None]
        if len(closes) < 2:
            continue
        base = closes[0]
        momentum = ((closes[-1] - base) / base * 100.0) if base else 0.0
        ranked.append({'symbol': row.get('symbol'), 'exchange': row.get('exchange'), 'momentum_pct': round(momentum, 2)})
    ranked.sort(key=lambda r: r['momentum_pct'], reverse=True)
    return {'ranked': ranked[:top_n]}   # 표준 심볼 배열
```

## 실행 (dry_run E2E)

```bash
cd src/programgarden
poetry run python -c "
import asyncio, json
from programgarden import WorkflowExecutor
wf = json.load(open('examples/workflows/88-code-node-symbol-passthrough.json'))
async def main():
    exe = WorkflowExecutor()
    job = await exe.execute(wf, context_params={'dry_run': True, 'max_cycles': 1})
    if getattr(job, '_task', None):
        await asyncio.wait_for(job._task, timeout=60)
    print('ranked:', job.context.get_all_outputs('rank'))
asyncio.run(main())
"
```

> ⚠️ 실계좌(overseas_stock)이지만 **조회·계산·표시·사이징 경로만** 사용 — 주문 노드 없음 →
> 무인 실행에서 실주문 0. dry_run 으로 안전 검증됩니다.

> ℹ️ 참고: `PositionSizingNode` 의 출력 포트는 현재 스키마상 `order`(단수)이지만 런타임은
> auto-iterate 병합으로 `orders`(복수)를 방출합니다(계획서 20260702 D-1, alias 미적용). 그래서
> 이 예제는 사이징 결과를 디스플레이에 바인딩하지 않고 CodeNode 의 `ranked` 를 표시합니다 —
> pattern 2 의 요점은 **표준 심볼 배열이 typed 노드 입력으로 그대로 흘러 들어간다**는 것입니다.
