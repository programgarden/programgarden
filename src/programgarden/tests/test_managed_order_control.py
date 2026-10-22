"""The managed stop control cannot race active order nodes or another account."""
import asyncio
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock

import pytest
from programgarden_core.bases.listener import NodeState
from programgarden.managed_order_control import can_cancel_owned_orders, pause_and_cancel_owned_orders
from programgarden.database.position_reconciliation import ReconciliationUnavailable


def make_job():
    tracker = NS(execution_key="owned", product="overseas_stock", provider="ls")
    job = NS(context=NS(_workflow_position_tracker=tracker, is_dry_run=False, is_shutdown=False),
             status="running", _node_states={}, cancel_pending_orders=AsyncMock(return_value={"status": "confirmed"}))
    async def pause():
        job.status = "paused"
    job.pause = AsyncMock(side_effect=pause)
    return job


@pytest.mark.parametrize("field,value", [("execution_key", "other"), ("product", "korea_stock"),
                                         ("product", "overseas_futures"), ("provider", "other")])
async def test_wrong_scope_or_unsupported_product_cannot_pause(field, value):
    job = make_job()
    setattr(job.context._workflow_position_tracker, field, value)
    with pytest.raises(ReconciliationUnavailable):
        await pause_and_cancel_owned_orders(job, "owned", can_continue=lambda: True)
    job.pause.assert_not_awaited()
    job.cancel_pending_orders.assert_not_awaited()


async def test_waits_for_active_nodes_before_first_cancel():
    job = make_job()
    job._node_states["order"] = NodeState.RUNNING
    operation = asyncio.create_task(pause_and_cancel_owned_orders(job, "owned", can_continue=lambda: True))
    await asyncio.sleep(0.02)
    job.cancel_pending_orders.assert_not_awaited()
    assert job.status == "paused" and job._cancellation_requires_restart
    job._node_states.clear()
    assert await operation == {"status": "confirmed"}
    job.cancel_pending_orders.assert_awaited_once()
    assert not can_cancel_owned_orders(job, "owned")


async def test_external_stop_interrupts_drain_without_cancel():
    job = make_job()
    job._node_states["order"] = NodeState.RUNNING
    running = True
    operation = asyncio.create_task(pause_and_cancel_owned_orders(job, "owned", can_continue=lambda: running))
    await asyncio.sleep(0.02)
    running = False
    with pytest.raises(ReconciliationUnavailable, match="interrupted"):
        await operation
    job.cancel_pending_orders.assert_not_awaited()


async def test_dry_run_and_previous_cancellation_are_unavailable():
    job = make_job()
    job.context.is_dry_run = True
    assert not can_cancel_owned_orders(job, "owned")
    job.context.is_dry_run = False
    job._cancellation_requires_restart = True
    assert not can_cancel_owned_orders(job, "owned")
