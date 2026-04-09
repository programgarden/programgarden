# 노드 단독 실행하기 (NodeRunner)

Python 코드 몇 줄로 해외주식 시세, 잔고, 펀더멘털 데이터를 바로 조회할 수 있는 가이드입니다.

***

## 1. NodeRunner가 뭔가요?

ProgramGarden에서 노드(Node)는 "하나의 기능을 담당하는 블록"입니다. 예를 들어:

- **MarketDataNode** — 종목의 현재가, 거래량 조회
- **AccountNode** — 내 계좌의 보유 종목, 잔고 조회
- **FundamentalNode** — PER, EPS, 시가총액 등 기업 정보 조회
- **HistoricalDataNode** — 과거 시세(일봉, 주봉 등) 조회

보통 이 노드들은 **워크플로우**(자동매매 전략)에 넣어서 다른 노드들과 연결해 사용합니다. 하지만 "지금 애플 주가가 얼마지?", "내 잔고에 뭐가 있지?" 같은 **간단한 조회를 하려고 워크플로우 전체를 만드는 건 번거롭습니다**.

**NodeRunner**는 이 문제를 해결합니다. 워크플로우 없이 **노드 하나만 골라서 바로 실행**할 수 있습니다.

```
기존 방식 (워크플로우 필요):
  BrokerNode → WatchlistNode → MarketDataNode
  + JSON 정의 + edges 연결 + credentials 설정 ...

NodeRunner 방식 (노드 1개만):
  runner.run("MarketDataNode", symbols=["AAPL"])  끝!
```

### 이럴 때 사용하세요

| 상황 | 예시 |
|------|------|
| 주가 빠르게 확인 | "AAPL 현재가가 얼마지?" |
| 내 잔고 확인 | "지금 보유 중인 종목이 뭐지?" |
| 기업 정보 확인 | "테슬라 PER이 얼마지?" |
| 과거 데이터 조회 | "최근 30일 일봉 데이터를 가져와서 분석하고 싶다" |
| 전략 만들기 전 테스트 | "이 노드가 어떤 데이터를 반환하는지 먼저 확인하고 싶다" |
| Jupyter Notebook | 데이터를 불러와서 pandas로 분석하고 싶다 |

---

## 2. 사전 준비

### 2.1 설치

```bash
pip install programgarden
```

### 2.2 LS증권 API 키 준비

해외주식/선물 데이터를 조회하려면 LS증권의 **App Key**와 **App Secret**이 필요합니다.

아직 없다면 [빠른 시작 가이드](non_dev_quick_guide.md)의 "1.1 LS증권 계좌 개설"과 "1.2 API 키 발급"을 먼저 진행해 주세요.

> **주의**: App Key와 App Secret은 비밀번호와 같습니다. 코드에 직접 넣지 말고, 환경변수나 `.env` 파일로 관리하세요.

### 2.3 async/await 기본 지식

NodeRunner는 Python의 `async/await` 문법을 사용합니다. 처음이라면 아래 패턴만 기억하세요:

```python
import asyncio

async def main():
    # 여기에 NodeRunner 코드 작성
    pass

# 실행
asyncio.run(main())
```

모든 NodeRunner 코드는 `async def main()` 안에 넣고, `asyncio.run(main())`으로 실행하면 됩니다.

---

## 3. 첫 번째 실행: 애플 주가 조회

### 3.1 전체 코드

```python
import asyncio
from programgarden import NodeRunner

async def main():
    # 1단계: NodeRunner에 LS증권 인증 정보 전달
    runner = NodeRunner(credentials=[
        {
            "credential_id": "my-broker",        # 내가 정한 이름 (아무거나 OK)
            "type": "broker_ls_overseas_stock",   # 해외주식용 브로커
            "data": {
                "appkey": "여기에_앱키_입력",       # LS증권에서 발급받은 App Key
                "appsecret": "여기에_앱시크릿_입력",  # LS증권에서 발급받은 App Secret
            },
        }
    ])

    # 2단계: AAPL(애플) 현재가 조회
    result = await runner.run(
        "OverseasStockMarketDataNode",              # 사용할 노드 이름
        credential_id="my-broker",                  # 위에서 정한 credential 이름
        symbols=[{"symbol": "AAPL", "exchange": "NASDAQ"}],  # 조회할 종목
        fields=["price", "volume", "change_pct"],   # 가져올 데이터 항목
    )

    # 3단계: 결과 출력
    for item in result["values"]:
        print(f"종목: {item['symbol']}")
        print(f"현재가: ${item['price']}")
        print(f"거래량: {item['volume']:,}")
        print(f"등락률: {item['change_pct']}%")

    # 4단계: 정리
    await runner.cleanup()

asyncio.run(main())
```

### 3.2 실행 결과 예시

```
종목: AAPL
현재가: $263.56
거래량: 24,289
등락률: -0.3%
```

### 3.3 코드 설명

**1단계 — credentials 설정**: NodeRunner에게 "어떤 증권사를 쓸 건지" 알려줍니다.

```python
credentials=[{
    "credential_id": "my-broker",        # 나만의 이름표 (여러 개 쓸 때 구분용)
    "type": "broker_ls_overseas_stock",   # LS증권 해외주식
    "data": {"appkey": "...", "appsecret": "..."},  # API 키
}]
```

- `credential_id` — 자유롭게 정할 수 있는 이름입니다. 나중에 `runner.run()`에서 이 이름으로 어떤 인증을 쓸지 지정합니다.
- `type` — 증권사와 상품 종류를 지정합니다.
  - `broker_ls_overseas_stock` = LS증권 해외주식
  - `broker_ls_overseas_futures` = LS증권 해외선물

**2단계 — 노드 실행**: 어떤 노드를 어떤 설정으로 실행할지 지정합니다.

```python
await runner.run(
    "OverseasStockMarketDataNode",    # 해외주식 현재가 조회 노드
    credential_id="my-broker",        # 1단계에서 정한 이름
    symbols=[...],                    # 조회할 종목
    fields=[...],                     # 가져올 데이터
)
```

**3단계 — 결과 사용**: 결과는 Python 딕셔너리(dict)로 돌아옵니다. 시세 노드는 `result["values"]` 안에 종목별 데이터가 리스트로 들어있습니다.

---

## 4. 자주 쓰는 조회 예제

아래 예제들은 모두 같은 credentials 설정을 사용합니다. `appkey`와 `appsecret`만 실제 값으로 바꿔주세요.

### 4.1 여러 종목 한번에 시세 조회

```python
async def main():
    async with NodeRunner(credentials=[
        {"credential_id": "broker", "type": "broker_ls_overseas_stock",
         "data": {"appkey": "...", "appsecret": "..."}}
    ]) as runner:

        result = await runner.run("OverseasStockMarketDataNode",
            credential_id="broker",
            symbols=[
                {"symbol": "AAPL", "exchange": "NASDAQ"},    # 애플
                {"symbol": "MSFT", "exchange": "NASDAQ"},    # 마이크로소프트
                {"symbol": "GOOGL", "exchange": "NASDAQ"},   # 구글
                {"symbol": "AMZN", "exchange": "NASDAQ"},    # 아마존
                {"symbol": "TSLA", "exchange": "NASDAQ"},    # 테슬라
            ],
            fields=["price", "volume", "change", "change_pct"],
        )

        print(f"{'종목':>6} {'현재가':>10} {'등락':>8} {'등락률':>8} {'거래량':>12}")
        print("-" * 50)
        for item in result["values"]:
            print(f"{item['symbol']:>6} ${item['price']:>9,.2f} "
                  f"{item['change']:>+8.2f} {item['change_pct']:>+7.2f}% "
                  f"{item['volume']:>12,}")
```

출력 예시:
```
  종목       현재가       등락      등락률         거래량
--------------------------------------------------
  AAPL   $  263.56    -0.79   -0.30%       24,289
  MSFT   $  453.12    +2.35   +0.52%       18,456
 GOOGL   $  185.23    -1.12   -0.60%       12,789
  AMZN   $  228.45    +3.21   +1.43%       31,234
  TSLA   $  352.78    -5.67   -1.58%       85,432
```

> **참고**: `async with NodeRunner(...) as runner:` 패턴을 사용하면 코드 블록이 끝날 때 자동으로 정리됩니다. `cleanup()`을 직접 호출하지 않아도 됩니다.

### 4.2 내 계좌 잔고 조회

```python
async def main():
    async with NodeRunner(credentials=[
        {"credential_id": "broker", "type": "broker_ls_overseas_stock",
         "data": {"appkey": "...", "appsecret": "..."}}
    ]) as runner:

        result = await runner.run("OverseasStockAccountNode",
            credential_id="broker",
        )

        print(f"보유 종목 수: {result['count']}개\n")

        for pos in result.get("positions", []):
            print(f"  {pos.get('symbol', '?'):>6}: "
                  f"{pos.get('quantity', 0)}주, "
                  f"평균단가 ${pos.get('avg_price', 0):,.2f}")
```

### 4.3 기업 펀더멘털 데이터 조회

PER(주가수익비율), EPS(주당순이익), 시가총액, 52주 고저가 등을 조회합니다.

```python
async def main():
    async with NodeRunner(credentials=[
        {"credential_id": "broker", "type": "broker_ls_overseas_stock",
         "data": {"appkey": "...", "appsecret": "..."}}
    ]) as runner:

        result = await runner.run("OverseasStockFundamentalNode",
            credential_id="broker",
            symbols=[
                {"symbol": "AAPL", "exchange": "NASDAQ"},
                {"symbol": "MSFT", "exchange": "NASDAQ"},
            ],
            fields=["per", "eps", "market_cap", "high_52w", "low_52w"],
        )

        for item in result["values"]:
            print(f"=== {item['symbol']} ({item.get('name', '')}) ===")
            print(f"  PER: {item['per']:.2f}")
            print(f"  EPS: ${item['eps']:.2f}")
            print(f"  시가총액: ${item['market_cap']:,.0f}")
            print(f"  52주 최고: ${item['high_52w']:,.2f}")
            print(f"  52주 최저: ${item['low_52w']:,.2f}")
            print()
```

출력 예시:
```
=== AAPL (APPLE INC) ===
  PER: 33.39
  EPS: $7.90
  시가총액: $3,869,350,716,000
  52주 최고: $288.62
  52주 최저: $169.21
```

### 4.4 과거 시세 데이터 조회 (일봉)

백테스트나 차트 분석에 사용할 과거 데이터를 가져옵니다.

```python
async def main():
    async with NodeRunner(credentials=[
        {"credential_id": "broker", "type": "broker_ls_overseas_stock",
         "data": {"appkey": "...", "appsecret": "..."}}
    ]) as runner:

        result = await runner.run("OverseasStockHistoricalDataNode",
            credential_id="broker",
            symbols=[{"symbol": "AAPL", "exchange": "NASDAQ"}],
            interval="1d",  # 1d=일봉, 1w=주봉, 1M=월봉
        )

        print(f"데이터 건수: {len(result.get('values', []))}개\n")
        # 최근 5일만 출력
        for candle in result.get("values", [])[:5]:
            print(f"  {candle.get('date', '?')}: "
                  f"시가 ${candle.get('open', 0):.2f}, "
                  f"고가 ${candle.get('high', 0):.2f}, "
                  f"저가 ${candle.get('low', 0):.2f}, "
                  f"종가 ${candle.get('close', 0):.2f}")
```

### 4.5 해외선물 조회 (모의투자)

해외선물은 모의투자를 지원합니다. `type`을 `broker_ls_overseas_futures`로, `paper_trading`을 `true`로 설정하세요.

```python
async def main():
    async with NodeRunner(credentials=[
        {"credential_id": "futures-broker", "type": "broker_ls_overseas_futures",
         "data": {"appkey": "...", "appsecret": "...", "paper_trading": True}}
    ]) as runner:

        # 해외선물 잔고 조회 (모의투자)
        result = await runner.run("OverseasFuturesAccountNode",
            credential_id="futures-broker",
        )
        print(f"선물 포지션: {result['count']}개")
```

> **주의**: 해외주식(`broker_ls_overseas_stock`)은 LS증권 정책상 **모의투자를 지원하지 않습니다**. 해외주식은 항상 실전 모드로 실행됩니다.

---

## 5. 조회 가능한 필드(fields) 목록

### 5.1 MarketDataNode 필드

`OverseasStockMarketDataNode`에서 조회할 수 있는 필드입니다.

| 필드명 | 설명 | 예시 값 |
|--------|------|---------|
| `price` | 현재가 | 263.56 |
| `open` | 시가 | 263.62 |
| `high` | 고가 | 263.82 |
| `low` | 저가 | 263.10 |
| `close` | 종가 | 263.56 |
| `volume` | 거래량 | 24289 |
| `change` | 전일 대비 변동 | -0.79 |
| `change_pct` | 전일 대비 변동률(%) | -0.30 |
| `per` | PER (주가수익비율) | 33.39 |
| `eps` | EPS (주당순이익) | 7.90 |

### 5.2 FundamentalNode 필드

`OverseasStockFundamentalNode`에서 조회할 수 있는 필드입니다.

| 필드명 | 설명 | 예시 값 |
|--------|------|---------|
| `per` | PER (주가수익비율) | 33.39 |
| `eps` | EPS (주당순이익) | 7.90 |
| `market_cap` | 시가총액 | 3869350716000 |
| `high_52w` | 52주 최고가 | 288.62 |
| `low_52w` | 52주 최저가 | 169.21 |
| `name` | 종목명 | APPLE INC |
| `industry` | 업종 | 하드웨어 및 장비 |
| `nation` | 국가 | 미국 |
| `exchange_name` | 거래소명 | 나스닥 |
| `shares_outstanding` | 발행주식수 | 14681100000 |
| `exchange_rate` | 환율 | 1443.1 |

---

## 6. 사용 가능한 노드 목록

NodeRunner에서 실행할 수 있는 주요 노드입니다. 전체 목록은 `runner.list_node_types()`로 확인할 수 있습니다.

### 시세/데이터 조회

| 노드 | 용도 | credential type |
|------|------|:---:|
| `OverseasStockMarketDataNode` | 해외주식 현재가 | `broker_ls_overseas_stock` |
| `OverseasStockFundamentalNode` | 해외주식 펀더멘털 | `broker_ls_overseas_stock` |
| `OverseasStockHistoricalDataNode` | 해외주식 과거 시세 | `broker_ls_overseas_stock` |
| `OverseasFuturesMarketDataNode` | 해외선물 현재가 | `broker_ls_overseas_futures` |
| `OverseasFuturesHistoricalDataNode` | 해외선물 과거 시세 | `broker_ls_overseas_futures` |

### 계좌 조회

| 노드 | 용도 | credential type |
|------|------|:---:|
| `OverseasStockAccountNode` | 해외주식 잔고/보유종목 | `broker_ls_overseas_stock` |
| `OverseasStockOpenOrdersNode` | 해외주식 미체결 주문 | `broker_ls_overseas_stock` |
| `OverseasFuturesAccountNode` | 해외선물 잔고/포지션 | `broker_ls_overseas_futures` |
| `OverseasFuturesOpenOrdersNode` | 해외선물 미체결 주문 | `broker_ls_overseas_futures` |

### 주문

| 노드 | 용도 | credential type |
|------|------|:---:|
| `OverseasStockNewOrderNode` | 해외주식 신규 주문 | `broker_ls_overseas_stock` |
| `OverseasStockModifyOrderNode` | 해외주식 주문 정정 | `broker_ls_overseas_stock` |
| `OverseasStockCancelOrderNode` | 해외주식 주문 취소 | `broker_ls_overseas_stock` |
| `OverseasFuturesNewOrderNode` | 해외선물 신규 주문 | `broker_ls_overseas_futures` |

### 데이터 가공 (credential 불필요)

| 노드 | 용도 |
|------|------|
| `HTTPRequestNode` | 외부 API 호출 |
| `FieldMappingNode` | 데이터 필드 변환/매핑 |
| `ConditionNode` | RSI, MACD 등 전략 조건 판단 |
| `IfNode` | 조건에 따라 분기 |

> **사용 불가**: `OverseasStockRealMarketDataNode` 등 "Real"이 붙은 실시간 노드는 WebSocket 연결이 필요하여 NodeRunner에서 지원하지 않습니다. 실시간 데이터가 필요하면 [워크플로우](structure.md)를 사용하세요.

---

## 7. 종목 코드(symbols) 입력 방법

시세/펀더멘털 노드에 종목을 전달할 때는 반드시 **배열(리스트)** 형태로, `symbol`과 `exchange`를 함께 지정합니다.

```python
# 한 종목
symbols=[{"symbol": "AAPL", "exchange": "NASDAQ"}]

# 여러 종목
symbols=[
    {"symbol": "AAPL", "exchange": "NASDAQ"},
    {"symbol": "MSFT", "exchange": "NASDAQ"},
    {"symbol": "AMZN", "exchange": "NASDAQ"},
]
```

### 주요 거래소 코드

| 거래소 | exchange 코드 | 대표 종목 |
|--------|:---:|------|
| 나스닥 | `NASDAQ` | AAPL, MSFT, GOOGL, AMZN, TSLA, META, NVDA |
| 뉴욕증권거래소 | `NYSE` | JPM, V, JNJ, WMT, KO, DIS |
| 아멕스 | `AMEX` | SPY, QQQ, IWM (ETF) |
| 홍콩 | `HKEX` | 0700(텐센트), 9988(알리바바) |
| 도쿄 | `TSE` | 7203(토요타) |

---

## 8. 에러가 발생하면?

### 8.1 기본 동작: 예외 발생

NodeRunner는 기본적으로 에러가 발생하면 **즉시 프로그램을 멈추고 에러 메시지를 보여줍니다**. 이를 통해 문제를 바로 알 수 있습니다.

```python
try:
    result = await runner.run("OverseasStockMarketDataNode",
        credential_id="broker",
        symbols=[{"symbol": "INVALID_SYMBOL", "exchange": "NASDAQ"}],
    )
except RuntimeError as e:
    print(f"에러 발생: {e}")
    # 에러 발생: Node 'OverseasStockMarketDataNode' execution failed: ...
```

### 8.2 에러를 무시하고 계속 진행하고 싶다면

여러 종목을 순회하면서 일부 실패해도 계속 진행하고 싶을 때:

```python
# raise_on_error=False로 설정하면 에러가 발생해도 결과를 반환합니다
runner = NodeRunner(credentials=[...], raise_on_error=False)

result = await runner.run(...)

if "error" in result:
    print(f"실패: {result['error']}")
else:
    print(f"성공: {result}")
```

### 8.3 자주 발생하는 에러

| 에러 메시지 | 원인 | 해결 방법 |
|-------------|------|----------|
| `LS login failed` | App Key 또는 App Secret이 잘못됨 | LS증권 투혼앱에서 API 키를 재확인하세요 |
| `appkey/appsecret not found` | credentials의 data에 키를 안 넣었음 | `"data": {"appkey": "...", "appsecret": "..."}` 확인 |
| `Missing credentials` | credential_id가 일치하지 않음 | `run()`의 credential_id와 credentials의 credential_id가 같은지 확인 |
| `호출 거래건수를 초과` | API 호출 횟수 제한 초과 | 1분 정도 기다린 후 다시 실행하세요 |
| `실시간(WebSocket) 노드` | Real 노드를 실행하려고 함 | Real이 없는 일반 노드를 사용하세요 |

---

## 9. 실전 예제: 종목 스크리닝

여러 종목의 현재가와 펀더멘털을 한번에 조회하고, 내 잔고도 확인하는 종합 예제입니다.

```python
import asyncio
from programgarden import NodeRunner

async def screen_stocks():
    # LS증권 인증 정보 설정
    credentials = [{
        "credential_id": "broker",
        "type": "broker_ls_overseas_stock",
        "data": {
            "appkey": "여기에_앱키",
            "appsecret": "여기에_앱시크릿",
        },
    }]

    # async with를 쓰면 끝날 때 자동 정리
    async with NodeRunner(credentials=credentials) as runner:

        # ── 1) 관심 종목 현재가 조회 ──
        market = await runner.run("OverseasStockMarketDataNode",
            credential_id="broker",
            symbols=[
                {"symbol": "AAPL", "exchange": "NASDAQ"},
                {"symbol": "MSFT", "exchange": "NASDAQ"},
                {"symbol": "GOOGL", "exchange": "NASDAQ"},
                {"symbol": "NVDA", "exchange": "NASDAQ"},
            ],
            fields=["price", "volume", "change_pct"],
        )

        print("=== 현재가 ===")
        for item in market["values"]:
            arrow = "+" if item["change_pct"] >= 0 else ""
            print(f"  {item['symbol']:>6}: ${item['price']:>9,.2f}  "
                  f"({arrow}{item['change_pct']:.2f}%)  "
                  f"거래량 {item['volume']:>10,}")

        # ── 2) 펀더멘털 비교 ──
        fund = await runner.run("OverseasStockFundamentalNode",
            credential_id="broker",
            symbols=[
                {"symbol": "AAPL", "exchange": "NASDAQ"},
                {"symbol": "MSFT", "exchange": "NASDAQ"},
                {"symbol": "GOOGL", "exchange": "NASDAQ"},
                {"symbol": "NVDA", "exchange": "NASDAQ"},
            ],
            fields=["per", "eps", "market_cap"],
        )

        print("\n=== 펀더멘털 비교 ===")
        print(f"  {'종목':>6} {'PER':>8} {'EPS':>8} {'시가총액':>18}")
        for item in fund["values"]:
            mc = f"${item['market_cap']:,.0f}"
            print(f"  {item['symbol']:>6} {item['per']:>8.2f} "
                  f"${item['eps']:>7.2f} {mc:>18}")

        # ── 3) 내 잔고 확인 ──
        account = await runner.run("OverseasStockAccountNode",
            credential_id="broker",
        )

        print(f"\n=== 내 보유 종목 ({account['count']}개) ===")
        for pos in account.get("positions", []):
            print(f"  {pos.get('symbol', '?'):>6}: {pos.get('quantity', 0)}주")

# 실행
asyncio.run(screen_stocks())
```

---

## 10. 알아두면 좋은 팁

### 세션 재사용

같은 `runner` 인스턴스로 여러 노드를 실행하면 **LS 로그인을 한 번만** 합니다. 매번 새 `NodeRunner`를 만들면 매번 로그인을 다시 해야 하므로 느려집니다.

```python
# 좋은 방법: runner 하나로 여러 번 실행
async with NodeRunner(credentials=[...]) as runner:
    market = await runner.run("OverseasStockMarketDataNode", ...)   # 첫 실행: 로그인
    account = await runner.run("OverseasStockAccountNode", ...)     # 두 번째: 로그인 생략 (빠름)
    fund = await runner.run("OverseasStockFundamentalNode", ...)    # 세 번째: 로그인 생략 (빠름)
```

### 어떤 노드가 있는지 확인

```python
runner = NodeRunner()
for name in runner.list_node_types():
    print(name)
```

### 노드에 어떤 설정을 넣을 수 있는지 확인

```python
runner = NodeRunner()
schema = runner.get_node_schema("OverseasStockMarketDataNode")
print(schema)
```

---

## 다음 단계

NodeRunner로 데이터 조회에 익숙해졌다면, 다음으로 넘어가세요:

- [워크플로우 구조 이해](structure.md) — 여러 노드를 연결해서 자동매매 전략 만들기
- [전체 노드 레퍼런스](node_reference.md) — 72개 노드의 상세 설명
- [종목조건 플러그인](strategies/stock_condition.md) — RSI, MACD, 볼린저밴드 등 77개 전략
