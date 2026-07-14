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

import pytest

from programgarden_core import EmptyOrderReason
from programgarden.executor import _order_failure_from_outputs


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
