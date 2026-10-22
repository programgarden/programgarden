"""Real SDK field and thread contracts for bounded futures account refreshes."""
import asyncio
import threading
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from programgarden_finance.ls.overseas_futureoption.extension.tracker import FuturesAccountTracker
from programgarden_finance.ls.overseas_futureoption.real.TC2.blocks import TC2RealResponseBody
from programgarden_finance.ls.overseas_futureoption.real.TC3.blocks import TC3RealResponseBody


def message(model, service):
    assert 'svc_id' in model.model_fields and 'svcId' not in model.model_fields
    fields = {name: '' for name, field in model.model_fields.items() if field.is_required()}
    fields['svc_id'] = service
    if model is TC2RealResponseBody:
        fields['ordr_typ_cd'] = '2'
    return SimpleNamespace(body=model(**fields))


class Stream:
    def __init__(self, name):
        self.callbacks = []
        setattr(self, f'on_{name}_message', self.callbacks.append)
        setattr(self, f'on_remove_{name}_message', self.remove)

    def remove(self, callback):
        if callback in self.callbacks:
            self.callbacks.remove(callback)


async def started_tracker():
    tc2, tc3, ovc = Stream('tc2'), Stream('tc3'), Stream('ovc')
    real = SimpleNamespace(is_connected=AsyncMock(return_value=True),
                           TC2=lambda:tc2, TC3=lambda:tc3, OVC=lambda:ovc)
    tracker = FuturesAccountTracker(None, None, real_client=real)
    tracker._spec_manager.initialize = AsyncMock()
    tracker._spec_manager.stop = AsyncMock()
    tracker._sync_tick_subscriptions = AsyncMock()
    tracker._fetch_all_data_locked = AsyncMock()
    tracker.DEFAULT_ORDER_DELAY = 0
    await tracker.start()
    tracker._fetch_all_data_locked.reset_mock()
    return tracker, tc2, tc3


@pytest.mark.asyncio
@pytest.mark.parametrize('model,service,channel', [
    (TC2RealResponseBody,'HO02','TC2'), (TC3RealResponseBody,'CH01','TC3'),
])
async def test_real_sdk_message_from_broker_thread_refreshes_once(model,service,channel):
    tracker,tc2,tc3 = await started_tracker()
    called = asyncio.Event()
    tracker._fetch_all_data_locked.side_effect = lambda: called.set()
    callback = (tc2 if channel == 'TC2' else tc3).callbacks[0]
    packet = message(model,service)
    try:
        thread = threading.Thread(target=lambda: [callback(packet) for _ in range(10)])
        thread.start()
        thread.join(timeout=2)
        assert not thread.is_alive()
        await asyncio.wait_for(called.wait(),1)
        await tracker._order_refresh_task
        assert tracker._fetch_all_data_locked.await_count == 1
    finally:
        await tracker.stop()
    assert tc2.callbacks == [] and tc3.callbacks == []


@pytest.mark.asyncio
async def test_fill_arriving_during_refresh_requests_a_serial_followup():
    tracker,_,tc3 = await started_tracker()
    entered,release = asyncio.Event(),asyncio.Event()
    calls = []
    async def fetch():
        calls.append('read')
        if len(calls) == 1:
            entered.set()
            await release.wait()
    tracker._fetch_all_data_locked.side_effect = fetch
    packet = message(TC3RealResponseBody,'CH01')
    try:
        await asyncio.to_thread(tc3.callbacks[0],packet)
        await asyncio.wait_for(entered.wait(),1)
        await asyncio.to_thread(tc3.callbacks[0],packet)
        await asyncio.sleep(0)
        release.set()
        await asyncio.wait_for(tracker._order_refresh_task,1)
        assert len(calls) == 2
    finally:
        await tracker.stop()


@pytest.mark.asyncio
async def test_stop_cancels_owned_refresh_and_ignores_late_events():
    tracker,tc2,tc3 = await started_tracker()
    tracker.DEFAULT_ORDER_DELAY = 10
    foreign = lambda response: None
    tc3.callbacks.append(foreign)
    packet = message(TC3RealResponseBody,'CH01')
    await asyncio.to_thread(tracker._on_order_event,packet)
    await asyncio.sleep(0)
    task = tracker._order_refresh_task
    assert task is not None
    await tracker.stop()
    assert task.cancelled()
    assert tc3.callbacks == [foreign]
    await asyncio.to_thread(tracker._on_order_event,packet)
    assert tracker._order_refresh_task is None
    tracker._fetch_all_data_locked.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize('packet', [None, SimpleNamespace(body=None),
    SimpleNamespace(body=SimpleNamespace(svcId='HO02')),
    message(TC2RealResponseBody,'HO03')])
async def test_missing_misspelled_or_rejected_events_do_not_refresh(packet):
    tracker,_,_ = await started_tracker()
    try:
        await asyncio.to_thread(tracker._on_order_event,packet)
        await asyncio.sleep(0)
        assert tracker._order_refresh_task is None
        tracker._fetch_all_data_locked.assert_not_awaited()
    finally:
        await tracker.stop()


@pytest.mark.asyncio
async def test_periodic_and_event_reads_cannot_overlap():
    tracker,_,tc3 = await started_tracker()
    entered,release = asyncio.Event(),asyncio.Event()
    active,maximum = 0,0
    async def fetch():
        nonlocal active,maximum
        active += 1
        maximum = max(maximum,active)
        entered.set()
        await release.wait()
        active -= 1
    tracker._fetch_all_data_locked.side_effect = fetch
    periodic = asyncio.create_task(tracker._fetch_all_data())
    try:
        await asyncio.wait_for(entered.wait(),1)
        await asyncio.to_thread(tc3.callbacks[0],message(TC3RealResponseBody,'CH01'))
        await asyncio.sleep(0)
        release.set()
        await periodic
        await asyncio.wait_for(tracker._order_refresh_task,1)
        assert maximum == 1
        assert tracker._fetch_all_data_locked.await_count == 2
    finally:
        await tracker.stop()
