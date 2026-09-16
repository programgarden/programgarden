"""Actual SQLite consumers must isolate account executions and retain old state."""
from pathlib import Path
from types import SimpleNamespace
import sqlite3

import pytest

from programgarden.context import ExecutionContext
from programgarden.database.db_naming import engine_db_filename
from programgarden.executor import WorkflowJob
from programgarden.tools.job_tools import emergency_close_all


def make_context(tmp_path, key, job_id='job'):
    ctx = ExecutionContext(job_id=job_id, workflow_id='strategy', storage_dir=str(tmp_path), execution_key=key)
    ctx.set_listeners([SimpleNamespace(on_workflow_pnl_update=lambda *args: None)])
    ctx.init_workflow_position_tracker('broker', 'overseas_stock', 'ls', False)
    return ctx


def test_same_execution_resumes_but_account_switch_keeps_a_separate_database(tmp_path):
    prior = make_context(tmp_path, 'execution-a')
    assert prior._workflow_position_tracker is not None
    path = prior._workflow_position_tracker.db_path
    with sqlite3.connect(path) as conn:
        conn.execute('CREATE TABLE retained_test_record (value TEXT)')
        conn.execute("INSERT INTO retained_test_record VALUES ('retained')")
    resumed = make_context(tmp_path, 'execution-a', 'different-job')
    current = make_context(tmp_path, 'execution-b')
    assert resumed._workflow_position_tracker.db_path == path
    assert current._workflow_position_tracker.db_path != path
    with sqlite3.connect(path) as conn:
        assert conn.execute('SELECT value FROM retained_test_record').fetchone() == ('retained',)
    with sqlite3.connect(current._workflow_position_tracker.db_path) as conn:
        assert conn.execute("SELECT name FROM sqlite_master WHERE name='retained_test_record'").fetchone() is None
    for ctx in (prior, resumed, current):
        job = SimpleNamespace(context=ctx, _checkpoint_mgr=None)
        assert WorkflowJob._get_checkpoint_mgr(job).db_path == ctx._workflow_position_tracker.db_path


def test_legacy_name_stays_compatible_and_scope_never_becomes_a_path(tmp_path):
    legacy = make_context(tmp_path, None)
    assert Path(legacy._workflow_position_tracker.db_path).name == 'strategy_workflow.db'
    scoped = make_context(tmp_path, '../../untrusted/account')
    assert Path(scoped._workflow_position_tracker.db_path).parent == tmp_path
    assert 'untrusted' not in scoped.engine_db_filename
    assert engine_db_filename(workflow_id='edited-id', job_id='job', execution_key='execution-a') == engine_db_filename(workflow_id='strategy', job_id='job', execution_key='execution-a')


@pytest.mark.parametrize('key', ['', ' ', 123, 'x' * 257])
def test_invalid_scope_rejected_before_database_creation(tmp_path, key):
    with pytest.raises(ValueError):
        make_context(tmp_path, key)
    assert list(tmp_path.iterdir()) == []


def test_excluded_liquidation_does_not_claim_success():
    result = emergency_close_all('job')
    assert result['status'] == 'not_implemented'
    assert result['closed_positions'] == result['cancelled_orders'] == []


@pytest.mark.asyncio
async def test_risk_events_resume_with_same_scope_without_crossing_accounts(tmp_path):
    contexts = [make_context(tmp_path, 'execution-a'),
                make_context(tmp_path, 'execution-a', job_id='resumed-job'),
                make_context(tmp_path, 'execution-b')]
    try:
        for ctx in contexts:
            ctx.init_risk_tracker({'events'}, 'overseas_stock', 'ls', False)
            assert ctx.risk_tracker is not None
            assert ctx.risk_tracker.db_path == ctx._workflow_position_tracker.db_path
        prior, resumed, current = contexts
        event_id = prior.risk_tracker.record_risk_event('storage_scope_test', severity='info')
        assert event_id is not None
        assert len(resumed.risk_tracker.get_risk_events('storage_scope_test')) == 1
        assert current.risk_tracker.get_risk_events('storage_scope_test') == []
    finally:
        for ctx in contexts:
            if ctx.risk_tracker is not None:
                await ctx.risk_tracker.stop_flush_loop()
