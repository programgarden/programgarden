# ProgramGarden DSL 커스터마이징 가이드

## 1. 개요

ProgramGarden DSL(Domain Specific Language)은 투자 자동화를 위한 **노드 기반 워크플로우**를 정의하는 설정 언어입니다. 해외 주식(`overseas_stock`)과 해외 선물(`overseas_futures`) 상품군을 지원하며, `programgarden-core` 패키지의 베이스 클래스를 확장해 자신만의 플러그인을 파이썬으로 작성할 수 있습니다.

이 문서는 개발자가 ProgramGarden DSL을 이해하고 커스텀 플러그인을 만들 수 있도록 작성되었습니다.

---

## 2. 노드 그래프 구조 이해하기

ProgramGarden은 JSON 직렬화 가능한 노드 그래프 기반 DSL을 사용합니다.

### 2.1 기본 구조

```json
{
  "nodes": [
    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "my-cred"},
    {"id": "rsi", "type": "ConditionNode", "plugin": "RSI", "fields": {...}},
    {"id": "order", "type": "OverseasStockNewOrderNode", "plugin": "MarketOrder", "fields": {...}}
  ],
  "edges": [
    {"from": "broker", "to": "rsi"},
    {"from": "rsi", "to": "order"}
  ]
}
```

### 2.2 nodes 배열

각 노드는 다음 필드를 가집니다:

| 필드 | 필수 | 설명 |
|------|:----:|------|
| `id` | ✓ | 고유 식별자 (워크플로우 내 중복 불가) |
| `type` | ✓ | 노드 타입 (OverseasStockBrokerNode, ConditionNode 등) |
| `credential_id` | | Broker 노드용 인증 정보 ID |
| `plugin` | | 사용할 플러그인 ID (ConditionNode, NewOrderNode 등) |
| `fields` | | 플러그인에 전달할 파라미터 |
| `position` | | 클라이언트 UI용 위치 정보 `{"x": 400, "y": 200}` |

### 2.3 edges 배열

노드 간 실행 순서를 정의합니다:

```json
{
  "from": "sourceNodeId",
  "to": "targetNodeId"
}
```

- **DAG 기반**: 엣지는 노드 ID 간 연결로, 실행 순서(DAG)를 결정합니다
- **Multiple 연결**: 하나의 노드에서 여러 노드로 연결 가능
- **엣지 타입**: `main` (기본, 실행 순서), `ai_model` (LLM 연결), `tool` (AI Agent 도구 등록)

### 2.4 inputs 섹션

워크플로우에 전달할 입력 파라미터를 정의합니다:

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
  "nodes": [...],
  "edges": [...]
}
```

입력 파라미터는 `{{ input.xxx }}` 문법으로 노드 설정에서 참조합니다.

### 2.5 Expression 문법

노드 설정값을 동적으로 계산할 때 Jinja2 스타일의 `{{ }}` 문법을 사용합니다:

```json
{
  "id": "watchlist",
  "type": "WatchlistNode",
  "symbols": "{{ input.symbols }}"
},
{
  "id": "historicalData",
  "type": "OverseasStockHistoricalDataNode",
  "start_date": "{{ date.ago(30) }}",
  "end_date": "{{ date.today() }}"
}
```

#### 지원 기능

| 기능 | 예시 |
|------|------|
| 입력 변수 참조 | `{{ input.symbols }}` |
| 산술 연산 | `{{ price * 0.99 }}` |
| 날짜 함수 | `{{ date.today() }}`, `{{ date.ago(7) }}` |
| 통계 함수 | `{{ stats.avg(prices) }}`, `{{ stats.median(values) }}` |
| 금융 함수 | `{{ finance.pct_change(100, 110) }}` → `10.0` |
| 조건 표현식 | `{{ "buy" if rsi < 30 else "hold" }}` |

> 📖 **상세 가이드**: [Expression 가이드](expression_guide.md)에서 모든 내장 함수와 사용법을 확인하세요.

---

## 3. 노드 타입별 상세

### 3.1 인프라 노드 (infra)

#### BrokerNode

증권사 연결을 담당합니다. 상품별로 분리되어 있습니다.

```json
{
  "id": "broker",
  "type": "OverseasStockBrokerNode",
  "credential_id": "my-cred"
}
```

> **참고**: Broker 연결은 Executor가 DAG 순회를 통해 자동으로 하위 노드에 주입합니다. 별도의 `connection` 바인딩이 필요 없습니다.

| 상품 | 노드 타입 |
|------|----------|
| 해외주식 | `OverseasStockBrokerNode` |
| 해외선물 | `OverseasFuturesBrokerNode` |

### 3.2 실시간 노드 (realtime)

#### RealMarketDataNode

WebSocket으로 실시간 시세를 수신합니다.

```json
{
  "id": "realMarket",
  "type": "OverseasStockRealMarketDataNode"
}
```

| 입력 | 타입 | 설명 |
|------|------|------|
| `symbols` | symbol_list | 구독할 종목 목록 |

| 출력 | 타입 | 설명 |
|------|------|------|
| `price` | market_data | 실시간 가격 데이터 |
| `volume` | market_data | 실시간 거래량 데이터 |

#### RealAccountNode

실시간 계좌 정보를 제공합니다.

```json
{
  "id": "realAccount",
  "type": "OverseasStockRealAccountNode"
}
```

| 출력 | 타입 | 설명 |
|------|------|------|
| `held_symbols` | symbol_list | 보유종목 코드 리스트 |
| `balance` | balance_data | 예수금/매수가능금액 |
| `open_orders` | order_list | 미체결 주문 목록 |
| `positions` | position_data | 보유종목 상세 (실시간 수익률 포함) |

**positions 상세 구조:**

```json
{
  "AAPL": {
    "symbol": "AAPL",
    "quantity": 10,
    "buy_price": 185.50,
    "current_price": 190.25,
    "pnl_amount": 42.50,
    "pnl_rate": 2.29,
    "realtime_pnl": {
      "gross_profit_foreign": 47.50,
      "net_profit_foreign": 42.50,
      "total_fee_foreign": 5.00,
      "return_rate_percent": 2.29
    }
  }
}
```

### 3.3 조건 노드 (condition)

#### ConditionNode

조건 플러그인을 실행합니다.

```json
{
  "id": "rsi",
  "type": "ConditionNode",
  "plugin": "RSI",
  "fields": {
    "period": 14,
    "oversold": 30
  }
}
```

| 입력 | 타입 | 설명 |
|------|------|------|
| `trigger` | signal | 실행 트리거 |
| `price_data` | market_data | 가격 데이터 |
| `symbols` | symbol_list | 평가할 종목 목록 |

| 출력 | 타입 | 설명 |
|------|------|------|
| `result` | condition_result | 조건 평가 결과 |
| `passed_symbols` | symbol_list | 조건 통과 종목 |

#### LogicNode

여러 조건을 조합합니다.

```json
{
  "id": "logic",
  "type": "LogicNode",
  "operator": "at_least",
  "threshold": 2,
  "conditions": [
    {"is_condition_met": "{{ nodes.cond1.result }}", "passed_symbols": "{{ nodes.cond1.passed_symbols }}"},
    {"is_condition_met": "{{ nodes.cond2.result }}", "passed_symbols": "{{ nodes.cond2.passed_symbols }}"}
  ]
}
```

| operator | 설명 | threshold 필요 |
|----------|------|:--------------:|
| `all` | 모든 조건 만족 (AND) | ✗ |
| `any` | 하나 이상 만족 (OR) | ✗ |
| `not` | 모든 조건 불만족 | ✗ |
| `xor` | 정확히 하나만 만족 | ✗ |
| `at_least` | N개 이상 만족 | ✓ |
| `at_most` | N개 이하 만족 | ✓ |
| `exactly` | 정확히 N개 만족 | ✓ |
| `weighted` | 가중치 합이 threshold 이상 | ✓ |

### 3.4 주문 노드 (order)

#### NewOrderNode

신규 주문을 실행합니다.

```json
{
  "id": "order",
  "type": "OverseasStockNewOrderNode",
  "plugin": "MarketOrder",
  "fields": {
    "side": "buy",
    "amount_type": "percent_balance",
    "amount": 10
  }
}
```

| 입력 | 타입 | 설명 |
|------|------|------|
| `symbols` | symbol_list | 주문할 종목 |
| `held_symbols` | symbol_list | 보유 종목 (중복 방지용) |
| `balance` | balance_data | 예수금 정보 |

#### ModifyOrderNode / CancelOrderNode

미체결 주문 정정/취소를 담당합니다.

```json
{
  "id": "modifyOrder",
  "type": "OverseasStockModifyOrderNode",
  "plugin": "TrailingStop",
  "fields": {
    "price_gap_percent": 0.5
  }
}
```

| 입력 | 타입 | 설명 |
|------|------|------|
| `target_orders` | order_list | 대상 주문 (RealAccountNode.open_orders에서 연결) |
| `price_data` | market_data | 현재 가격 데이터 |

---

## 4. 플러그인 개발

### 4.1 플러그인 반환 구조 (PluginResult)

모든 플러그인은 `PluginResult` 타입을 반환합니다.

```python
class PluginResult(TypedDict):
    passed: bool              # 조건 충족 여부
    value: Any                # 계산된 값 (예: RSI 28.5)
    symbol: str               # 평가된 종목
    analysis: AnalysisData    # 분석 데이터 (시각화용)
```

**analysis 상세 구조:**

```json
{
  "passed": true,
  "value": 28.5,
  "symbol": "AAPL",
  "analysis": {
    "indicator": "RSI",
    "period": 14,
    "threshold": 30,
    "direction": "below",
    "comparison": "RSI < 30 → passed"
  }
}
```

**조건 플러그인 전체 반환 구조:**

```json
{
  "passed_symbols": [{"exchange": "NASDAQ", "symbol": "AAPL"}],
  "failed_symbols": [{"exchange": "NASDAQ", "symbol": "NVDA"}],
  "symbol_results": [
    {"symbol": "AAPL", "exchange": "NASDAQ", "rsi": 28.5, "current_price": 192.30},
    {"symbol": "NVDA", "exchange": "NASDAQ", "rsi": 65.2, "current_price": 450.50}
  ],
  "values": [
    {
      "symbol": "AAPL",
      "exchange": "NASDAQ",
      "time_series": [
        {"date": "20251224", "open": 272.34, "high": 275.43, "low": 272.19, "close": 273.81, "volume": 17910574, "rsi": 33.54},
        {"date": "20251225", "open": 274.00, "high": 276.50, "low": 273.00, "close": 275.20, "volume": 15000000, "rsi": 28.50}
      ]
    }
  ],
  "result": true,
  "analysis": {...}
}
```

| 필드 | 설명 |
|------|------|
| `passed_symbols` | 조건 통과 종목 (거래소 정보 포함) |
| `failed_symbols` | 조건 미통과 종목 |
| `symbol_results` | 종목별 계산 결과 (RSI 값, 현재가 등) |
| `values` | 종목별 그룹화된 시계열 데이터 (DisplayNode 차트용) |
| `result` | 조건 통과 여부 (passed_symbols > 0) |

### 4.2 조건 플러그인 (ConditionNode용)

조건 플러그인은 **필요 데이터 타입**에 따라 두 종류로 나뉩니다:

| 플러그인 타입 | required_data | 필수 입력 | 예시 |
|--------------|---------------|----------|------|
| 시계열 기반 | `["data"]` | OHLCV 배열 | RSI, MACD, BollingerBands |
| 포지션 기반 | `["positions"]` | 포지션 데이터 (pnl_rate 포함) | ProfitTarget, StopLoss |

#### 시계열 기반 플러그인 예시 (RSI)

```python
from programgarden_core import (
    BaseStrategyConditionOverseasStock,
    BaseStrategyConditionResponseOverseasStockType,
)

class RSI(BaseStrategyConditionOverseasStock):
    id = "RSI"
    version = "1.0.0"
    description = "상대강도지수 조건"
    securities = ["ls-sec.co.kr"]
    required_data = ["data"]  # OHLCV 시계열 데이터 필요

    def __init__(self, period: int = 14, oversold: float = 30):
        super().__init__()
        self.period = period
        self.oversold = oversold

    async def execute(self) -> BaseStrategyConditionResponseOverseasStockType:
        # self.data에서 OHLCV 데이터 접근
        # RSI 계산 후 조건 평가
        return {...}
```

#### 포지션 기반 플러그인 예시 (ProfitTarget v3.0.0)

```python
from programgarden_core import (
    BaseStrategyConditionOverseasStock,
    BaseStrategyConditionResponseOverseasStockType,
)

class ProfitTarget(BaseStrategyConditionOverseasStock):
    id = "ProfitTarget"
    version = "3.0.0"
    description = "목표 수익률 도달 조건"
    securities = ["ls-sec.co.kr"]
    required_data = ["positions"]  # 포지션 데이터만 필요 (시계열 불필요)

    def __init__(self, target_percent: float = 5.0):
        super().__init__()
        self.target_percent = target_percent

    async def execute(self) -> BaseStrategyConditionResponseOverseasStockType:
        # self.positions에서 직접 pnl_rate 확인
        # positions = {"AAPL": {"qty": 10, "pnl_rate": 5.5}, ...}
        passed_symbols = []
        for symbol, pos in (self.positions or {}).items():
            pnl_rate = pos.get("pnl_rate", 0)
            if pnl_rate >= self.target_percent:
                passed_symbols.append({"symbol": symbol, "exchange": pos.get("exchange", "")})
        
        return {
            "condition_id": self.id,
            "success": len(passed_symbols) > 0,
            "passed_symbols": passed_symbols,
            "data": {"target": self.target_percent},
            "product": "overseas_stock",
        }
```

> **v3.0.0 변경사항**: ProfitTarget/StopLoss 플러그인은 `positions` 데이터의 `pnl_rate`를 직접 사용합니다.
> 시계열 데이터(data)를 통한 수익률 계산이 불필요하여 훨씬 간단해졌습니다.

#### 해외 주식 시계열 조건 예시

```python
from programgarden_core import (
    BaseStrategyConditionOverseasStock,
    BaseStrategyConditionResponseOverseasStockType,
)

class SMAGoldenDeadCross(BaseStrategyConditionOverseasStock):
    id = "SMAGoldenDeadCross"
    version = "1.0.0"
    description = "단기·장기 이동평균 골든/데드 크로스"
    securities = ["ls-sec.co.kr"]

    def __init__(self, short_period: int = 5, long_period: int = 20):
        super().__init__()
        self.short_period = short_period
        self.long_period = long_period

    async def execute(self) -> BaseStrategyConditionResponseOverseasStockType:
        symbol = self.symbol or {}
        # 가격 데이터를 조회하고 SMA를 계산한 결과로 대체하세요.
        is_cross = True
        return {
            "condition_id": self.id,
            "success": is_cross,
            "symbol": symbol.get("symbol", ""),
            "exchcd": symbol.get("exchcd", ""),
            "data": {"short": self.short_period, "long": self.long_period},
            "weight": 1 if is_cross else 0,
            "product": "overseas_stock",
            "analysis": {
                "time_series": [...],
                "threshold": {"value": 0, "direction": "cross"},
            },
        }
```

#### 해외 선물 조건 예시

```python
from programgarden_core import (
    BaseStrategyConditionOverseasFutures,
    BaseStrategyConditionResponseOverseasFuturesType,
)

class MomentumWithPosition(BaseStrategyConditionOverseasFutures):
    id = "MomentumWithPosition"
    version = "1.0.0"
    description = "선물 모멘텀 + 포지션 방향성"
    securities = ["ls-sec.co.kr"]

    def __init__(self, threshold: float = 0.8):
        super().__init__()
        self.threshold = threshold

    async def execute(self) -> BaseStrategyConditionResponseOverseasFuturesType:
        symbol = self.symbol or {}
        momentum_score = 0.9
        position_side = "long" if momentum_score >= self.threshold else "short" if momentum_score <= -self.threshold else "flat"
        return {
            "condition_id": self.id,
            "success": position_side in {"long", "short"},
            "symbol": symbol.get("symbol", ""),
            "exchcd": symbol.get("exchcd", ""),
            "data": {"momentum": momentum_score},
            "weight": round(abs(momentum_score), 2),
            "product": "overseas_futures",
            "position_side": position_side,
        }
```

#### position_side 규칙 (해외선물 전용)

| 값 | 설명 |
|----|------|
| `long` | 매수 방향 |
| `short` | 매도 방향 |
| `neutral` | 방향 결정에 관여하지 않음 (필터 조건용) |
| `flat` | 진입 신호 없음 → 실패 처리 |

- 모든 조건이 `neutral`이면 방향을 결정할 수 없어 주문 실행 안 됨
- `flat`이 하나라도 있으면 전체 실패 처리

### 4.3 주문 플러그인 (NewOrderNode용)

#### 해외 주식 신규 주문 예시

```python
from typing import List
from programgarden_core import (
    BaseNewOrderOverseasStock,
    BaseNewOrderOverseasStockResponseType,
)

class StockSplitFunds(BaseNewOrderOverseasStock):
    id = "StockSplitFunds"
    version = "1.0.0"
    description = "예수금 균등 분할 매수"
    securities = ["ls-sec.co.kr"]
    order_types = ["new_buy", "new_sell"]

    def __init__(self, percent_balance: float = 10.0, max_symbols: int = 5):
        super().__init__()
        self.percent_balance = percent_balance
        self.max_symbols = max_symbols

    async def execute(self) -> List[BaseNewOrderOverseasStockResponseType]:
        if not self.available_symbols:
            return []
        
        budget = (self.dps or [{}])[0].get("fcurr_ord_able_amt", 0) * (self.percent_balance / 100)
        per_symbol = budget / min(len(self.available_symbols), self.max_symbols or 1)
        
        orders: List[BaseNewOrderOverseasStockResponseType] = []
        for symbol in self.available_symbols[:self.max_symbols]:
            unit_price = symbol.get("unit_price") or symbol.get("ovrs_ord_prc") or 1
            quantity = max(int(per_symbol // unit_price), 1)
            orders.append({
                "success": True,
                "ord_ptn_code": "02",
                "ord_mkt_code": symbol.get("exchcd", "82"),
                "shtn_isu_no": symbol.get("symbol", ""),
                "ord_qty": quantity,
                "ovrs_ord_prc": symbol.get("target_price", unit_price),
                "ordprc_ptn_code": "00",
                "crcy_code": "USD",
                "bns_tp_code": "2",
            })
        return orders

    async def on_real_order_receive(self, order_type: str, response: dict):
        # 실시간 주문 이벤트 처리
        pass
```

### 4.4 플러그인 클래스 필수 필드

| 필드 | 타입 | 설명 |
|------|------|------|
| `id` | str | 플러그인 고유 ID |
| `version` | str | 버전 (예: "1.0.0") |
| `description` | str | 설명 |
| `securities` | List[str] | 지원 증권사 |
| `parameter_schema` | dict | Pydantic 모델의 JSON Schema (선택) |

---

## 5. DSL에 커스텀 플러그인 연결하기

### 5.1 모듈 경로 등록

`programgarden-community`에 PR하여 플러그인을 등록하면 DSL에서 ID로 참조 가능합니다.

```json
{
  "id": "myCondition",
  "type": "ConditionNode",
  "plugin": "MySMACondition",
  "fields": {"short_period": 5, "long_period": 20}
}
```

### 5.2 워크플로우 실행

Python 코드에서 `WorkflowExecutor`를 사용하여 워크플로우를 실행합니다.

```python
from programgarden import WorkflowExecutor

executor = WorkflowExecutor()

workflow = {
    "nodes": [
        {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "my-cred"},
        {"id": "rsi", "type": "ConditionNode", "plugin": "MySMACondition", "fields": {"short_period": 5, "long_period": 20}},
        {"id": "order", "type": "OverseasStockNewOrderNode", "plugin": "MarketOrder", "fields": {"side": "buy"}}
    ],
    "edges": [
        {"from": "broker", "to": "rsi"},
        {"from": "rsi", "to": "order"}
    ],
    "credentials": [...]
}

job = await executor.execute(workflow)
```

---

## 6. 디버깅 팁

### 6.1 ExecutionListener 활용

`ExecutionListener`를 구현하여 워크플로우 실행 이벤트를 수신합니다.

```python
from programgarden_core.bases import BaseExecutionListener

class MyListener(BaseExecutionListener):
    async def on_node_state_change(self, data):
        print(f"노드 상태 변경: {data}")

    async def on_log(self, data):
        print(f"로그: {data}")

    async def on_display_data(self, data):
        print(f"디스플레이: {data}")

executor = WorkflowExecutor()
job = await executor.execute(workflow, listeners=[MyListener()])
```

### 6.2 로깅 설정

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("programgarden")
```

### 6.3 모의투자 모드

실제 주문 없이 테스트 (해외선물만 지원, 해외주식은 LS증권 모의투자 미지원):

```json
{
  "id": "broker",
  "type": "OverseasFuturesBrokerNode",
  "credential_id": "my-cred",
  "paper_trading": true
}
```

> **주의**: `paper_trading`은 credential과 노드 설정 양쪽 모두에 설정해야 합니다.

---

## 7. 주의사항

### 7.1 형식 준수

TypedDict 스펙을 지키지 않으면 런타임 에러가 발생합니다.

### 7.2 상태 공유 최소화

플러그인 클래스는 상태를 최소로 유지하고, 실행 시점에 전달되는 컨텍스트만 사용하세요.

### 7.3 버전 관리

플러그인에 `version` 필드를 반드시 추가하세요. DSL에서 특정 버전을 지정할 수 있습니다:

```json
"plugin": "RSI@1.2.0"
```

### 7.4 analysis 필드

모든 조건 플러그인은 `analysis` 필드를 반환해야 합니다. DisplayNode에서 시각화에 활용됩니다.

| analysis 필드 | DisplayNode 차트 타입 |
|---------------|----------------------|
| `time_series` | line, candlestick |
| `distribution` | bar, radar |
| `threshold` | line (threshold overlay) |
| `comparison` | table |

---

## 8. 커뮤니티 기여

재사용 가능한 플러그인을 https://github.com/programgarden/programgarden_community 에 PR하면 다른 투자자들과 공유할 수 있습니다.

자세한 기여 방법은 [오픈소스 기여 가이드](contribution_guide.md)를 참고하세요.
