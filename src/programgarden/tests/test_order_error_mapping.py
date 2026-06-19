"""
Order error mapping / empty-order reason 분류 테스트.

대상 (feat/order-error-mapping, Phase 2-3):
- NewOrderNodeExecutor._execute_overseas_stock 의 COSAT00301 거부 경로 → diagnostics 동봉
- NewOrderNodeExecutor._order_result / _empty_result 구조 (하위호환 + 신규 필드)
- NewOrderNodeExecutor._diagnose_empty_reason (no_signal / fetch_failed / no_symbol)
- PositionSizingNodeExecutor._empty_result reason 분류

전부 mock — 라이브 LS API 호출 없음.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from programgarden_core import EmptyOrderReason, OrderRejectInfo
from programgarden_core.bases.listener import NotificationCategory
from programgarden.executor import NewOrderNodeExecutor, PositionSizingNodeExecutor


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_context() -> MagicMock:
    """_execute_overseas_stock 가 필요로 하는 최소 ExecutionContext mock."""
    ctx = MagicMock()
    ctx.log = MagicMock()
    ctx.record_workflow_order = MagicMock()
    ctx.send_notification = AsyncMock()
    return ctx


def _make_ls_with_cosat_response(response: MagicMock) -> MagicMock:
    """ls.overseas_stock().주문().cosat00301(...).req_async() → response 체인 mock."""
    order_api = MagicMock()
    order_api.req_async = AsyncMock(return_value=response)

    order_ns = MagicMock()
    order_ns.cosat00301 = MagicMock(return_value=order_api)

    overseas_stock = MagicMock()
    overseas_stock.주문 = MagicMock(return_value=order_ns)

    ls = MagicMock()
    ls.overseas_stock = MagicMock(return_value=overseas_stock)
    return ls


def _cosat_response(
    *,
    rsp_cd: str = "00000",
    rsp_msg: str = "정상처리",
    error_msg=None,
    ord_no=None,
) -> MagicMock:
    """COSAT00301 OutBlock 구조(rsp_cd/rsp_msg/error_msg/block2.OrdNo) mock."""
    resp = MagicMock()
    resp.rsp_cd = rsp_cd
    resp.rsp_msg = rsp_msg
    resp.error_msg = error_msg
    if ord_no is None:
        resp.block2 = None
    else:
        b2 = MagicMock()
        b2.OrdNo = ord_no
        resp.block2 = b2
    return resp


ORDER = {"symbol": "AAPL", "exchange": "NASDAQ", "quantity": 1, "price": 150.0}


# ---------------------------------------------------------------------------
# Phase 2: 주문 거부 diagnostics 동봉
# ---------------------------------------------------------------------------

class TestOrderRejectDiagnostics:
    @pytest.mark.asyncio
    async def test_error_msg_rejection_attaches_diagnostics(self):
        """error_msg 거부 경로 → diagnostics.rsp_cd 채워지고 known=False 폴백."""
        ex = NewOrderNodeExecutor()
        ctx = _make_context()
        resp = _cosat_response(rsp_cd="40570", error_msg="잔고 부족")
        ls = _make_ls_with_cosat_response(resp)

        result = await ex._execute_overseas_stock(
            ls, dict(ORDER), "buy", "limit", {}, ctx, "order-1"
        )

        order_result = result["order_result"]
        # 하위호환: 기존 error 키 보존
        assert order_result["error"] == "잔고 부족"
        assert order_result["success"] is False
        # 신규: diagnostics 동봉
        diag = order_result["diagnostics"]
        assert diag is not None
        assert diag["rsp_cd"] == "40570"
        # 빈 매핑 테이블 → known=False raw 폴백
        assert diag["known"] is False
        assert diag["raw_msg"] == "잔고 부족"
        # 거부 알림 1건 발행
        ctx.send_notification.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_empty_order_no_uses_dedicated_diagnostic(self):
        """rsp_cd 성공인데 OrderNo 없음 → 전용 cause(market closed/broker delay)."""
        ex = NewOrderNodeExecutor()
        ctx = _make_context()
        resp = _cosat_response(rsp_cd="00000", rsp_msg="처리중", error_msg=None, ord_no=None)
        ls = _make_ls_with_cosat_response(resp)

        result = await ex._execute_overseas_stock(
            ls, dict(ORDER), "buy", "limit", {}, ctx, "order-2"
        )

        order_result = result["order_result"]
        assert order_result["success"] is False
        # 하위호환: error 키에 Empty OrderNo prefix 보존
        assert order_result["error"].startswith("Empty OrderNo:")
        diag = order_result["diagnostics"]
        assert diag is not None
        assert diag["rsp_cd"] == "00000"
        assert diag["known"] is True
        assert "no order number" in diag["cause"].lower()
        assert diag["tip"] is not None
        ctx.send_notification.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_exception_path_attaches_fallback_diagnostic(self):
        """예외 경로 → map_reject_code 빈 rsp_cd 폴백(known=False)."""
        ex = NewOrderNodeExecutor()
        ctx = _make_context()
        order_api = MagicMock()
        order_api.req_async = AsyncMock(side_effect=RuntimeError("network down"))
        order_ns = MagicMock()
        order_ns.cosat00301 = MagicMock(return_value=order_api)
        overseas_stock = MagicMock()
        overseas_stock.주문 = MagicMock(return_value=order_ns)
        ls = MagicMock()
        ls.overseas_stock = MagicMock(return_value=overseas_stock)

        result = await ex._execute_overseas_stock(
            ls, dict(ORDER), "buy", "limit", {}, ctx, "order-3"
        )

        order_result = result["order_result"]
        assert order_result["success"] is False
        assert "network down" in order_result["error"]
        diag = order_result["diagnostics"]
        assert diag is not None
        assert diag["known"] is False
        assert diag["rsp_cd"] == ""

    @pytest.mark.asyncio
    async def test_success_path_has_null_diagnostics(self):
        """정상 체결 → diagnostics=None, 기존 success 구조 보존."""
        ex = NewOrderNodeExecutor()
        ctx = _make_context()
        resp = _cosat_response(rsp_cd="00000", error_msg=None, ord_no="A123456")
        ls = _make_ls_with_cosat_response(resp)

        result = await ex._execute_overseas_stock(
            ls, dict(ORDER), "buy", "limit", {}, ctx, "order-4"
        )

        order_result = result["order_result"]
        assert order_result["success"] is True
        assert order_result["status"] == "submitted"
        assert order_result["diagnostics"] is None
        assert result["order_id"] == "A123456"
        ctx.send_notification.assert_not_awaited()


# ---------------------------------------------------------------------------
# Phase 2: _order_result 시그니처 하위호환
# ---------------------------------------------------------------------------

class TestOrderResultBackcompat:
    def test_order_result_without_reject_info(self):
        """reject_info 미전달(기존 호출) → diagnostics=None, error 키 그대로."""
        ex = NewOrderNodeExecutor()
        result = ex._order_result(False, "AAPL", "NASDAQ", "buy", 1, 150.0, "boom")
        order_result = result["order_result"]
        assert order_result["error"] == "boom"
        assert order_result["diagnostics"] is None
        # 기존 키 전부 보존
        for key in ("success", "symbol", "exchange", "side", "quantity", "price", "status"):
            assert key in order_result

    def test_order_result_with_reject_info(self):
        ex = NewOrderNodeExecutor()
        reject = OrderRejectInfo(
            rsp_cd="40570", cause="insufficient balance", tip="add funds",
            raw_msg="잔고 부족", known=True,
        )
        result = ex._order_result(
            False, "AAPL", "NASDAQ", "buy", 1, 150.0, "잔고 부족", reject_info=reject
        )
        diag = result["order_result"]["diagnostics"]
        assert diag["rsp_cd"] == "40570"
        assert diag["cause"] == "insufficient balance"
        assert diag["known"] is True


# ---------------------------------------------------------------------------
# Phase 3: NewOrder _empty_result reason 분류
# ---------------------------------------------------------------------------

class TestNewOrderEmptyResultReason:
    def test_default_no_signal(self):
        ex = NewOrderNodeExecutor()
        result = ex._empty_result()
        order_result = result["order_result"]
        assert order_result["reason"] == "no_signal"
        assert "No trading signal" in order_result["message"]
        # 하위호환: 기존 error 키 보존
        assert order_result["error"] == "No order to submit"
        assert order_result["success"] is False

    def test_fetch_failed_message(self):
        ex = NewOrderNodeExecutor()
        result = ex._empty_result(EmptyOrderReason.FETCH_FAILED, "screener boom")
        order_result = result["order_result"]
        assert order_result["reason"] == "fetch_failed"
        assert "fetch failed" in order_result["message"].lower()
        assert order_result["detail"] == "screener boom"

    def test_no_symbol_message(self):
        ex = NewOrderNodeExecutor()
        result = ex._empty_result(EmptyOrderReason.NO_SYMBOL)
        assert result["order_result"]["reason"] == "no_symbol"


class TestDiagnoseEmptyReason:
    def test_normal_empty_upstream_is_no_signal(self):
        """상류 정상 빈 결과(order 자체는 dict 형태지만 정상) → no_signal."""
        ex = NewOrderNodeExecutor()
        # order 가 정상 dict 지만 normalize 실패할 만한 케이스 — 상류 error/빈 신호 없음
        order = {"symbol": "AAPL", "exchange": "NASDAQ", "quantity": 0}
        reason, detail = ex._diagnose_empty_reason(order, {})
        assert reason == EmptyOrderReason.NO_SIGNAL
        assert detail == ""

    def test_upstream_error_dict_is_fetch_failed(self):
        """상류가 빈 symbols 에 error 키 동봉 → fetch_failed."""
        ex = NewOrderNodeExecutor()
        upstream = {"symbols": [], "count": 0, "error": "screener TR failed"}
        reason, detail = ex._diagnose_empty_reason(upstream, {})
        assert reason == EmptyOrderReason.FETCH_FAILED
        assert detail == "screener TR failed"

    def test_upstream_error_via_config_symbols(self):
        ex = NewOrderNodeExecutor()
        config = {"symbols": {"symbols": [], "error": "universe fetch failed"}}
        reason, detail = ex._diagnose_empty_reason(None, config)
        # order=None → balance/symbols 신호 우선. config.symbols 에 error.
        assert reason == EmptyOrderReason.FETCH_FAILED
        assert detail == "universe fetch failed"

    def test_balance_partial_failure_is_fetch_failed(self):
        ex = NewOrderNodeExecutor()
        config = {
            "balance": {
                "_partial_failure": True,
                "_failure_reason": "COSOQ02701 timeout",
                "_failure_codes": ["COSOQ02701"],
            }
        }
        reason, detail = ex._diagnose_empty_reason({"symbol": "AAPL"}, config)
        assert reason == EmptyOrderReason.FETCH_FAILED
        assert "COSOQ02701" in detail

    def test_empty_order_payload_is_no_symbol(self):
        ex = NewOrderNodeExecutor()
        for empty in (None, [], {}, ""):
            reason, _ = ex._diagnose_empty_reason(empty, {})
            assert reason == EmptyOrderReason.NO_SYMBOL, f"failed for {empty!r}"

    def test_normal_nonempty_symbols_not_fetch_failed(self):
        """상류 결과에 error 가 있어도 symbols 가 비어있지 않으면 fetch_failed 아님."""
        ex = NewOrderNodeExecutor()
        upstream = {"symbols": [{"symbol": "AAPL"}], "error": "partial warn"}
        reason, _ = ex._diagnose_empty_reason(upstream, {})
        # symbols 가 채워져 있으므로 error 무시 → 빈 페이로드 아님 → no_signal
        assert reason == EmptyOrderReason.NO_SIGNAL


# ---------------------------------------------------------------------------
# Phase 3: PositionSizing _empty_result reason 분류
# ---------------------------------------------------------------------------

class TestPositionSizingEmptyResult:
    def test_default_no_signal_keeps_legacy_keys(self):
        ex = PositionSizingNodeExecutor()
        result = ex._empty_result()
        # 하위호환: 기존 키 전부 보존
        for key in ("orders", "total_amount", "symbols", "method", "config"):
            assert key in result
        assert result["reason"] == "no_signal"
        assert "No trading signal" in result["message"]

    def test_no_symbol_reason(self):
        ex = PositionSizingNodeExecutor()
        result = ex._empty_result(EmptyOrderReason.NO_SYMBOL)
        assert result["reason"] == "no_symbol"
        assert result["orders"] == []

    def test_fetch_failed_reason_with_detail(self):
        ex = PositionSizingNodeExecutor()
        result = ex._empty_result(EmptyOrderReason.FETCH_FAILED, "balance timeout")
        assert result["reason"] == "fetch_failed"
        assert result["detail"] == "balance timeout"


# ---------------------------------------------------------------------------
# BLOCKER regression: empty-order fetch_failed must NOT be misclassified
# as no_signal when bound via {{ nodes.sizing.order }} to a missing port.
#
# This is the test that was MISSING and let the silent no-op through: the
# upstream sizing/screener produced a fetch-failure empty result, the order
# node bound `{{ nodes.sizing.order }}` (a port that resolved to None), and
# the diagnosis collapsed to no_signal/no_symbol instead of fetch_failed.
# ---------------------------------------------------------------------------

class TestEmptyOrderRealPathBlocker:
    @staticmethod
    def _ctx_with_upstream(node_id: str, output: dict) -> MagicMock:
        ctx = MagicMock()
        ctx.get_all_outputs = MagicMock(
            return_value=(output if True else {})
        )
        # only the requested node id returns the output; others → {}
        def _get_all(nid):
            return output if nid == node_id else {}
        ctx.get_all_outputs.side_effect = _get_all
        return ctx

    def test_upstream_fetch_failed_via_missing_port_is_fetch_failed(self):
        """상류 sizing 이 fetch_failed 빈 결과, order 가 {{ nodes.sizing.order }}
        (해석되면 None) → 상류 FULL 출력 조회로 fetch_failed 로 분류."""
        ex = NewOrderNodeExecutor()
        upstream = {
            "orders": [],
            "order": None,
            "reason": "fetch_failed",
            "message": "Upstream data fetch failed",
            "detail": "screener TR timeout",
        }
        ctx = self._ctx_with_upstream("sizing", upstream)
        reason, detail = ex._diagnose_empty_reason(
            None, {}, "{{ nodes.sizing.order }}", ctx
        )
        assert reason == EmptyOrderReason.FETCH_FAILED
        assert "screener TR timeout" in detail

    def test_upstream_error_key_via_missing_port_is_fetch_failed(self):
        """상류가 error 키만 동봉(빈 symbols) → 상류 조회로 fetch_failed."""
        ex = NewOrderNodeExecutor()
        upstream = {"symbols": [], "count": 0, "error": "screener TR failed"}
        ctx = self._ctx_with_upstream("screener", upstream)
        reason, detail = ex._diagnose_empty_reason(
            None, {}, "{{ nodes.screener.order }}", ctx
        )
        assert reason == EmptyOrderReason.FETCH_FAILED
        assert "screener TR failed" in detail

    def test_upstream_partial_failure_via_missing_port_is_fetch_failed(self):
        """상류 _partial_failure → fetch_failed (symbols 유무 무관)."""
        ex = NewOrderNodeExecutor()
        upstream = {
            "order": None,
            "_partial_failure": True,
            "_failure_reason": "COSOQ02701 timeout",
        }
        ctx = self._ctx_with_upstream("sizing", upstream)
        reason, detail = ex._diagnose_empty_reason(
            None, {}, "{{ nodes.sizing.order }}", ctx
        )
        assert reason == EmptyOrderReason.FETCH_FAILED
        assert "COSOQ02701" in detail

    def test_normal_empty_upstream_via_missing_port_is_no_symbol(self):
        """상류가 정상 빈 결과(실패 신호 없음) + order=None → no_symbol(설정 누락)."""
        ex = NewOrderNodeExecutor()
        upstream = {"orders": [], "order": None, "reason": "no_signal"}
        ctx = self._ctx_with_upstream("sizing", upstream)
        reason, _ = ex._diagnose_empty_reason(
            None, {}, "{{ nodes.sizing.order }}", ctx
        )
        # 상류 실패 신호 없음 → order 페이로드 비어있음 → no_symbol
        assert reason == EmptyOrderReason.NO_SYMBOL

    def test_unresolved_literal_expression_is_fetch_failed(self):
        """order 가 미해석 리터럴('{{ ... }}') 로 넘어옴 → fetch_failed(보수적)."""
        ex = NewOrderNodeExecutor()
        reason, detail = ex._diagnose_empty_reason(
            "{{ nodes.sizing.order }}", {}, "{{ nodes.sizing.order }}", None
        )
        assert reason == EmptyOrderReason.FETCH_FAILED
        assert "not be resolved" in detail.lower() or "{{" in detail

    def test_auto_iterate_item_binding_falls_back_gracefully(self):
        """order 가 {{ item }} 바인딩(상류 노드 ref 없음)이면 기존 동작 유지."""
        ex = NewOrderNodeExecutor()
        ctx = self._ctx_with_upstream("sizing", {"reason": "fetch_failed"})
        # raw expr 에 nodes.X 패턴 없음 → 상류 조회 생략 → 빈 order → no_symbol
        reason, _ = ex._diagnose_empty_reason(None, {}, "{{ item }}", ctx)
        assert reason == EmptyOrderReason.NO_SYMBOL

    def test_unknown_upstream_node_does_not_misclassify(self):
        """상류 노드가 미실행/미지(get_all_outputs={}) → fetch_failed 오판 안 함."""
        ex = NewOrderNodeExecutor()
        ctx = MagicMock()
        ctx.get_all_outputs = MagicMock(return_value={})
        reason, _ = ex._diagnose_empty_reason(
            None, {}, "{{ nodes.ghost.order }}", ctx
        )
        assert reason == EmptyOrderReason.NO_SYMBOL

    def test_backward_compatible_two_arg_call(self):
        """기존 2-arg 호출(raw_expr/context 없음)이 그대로 동작."""
        ex = NewOrderNodeExecutor()
        reason, detail = ex._diagnose_empty_reason(
            {"symbols": [], "error": "boom"}, {}
        )
        assert reason == EmptyOrderReason.FETCH_FAILED
        assert detail == "boom"


# ---------------------------------------------------------------------------
# BLOCKER end-to-end: production wiring of the raw_order_expr capture.
#
# The unit tests above call _diagnose_empty_reason(...) DIRECTLY with a hand-
# injected raw_order_expr/context, so they do NOT protect the load-bearing
# capture line inside NewOrderNodeExecutor.execute():
#
#     raw_order_expr = config.get("order")   # captured BEFORE evaluate
#     config = evaluate_all_bindings(config, context, node_id)
#
# If a refactor moved that capture AFTER evaluate_all_bindings (which rebinds
# config["order"] to None and loses the expression text), every direct-call
# test would stay green while the real path silently regressed.
#
# These tests drive the REAL execute() path against a REAL ExecutionContext:
#   config raw capture → evaluate_all_bindings(real) → _normalize_order(real)
#     → _diagnose_empty_reason(real) → _empty_result(real)
#
# No LS login / broker resolution mock is needed: the empty-order branch
# returns from execute() (line ~12277) BEFORE the LS login block (~12348),
# so the path is fully exercised with no live API contact. The only wiring
# required is a `connection` dict in config (so execute() does not bail at the
# connection guard) and an upstream `sizing` output stored in the context.
# ---------------------------------------------------------------------------

class TestExecuteRawOrderExprWiring:
    @staticmethod
    def _real_context_with_upstream(node_id: str, output: dict):
        """Real ExecutionContext with one upstream node output stored.

        Using a real context (not a MagicMock) means evaluate_all_bindings,
        get_expression_context, and get_all_outputs all behave authentically —
        '{{ nodes.<id>.order }}' resolves to None via the real evaluator
        (getattr(proxy, 'order', None) swallows the missing-port AttributeError),
        exactly as it does in production.
        """
        from programgarden.context import ExecutionContext

        ctx = ExecutionContext(job_id="job-e2e", workflow_id="wf-e2e")
        for port, value in output.items():
            ctx.set_output(node_id, port, value)
        return ctx

    # connection dict gets execute() past the connection guard; product is
    # forced to overseas_stock by the node_type prefix ("Stock...").
    _CONNECTION = {"product": "overseas_stock", "paper_trading": False}

    @pytest.mark.asyncio
    async def test_execute_missing_port_fetch_failed_is_wired(self):
        """E2E: upstream sizing produced a fetch_failed empty result; the order
        node binds '{{ nodes.sizing.order }}' (resolves to None because sizing
        only emits 'orders'). execute() must capture the RAW expression before
        evaluate_all_bindings and diagnose fetch_failed via the upstream lookup.
        """
        ex = NewOrderNodeExecutor()
        upstream = {
            "orders": [],
            "symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}],
            "reason": "fetch_failed",
            "message": "Upstream data fetch failed",
            "detail": "screener TR failed",
        }
        ctx = self._real_context_with_upstream("sizing", upstream)

        config = {
            "connection": dict(self._CONNECTION),
            "order": "{{ nodes.sizing.order }}",
            "side": "buy",
            "order_type": "limit",
        }
        result = await ex.execute(
            "order-e2e", "StockNewOrderNode", config, ctx
        )

        order_result = result["order_result"]
        assert order_result["success"] is False
        # The load-bearing assertion: the full real chain surfaced fetch_failed,
        # not no_signal / no_symbol. This only holds if raw_order_expr was
        # captured BEFORE evaluate_all_bindings rebound config["order"] to None.
        assert order_result["reason"] == "fetch_failed"
        # Upstream failure signal is carried through to message/detail.
        assert order_result["detail"] == "screener TR failed"
        assert "fetch failed" in order_result["message"].lower()

    @pytest.mark.asyncio
    async def test_execute_missing_port_no_signal_control(self):
        """Control: upstream sizing produced a NORMAL empty result (no failure
        signal). The same missing-port binding must NOT be misread as
        fetch_failed — execute() yields no_symbol (empty payload, no upstream
        error) rather than fetch_failed.
        """
        ex = NewOrderNodeExecutor()
        upstream = {
            "orders": [],
            "symbols": [],
            "reason": "no_signal",
            "message": "No trading signal today",
        }
        ctx = self._real_context_with_upstream("sizing", upstream)

        config = {
            "connection": dict(self._CONNECTION),
            "order": "{{ nodes.sizing.order }}",
            "side": "buy",
            "order_type": "limit",
        }
        result = await ex.execute(
            "order-e2e", "StockNewOrderNode", config, ctx
        )

        order_result = result["order_result"]
        assert order_result["success"] is False
        # No upstream failure signal + empty order payload → no_symbol, and
        # critically NOT fetch_failed (no false positive).
        assert order_result["reason"] != "fetch_failed"
        assert order_result["reason"] == "no_symbol"


# ---------------------------------------------------------------------------
# Overseas futures (CIDBT00100) reject diagnostics — structural parity
# ---------------------------------------------------------------------------

def _make_ls_with_futures_response(response: MagicMock) -> MagicMock:
    """ls.overseas_futureoption().order().CIDBT00100(...).req_async() chain."""
    order_api = MagicMock()
    order_api.req_async = AsyncMock(return_value=response)
    order_ns = MagicMock()
    order_ns.CIDBT00100 = MagicMock(return_value=order_api)
    ofo = MagicMock()
    ofo.order = MagicMock(return_value=order_ns)
    ls = MagicMock()
    ls.overseas_futureoption = MagicMock(return_value=ofo)
    return ls


def _futures_response(*, rsp_cd="00000", rsp_msg="정상처리", error_msg=None, ord_no=None):
    resp = MagicMock()
    resp.rsp_cd = rsp_cd
    resp.rsp_msg = rsp_msg
    resp.error_msg = error_msg
    if ord_no is None:
        resp.block2 = None
    else:
        b2 = MagicMock()
        b2.OvrsFutsOrdNo = ord_no
        resp.block2 = b2
    return resp


FUT_ORDER = {"symbol": "HSIM25", "exchange": "HKEX", "quantity": 1, "price": 18000.0}


class TestOverseasFuturesRejectDiagnostics:
    @pytest.mark.asyncio
    async def test_futures_error_msg_attaches_diagnostics_and_notifies(self):
        ex = NewOrderNodeExecutor()
        ctx = _make_context()
        resp = _futures_response(rsp_cd="50001", error_msg="증거금 부족")
        ls = _make_ls_with_futures_response(resp)

        result = await ex._execute_overseas_futures(
            ls, dict(FUT_ORDER), "buy", "limit", {}, ctx, "fut-1"
        )
        order_result = result["order_result"]
        assert order_result["success"] is False
        assert order_result["error"] == "증거금 부족"
        diag = order_result["diagnostics"]
        assert diag is not None
        assert diag["rsp_cd"] == "50001"
        # empty futures table → known=False raw fallback
        assert diag["known"] is False
        assert diag["raw_msg"] == "증거금 부족"
        ctx.send_notification.assert_awaited_once()
        # ORDER_REJECTED category + futures node label
        _, kwargs = ctx.send_notification.await_args
        assert kwargs["category"] == NotificationCategory.ORDER_REJECTED
        assert kwargs["node_type"] == "OverseasFuturesNewOrderNode"

    @pytest.mark.asyncio
    async def test_futures_empty_order_no_uses_dedicated_diagnostic(self):
        ex = NewOrderNodeExecutor()
        ctx = _make_context()
        resp = _futures_response(rsp_cd="00000", rsp_msg="처리중", ord_no="")
        ls = _make_ls_with_futures_response(resp)

        result = await ex._execute_overseas_futures(
            ls, dict(FUT_ORDER), "buy", "limit", {}, ctx, "fut-2"
        )
        order_result = result["order_result"]
        assert order_result["success"] is False
        assert order_result["error"].startswith("Empty OrderNo:")
        diag = order_result["diagnostics"]
        assert diag is not None
        assert diag["known"] is True
        assert "no order number" in diag["cause"].lower()
        ctx.send_notification.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_futures_exception_attaches_fallback_diagnostic(self):
        ex = NewOrderNodeExecutor()
        ctx = _make_context()
        order_api = MagicMock()
        order_api.req_async = AsyncMock(side_effect=RuntimeError("net down"))
        order_ns = MagicMock()
        order_ns.CIDBT00100 = MagicMock(return_value=order_api)
        ofo = MagicMock()
        ofo.order = MagicMock(return_value=order_ns)
        ls = MagicMock()
        ls.overseas_futureoption = MagicMock(return_value=ofo)

        result = await ex._execute_overseas_futures(
            ls, dict(FUT_ORDER), "buy", "limit", {}, ctx, "fut-3"
        )
        order_result = result["order_result"]
        assert order_result["success"] is False
        assert "net down" in order_result["error"]
        diag = order_result["diagnostics"]
        assert diag is not None
        assert diag["known"] is False
        assert diag["rsp_cd"] == ""

    @pytest.mark.asyncio
    async def test_futures_success_has_null_diagnostics(self):
        ex = NewOrderNodeExecutor()
        ctx = _make_context()
        resp = _futures_response(rsp_cd="00000", ord_no="F987654")
        ls = _make_ls_with_futures_response(resp)

        result = await ex._execute_overseas_futures(
            ls, dict(FUT_ORDER), "buy", "limit", {}, ctx, "fut-4"
        )
        order_result = result["order_result"]
        assert order_result["success"] is True
        assert order_result["diagnostics"] is None
        assert result["order_id"] == "F987654"
        ctx.send_notification.assert_not_awaited()


# ---------------------------------------------------------------------------
# Korea stock (CSPAT00601) reject diagnostics + empty-OrderNo guard
# ---------------------------------------------------------------------------

def _make_ls_with_korea_response(response: MagicMock) -> MagicMock:
    order_api = MagicMock()
    order_api.req_async = AsyncMock(return_value=response)
    order_ns = MagicMock()
    order_ns.cspat00601 = MagicMock(return_value=order_api)
    ks = MagicMock()
    ks.order = MagicMock(return_value=order_ns)
    ls = MagicMock()
    ls.korea_stock = MagicMock(return_value=ks)
    return ls


def _korea_response(*, rsp_cd="00000", rsp_msg="정상처리", error_msg=None, ord_no=None):
    resp = MagicMock()
    resp.rsp_cd = rsp_cd
    resp.rsp_msg = rsp_msg
    resp.error_msg = error_msg
    if ord_no is None:
        resp.block2 = None
    else:
        b2 = MagicMock()
        b2.OrdNo = ord_no
        resp.block2 = b2
    return resp


KR_ORDER = {"symbol": "005930", "exchange": "KRX", "quantity": 1, "price": 70000.0}


class TestKoreaStockRejectDiagnostics:
    @pytest.mark.asyncio
    async def test_korea_error_msg_attaches_diagnostics_and_notifies(self):
        ex = NewOrderNodeExecutor()
        ctx = _make_context()
        resp = _korea_response(rsp_cd="40300", error_msg="주문가능금액 부족")
        ls = _make_ls_with_korea_response(resp)

        result = await ex._execute_korea_stock(
            ls, dict(KR_ORDER), "buy", "limit", {}, ctx, "kr-1"
        )
        order_result = result["order_result"]
        assert order_result["success"] is False
        assert order_result["error"] == "주문가능금액 부족"
        diag = order_result["diagnostics"]
        assert diag is not None
        assert diag["rsp_cd"] == "40300"
        assert diag["known"] is False
        ctx.send_notification.assert_awaited_once()
        _, kwargs = ctx.send_notification.await_args
        assert kwargs["category"] == NotificationCategory.ORDER_REJECTED
        assert kwargs["node_type"] == "KoreaStockNewOrderNode"

    @pytest.mark.asyncio
    async def test_korea_zero_order_no_is_rejected_not_silent_success(self):
        """OrdNo int default 0 → str(0)=='0' truthy. 빈/0 OrderNo 는 성공으로
        silently 기록되지 않고 명시 거부(diagnostics)로 처리되어야 한다."""
        ex = NewOrderNodeExecutor()
        ctx = _make_context()
        resp = _korea_response(rsp_cd="00000", rsp_msg="처리중", ord_no=0)
        ls = _make_ls_with_korea_response(resp)

        result = await ex._execute_korea_stock(
            ls, dict(KR_ORDER), "buy", "limit", {}, ctx, "kr-2"
        )
        order_result = result["order_result"]
        assert order_result["success"] is False
        assert order_result["error"].startswith("Empty OrderNo:")
        assert order_result["diagnostics"]["known"] is True
        ctx.send_notification.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_korea_success_records_order_no(self):
        ex = NewOrderNodeExecutor()
        ctx = _make_context()
        resp = _korea_response(rsp_cd="00000", ord_no=123456)
        ls = _make_ls_with_korea_response(resp)

        result = await ex._execute_korea_stock(
            ls, dict(KR_ORDER), "buy", "limit", {}, ctx, "kr-3"
        )
        order_result = result["order_result"]
        assert order_result["success"] is True
        assert order_result["order_id"] == "123456"
        assert order_result["product"] == "korea_stock"
        ctx.send_notification.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_korea_exception_attaches_fallback_diagnostic(self):
        ex = NewOrderNodeExecutor()
        ctx = _make_context()
        order_api = MagicMock()
        order_api.req_async = AsyncMock(side_effect=RuntimeError("kr net down"))
        order_ns = MagicMock()
        order_ns.cspat00601 = MagicMock(return_value=order_api)
        ks = MagicMock()
        ks.order = MagicMock(return_value=order_ns)
        ls = MagicMock()
        ls.korea_stock = MagicMock(return_value=ks)

        result = await ex._execute_korea_stock(
            ls, dict(KR_ORDER), "buy", "limit", {}, ctx, "kr-4"
        )
        order_result = result["order_result"]
        assert order_result["success"] is False
        assert "kr net down" in order_result["error"]
        assert order_result["diagnostics"]["known"] is False
        assert order_result["diagnostics"]["rsp_cd"] == ""
