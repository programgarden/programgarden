"""
03_order 워크플로우 모음 - 주문 실행

- w01_market_order: 시장가 주문
- w02_limit_order: 지정가 주문
- w03_position_sizing: 포지션 사이징
- w04_modify_order: 주문 정정
- w05_cancel_order: 주문 취소
- w06_buy_sell_basic: 기본 매수매도
"""

from .w01_market_order import get_workflow as get_market_order
from .w02_limit_order import get_workflow as get_limit_order
from .w03_position_sizing import get_workflow as get_position_sizing
from .w04_modify_order import get_workflow as get_modify_order
from .w05_cancel_order import get_workflow as get_cancel_order
from .w06_buy_sell_basic import get_workflow as get_buy_sell_basic

WORKFLOWS = [
    {
        "id": "order-01",
        "name": "🛒 시장가 주문",
        "description": "RSI 조건 만족시 시장가 매수",
        "get_workflow": get_market_order,
    },
    {
        "id": "order-02",
        "name": "📝 지정가 주문",
        "description": "현재가 -1% 지정가 매수",
        "get_workflow": get_limit_order,
    },
    {
        "id": "order-03",
        "name": "📏 포지션 사이징",
        "description": "1% 리스크 기반 수량 결정",
        "get_workflow": get_position_sizing,
    },
    {
        "id": "order-04",
        "name": "✏️ 주문 정정",
        "description": "미체결 주문 현재가 추적 정정",
        "get_workflow": get_modify_order,
    },
    {
        "id": "order-05",
        "name": "❌ 주문 취소",
        "description": "30분 초과 미체결 주문 취소",
        "get_workflow": get_cancel_order,
    },
    {
        "id": "order-06",
        "name": "🔄 기본 매수매도",
        "description": "RSI 과매도 매수, 과매수 매도",
        "get_workflow": get_buy_sell_basic,
    },
]

__all__ = [
    "get_market_order",
    "get_limit_order",
    "get_position_sizing",
    "get_modify_order",
    "get_cancel_order",
    "get_buy_sell_basic",
    "WORKFLOWS",
]
