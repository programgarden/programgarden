from typing import List
from dotenv import load_dotenv
from programgarden import Programgarden
from programgarden_core import (
    BaseStrategyConditionOverseasFutures,
    BaseStrategyConditionResponseOverseasFuturesType,
    BaseCancelOrderOverseasFutures,
    BaseCancelOrderOverseasFuturesResponseType
)
import os

load_dotenv()


class StrategyTest(BaseStrategyConditionOverseasFutures):

    id: str = "StrategyTest"
    description: str = "샘플 전략 조건입니다."

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def execute(self) -> BaseStrategyConditionResponseOverseasFuturesType:

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


class OrderCancelTest(BaseCancelOrderOverseasFutures):

    id: str = "OrderCancelTest"
    description: str = "취소주문 테스트"
    securities: List[str] = ["ls-sec.co.kr"]
    order_types = ["cancel_buy", "cancel_sell"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def execute(self) -> List[BaseCancelOrderOverseasFuturesResponseType]:
        print(f"Executing order for symbol: {self.non_traded_symbols}")

        return [{
            "success": True,
            "ovrs_futs_org_ord_no": self.non_traded_symbols[0].get("OvrsFutsOrdNo", ""),
            "isu_code_val": self.non_traded_symbols[0].get("IsuCodeVal", ""),
            "futs_ord_tp_code": "3",
            "prdt_tp_code": "",
            "exch_code": "",
            "ord_dt": "20251023",
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
                        "symbol": "MCAX25",
                        "name": "China A50 Index Futures",
                        "exchange": "HKEX"
                    }],
                    "order_id": "OrderCancelTest",
                    "conditions": [
                        StrategyTest()
                    ],
                },
            ],
            "orders": [
                {
                    "order_id": "OrderCancelTest",
                    "description": "테스트 주문",
                    "block_duplicate_buy": True,
                    "condition": OrderCancelTest()
                }
            ]
        }
    )
