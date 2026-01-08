"""
10_ui Workflows - 워크플로우 통합 모음

카테고리:
- infra: 인프라 (시작, 브로커, 스케줄 등)
- condition: 조건 평가 (단일/다중/가중치/중첩 논리)
- order: 주문 실행 (시장가/지정가/정정/취소)
- advanced: 고급 기능 (스크리너/이벤트/에러 핸들러/리스크 가드)
- operation: 운영 (거래시간/일시정지/스냅샷/다중시장/장시간실행)
- backtest: 백테스트 (단순/자동배포/주간스케줄)
- futures: 해외선물 전용
- custom: 기존 커스텀 워크플로우 (백테스트 비교/스파이더 차트/포트폴리오)
"""

# 카테고리별 임포트
from . import infra
from . import condition
from . import order
from . import advanced
from . import operation
from . import backtest
from . import futures

# 기존 커스텀 워크플로우
from .w01_backtest import get_workflow as get_backtest_workflow
from .w02_spider import get_workflow as get_spider_workflow
from .w03_portfolio import get_workflow as get_portfolio_workflow

__all__ = [
    # 카테고리 모듈
    "infra",
    "condition",
    "order",
    "advanced",
    "operation",
    "backtest",
    "futures",
    # 기존 워크플로우
    "get_backtest_workflow",
    "get_spider_workflow",
    "get_portfolio_workflow",
    # 유틸리티 함수
    "get_all_categories",
    "get_workflows_by_category",
    "get_all_workflows",
    "get_workflow_by_id",
    "CATEGORIES",
]

# 카테고리 정의
CATEGORIES = [
    {"id": "infra", "name": "🏗️ 인프라", "module": infra, "description": "시작, 브로커, 스케줄 등 기본 인프라"},
    {"id": "condition", "name": "⚡ 조건", "module": condition, "description": "단일/다중/가중치/중첩 조건 평가"},
    {"id": "order", "name": "🛒 주문", "module": order, "description": "시장가/지정가/정정/취소 주문 실행"},
    {"id": "advanced", "name": "🔧 고급", "module": advanced, "description": "스크리너/이벤트/에러 핸들러/리스크 가드"},
    {"id": "operation", "name": "⚙️ 운영", "module": operation, "description": "거래시간/일시정지/스냅샷/다중시장/장시간실행"},
    {"id": "backtest", "name": "📈 백테스트", "module": backtest, "description": "단순/자동배포/주간 스케줄 백테스트"},
    {"id": "futures", "name": "🔥 해외선물", "module": futures, "description": "해외선물 전용 브로커/잔고/주문"},
    {
        "id": "custom",
        "name": "✨ 커스텀",
        "module": None,
        "description": "기존 커스텀 워크플로우",
        "workflows": [
            {"id": "custom-01", "name": "📊 멀티 전략 백테스트 비교", "description": "5가지 전략의 1년 백테스트 성과 비교", "get_workflow": get_backtest_workflow},
            {"id": "custom-02", "name": "🕸️ 스파이더 차트 포트폴리오 분석", "description": "5종목의 기술적 지표를 레이더 차트로 비교", "get_workflow": get_spider_workflow},
            {"id": "custom-03", "name": "🏛️ 계층적 포트폴리오 백테스트", "description": "PortfolioNode를 활용한 멀티 전략 자본 배분 및 리밸런싱", "get_workflow": get_portfolio_workflow},
        ],
    },
]


def get_all_categories():
    """모든 카테고리 목록 반환"""
    return [{"id": c["id"], "name": c["name"], "description": c["description"]} for c in CATEGORIES]


def get_workflows_by_category(category_id: str):
    """카테고리별 워크플로우 목록 반환"""
    for cat in CATEGORIES:
        if cat["id"] == category_id:
            if cat["module"]:
                return cat["module"].WORKFLOWS
            elif "workflows" in cat:
                return cat["workflows"]
    raise ValueError(f"Unknown category: {category_id}")


def get_all_workflows():
    """모든 워크플로우 메타데이터 반환 (카테고리 정보 포함)"""
    all_workflows = []
    for cat in CATEGORIES:
        if cat["module"]:
            for wf in cat["module"].WORKFLOWS:
                all_workflows.append({**wf, "category": cat["id"], "category_name": cat["name"]})
        elif "workflows" in cat:
            for wf in cat["workflows"]:
                all_workflows.append({**wf, "category": cat["id"], "category_name": cat["name"]})
    return all_workflows


def get_workflow_by_id(workflow_id: str):
    """ID로 워크플로우 조회"""
    for wf in get_all_workflows():
        if wf["id"] == workflow_id:
            return wf["get_workflow"]()
    raise ValueError(f"Unknown workflow: {workflow_id}")
