"""
notification 워크플로우 모음 - 알림/메시징 예제

- w01_holdings_telegram: 보유잔고 텔레그램 전송
"""

from .w01_holdings_telegram import get_workflow as get_holdings_telegram

WORKFLOWS = [
    {
        "id": "notification-01",
        "name": "📱 보유잔고 텔레그램 전송",
        "description": "해외주식 보유잔고를 텔레그램으로 전송",
        "get_workflow": get_holdings_telegram,
    },
]

__all__ = [
    "get_holdings_telegram",
    "WORKFLOWS",
]
