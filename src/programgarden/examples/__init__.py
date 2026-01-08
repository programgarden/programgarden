"""
ProgramGarden Examples - Node-Based DSL

모든 워크플로우 예제는 workflow_editor/workflows/로 이전되었습니다.

사용법:
    from examples.workflow_editor.workflows import (
        get_all_categories,
        get_workflows_by_category,
        get_all_workflows,
        get_workflow_by_id,
    )
    
    # 카테고리 목록
    categories = get_all_categories()
    
    # 카테고리별 워크플로우
    futures_workflows = get_workflows_by_category("futures")
    
    # 전체 워크플로우 (36개)
    all_workflows = get_all_workflows()
    
    # ID로 조회
    workflow = get_workflow_by_id("futures-01")
"""

# workflow_editor/workflows에서 re-export
try:
    from .workflow_editor.workflows import (
        get_all_categories,
        get_workflows_by_category,
        get_all_workflows,
        get_workflow_by_id,
        CATEGORIES,
    )
except ImportError:
    # fallback for direct import
    pass


def get_example(name: str):
    """예제 워크플로우 조회 (deprecated - use get_workflow_by_id instead)"""
    try:
        return get_workflow_by_id(name)
    except (ValueError, NameError):
        return None


def list_examples():
    """모든 예제 목록 조회 (deprecated - use get_all_workflows instead)"""
    try:
        return [w["id"] for w in get_all_workflows()]
    except NameError:
        return []


__all__ = [
    "get_example",
    "list_examples",
    "get_all_categories",
    "get_workflows_by_category",
    "get_all_workflows",
    "get_workflow_by_id",
    "CATEGORIES",
]
