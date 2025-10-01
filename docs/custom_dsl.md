# 파이썬으로 DSL 커스텀하기

## 1. 개요

이 가이드는 ProgramGarden의 DSL(Domain Specific Language)을 커스텀하여 자신만의 트레이딩 전략을 개발하는 방법을 설명합니다. 개발자는 Python 클래스를 상속받아 커스텀 컨디션(조건)과 오더 전#### BaseNewOrderOverseasStock 부모 클래스 설명

`BaseNewOrderOverseasStock`은 `BaseOrderOverseasStock`를 상속받아 다음과 같은 추가 속성과 메소드를 제공합니다:

* **속성** (상속 포함):
  * `id`, `description`, `securities`: 클래스 레벨 속성.
  * `available_symbols`: 매매 전략에 사용할 종목 리스트.
  * `held_symbols`: 보유 중인 종목 리스트.
  * `non_traded_symbols`: 미체결 종목 리스트.
  * `fcurr_dps`: 외화 예금 잔고.
  * `fcurr_ord_able_amt`: 외화 주문 가능 금액.
  * `system_id`: 시스템 ID.
* **메소드**:
  * `__init__(**kwargs)`: 초기화. `super().__init__()` 호출, 잔고 속성 초기화.
  * `execute()`: **필수 구현**. 주문 리스트 생성 로직. `List[BaseNewOrderOverseasStockResponseType]` 반환.
  * `on_real_order_receive(order_type, response)`: **필수 구현**. 실시간 주문 응답 처리.

이 메소드들은 프레임워크에서 자동으로 호출되며, 자식 클래스에서 오버라이드할 수 있습니다.

이 클래스를 DSL에서 `"order_id": "StockSplitFunds"`로 사용합니다. 이 가이드를 통해 직접 코드를 작성하고 DSL에 통합하는 방법을 배우게 됩니다.

비개발자를 위한 [퀵스타트 가이드](../invest/non_dev_quick_guide.md)와 달리, 이 가이드는 코드 레벨의 구현을 중점으로 합니다. 예시 코드를 따라하며 자신의 전략을 구축하세요.

\


## 2. 준비 단계

### 2.1. 필요한 패키지 설치

ProgramGarden을 사용하려면 관련 패키지를 설치해야 합니다. 터미널에서 다음 명령어를 실행하세요:

```bash
pip install programgarden programgarden-core programgarden-finance
```

### 2.2. Base 클래스 이해

커스텀 전략을 만들기 위해 다음 base 클래스를 상속받습니다. 
이 클래스들은 `programgarden_core` 패키지에서 제공됩니다.

* **BaseStrategyCondition**: 시장 분석 조건을 정의하는 클래스. `execute` 메소드를 구현하여 조건 평가 로직을 작성합니다.
* **BaseNewOrderOverseasStock**: 해외 주식 신규 매매 전략을 정의하는 클래스. `execute` 메소드를 구현하여 주문 생성 로직을 작성합니다.
* **BaseModifyOrderOverseasStock**: 해외 주식 정정 매매 전략을 정의하는 클래스. `execute` 메소드를 구현하여 주문 생성 로직을 작성합니다.
* **BaseCancelOrderOverseasStock**: 해외 주식 취소 매매 전략을 정의하는 클래스. `execute` 메소드를 구현하여 주문 생성 로직을 작성합니다.


## 3. 커스텀 컨디션 만들기

컨디션은 시장 데이터를 분석하여 특정 조건이 만족되는지 평가하는 로직입니다. `BaseStrategyCondition`을 상속받아 `execute` 메소드를 구현합니다.

### 3.1. 클래스 구조

커스텀 컨디션 클래스는 다음 요소를 포함합니다:

* **id**: 컨디션의 고유 식별자 (문자열).
* **description**: 컨디션 설명.
* **`__init__` 메소드**: 초기화 파라미터 설정.
* **`execute` 메소드**: 비동기 메소드로, 조건 평가 로직 구현. `BaseStrategyConditionResponseType`을 반환.

### 3.2. 예시: SMAGoldenDeadCross 컨디션

이 예시는 이동평균선의 골든 크로스를 감지하는 간단한 컨디션입니다. 실제 구현은 복잡할 수 있지만, 여기서는 기본 구조를 보여줍니다.

```python
class SMAGoldenDeadCross(BaseStrategyCondition):
    id: str = "SMAGoldenDeadCross"
    description: str = "SMA 골든 크로스 감지 컨디션"

    def __init__(self, short_period: int = 5, long_period: int = 20, **kwargs):
        super().__init__()
        self.short_period = short_period
        self.long_period = long_period
        # 추가 초기화...

    async def execute(self) -> BaseStrategyConditionResponseType:
        # 데이터 가져오기 (LS API 또는 다른 소스)
        # SMA 계산 로직
        # 조건 평가
        return {
            "condition_id": self.id,
            "success": True,  # 조건 만족 여부
            "exchange": self.symbol.get("exchcd"),
            "symbol": self.symbol.get("symbol"),
            "data": []  # 추가 데이터
        }
```

#### BaseStrategyCondition 부모 클래스 설명

`BaseStrategyCondition`은 다음과 같은 속성과 메소드를 제공합니다:

* **속성**:
  * `id`: 전략의 고유 ID (클래스 레벨).
  * `description`: 전략 설명 (클래스 레벨).
  * `securities`: 사용 가능한 증권사/거래소 리스트 (클래스 레벨).
  * `symbol`: 현재 분석 중인 종목 정보 (딕셔너리, `{"exchcd": "82", "symbol": "TSLA"}` 형태).
  * `system_id`: 시스템 고유 ID.
* **메소드**:
  * `__init__(**kwargs)`: 초기화. 자식 클래스에서 `super().__init__()` 호출 필요. `self.symbol = None` 설정.
  * `execute()`: **필수 구현**. 비동기로 조건 평가 로직 작성. `BaseStrategyConditionResponseType` 반환.

이 메소드들은 프레임워크에서 자동으로 호출되며, 자식 클래스에서 오버라이드할 수 있습니다.

이 클래스를 DSL에서 `"condition_id": "SMAGoldenDeadCross"`로 참조합니다.

\


## 4. 커스텀 오더 전략 만들기

오더 전략은 조건이 만족되었을 때 실제 주문을 생성하는 로직입니다. 전략은 `BaseNewOrderOverseasStock`, `BaseModifyOrderOverseasStock`, `BaseCancelOrderOverseasStock`을 상속받아 `execute` 메소드를 구현합니다.

### 4.1. 신규 오더 전략 (newOrder)

커스텀 오더 클래스는 다음 요소를 포함합니다:

* **id**: 전략의 고유 식별자.
* **description**: 전략 설명.
* **securities**: 지원하는 증권사 리스트.
* **`__init__` 메소드**: 초기화 파라미터.
* **`execute` 메소드**: 주문 리스트 생성. `List[BaseNewOrderOverseasStockResponseType]` 반환.
* **`on_real_order_receive` 메소드**: 실시간 주문 응답 처리.

### 4.2. 예시: StockSplitFunds 신규 오더 전략

이 예시는 예수금을 균등하게 분할하여 여러 종목을 매수하는 전략입니다. 실제 구현은 복잡할 수 있지만, 여기서는 기본 구조를 보여줍니다.

```python
class StockSplitFunds(BaseNewOrderOverseasStock):
    id: str = "StockSplitFunds"
    description: str = "균등 분할 신규 오더 전략"
    securities: List[str] = ["ls-sec.co.kr"]
    order_types: List[OrderType] = ["new_buy", "new_sell"]

    def __init__(self, percent_balance: float = 10.0, max_symbols: int = 5, **kwargs):
        super().__init__()
        self.percent_balance = percent_balance
        self.max_symbols = max_symbols
        # 추가 초기화...

    async def execute(self) -> List[BaseNewOrderOverseasStockResponseType]:
        # 잔고 계산, 종목별 자금 분배 로직
        # 주문 리스트 생성 (매수 또는 매도)
        return [
            {
                "success": True,
                "ord_ptn_code": "02",  # 매수
                "ord_mkt_code": "82",
                "isu_no": "TSLA",
                "ord_qty": 10,
                "ovrs_ord_prc": 150.0,
                "ordprc_ptn_code": "00",
                "brk_tp_code": "01"
            },
            {
                "success": True,
                "ord_ptn_code": "01",  # 매도
                "ord_mkt_code": "82",
                "shtn_isu_no": "NVDA",
                "ord_qty": 5,
                "ovrs_ord_prc": 160.0,
                "ordprc_ptn_code": "00",
                "crcy_code": "USD"
            }
            # 추가 주문들...
        ]

    async def on_real_order_receive(self, order_type, response):
        print(f"주문 응답: {order_type}")
```

이러한 주문 전략은 `BaseOrderOverseasStock`를 상속받고 있습니다. 그래서 다음과 같은 추가 속성과 메소드를 제공합니다:

* **속성** (상속 포함):
  * `id`, `description`, `securities`, `order_types`: 클래스 레벨 속성.
  * `available_symbols`: 매매 전략에 사용할 종목 리스트.
  * `held_symbols`: 보유 중인 종목 리스트.
  * `non_traded_symbols`: 미체결 종목 리스트.
  * `fcurr_dps`: 외화 예금 잔고.
  * `fcurr_ord_able_amt`: 외화 주문 가능 금액.
  * `system_id`: 시스템 ID.
* **메소드**:
  * `__init__()`: 초기화. `super().__init__()` 호출, 잔고 속성 초기화.
  * `execute()`: **필수 구현**. 주문 리스트 생성 로직 반환.
  * `on_real_order_receive(order_type, response)`: **필수 구현**. 실시간 주문 응답 처리.

이 메소드들은 프레임워크에서 자동으로 호출되며, 자식 클래스에서 오버라이드할 수 있습니다.

그리고 정정, 취소 주문도 마찬가지로 `BaseModifyOrderOverseasStock`, `BaseCancelOrderOverseasStock`을 상속받아 구현하면 됩니다.

그리고 외부 투자자들은 매매전략을 DSL에서 `"condition_id": "StockSplitFunds"`로 지정된 id를 불러서 사용합니다.


## 5. DSL 구성 및 실행

커스텀 클래스를 만든 후, DSL 딕셔너리에 통합하여 실행합니다. ProgramGarden 인스턴스를 생성하고 `run` 메소드를 호출합니다.

### 5.1. 전체 예시 코드

```python
from programgarden import Programgarden
import os

# 커스텀 클래스 정의 (위에서 작성한 클래스들)

class CustomConditionExample:
    def run_example(self):
        pg = Programgarden()

        # 콜백 설정 (옵션)
        pg.on_strategies_message(
            callback=lambda message: print(f"전략 메시지: {message.get('condition_id')}")
        )
        pg.on_real_order_message(
            callback=lambda message: print(f"실시간 주문: {message.get('order_type')}")
        )

        # DSL 구성
        pg.run(
            system={
                "settings": {
                    "system_id": "custom_example_001",
                    "name": "커스텀 전략 예시",
                    "description": "개발자 커스텀 전략 데모",
                    "version": "1.0.0",
                    "author": "개발자 이름",
                    "date": "2025-09-24",
                    "debug": "DEBUG",
                },
                "securities": {
                    "company": "ls",
                    "product": "overseas_stock",
                    "appkey": "LS증권 앱키 입력",
                    "appsecretkey": "LS증권 앱스크릿키 입력",
                },
                "strategies": [
                    {
                        "id": "custom_sma_analysis",
                        "description": "커스텀 SMA 분석",
                        "schedule": "0 */15 * * * *",  # 15분마다
                        "timezone": "Asia/Seoul",
                        "logic": "at_least",
                        "threshold": 1,
                        "symbols": [
                            {"symbol": "TSLA", "exchcd": "82"},
                            {"symbol": "NVDA", "exchcd": "82"},
                        ],
                        "order_id": "split_order_1",
                        "max_symbols": {"order": "mcap", "limit": 5},
                        "conditions": [
                            SMAGoldenDeadCross,
                        ],
                    },
                ],
                "orders": [
                    {
                        "order_id": "split_order_1",
                        "description": "분할 신규 오더",
                        "block_duplicate_trade": True,
                        "order_time": {
                            "start": "09:00:00",
                            "end": "15:00:00",
                            "days": ["mon", "tue", "wed", "thu", "fri"],
                            "timezone": "Asia/Seoul",
                            "behavior": "defer",
                            "max_delay_seconds": 3600,
                        },
                        "condition": {
                            "condition_id": "StockSplitFunds",
                            "params": {
                                "percent_balance": 10.0,
                                "max_symbols": 5,
                            },
                        },
                    },
                    {
                        "order_id": "modify_order_1",
                        "description": "주문 정정",
                        "block_duplicate_trade": True,
                        "order_time": {
                            "start": "09:00:00",
                            "end": "15:00:00",
                            "days": ["mon", "tue", "wed", "thu", "fri"],
                            "timezone": "Asia/Seoul",
                            "behavior": "defer",
                            "max_delay_seconds": 3600,
                        },
                        "condition": ModifyOrderExample,
                    },
                    {
                        "order_id": "cancel_order_1",
                        "description": "주문 취소",
                        "block_duplicate_trade": True,
                        "order_time": {
                            "start": "09:00:00",
                            "end": "15:00:00",
                            "days": ["mon", "tue", "wed", "thu", "fri"],
                            "timezone": "Asia/Seoul",
                            "behavior": "defer",
                            "max_delay_seconds": 3600,
                        },
                        "condition": CancelOrderExample,
                    },
                ]
            }
        )

# 실행
example = CustomConditionExample()
example.run_example()
```

\


## 6. 추가 팁

* **디버깅**: `settings`의 `debug`를 `"DEBUG"`로 설정하여 상세 로그를 확인하세요.
* **커뮤니티**: 커스텀 클래스를 `programgarden-community`에 기여하여 다른 사용자와 공유하세요.

이 가이드를 따라 자신만의 트레이딩 전략을 구축하세요. 질문이 있으면 Issue나 커뮤니티(https://cafe.naver.com/programgarden)를 방문해주세요.
