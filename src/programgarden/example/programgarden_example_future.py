from dotenv import load_dotenv
from programgarden import Programgarden
from programgarden_core import (
    BaseStrategyConditionOverseasFutures,
    BaseStrategyConditionResponseOverseasFuturesType
)
import os

load_dotenv()


class StrategyTest(BaseStrategyConditionOverseasFutures):

    async def execute(self) -> BaseStrategyConditionResponseOverseasFuturesType:
        return


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
                    "스케줄": "*/5 * * * * *",
                    "시간대": "Asia/Seoul",
                    "로직": "at_least",
                    "임계값": 1,
                    "종목": [],
                    "최대종목": {
                        "정렬": "mcap",
                        "제한": 5
                    },
                    "conditions": [
                        {}
                    ],
                },
            ],
            "orders": [
                {
                    "order_id": "자금분배매수_1",
                    "description": "자금 분배 매수 주문",
                    "order_type": "fund_distribution_buy",
                    "parameters": {
                        "total_investment": 1000000,
                        "max_positions": 5,
                        "allocation_strategy": "equal",
                    },
                }
            ]
        }
    )
