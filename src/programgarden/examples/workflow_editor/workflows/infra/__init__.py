"""
01_infra 워크플로우 모음

- w01_start_only: StartNode 기본 예제
- w02_start_schedule: 스케줄 트리거 예제
- w03_trading_hours: 거래시간 필터 예제
- w04_broker_connection: 증권사 연결 예제
- w05_watchlist_realmarket: 관심종목 실시간 시세
"""

from .w01_start_only import get_workflow as get_start_only
from .w02_start_schedule import get_workflow as get_start_schedule
from .w03_trading_hours import get_workflow as get_trading_hours
from .w04_broker_connection import get_workflow as get_broker_connection
from .w05_watchlist_realmarket import get_workflow as get_watchlist_realmarket

WORKFLOWS = [
    {
        "id": "infra-01",
        "name": "🚀 Start Only",
        "description": "StartNode 기본 예제",
        "get_workflow": get_start_only,
    },
    {
        "id": "infra-02",
        "name": "⏰ Start + Schedule",
        "description": "5분마다 트리거 발생",
        "get_workflow": get_start_schedule,
    },
    {
        "id": "infra-03",
        "name": "🕐 Trading Hours Filter",
        "description": "NYSE 거래시간에만 실행",
        "get_workflow": get_trading_hours,
    },
    {
        "id": "infra-04",
        "name": "🔌 Broker Connection",
        "description": "LS증권 해외주식 연결",
        "get_workflow": get_broker_connection,
    },
    {
        "id": "infra-05",
        "name": "📊 Watchlist + RealMarket",
        "description": "관심종목 실시간 시세 구독",
        "get_workflow": get_watchlist_realmarket,
    },
]

__all__ = [
    "get_start_only",
    "get_start_schedule",
    "get_trading_hours",
    "get_broker_connection",
    "get_watchlist_realmarket",
    "WORKFLOWS",
]
