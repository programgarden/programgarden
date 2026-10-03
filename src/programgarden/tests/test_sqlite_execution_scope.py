"""Durable reservations survive new process contexts without crossing executions."""
import pytest
from programgarden.context import ExecutionContext
from programgarden.executor import SQLiteNodeExecutor
from programgarden.database.sqlite_scope import scoped_sqlite_filename
from programgarden_core.nodes.session_gate import SessionGateNode
from datetime import datetime


@pytest.mark.asyncio
async def test_injected_volume_restart_and_account_execution_isolation(tmp_path):
    async def query(context, sql):
        return await SQLiteNodeExecutor().execute('state', 'SQLiteNode', {
            'storage_scope': 'execution', 'db_name': 'rollover.db',
            'operation': 'execute_query', 'query': sql,
        }, context)
    def host(job, key):
        return ExecutionContext(job_id=job, workflow_id='same-editable-json-id',
                                execution_key=key, storage_dir=str(tmp_path))
    first = host('before-restart', 'host-project-account-A')
    await query(first, 'CREATE TABLE reservation (quantity INTEGER, status TEXT)')
    await query(first, "INSERT INTO reservation VALUES (2, 'close_submitted')")
    restored = await query(host('after-restart', 'host-project-account-A'), 'SELECT * FROM reservation')
    assert restored['rows'] == [{'quantity': 2, 'status': 'close_submitted'}]
    other = host('other-account', 'host-project-account-B')
    await query(other, 'CREATE TABLE reservation (quantity INTEGER, status TEXT)')
    assert (await query(other, 'SELECT * FROM reservation'))['rows'] == []
    assert len(list(tmp_path.glob('strategy_*_rollover.db'))) == 2
    assert scoped_sqlite_filename({'db_name': 'legacy.db'}, first) == 'legacy.db'


@pytest.mark.parametrize('name', ['../x.db', '/tmp/x.db', 'x/y.db'])
def test_execution_scoped_filename_cannot_escape_storage(name):
    with pytest.raises(ValueError):
        scoped_sqlite_filename({'storage_scope': 'execution', 'db_name': name},
                               ExecutionContext(job_id='j', workflow_id='w'))


@pytest.mark.parametrize('clock,allowed', [
    ('2026-09-22T06:30:00+00:00', True),
    ('2026-10-01T06:30:00+00:00', False),
    ('2026-09-22T04:30:00+00:00', False),
    ('2026-12-24T06:30:00+00:00', False),
    ('2026-09-26T06:30:00+00:00', False),
])
def test_hong_kong_cash_calendar_intersection_blocks_holidays_breaks_half_days(clock, allowed):
    gate = SessionGateNode(id='gate', timezone='Asia/Hong_Kong', windows=[{'start': '09:00', 'end': '17:00'}],
                           exchange_calendar='XHKG', days=['mon', 'tue', 'wed', 'thu', 'fri'])
    assert gate.evaluate_at(datetime.fromisoformat(clock))['allowed'] is allowed
