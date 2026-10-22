"""Stable runtime-owned database names, independent of editable workflow JSON."""

import hashlib


def engine_db_filename(*, workflow_id: str, job_id: str, execution_key: str | None = None) -> str:
    if execution_key is None:
        return f"{workflow_id or job_id}_workflow.db"
    if not isinstance(execution_key, str) or not execution_key.strip() or len(execution_key) > 256:
        raise ValueError("execution_key must be a nonempty string of at most 256 characters")
    # The host owns this globally scoped identity (project + account execution).
    # Editable DSL IDs and per-process job IDs must not reset a resumed ledger.
    digest = hashlib.sha256(execution_key.encode()).hexdigest()
    return f"execution_{digest}_workflow.db"
