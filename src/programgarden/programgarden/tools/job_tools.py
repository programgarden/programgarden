"""
ProgramGarden - Job Tools

Workflow execution instance (Job) management tools
"""

from typing import Optional, List, Dict, Any
import asyncio

# Global executor (singleton)
_executor = None


def _get_executor():
    """Executor singleton"""
    global _executor
    if _executor is None:
        from programgarden.executor import WorkflowExecutor
        _executor = WorkflowExecutor()
    return _executor


def start_job(
    workflow_id: str,
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Start workflow execution

    Args:
        workflow_id: Workflow ID to execute
        context: Execution context (credential_id, symbols, etc.)

    Returns:
        Created WorkflowJob info

    Example:
        >>> start_job("my-strategy", {"credential_id": "cred-001", "symbols": ["AAPL"]})
        {"job_id": "job-abc123", "status": "running", ...}
    """
    from programgarden.tools.definition_tools import get_workflow

    # Get workflow definition
    definition = get_workflow(workflow_id)
    if not definition:
        raise ValueError(f"Workflow not found: {workflow_id}")

    # Async execution
    executor = _get_executor()

    async def _start():
        job = await executor.execute(definition, context)
        return job.get_state()

    return asyncio.run(_start())


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Get Job state

    Args:
        job_id: Job ID

    Returns:
        Job state or None

    Example:
        >>> get_job("job-abc123")
        {"job_id": "job-abc123", "status": "running", "stats": {...}, ...}
    """
    executor = _get_executor()
    job = executor.get_job(job_id)
    return job.get_state() if job else None


def list_jobs(
    workflow_id: Optional[str] = None,
    status: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    List Jobs

    Args:
        workflow_id: Workflow ID filter
        status: Status filter (pending, running, paused, completed, failed, cancelled)

    Returns:
        List of Jobs

    Example:
        >>> list_jobs(status="running")
        [{"job_id": "job-abc123", "status": "running", ...}]
    """
    executor = _get_executor()
    jobs = executor.list_jobs()

    result = []
    for job in jobs:
        state = job.get_state()

        if workflow_id and state.get("workflow_id") != workflow_id:
            continue
        if status and state.get("status") != status:
            continue

        result.append(state)

    return result


def pause_job(job_id: str, save_state: bool = True) -> Dict[str, Any]:
    """
    Pause Job

    Args:
        job_id: Job ID
        save_state: Whether to save state (for Graceful Restart)

    Returns:
        Updated Job state

    Example:
        >>> pause_job("job-abc123")
        {"job_id": "job-abc123", "status": "paused", ...}
    """
    executor = _get_executor()
    job = executor.get_job(job_id)

    if not job:
        raise ValueError(f"Job not found: {job_id}")

    async def _pause():
        await job.pause()
        return job.get_state()

    return asyncio.run(_pause())


def resume_job(job_id: str, restore_state: bool = True) -> Dict[str, Any]:
    """
    Resume Job

    Args:
        job_id: Job ID
        restore_state: Whether to restore state (for Graceful Restart)

    Returns:
        Updated Job state

    Example:
        >>> resume_job("job-abc123")
        {"job_id": "job-abc123", "status": "running", ...}
    """
    executor = _get_executor()
    job = executor.get_job(job_id)

    if not job:
        raise ValueError(f"Job not found: {job_id}")

    async def _resume():
        await job.resume()
        return job.get_state()

    return asyncio.run(_resume())


def cancel_job(job_id: str) -> Dict[str, Any]:
    """
    Cancel Job

    Args:
        job_id: Job ID

    Returns:
        Updated Job state

    Example:
        >>> cancel_job("job-abc123")
        {"job_id": "job-abc123", "status": "cancelled", ...}
    """
    executor = _get_executor()
    job = executor.get_job(job_id)

    if not job:
        raise ValueError(f"Job not found: {job_id}")

    async def _cancel():
        await job.cancel()
        return job.get_state()

    return asyncio.run(_cancel())


def get_job_state(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Get Job state snapshot (for Graceful Restart)

    Args:
        job_id: Job ID

    Returns:
        JobState snapshot (positions, balances, pending_orders, etc.)

    Example:
        >>> get_job_state("job-abc123")
        {"job_id": "job-abc123", "positions": {...}, "balances": {...}, ...}
    """
    # TODO: Implement actual state snapshot
    job = get_job(job_id)
    if not job:
        return None

    return {
        "job_id": job_id,
        "paused_at": job.get("paused_at"),
        "positions": {},
        "balances": {},
        "pending_orders": [],
        "condition_states": {},
        "can_restore": True,
    }


def emergency_close_all(job_id: str) -> Dict[str, Any]:
    """
    Emergency close all positions

    Close all positions at market price and cancel pending orders

    Args:
        job_id: Job ID

    Returns:
        Close result

    Example:
        >>> emergency_close_all("job-abc123")
        {"closed_positions": [...], "cancelled_orders": [...], ...}
    """
    # TODO: Implement actual close
    return {
        "job_id": job_id,
        "closed_positions": [],
        "cancelled_orders": [],
        "status": "emergency_closed",
    }


def cancel_all_orders(job_id: str) -> Dict[str, Any]:
    """
    Cancel all pending orders

    Args:
        job_id: Job ID

    Returns:
        Cancel result

    Example:
        >>> cancel_all_orders("job-abc123")
        {"cancelled_orders": [...], "failed_orders": [...]}
    """
    # TODO: Implement actual cancel
    return {
        "job_id": job_id,
        "cancelled_orders": [],
        "failed_orders": [],
    }


def restore_job(
    definition: Dict[str, Any],
    job_id: str,
    secrets: Optional[Dict[str, Any]] = None,
    listeners: Optional[List] = None,
    storage_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    체크포인트에서 워크플로우 복원

    서버 재시작 후 중단된 워크플로우를 복구합니다.
    일회성 워크플로우는 완료 노드 스킵 후 미완료 노드부터 재실행하고,
    실시간 워크플로우는 전체 재실행합니다.

    Args:
        definition: 워크플로우 정의 (원본과 동일해야 함)
        job_id: 복원할 Job ID
        secrets: 민감 자격증명
        listeners: ExecutionListener 목록
        storage_dir: DB 저장 디렉토리

    Returns:
        복원된 Job 상태

    Raises:
        ValueError: checkpoint 없음, 만료, 워크플로우 변경 시

    Example:
        >>> restore_job(definition, "job-abc123", secrets={"appkey": "..."})
        {"job_id": "job-abc123", "status": "running", ...}
    """
    executor = _get_executor()

    async def _restore():
        job = await executor.restore(
            definition=definition,
            job_id=job_id,
            secrets=secrets,
            listeners=listeners,
            storage_dir=storage_dir,
        )
        return job.get_state()

    return asyncio.run(_restore())


def has_checkpoint(
    workflow_id: str,
    job_id: str,
    storage_dir: Optional[str] = None,
) -> bool:
    """
    체크포인트 존재 여부 확인

    Args:
        workflow_id: Workflow ID
        job_id: Job ID
        storage_dir: DB 저장 디렉토리

    Returns:
        체크포인트 존재 여부

    Example:
        >>> has_checkpoint("my-strategy", "job-abc123")
        True
    """
    from programgarden.database.checkpoint_manager import CheckpointManager
    from pathlib import Path

    if storage_dir:
        db_dir = Path(storage_dir)
    elif Path("/app/data").exists():
        db_dir = Path("/app/data")
    else:
        db_dir = Path("./app/data")

    db_path = db_dir / f"{workflow_id}_workflow.db"
    if not db_path.exists():
        return False

    mgr = CheckpointManager(str(db_path))
    return mgr.has_checkpoint(job_id)


def get_checkpoint_info(
    workflow_id: str,
    job_id: str,
    storage_dir: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    체크포인트 요약 정보 조회 (outputs 제외, 경량)

    Args:
        workflow_id: Workflow ID
        job_id: Job ID
        storage_dir: DB 저장 디렉토리

    Returns:
        체크포인트 요약 또는 None

    Example:
        >>> get_checkpoint_info("my-strategy", "job-abc123")
        {"job_id": "job-abc123", "status": "running", "completed_nodes": [...], ...}
    """
    from programgarden.database.checkpoint_manager import CheckpointManager
    from pathlib import Path

    if storage_dir:
        db_dir = Path(storage_dir)
    elif Path("/app/data").exists():
        db_dir = Path("/app/data")
    else:
        db_dir = Path("./app/data")

    db_path = db_dir / f"{workflow_id}_workflow.db"
    if not db_path.exists():
        return None

    mgr = CheckpointManager(str(db_path))
    return mgr.get_checkpoint_info(job_id)
