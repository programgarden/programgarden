# 노드 단독 실행하기 (NodeRunner)

## 1. 개요

### NodeRunner란?

**NodeRunner**는 워크플로우를 만들지 않고, 개별 노드를 **단독으로 실행**하여 데이터를 주고받을 수 있는 경량 API입니다.

기존에는 노드를 사용하려면 워크플로우 JSON을 정의하고, `WorkflowExecutor`로 전체 워크플로우를 실행해야 했습니다. NodeRunner는 이 과정 없이 **노드 하나만 바로 실행**할 수 있게 해줍니다.

### 워크플로우 실행 vs NodeRunner

| 항목 | 워크플로우 실행 | NodeRunner |
|------|----------------|------------|
| 사용 방식 | JSON 정의 → WorkflowExecutor | `runner.run("노드타입", ...)` |
| 실행 단위 | 전체 DAG (여러 노드) | 노드 1개 |
| 브로커 연결 | BrokerNode가 자동 처리 | NodeRunner가 자동 처리 |
| 적합한 경우 | 자동매매 전략 운영 | 데이터 조회, 테스트, 프로토타이핑 |

### 언제 사용하는가?

- **시세/잔고를 빠르게 조회**하고 싶을 때
- 새로운 전략을 만들기 전에 **노드 동작을 테스트**하고 싶을 때
- 스크립트에서 **특정 노드의 I/O만 활용**하고 싶을 때
- Jupyter Notebook 등에서 **탐색적으로 데이터를 조회**하고 싶을 때

---

## 2. 빠른 시작

### 설치

```bash
pip install programgarden
```

### 단순 노드 실행 (credential 불필요)

```python
import asyncio
from programgarden import NodeRunner

async def main():
    runner = NodeRunner()
    result = await runner.run("HTTPRequestNode",
        url="https://api.example.com/data",
        method="GET",
    )
    print(result)
    # {"body": {...}, "status_code": 200, "headers": {...}}

asyncio.run(main())
```

### 시세 조회 (브로커 credential 필요)

```python
import asyncio
from programgarden import NodeRunner

async def main():
    async with NodeRunner(credentials=[
        {
            "credential_id": "my-broker",
            "type": "broker_ls_overseas_stock",
            "data": {
                "appkey": "여기에_앱키",
                "appsecret": "여기에_앱시크릿",
            },
        }
    ]) as runner:
        # AAPL 현재가 조회
        result = await runner.run("OverseasStockMarketDataNode",
            credential_id="my-broker",
            symbols=[{"symbol": "AAPL", "exchange": "NASDAQ"}],
            fields=["price", "volume", "change_pct"],
        )
        print(result)
        # {"values": [{"symbol": "AAPL", "price": 263.56, "volume": 24289, ...}]}

asyncio.run(main())
```

---

## 3. 노드 유형별 사용법

NodeRunner가 지원하는 노드는 3가지 유형으로 나뉩니다.

### 유형 1: 단순 노드 (credential 불필요)

외부 API 인증 없이 실행 가능한 노드입니다.

| 노드 | 용도 |
|------|------|
| `HTTPRequestNode` | HTTP API 호출 |
| `FieldMappingNode` | 데이터 변환/매핑 |
| `ConditionNode` | 조건 판단 (플러그인 기반) |
| `IfNode` | 조건 분기 |
| `TableDisplayNode` | 테이블 표시 |
| `SplitNode` / `AggregateNode` | 데이터 분할/집계 |

```python
runner = NodeRunner()

# ConditionNode + RSI 플러그인
result = await runner.run("ConditionNode",
    plugin="RSI",
    fields={"period": 14, "threshold": 30},
    data=[{"close": 100}, {"close": 95}, {"close": 92}, ...],
)
```

### 유형 2: Credential 노드

API 키 등 인증 정보가 필요한 노드입니다. `credentials` 배열로 전달합니다.

| 노드 | credential type |
|------|-----------------|
| `HTTPRequestNode` (Bearer) | `http_bearer` |

```python
runner = NodeRunner(credentials=[
    {
        "credential_id": "my-api",
        "type": "http_bearer",
        "data": {"token": "sk-xxx", "header_name": "Authorization"},
    }
])

result = await runner.run("HTTPRequestNode",
    credential_id="my-api",
    url="https://api.example.com/protected",
    method="GET",
)
```

### 유형 3: 브로커 의존 노드

LS증권 API를 사용하는 노드입니다. NodeRunner가 **LS 로그인과 connection 생성을 자동 처리**합니다.

| 노드 | 용도 | credential type |
|------|------|-----------------|
| `OverseasStockMarketDataNode` | 해외주식 현재가 | `broker_ls_overseas_stock` |
| `OverseasStockFundamentalNode` | 펀더멘털 (PER, EPS 등) | `broker_ls_overseas_stock` |
| `OverseasStockAccountNode` | 해외주식 잔고 | `broker_ls_overseas_stock` |
| `OverseasStockHistoricalDataNode` | 해외주식 과거 시세 | `broker_ls_overseas_stock` |
| `OverseasStockNewOrderNode` | 해외주식 주문 | `broker_ls_overseas_stock` |
| `OverseasFuturesMarketDataNode` | 해외선물 현재가 | `broker_ls_overseas_futures` |
| `OverseasFuturesAccountNode` | 해외선물 잔고 | `broker_ls_overseas_futures` |

```python
runner = NodeRunner(credentials=[
    {
        "credential_id": "stock-broker",
        "type": "broker_ls_overseas_stock",
        "data": {"appkey": "...", "appsecret": "..."},
    }
])

# 잔고 조회
account = await runner.run("OverseasStockAccountNode",
    credential_id="stock-broker",
)
print(f"보유 종목 수: {account['count']}")

# 펀더멘털 조회
fundamental = await runner.run("OverseasStockFundamentalNode",
    credential_id="stock-broker",
    symbols=[{"symbol": "AAPL", "exchange": "NASDAQ"}],
    fields=["per", "eps", "market_cap"],
)
print(f"AAPL PER: {fundamental['values'][0]['per']}")
```

> **참고**: `broker_ls_overseas_stock`은 LS증권 해외주식 실전 전용입니다 (모의투자 미지원). 해외선물 모의투자는 `broker_ls_overseas_futures` + `"paper_trading": true`로 사용하세요.

---

## 4. API 레퍼런스

### NodeRunner 생성

```python
NodeRunner(
    credentials: list = None,       # Credential 목록
    context_params: dict = None,    # 실행 컨텍스트 파라미터
    raise_on_error: bool = True,    # 에러 시 예외 발생 여부
)
```

| 파라미터 | 설명 | 기본값 |
|----------|------|--------|
| `credentials` | 워크플로우 JSON의 `credentials`와 동일한 형식 | `None` |
| `context_params` | 실행 컨텍스트에 전달할 추가 파라미터 | `None` |
| `raise_on_error` | 노드 결과에 `error`가 있으면 `RuntimeError` 발생 | `True` |

### runner.run()

```python
await runner.run(
    node_type: str,          # 노드 타입명 (예: "OverseasStockMarketDataNode")
    *,
    node_id: str = None,     # 노드 ID (생략 시 자동 생성)
    credential_id: str = None,  # 사용할 credential ID
    **config,                # 노드 설정 값
) -> dict
```

**반환값**: 노드 실행 결과 딕셔너리 (출력 포트 값들)

**예외**:
- `ValueError` — 알 수 없는 노드 타입, 실시간 노드 실행 시도
- `RuntimeError` — 실행 실패 (`raise_on_error=True`인 경우)

### runner.list_node_types()

```python
runner.list_node_types() -> list[str]
```

사용 가능한 노드 타입 목록을 반환합니다. 실시간 노드와 BrokerNode는 제외됩니다.

### runner.get_node_schema()

```python
runner.get_node_schema(node_type: str) -> dict | None
```

노드의 설정 스키마를 반환합니다. 어떤 파라미터를 전달할 수 있는지 확인할 때 유용합니다.

### runner.cleanup()

```python
await runner.cleanup()
```

LS 세션 등 리소스를 정리합니다. `async with` 패턴 사용 시 자동 호출됩니다.

---

## 5. async with 패턴

`async with`를 사용하면 실행 후 자동으로 리소스가 정리됩니다. 특히 브로커 노드 사용 시 권장합니다.

```python
async with NodeRunner(credentials=[...]) as runner:
    result1 = await runner.run("OverseasStockMarketDataNode", ...)
    result2 = await runner.run("OverseasStockAccountNode", ...)
# 여기서 자동으로 cleanup() 호출
```

같은 `runner` 인스턴스 내에서 **여러 노드를 실행하면 LS 로그인 세션을 재사용**합니다. 매번 새 `NodeRunner`를 만드는 것보다 효율적입니다.

---

## 6. 에러 처리

### raise_on_error=True (기본값)

노드 결과에 `error` 키가 있으면 `RuntimeError`가 발생합니다.

```python
runner = NodeRunner(raise_on_error=True)  # 기본값

try:
    result = await runner.run("OverseasStockMarketDataNode",
        credential_id="broker",
        symbols=[{"symbol": "INVALID"}],
    )
except RuntimeError as e:
    print(f"에러: {e}")
```

### raise_on_error=False

에러가 있어도 결과를 그대로 반환합니다. 직접 체크해야 합니다.

```python
runner = NodeRunner(raise_on_error=False)
result = await runner.run(...)

if "error" in result:
    print(f"에러 발생: {result['error']}")
else:
    print(f"성공: {result}")
```

---

## 7. 지원하지 않는 노드

### 실시간(WebSocket) 노드

실시간 노드는 WebSocket 연결을 유지하며 지속적으로 데이터를 수신해야 하므로, 단독 실행 개념과 맞지 않아 지원하지 않습니다.

| 미지원 노드 | 대안 |
|-------------|------|
| `OverseasStockRealMarketDataNode` | `OverseasStockMarketDataNode` (REST API) |
| `OverseasStockRealAccountNode` | `OverseasStockAccountNode` (REST API) |
| `OverseasStockRealOrderEventNode` | 워크플로우에서 사용 |

실시간 데이터가 필요하면 기존 워크플로우 방식을 사용하세요.

### BrokerNode

`OverseasStockBrokerNode` / `OverseasFuturesBrokerNode`는 NodeRunner에서 직접 실행할 필요 없습니다. credential을 전달하면 브로커 로그인이 **자동 처리**됩니다.

---

## 8. 전체 예제: 종목 스크리닝

```python
import asyncio
from programgarden import NodeRunner

async def screen_stocks():
    credentials = [{
        "credential_id": "broker",
        "type": "broker_ls_overseas_stock",
        "data": {"appkey": "...", "appsecret": "..."},
    }]

    async with NodeRunner(credentials=credentials) as runner:
        # 1. 관심 종목 현재가 조회
        market = await runner.run("OverseasStockMarketDataNode",
            credential_id="broker",
            symbols=[
                {"symbol": "AAPL", "exchange": "NASDAQ"},
                {"symbol": "MSFT", "exchange": "NASDAQ"},
                {"symbol": "GOOGL", "exchange": "NASDAQ"},
            ],
            fields=["price", "volume", "change_pct"],
        )

        print("=== 현재가 ===")
        for item in market["values"]:
            print(f"  {item['symbol']}: ${item['price']} ({item['change_pct']}%)")

        # 2. 펀더멘털 조회
        fundamental = await runner.run("OverseasStockFundamentalNode",
            credential_id="broker",
            symbols=[
                {"symbol": "AAPL", "exchange": "NASDAQ"},
                {"symbol": "MSFT", "exchange": "NASDAQ"},
                {"symbol": "GOOGL", "exchange": "NASDAQ"},
            ],
            fields=["per", "eps", "market_cap"],
        )

        print("\n=== 펀더멘털 ===")
        for item in fundamental["values"]:
            print(f"  {item['symbol']}: PER={item['per']}, EPS={item['eps']}")

        # 3. 잔고 조회
        account = await runner.run("OverseasStockAccountNode",
            credential_id="broker",
        )

        print(f"\n=== 보유 종목: {account['count']}개 ===")
        for pos in account.get("positions", []):
            print(f"  {pos['symbol']}: {pos['quantity']}주")

asyncio.run(screen_stocks())
```
