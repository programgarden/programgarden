"""Real client executors must not cross-cancel another client's same-named job."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from programgarden import ProgramGarden
from programgarden.tools import cancel_all_orders, cancel_all_orders_async


async def test_explicit_client_executor_cannot_fall_back_to_other_client():
    one, two = ProgramGarden(), ProgramGarden()
    first = SimpleNamespace(_task=asyncio.current_task(), cancel_pending_orders=AsyncMock(return_value={"owner": "first"}))
    second = SimpleNamespace(_task=asyncio.current_task(), cancel_pending_orders=AsyncMock(return_value={"owner": "second"}))
    one.executor._jobs["same-id"] = first
    two.executor._jobs["same-id"] = second
    assert await cancel_all_orders_async("same-id", executor=one.executor) == {"owner": "first"}
    second.cancel_pending_orders.assert_not_awaited()
    with pytest.raises(ValueError):
        await cancel_all_orders_async("missing", executor=one.executor)
    with pytest.raises(RuntimeError, match="owning loop"):
        cancel_all_orders("same-id", executor=two.executor)
    second.cancel_pending_orders.assert_not_awaited()


async def test_wrong_event_loop_is_rejected_before_any_request():
    pg = ProgramGarden()
    other_loop = asyncio.new_event_loop()
    try:
        operation = AsyncMock()
        pg.executor._jobs["job"] = SimpleNamespace(_task=SimpleNamespace(get_loop=lambda: other_loop), cancel_pending_orders=operation)
        with pytest.raises(RuntimeError, match="owning job event loop"):
            await cancel_all_orders_async("job", executor=pg.executor)
        operation.assert_not_awaited()
    finally:
        other_loop.close()


async def test_synchronous_worker_thread_dispatches_on_owning_active_loop():
    pg = ProgramGarden()
    loop = asyncio.get_running_loop()
    async def cancel():
        assert asyncio.get_running_loop() is loop
        return {"status": "confirmation_pending"}
    pg.executor._jobs["job"] = SimpleNamespace(_task=asyncio.current_task(), cancel_pending_orders=cancel)
    result = await asyncio.to_thread(cancel_all_orders, "job", executor=pg.executor)
    assert result["status"] == "confirmation_pending"
