"""Managed futures cannot double-write the legacy TC3 FIFO path."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import programgarden.executor as engine
from programgarden.context import ExecutionContext


@pytest.mark.asyncio
@pytest.mark.parametrize("managed", [True, False])
async def test_tc3_managed_session_uses_only_canonical_reconciliation(tmp_path, monkeypatch, managed):
    callbacks = {}
    real = SimpleNamespace(
        connect=AsyncMock(),
        TC2=lambda: SimpleNamespace(on_tc2_message=lambda cb: callbacks.update(tc2=cb)),
        TC3=lambda: SimpleNamespace(on_tc3_message=lambda cb: callbacks.update(tc3=cb)),
    )
    ls = SimpleNamespace(overseas_futureoption=lambda: SimpleNamespace(real=lambda: real))
    ctx = ExecutionContext(job_id="synthetic-job", workflow_id="synthetic-workflow",
        storage_dir=str(tmp_path), order_lifecycle_handler=object() if managed else None)
    writes = []
    def record(**fields):
        writes.append(fields)
        return object()
    ctx.record_workflow_fill = record
    scheduled = []
    monkeypatch.setattr(engine.asyncio, "run_coroutine_threadsafe",
                        lambda operation, loop: scheduled.append(operation))
    executor = engine.BrokerNodeExecutor()
    await executor._subscribe_overseas_futures_fill_events(ls, "synthetic-broker", ctx)
    event = SimpleNamespace(body=SimpleNamespace(svc_id="CH01", ordr_no="000123",
        ordr_dt="20260908", ccls_dt="20260909", ccls_no="456", ccls_tm="121000123",
        is_cd="SYNTHETIC", s_b_ccd="2", ccls_q=1, ccls_prc="100.25"))
    callbacks["tc3"](event)
    callbacks["tc3"](event)
    if managed:
        assert not writes and not scheduled
    else:
        # Standalone compatibility is deliberately unchanged in this guard.
        assert len(writes) == len(scheduled) == 2
    ctx._is_shutdown = True
    executor._active_trackers.clear()
