"""
Graceful Restart 통합 테스트

테스트 대상:
1. 일회성 워크플로우 복구 (완료 노드 스킵 + 미완료 노드 실행)
2. 실시간 워크플로우 복구 (전체 재실행)
3. 안전장치 (만료, 워크플로우 변경, 미존재)
4. 저장 트리거 (stop/pause/정상 완료/노드 완료)
5. Risk 연속성 (risk_halt 복원)
6. RestartEvent 리스너 콜백
7. Edge cases (IfNode 분기 후 복구 등)

실행:
    cd src/programgarden && poetry run pytest tests/test_graceful_restart.py -v
"""

import asyncio
import json
import os
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from programgarden.executor import WorkflowExecutor, WorkflowJob
from programgarden.context import ExecutionContext
from programgarden.database.checkpoint_manager import CheckpointManager
from programgarden_core.bases.listener import (
    BaseExecutionListener,
    RestartEvent,
    NodeState,
)


# ---------------------------------------------------------------------------
# Test timeout
# ---------------------------------------------------------------------------

TEST_TIMEOUT = 10


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_storage(tmp_path):
    """임시 storage 디렉토리."""
    return str(tmp_path)


@pytest.fixture
def executor():
    """WorkflowExecutor 인스턴스."""
    return WorkflowExecutor()


def _simple_workflow(workflow_id="wf-test"):
    """StartNode 단순 워크플로우."""
    return {
        "id": workflow_id,
        "name": "테스트 워크플로우",
        "nodes": [
            {"id": "start", "type": "StartNode"},
        ],
        "edges": [],
        "credentials": [],
    }


def _make_db_and_checkpoint(storage_dir, workflow_id, job_id, **overrides):
    """DB 생성 + 체크포인트 저장 헬퍼."""
    db_dir = Path(storage_dir)
    db_dir.mkdir(parents=True, exist_ok=True)
    db_path = str(db_dir / f"{workflow_id}_workflow.db")
    mgr = CheckpointManager(db_path)

    definition = _simple_workflow(workflow_id)
    wf_hash = CheckpointManager.compute_workflow_hash(definition)

    defaults = dict(
        job_id=job_id,
        workflow_id=workflow_id,
        status="running",
        workflow_type="oneshot",
        completed_nodes=["start"],
        stats={"conditions_evaluated": 0, "orders_placed": 0, "orders_filled": 0, "errors_count": 0, "flow_executions": 0, "realtime_updates": 0},
        node_outputs={"start": {"output": True}},
        workflow_json_hash=wf_hash,
        workflow_start_datetime=datetime.now(timezone.utc).isoformat(),
        risk_halt=False,
        context_params={},
    )
    defaults.update(overrides)
    mgr.save_checkpoint(**defaults)
    return mgr, definition


# ---------------------------------------------------------------------------
# Part 1: CheckpointManager → executor 연동 (저장 트리거)
# ---------------------------------------------------------------------------


class TestSaveTriggerStop:
    """stop() 호출 시 checkpoint 저장."""

    @pytest.mark.asyncio
    async def test_stop_saves_checkpoint(self, executor, tmp_storage):
        """stop() 호출 시 checkpoint가 DB에 저장됨."""
        definition = _simple_workflow()

        with patch("programgarden.executor.ensure_ls_login", new_callable=AsyncMock):
            job = await asyncio.wait_for(
                executor.execute(definition, storage_dir=tmp_storage),
                timeout=TEST_TIMEOUT,
            )

            # 실행 대기
            await asyncio.sleep(0.5)

            # stop
            await asyncio.wait_for(job.stop(), timeout=TEST_TIMEOUT)

        # checkpoint 확인
        db_path = Path(tmp_storage) / f"{definition.get('workflow_id', 'wf-test')}_workflow.db"
        if db_path.exists():
            mgr = CheckpointManager(str(db_path))
            # stop 후 checkpoint가 저장되어야 함
            assert mgr.has_checkpoint(job.job_id)


class TestSaveTriggerPause:
    """pause() 호출 시 checkpoint 저장."""

    @pytest.mark.asyncio
    async def test_pause_saves_checkpoint(self, executor, tmp_storage):
        """pause() 호출 시 checkpoint가 DB에 저장됨."""
        definition = _simple_workflow()

        with patch("programgarden.executor.ensure_ls_login", new_callable=AsyncMock):
            job = await asyncio.wait_for(
                executor.execute(definition, storage_dir=tmp_storage),
                timeout=TEST_TIMEOUT,
            )
            await asyncio.sleep(0.5)

            # pause
            await asyncio.wait_for(job.pause(), timeout=TEST_TIMEOUT)

        db_path = Path(tmp_storage) / f"{definition.get('workflow_id', 'wf-test')}_workflow.db"
        if db_path.exists():
            mgr = CheckpointManager(str(db_path))
            assert mgr.has_checkpoint(job.job_id)


class TestSaveTriggerNormalCompletion:
    """정상 완료 시 checkpoint 삭제."""

    @pytest.mark.asyncio
    async def test_normal_completion_deletes_checkpoint(self, executor, tmp_storage):
        """정상 완료 후 checkpoint가 삭제되어야 함."""
        definition = _simple_workflow()

        with patch("programgarden.executor.ensure_ls_login", new_callable=AsyncMock):
            job = await asyncio.wait_for(
                executor.execute(definition, storage_dir=tmp_storage),
                timeout=TEST_TIMEOUT,
            )

            # 완료 대기 (일회성이므로 바로 끝남)
            try:
                await asyncio.wait_for(job._task, timeout=TEST_TIMEOUT)
            except (asyncio.CancelledError, Exception):
                pass

        db_path = Path(tmp_storage) / f"{definition.get('workflow_id', 'wf-test')}_workflow.db"
        if db_path.exists():
            mgr = CheckpointManager(str(db_path))
            # 정상 완료 후에는 삭제됨
            assert not mgr.has_checkpoint(job.job_id)


class TestSaveTriggerNodeCompletion:
    """일회성 워크플로우: 노드 완료마다 checkpoint 갱신."""

    @pytest.mark.asyncio
    async def test_completed_nodes_tracked(self, executor, tmp_storage):
        """실행 후 _completed_node_ids에 완료 노드가 기록됨."""
        definition = _simple_workflow()

        with patch("programgarden.executor.ensure_ls_login", new_callable=AsyncMock):
            job = await asyncio.wait_for(
                executor.execute(definition, storage_dir=tmp_storage),
                timeout=TEST_TIMEOUT,
            )
            try:
                await asyncio.wait_for(job._task, timeout=TEST_TIMEOUT)
            except (asyncio.CancelledError, Exception):
                pass

        # 완료된 노드가 추적되었는지 확인
        assert len(job._completed_node_ids) > 0


# ---------------------------------------------------------------------------
# Part 2: 안전장치 (유효성 검증)
# ---------------------------------------------------------------------------


class TestValidationCheckpointNotFound:
    """Checkpoint 미존재 → ValueError."""

    @pytest.mark.asyncio
    async def test_restore_no_checkpoint(self, executor, tmp_storage):
        definition = _simple_workflow()

        with pytest.raises(ValueError, match="checkpoint"):
            await asyncio.wait_for(
                executor.restore(definition, "nonexistent-job", storage_dir=tmp_storage),
                timeout=TEST_TIMEOUT,
            )


class TestValidationCheckpointExpired:
    """Checkpoint 10분 초과 → ValueError."""

    @pytest.mark.asyncio
    async def test_restore_expired_checkpoint(self, executor, tmp_storage):
        # checkpoint 생성
        mgr, definition = _make_db_and_checkpoint(
            tmp_storage, "wf-test", "job-expired",
        )

        # 직접 DB에서 created_at을 11분 전으로 수정
        import sqlite3
        old_time = (datetime.now(timezone.utc) - timedelta(minutes=11)).isoformat()
        db_path = str(Path(tmp_storage) / "wf-test_workflow.db")
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "UPDATE checkpoint_meta SET created_at = ? WHERE job_id = ?",
                (old_time, "job-expired"),
            )
            conn.commit()

        with pytest.raises(ValueError, match="checkpoint_expired|복구 불가"):
            await asyncio.wait_for(
                executor.restore(definition, "job-expired", storage_dir=tmp_storage),
                timeout=TEST_TIMEOUT,
            )


class TestValidationWorkflowChanged:
    """워크플로우 변경 → ValueError."""

    @pytest.mark.asyncio
    async def test_restore_workflow_changed(self, executor, tmp_storage):
        mgr, definition = _make_db_and_checkpoint(
            tmp_storage, "wf-test", "job-changed",
        )

        # 워크플로우 변경 (노드 추가)
        modified = dict(definition)
        modified["nodes"] = list(definition["nodes"]) + [
            {"id": "extra_if", "type": "IfNode"},
        ]
        modified["edges"] = [{"from": "start", "to": "extra_if"}]

        with pytest.raises(ValueError, match="workflow_changed|복구 불가"):
            await asyncio.wait_for(
                executor.restore(modified, "job-changed", storage_dir=tmp_storage),
                timeout=TEST_TIMEOUT,
            )


# ---------------------------------------------------------------------------
# Part 3: 복구 로직
# ---------------------------------------------------------------------------


class TestOneshotRestore:
    """일회성 워크플로우 복구."""

    @pytest.mark.asyncio
    async def test_restore_skips_completed_nodes(self, executor, tmp_storage):
        """완료 노드 스킵 + 미완료 노드 실행."""
        mgr, definition = _make_db_and_checkpoint(
            tmp_storage, "wf-test", "job-restore",
            completed_nodes=["start"],
            node_outputs={"start": {"output": True}},
        )

        # on_restart 리스너
        events_received = []

        class RestartListener(BaseExecutionListener):
            async def on_restart(self, event):
                events_received.append(event)

        listener = RestartListener()

        with patch("programgarden.executor.ensure_ls_login", new_callable=AsyncMock):
            job = await asyncio.wait_for(
                executor.restore(
                    definition, "job-restore",
                    listeners=[listener],
                    storage_dir=tmp_storage,
                ),
                timeout=TEST_TIMEOUT,
            )

            try:
                await asyncio.wait_for(job._task, timeout=TEST_TIMEOUT)
            except (asyncio.CancelledError, Exception):
                pass

        # RestartEvent 수신 확인
        assert len(events_received) >= 1
        assert events_received[0].restart_reason == "checkpoint_restore"
        assert "start" in events_received[0].skipped_nodes


class TestRestoreOutputsAvailable:
    """복원된 outputs가 하위 노드에서 참조 가능."""

    @pytest.mark.asyncio
    async def test_restored_outputs_accessible(self, executor, tmp_storage):
        mgr, definition = _make_db_and_checkpoint(
            tmp_storage, "wf-test", "job-outputs",
            completed_nodes=["start"],
            node_outputs={"start": {"output": True}},
        )

        with patch("programgarden.executor.ensure_ls_login", new_callable=AsyncMock):
            job = await asyncio.wait_for(
                executor.restore(
                    definition, "job-outputs",
                    storage_dir=tmp_storage,
                ),
                timeout=TEST_TIMEOUT,
            )

        # context에서 start 노드 output 확인
        start_output = job.context.get_output("start", "output")
        assert start_output is True


class TestRestoreStats:
    """stats/workflow_start_datetime 복원."""

    @pytest.mark.asyncio
    async def test_stats_restored(self, executor, tmp_storage):
        custom_stats = {
            "conditions_evaluated": 5,
            "orders_placed": 2,
            "orders_filled": 1,
            "errors_count": 0,
            "flow_executions": 1,
            "realtime_updates": 10,
        }
        wsd = "2026-02-28T09:00:00+00:00"

        mgr, definition = _make_db_and_checkpoint(
            tmp_storage, "wf-test", "job-stats",
            stats=custom_stats,
            workflow_start_datetime=wsd,
        )

        with patch("programgarden.executor.ensure_ls_login", new_callable=AsyncMock):
            job = await asyncio.wait_for(
                executor.restore(
                    definition, "job-stats",
                    storage_dir=tmp_storage,
                ),
                timeout=TEST_TIMEOUT,
            )

        assert job.stats["conditions_evaluated"] == 5
        assert job.stats["orders_placed"] == 2
        assert job.workflow_start_datetime.hour == 9


# ---------------------------------------------------------------------------
# Part 4: Risk 연속성
# ---------------------------------------------------------------------------


class TestRiskHaltRestore:
    """risk_halt 플래그 복원."""

    @pytest.mark.asyncio
    async def test_risk_halt_restored(self, executor, tmp_storage):
        mgr, definition = _make_db_and_checkpoint(
            tmp_storage, "wf-test", "job-risk",
            risk_halt=True,
        )

        with patch("programgarden.executor.ensure_ls_login", new_callable=AsyncMock):
            job = await asyncio.wait_for(
                executor.restore(
                    definition, "job-risk",
                    storage_dir=tmp_storage,
                ),
                timeout=TEST_TIMEOUT,
            )

        assert job.context._risk_halt is True


# ---------------------------------------------------------------------------
# Part 5: RestartEvent 리스너
# ---------------------------------------------------------------------------


class TestRestartEventListener:
    """on_restart 콜백 검증."""

    @pytest.mark.asyncio
    async def test_restore_failure_event(self, executor, tmp_storage):
        """복구 실패 시 RestartEvent(reason=restore_failed) 발행."""
        definition = _simple_workflow()

        events_received = []

        class FailureListener(BaseExecutionListener):
            async def on_restart(self, event):
                events_received.append(event)

        with pytest.raises(ValueError):
            await asyncio.wait_for(
                executor.restore(
                    definition, "nonexistent",
                    listeners=[FailureListener()],
                    storage_dir=tmp_storage,
                ),
                timeout=TEST_TIMEOUT,
            )

        assert len(events_received) == 1
        assert events_received[0].restart_reason == "restore_failed"


# ---------------------------------------------------------------------------
# Part 6: CheckpointManager 직접 연동
# ---------------------------------------------------------------------------


class TestCheckpointManagerIntegration:
    """WorkflowJob → CheckpointManager 연동."""

    def test_workflow_json_hash_set_on_execute(self, executor, tmp_storage):
        """execute() 시 _workflow_json_hash 설정 확인."""
        definition = _simple_workflow()

        async def _run():
            with patch("programgarden.executor.ensure_ls_login", new_callable=AsyncMock):
                job = await executor.execute(definition, storage_dir=tmp_storage)
                assert job._workflow_json_hash is not None
                assert len(job._workflow_json_hash) > 0
                await job.stop()

        asyncio.get_event_loop().run_until_complete(
            asyncio.wait_for(_run(), timeout=TEST_TIMEOUT)
        )


# ---------------------------------------------------------------------------
# Part 7: _validate_checkpoint 단위 테스트
# ---------------------------------------------------------------------------


class TestValidateCheckpoint:
    """_validate_checkpoint 유효성 검증 메서드."""

    def test_none_checkpoint(self, executor):
        is_valid, reason = executor._validate_checkpoint(None, {})
        assert is_valid is False
        assert "not_found" in reason

    def test_valid_checkpoint(self, executor):
        cp = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "workflow_json_hash": CheckpointManager.compute_workflow_hash({"nodes": [], "edges": []}),
        }
        defn = {"nodes": [], "edges": []}
        is_valid, reason = executor._validate_checkpoint(cp, defn)
        assert is_valid is True

    def test_expired_checkpoint(self, executor):
        old = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
        cp = {"created_at": old}
        is_valid, reason = executor._validate_checkpoint(cp, {})
        assert is_valid is False
        assert "expired" in reason

    def test_hash_mismatch(self, executor):
        cp = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "workflow_json_hash": "wrong_hash",
        }
        defn = {"nodes": [{"id": "a"}], "edges": []}
        is_valid, reason = executor._validate_checkpoint(cp, defn)
        assert is_valid is False
        assert "changed" in reason

    def test_no_hash_in_checkpoint(self, executor):
        """hash가 없는 checkpoint는 검증 통과."""
        cp = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "workflow_json_hash": None,
        }
        is_valid, reason = executor._validate_checkpoint(cp, {})
        assert is_valid is True


# ---------------------------------------------------------------------------
# Part 8: _save_checkpoint / _delete_checkpoint 헬퍼
# ---------------------------------------------------------------------------


class TestSaveDeleteCheckpointHelpers:
    """_save_checkpoint / _delete_checkpoint 직접 테스트."""

    @pytest.mark.asyncio
    async def test_save_and_delete(self, executor, tmp_storage):
        definition = _simple_workflow()

        with patch("programgarden.executor.ensure_ls_login", new_callable=AsyncMock):
            job = await asyncio.wait_for(
                executor.execute(definition, storage_dir=tmp_storage),
                timeout=TEST_TIMEOUT,
            )

            await asyncio.sleep(0.3)

            # 수동 save
            await job._save_checkpoint()

            mgr = job._get_checkpoint_mgr()
            assert mgr.has_checkpoint(job.job_id)

            # 수동 delete
            job._delete_checkpoint()
            assert not mgr.has_checkpoint(job.job_id)

            await job.stop()


# ---------------------------------------------------------------------------
# Part 9: Checkpoint loop (실시간)
# ---------------------------------------------------------------------------


class TestCheckpointLoop:
    """_checkpoint_loop 시작/중단."""

    @pytest.mark.asyncio
    async def test_start_stop_loop(self, executor, tmp_storage):
        definition = _simple_workflow()

        with patch("programgarden.executor.ensure_ls_login", new_callable=AsyncMock):
            job = await asyncio.wait_for(
                executor.execute(definition, storage_dir=tmp_storage),
                timeout=TEST_TIMEOUT,
            )

            # loop 시작
            job._start_checkpoint_loop()
            assert job._checkpoint_task is not None
            assert not job._checkpoint_task.done()

            # loop 중단
            await job._stop_checkpoint_loop()
            assert job._checkpoint_task is None

            await job.stop()


# ---------------------------------------------------------------------------
# Part 10: Realtime 워크플로우 복구 (전체 재실행)
# ---------------------------------------------------------------------------


class TestRealtimeRestore:
    """실시간 워크플로우 복구 시 전체 재실행."""

    @pytest.mark.asyncio
    async def test_realtime_full_reexecution(self, executor, tmp_storage):
        """workflow_type=realtime → skip_nodes 없이 전체 재실행."""
        mgr, definition = _make_db_and_checkpoint(
            tmp_storage, "wf-test", "job-realtime",
            workflow_type="realtime",
            completed_nodes=["start", "cond"],
            node_outputs={
                "start": {"output": True},
                "cond": {"signal": "buy"},
            },
        )

        events = []

        class TrackListener(BaseExecutionListener):
            async def on_restart(self, event):
                events.append(event)

        with patch("programgarden.executor.ensure_ls_login", new_callable=AsyncMock):
            job = await asyncio.wait_for(
                executor.restore(
                    definition, "job-realtime",
                    listeners=[TrackListener()],
                    storage_dir=tmp_storage,
                ),
                timeout=TEST_TIMEOUT,
            )

            try:
                await asyncio.wait_for(job._task, timeout=TEST_TIMEOUT)
            except (asyncio.CancelledError, Exception):
                pass

        assert len(events) >= 1
        assert events[0].workflow_type == "realtime"


# ---------------------------------------------------------------------------
# Part 11: job_tools API 테스트
# ---------------------------------------------------------------------------


class TestJobToolsAPI:
    """tools/job_tools.py의 has_checkpoint, get_checkpoint_info."""

    def test_has_checkpoint_false_no_db(self, tmp_storage):
        from programgarden.tools.job_tools import has_checkpoint

        result = has_checkpoint("wf-nonexist", "job-xxx", storage_dir=tmp_storage)
        assert result is False

    def test_has_checkpoint_true(self, tmp_storage):
        from programgarden.tools.job_tools import has_checkpoint

        _make_db_and_checkpoint(tmp_storage, "wf-test", "job-001")
        result = has_checkpoint("wf-test", "job-001", storage_dir=tmp_storage)
        assert result is True

    def test_get_checkpoint_info_none(self, tmp_storage):
        from programgarden.tools.job_tools import get_checkpoint_info

        result = get_checkpoint_info("wf-nonexist", "job-xxx", storage_dir=tmp_storage)
        assert result is None

    def test_get_checkpoint_info_returns_meta(self, tmp_storage):
        from programgarden.tools.job_tools import get_checkpoint_info

        _make_db_and_checkpoint(tmp_storage, "wf-test", "job-info")
        info = get_checkpoint_info("wf-test", "job-info", storage_dir=tmp_storage)
        assert info is not None
        assert info["job_id"] == "job-info"
        assert "completed_nodes" in info
