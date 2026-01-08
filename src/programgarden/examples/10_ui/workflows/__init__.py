"""
10_ui Workflows

사용 가능한 워크플로우 목록:
- w01_backtest: 멀티 전략 백테스트 비교
- w02_spider: 스파이더 차트 포트폴리오 분석
- w03_portfolio: 계층적 포트폴리오 백테스트
"""

from .w01_backtest import get_workflow as get_backtest_workflow
from .w02_spider import get_workflow as get_spider_workflow
from .w03_portfolio import get_workflow as get_portfolio_workflow

__all__ = [
    "get_backtest_workflow",
    "get_spider_workflow", 
    "get_portfolio_workflow",
]

# 워크플로우 메타데이터
WORKFLOWS = [
    {
        "id": "w01",
        "name": "📊 멀티 전략 백테스트 비교",
        "description": "5가지 전략(개별3+조합2)의 1년 백테스트 성과 비교",
        "get_workflow": get_backtest_workflow,
    },
    {
        "id": "w02",
        "name": "🕸️ 스파이더 차트 포트폴리오 분석",
        "description": "5종목의 기술적 지표를 레이더 차트로 비교",
        "get_workflow": get_spider_workflow,
    },
    {
        "id": "w03",
        "name": "🏛️ 계층적 포트폴리오 백테스트",
        "description": "PortfolioNode를 활용한 멀티 전략 자본 배분 및 리밸런싱",
        "get_workflow": get_portfolio_workflow,
    },
]


def get_all_workflows():
    """모든 워크플로우 메타데이터 반환"""
    return WORKFLOWS


def get_workflow_by_id(workflow_id: str):
    """ID로 워크플로우 조회"""
    for wf in WORKFLOWS:
        if wf["id"] == workflow_id:
            return wf["get_workflow"]()
    raise ValueError(f"Unknown workflow: {workflow_id}")
