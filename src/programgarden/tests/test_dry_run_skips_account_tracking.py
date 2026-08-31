"""dry_run 에서는 브로커 노드가 계좌 추적기·체결내역 동기화를 띄우지 않는다 (Phase 9.6 실측, 2026-08-29).

두 경로는 별도 ``LS()`` 로 appkey/appsecret 직접 로그인한다(토큰 공급자 미상속). 서버 단일 발급
토큰 + 더미 appsecret 으로 도는 트레이앱 검증 잡에서는 그 로그인이 403 → "Failed to login for
account tracking" 이 errors[] 에 실려 모의 실행이 항상 실패했다. 모의 실행엔 주문·체결이 없으니
둘 다 skip 이 맞다. runtime(실행) 은 종전대로 띄운다.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from programgarden.context import ExecutionContext
from programgarden.executor import BrokerNodeExecutor
from programgarden_core.bases.listener import BaseExecutionListener, WorkflowPnLEvent


class _PnLListener(BaseExecutionListener):
    async def on_workflow_pnl_update(self, event: WorkflowPnLEvent) -> None:  # pragma: no cover
        pass


def _ctx(dry_run: bool) -> ExecutionContext:
    ctx = ExecutionContext(job_id="j", workflow_id="wf", context_params={"dry_run": dry_run})
    listener = _PnLListener()
    if hasattr(ctx, "add_listener"):
        ctx.add_listener(listener)
    else:
        ctx._listeners = [listener]
    assert ctx.is_dry_run is dry_run
    return ctx


_CFG = {"appkey": "k", "appsecret": "dummy-secret", "paper_trading": False}


async def _run_broker(ctx: ExecutionContext):
    ex = BrokerNodeExecutor()
    with patch.object(BrokerNodeExecutor, "_start_account_tracking", new=AsyncMock()) as track, \
         patch.object(BrokerNodeExecutor, "_sync_fill_prices_from_history", new=AsyncMock()) as sync:
        out = await ex.execute("broker", "OverseasStockBrokerNode", dict(_CFG), ctx)
        await asyncio.sleep(0)  # create_task 된 코루틴이 있으면 여기서 시작된다
    return out, track, sync


@pytest.mark.asyncio
async def test_dry_run_broker_does_not_start_account_tracking_or_fill_sync():
    out, track, sync = await _run_broker(_ctx(dry_run=True))
    assert out.get("connected") is True or out.get("connection")
    track.assert_not_awaited()
    sync.assert_not_awaited()


@pytest.mark.asyncio
async def test_runtime_broker_still_starts_account_tracking_and_fill_sync():
    out, track, sync = await _run_broker(_ctx(dry_run=False))
    assert out.get("connected") is True or out.get("connection")
    track.assert_awaited_once()
    sync.assert_awaited_once()
