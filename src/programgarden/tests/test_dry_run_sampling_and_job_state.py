"""
dry_run 종목 표본 상한(K, 기본 3) + get_state() 진단 보강 — 3.1.4 / 3.1.5

- 3.1.5: dry_run 에서 auto-iterate 아이템을 앞에서 K개로 절단(K=0 전수), HistoricalDataNode
  단독 복수 목록에도 같은 K. `get_state()["dry_run_sampling"]` 에 N중 K 기록.
  deep_validate·runtime 무변화.
- 3.1.4: 노드 항목에 `status`(=`state`) 별칭, 실행 중 노드에 `started_at`/`elapsed_ms`
  → 타임아웃으로 잘린 모의 실행에서 "어느 노드가 몇 초째" 가 남는다.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional
from unittest.mock import patch

from programgarden.context import ExecutionContext
from programgarden.executor import (
    BrokerNodeExecutor,
    HistoricalDataNodeExecutor,
    NewOrderNodeExecutor,
    WorkflowExecutor,
)

WATCH10 = [{"symbol": f"S{i:02d}", "exchange": "NASDAQ"} for i in range(10)]
CREDS = [{
    "credential_id": "broker_cred", "type": "broker_ls_overseas_stock",
    "data": [{"key": "appkey", "value": "dummy", "type": "password"},
             {"key": "appsecret", "value": "dummy", "type": "password"}],
}]


def _wf_hist(hist_cfg: Dict[str, Any], *, with_watchlist: bool = True, with_orders: bool = False):
    nodes: List[Dict[str, Any]] = [
        {"id": "start", "type": "StartNode"},
        {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred"},
    ]
    edges: List[Dict[str, str]] = [{"from": "start", "to": "broker"}]
    if with_watchlist:
        nodes.append({"id": "watchlist", "type": "WatchlistNode", "symbols": list(WATCH10)})
        edges += [{"from": "broker", "to": "watchlist"}, {"from": "watchlist", "to": "historical"}]
    else:
        edges.append({"from": "broker", "to": "historical"})
    nodes.append({"id": "historical", "type": "OverseasStockHistoricalDataNode",
                  "start_date": "20260101", "end_date": "20260201", "interval": "1d", **hist_cfg})
    if with_orders:
        nodes += [
            {"id": "sizing", "type": "PositionSizingNode",
             "symbols": "{{ nodes.watchlist.symbols }}", "method": "fixed_quantity", "fixed_quantity": 1,
             "price_data": {s["symbol"]: 10.0 for s in WATCH10}},
            {"id": "buy_order", "type": "OverseasStockNewOrderNode",
             "side": "buy", "order_type": "market", "order": "{{ item }}"},
        ]
        edges += [{"from": "watchlist", "to": "sizing"},
                  {"from": "sizing.orders", "to": "buy_order"},
                  {"from": "broker", "to": "buy_order"}]
    return {"id": "wf-sampling", "name": "sampling", "version": "1.0.0",
            "nodes": nodes, "edges": edges, "credentials": CREDS}


async def _run(workflow: Dict[str, Any], context_params: Optional[Dict[str, Any]] = None):
    fetch_calls: List[List[str]] = []
    order_calls: List[str] = []

    async def fake_broker(self, node_id, node_type, config, context, **kw):
        return {"connection": {"product": "overseas_stock", "paper_trading": True,
                               "credential_id": "broker_cred", "appkey": "x", "appsecret": "y"}}

    async def fake_fetch(self, symbols, start_date, end_date, interval, context, node_id, *rest):
        fetch_calls.append(list(symbols))
        return [{"symbol": s, "exchange": "NASDAQ",
                 "time_series": [{"date": "20260101", "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1}]}
                for s in symbols]

    async def fake_order(self, node_id, node_type, config, context, **kw):
        order_calls.append((config.get("order") or {}).get("symbol", "?"))
        return {"order_id": f"X{len(order_calls)}", "status": "simulated", "dry_run": True}

    with patch.object(BrokerNodeExecutor, "execute", new=fake_broker), \
         patch.object(HistoricalDataNodeExecutor, "_fetch_overseas_stock", new=fake_fetch), \
         patch.object(NewOrderNodeExecutor, "execute", new=fake_order):
        job = await WorkflowExecutor().execute(workflow, context_params=context_params)
        try:
            await asyncio.wait_for(job._task, timeout=30)
        except asyncio.TimeoutError:
            await job.stop()
    return job, fetch_calls, order_calls


# ---------------------------------------------------------------------------
# 3.1.5 표본 상한
# ---------------------------------------------------------------------------

async def test_dry_run_default_k3_samples_auto_iterate():
    job, fetch, orders = await _run(_wf_hist({"symbol": "{{ item }}"}, with_orders=True), {"dry_run": True})
    st = job.get_state()
    assert st["errors"] == [], st["errors"]
    assert len(fetch) == 3, f"historical 호출 {len(fetch)}회 (기대 3)"
    assert [c[0] for c in fetch] == ["S00", "S01", "S02"], "앞에서 K개"
    assert len(orders) == 3, f"주문 후보 {len(orders)} (기대 ≤3)"
    samp = st["dry_run_sampling"]
    assert samp["applied"] is True and samp["k"] == 3
    assert {"node_id": "historical", "n": 10, "k": 3} in samp["nodes"]
    assert {"node_id": "buy_order", "n": 10, "k": 3} in samp["nodes"]
    assert any("10 items → sampled 3" in l["message"] for l in job.context.get_logs(limit=500))


async def test_dry_run_sample_size_zero_means_full():
    job, fetch, _ = await _run(_wf_hist({"symbol": "{{ item }}"}), {"dry_run": True, "dry_run_sample_size": 0})
    assert len(fetch) == 10
    assert job.get_state()["dry_run_sampling"] == {"applied": False, "k": 0, "nodes": []}


async def test_runtime_never_samples():
    job, fetch, _ = await _run(_wf_hist({"symbol": "{{ item }}"}), None)
    assert len(fetch) == 10
    assert job.get_state()["dry_run_sampling"]["applied"] is False


def test_deep_validate_is_not_sampled():
    ctx = ExecutionContext(job_id="j", workflow_id="w", context_params={"deep_validate": True})
    assert ctx.is_dry_run is True and ctx.dry_run_sampling_active is False
    ctx2 = ExecutionContext(job_id="j", workflow_id="w", context_params={"dry_run": True})
    assert ctx2.dry_run_sampling_active is True and ctx2.dry_run_sample_size == 3
    ctx3 = ExecutionContext(job_id="j", workflow_id="w", context_params={"dry_run": True, "dry_run_sample_size": "7"})
    assert ctx3.dry_run_sample_size == 7
    ctx4 = ExecutionContext(job_id="j", workflow_id="w", context_params={"dry_run": True, "dry_run_sample_size": "bad"})
    assert ctx4.dry_run_sample_size == 3, "잘못된 값은 기본 3"


async def test_standalone_plural_list_sampled_in_dry_run():
    literal = [{"symbol": s["symbol"], "exchange": "NASDAQ"} for s in WATCH10]
    job, fetch, _ = await _run(_wf_hist({"symbols": literal}, with_watchlist=False), {"dry_run": True})
    assert job.get_state()["errors"] == []
    assert fetch == [["S00", "S01", "S02"]], fetch
    assert {"node_id": "historical", "n": 10, "k": 3} in job.get_state()["dry_run_sampling"]["nodes"]


async def test_plural_binding_with_upstream_sampled_to_k_calls():
    """사건 모양(symbols 전체 바인딩 + 상류 배열) 도 3.1.3 × 3.1.5 = 3회 × 1종목."""
    job, fetch, _ = await _run(_wf_hist({"symbols": "{{ nodes.watchlist.symbols }}"}), {"dry_run": True})
    assert job.get_state()["errors"] == []
    assert fetch == [["S00"], ["S01"], ["S02"]], fetch


# ---------------------------------------------------------------------------
# 3.1.4 진단 보강
# ---------------------------------------------------------------------------

_SLOW_CODE = (
    "import time\n"
    "async def execute(data, params, context):\n"
    "    time.sleep(params.get('sleep', 1.0))\n"
    "    return {'value': 1}"
)


async def test_running_node_exposes_status_started_at_elapsed():
    wf = {
        "id": "wf-diag", "name": "diag", "version": "1.0.0",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            {"id": "slow", "type": "CodeNode", "params": {"sleep": 1.2},
             "outputs": [{"name": "value", "type": "number"}], "code": _SLOW_CODE},
        ],
        "edges": [{"from": "start", "to": "slow"}],
    }
    job = await WorkflowExecutor().execute(wf, context_params={"dry_run": True})
    # 실행 중 스냅샷 — 60초 타임아웃으로 잘린 샌드박스가 보는 모양
    await asyncio.sleep(0.5)
    mid = job.get_state()
    slow = mid["nodes"]["slow"]
    assert slow["state"] == "running" and slow["status"] == "running", slow
    assert "started_at" in slow and slow["elapsed_ms"] >= 300, slow
    assert "duration_ms" not in slow
    assert mid["nodes"]["start"]["status"] == mid["nodes"]["start"]["state"] == "completed"

    await asyncio.wait_for(job._task, timeout=30)
    done = job.get_state()
    slow = done["nodes"]["slow"]
    assert slow["state"] == slow["status"] == "completed"
    assert slow["duration_ms"] >= 1000 and "elapsed_ms" not in slow and "started_at" in slow
    for entry in done["nodes"].values():
        assert entry["status"] == entry["state"]
