"""Explicit managed stop controls; never used by ordinary stop or shutdown."""

import asyncio

from programgarden_core.bases.listener import NodeState

from .database.position_reconciliation import ReconciliationUnavailable


def can_cancel_owned_orders(job, execution_key):
    """Only the caller's initialized, running overseas-stock execution qualifies."""
    context = job.context
    tracker = context._workflow_position_tracker
    return bool(
        execution_key and tracker is not None
        and tracker.execution_key == execution_key
        and tracker.product == "overseas_stock"
        and tracker.provider in {"ls", "ls-sec.co.kr"}
        and job.status == "running"
        and not context.is_dry_run and not context.is_shutdown
        and not getattr(job, "_owned_cancellation_active", False)
        and not getattr(job, "_cancellation_requires_restart", False)
    )


async def pause_and_cancel_owned_orders(job, execution_key, *, can_continue):
    """Pause, drain in-flight nodes, then invoke the journalled stock adapter.

    The host owns final shutdown, including errors, disconnects and timeouts.
    No caller may resume this job after entering this explicit stop operation.
    A regular stop can interrupt the drain; it never implicitly sends a cancel.
    """
    if not can_cancel_owned_orders(job, execution_key) or not can_continue():
        raise ReconciliationUnavailable("owned_cancellation_unavailable")
    job._cancellation_requires_restart = True
    async with asyncio.timeout(135):
        await job.pause()
        async with asyncio.timeout(10):
            while any(state == NodeState.RUNNING for state in job._node_states.values()):
                if not can_continue() or job.context.is_shutdown:
                    raise ReconciliationUnavailable("owned_cancellation_interrupted")
                await asyncio.sleep(0.05)
        if not can_continue() or job.context.is_shutdown:
            raise ReconciliationUnavailable("owned_cancellation_interrupted")
        return await job.cancel_pending_orders()
