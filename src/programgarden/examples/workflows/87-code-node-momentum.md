# 87 · CodeNode 커스텀 모멘텀 스코어 (NASDAQ)

`CodeNode` 로 **기존 타입 노드가 커버하지 못하는 커스텀 계산**을 워크플로우 안에서
실행하는 예제입니다. 종가 배열에서 커스텀 모멘텀 %(첫 종가 대비 마지막 종가 변화율)를
계산하고 매수/매도 시그널을 붙여 랭킹합니다.

## 파이프라인

```
StartNode → OverseasStockBrokerNode → OverseasStockHistoricalDataNode
          → CodeNode(모멘텀 계산) → TableDisplayNode
```

- `OverseasStockHistoricalDataNode` 가 AAPL/MSFT/NVDA 의 일봉 30개를 조회 → `values`
- `CodeNode` 가 `data = {{ nodes.historical.values }}` 로 배열 전체를 받아 **코드 안에서 반복**
  (auto-iterate 아님 — 자식 프로세스 1회 호출로 배치 처리)
- 선언 `outputs` = `ranked`(array) / `count`(number) → 반환 dict 의 동명 키가 각 포트로 매핑
- `TableDisplayNode` 가 `{{ nodes.momentum.ranked }}` 를 표로 출력

## CodeNode 실행 계약

```python
async def execute(data, params, context):
    lookback = int(params.get('lookback', 20))
    results = []
    for row in (data or []):
        ts = row.get('time_series') or []
        closes = [b.get('close') for b in ts if isinstance(b, dict) and b.get('close') is not None]
        if len(closes) < 2:
            continue
        window = closes[-lookback:] if len(closes) >= lookback else closes
        base = window[0]
        momentum = ((window[-1] - base) / base * 100.0) if base else 0.0
        results.append({
            'symbol': row.get('symbol'),
            'exchange': row.get('exchange'),
            'momentum_pct': round(momentum, 2),
            'signal': 'buy' if momentum > 0 else 'sell',
        })
    ranked = sorted(results, key=lambda r: r['momentum_pct'], reverse=True)
    return {'ranked': ranked, 'count': len(ranked)}
```

- `data` / `params` 는 실행 전에 바인딩이 평가되어 값으로 전달됩니다.
- `context` 는 **읽기 전용 스크럽 컨텍스트** — 안전 헬퍼(`context.date/finance/stats/format/lst`),
  risk 스냅샷, 워크플로우 메타만 노출. **credential·broker·network 접근 없음.**
- 반환은 **JSON 직렬화 가능한 값**이어야 합니다(자식→부모 경계를 넘기 때문).

## 보안 (항상 적용, 끄는 스위치 없음)

CodeNode 코드는 **앱키 없는 자식 프로세스**에서 실행됩니다:

1. **스크럽 컨텍스트** — credential 접근 경로 자체가 없음
2. **제한 builtins + AST 차단목록** — `os/socket/urllib/subprocess/open`, introspection dunder
   (`__class__`/`__globals__`/…), `eval/exec/getattr` 차단. 순수 계산용 stdlib(math/statistics/json/…)만 import 허용
3. **바인딩 봉쇄** — `data`/`params` 에 credential 유사 바인딩 금지 (`{{ ... appsecret }}` 등)
4. **subprocess 격리** — 고정 워커풀, 자식엔 앱키 물리 부재, 결과는 JSON 만 왕복

## 실행

```bash
cd src/programgarden
poetry run python -c "
import asyncio, json
from programgarden import WorkflowExecutor
wf = json.load(open('examples/workflows/87-code-node-momentum.json'))
async def main():
    exe = WorkflowExecutor()
    job = await exe.execute(wf, context_params={'dry_run': True, 'max_cycles': 1})
    if getattr(job, '_task', None):
        await asyncio.wait_for(job._task, timeout=60)
    print(job.context.get_all_outputs('momentum'))
asyncio.run(main())
"
```

> ⚠️ 실계좌(overseas_stock)이지만 이 예제는 **조회·계산·표시 경로만** 사용하므로 주문을
> 발사하지 않습니다. dry_run 으로 안전하게 검증됩니다.

## 언제 CodeNode 를 쓰나

- ✅ 기존 노드로 표현 못 하는 커스텀 지표/점수 산식, 임시 데이터 가공
- ❌ 기존 타입 노드로 가능한 로직(RSI/필드 리네임/주문 사이징/if 분기) — 각각
  ConditionNode/FieldMappingNode/PositionSizingNode/IfNode 사용
- ❌ credential·주문·네트워크 접근 (설계상 불가)
