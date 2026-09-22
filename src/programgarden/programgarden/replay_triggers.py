"""Single-cycle trigger replay; never start timers or manufacture market access."""

import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

from programgarden.replay_contracts import ContractViolation


def fixture_instant(context, node_id):
    value = context.validation_as_of
    if not value:
        raise ContractViolation(node_id, "Trigger verification requires an explicit fixture clock",
                                "REPLAY_FIXTURE_REQUIRED")
    instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ContractViolation(node_id, "Trigger clock must include a timezone")
    return instant


class _StartupContext:
    """Run the actual startup executor while cancelling its timer before it runs.

    Creating/registering the task does not yield control in the live executor.
    The timer is cancelled synchronously, then drained before replay continues.
    This proves the initial traversal only, not recurring cron event delivery.
    """

    def __init__(self, context):
        self.context, self.tasks = context, []

    def __getattr__(self, name):
        return getattr(self.context, name)

    def register_persistent_task(self, node_id, task):
        task.cancel()
        self.tasks.append(task)


async def schedule_startup(node, config, context):
    from programgarden.executor import ScheduleNodeExecutor
    fixture_instant(context, node.id)
    # The live legacy executor substitutes UTC for an invalid zone. Verification
    # must reject that ambiguous configuration instead of certifying its intent.
    try:
        ZoneInfo(node.timezone)
    except (ValueError, KeyError):
        raise ContractViolation(node.id, "Invalid schedule timezone") from None
    if node.count < 1 or node.max_duration_hours <= 0:
        raise ContractViolation(node.id, "Schedule safety limits must be positive")
    proxy = _StartupContext(context)
    try:
        return await ScheduleNodeExecutor().execute(node.id, node.type, config, proxy)
    finally:
        if proxy.tasks:
            await asyncio.gather(*proxy.tasks, return_exceptions=True)


def trading_hours(node, context):
    instant = fixture_instant(context, node.id)
    # Use the same predicate as LIVE. In LIVE, a closed window waits; returning
    # passed=False here would invent an after-hours branch the real node did not
    # take. An in-window fixture verifies the immediate path; waiting needs a
    # separate temporal replay capability and cannot become a synthetic PASS.
    if not node._is_trading_hours(as_of=instant):
        raise ContractViolation(node.id, "Trading-hours node would wait at the fixture instant",
                                "REPLAY_TIME_WAIT_BLOCKED")
    return {"passed": True, "blocked": False}
