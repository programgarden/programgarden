"""
공용 수량 헬퍼(``plugins/_position_qty.py``) 계약 테스트 + 상태 경로 실상 고정(pin).

이 파일은 두 가지를 한다:
1. 절단(``int()``)·바닥올림(``max(1, ...)``) 없는 수량 계산 계약을 고정한다.
   같은 식이 여러 플러그인에 복사돼 있던 것을 한 곳으로 모았으므로, 계약도
   한 곳에서 잠근다.
2. risk_tracker 상태/이벤트 경로가 **실제로는 동작하지 않는다**는 사실을
   테스트로 못 박는다(아래 ``TestRiskTrackerInterfaceTruth``). 지금 초록인 것은
   '고쳐졌다'는 뜻이 아니라 '아직 깨진 채다'라는 뜻이다 — 엔진 쪽에서 메서드명을
   맞추면 이 테스트가 빨개지고, 그때 플러그인 docstring 의 '미검증' 문구와 목을
   함께 고치면 된다.
"""

from decimal import Decimal

import pytest

from programgarden_community.plugins._position_qty import (
    below_broker_lot,
    coerce_qty,
    half_position_qty,
    partial_sell_qty,
    preserve_qty,
)


class TestCoerceQty:
    @pytest.mark.parametrize("raw,expected", [
        (0.532, 0.532), (1, 1.0), (10, 10.0), ("2.5", 2.5),
        (Decimal("0.532"), 0.532), (0, 0.0), (-3, -3.0),
    ])
    def test_reads_finite_values(self, raw, expected):
        assert coerce_qty(raw) == pytest.approx(expected)

    @pytest.mark.parametrize("raw", [None, "n/a", "", object(), float("nan"),
                                     float("inf"), Decimal("NaN")])
    def test_unreadable_is_none_not_zero(self, raw):
        """'못 읽음' 과 '0' 은 다른 사건이다 — 0 으로 뭉개지 않는다."""
        assert coerce_qty(raw) is None


class TestPreserveQty:
    @pytest.mark.parametrize("raw,expected,typ", [
        (0.532, 0.532, float), (1, 1, int), (10.0, 10, int),
        (Decimal("0.847972"), 0.847972, float), (Decimal("3"), 3, int),
    ])
    def test_integers_stay_int_fractions_stay_float(self, raw, expected, typ):
        out = preserve_qty(raw)
        assert out == pytest.approx(expected)
        assert isinstance(out, typ)


class TestHalfPositionQty:
    @pytest.mark.parametrize("qty,expected", [
        (0.532, 0.266),   # 구: max(1, int(0.532)//2) = 1 → 보유 초과 매도
        (1, 0.5),         # 구: max(1, 1//2) = 1 → '절반 축소'가 전량 매도
        (10, 5),
        (3, 1.5),         # 구: 3//2 = 1 (0.5주 증발)
        (Decimal("0.532"), 0.266),
    ])
    def test_exact_half_no_truncation_no_floor(self, qty, expected):
        assert half_position_qty(qty) == pytest.approx(expected)

    @pytest.mark.parametrize("qty", [0.532, 1, 10, 3, 0.001])
    def test_never_exceeds_held(self, qty):
        assert half_position_qty(qty) <= qty

    @pytest.mark.parametrize("qty", [0, -1, None, "n/a", float("nan")])
    def test_unusable_quantity_is_none(self, qty):
        """수량을 못 읽거나 0 이하면 수량을 지어내지 않는다(호출부가 사유를 남긴다)."""
        assert half_position_qty(qty) is None

    def test_integer_half_is_int(self):
        assert isinstance(half_position_qty(10), int)


class TestPartialSellQty:
    @pytest.mark.parametrize("base,pct,held,expected", [
        (0.532, 50, 0.532, 0.266),   # 구: int(0.266) = 0 → 단계 통째로 스킵
        (100, 30, 100, 30),
        (100, 30, 5, 5),             # 보유량 상한
        (Decimal("10"), 30, 5, 3),
    ])
    def test_percentage_of_base_capped_at_held(self, base, pct, held, expected):
        assert partial_sell_qty(base, pct, held) == pytest.approx(expected)

    def test_zero_percent_is_zero_not_none(self):
        """진짜 0 은 0 으로 돌려준다 — '못 읽음'(None)과 구분."""
        assert partial_sell_qty(100, 0, 100) == 0

    @pytest.mark.parametrize("args", [
        ("n/a", 50, 100), (100, "n/a", 100), (100, 50, None),
    ])
    def test_unreadable_is_none(self, args):
        assert partial_sell_qty(*args) is None


@pytest.fixture(scope="module")
def tracker_cls():
    # community 패키지는 엔진(programgarden)에 의존하지 않는다 —
    # 엔진 없이 설치된 환경에서는 이 pin 을 건너뛴다.
    mod = pytest.importorskip(
        "programgarden.database.workflow_risk_tracker",
        reason="engine package not installed; interface pin skipped",
    )
    return mod.WorkflowRiskTracker


class TestRiskTrackerInterfaceTruth:
    """플러그인이 부르는 이름과 실제 트래커의 이름이 **어긋나 있다**는 사실을 고정한다.

    관측 2026-09-12 (실제 클래스 introspection).
    엔진 쪽에서 이름을 맞추는 수정은 이번 회차 범위 밖 — 후속 필요.
    """

    @pytest.mark.parametrize("name", ["get_state", "set_state", "record_event"])
    def test_names_the_plugins_call_do_not_exist(self, tracker_cls, name):
        """플러그인들이 호출하는 이름이 실제 클래스에 없다 → 상태/이벤트 경로는 죽어 있다."""
        assert not hasattr(tracker_cls, name), (
            f"{name} 이 생겼다면 엔진이 고쳐진 것이다 — 플러그인 docstring 의 "
            "'미검증/동작하지 않음' 문구와 MockRiskTracker 를 함께 갱신할 것."
        )

    @pytest.mark.parametrize("name", ["load_state", "save_state", "delete_state",
                                      "record_risk_event"])
    def test_real_names_are_these(self, tracker_cls, name):
        assert hasattr(tracker_cls, name)

    def test_real_state_methods_are_synchronous(self, tracker_cls):
        """플러그인은 ``await delete_state(...)`` 하지만 실제 메서드는 동기다."""
        import inspect
        for name in ("save_state", "load_state", "delete_state"):
            assert not inspect.iscoroutinefunction(getattr(tracker_cls, name)), name


class TestBelowBrokerLot:
    """0 < 수량 < 1 판정 — 주문 송신부가 정수부 0 으로 접어 주문을 만들지 않는 구간.

    근거는 추정이 아니라 엔진 송신부 직접 호출 실측이다(2026-09-12):
    ``NewOrderNodeExecutor._normalize_order`` 에 quantity 0.5 / 0.999 를 주면
    ``None`` 을 돌려 주문을 만들지 않고, 1.0 은 quantity 1, 1.5 는 quantity 1 +
    fractional_remainder 0.5 를 돌려준다. 아래 ``TestOrderSenderContract`` 가
    그 사실을 직접 고정한다.
    """

    @pytest.mark.parametrize("raw", [0.5, 0.266, 0.999, 0.001, Decimal("0.532"), "0.75"])
    def test_true_below_one_share(self, raw):
        assert below_broker_lot(raw) is True

    @pytest.mark.parametrize("raw", [1, 1.0, 1.5, 10, Decimal("1"), "2"])
    def test_false_at_or_above_one_share(self, raw):
        assert below_broker_lot(raw) is False

    @pytest.mark.parametrize("raw", [0, 0.0, -0.5, -3])
    def test_false_for_zero_and_negative(self, raw):
        """0 과 음수는 이 판정의 대상이 아니다(호출부가 앞서 걸러낸다)."""
        assert below_broker_lot(raw) is False

    @pytest.mark.parametrize("raw", [None, "n/a", "", float("nan")])
    def test_false_for_unreadable(self, raw):
        """'못 읽음' 은 별개의 사건 — 호출부가 다른 사유로 따로 보고한다."""
        assert below_broker_lot(raw) is False

    def test_it_only_judges_and_never_changes_the_quantity(self):
        """판정 함수다 — 수량을 올리거나 자르지 않는다(반환형은 bool)."""
        assert isinstance(below_broker_lot(0.5), bool)
        assert half_position_qty(1) == 0.5  # 판정과 무관하게 절반은 그대로 0.5


class TestOrderSenderContract:
    """Z4 전제의 라이브 고정 — 송신부가 1주 미만을 주문으로 만들지 않는다."""

    def test_normalize_order_drops_sub_one_share(self):
        executor_mod = pytest.importorskip(
            "programgarden.executor",
            reason="engine package not installed; live-truth pin skipped",
        )
        ex = executor_mod.NewOrderNodeExecutor()

        def norm(q):
            return ex._normalize_order(
                {"symbol": "AAPL", "exchange": "NASDAQ", "quantity": q, "price": 10.0}, {}
            )

        for q in (0.5, 0.266, 0.999):
            assert norm(q) is None, f"{q} 주 주문이 만들어졌다 — below_broker_lot 전제가 바뀌었다"
            assert below_broker_lot(q) is True
        for q in (1.0, 1.5, 10):
            assert norm(q) is not None
            assert below_broker_lot(q) is False
