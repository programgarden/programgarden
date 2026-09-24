"""Real SQLite operations confined to a fresh replay workspace.

The production SQL builder and operation implementations are reused. Validation
does not take the dry-run shortcut that silently drops reservation writes. SQL
cannot attach files, load extensions, create virtual tables or change pragmas.
The dedicated worker also has no credentials, network or writable host mounts.
"""
from pathlib import Path
import re
import sqlite3

import aiosqlite

from programgarden.executor import SQLiteNodeExecutor
from programgarden.replay_contracts import ContractViolation


async def execute_sqlite(node_id, config, context):
    name = config.get("db_name", "default.db")
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_-][A-Za-z0-9_.-]{0,119}\.db", name):
        raise ContractViolation(node_id, "Replay SQLite requires a plain .db filename")
    root = Path(context._storage_dir).resolve()
    path = root / name
    if path.is_symlink() or path.resolve().parent != root:
        raise ContractViolation(node_id, "SQLite path leaves the replay workspace")
    operation = config.get("operation", "simple")
    if operation == "execute_query" and not (config.get("query") or "").strip():
        raise ContractViolation(node_id, "SQLite query is required")
    if operation == "simple" and (not config.get("table") or (
            config.get("action") == "upsert" and not config.get("on_conflict"))):
        raise ContractViolation(node_id, "SQLite table and upsert conflict key are required")
    denied = {sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH, sqlite3.SQLITE_PRAGMA,
              sqlite3.SQLITE_CREATE_VTABLE, sqlite3.SQLITE_DROP_VTABLE}
    def authorize(action, first, second, database, trigger):
        if action in denied or (action == sqlite3.SQLITE_FUNCTION and
                str(second).lower() in {"load_extension", "readfile", "writefile"}):
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK
    ticks = 0
    def progress():
        nonlocal ticks
        ticks += 1
        return int(ticks > 1000)
    executor = SQLiteNodeExecutor()
    async with aiosqlite.connect(str(path)) as db:
        db.row_factory = aiosqlite.Row
        # Authorizer installation must run on aiosqlite's connection thread.
        await db._execute(db._conn.set_authorizer, authorize)
        await db.set_progress_handler(progress, 1000)
        if operation == "execute_query":
            return await executor._execute_query_mode(db, config, context, node_id)
        return await executor._execute_simple_mode(db, config, context, node_id)
