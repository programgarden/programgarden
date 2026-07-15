"""주문 실패가 관측 표면에 드러나는지 검증 (DEF-21).

배경 (2026-07-14, S5 E2E — 해외선물 모의 즉시주문):
    주문 배선이 해소되지 않아 주문이 발주되지 않았다. 엔진은 그 사실을 **정확히
    알고 있었다** — ``order_result`` 에 사유(``reason: "fetch_failed"``)와 detail 까지
    담았다. 그런데 관측 표면은 전부 성공을 말했다:

        노드 상태     : completed  (failed 아님)
        errors_count : 0
        last_error   : null
        job status   : completed

    대시보드·모니터링·사용자 눈에는 "워크플로우 정상 완료" 로 보였고, 실제로는
    매수 주문이 나가지 않았다. 자동매매에서 가장 위험한 실패 모드다.

    원인: 노드는 **예외를 던져야만** FAILED / errors_count 로 잡힌다. 주문 노드는
    실패를 예외가 아니라 ``order_result.success=False`` 로 *정상 반환*한다.

fix 이후 계약 (이 테스트가 못 박는 것):
    - ``order_result.success=False`` + reason != no_signal  → 노드 FAILED,
      errors_count += 1, last_error 기록.
    - ``reason == "no_signal"``("오늘 신호 없음")은 정상 no-op → completed 유지.
    - 주문 노드가 아닌 노드(order_result 없음)는 영향 없음.
    - 흐름은 중단하지 않는다 — 스케줄 잡이 한 사이클의 주문 실패로 죽지 않도록.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from programgarden_core import EmptyOrderReason
from programgarden.executor import (
    NewOrderNodeExecutor,
    _order_failure_from_outputs,
    _orders_filled_from_outputs,
    _orders_placed_from_outputs,
)


class TestOrderFailureDetection:
    def test_fetch_failed_is_surfaced(self):
        """상류 파이프라인 고장 — S5 에서 실제로 나온 그 출력."""
        outputs = {
            "order_result": {
                "success": False,
                "error": "No order to submit",
                "reason": EmptyOrderReason.FETCH_FAILED.value,
                "message": "Upstream data fetch failed; no order placed (pipeline error).",
                "detail": "Order binding was not resolved (unresolved expression: {{ item }})",
            },
            "order_id": "",
        }
        failure = _order_failure_from_outputs(outputs)
        assert failure is not None, "주문이 안 나갔는데 실패로 잡히지 않았다"
        assert "fetch_failed" in failure
        assert "{{ item }}" in failure, "진단에 필요한 detail 이 사라졌다"

    def test_no_signal_is_not_a_failure(self):
        """'오늘 신호 없음' 은 정상 no-op — 실패로 오탐하면 안 된다."""
        outputs = {
            "order_result": {
                "success": False,
                "error": "No order to submit",
                "reason": EmptyOrderReason.NO_SIGNAL.value,
                "message": "No trading signal today; nothing to order.",
                "detail": "",
            },
            "order_id": "",
        }
        assert _order_failure_from_outputs(outputs) is None

    def test_no_symbol_is_surfaced(self):
        """종목이 안 채워진 채 주문 노드에 도달 = 설정 오류 → 실패."""
        outputs = {
            "order_result": {
                "success": False,
                "error": "No order to submit",
                "reason": EmptyOrderReason.NO_SYMBOL.value,
                "message": "No symbol resolved; no order placed.",
                "detail": "",
            }
        }
        failure = _order_failure_from_outputs(outputs)
        assert failure is not None
        assert "no_symbol" in failure

    def test_explicit_error_without_reason_is_surfaced(self):
        """_error_result 경로 — reason 이 아예 없는 실패도 잡는다."""
        outputs = {
            "order_result": {"success": False, "error": "LS API rejected: 40510"},
            "order_id": "",
        }
        failure = _order_failure_from_outputs(outputs)
        assert failure is not None
        assert "40510" in failure

    def test_successful_order_is_not_a_failure(self):
        outputs = {
            "order_result": {"success": True, "order_id": "A0001"},
            "order_id": "A0001",
        }
        assert _order_failure_from_outputs(outputs) is None

    @pytest.mark.parametrize(
        "outputs",
        [
            {},
            {"data": [1, 2, 3]},
            {"report": [{"symbol": "AAPL"}]},
            None,
            "not-a-dict",
            {"order_result": None},
            {"order_result": "weird"},
        ],
    )
    def test_non_order_nodes_are_untouched(self, outputs):
        """주문 노드가 아닌 출력은 절대 실패로 보지 않는다 (오탐 0)."""
        assert _order_failure_from_outputs(outputs) is None


# ── DEF-26: orders_placed / orders_filled 死카운터 배선 ──


class TestOrdersPlacedCounter:
    """orders_placed = 이 노드가 실제로 접수(발주)한 주문 수 (DEF-26)."""

    def test_successful_single_order_counts_one(self):
        outputs = {
            "order_result": {
                "success": True,
                "status": "submitted",
                "symbol": "028670",
                "quantity": 1,
            },
            "order_id": "9972",
        }
        assert _orders_placed_from_outputs(outputs) == 1

    def test_filled_order_still_counts_as_placed(self):
        """접수 후 체결로 승격돼도 '접수 1건'은 그대로."""
        outputs = {
            "order_result": {"success": True, "status": "filled", "quantity": 1},
            "order_id": "9972",
        }
        assert _orders_placed_from_outputs(outputs) == 1

    def test_failed_order_counts_zero(self):
        outputs = {"order_result": {"success": False, "error": "rejected"}, "order_id": ""}
        assert _orders_placed_from_outputs(outputs) == 0

    def test_no_signal_counts_zero(self):
        outputs = {"order_result": {"success": False, "reason": EmptyOrderReason.NO_SIGNAL.value}}
        assert _orders_placed_from_outputs(outputs) == 0

    def test_batch_shape_uses_success_count(self):
        outputs = {"order_result": {"success": True, "success_count": 3, "total": 5}}
        assert _orders_placed_from_outputs(outputs) == 3

    @pytest.mark.parametrize(
        "outputs",
        [{}, None, "x", {"data": [1, 2]}, {"order_result": None}, {"order_result": "weird"}],
    )
    def test_non_order_nodes_count_zero(self, outputs):
        assert _orders_placed_from_outputs(outputs) == 0


class TestOrdersFilledCounter:
    """orders_filled = 재조회로 '완전 체결'이 확인된 주문 수만 (DEF-26/DEF-27)."""

    def test_filled_status_counts_one(self):
        outputs = {"order_result": {"success": True, "status": "filled", "filled_count": 1}}
        assert _orders_filled_from_outputs(outputs) == 1

    def test_submitted_but_unconfirmed_counts_zero(self):
        """DEF-27 핵심: 접수만 됐고 체결 미확인이면 filled 로 세면 안 된다."""
        outputs = {"order_result": {"success": True, "status": "submitted"}}
        assert _orders_filled_from_outputs(outputs) == 0

    def test_open_counts_zero(self):
        outputs = {"order_result": {"success": True, "status": "open", "filled_count": 0}}
        assert _orders_filled_from_outputs(outputs) == 0

    def test_partially_filled_counts_zero(self):
        """부분체결은 '완전 체결'이 아니므로 filled 카운터에 넣지 않는다."""
        outputs = {
            "order_result": {
                "success": True,
                "status": "partially_filled",
                "filled_count": 0,
                "filled_quantity": 3,
            }
        }
        assert _orders_filled_from_outputs(outputs) == 0

    def test_failed_counts_zero(self):
        outputs = {"order_result": {"success": False, "status": "failed"}}
        assert _orders_filled_from_outputs(outputs) == 0

    @pytest.mark.parametrize(
        "outputs", [{}, None, "x", {"order_result": None}, {"data": [1]}]
    )
    def test_non_order_nodes_count_zero(self, outputs):
        assert _orders_filled_from_outputs(outputs) == 0


# ── DEF-27: 접수 후 체결 재조회 (submitted → filled/partially_filled/open) ──


def _mock_ctx():
    ctx = MagicMock()
    ctx.log = MagicMock()
    return ctx


class TestConfirmOrderFill:
    """_confirm_order_fill 이 order_result.status 를 체결 실측으로 승격하는지 +
    어떤 경우에도 접수 성공(success)을 뒤집지 않는지 검증."""

    def _executor(self):
        return NewOrderNodeExecutor()

    def _submitted(self, symbol="028670", qty=1, order_id="9972"):
        return {
            "order_result": {
                "success": True,
                "status": "submitted",
                "symbol": symbol,
                "quantity": qty,
            },
            "order_id": order_id,
        }

    @pytest.mark.asyncio
    async def test_full_fill_upgrades_to_filled(self, monkeypatch):
        ex = self._executor()

        async def fake_query(ls, order_id, symbol, context, node_id):
            return 1, 5270.0

        monkeypatch.setattr(ex, "_query_korea_fill", fake_query)
        order_result = self._submitted()
        await ex._confirm_order_fill(
            MagicMock(), "korea_stock", "market", order_result,
            {"fill_confirm_delay_seconds": 0}, _mock_ctx(), "ord1",
        )
        inner = order_result["order_result"]
        assert inner["status"] == "filled"
        assert inner["filled_count"] == 1
        assert inner["filled_quantity"] == 1
        assert inner["fill_price"] == 5270.0
        assert inner["success"] is True  # never flipped

    @pytest.mark.asyncio
    async def test_no_fill_marks_open(self, monkeypatch):
        ex = self._executor()

        async def fake_query(*a, **k):
            return 0, 0.0

        monkeypatch.setattr(ex, "_query_korea_fill", fake_query)
        order_result = self._submitted()
        await ex._confirm_order_fill(
            MagicMock(), "korea_stock", "limit", order_result,
            {"fill_confirm_delay_seconds": 0}, _mock_ctx(), "ord1",
        )
        inner = order_result["order_result"]
        assert inner["status"] == "open"
        assert inner["filled_count"] == 0
        assert inner["success"] is True

    @pytest.mark.asyncio
    async def test_partial_fill_marks_partially_filled(self, monkeypatch):
        ex = self._executor()

        async def fake_query(*a, **k):
            return 3, 100.0

        monkeypatch.setattr(ex, "_query_korea_fill", fake_query)
        order_result = self._submitted(symbol="AAA", qty=10, order_id="1")
        await ex._confirm_order_fill(
            MagicMock(), "korea_stock", "limit", order_result,
            {"fill_confirm_delay_seconds": 0, "fill_confirm_attempts": 1}, _mock_ctx(), "ord1",
        )
        inner = order_result["order_result"]
        assert inner["status"] == "partially_filled"
        assert inner["filled_quantity"] == 3
        assert inner["filled_count"] == 0

    @pytest.mark.asyncio
    async def test_requery_exception_never_disturbs_submission(self, monkeypatch):
        """재조회가 터져도 예외 전파 없이 접수 성공을 보존한다 (best-effort 계약)."""
        ex = self._executor()

        async def boom(*a, **k):
            raise RuntimeError("network down")

        monkeypatch.setattr(ex, "_query_korea_fill", boom)
        order_result = self._submitted()
        await ex._confirm_order_fill(
            MagicMock(), "korea_stock", "limit", order_result,
            {"fill_confirm_delay_seconds": 0}, _mock_ctx(), "ord1",
        )
        inner = order_result["order_result"]
        assert inner["success"] is True
        assert inner["status"] == "submitted"  # 손대지 않음

    @pytest.mark.asyncio
    async def test_overseas_futures_full_fill_upgrades_to_filled(self, monkeypatch):
        """해외선물(HKEX 모의 포함)도 CIDBQ02400 재조회로 체결 확정된다."""
        ex = self._executor()

        async def fake_query(ls, order_id, context, node_id):
            return 1, 24680.0

        monkeypatch.setattr(ex, "_query_overseas_futures_fill", fake_query)
        order_result = self._submitted(symbol="HSIF26", order_id="F1")
        await ex._confirm_order_fill(
            MagicMock(), "overseas_futures", "market", order_result,
            {"fill_confirm_delay_seconds": 0}, _mock_ctx(), "ord1",
        )
        inner = order_result["order_result"]
        assert inner["status"] == "filled"
        assert inner["filled_count"] == 1
        assert inner["fill_price"] == 24680.0

    @pytest.mark.asyncio
    async def test_unknown_product_stays_submitted(self):
        """알 수 없는 상품은 재조회하지 않고 접수 상태 그대로."""
        ex = self._executor()
        order_result = self._submitted(symbol="???", order_id="Z1")
        await ex._confirm_order_fill(
            MagicMock(), "mystery_product", "market", order_result,
            {"fill_confirm_delay_seconds": 0}, _mock_ctx(), "ord1",
        )
        assert order_result["order_result"]["status"] == "submitted"

    @pytest.mark.asyncio
    async def test_query_overseas_futures_fill_sums_execqty(self):
        """CIDBQ02400 block2 에서 내 주문번호 행들의 ExecQty 를 합산한다(부분체결 다행)."""
        ex = self._executor()
        r1 = MagicMock(OvrsFutsOrdNo="F1", ExecQty=1, AbrdFutsExecPrc=24680.0)
        r2 = MagicMock(OvrsFutsOrdNo="F1", ExecQty=2, AbrdFutsExecPrc=24690.0)
        r_other = MagicMock(OvrsFutsOrdNo="F9", ExecQty=99, AbrdFutsExecPrc=1.0)
        resp = MagicMock(error_msg=None, block2=[r1, r_other, r2])
        req = MagicMock()
        req.req_async = AsyncMock(return_value=resp)
        ls = MagicMock()
        ls.overseas_futureoption.return_value.accno.return_value.CIDBQ02400.return_value = req

        filled, price = await ex._query_overseas_futures_fill(ls, "F1", _mock_ctx(), "ord1")
        assert filled == 3  # 1 + 2, F9 제외
        # 가중평균: (1*24680 + 2*24690) / 3
        assert abs(price - (1 * 24680.0 + 2 * 24690.0) / 3) < 1e-6

    @pytest.mark.asyncio
    async def test_query_korea_fill_matches_order_in_t0425(self):
        """t0425 응답에서 내 주문번호 행만 골라 체결수량/가격을 읽는다."""
        ex = self._executor()
        row_match = MagicMock(ordno=9972, cheqty=1, cheprice=5270)
        row_other = MagicMock(ordno=1234, cheqty=99, cheprice=1)
        resp = MagicMock(error_msg=None, block=[row_other, row_match])
        req = MagicMock()
        req.req_async = AsyncMock(return_value=resp)
        ls = MagicMock()
        ls.korea_stock.return_value.accno.return_value.t0425.return_value = req

        filled, price = await ex._query_korea_fill(ls, "9972", "028670", _mock_ctx(), "ord1")
        assert filled == 1
        assert price == 5270.0

    @pytest.mark.asyncio
    async def test_query_korea_fill_returns_zero_when_order_absent(self):
        ex = self._executor()
        resp = MagicMock(error_msg=None, block=[MagicMock(ordno=1234, cheqty=5, cheprice=10)])
        req = MagicMock()
        req.req_async = AsyncMock(return_value=resp)
        ls = MagicMock()
        ls.korea_stock.return_value.accno.return_value.t0425.return_value = req

        filled, price = await ex._query_korea_fill(ls, "9972", "028670", _mock_ctx(), "ord1")
        assert filled == 0
        assert price == 0.0
