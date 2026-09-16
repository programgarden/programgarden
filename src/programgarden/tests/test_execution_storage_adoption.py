"""Exercise SQLite/WAL adoption and ownership failures without broker transport."""

import json
from pathlib import Path
import sqlite3

import pytest

from programgarden.database.execution_storage import prepare_execution_storage, ExecutionStorageUnavailable


def marker(root, workflow="old", project="project", ids=None, **updates):
    path = root / f"{workflow}_execution.json"
    path.write_text(json.dumps({"workflow_id": workflow, "project_id": project,
                                "execution_ids": ["account-run"] if ids is None else ids,
                                "history": [], **updates}))
    return path


def legacy(root, workflow="old"):
    path = root / f"{workflow}_workflow.db"
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA wal_autocheckpoint=0")
    conn.execute("CREATE TABLE retained (value TEXT)")
    conn.execute("INSERT INTO retained VALUES ('committed-in-wal')")
    conn.commit()
    return conn, path


def prepare(root, **updates):
    return prepare_execution_storage(root, **{"project_id": "project", "workflow_id": "old",
                                             "execution_ids": ["account-run"], **updates})


def test_adoption_copies_committed_wal_and_keeps_source_then_resumes_edited_id(tmp_path):
    conn, source = legacy(tmp_path)
    marker_path = marker(tmp_path)
    original_marker = marker_path.read_bytes()
    try:
        assert Path(str(source) + "-wal").stat().st_size > 0
        lease = prepare(tmp_path)
        assert lease.action == "adopted" and lease.db_path != source
        with sqlite3.connect(lease.db_path) as adopted:
            assert adopted.execute("SELECT value FROM retained").fetchall() == [("committed-in-wal",)]
            adopted.execute("INSERT INTO retained VALUES ('new-run-value')")
        assert conn.execute("SELECT value FROM retained").fetchall() == [("committed-in-wal",)]
        assert marker_path.read_bytes() == original_marker
        path, key = lease.db_path, lease.execution_key
        lease.close()
        resumed = prepare(tmp_path, workflow_id="edited-dsl")
        assert resumed.action == "resumed" and resumed.db_path == path and resumed.execution_key == key
        resumed.close()
    finally:
        conn.close()


def test_edited_dsl_discovers_matching_old_marker(tmp_path):
    conn, source = legacy(tmp_path)
    marker(tmp_path)
    conn.close()
    lease = prepare(tmp_path, workflow_id="renamed")
    assert lease.action == "adopted" and source.exists()
    lease.close()


def test_account_switch_and_foreign_clone_never_inherit_source(tmp_path):
    conn, source = legacy(tmp_path)
    marker(tmp_path)
    conn.close()
    for updates in ({"execution_ids": ["another-account"]}, {"project_id": "clone"}):
        lease = prepare(tmp_path, **updates)
        assert lease.action == "created"
        with sqlite3.connect(lease.db_path) as check:
            assert check.execute("SELECT name FROM sqlite_master WHERE name='retained'").fetchone() is None
        lease.close()
    assert source.exists()


@pytest.mark.parametrize("ids", [None, [], ["a", "b"], [""], "account-run"])
def test_missing_or_multiple_server_execution_ids_do_not_touch_storage(tmp_path, ids):
    with pytest.raises(ExecutionStorageUnavailable):
        prepare(tmp_path, execution_ids=ids)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("change", [
    {"ids": []}, {"ids": ["account-run", "other"]}, {"project": ""},
    {"history": [{"action": "skipped_partial"}]}, {"history": "broken"},
])
def test_unproven_legacy_ownership_holds_without_rewriting_source(tmp_path, change):
    conn, source = legacy(tmp_path)
    conn.close()
    path = marker(tmp_path, **change)
    before = source.read_bytes(), path.read_bytes()
    with pytest.raises(ExecutionStorageUnavailable):
        prepare(tmp_path)
    assert (source.read_bytes(), path.read_bytes()) == before
    assert not list(tmp_path.glob("execution_*_workflow.db"))
    assert not list(tmp_path.glob(".execution-adopt-*"))


def test_missing_marker_and_corrupt_marker_hold(tmp_path):
    conn, _ = legacy(tmp_path)
    conn.close()
    with pytest.raises(ExecutionStorageUnavailable, match="no ownership"):
        prepare(tmp_path)
    (tmp_path / "old_execution.json").write_text("not-json")
    with pytest.raises(ExecutionStorageUnavailable, match="unreadable"):
        prepare(tmp_path)


def test_two_candidate_files_hold_instead_of_choosing_one(tmp_path):
    for workflow in ("old", "duplicate"):
        conn, _ = legacy(tmp_path, workflow)
        conn.close()
        marker(tmp_path, workflow)
    with pytest.raises(ExecutionStorageUnavailable, match="Multiple legacy"):
        prepare(tmp_path)


def test_active_lease_blocks_overlap_then_releases(tmp_path):
    lease = prepare(tmp_path)
    with pytest.raises(ExecutionStorageUnavailable, match="active storage owner"):
        prepare(tmp_path)
    with pytest.raises(ExecutionStorageUnavailable, match="active storage owner"):
        prepare(tmp_path, execution_ids=["replacement-account"])
    unrelated = prepare(tmp_path, project_id="another-project")
    unrelated.close()
    lease.close()
    next_lease = prepare(tmp_path)
    assert next_lease.action == "resumed"
    next_lease.close()


def test_active_legacy_writer_holds_and_releases_lock_on_failure(tmp_path):
    conn, _ = legacy(tmp_path)
    marker(tmp_path)
    conn.execute("BEGIN IMMEDIATE")
    try:
        with pytest.raises(ExecutionStorageUnavailable):
            prepare(tmp_path)
    finally:
        conn.rollback()
        conn.close()
    lease = prepare(tmp_path)
    assert lease.action == "adopted"
    lease.close()


def test_target_with_conflicting_owner_is_not_overwritten(tmp_path):
    lease = prepare(tmp_path)
    path = lease.db_path
    lease.close()
    with sqlite3.connect(path) as conn:
        conn.execute("UPDATE managed_execution_storage SET project_id='foreign'")
    with pytest.raises(ExecutionStorageUnavailable, match="ownership does not match"):
        prepare(tmp_path)


def test_source_symlink_and_unsafe_workflow_name_are_rejected(tmp_path):
    conn, source = legacy(tmp_path, "actual")
    conn.close()
    (tmp_path / "old_workflow.db").symlink_to(source)
    marker(tmp_path)
    with pytest.raises(ExecutionStorageUnavailable, match="symbolic link"):
        prepare(tmp_path)
    with pytest.raises(ExecutionStorageUnavailable, match="filename"):
        prepare(tmp_path, workflow_id="../escape")
