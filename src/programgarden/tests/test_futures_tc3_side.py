"""Pass real SDK TC3 messages through the engine without network access."""

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from programgarden.executor import BrokerNodeExecutor
from programgarden_finance.ls.overseas_futureoption.real import Real
from programgarden_finance.ls.overseas_futureoption.real.TC3.blocks import TC3RealResponseBody


class MemorySocket:
    def __init__(self):
        self.messages = asyncio.Queue()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def recv(self):
        return await self.messages.get()

    async def send(self, message):
        # Subscription envelopes stay inside this in-memory transport.
        pass

    async def close(self):
        pass


def tc3_packet(side):
    body = {
        name: "" for name, field in TC3RealResponseBody.model_fields.items()
        if field.is_required()
    }
    body.update(
        lineseq="1", key="synthetic-key", user="synthetic-user", svc_id="CH01",
        ordr_dt="20260909", ordr_no="000123", is_cd="SYNTHETIC", s_b_ccd=side,
        ccls_q="2", ccls_prc="100.25", ccls_no="000777",
        ccls_dt="20260910", ccls_tm="001500",
    )
    return {
        "header": {"tr_cd": "TC3", "rsp_cd": "00000", "rsp_msg": "synthetic"},
        "body": body,
    }


async def deliver_tc3(monkeypatch, side, *, managed=False, shutdown=False):
    socket = MemorySocket()
    connect = Mock(return_value=socket)
    monkeypatch.setattr("programgarden_finance.ls.real_base.connect", connect)
    monkeypatch.setattr(BrokerNodeExecutor, "_active_trackers", {})
    real = Real(
        token_manager=SimpleNamespace(
            access_token="synthetic-token", wss_url="wss://offline.invalid",
        ),
        reconnect=False,
    )
    writes, scheduled, parsed = [], [], []

    async def record(**fields):
        writes.append(fields)

    context = SimpleNamespace(
        job_id="tc3-side-offline", is_shutdown=shutdown,
        order_lifecycle_handler=object() if managed else None,
        log=Mock(), record_workflow_fill=record,
    )
    ls = SimpleNamespace(overseas_futureoption=lambda: SimpleNamespace(real=lambda: real))
    executor = BrokerNodeExecutor()
    original_schedule = asyncio.run_coroutine_threadsafe

    def schedule(coroutine, loop):
        future = original_schedule(coroutine, loop)
        scheduled.append(future)
        return future

    monkeypatch.setattr(asyncio, "run_coroutine_threadsafe", schedule)
    loop = asyncio.get_running_loop()
    processed = asyncio.Event()
    try:
        await executor._subscribe_overseas_futures_fill_events(ls, "broker", context)
        callback = real._on_message_listeners["TC3"]

        def observe(response):
            try:
                parsed.append(response)
                callback(response)
            finally:
                loop.call_soon_threadsafe(processed.set)

        real.TC3().on_tc3_message(observe)
        await socket.messages.put(json.dumps(tc3_packet(side)))
        await asyncio.wait_for(processed.wait(), timeout=2)
        # The callback has finished on the SDK thread. Drain every submitted
        # coroutine so a skipped event cannot appear successful due to a race.
        for future in scheduled:
            await asyncio.wait_for(asyncio.wrap_future(future), timeout=2)
        connect.assert_called_once()
        assert len(parsed) == 1
        assert isinstance(parsed[0].body, TC3RealResponseBody)
        assert parsed[0].body.s_b_ccd == side
        return writes, len(scheduled)
    finally:
        await real.close(force=True)
        executor._active_trackers.clear()


@pytest.mark.asyncio
@pytest.mark.parametrize("managed", [False, True], ids=["standalone", "app-managed"])
@pytest.mark.parametrize("side, expected", [("1", "sell"), ("2", "buy"), ("9", None), ("", None)])
async def test_tc3_sdk_side_and_managed_reconciliation_guard(monkeypatch, caplog, side, expected, managed):
    writes, scheduled = await deliver_tc3(monkeypatch, side, managed=managed)
    if managed or expected is None:
        assert writes == []
        assert scheduled == 0
        if not managed:
            assert "Ignoring TC3 fill with unknown side code" in caplog.text
    else:
        assert scheduled == 1
        assert writes == [{
            "order_no": "000123", "order_date": "20260909", "symbol": "SYNTHETIC",
            "exchange": "FUTURES", "side": expected, "quantity": 2, "price": 100.25,
            "fill_time": "001500", "commda_code": "40",
        }]
        # This fix does not invent TC3/REST execution identity or time aliases.
        assert "execution_id" not in writes[0]


@pytest.mark.asyncio
@pytest.mark.parametrize("side", ["1", "2"])
async def test_tc3_after_shutdown_never_schedules_inventory_write(monkeypatch, side):
    writes, scheduled = await deliver_tc3(monkeypatch, side, shutdown=True)
    assert writes == []
    assert scheduled == 0
