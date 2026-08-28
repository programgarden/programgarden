"""
HistoricalDataNode 복수 `symbols` 바인딩 + 자동반복 = N² 조회 방지 — 3.1.3

배경 (prod 대화 f2eed93c, 2026-08-28): `historical.symbols = "{{ nodes.watchlist.symbols }}"`
로 배선된 노드가 상류 7종목 배열 때문에 7회 반복됐고, 매 회 config.symbols 폴백이
전체 7종목을 다시 조회해 g3204 49회(1건/3초 제한기) → 60초에 2종목만 완료.

수정: 반복 중이면 현재 반복 아이템 1건만 조회(MarketDataNodeExecutor 와 같은 규칙).
반복 소스가 없는 단독 실행은 종전대로 config.symbols 전체. runtime 에도 적용.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List
from unittest.mock import patch

from programgarden.executor import (
    BrokerNodeExecutor,
    HistoricalDataNodeExecutor,
    WorkflowExecutor,
)

WATCHLIST7 = [{"symbol": s, "exchange": "NASDAQ"}
              for s in ("AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA")]


def _wf(historical_cfg: Dict[str, Any], *, with_watchlist: bool) -> Dict[str, Any]:
    nodes = [
        {"id": "start", "type": "StartNode"},
        {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred"},
    ]
    edges = [{"from": "start", "to": "broker"}]
    if with_watchlist:
        nodes.append({"id": "watchlist", "type": "WatchlistNode", "symbols": list(WATCHLIST7)})
        edges += [{"from": "broker", "to": "watchlist"}, {"from": "watchlist", "to": "historical"}]
    else:
        edges += [{"from": "broker", "to": "historical"}]
    nodes.append({
        "id": "historical", "type": "OverseasStockHistoricalDataNode",
        "start_date": "20260101", "end_date": "20260201", "interval": "1d",
        **historical_cfg,
    })
    return {
        "id": "wf-hist-n2", "name": "hist-n2", "version": "1.0.0",
        "nodes": nodes, "edges": edges,
        "credentials": [{
            "credential_id": "broker_cred", "type": "broker_ls_overseas_stock",
            "data": [{"key": "appkey", "value": "dummy", "type": "password"},
                     {"key": "appsecret", "value": "dummy", "type": "password"}],
        }],
    }


async def _run(workflow: Dict[str, Any], *, dry_run: bool = False) -> tuple:
    fetch_calls: List[List[str]] = []

    async def fake_broker(self, node_id, node_type, config, context, **kw):
        return {"connection": {"product": "overseas_stock", "paper_trading": True,
                               "credential_id": "broker_cred", "appkey": "x", "appsecret": "y"}}

    async def fake_fetch(self, symbols, start_date, end_date, interval, context, node_id, *rest):
        fetch_calls.append(list(symbols))
        return [{"symbol": s, "exchange": "NASDAQ",
                 "time_series": [{"date": "20260101", "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1}]}
                for s in symbols]

    with patch.object(BrokerNodeExecutor, "execute", new=fake_broker), \
         patch.object(HistoricalDataNodeExecutor, "_fetch_overseas_stock", new=fake_fetch):
        ex = WorkflowExecutor()
        job = await ex.execute(workflow, context_params={"dry_run": True} if dry_run else None)
        try:
            await asyncio.wait_for(job._task, timeout=30)
        except asyncio.TimeoutError:
            await job.stop()
    return job, fetch_calls


async def test_plural_binding_with_upstream_array_fetches_each_symbol_once():
    """사건 모양: symbols 전체 바인딩 + 상류 7종목 → g3204 7회(회당 1종목), 49회 아님."""
    job, calls = await _run(_wf({"symbols": "{{ nodes.watchlist.symbols }}"}, with_watchlist=True))
    assert job.get_state()["errors"] == [], job.get_state()["errors"]
    assert len(calls) == 7, f"조회 호출 {len(calls)}회 (기대 7)"
    assert all(len(c) == 1 for c in calls), calls
    assert sorted(s for c in calls for s in c) == sorted(e["symbol"] for e in WATCHLIST7)
    assert len(job.context.get_output("historical", "values")) == 7


async def test_plural_binding_runtime_and_dry_run_same_count():
    """runtime 에도 적용 — dry_run 과 동일하게 7회."""
    _, rt = await _run(_wf({"symbols": "{{ nodes.watchlist.symbols }}"}, with_watchlist=True))
    _, dr = await _run(_wf({"symbols": "{{ nodes.watchlist.symbols }}"}, with_watchlist=True), dry_run=True)
    assert sum(len(c) for c in rt) == 7 and sum(len(c) for c in dr) == 7


async def test_item_binding_shape_unchanged():
    """예제 28 모양(symbol: {{ item }}) 은 종전대로 7회 × 1종목."""
    job, calls = await _run(_wf({"symbol": "{{ item }}"}, with_watchlist=True))
    assert job.get_state()["errors"] == []
    assert len(calls) == 7 and all(len(c) == 1 for c in calls)


async def test_standalone_literal_symbols_fetches_whole_list_once():
    """반복 소스가 없는 단독 실행 + 리터럴 symbols 3건 → 1회 호출에 3종목 전체(종전 동작)."""
    literal = [{"symbol": s, "exchange": "NASDAQ"} for s in ("AAPL", "MSFT", "NVDA")]
    job, calls = await _run(_wf({"symbols": literal}, with_watchlist=False))
    assert job.get_state()["errors"] == [], job.get_state()["errors"]
    assert calls == [["AAPL", "MSFT", "NVDA"]], calls
