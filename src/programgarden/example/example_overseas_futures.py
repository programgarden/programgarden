from typing import List
from dotenv import load_dotenv
from programgarden import Programgarden
from programgarden_core import (
    BaseStrategyConditionOverseasFutures,
    BaseNewOrderOverseasFutures,
    BaseStrategyConditionResponseOverseasFuturesType,
    BaseNewOrderOverseasFuturesResponseType,
)
import os

load_dotenv()


class StrategyTest(BaseStrategyConditionOverseasFutures):

    id: str = "StrategyTest"
    description: str = """
Moving average golden/dead cross detection conditions

1) Observed a dead->golden where golden_price > dead_price (candidate)
2) The golden occurred within the most recent 2 data points
3) The latest alignment is golden (still maintained)
"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def execute(self) -> BaseStrategyConditionResponseOverseasFuturesType:
        print(f"Executing condition for symbol: {self.symbol}")

        return {
            "success": True,
            "symbol": self.symbol.get("symbol", ""),
            "product": "overseas_futures",
            "position_side": "long",
            "condition_id": self.id,
            "description": self.description,
            "exchcd": "CME",
            "data": {"test_key": "test_value"},
            "weight": 0.5,
        }


class OrderTest(BaseNewOrderOverseasFutures):

    id: str = "OrderTest"
    description: str = "주식 분할 자금"
    securities: List[str] = ["ls-sec.co.kr"]
    order_types = ["new_buy"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def execute(self) -> List[BaseNewOrderOverseasFuturesResponseType]:
        print(f"Executing order for symbol: {self.available_symbols}")

        return [{
            "success": True,
            "ord_dt": "20251023",
            "isu_code_val": self.available_symbols[0].get("symbol", ""),
            "futs_ord_tp_code": "1",
            "bns_tp_code": "2",
            "abrd_futs_ord_ptn_code": "2",
            "ord_qty": 1,
            "ovrs_drvt_ord_prc": 6700.0,
            "cndi_ord_prc": 0.0,
        }]

    async def on_real_order_receive(self, order_type, response):
        pass


if __name__ == "__main__":

    pg = Programgarden()

    # 전략 수행 응답 콜백
    pg.on_strategies_message(
        callback=lambda message: print(f"Strategies: {message}")
    )

    # 실시간 주문 응답 콜백
    pg.on_real_order_message(
        callback=lambda message: print(f"Real Order Message: {message.get('order_type')}, {message.get('message')}")
    )

    pg.on_error_message(
        callback=lambda message: print(f"Error Message: {message}")
    )

    pg.run(
        system={
            "settings": {
                "시스템ID": "example_condition_001",
                "이름": "양방향 추세매매 전략 시스템",
                "설명": "장기 이평선 골든크로스 조건을 활용한 양방향 추세매매 전략 시스템",
                "버전": "1.0.0",
                "작성자": "Author Name",
                "작성일": "2023-10-01",
                "디버그": "DEBUG",
            },
            "securities": {
                "회사": "ls",
                "상품": "overseas_futures",
                "모의투자": True,
                "앱키": os.getenv("APPKEY_FUTURE_FAKE"),  # LS증권 앱키로 대체해주세요.
                "앱시크릿": os.getenv("APPSECRET_FUTURE_FAKE"),  # LS증권 앱시크릿키로 대체해주세요.
            },
            "strategies": [
                {
                    "전략ID": "condition_market_analysis",
                    "설명": "시장 분석 전략",
                    "스케줄": "*/10 * * * * *",
                    "시간대": "Asia/Seoul",
                    "시작즉시실행": True,
                    "로직": "at_least",
                    "임계값": 1,
                    "symbols": [{
                        "symbol": "ADZ25",
                        "name": "Australian Dollar",
                        "exchange": "CME"
                    }],
                    "order_id": "OrderTest",
                    "conditions": [
                        StrategyTest()
                    ],
                },
            ],
            "orders": [
                {
                    "order_id": "OrderTest",
                    "description": "테스트 주문",
                    "block_duplicate_buy": True,
                    "condition": OrderTest()
                }
            ]
        }
    )
