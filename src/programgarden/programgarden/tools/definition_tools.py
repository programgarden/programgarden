"""
ProgramGarden - Definition Tools

Workflow definition management tools
"""

from typing import Optional, List, Dict, Any

# In-memory storage (use DB in actual implementation)
_workflows: Dict[str, Dict[str, Any]] = {}


def create_workflow(definition: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create new workflow definition

    Args:
        definition: Workflow definition (includes nodes, edges)

    Returns:
        Created WorkflowDefinition

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

    # Validate
    resolver = WorkflowResolver()
    validation = resolver.validate(definition)

    if not validation.is_valid:
        raise ValueError(f"Validation failed: {validation.errors}")

    # Save
    workflow = WorkflowDefinition(**definition)
    key = f"{workflow.id}@{workflow.version}"
    _workflows[key] = workflow.model_dump()
    _workflows[workflow.id] = workflow.model_dump()  # Latest version

    return workflow.model_dump()


def validate_workflow(definition: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate workflow definition (without saving)

    Args:
        definition: Workflow definition

    Returns:
        Validation result {"is_valid": bool, "errors": [...], "warnings": [...]}

    Example:
        >>> validate_workflow({"id": "test", "nodes": [], "edges": []})
        {"is_valid": False, "errors": ["StartNode is missing"], "warnings": []}
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
    Get workflow definition

    Args:
        workflow_id: Workflow ID
        version: Version (latest if omitted)

    Returns:
        WorkflowDefinition or None

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
    List all workflow definitions

    Returns:
        List of workflow summaries

    Example:
        >>> list_workflows()
        [{"id": "my-strategy", "name": "My Trading Strategy", "version": "1.0.0"}, ...]
    """
    result = []
    seen = set()

    for key, workflow in _workflows.items():
        if "@" in key:  # Skip versioned keys
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
    Update workflow definition (creates new version)

    Args:
        workflow_id: Workflow ID
        definition: New definition

    Returns:
        Updated WorkflowDefinition

    Example:
        >>> update_workflow("my-strategy", {"version": "1.1.0", ...})
        {"id": "my-strategy", "version": "1.1.0", ...}
    """
    # Keep ID
    definition["id"] = workflow_id

    # Auto-increment version (if not specified)
    if "version" not in definition:
        old = get_workflow(workflow_id)
        if old:
            # Simple version increment (use semantic versioning parser in actual implementation)
            parts = old.get("version", "1.0.0").split(".")
            parts[-1] = str(int(parts[-1]) + 1)
            definition["version"] = ".".join(parts)

    return create_workflow(definition)


def delete_workflow(workflow_id: str) -> bool:
    """
    Delete workflow definition

    Args:
        workflow_id: Workflow ID to delete

    Returns:
        Whether deletion was successful

    Example:
        >>> delete_workflow("my-strategy")
        True
    """
    deleted = False

    # Delete both versioned keys and latest key
    keys_to_delete = [k for k in _workflows.keys() if k.startswith(workflow_id)]
    for key in keys_to_delete:
        del _workflows[key]
        deleted = True

    return deleted
