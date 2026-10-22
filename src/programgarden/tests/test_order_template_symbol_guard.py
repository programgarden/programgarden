"""C23: 미해석 템플릿 심볼 차단 + 결과 오염 방지.

상류 바인딩이 풀리지 않아 order.symbol 이 '{{ item.symbol }}' 리터럴로 넘어오면:
  1) _normalize_order 가 주문 자체를 만들지 않는다(None) — 브로커로 안 나간다.
  2) 그래도 _order_result 를 부르는 실패 경로는 symbol/exchange 를 None 으로 비우고
     error='unresolved_template_symbol', diagnostics 에 원문을 남긴다.
prod 실측 order_fills id=17(symbol='{{ item.symbol }}') 재발 차단.
"""
from unittest.mock import AsyncMock

import pytest

from programgarden.context import ExecutionContext
from programgarden.executor import NewOrderNodeExecutor


def _executor() -> NewOrderNodeExecutor:
    return NewOrderNodeExecutor.__new__(NewOrderNodeExecutor)


class TestNormalizeOrderTemplateGuard:
    def test_template_symbol_returns_none(self):
        out = _executor()._normalize_order(
            {"symbol": "{{ item.symbol }}", "exchange": "NASDAQ",
             "quantity": 1, "price": 10.0}, {},
        )
        assert out is None

    def test_template_exchange_returns_none(self):
        out = _executor()._normalize_order(
            {"symbol": "AAPL", "exchange": "{{ item.exchange }}",
             "quantity": 1, "price": 10.0}, {},
        )
        assert out is None

    def test_valid_symbol_still_normalizes(self):
        out = _executor()._normalize_order(
            {"symbol": "AAPL", "exchange": "NASDAQ", "quantity": 1, "price": 10.0}, {},
        )
        assert out is not None
        assert out["symbol"] == "AAPL"

    def test_template_symbol_logs_error_reason(self):
        ctx = ExecutionContext(job_id="j", workflow_id="w")
        out = _executor()._normalize_order(
            {"symbol": "{{ item.symbol }}", "exchange": "NASDAQ",
             "quantity": 1, "price": 10.0}, {}, ctx, "order_node",
        )
        assert out is None
        error_logs = [l for l in ctx.get_logs() if l["level"] == "error"]
        assert any("unresolved_template_symbol" in l["message"] for l in error_logs)


class TestOrderResultTemplateGuard:
    def test_template_symbol_nulled_with_error_code(self):
        # 현재가 조회 실패 경로가 템플릿 심볼로 _order_result 를 부르는 상황 재현.
        result = _executor()._order_result(
            False, "{{ item.symbol }}", "NASDAQ", "buy", 1, 0, "현재가 조회 실패",
        )
        inner = result["order_result"]
        assert inner["symbol"] is None
        assert inner["error"] == "unresolved_template_symbol"
        assert inner["success"] is False
        assert inner["status"] == "failed"
        assert inner["diagnostics"]["unresolved_template"] is True
        assert inner["diagnostics"]["raw_symbol"] == "{{ item.symbol }}"

    def test_template_exchange_nulled(self):
        result = _executor()._order_result(
            True, "AAPL", "{{ item.exchange }}", "sell", 2, 100.0, None, "ord-9",
        )
        inner = result["order_result"]
        assert inner["symbol"] is None
        assert inner["exchange"] is None
        assert inner["error"] == "unresolved_template_symbol"
        assert inner["diagnostics"]["raw_exchange"] == "{{ item.exchange }}"

    def test_normal_result_unchanged(self):
        result = _executor()._order_result(
            True, "AAPL", "NASDAQ", "buy", 1, 190.0, None, "ord-1",
        )
        inner = result["order_result"]
        assert inner["symbol"] == "AAPL"
        assert inner["exchange"] == "NASDAQ"
        assert inner["success"] is True
        assert inner["status"] == "submitted"
        assert inner["diagnostics"] is None


class TestBrokerNotCalledOnTemplateSymbol:
    @pytest.mark.asyncio
    async def test_execute_order_never_dispatches_to_broker(self):
        ex = _executor()
        # 세 상품 주문 경로를 스파이 — 하나라도 불리면 실패.
        ex._execute_overseas_stock = AsyncMock()
        ex._execute_korea_stock = AsyncMock()
        ex._execute_overseas_futures = AsyncMock()

        ctx = ExecutionContext(job_id="j", workflow_id="w")
        config = {
            "connection": {
                "appkey": "x", "appsecret": "y", "product": "overseas_stock",
            },
            "order": {
                "symbol": "{{ item.symbol }}", "exchange": "NASDAQ",
                "quantity": 1, "price": 10.0,
            },
            "side": "buy",
            "order_type": "limit",
        }

        result = await ex._execute_order("node1", "StockNewOrderNode", config, ctx)

        # 브로커 주문 메서드 0회 호출.
        ex._execute_overseas_stock.assert_not_awaited()
        ex._execute_korea_stock.assert_not_awaited()
        ex._execute_overseas_futures.assert_not_awaited()

        # 결과는 성공이 아니며, 로그에 unresolved_template_symbol 사유가 남는다.
        assert result["order_result"]["success"] is False
        error_logs = [l for l in ctx.get_logs() if l["level"] == "error"]
        assert any("unresolved_template_symbol" in l["message"] for l in error_logs)
