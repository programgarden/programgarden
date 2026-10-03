"""Opt-in strategy SQLite namespace below the host-provided durable directory."""
import hashlib
import re


def scoped_sqlite_filename(config, context):
    name = config.get('db_name', 'default.db')
    scope = config.get('storage_scope', 'shared')
    if scope == 'shared':
        return name
    if scope != 'execution':
        raise ValueError('Unknown SQLite storage scope')
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_-][A-Za-z0-9_.-]{0,119}\.db', name):
        raise ValueError('Execution-scoped SQLite requires a plain .db filename')
    key = context.execution_key or context.workflow_id
    if not isinstance(key, str) or not key.strip():
        raise ValueError('Execution-scoped SQLite requires a stable execution or workflow identity')
    basis = ('execution:' if context.execution_key else 'workflow:') + key
    return 'strategy_' + hashlib.sha256(basis.encode()).hexdigest() + '_' + name
