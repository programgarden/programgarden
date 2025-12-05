# ProgramGarden DSL 커스터마이징 가이드

## 1. 개요
ProgramGarden DSL(Domain Specific Language)은 투자 자동화를 위한 전략 정의, 조건 실행, 주문 모듈을 선언적으로 기술할 수 있도록 설계된 설정 언어입니다. 해외 주식(`overseas_stock`)과 해외 선물(`overseas_futures`) 상품군을 동시에 지원하며, `programgarden-core` 패키지의 베이스 클래스를 확장해 자신만의 전략 로직을 파이썬으로 작성한 뒤 DSL에 매핑하면 즉시 실행할 수 있습니다. 이 문서는 외부 개발자가 ProgramGarden DSL을 이해하고 확장할 수 있도록 최신 코어 코드명 변경 사항과 해외선물 기능 추가 내용을 반영해 정리했습니다.

## 2. DSL 전반 구조 이해하기
ProgramGarden은 하나의 `system` 딕셔너리를 입력으로 받아 전략을 실행합니다. 이 딕셔너리는 다음 네 개의 최상위 섹션으로 구성됩니다.

| 섹션 | 필수 여부 | 설명 |
|------|-----------|------|
| `settings` | 필수 | 시스템 ID, 작성자, 디버그 옵션 등 메타데이터 |
| `securities` | 필수 | 연결할 증권사, 상품(`overseas_stock` 또는 `overseas_futures`), 인증 정보 |
| `strategies` | 선택 | 조건 실행 및 주문 연동 로직. 미지정 시 주문을 직접 호출하는 형태로 사용 가능 |
| `orders` | 선택 | 주문 전략 정의. `strategies`에서 참조하거나 직접 실행할 수 있음 |

> 참고: `programgarden_core.alias_resolver.normalize_system_config`가 한글 키를 자동으로 영문 표준 키로 치환합니다. 예를 들어 `"설정"` → `"settings"`, `"전략ID"` → `"id"`로 변환되므로 한글 DSL도 그대로 사용할 수 있습니다.

### 2.1 settings
```json
{
  "settings": {
    "system_id": "custom_example_001",
    "name": "커스텀 전략 시스템",
    "description": "해외 주식·선물 통합 전략",
    "version": "1.0.0",
    "author": "Your Name",
    "date": "2025-11-02",
    "debug": "DEBUG",
    "dry_run_mode": "test",
    "perf_thresholds": {
      "max_avg_cpu_percent": 80,
      "max_memory_delta_mb": 256
    }
  }
}
```
`debug` 값은 `TRACE`, `DEBUG`, `INFO`, `WARN`, `ERROR` 중 선택할 수 있으며 실행 내용을 보고 싶다면 실행 로그 레벨을 추가하면 됩니다. 그게 아니라면 debug는 빈값으로 두면 됩니다.

#### 드라이런 및 성능 가드 옵션
`settings` 블록에서 실행 정책을 바로 제어할 수 있습니다.

- `dry_run_mode`:
  - `test`: 조건 계산과 성능 측정만 수행하고 주문은 전송하지 않습니다. 한 번이라도 성공하면 자동으로 `live`로 승격되며 `safe_to_live` 성격의 퍼포먼스 이벤트가 발생합니다.
  - `live`(기본값): 기존과 동일하게 실주문을 즉시 전송합니다.
  - `guarded_live`: 실주문은 전송하되, `perf_thresholds`를 초과하면 즉시 중단하며 `PerformanceExceededException`을 사용자 코드로 전달합니다.

- `perf_thresholds`:
  - `max_avg_cpu_percent`: 평균 CPU %, 초과 시 실행 중단
  - `max_memory_delta_mb`: RSS 증가치(MB), 초과 시 중단

임계치를 넘어서면 `pg.on_performance_message`로 전달되는 콜백 payload에 `status="throttled"`가 포함되어 시스템 중단 이벤트를 바로 감지할 수 있습니다.

### 2.2 securities
```json
{
  "securities": {
    "company": "ls",
    "product": "overseas_futures",
    "appkey": "...",
    "appsecretkey": "...",
    "paper_trading": true
  }
}
```
`product`는 반드시 `overseas_stock` 또는 `overseas_futures` 중 하나여야 합니다.

### 2.3 strategies
전략 블록은 조건을 일정 주기로 실행하고 조건 결과를 주문 전략에 연결합니다.
```json
{
  "strategies": [
    {
      "id": "condition_market_analysis",
      "description": "시장 분석",
      "schedule": "0 */15 * * * *",
      "timezone": "Asia/Seoul",
      "logic": "at_least",
      "threshold": 1,
      "symbols": [
        {"symbol": "TSLA", "name": "테슬라", "exchange": "82"},
        {"symbol": "NVDA", "name": "엔비디아", "exchange": "82"}
      ],
      "order_id": "split_order_stock",
      "conditions": [
        {"condition_id": "SMAGoldenDeadCross", "params": {"short_period": 5, "long_period": 20}}
      ]
    }
  ]
}
```
`logic`에는 `and`, `or`, `xor`, `at_least`, `weighted` 등 조건 집계 연산자를 지정할 수 있습니다. 해외선물 조건이 하나라도 있는 경우 `position_side`를 기반으로 추가 검증이 수행되며, 규칙은 다음과 같습니다:
- `long` 또는 `short`: 방향을 결정하는 조건입니다. 모든 방향 조건이 동일한 방향이어야 주문이 실행됩니다.
- `neutral`: 방향 결정에 관여하지 않고 다른 조건에 위임합니다. 변동성, 거래량 등 필터 조건에 적합합니다.
- `flat`: 조건은 통과했지만 진입 신호가 없음을 의미하며, 하나라도 `flat`이 있으면 전체가 실패 처리됩니다.
- 해외선물 조건이 모두 `neutral`이면 방향을 결정할 수 없어 주문이 실행되지 않습니다.

- `DictConditionType` 형태의 조건에서 `"weight"` 필드를 작성하면, 커뮤니티 플러그인이 반환하는 기본 weight 대신 해당 값이 그대로 사용됩니다. 전략별로 동일한 플러그인에 서로 다른 비중을 줄 수 있습니다.

### 2.4 orders
주문 전략은 조건 또는 외부 트리거가 호출할 실제 주문 실행 로직을 지정합니다.
```json
{
  "orders": [
    {
      "order_id": "split_order_stock",
      "description": "해외주식 균등 분할",
      "order_time": {
        "start": "09:00:00",
        "end": "15:00:00",
        "days": ["mon", "tue", "wed", "thu", "fri"],
        "timezone": "Asia/Seoul",
        "behavior": "defer",
        "max_delay_seconds": 3600
      },
      "condition": {
        "condition_id": "StockSplitFunds",
        "params": {"percent_balance": 10.0, "max_symbols": 5}
      }
    },
    {
      "order_id": "futures_new_long",
      "description": "선물 신규 진입",
      "condition": "OrderNewTest"
    }
  ]
}
```
`condition`에는 두 가지 형태를 사용할 수 있습니다.
- 딕셔너리: `condition_id`로 등록된 주문 전략을 plugin resolver가 찾아 로딩합니다.
- 클래스/인스턴스: 직접 작성한 파이썬 클래스 인스턴스를 넣을 수 있으며, 이 경우 DSL 로더가 그대로 활용합니다.

## 3. programgarden-core 베이스 클래스 정리 (2025)
해외선물 지원과 함께 코어 베이스 클래스 명칭이 정리되었습니다. 주요 클래스는 모두 `programgarden_core`에서 임포트할 수 있습니다.

### 3.1 조건(Condition) 계층
| 클래스 | 상품군 | 상속해야 할 상황 | 필수 구현 |
|--------|--------|------------------|-----------|
| `BaseStrategyConditionOverseasStock` | overseas_stock | 해외 주식 종목 조건 분석 | `execute()` 반환형: `BaseStrategyConditionResponseOverseasStockType` |
| `BaseStrategyConditionOverseasFutures` | overseas_futures | 해외 선물 종목 조건 분석 | `execute()` 반환형: `BaseStrategyConditionResponseOverseasFuturesType` |

공통 특징:
- `self.symbol`에 현재 평가 중인 종목 정보가 주입됩니다.
- `self.system_id`로 실행 중인 시스템 식별자를 조회할 수 있습니다.
- 응답(`success`, `symbol`, `exchcd`, `data`, `weight`) 구조는 TypedDict로 강제됩니다.
- 선물 조건은 반드시 `position_side`(`"long"`, `"short"`, `"flat"`, `"neutral"`)를 설정해야 합니다.
  - `long`/`short`: 해당 방향으로 주문 진행
  - `neutral`: 방향 결정을 다른 조건에 위임 (변동성, 거래량 등 필터 조건용)
  - `flat`: 조건은 통과했지만 진입 신호 없음 → 실패 처리

### 3.2 주문(Order) 계층
| 클래스 | 상품군 | 역할 | 반환 TypedDict |
|--------|--------|------|----------------|
| `BaseNewOrderOverseasStock` | overseas_stock | 신규 매수/매도 주문 | `BaseNewOrderOverseasStockResponseType` |
| `BaseModifyOrderOverseasStock` | overseas_stock | 정정 주문 | `BaseModifyOrderOverseasStockResponseType` |
| `BaseCancelOrderOverseasStock` | overseas_stock | 취소 주문 | `BaseCancelOrderOverseasStockResponseType` |
| `BaseNewOrderOverseasFutures` | overseas_futures | 선물 신규 주문 | `BaseNewOrderOverseasFuturesResponseType` |
| `BaseModifyOrderOverseasFutures` | overseas_futures | 선물 정정 | `BaseModifyOrderOverseasFuturesResponseType` |
| `BaseCancelOrderOverseasFutures` | overseas_futures | 선물 취소 | `BaseCancelOrderOverseasFuturesResponseType` |

공통 메소드:
- `__init__`: `super().__init__()` 호출. 내부에서 `available_symbols`, `held_symbols`, `non_traded_symbols`, `dps`(예수금), `system_id`를 제공합니다.
- `execute()`: 주문 메시지 리스트를 반환하는 비동기 메소드. 반환 리스트가 비어 있으면 주문이 실행되지 않습니다.
- `on_real_order_receive(order_type, response)`: 실시간 주문 이벤트를 처리합니다. `order_type`은 `submitted_new_buy`, `filled_new_sell` 등으로 들어옵니다.

## 4. 컨디션 구현 단계
1. `programgarden_core`에서 필요한 베이스 클래스와 응답 타입을 임포트합니다.
2. 고유 `id`와 `description`, `securities` 목록을 정의합니다.
3. `__init__`에서 추가 파라미터를 설정하고 반드시 `super().__init__()`를 호출합니다.
4. `execute()` 내에서 `self.symbol` 정보를 사용해 조건 검증을 수행합니다.
5. 검증에 통과되면 success를 `True`로 설정하고, 그렇지 않으면 `False`로 설정합니다. 그래야만 해당 조건에 대해서는 내부적으로 조건의 통과 여부를 인지합니다.
5. 결과 TypedDict를 반환합니다.

### 4.1 해외 주식 조건 예시
```python
from programgarden_core import (
    BaseStrategyConditionOverseasStock,
    BaseStrategyConditionResponseOverseasStockType,
)

class SMAGoldenDeadCross(BaseStrategyConditionOverseasStock):
    id = "SMAGoldenDeadCross"
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
        }
```

### 4.2 해외 선물 조건 예시
```python
from programgarden_core import (
    BaseStrategyConditionOverseasFutures,
    BaseStrategyConditionResponseOverseasFuturesType,
)

class MomentumWithPosition(BaseStrategyConditionOverseasFutures):
    id = "MomentumWithPosition"
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

#### 방향 중립(neutral) 조건 예시 - 변동성 필터
변동성이나 거래량 같은 필터 조건은 방향을 결정하지 않고 다른 조건에 위임해야 합니다. 이 경우 `position_side`를 `"neutral"`로 설정합니다.

```python
class VolatilityFilter(BaseStrategyConditionOverseasFutures):
    id = "VolatilityFilter"
    description = "변동성 필터 - 방향 결정에 관여하지 않음"
    securities = ["ls-sec.co.kr"]

    def __init__(self, min_volatility: float = 0.02):
        super().__init__()
        self.min_volatility = min_volatility

    async def execute(self) -> BaseStrategyConditionResponseOverseasFuturesType:
        symbol = self.symbol or {}
        current_volatility = 0.03  # 실제로는 변동성 계산 로직
        is_volatile_enough = current_volatility >= self.min_volatility
        return {
            "condition_id": self.id,
            "success": is_volatile_enough,
            "symbol": symbol.get("symbol", ""),
            "exchcd": symbol.get("exchcd", ""),
            "data": {"volatility": current_volatility},
            "weight": 1 if is_volatile_enough else 0,
            "product": "overseas_futures",
            "position_side": "neutral",  # 방향 결정을 다른 조건에 위임
        }
```

이렇게 `neutral`을 사용하면 여러 조건을 조합할 때 유연하게 구성할 수 있습니다:
- 모멘텀 조건 (`long`/`short`) + 변동성 필터 (`neutral`) → 변동성이 충분하고 모멘텀 방향이 결정되면 해당 방향으로 주문
- 모든 조건이 `neutral`이면 방향을 알 수 없어 주문이 실행되지 않습니다.

`position_side`가 `flat`이면 `success`가 자동으로 거짓으로 처리되어 주문이 실행되지 않습니다.

## 5. 주문 전략 구현하기
주문 전략은 계좌 잔고·보유 종목·미체결 주문 등의 정보를 활용해 실제 주문 메시지를 만듭니다. ProgramGarden 실행기는 `available_symbols`, `held_symbols`, `non_traded_symbols`, `dps`를 자동 주입하므로 `execute()`에서 바로 사용할 수 있습니다.

### 5.1 해외 주식 신규 주문 예시
```python
from typing import List
from programgarden_core import (
    BaseNewOrderOverseasStock,
    BaseNewOrderOverseasStockResponseType,
)

class StockSplitFunds(BaseNewOrderOverseasStock):
    id = "StockSplitFunds"
    description = "예수금 균등 분할 매수"
    securities = ["ls-sec.co.kr"]
    order_types = ["new_buy", "new_sell"]

    def __init__(self, percent_balance: float = 10.0, max_symbols: int = 5,):
        super().__init__()
        self.percent_balance = percent_balance
        self.max_symbols = max_symbols

    async def execute(self) -> List[BaseNewOrderOverseasStockResponseType]:
        if not self.available_symbols:
            return []
        budget = (self.dps or [{}])[0].get("fcurr_ord_able_amt", 0) * (self.percent_balance / 100)
        per_symbol = budget / min(len(self.available_symbols), self.max_symbols or 1)
        orders: List[BaseNewOrderOverseasStockResponseType] = []
        for symbol in self.available_symbols[: self.max_symbols]:
            unit_price = symbol.get("unit_price") or symbol.get("ovrs_ord_prc") or 1
            quantity = max(int(per_symbol // unit_price) or 0, 1)
            orders.append({
                "success": True,
                "ord_ptn_code": "02",
                "ord_mkt_code": symbol.get("exchcd", "82"),
                "shtn_isu_no": symbol.get("symbol", ""),
                "ord_qty": quantity,
                "ovrs_ord_prc": symbol.get("target_price", unit_price),
                "ordprc_ptn_code": "00",
                "brk_tp_code": "",
                "crcy_code": "USD",
                "pnl_rat": 0.0,
                "pchs_amt": per_symbol,
                "bns_tp_code": "2",
            })
        return orders

    async def on_real_order_receive(self, order_type, response):
        pass
```

### 5.2 해외 선물 신규 주문 예시
```python
from typing import List
from programgarden_core import (
    BaseNewOrderOverseasFutures,
    BaseNewOrderOverseasFuturesResponseType,
)

class OrderNewTest(BaseNewOrderOverseasFutures):
    id = "OrderNewTest"
    description = "선물 신규 진입"
    securities = ["ls-sec.co.kr"]
    order_types = ["new_buy"]

    def __init__(self, price_offset: float = 0.0):
        super().__init__()
        self.price_offset = price_offset

    async def execute(self) -> List[BaseNewOrderOverseasFuturesResponseType]:
        if not self.available_symbols:
            return []
        symbol = self.available_symbols[0]
        target_price = symbol.get("last_price", 0.0) + self.price_offset
        return [{
            "success": True,
            "ord_dt": "20251102",
            "isu_code_val": symbol.get("symbol", ""),
            "futs_ord_tp_code": "1",
            "bns_tp_code": "2",
            "abrd_futs_ord_ptn_code": "2",
            "ovrs_drvt_ord_prc": target_price,
            "cndi_ord_prc": 0.0,
            "ord_qty": 1,
            "exch_code": symbol.get("exchcd", ""),
            "prdt_code": symbol.get("prdt_code", ""),
            "due_yymm": symbol.get("due_yymm", ""),
            "crcy_code": symbol.get("currency_code", ""),
        }]

    async def on_real_order_receive(self, order_type, response):
        pass
```

### 5.3 정정·취소 전략 작성 팁
- 정정/취소 전략도 동일한 패턴으로 작성하되, 응답 TypedDict에서 `org_ord_no`(주식) 또는 `ovrs_futs_org_ord_no`(선물) 같은 필드를 정확히 채워야 합니다.
- `self.non_traded_symbols`에 미체결 주문 리스트가 주입되므로 원하는 주문 번호를 탐색해 정정/취소 대상으로 삼을 수 있습니다.

## 6. DSL에 내가 만든 커스텀 클래스 연결하기
파이썬 모듈에서 작성한 클래스를 DSL에 연결하는 방법은 두 가지입니다.
1. **모듈 경로 등록**: `programgarden`이 커스텀 클래스를 import할 수 있게 패키지를 `programgarden-community` 라이브러리에 공개적으로 전략을 PR하여 관리자에 의해서 반영되면 DSL의 `conditions`/`orders`에 전략 ID를 넣고 이용합니다.
2. **직접 인스턴스 전달**: DSL을 파이썬 코드에서 직접 구성할 때는  클래스 인스턴스를 직접 넣을 수 있습니다. (예: `OrderNewTest()`)

아래 예시는 한 시스템에서 주식과 선물 전략을 각각 실행하는 구조입니다.
```python
from programgarden import Programgarden
from custom.conditions import SMAGoldenDeadCross, MomentumWithPosition
from custom.orders import StockSplitFunds, OrderNewTest

pg = Programgarden()
pg.on_strategies_message(lambda message: print("전략 응답", message))
pg.on_real_order_message(lambda message: print("주문 이벤트", message))
pg.on_error_message(lambda message: print("오류", message))

pg.run(system={
    "settings": {...},
    "securities": {
        "company": "ls",
        "product": "overseas_stock",
        "appkey": "...",
        "appsecretkey": "...",
    },
    "strategies": [
        {
            "id": "stock_strategy",
            "logic": "at_least",
            "threshold": 1,
            "symbols": [{"symbol": "TSLA", "exchcd": "82"}],
            "order_id": "split_order_stock",
            "conditions": [SMAGoldenDeadCross(short_period=5, long_period=20)],
        }
    ],
    "orders": [
        {
            "order_id": "split_order_stock",
            "condition": StockSplitFunds(percent_balance=10.0, max_symbols=3),
        }
    ]
})
```
해외선물 전략도 같은 방식으로 커스텀하면 됩니다.

## 7. 실행, 검증, 디버깅 팁
- **콜백 활용**: `on_strategies_message`, `on_real_order_message`, `on_error_message`를 이용해 실행 결과를 실시간으로 모니터링하세요.
- **로컬 샌드박스**: `paper_trading`을 `True`로 두고 LS증권 모의투자 API KEY 이용하여 로직을 검증한 뒤 실거래 키로 전환합니다.
- **로깅**: `programgarden_core.logs`에 정의된 로거(`condition_logger`, `order_logger`, `system_logger`)를 사용하면 DSL 파이프라인의 각 단계별 상태를 추적할 수 있습니다.
- **에러 처리**: 예외 발생 시 `programgarden_core.exceptions`에 정의된 도메인 예외(`ConditionExecutionException`, `NotExistSystemKeyException` 등)를 참고하여 원인을 파악하세요.

## 8. 가장 유의할 점
- **형식 준수**: TypedDict 스펙을 지켜 반환하지 않으면 런타임에서 키 에러 또는 검증 실패가 발생합니다.
- **상태 공유 최소화**: 전략 클래스는 상태를 최소로 유지하고, 실행 시점에 전달되는 컨텍스트(`available_symbols`, `held_symbols`)만 사용하세요.
- **심볼 정규화**: `symbols` 입력에 `exchange`, `name` 등의 별칭을 사용하면 alias resolver가 자동 변환하지만, 가능하면 표준 키(`symbol`, `exchcd`, `product_type`)를 직접 지정하는 것이 안전합니다.
- **포지션 방향**: 해외선물 조건에서 `position_side`를 올바르게 설정해야 합니다:
  - 방향을 결정하는 조건: `long` 또는 `short` 반환
  - 필터 조건 (변동성, 거래량 등): `neutral` 반환 (방향 결정을 다른 조건에 위임)
  - 진입 신호 없음: `flat` 반환 → 전체 실패 처리
  - 모든 조건이 `neutral`이면 방향을 알 수 없어 주문 실패

## 9. 커뮤니티 기여 및 배포
- 재사용 가능한 전략을 배포해서 시스템 트레이딩 생태계 발전에 기여하세요. 직접 커스텀한 전략은 https://github.com/programgarden/programgarden_community 패키지에 PR하면 수 많은 투자자들이 공유하게 됩니다.

---
이 문서를 바탕으로 ProgramGarden DSL을 자신만의 전략에 맞게 커스터마이징하고, 해외 주식과 선물 상품을 안정적으로 운용해보세요.
