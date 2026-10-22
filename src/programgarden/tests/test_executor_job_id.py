"""
Job ID 중복 체크 테스트

WorkflowExecutor의 job_id 중복 방지 로직 테스트
"""

import pytest

from programgarden.executor import WorkflowExecutor
from programgarden_core.exceptions import DuplicateJobIdError


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
# Fixture
# ─────────────────────────────────────────────────

@pytest.fixture
def executor():
    """WorkflowExecutor 인스턴스"""
    return WorkflowExecutor()


# ─────────────────────────────────────────────────
# 테스트
# ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_duplicate_job_id_raises_error(executor):
    """동일한 job_id로 실행 시 DuplicateJobIdError 발생"""
    # 첫 번째 실행
    job1 = await executor.execute(SIMPLE_WORKFLOW, job_id="test-job-1")
    assert job1.job_id == "test-job-1"

    # 동일 job_id로 두 번째 실행 시도
    with pytest.raises(DuplicateJobIdError) as exc_info:
        await executor.execute(SIMPLE_WORKFLOW, job_id="test-job-1")

    assert exc_info.value.job_id == "test-job-1"
    assert "이미 사용 중" in exc_info.value.message
    assert exc_info.value.details.get("existing_job_status") is not None


@pytest.mark.asyncio
async def test_different_job_ids_succeed(executor):
    """서로 다른 job_id로 실행 시 성공"""
    job1 = await executor.execute(SIMPLE_WORKFLOW, job_id="job-a")
    job2 = await executor.execute(SIMPLE_WORKFLOW, job_id="job-b")

    assert job1.job_id == "job-a"
    assert job2.job_id == "job-b"
    assert job1.job_id != job2.job_id


@pytest.mark.asyncio
async def test_auto_generated_job_ids_no_collision(executor):
    """job_id 미지정 시 자동 생성되어 충돌 없음"""
    job1 = await executor.execute(SIMPLE_WORKFLOW)
    job2 = await executor.execute(SIMPLE_WORKFLOW)

    assert job1.job_id.startswith("job-")
    assert job2.job_id.startswith("job-")
    assert job1.job_id != job2.job_id


@pytest.mark.asyncio
async def test_duplicate_error_contains_existing_status(executor):
    """DuplicateJobIdError에 기존 job 상태 정보 포함"""
    job1 = await executor.execute(SIMPLE_WORKFLOW, job_id="status-test")

    with pytest.raises(DuplicateJobIdError) as exc_info:
        await executor.execute(SIMPLE_WORKFLOW, job_id="status-test")

    # details에 기존 job 상태 포함 확인
    assert "existing_job_status" in exc_info.value.details
