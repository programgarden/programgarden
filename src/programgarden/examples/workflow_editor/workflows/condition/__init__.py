"""
02_condition 워크플로우 모음

조건 노드 및 LogicNode 예제
"""

from .w01_single_condition import get_workflow as get_single_condition
from .w02_multi_condition import get_workflow as get_multi_condition
from .w03_weighted_condition import get_workflow as get_weighted_condition
from .w04_at_least_condition import get_workflow as get_at_least_condition
from .w05_nested_logic import get_workflow as get_nested_logic
from .w06_manual_binding import get_workflow as get_manual_binding

WORKFLOWS = [
    {
        "id": "condition-01",
        "name": "🎯 Single RSI Condition",
        "description": "RSI가 30 이하일 때 통과",
        "get_workflow": get_single_condition,
    },
    {
        "id": "condition-02",
        "name": "🔗 Multi Condition (AND)",
        "description": "RSI AND MACD 복합 조건",
        "get_workflow": get_multi_condition,
    },
    {
        "id": "condition-03",
        "name": "⚖️ Weighted Condition",
        "description": "RSI 40% + MACD 30% + BB 30% >= 70%",
        "get_workflow": get_weighted_condition,
    },
    {
        "id": "condition-04",
        "name": "📊 At-Least Condition",
        "description": "3개 조건 중 2개 이상 만족 시 통과",
        "get_workflow": get_at_least_condition,
    },
    {
        "id": "condition-05",
        "name": "🌳 Nested Logic",
        "description": "(RSI AND MACD) OR (BB AND Volume)",
        "get_workflow": get_nested_logic,
    },
    {
        "id": "condition-06",
        "name": "✋ Manual Binding",
        "description": "{{ nodes.xxx.yyy }} 명시적 바인딩 예제 (일봉 RSI)",
        "get_workflow": get_manual_binding,
    },
]

__all__ = [
    "get_single_condition",
    "get_multi_condition", 
    "get_weighted_condition",
    "get_at_least_condition",
    "get_nested_logic",
    "get_manual_binding",
    "WORKFLOWS",
]
