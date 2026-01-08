"""
05_operation 워크플로우 모음 - 운영 기능

- w01_trading_hours: 거래시간 필터
- w02_pause_resume: 일시정지/재개
- w03_state_snapshot: 상태 스냅샷
- w04_multi_market: 다중 시장
- w05_long_running: 장시간 실행
- w06_24h_autonomous: 24시간 완전 자동
"""

from .w01_trading_hours import get_workflow as get_trading_hours
from .w02_pause_resume import get_workflow as get_pause_resume
from .w03_state_snapshot import get_workflow as get_state_snapshot
from .w04_multi_market import get_workflow as get_multi_market
from .w05_long_running import get_workflow as get_long_running
from .w06_24h_autonomous import get_workflow as get_24h_autonomous

WORKFLOWS = [
    {
        "id": "operation-01",
        "name": "⏰ 거래시간 필터",
        "description": "NYSE 정규장 시간에만 거래",
        "get_workflow": get_trading_hours,
    },
    {
        "id": "operation-02",
        "name": "⏸️ 일시정지/재개",
        "description": "상태 보존하여 일시정지/재개",
        "get_workflow": get_pause_resume,
    },
    {
        "id": "operation-03",
        "name": "💾 상태 스냅샷",
        "description": "주기적 상태 저장 및 장애 복구",
        "get_workflow": get_state_snapshot,
    },
    {
        "id": "operation-04",
        "name": "🌐 다중 시장",
        "description": "미국 주식 + 선물 동시 운영",
        "get_workflow": get_multi_market,
    },
    {
        "id": "operation-05",
        "name": "🔄 장시간 실행",
        "description": "24시간 연속 운영 + 일별 리포트",
        "get_workflow": get_long_running,
    },
    {
        "id": "operation-06",
        "name": "🤖 24시간 완전 자동",
        "description": "RSI+BB+거래량 조건 24시간 자동 매매",
        "get_workflow": get_24h_autonomous,
    },
]

__all__ = [
    "get_trading_hours",
    "get_pause_resume",
    "get_state_snapshot",
    "get_multi_market",
    "get_long_running",
    "get_24h_autonomous",
    "WORKFLOWS",
]
