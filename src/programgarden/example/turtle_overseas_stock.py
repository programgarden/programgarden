from dotenv import load_dotenv
from programgarden import Programgarden
import os
import time
import threading
import asyncio

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

    pg.on_error_message(
        callback=lambda message: print(f"Error: {message}")
    )  

    # 5초 후 자동 종료를 위한 타이머 설정
    def stop_after_delay():
        time.sleep(5)
        print("5초 경과 - 시스템 종료 중...")
        asyncio.run(pg.stop())
    
    # 백그라운드 스레드로 타이머 시작
    timer_thread = threading.Thread(target=stop_after_delay, daemon=True)
    timer_thread.start()

    pg.run(
        system={
            'settings': {
                'system_id': 'example_turtle_overseas_stock',
                'name': '터틀 트레이딩 추세 전략',
                'description': '가격 진동폭을 확인해서 우상향 추세가 강하게 체크되면 진입합니다.',
                'version': '1.0.0',
                'author': 'Programgarden Community',
                'date': '2025-11-22',
                'debug': 'debug'
            },
            'securities': {
                'company': 'ls',
                'product': 'overseas_stock',
                "appkey": os.getenv("APPKEY"),  # LS증권 앱키로 대체해주세요.
                "appsecretkey": os.getenv("APPSECRET"),  # LS증권 앱시크릿키로 대체해주세요.
            },
            'strategies': [
                {
                    'id': 'turtle_screening',
                    'description': '가격 진동폭, 유동성, 돌파 거리를 확인해서 주문을 허용합니다.',
                    'schedule': '0 * * * * *',
                    'timezone': 'Asia/Seoul',
                    'run_once_on_start': True,
                    'logic': 'at_least',
                    'threshold': 1,
                    'symbols': [
                        {
                            'symbol': 'GOSS',
                            'exchange': 'NASDAQ'
                        }
                    ],
                    'order_id': 'turtle_new_order_block',
                    'conditions': [
                        {
                            'condition_id': 'TurtleBreakoutFilter',
                            'params': {
                                "appkey": os.getenv("APPKEY"),  # LS증권 앱키로 대체해주세요.
                                "appsecretkey": os.getenv("APPSECRET"),  # LS증권 앱시크릿키로 대체해주세요.
                                'entry_long_period': 20,
                                'strong_entry_period': 55,
                                'exit_period': 10,
                                'min_turnover': 2000000,
                                'min_volume': 500000,
                                'min_atr': 0.8
                            }
                        },
                        {
                            'condition_id': 'TurtleLiquidityFilter',
                            'params': {
                                "appkey": os.getenv("APPKEY"),  # LS증권 앱키로 대체해주세요.
                                "appsecretkey": os.getenv("APPSECRET"),  # LS증권 앱시크릿키로 대체해주세요.
                                'lookback_days': 20,
                                'min_turnover': 1000000,
                                'min_volume': 400000
                            }
                        },
                        {
                            'condition_id': 'TurtleVolatilityFilter',
                            'params': {
                                "appkey": os.getenv("APPKEY"),  # LS증권 앱키로 대체해주세요.
                                "appsecretkey": os.getenv("APPSECRET"),  # LS증권 앱시크릿키로 대체해주세요.
                                'atr_period': 20,
                                'min_atr': 0.7
                            }
                        }
                    ]
                },
                {
                    'id': 'turtle_just_modify',
                    'description': '정정 주문을 넣습니다.',
                    'schedule': '*/1 * * * *',
                    'timezone': 'Asia/Seoul',
                    'run_once_on_start': True,
                    'symbols': [
                        {
                            'symbol': 'GOSS',
                            'exchange': 'NASDAQ'
                        },
                        {
                            'symbol': 'JSPR',
                            'exchange': 'NASDAQ'
                        }
                    ],
                    'order_id': 'turtle_modify_block'
                },
                {
                    'id': 'only_loss_cut',
                    'description': '손절 주문을 넣습니다.',
                    'schedule': '*/2 * * * *',
                    'timezone': 'Asia/Seoul',
                    'run_once_on_start': True,
                    'order_id': 'loss_cut_order'
                }
            ],
            'orders': [
                {
                    'order_id': 'turtle_new_order_block',
                    'description': '계좌 기반 리스크 산정 방식을 사용해, 돌파 구간에서 피라미딩(추가 매수/추가 진입)을 수행한다.',
                    'block_duplicate_buy': True,
                    'order_time': {
                        'start': '22:00:00',
                        'end': '05:30:00',
                        'days': [
                            'mon',
                            'tue',
                            'wed',
                            'thu',
                            'fri'
                        ],
                        'timezone': 'Asia/Seoul',
                        'behavior': 'defer',
                        'max_delay_seconds': 900
                    },
                    'condition': {
                        'condition_id': 'TurtlePyramidNewOrder',
                        'params': {
                            "appkey": os.getenv("APPKEY"),  # LS증권 앱키로 대체해주세요.
                            "appsecretkey": os.getenv("APPSECRET"),  # LS증권 앱시크릿키로 대체해주세요.
                            'risk_per_trade': 0.01,
                            'cash_usage_ratio': 0.75,
                            'entry_period': 20,
                            'atr_period': 20,
                            'pyramid_trigger_atr': 0.5,
                            'limit_buffer_atr': 0.1,
                            'max_units_per_symbol': 4,
                            'min_trade_size': 1
                        }
                    }
                },
                {
                    'order_id': 'turtle_modify_block',
                    'description': '휴면 중인 터틀 주문을 조정하여 체결 경쟁력을 유지합니다.',
                    'order_time': {
                        'start': '22:00:00',
                        'end': '05:30:00',
                        'days': [
                            'mon',
                            'tue',
                            'wed',
                            'thu',
                            'fri'
                        ],
                        'timezone': 'Asia/Seoul',
                        'behavior': 'defer',
                        'max_delay_seconds': 600
                    },
                    'condition': {
                        'condition_id': 'TurtleAdaptiveModify',
                        'params': {
                            "appkey": os.getenv("APPKEY"),  # LS증권 앱키로 대체해주세요.
                            "appsecretkey": os.getenv("APPSECRET"),  # LS증권 앱시크릿키로 대체해주세요.
                            'price_gap': 0.25,
                            'tick_size': 0.05,
                            'timeout_seconds': 240,
                            'max_modify': 3,
                            'limit_padding': 0.02
                        }
                    }
                },
                {
                    'order_id': 'loss_cut_order',
                    'description': '손절 가격 이하로 떨어지면 매도합니다.',
                    'order_time': {
                        'start': '22:00:00',
                        'end': '05:30:00',
                        'days': [
                            'mon',
                            'tue',
                            'wed',
                            'thu',
                            'fri'
                        ],
                        'timezone': 'Asia/Seoul',
                        'behavior': 'defer',
                        'max_delay_seconds': 600
                    },
                    'condition': {
                        'condition_id': 'BasicLossCutManager',
                        'params': {
                            'losscut': -10
                        }
                    }
                }
            ]
        }

    )
