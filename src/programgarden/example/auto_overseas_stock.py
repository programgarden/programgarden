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
        callback=lambda message: print(f"Real Order Message: {message.get('order_type')}, {message.get('message')}")
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
                    "schedule": "*/30 * * * * *",
                    "timezone": "Asia/Seoul",
                    "logic": "at_least",
                    "run_once_on_start": True,
                    "threshold": 1,
                    # "order_id": "자금분배매수_1",
                    "symbols": [
                        {
                            "symbol": "GOSS",
                            "exchange": "NASDAQ",
                        },
                    ],
                    "max_symbols": {
                        "order": "mcap",
                        "limit": 5
                    },
                    "conditions": [
                        {
                            "condition_id": "SMAGoldenDeadCross",
                            "weight": 0.6,
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
                    "id": "loss_cut_net",
                    "description": "손절하기",
                    "schedule": "*/30 * * * * *",
                    "timezone": "Asia/Seoul",
                    "logic": "at_least",
                    "threshold": 1,
                    "order_id": "손절매도1",
                },
            ],

            "orders": [
                {
                    "order_id": "자금분배매수_1",
                    "description": "분할 매매 전략임",
                    "block_duplicate_buy": True,
                    "order_time": {
                        "start": "00:00:00",
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
                {
                    "order_id": "손절매도1",
                    "description": "손절 시장가 주문",
                    "order_time": {
                        "start": "00:00:00",
                        "end": "04:00:00",
                        "days": ["mon", "tue", "wed", "thu", "fri"],
                        "timezone": "Asia/Seoul",
                        "behavior": "defer",
                        "max_delay_seconds": 86400
                    },
                    "condition": {
                        "condition_id": "BasicLossCutManager",
                        "params": {
                            "losscut": 10
                        }
                    }
                }
            ]
        }
    )
