"""
04_advanced 워크플로우 모음 - 고급 기능

- w01_screener_to_order: 스크리너 → 주문
- w02_event_handler: 이벤트 핸들러
- w03_error_handler: 에러 핸들러
- w04_risk_guard: 리스크 가드
"""

from .w01_screener_to_order import get_workflow as get_screener_to_order
from .w02_event_handler import get_workflow as get_event_handler
from .w03_error_handler import get_workflow as get_error_handler
from .w04_risk_guard import get_workflow as get_risk_guard

WORKFLOWS = [
    {
        "id": "advanced-01",
        "name": "🔍 스크리너 → 주문",
        "description": "나스닥100에서 RSI 과매도 종목 스크리닝 후 매수",
        "get_workflow": get_screener_to_order,
    },
    {
        "id": "advanced-02",
        "name": "📢 이벤트 핸들러",
        "description": "체결 이벤트 시 Slack/Telegram 알림",
        "get_workflow": get_event_handler,
    },
    {
        "id": "advanced-03",
        "name": "⚠️ 에러 핸들러",
        "description": "주문 실패 시 3회 재시도 후 알림",
        "get_workflow": get_error_handler,
    },
    {
        "id": "advanced-04",
        "name": "🛡️ 리스크 가드",
        "description": "일일 손실 3% 도달 시 거래 중단",
        "get_workflow": get_risk_guard,
    },
]

__all__ = [
    "get_screener_to_order",
    "get_event_handler",
    "get_error_handler",
    "get_risk_guard",
    "WORKFLOWS",
]
