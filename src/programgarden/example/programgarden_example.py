from dotenv import load_dotenv
from programgarden import Programgarden
import os

load_dotenv()


if __name__ == "__main__":

    pg = Programgarden()

    # 전략 수행 응답 콜백
    pg.on_strategies_message(
        callback=lambda message: print(f"Strategies: {message.get('condition_id')}")
    )

    # 실시간 주문 응답 콜백
    pg.on_real_order_message(
        callback=lambda message: print(f"Real Order Message: {message.get('order_type')}")
    )

    pg.run(
        system={
            "settings": {
                "system_id": "example_condition_001",
                "name": "분할 매수 전략 시스템",
                "description": "장기 이평선 골든크로스 조건을 활용한 분할 매수 전략 시스템",
                "version": "1.0.0",
                "author": "Author Name",
                "date": "2023-10-01",
                "debug": "DEBUG",
            },
            "securities": {
                "company": "ls",
                "product": "overseas_stock",
                "appkey": os.getenv("APPKEY"),  # LS증권 앱키로 대체해주세요.
                "appsecretkey": os.getenv("APPSECRET"),  # LS증권 앱시크릿키로 대체해주세요.
            },
            "strategies": [
                {
                    "id": "condition_market_analysis",
                    "description": "시장 분석 전략",
                    "schedule": "* * * * * *",
                    "timezone": "Asia/Seoul",
                    "logic": "at_least",
                    "threshold": 1,
                    "symbols": [
                        {
                            "symbol": "GOSS",
                            "exchcd": "82"
                        },
                        {
                            "symbol": "JSPR",
                            "exchcd": "82"
                        },
                    ],
                    "order_id": "자금분배매수_1",
                    "max_symbols": {
                        "order": "mcap",
                        "limit": 5
                    },
                    "conditions": [
                        {
                            "condition_id": "SMAGoldenDeadCross",
                            "params": {
                                "use_ls": True,
                                "appkey": os.getenv("APPKEY"),  # LS증권 앱키로 대체해주세요.
                                "appsecretkey": os.getenv("APPSECRET"),  # LS증권 앱시크릿키로 대체해주세요.
                                "start_date": "20230101",
                                "end_date": "20250918",
                                "alignment": "golden",
                                "long_period": 120,
                                "short_period": 60,
                                "time_category": "days",
                            },
                        },
                    ],
                },
                {
                    "id": "condition_loss_cut",
                    "description": "수익률 마이너스되면 전량 매도하기",
                    "schedule": "* * * * * *",
                    "timezone": "Asia/Seoul",
                    "logic": "at_least",
                    "threshold": 0,
                    "order_id": "losscut_sell_1",
                }
            ],

            "orders": {
                "new_buys": [
                    {
                        "order_id": "자금분배매수_1",
                        "description": "시장 분석 전략",
                        "block_duplicate_trade": True,
                        "order_time": {
                            "start": "20:00:00",
                            "end": "04:00:00",
                            "days": ["mon", "tue", "wed", "thu", "fri"],
                            "timezone": "Asia/Seoul",
                            "behavior": "defer",
                            "max_delay_seconds": 86400
                        },
                        "condition": {
                            "condition_id": "StockSplitFunds",
                            "params": {
                                "appkey": os.getenv("APPKEY"),  # LS증권 앱키로 대체해주세요.
                                "appsecretkey": os.getenv("APPSECRET"),  # LS증권 앱시크릿키로 대체해주세요.
                                "percent_balance": 0.8,
                                "max_symbols": 2
                            }
                        }
                    },
                ],
                "new_sells": [
                    {
                        "order_id": "losscut_sell_1",
                        "description": "수익률 마이너스되면 전량 매도하기",
                        "order_time": {
                            "start": "02:00:00",
                            "end": "04:00:00",
                            "days": ["tue", "wed", "thu", "fri", "sat"],
                            "timezone": "Asia/Seoul",
                            "behavior": "defer",
                            "max_delay_seconds": 86400
                        },
                        "condition": {
                            "condition_id": "BasicLossCutManager",
                        }
                    },
                ],
            }
        }
    )
