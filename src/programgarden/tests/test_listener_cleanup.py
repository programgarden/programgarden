"""
리스너 정리 테스트

stop()/cancel() 호출 시 ExecutionContext._listeners가 정리되는지 확인
"""

import asyncio

import pytest

from programgarden.executor import WorkflowExecutor
from programgarden_core.bases.listener import BaseExecutionListener


# ─────────────────────────────────────────────────
# 테스트용 워크플로우
# ─────────────────────────────────────────────────

SIMPLE_WORKFLOW = {
    "id": "test-workflow",
    "name": "테스트 워크플로우",
    "nodes": [
        {"id": "start", "type": "StartNode"},
    ],
    "edges": [],
}


# ─────────────────────────────────────────────────
# 테스트용 리스너
# ─────────────────────────────────────────────────

class MockListener(BaseExecutionListener):
    """기본 테스트 리스너"""

    def __init__(self):
        self.closed = False

    async def on_node_state_change(self, event):
        pass


class CloseableListener(BaseExecutionListener):
    """close() 메서드가 있는 리스너"""

    def __init__(self):
        self.closed = False

    async def close(self):
        self.closed = True

    async def on_node_state_change(self, event):
        pass


class DisposableListener(BaseExecutionListener):
    """dispose() 메서드가 있는 리스너"""

    def __init__(self):
        self.disposed = False

    async def dispose(self):
        self.disposed = True

    async def on_node_state_change(self, event):
        pass


class ErrorListener(BaseExecutionListener):
    """close()에서 예외 발생하는 리스너"""

    async def close(self):
        raise RuntimeError("close failed")

    async def on_node_state_change(self, event):
        pass


# ─────────────────────────────────────────────────
# Fixture
# ─────────────────────────────────────────────────

@pytest.fixture
def executor():
    return WorkflowExecutor()


# ─────────────────────────────────────────────────
# 테스트
# ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stop_clears_listeners(executor):
    """stop() 호출 후 _listeners가 비어있는지 확인"""
    listener = MockListener()
    job = await executor.execute(
        SIMPLE_WORKFLOW,
        job_id="test-stop",
        listeners=[listener],
    )

    # job이 완료될 때까지 대기
    try:
        await asyncio.wait_for(job._task, timeout=5.0)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        pass

    await job.stop()
    assert len(job.context._listeners) == 0


@pytest.mark.asyncio
async def test_cancel_clears_listeners(executor):
    """cancel() 호출 후 _listeners가 비어있는지 확인"""
    listener = MockListener()
    job = await executor.execute(
        SIMPLE_WORKFLOW,
        job_id="test-cancel",
        listeners=[listener],
    )

    try:
        await asyncio.wait_for(job._task, timeout=5.0)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        pass

    await job.cancel()
    assert len(job.context._listeners) == 0


@pytest.mark.asyncio
async def test_closeable_listener_closed_on_stop(executor):
    """stop() 시 close() 메서드가 있는 리스너가 정리되는지 확인"""
    listener = CloseableListener()
    job = await executor.execute(
        SIMPLE_WORKFLOW,
        job_id="test-closeable",
        listeners=[listener],
    )

    try:
        await asyncio.wait_for(job._task, timeout=5.0)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        pass

    await job.stop()
    assert listener.closed is True


@pytest.mark.asyncio
async def test_disposable_listener_disposed_on_cancel(executor):
    """cancel() 시 dispose() 메서드가 있는 리스너가 정리되는지 확인"""
    listener = DisposableListener()
    job = await executor.execute(
        SIMPLE_WORKFLOW,
        job_id="test-disposable",
        listeners=[listener],
    )

    try:
        await asyncio.wait_for(job._task, timeout=5.0)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        pass

    await job.cancel()
    assert listener.disposed is True


@pytest.mark.asyncio
async def test_cleanup_listeners_idempotent(executor):
    """cleanup_listeners() 중복 호출 시 에러 없는지 확인"""
    listener = CloseableListener()
    job = await executor.execute(
        SIMPLE_WORKFLOW,
        job_id="test-idempotent",
        listeners=[listener],
    )

    try:
        await asyncio.wait_for(job._task, timeout=5.0)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        pass

    await job.context.cleanup_listeners()
    await job.context.cleanup_listeners()  # 두 번째 호출도 안전
    assert len(job.context._listeners) == 0
    assert listener.closed is True


@pytest.mark.asyncio
async def test_error_in_listener_close_does_not_propagate(executor):
    """리스너 close()에서 예외 발생해도 다른 리스너 정리가 계속되는지 확인"""
    error_listener = ErrorListener()
    closeable_listener = CloseableListener()
    job = await executor.execute(
        SIMPLE_WORKFLOW,
        job_id="test-error-listener",
        listeners=[error_listener, closeable_listener],
    )

    try:
        await asyncio.wait_for(job._task, timeout=5.0)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        pass

    await job.stop()
    # ErrorListener의 예외가 전파되지 않고, CloseableListener도 정리됨
    assert closeable_listener.closed is True
    assert len(job.context._listeners) == 0


@pytest.mark.asyncio
async def test_remove_job(executor):
    """완료된 job이 executor에서 제거되는지 확인"""
    job = await executor.execute(
        SIMPLE_WORKFLOW,
        job_id="test-remove",
    )

    try:
        await asyncio.wait_for(job._task, timeout=5.0)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        pass

    await job.stop()

    # 완료된 job 제거
    assert executor.remove_job("test-remove") is True
    assert executor.get_job("test-remove") is None

    # 존재하지 않는 job 제거 시도
    assert executor.remove_job("nonexistent") is False
