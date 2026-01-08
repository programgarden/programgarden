"""
06_backtest 워크플로우 모음 - 백테스트

- w01_backtest_simple: 단순 백테스트
- w02_backtest_with_deploy: 백테스트 → 자동 배포
- w03_scheduled_backtest: 주간 백테스트 기반 Job 제어
"""

from .w01_backtest_simple import get_workflow as get_backtest_simple
from .w02_backtest_with_deploy import get_workflow as get_backtest_with_deploy
from .w03_scheduled_backtest import get_workflow as get_scheduled_backtest

WORKFLOWS = [
    {
        "id": "backtest-01",
        "name": "📈 단순 백테스트",
        "description": "과거 1년 데이터로 RSI 전략 성과 검증",
        "get_workflow": get_backtest_simple,
    },
    {
        "id": "backtest-02",
        "name": "🚀 백테스트 → 자동 배포",
        "description": "백테스트 결과가 기준 충족 시 자동 배포",
        "get_workflow": get_backtest_with_deploy,
    },
    {
        "id": "backtest-03",
        "name": "📅 주간 백테스트 Job 제어",
        "description": "매주 백테스트 후 성과 불량 시 Job 일시정지",
        "get_workflow": get_scheduled_backtest,
    },
]

__all__ = [
    "get_backtest_simple",
    "get_backtest_with_deploy",
    "get_scheduled_backtest",
    "WORKFLOWS",
]
