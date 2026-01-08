"""
10_futures 워크플로우 모음 - 해외선물 전용

- w01_futures_broker: 해외선물 브로커 연결 (모의투자)
- w02_futures_account: 해외선물 잔고 조회
- w03_futures_order: 해외선물 주문 예제
"""

from .w01_futures_broker import get_workflow as get_futures_broker
from .w02_futures_account import get_workflow as get_futures_account
from .w03_futures_order import get_workflow as get_futures_order

WORKFLOWS = [
    {
        "id": "futures-01",
        "name": "🔥 해외선물 브로커 연결",
        "description": "해외선물 모의투자 연결 테스트",
        "get_workflow": get_futures_broker,
    },
    {
        "id": "futures-02",
        "name": "📊 해외선물 잔고 조회",
        "description": "해외선물 계좌 잔고 및 포지션 조회",
        "get_workflow": get_futures_account,
    },
    {
        "id": "futures-03",
        "name": "📝 해외선물 주문 예제",
        "description": "나스닥선물 조건부 주문",
        "get_workflow": get_futures_order,
    },
]

__all__ = [
    "get_futures_broker",
    "get_futures_account",
    "get_futures_order",
    "WORKFLOWS",
]
