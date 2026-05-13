"""ScreenerNodeExecutor routing tests — market × data_source matrix.

Covers Phase 3/4 of the screener-multi-market plan:
 - broker auto-detection across overseas_stock / overseas_futures / korea_stock
 - data_source ('auto' / 'ls' / 'yfinance') routing
 - LS branch limited to overseas_stock (fallback for the rest)
 - stock-only fields ignored on futures
 - universe fallback guards for futures / korea_stock without input symbols
 - backward compatibility (no `market` key in legacy workflows)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, patch

import pytest

from programgarden.executor import ScreenerNodeExecutor


class FakeContext:
    """Minimal stand-in for ExecutionContext.

    Only the methods that ScreenerNodeExecutor.execute touches are implemented.
    """

    def __init__(
        self,
        broker_outputs: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> None:
        # broker_type → output dict (or None to simulate "no broker")
        self._broker_outputs: Dict[str, Dict[str, Any]] = broker_outputs or {}
        self.logs: List[Dict[str, str]] = []

    def find_parent_output(self, node_id: str, broker_type: str) -> Optional[Dict[str, Any]]:
        return self._broker_outputs.get(broker_type)

    def log(self, level: str, message: str, node_id: Optional[str] = None) -> None:
        self.logs.append({"level": level, "message": message, "node_id": node_id or ""})

    def get_credential(self, key: str) -> Dict[str, Any]:
        return {}


def _ls_broker_output(product: str) -> Dict[str, Any]:
    return {"connection": {"provider": "ls-sec.co.kr", "product": product}}


def _logs(ctx: FakeContext, level: Optional[str] = None) -> List[str]:
    return [
        entry["message"]
        for entry in ctx.logs
        if level is None or entry["level"] == level
    ]


@pytest.mark.asyncio
async def test_auto_with_overseas_stock_broker_uses_ls():
    """market='auto' + OverseasStockBrokerNode upstream → LS branch."""
    ctx = FakeContext(
        broker_outputs={
            "OverseasStockBrokerNode": _ls_broker_output("overseas_stock"),
        }
    )
    executor = ScreenerNodeExecutor()
    input_symbols = [{"symbol": "AAPL", "exchange": "NASDAQ", "price": 150.0, "market_cap": 2_000_000_000_000}]

    with patch.object(
        ScreenerNodeExecutor,
        "_filter_via_ls_overseas_stock",
        new=AsyncMock(return_value=[{"symbol": "AAPL", "exchange": "NASDAQ", "price": 150.0, "market_cap": 2e12, "volume": 0}]),
    ) as ls_mock:
        result = await executor.execute(
            node_id="screener",
            node_type="ScreenerNode",
            config={"market": "auto", "data_source": "auto", "symbols": input_symbols},
            context=ctx,
        )

    assert ls_mock.await_count == 1
    assert result["count"] == 1
    assert any("LS:overseas_stock" in m for m in _logs(ctx, "info"))


@pytest.mark.asyncio
async def test_auto_with_overseas_futures_broker_falls_back_to_yfinance():
    """market='auto' + OverseasFuturesBrokerNode → use_ls=False, yfinance:overseas_futures."""
    ctx = FakeContext(
        broker_outputs={
            "OverseasFuturesBrokerNode": _ls_broker_output("overseas_futures"),
        }
    )
    executor = ScreenerNodeExecutor()
    input_symbols = [{"symbol": "CL=F", "exchange": "NYMEX"}]

    with patch.object(
        ScreenerNodeExecutor,
        "_filter_symbols",
        new=AsyncMock(return_value=[{"symbol": "CL=F", "exchange": "NYMEX", "market_cap": 0, "volume": 1000, "price": 70.0, "sector": ""}]),
    ) as yf_mock, patch.object(
        ScreenerNodeExecutor,
        "_filter_via_ls_overseas_stock",
        new=AsyncMock(),
    ) as ls_mock:
        result = await executor.execute(
            node_id="screener",
            node_type="ScreenerNode",
            config={"market": "auto", "data_source": "auto", "symbols": input_symbols},
            context=ctx,
        )

    assert ls_mock.await_count == 0
    assert yf_mock.await_count == 1
    assert result["count"] == 1
    assert any("yfinance:overseas_futures" in m for m in _logs(ctx, "info"))


@pytest.mark.asyncio
async def test_auto_no_broker_defaults_to_overseas_stock_yfinance():
    """market='auto' + no broker → effective='overseas_stock', yfinance."""
    ctx = FakeContext()
    executor = ScreenerNodeExecutor()
    input_symbols = [{"symbol": "AAPL", "exchange": "NASDAQ"}]

    with patch.object(
        ScreenerNodeExecutor,
        "_filter_symbols",
        new=AsyncMock(return_value=[{"symbol": "AAPL"}]),
    ) as yf_mock:
        result = await executor.execute(
            node_id="screener",
            node_type="ScreenerNode",
            config={"market": "auto", "data_source": "auto", "symbols": input_symbols},
            context=ctx,
        )

    assert yf_mock.await_count == 1
    assert result["count"] == 1
    assert any("yfinance:overseas_stock" in m for m in _logs(ctx, "info"))


@pytest.mark.asyncio
async def test_data_source_ls_without_broker_returns_error():
    """market='overseas_stock' + data_source='ls' + no broker → explicit error."""
    ctx = FakeContext()
    executor = ScreenerNodeExecutor()

    result = await executor.execute(
        node_id="screener",
        node_type="ScreenerNode",
        config={"market": "overseas_stock", "data_source": "ls", "symbols": [{"symbol": "AAPL"}]},
        context=ctx,
    )

    assert result["symbols"] == []
    assert result["count"] == 0
    assert "Missing broker" in result["error"]
    assert any("OverseasStockBrokerNode" in m for m in _logs(ctx, "error"))


@pytest.mark.asyncio
async def test_data_source_ls_with_futures_warns_and_falls_back():
    """market='overseas_futures' + data_source='ls' → NotImpl warning + yfinance fallback."""
    ctx = FakeContext(
        broker_outputs={
            "OverseasFuturesBrokerNode": _ls_broker_output("overseas_futures"),
        }
    )
    executor = ScreenerNodeExecutor()

    with patch.object(
        ScreenerNodeExecutor,
        "_filter_symbols",
        new=AsyncMock(return_value=[]),
    ) as yf_mock:
        result = await executor.execute(
            node_id="screener",
            node_type="ScreenerNode",
            config={
                "market": "overseas_futures",
                "data_source": "ls",
                "symbols": [{"symbol": "CL=F"}],
            },
            context=ctx,
        )

    assert yf_mock.await_count == 1
    assert any("overseas_stock 만 지원" in m for m in _logs(ctx, "warning"))
    assert any("yfinance:overseas_futures" in m for m in _logs(ctx, "info"))
    assert "error" not in result


@pytest.mark.asyncio
async def test_overseas_futures_drops_stock_only_fields():
    """market='overseas_futures' + market_cap_min/sector → warning + None forced."""
    ctx = FakeContext()
    executor = ScreenerNodeExecutor()
    captured: Dict[str, Any] = {}

    async def capture(self, symbols, market_cap_min, market_cap_max, volume_min,
                      price_min, price_max, sector, exchange, max_results, context, node_id):
        captured["market_cap_min"] = market_cap_min
        captured["market_cap_max"] = market_cap_max
        captured["sector"] = sector
        return [{"symbol": "CL=F"}]

    with patch.object(ScreenerNodeExecutor, "_filter_symbols", new=capture):
        await executor.execute(
            node_id="screener",
            node_type="ScreenerNode",
            config={
                "market": "overseas_futures",
                "data_source": "auto",
                "symbols": [{"symbol": "CL=F"}],
                "market_cap_min": 1_000_000_000,
                "sector": "Energy",
            },
            context=ctx,
        )

    assert captured["market_cap_min"] is None
    assert captured["market_cap_max"] is None
    assert captured["sector"] is None
    assert any("stock 전용 필드 무시됨" in m for m in _logs(ctx, "warning"))


@pytest.mark.asyncio
async def test_korea_stock_without_input_symbols_returns_error():
    """market='korea_stock' + no input_symbols → explicit error (no SP500 fallback)."""
    ctx = FakeContext()
    executor = ScreenerNodeExecutor()

    result = await executor.execute(
        node_id="screener",
        node_type="ScreenerNode",
        config={"market": "korea_stock", "data_source": "auto"},  # no symbols
        context=ctx,
    )

    assert result["symbols"] == []
    assert result["error"] == "korea_stock requires input symbols"
    assert any("KoreaStockSymbolQueryNode" in m for m in _logs(ctx, "error"))


@pytest.mark.asyncio
async def test_overseas_futures_without_input_symbols_returns_error():
    """market='overseas_futures' + no input_symbols → explicit error."""
    ctx = FakeContext()
    executor = ScreenerNodeExecutor()

    result = await executor.execute(
        node_id="screener",
        node_type="ScreenerNode",
        config={"market": "overseas_futures", "data_source": "auto"},
        context=ctx,
    )

    assert result["error"] == "futures requires input symbols"


@pytest.mark.asyncio
async def test_legacy_workflow_without_market_field_uses_auto_default():
    """Legacy workflow JSON without `market` key → default 'auto' → identical to test 1."""
    ctx = FakeContext(
        broker_outputs={
            "OverseasStockBrokerNode": _ls_broker_output("overseas_stock"),
        }
    )
    executor = ScreenerNodeExecutor()
    input_symbols = [{"symbol": "AAPL", "exchange": "NASDAQ"}]

    with patch.object(
        ScreenerNodeExecutor,
        "_filter_via_ls_overseas_stock",
        new=AsyncMock(return_value=[{"symbol": "AAPL"}]),
    ) as ls_mock:
        result = await executor.execute(
            node_id="screener",
            node_type="ScreenerNode",
            config={"data_source": "auto", "symbols": input_symbols},  # no `market`
            context=ctx,
        )

    assert ls_mock.await_count == 1
    assert result["count"] == 1
    assert any("LS:overseas_stock" in m for m in _logs(ctx, "info"))


@pytest.mark.asyncio
async def test_market_mismatch_user_choice_wins_with_warning():
    """User-specified market overrides broker product when they disagree."""
    ctx = FakeContext(
        broker_outputs={
            # User asks for korea_stock but only the overseas_futures broker is upstream.
            # Since BROKER_BY_PRODUCT lookup keys on market_choice, we wire korea_stock here:
            "KoreaStockBrokerNode": _ls_broker_output("overseas_stock"),
        }
    )
    executor = ScreenerNodeExecutor()

    with patch.object(
        ScreenerNodeExecutor,
        "_filter_symbols",
        new=AsyncMock(return_value=[{"symbol": "005930"}]),
    ):
        result = await executor.execute(
            node_id="screener",
            node_type="ScreenerNode",
            config={
                "market": "korea_stock",
                "data_source": "auto",
                "symbols": [{"symbol": "005930"}],
            },
            context=ctx,
        )

    assert result["count"] == 1
    assert any("사용자 지정 market 을 우선" in m for m in _logs(ctx, "warning"))
    assert any("yfinance:korea_stock" in m for m in _logs(ctx, "info"))
