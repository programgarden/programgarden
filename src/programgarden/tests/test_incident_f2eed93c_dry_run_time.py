"""
Phase 1 종료 검토 — 사건 DSL(f2eed93c 재구성) dry_run 완주 시간.

LS 호출 3종(계좌·과거시세·현재가)만 mock 하고 **주문 노드는 실제 dry_run 경로**(모의 응답 +
클래스 _rate_limit 5초 그대로)로 돈다. 종전 코드라면 매수 4건 × 5초 pacing 만으로 15초를
넘겼고(사건 당시 16건 = 75초), 수정 후엔 흐름 전체가 3초 안에 끝나야 한다.
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

from programgarden.executor import (
    AccountNodeExecutor,
    BrokerNodeExecutor,
    HistoricalDataNodeExecutor,
    MarketDataNodeExecutor,
    WorkflowExecutor,
)

FIXTURE = Path(__file__).parent / "fixtures" / "f2eed93c-ma-golden-cross-stop-loss.json"
CROSSERS = {"AAPL", "MSFT", "NVDA", "AMZN"}          # 마지막 봉에서 MA10 > MA30 골든크로스
HELD = [  # 보유 2종목 — 첫 종목이 -10% (손절선 -8% 아래)
    {"symbol": "HOLD1", "exchange": "NASDAQ", "exchange_code": "82", "quantity": 5, "qty": 5,
     "avg_price": 100.0, "current_price": 90.0, "price": 90.0, "pnl_rate": -10.0, "close_side": "sell"},
    {"symbol": "HOLD2", "exchange": "NASDAQ", "exchange_code": "82", "quantity": 3, "qty": 3,
     "avg_price": 100.0, "current_price": 105.0, "price": 105.0, "pnl_rate": 5.0, "close_side": "sell"},
]


def _series(symbol: str) -> List[Dict[str, Any]]:
    bars = [{"date": f"2026{(i // 28) + 1:02d}{(i % 28) + 1:02d}", "open": 100.0, "high": 100.0,
             "low": 100.0, "close": 100.0, "volume": 1000} for i in range(59)]
    last = 150.0 if symbol in CROSSERS else 50.0
    bars.append({"date": "20260601", "open": last, "high": last, "low": last, "close": last, "volume": 1000})
    return bars


async def _run(context_params: Dict[str, Any]) -> tuple:
    fetch_calls: List[List[str]] = []

    async def fake_broker(self, node_id, node_type, config, context, **kw):
        return {"connection": {"product": "overseas_stock", "paper_trading": True,
                               "credential_id": "broker_cred", "appkey": "x", "appsecret": "y"}}

    async def fake_account(self, node_id, node_type, config, context, **kw):
        return {
            "positions": [dict(p) for p in HELD],
            "balance": {"orderable_amount": 100000.0, "cash": 100000.0, "total_value": 100000.0,
                        "USD": {"orderable_amount": 100000.0}},
            "held_symbols": [{"exchange": p["exchange"], "exchange_code": "82", "symbol": p["symbol"]} for p in HELD],
        }

    async def fake_hist(self, symbols, start_date, end_date, interval, context, node_id, *rest):
        fetch_calls.append(list(symbols))
        return [{"symbol": s, "exchange": "NASDAQ", "time_series": _series(s)} for s in symbols]

    async def fake_market(self, symbols, context, node_id):
        vals = [{"symbol": e.get("symbol"), "exchange": e.get("exchange", "NASDAQ"),
                 "price": 150.0, "current_price": 150.0, "last_price": 150.0} for e in symbols]
        return {"value": vals[0] if len(vals) == 1 else None, "values": vals,
                "symbols": [v["symbol"] for v in vals]}

    workflow = json.loads(FIXTURE.read_text(encoding="utf-8"))
    with patch.object(BrokerNodeExecutor, "execute", new=fake_broker), \
         patch.object(AccountNodeExecutor, "execute", new=fake_account), \
         patch.object(HistoricalDataNodeExecutor, "_fetch_overseas_stock", new=fake_hist), \
         patch.object(MarketDataNodeExecutor, "_fetch_overseas_stock", new=fake_market):
        t0 = time.monotonic()
        job = await WorkflowExecutor().execute(workflow, context_params=context_params)
        try:
            await asyncio.wait_for(job._task, timeout=60)
        except asyncio.TimeoutError:
            await job.stop()
        elapsed = time.monotonic() - t0
    return job, fetch_calls, elapsed


def _simulated(job, node_id: str) -> int:
    return sum(1 for l in job.context.get_logs(limit=1000)
               if l.get("node_id") == node_id and "simulated order" in (l.get("message") or ""))


async def test_full_dry_run_completes_under_3s_with_ls_mocked():
    job, fetch, elapsed = await _run({"dry_run": True, "dry_run_sample_size": 0})
    st = job.get_state()
    assert st["status"] == "completed", st["status"]
    assert st["errors"] == [], st["errors"]
    assert elapsed < 3.0, f"dry_run 완주 {elapsed:.2f}s (기대 < 3s; 종전 코드는 pacing 만으로 ≥ 15s)"
    # 3.1.3: 7종목 × 1회 (49회 아님)
    assert len(fetch) == 7 and all(len(c) == 1 for c in fetch), fetch
    # 3.1.2: 골든크로스 4종목 → sizing 1회(전체) → 매수 4건 (16건 아님)
    assert len(job.context.get_output("sizing", "symbols")) == 4
    assert len(job.context.get_output("sizing", "orders")) == 4
    assert _simulated(job, "buy_order") == 4
    # 손절: -10% 보유 1종목만 매도
    assert _simulated(job, "sell_order") == 1
    assert st["dry_run_sampling"]["applied"] is False
    print(f"\n  [f2eed93c] dry_run 완주 {elapsed:.2f}s — historical {len(fetch)}회, buy 4, sell 1")


async def test_default_sampling_k3_shortens_and_reports():
    job, fetch, elapsed = await _run({"dry_run": True})
    st = job.get_state()
    assert st["status"] == "completed" and st["errors"] == [], st["errors"]
    assert elapsed < 3.0, elapsed
    assert len(fetch) == 3, fetch
    samp = st["dry_run_sampling"]
    assert samp["applied"] is True and samp["k"] == 3
    assert {"node_id": "historical", "n": 7, "k": 3} in samp["nodes"]
    assert 1 <= _simulated(job, "buy_order") <= 3
    for node_id, entry in st["nodes"].items():
        assert entry["status"] == entry["state"], node_id
