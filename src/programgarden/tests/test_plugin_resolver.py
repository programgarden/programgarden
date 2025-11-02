from __future__ import annotations

from typing import Any, Dict, List

import pytest

from programgarden.plugin_resolver import PluginResolver
from programgarden import plugin_resolver as resolver_module
from programgarden_core import (
    BaseStrategyConditionOverseasFutures,
    BaseStrategyConditionResponseOverseasFuturesType,
    BaseNewOrderOverseasFutures,
    BaseNewOrderOverseasFuturesResponseType,
)


class DummyNewOrder(BaseNewOrderOverseasFutures):
    id = "DummyNewOrder"
    description = "Test order"
    securities = ["ls-sec.co.kr"]
    order_types = ["new_buy"]

    def __init__(self, *, quantity: int = 1) -> None:
        self.quantity = quantity
        self.available_symbols: List[Dict[str, Any]] = []
        self.held_symbols = []
        self.non_traded_symbols = []
        self.dps = None
        self.system_id = None

    async def execute(self) -> List[BaseNewOrderOverseasFuturesResponseType]:
        symbol = self.available_symbols[0] if self.available_symbols else {"symbol": "UNKNOWN"}
        return [
            {
                "success": True,
                "ord_dt": "20250101",
                "isu_code_val": symbol.get("symbol", "UNKNOWN"),
                "futs_ord_tp_code": "1",
                "bns_tp_code": "2",
                "abrd_futs_ord_ptn_code": "2",
                "ovrs_drvt_ord_prc": 100.0,
                "cndi_ord_prc": 0.0,
                "ord_qty": self.quantity,
                "prdt_code": symbol.get("prdt_code", ""),
                "due_yymm": symbol.get("due_yymm", ""),
                "exch_code": symbol.get("exch_code", symbol.get("exchcd", "")),
                "crcy_code": symbol.get("crcy_code", ""),
            }
        ]

    async def on_real_order_receive(self, order_type: str, response: Dict[str, Any]) -> None:  # pragma: no cover
        return None


class DummyCondition(BaseStrategyConditionOverseasFutures):
    id = "DummyCondition"
    description = "Test condition"
    securities = ["ls-sec.co.kr"]

    def __init__(self, *, weight: int = 1) -> None:
        super().__init__()
        self.weight = weight

    async def execute(self) -> BaseStrategyConditionResponseOverseasFuturesType:
        symbol = self.symbol or {"symbol": "UNKNOWN", "exchcd": "?"}
        return {
            "condition_id": self.id,
            "success": True,
            "symbol": symbol.get("symbol", "UNKNOWN"),
            "exchcd": symbol.get("exchcd", ""),
            "data": {"weight": self.weight},
            "weight": self.weight,
            "product": "overseas_futures",
            "position_side": "long",
        }


@pytest.mark.asyncio
async def test_resolve_buysell_community_executes_plugin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(resolver_module, "get_community_condition", lambda ident: DummyNewOrder if ident == "DummyNewOrder" else None)

    resolver = PluginResolver()

    trade = {
        "condition": {
            "condition_id": "DummyNewOrder",
            "params": {"quantity": 3},
        }
    }
    symbols = [{"symbol": "ADZ25", "exchcd": "CME"}]

    responses, instance = await resolver.resolve_buysell_community(
        system_id="sys-1",
        trade=trade,
        symbols=symbols,
    )

    assert instance is not None
    assert instance.available_symbols == symbols
    assert instance.system_id == "sys-1"

    assert responses is not None
    assert responses[0]["ord_qty"] == 3
    assert responses[0]["isu_code_val"] == "ADZ25"
    assert responses[0]["prdt_code"] == ""
    assert responses[0]["exch_code"] == "CME"
    assert responses[0]["crcy_code"] == ""


@pytest.mark.asyncio
async def test_resolve_condition_returns_plugin_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(resolver_module, "get_community_condition", lambda ident: DummyCondition if ident == "DummyCondition" else None)

    resolver = PluginResolver()
    symbol = {"symbol": "ADZ25", "exchcd": "CME", "product_type": "overseas_futures"}

    result = await resolver.resolve_condition(
        system_id="sys-1",
        condition_id="DummyCondition",
        params={"weight": 5},
        symbol_info=symbol,
    )

    assert result["success"] is True
    assert result["symbol"] == "ADZ25"
    assert result["data"] == {"weight": 5}
