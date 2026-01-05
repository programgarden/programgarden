"""
ProgramGarden - Definition Tools

워크플로우 정의 관리 도구
"""

from typing import Optional, List, Dict, Any

# 인메모리 저장소 (실제 구현에서는 DB 사용)
_workflows: Dict[str, Dict[str, Any]] = {}


def create_workflow(definition: Dict[str, Any]) -> Dict[str, Any]:
    """
    새 워크플로우 정의 생성

    Args:
        definition: 워크플로우 정의 (nodes, edges 포함)

    Returns:
        생성된 WorkflowDefinition

    Example:
        >>> create_workflow({
        ...     "id": "my-strategy",
        ...     "name": "My Trading Strategy",
        ...     "nodes": [...],
        ...     "edges": [...]
        ... })
        {"id": "my-strategy", "version": "1.0.0", ...}
    """
    from programgarden_core import WorkflowDefinition
    from programgarden.resolver import WorkflowResolver

    # 검증
    resolver = WorkflowResolver()
    validation = resolver.validate(definition)

    if not validation.is_valid:
        raise ValueError(f"Validation failed: {validation.errors}")

    # 저장
    workflow = WorkflowDefinition(**definition)
    key = f"{workflow.id}@{workflow.version}"
    _workflows[key] = workflow.model_dump()
    _workflows[workflow.id] = workflow.model_dump()  # 최신 버전

    return workflow.model_dump()


def validate_workflow(definition: Dict[str, Any]) -> Dict[str, Any]:
    """
    워크플로우 정의 검증 (저장 없이)

    Args:
        definition: 워크플로우 정의

    Returns:
        검증 결과 {"is_valid": bool, "errors": [...], "warnings": [...]}

    Example:
        >>> validate_workflow({"id": "test", "nodes": [], "edges": []})
        {"is_valid": False, "errors": ["StartNode가 없습니다"], "warnings": []}
    """
    from programgarden.resolver import WorkflowResolver

    resolver = WorkflowResolver()
    result = resolver.validate(definition)

    return {
        "is_valid": result.is_valid,
        "errors": result.errors,
        "warnings": result.warnings,
    }


def get_workflow(
    workflow_id: str,
    version: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    워크플로우 정의 조회

    Args:
        workflow_id: 워크플로우 ID
        version: 버전 (생략 시 최신 버전)

    Returns:
        WorkflowDefinition 또는 None

    Example:
        >>> get_workflow("my-strategy", "1.0.0")
        {"id": "my-strategy", "version": "1.0.0", ...}
    """
    if version:
        key = f"{workflow_id}@{version}"
        return _workflows.get(key)
    return _workflows.get(workflow_id)


def list_workflows() -> List[Dict[str, Any]]:
    """
    모든 워크플로우 정의 목록 조회

    Returns:
        워크플로우 요약 목록

    Example:
        >>> list_workflows()
        [{"id": "my-strategy", "name": "My Trading Strategy", "version": "1.0.0"}, ...]
    """
    result = []
    seen = set()

    for key, workflow in _workflows.items():
        if "@" in key:  # 버전별 키는 스킵
            continue
        if workflow["id"] not in seen:
            result.append({
                "id": workflow["id"],
                "name": workflow.get("name"),
                "version": workflow.get("version"),
                "description": workflow.get("description"),
            })
            seen.add(workflow["id"])

    return result


def update_workflow(
    workflow_id: str,
    definition: Dict[str, Any],
) -> Dict[str, Any]:
    """
    워크플로우 정의 업데이트 (새 버전 생성)

    Args:
        workflow_id: 워크플로우 ID
        definition: 새 정의

    Returns:
        업데이트된 WorkflowDefinition

    Example:
        >>> update_workflow("my-strategy", {"version": "1.1.0", ...})
        {"id": "my-strategy", "version": "1.1.0", ...}
    """
    # ID 유지
    definition["id"] = workflow_id

    # 버전 자동 증가 (없으면)
    if "version" not in definition:
        old = get_workflow(workflow_id)
        if old:
            # 간단한 버전 증가 (실제로는 semantic versioning 파서 사용)
            parts = old.get("version", "1.0.0").split(".")
            parts[-1] = str(int(parts[-1]) + 1)
            definition["version"] = ".".join(parts)

    return create_workflow(definition)


def delete_workflow(workflow_id: str) -> bool:
    """
    워크플로우 정의 삭제

    Args:
        workflow_id: 삭제할 워크플로우 ID

    Returns:
        삭제 성공 여부

    Example:
        >>> delete_workflow("my-strategy")
        True
    """
    deleted = False

    # 버전별 키와 최신 키 모두 삭제
    keys_to_delete = [k for k in _workflows.keys() if k.startswith(workflow_id)]
    for key in keys_to_delete:
        del _workflows[key]
        deleted = True

    return deleted
