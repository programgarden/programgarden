"""A paused workflow must leave its wait without running queued order branches."""

import asyncio
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock

from test_broker_tracker_lifecycle import make_job


async def test_stop_exits_paused_event_wait_without_triggering_branch():
    job = make_job()
    job.context.start()
    job.context.pause()
    job._handle_realtime_update = AsyncMock()
    await job.context.emit_event("realtime_update", "quote", {"price": 100})
    task = asyncio.create_task(job._event_loop())
    await asyncio.sleep(0.01)
    job.context.stop()
    await asyncio.wait_for(task, 0.5)
    job._handle_realtime_update.assert_not_awaited()


async def test_stop_exits_paused_main_flow_without_executing_node():
    job = make_job()
    job.workflow.nodes = {"buy": NS(node_type="OverseasStockNewOrderNode", config={})}
    job.workflow.execution_order = ["buy"]
    job.context.start()
    job.context.pause()
    job._find_split_aggregate_pairs = lambda: {}
    job._execute_node = AsyncMock()
    task = asyncio.create_task(job._execute_main_flow())
    await asyncio.sleep(0.01)
    job.context.stop()
    await asyncio.wait_for(task, 0.5)
    job._execute_node.assert_not_awaited()
