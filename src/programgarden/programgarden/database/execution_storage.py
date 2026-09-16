"""Adopt a stopped host's verified legacy database without deleting its source.

The host supplies project/execution identity from its authenticated start response.
Legacy ownership comes from its P3 marker, never from editable workflow JSON.
Keep the returned lease until all engine tasks have stopped.
"""

from __future__ import annotations

from dataclasses import dataclass
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile

from .db_naming import engine_db_filename


class ExecutionStorageUnavailable(RuntimeError):
    """Storage ownership or exclusive access could not be established."""


@dataclass
class ExecutionStorageLease:
    execution_key: str
    db_path: Path
    action: str
    _locks: list

    def close(self):
        while self._locks:
            self._locks.pop().close()


def _identifier(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 128:
        raise ExecutionStorageUnavailable("Missing or invalid managed execution identity")
    return value


def _workflow_name(value):
    value = _identifier(value)
    if value in {".", ".."} or any(c in value for c in ("/", "\\", "\0")):
        raise ExecutionStorageUnavailable("Invalid legacy workflow filename")
    return value


def _lease_lock(path):
    flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    handle = os.fdopen(os.open(path, flags, 0o600), "r+b")
    try:
        if os.name == "nt":
            import msvcrt
            if path.stat().st_size == 0:
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return handle
    except (OSError, BlockingIOError):
        handle.close()
        raise ExecutionStorageUnavailable("The account execution still has an active storage owner") from None


def _read_marker(path):
    if path.is_symlink():
        raise ExecutionStorageUnavailable("Legacy marker must not be a symbolic link")
    try:
        raw = path.read_bytes()
        marker = json.loads(raw)
    except (OSError, ValueError):
        raise ExecutionStorageUnavailable("Legacy execution marker is unreadable") from None
    if not isinstance(marker, dict):
        raise ExecutionStorageUnavailable("Legacy execution marker is malformed")
    return raw, marker


def _legacy_source(directory, workflow_id, project_id, execution_id):
    candidates = []
    current = directory / f"{workflow_id}_workflow.db"
    current_marker = directory / f"{workflow_id}_execution.json"
    if current.exists() and not current_marker.exists():
        raise ExecutionStorageUnavailable("Existing legacy database has no ownership marker")
    for path in directory.glob("*_execution.json"):
        raw, marker = _read_marker(path)
        if marker.get("project_id") != project_id:
            if path == current_marker and not marker.get("project_id") and current.exists():
                raise ExecutionStorageUnavailable("Legacy database project ownership is unknown")
            continue
        ids = marker.get("execution_ids")
        if not isinstance(ids, list) or any(not isinstance(i, str) or not i for i in ids):
            raise ExecutionStorageUnavailable("Legacy execution identity is malformed")
        if not ids:
            raise ExecutionStorageUnavailable("Legacy database account ownership is unknown")
        if execution_id not in ids:
            continue  # Another account execution stays untouched.
        if ids != [execution_id]:
            raise ExecutionStorageUnavailable("A mixed-account legacy database cannot be adopted")
        history = marker.get("history", [])
        if not isinstance(history, list) or any(not isinstance(h, dict) for h in history):
            raise ExecutionStorageUnavailable("Legacy ownership history is malformed")
        # A reset archives the old mixed file. Earlier ambiguity cannot taint
        # the new file, but ambiguity after that boundary must keep it held.
        since_reset = history
        for index, item in enumerate(history):
            if item.get("action") == "reset":
                since_reset = history[index + 1:]
        if any(h.get("action") == "skipped_partial" for h in since_reset):
            raise ExecutionStorageUnavailable("Legacy database contains unresolved account history")
        name = _workflow_name(marker.get("workflow_id"))
        if path.name != f"{name}_execution.json":
            raise ExecutionStorageUnavailable("Legacy marker filename does not match its identity")
        source = directory / f"{name}_workflow.db"
        if source.is_symlink():
            raise ExecutionStorageUnavailable("Legacy database must not be a symbolic link")
        if source.exists():
            candidates.append((source, path, raw))
    if len(candidates) > 1:
        raise ExecutionStorageUnavailable("Multiple legacy databases claim the same account execution")
    return candidates[0] if candidates else None


def _open_existing(path, mode):
    return closing(sqlite3.connect(f"{path.as_uri()}?mode={mode}", uri=True, timeout=0))


def prepare_execution_storage(data_dir, *, project_id, workflow_id, execution_ids):
    """Return exclusive managed storage; fail before execution on ambiguity.

    Invoke only after the prior local run is fully stopped. SQLite backup keeps
    committed WAL pages and all checkpoint/risk/ledger tables. Publishing the new
    file is atomic and never overwrites the source or another target.
    """
    project_id = _identifier(project_id)
    workflow_id = _workflow_name(workflow_id)
    if not isinstance(execution_ids, list) or len(execution_ids) != 1:
        raise ExecutionStorageUnavailable("Exactly one server-confirmed account execution is required")
    execution_id = _identifier(execution_ids[0])
    identity = json.dumps([project_id, execution_id], separators=(",", ":"))
    key = "managed:" + hashlib.sha256(identity.encode()).hexdigest()
    directory = Path(data_dir).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / engine_db_filename(workflow_id="", job_id="", execution_key=key)
    # An account switch must also wait for the old project's writer to stop.
    project_digest = hashlib.sha256(project_id.encode()).hexdigest()
    locks = []
    temporary = None
    try:
        locks.append(_lease_lock(directory / f"project_{project_digest}.lock"))
        locks.append(_lease_lock(target.with_suffix(".lock")))
        if target.is_symlink():
            raise ExecutionStorageUnavailable("Managed database must not be a symbolic link")
        if target.exists():
            with _open_existing(target, "ro") as conn:
                row = conn.execute("SELECT project_id, execution_id FROM managed_execution_storage WHERE singleton=1").fetchone()
                if row != (project_id, execution_id):
                    raise ExecutionStorageUnavailable("Managed database ownership does not match this run")
            return ExecutionStorageLease(key, target, "resumed", locks)
        source = _legacy_source(directory, workflow_id, project_id, execution_id)
        fd, name = tempfile.mkstemp(prefix=".execution-adopt-", suffix=".db", dir=directory)
        os.close(fd)
        temporary = Path(name)
        with closing(sqlite3.connect(temporary)) as dest:
            if source:
                path, marker_path, marker_bytes = source
                with _open_existing(path, "rw") as guard, _open_existing(path, "ro") as reader:
                    guard.execute("BEGIN IMMEDIATE")
                    reader.backup(dest)
                    if marker_path.read_bytes() != marker_bytes:
                        raise ExecutionStorageUnavailable("Legacy ownership changed during adoption")
                    guard.rollback()
            if dest.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
                raise ExecutionStorageUnavailable("Execution database integrity check failed")
            dest.execute("PRAGMA journal_mode=DELETE")
            dest.execute("CREATE TABLE managed_execution_storage (singleton INTEGER PRIMARY KEY CHECK(singleton=1), project_id TEXT NOT NULL, execution_id TEXT NOT NULL, legacy_filename TEXT)")
            dest.execute("INSERT INTO managed_execution_storage VALUES (1, ?, ?, ?)",
                         (project_id, execution_id, source[0].name if source else None))
            dest.commit()
        with temporary.open("rb") as handle:
            os.fsync(handle.fileno())
        os.link(temporary, target)  # Exclusive atomic publication, no overwrite.
        return ExecutionStorageLease(key, target, "adopted" if source else "created", locks)
    except BaseException as exc:
        while locks:
            locks.pop().close()
        if isinstance(exc, (sqlite3.Error, OSError)):
            raise ExecutionStorageUnavailable("Execution storage could not be verified or prepared") from None
        raise
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
