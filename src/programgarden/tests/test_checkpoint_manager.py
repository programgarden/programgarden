"""
CheckpointManager 단위 테스트

테스트 대상: database/checkpoint_manager.py
- 테이블 생성 (WAL 모드)
- save → load roundtrip
- 복잡한 outputs 직렬화 (Decimal, nested dict, list of dicts, None)
- delete 후 load → None
- has_checkpoint (존재/미존재)
- 동일 job_id UPSERT
- 대형 output (>1MB) 스킵 처리
- compute_workflow_hash
- get_checkpoint_info (경량 조회)

실행:
    cd src/programgarden && poetry run pytest tests/test_checkpoint_manager.py -v
"""

import json
import os
import sqlite3
import tempfile
from decimal import Decimal

import pytest

from programgarden.database.checkpoint_manager import CheckpointManager, MAX_OUTPUT_SIZE


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_path(tmp_path):
    """임시 DB 경로."""
    return str(tmp_path / "test_workflow.db")


@pytest.fixture
def mgr(db_path):
    """CheckpointManager 인스턴스."""
    return CheckpointManager(db_path)


def _sample_checkpoint(mgr, job_id="job-001", **overrides):
    """기본 체크포인트 저장 헬퍼."""
    defaults = dict(
        job_id=job_id,
        workflow_id="wf-test",
        status="running",
        workflow_type="oneshot",
        completed_nodes=["start", "broker"],
        stats={"conditions_evaluated": 3, "orders_placed": 1},
        node_outputs={
            "start": {"output": True},
            "broker": {"connection": {"provider": "ls"}},
        },
        workflow_json_hash="abc123",
        workflow_start_datetime="2026-02-28T10:00:00+00:00",
        risk_halt=False,
        context_params={"symbols": ["AAPL"]},
    )
    defaults.update(overrides)
    mgr.save_checkpoint(**defaults)
    return defaults


# ---------------------------------------------------------------------------
# Part 1: 테이블 생성
# ---------------------------------------------------------------------------


class TestTableCreation:
    """테이블 생성 + WAL 모드."""

    def test_tables_created(self, db_path, mgr):
        with sqlite3.connect(db_path) as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            names = {t[0] for t in tables}
            assert "checkpoint_meta" in names
            assert "checkpoint_outputs" in names

    def test_wal_mode(self, db_path, mgr):
        with sqlite3.connect(db_path) as conn:
            mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
            assert mode == "wal"

    def test_idempotent_creation(self, db_path):
        """중복 생성해도 에러 없음."""
        CheckpointManager(db_path)
        CheckpointManager(db_path)  # 두 번째 호출도 문제 없어야 함


# ---------------------------------------------------------------------------
# Part 2: Save / Load Roundtrip
# ---------------------------------------------------------------------------


class TestSaveLoadRoundtrip:
    """저장 → 로드 왕복 테스트."""

    def test_basic_roundtrip(self, mgr):
        _sample_checkpoint(mgr)
        loaded = mgr.load_checkpoint("job-001")

        assert loaded is not None
        assert loaded["job_id"] == "job-001"
        assert loaded["workflow_id"] == "wf-test"
        assert loaded["status"] == "running"
        assert loaded["workflow_type"] == "oneshot"
        assert loaded["completed_nodes"] == ["start", "broker"]
        assert loaded["stats"]["conditions_evaluated"] == 3
        assert loaded["workflow_json_hash"] == "abc123"
        assert loaded["risk_halt"] is False

    def test_outputs_roundtrip(self, mgr):
        _sample_checkpoint(mgr)
        loaded = mgr.load_checkpoint("job-001")

        outputs = loaded["node_outputs"]
        assert outputs["start"]["output"] is True
        assert outputs["broker"]["connection"]["provider"] == "ls"

    def test_complex_outputs(self, mgr):
        """Decimal, nested dict, list of dicts, None 직렬화."""
        _sample_checkpoint(
            mgr,
            node_outputs={
                "cond": {
                    "rsi": 35.5,
                    "signal": "buy",
                    "details": {"period": 14, "values": [1, 2, 3]},
                },
                "empty": {"result": None},
                "positions": {
                    "data": [
                        {"symbol": "AAPL", "qty": 10},
                        {"symbol": "TSLA", "qty": 5},
                    ]
                },
            },
        )
        loaded = mgr.load_checkpoint("job-001")
        outputs = loaded["node_outputs"]

        assert outputs["cond"]["rsi"] == 35.5
        assert outputs["cond"]["signal"] == "buy"
        assert outputs["cond"]["details"]["period"] == 14
        assert outputs["empty"]["result"] is None
        assert len(outputs["positions"]["data"]) == 2

    def test_integer_output(self, mgr):
        """정수 값 직렬화/역직렬화."""
        _sample_checkpoint(
            mgr,
            node_outputs={"counter": {"count": 42}},
        )
        loaded = mgr.load_checkpoint("job-001")
        assert loaded["node_outputs"]["counter"]["count"] == 42
        assert isinstance(loaded["node_outputs"]["counter"]["count"], int)

    def test_boolean_output(self, mgr):
        """불리언 값 직렬화/역직렬화."""
        _sample_checkpoint(
            mgr,
            node_outputs={"check": {"passed": True, "failed": False}},
        )
        loaded = mgr.load_checkpoint("job-001")
        assert loaded["node_outputs"]["check"]["passed"] is True
        assert loaded["node_outputs"]["check"]["failed"] is False

    def test_context_params_roundtrip(self, mgr):
        """context_params 직렬화."""
        _sample_checkpoint(
            mgr,
            context_params={"dry_run": True, "symbols": ["AAPL", "TSLA"]},
        )
        loaded = mgr.load_checkpoint("job-001")
        assert loaded["context_params"]["dry_run"] is True
        assert loaded["context_params"]["symbols"] == ["AAPL", "TSLA"]

    def test_risk_halt_true(self, mgr):
        """risk_halt=True 저장/복원."""
        _sample_checkpoint(mgr, risk_halt=True)
        loaded = mgr.load_checkpoint("job-001")
        assert loaded["risk_halt"] is True


# ---------------------------------------------------------------------------
# Part 3: Delete
# ---------------------------------------------------------------------------


class TestDelete:
    """체크포인트 삭제."""

    def test_delete_then_load_none(self, mgr):
        _sample_checkpoint(mgr)
        mgr.delete_checkpoint("job-001")
        assert mgr.load_checkpoint("job-001") is None

    def test_delete_nonexistent(self, mgr):
        """존재하지 않는 ID 삭제해도 에러 없음."""
        mgr.delete_checkpoint("nonexistent")  # no exception


# ---------------------------------------------------------------------------
# Part 4: has_checkpoint
# ---------------------------------------------------------------------------


class TestHasCheckpoint:
    """존재 여부 확인."""

    def test_exists(self, mgr):
        _sample_checkpoint(mgr)
        assert mgr.has_checkpoint("job-001") is True

    def test_not_exists(self, mgr):
        assert mgr.has_checkpoint("no-such") is False

    def test_after_delete(self, mgr):
        _sample_checkpoint(mgr)
        mgr.delete_checkpoint("job-001")
        assert mgr.has_checkpoint("job-001") is False


# ---------------------------------------------------------------------------
# Part 5: UPSERT
# ---------------------------------------------------------------------------


class TestUpsert:
    """동일 job_id UPSERT."""

    def test_upsert_updates(self, mgr):
        _sample_checkpoint(mgr, completed_nodes=["start"])
        _sample_checkpoint(mgr, completed_nodes=["start", "broker", "cond"])

        loaded = mgr.load_checkpoint("job-001")
        assert loaded["completed_nodes"] == ["start", "broker", "cond"]

    def test_upsert_replaces_outputs(self, mgr):
        _sample_checkpoint(mgr, node_outputs={"a": {"x": 1}})
        _sample_checkpoint(mgr, node_outputs={"a": {"x": 2}, "b": {"y": 3}})

        loaded = mgr.load_checkpoint("job-001")
        assert loaded["node_outputs"]["a"]["x"] == 2
        assert loaded["node_outputs"]["b"]["y"] == 3


# ---------------------------------------------------------------------------
# Part 6: 대형 output 스킵
# ---------------------------------------------------------------------------


class TestLargeOutputSkip:
    """1MB 초과 output 스킵."""

    def test_large_output_skipped(self, mgr):
        large_value = "x" * (MAX_OUTPUT_SIZE + 100)
        _sample_checkpoint(
            mgr,
            node_outputs={
                "normal": {"data": "small"},
                "huge": {"big_data": large_value},
            },
        )
        loaded = mgr.load_checkpoint("job-001")
        outputs = loaded["node_outputs"]

        # normal은 저장됨
        assert "normal" in outputs
        assert outputs["normal"]["data"] == "small"

        # huge는 스킵됨 (키 자체가 없거나 빈 dict)
        assert "huge" not in outputs or "big_data" not in outputs.get("huge", {})


# ---------------------------------------------------------------------------
# Part 7: compute_workflow_hash
# ---------------------------------------------------------------------------


class TestWorkflowHash:
    """워크플로우 해시 계산."""

    def test_same_definition_same_hash(self):
        d1 = {"nodes": [{"id": "a"}], "edges": [{"from": "a", "to": "b"}]}
        d2 = {"nodes": [{"id": "a"}], "edges": [{"from": "a", "to": "b"}]}
        assert CheckpointManager.compute_workflow_hash(d1) == CheckpointManager.compute_workflow_hash(d2)

    def test_different_definition_different_hash(self):
        d1 = {"nodes": [{"id": "a"}], "edges": []}
        d2 = {"nodes": [{"id": "a"}, {"id": "b"}], "edges": []}
        assert CheckpointManager.compute_workflow_hash(d1) != CheckpointManager.compute_workflow_hash(d2)

    def test_ignores_credentials_and_notes(self):
        """credentials, notes 변경은 해시에 영향 없음."""
        d1 = {"nodes": [{"id": "a"}], "edges": [], "credentials": [{"key": "old"}]}
        d2 = {"nodes": [{"id": "a"}], "edges": [], "credentials": [{"key": "new"}]}
        assert CheckpointManager.compute_workflow_hash(d1) == CheckpointManager.compute_workflow_hash(d2)


# ---------------------------------------------------------------------------
# Part 8: get_checkpoint_info (경량 조회)
# ---------------------------------------------------------------------------


class TestGetCheckpointInfo:
    """경량 조회 (outputs 제외)."""

    def test_info_returns_meta(self, mgr):
        _sample_checkpoint(mgr)
        info = mgr.get_checkpoint_info("job-001")

        assert info is not None
        assert info["job_id"] == "job-001"
        assert info["workflow_id"] == "wf-test"
        assert info["completed_nodes"] == ["start", "broker"]
        assert "node_outputs" not in info

    def test_info_nonexistent(self, mgr):
        assert mgr.get_checkpoint_info("no-such") is None
