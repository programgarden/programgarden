"""
ProgramGarden - Job Tools

워크플로우 실행 인스턴스(Job) 관리 도구
"""

from typing import Optional, List, Dict, Any
import asyncio

# 글로벌 실행기 (싱글톤)
_executor = None


def _get_executor():
    """실행기 싱글톤"""
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
    워크플로우 실행 시작

    Args:
        workflow_id: 실행할 워크플로우 ID
        context: 실행 컨텍스트 (credential_id, symbols 등)

    Returns:
        생성된 WorkflowJob 정보

    Example:
        >>> start_job("my-strategy", {"credential_id": "cred-001", "symbols": ["AAPL"]})
        {"job_id": "job-abc123", "status": "running", ...}
    """
    from programgarden.tools.definition_tools import get_workflow

    # 워크플로우 정의 조회
    definition = get_workflow(workflow_id)
    if not definition:
        raise ValueError(f"Workflow not found: {workflow_id}")

    # 비동기 실행
    executor = _get_executor()

    async def _start():
        job = await executor.execute(definition, context)
        return job.get_state()

    return asyncio.run(_start())


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Job 상태 조회

    Args:
        job_id: Job ID

    Returns:
        Job 상태 또는 None

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
    Job 목록 조회

    Args:
        workflow_id: 워크플로우 ID 필터
        status: 상태 필터 (pending, running, paused, completed, failed, cancelled)

    Returns:
        Job 목록

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
    Job 일시정지

    Args:
        job_id: Job ID
        save_state: 상태 저장 여부 (Graceful Restart용)

    Returns:
        업데이트된 Job 상태

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
    Job 재개

    Args:
        job_id: Job ID
        restore_state: 상태 복원 여부 (Graceful Restart용)

    Returns:
        업데이트된 Job 상태

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
    Job 취소

    Args:
        job_id: Job ID

    Returns:
        업데이트된 Job 상태

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
    Job 상태 스냅샷 조회 (Graceful Restart용)

    Args:
        job_id: Job ID

    Returns:
        JobState 스냅샷 (positions, balances, pending_orders 등)

    Example:
        >>> get_job_state("job-abc123")
        {"job_id": "job-abc123", "positions": {...}, "balances": {...}, ...}
    """
    # TODO: 실제 상태 스냅샷 구현
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
    비상 전체 청산

    모든 포지션을 시장가로 청산하고 미체결 주문 취소

    Args:
        job_id: Job ID

    Returns:
        청산 결과

    Example:
        >>> emergency_close_all("job-abc123")
        {"closed_positions": [...], "cancelled_orders": [...], ...}
    """
    # TODO: 실제 청산 구현
    return {
        "job_id": job_id,
        "closed_positions": [],
        "cancelled_orders": [],
        "status": "emergency_closed",
    }


def cancel_all_orders(job_id: str) -> Dict[str, Any]:
    """
    미체결 주문 일괄 취소

    Args:
        job_id: Job ID

    Returns:
        취소 결과

    Example:
        >>> cancel_all_orders("job-abc123")
        {"cancelled_orders": [...], "failed_orders": [...]}
    """
    # TODO: 실제 취소 구현
    return {
        "job_id": job_id,
        "cancelled_orders": [],
        "failed_orders": [],
    }
