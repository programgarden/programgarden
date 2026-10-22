"""
DrawdownProtection (낙폭 보호) 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.drawdown_protection import (
    drawdown_protection_condition,
    DRAWDOWN_PROTECTION_SCHEMA,
    risk_features,
)


class MockHWM:
    def __init__(self, hwm_price, current_price, position_avg_price, drawdown_pct):
        self.hwm_price = hwm_price
        self.current_price = current_price
        self.position_avg_price = position_avg_price
        self.drawdown_pct = drawdown_pct


class MockRiskTracker:
    def __init__(self, hwm_data=None):
        self._hwm_data = hwm_data or {}

    def get_hwm(self, symbol):
        return self._hwm_data.get(symbol)


class MockContext:
    def __init__(self, risk_tracker=None):
        self.risk_tracker = risk_tracker


class TestDrawdownProtectionPlugin:
    """DrawdownProtection 플러그인 테스트"""

    @pytest.fixture
    def positions_normal(self):
        return [
            {"symbol": "AAPL", "pnl_rate": 5.0, "current_price": 157.5, "qty": 10, "market_code": "82"},
            {"symbol": "MSFT", "pnl_rate": -2.0, "current_price": 392.0, "qty": 5, "market_code": "82"},
        ]

    @pytest.fixture
    def positions_drawdown(self):
        return [
            {"symbol": "AAPL", "pnl_rate": -12.5, "current_price": 131.25, "qty": 10, "market_code": "82"},
            {"symbol": "MSFT", "pnl_rate": -15.0, "current_price": 340.0, "qty": 5, "market_code": "82"},
        ]

    # === 스키마 테스트 ===
    def test_schema_id(self):
        assert DRAWDOWN_PROTECTION_SCHEMA.id == "DrawdownProtection"

    def test_schema_category(self):
        assert DRAWDOWN_PROTECTION_SCHEMA.category == "position"

    def test_risk_features(self):
        assert "hwm" in risk_features
        assert "events" in risk_features

    # === 조건 평가 테스트 ===
    @pytest.mark.asyncio
    async def test_no_drawdown(self, positions_normal):
        result = await drawdown_protection_condition(
            positions=positions_normal,
            fields={"max_drawdown_pct": -10.0, "action": "exit_all"},
        )
        assert result["result"] is False
        assert len(result["passed_symbols"]) == 0

    @pytest.mark.asyncio
    async def test_drawdown_triggered(self, positions_drawdown):
        result = await drawdown_protection_condition(
            positions=positions_drawdown,
            fields={"max_drawdown_pct": -10.0, "action": "exit_all"},
        )
        assert result["result"] is True
        assert len(result["passed_symbols"]) == 2

    @pytest.mark.asyncio
    async def test_reduce_half_action(self, positions_drawdown):
        result = await drawdown_protection_condition(
            positions=positions_drawdown,
            fields={"max_drawdown_pct": -10.0, "action": "reduce_half"},
        )
        for sym in result["passed_symbols"]:
            assert "sell_quantity" in sym

    @pytest.mark.asyncio
    async def test_partial_trigger(self):
        positions = [
            {"symbol": "AAPL", "pnl_rate": -5.0, "current_price": 142.5, "qty": 10, "market_code": "82"},
            {"symbol": "MSFT", "pnl_rate": -15.0, "current_price": 340.0, "qty": 5, "market_code": "82"},
        ]
        result = await drawdown_protection_condition(
            positions=positions,
            fields={"max_drawdown_pct": -10.0},
        )
        assert len(result["passed_symbols"]) == 1
        assert result["passed_symbols"][0]["symbol"] == "MSFT"

    @pytest.mark.asyncio
    async def test_empty_positions(self):
        result = await drawdown_protection_condition(positions=[], fields={})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_with_risk_tracker(self, positions_normal):
        tracker = MockRiskTracker(hwm_data={
            "AAPL": MockHWM(hwm_price=170, current_price=157.5, position_avg_price=150, drawdown_pct=12.0),
            "MSFT": MockHWM(hwm_price=400, current_price=392, position_avg_price=380, drawdown_pct=2.0),
        })
        context = MockContext(risk_tracker=tracker)
        result = await drawdown_protection_condition(
            positions=positions_normal,
            fields={"max_drawdown_pct": -10.0},
            context=context,
        )
        # AAPL: HWM drawdown = -12% → triggered
        # MSFT: HWM drawdown = -2% → not triggered
        assert len(result["passed_symbols"]) == 1
        assert result["passed_symbols"][0]["symbol"] == "AAPL"

    @pytest.mark.asyncio
    async def test_analysis_output(self, positions_drawdown):
        result = await drawdown_protection_condition(
            positions=positions_drawdown,
            fields={"max_drawdown_pct": -10.0, "action": "exit_all"},
        )
        assert result["analysis"]["indicator"] == "DrawdownProtection"
        assert result["analysis"]["triggered_count"] == 2

    @pytest.mark.asyncio
    async def test_symbol_results_detail(self, positions_drawdown):
        result = await drawdown_protection_condition(
            positions=positions_drawdown,
            fields={"max_drawdown_pct": -10.0},
        )
        for sr in result["symbol_results"]:
            assert "drawdown" in sr
            assert "triggered" in sr
            assert "action" in sr

    @pytest.mark.asyncio
    async def test_exchange_name_mapping(self, positions_normal):
        result = await drawdown_protection_condition(
            positions=positions_normal,
            fields={},
        )
        for sr in result["symbol_results"]:
            assert sr["exchange"] == "NASDAQ"  # market_code "82" → NASDAQ


class TestReduceHalfQuantity:
    """'reduce_half'(절반 축소)가 보유량을 넘지 않고 소수 잔량도 보존해야 한다.

    구 코드는 ``max(1, int(qty) // 2)`` 였다:
    - 0.532주 보유 → ``int(0.532)//2 = 0`` → ``max(1,0) = 1`` → **보유 0.532 인데 1주 매도**
    - 1주 보유 → 같은 경로로 1 → '절반 축소'가 사실상 전량 매도
    LS 는 해외주식 소수점 주식을 지원한다(출처: 오너 진술 2026-09-12).
    정수화는 주문 송신부(_normalize_order)의 규약이므로 플러그인은 자르지 않는다.
    """

    @staticmethod
    async def _run(qty):
        return await drawdown_protection_condition(
            positions=[{
                "symbol": "AAPL", "pnl_rate": -15.0, "current_price": 131.25,
                "qty": qty, "market_code": "82",
            }],
            fields={"max_drawdown_pct": -10.0, "action": "reduce_half"},
        )

    @pytest.mark.asyncio
    async def test_fractional_position_does_not_oversell(self):
        result = await self._run(0.532)
        sym = result["passed_symbols"][0]
        assert sym["sell_quantity"] == pytest.approx(0.266)  # 구 코드는 1 (보유 초과)
        assert sym["sell_quantity"] <= 0.532

    @pytest.mark.asyncio
    async def test_decimal_fractional_position(self):
        from decimal import Decimal

        result = await self._run(Decimal("0.532"))
        assert result["passed_symbols"][0]["sell_quantity"] == pytest.approx(0.266)

    @pytest.mark.asyncio
    async def test_single_share_sells_half_not_all(self):
        result = await self._run(1)
        sym = result["passed_symbols"][0]
        assert sym["sell_quantity"] == pytest.approx(0.5)  # 구 코드는 1 (전량)
        assert sym["sell_quantity"] < 1

    @pytest.mark.asyncio
    async def test_integer_position_halves_as_int(self):
        result = await self._run(10)
        sym = result["passed_symbols"][0]
        assert sym["sell_quantity"] == 5
        assert isinstance(sym["sell_quantity"], int)  # 직렬화 모양 유지

    @pytest.mark.asyncio
    async def test_odd_integer_position_keeps_remainder(self):
        """홀수 보유(9)는 4.5 — 바닥/올림 모두 하지 않는다(하류가 정수부만 주문)."""
        result = await self._run(9)
        assert result["passed_symbols"][0]["sell_quantity"] == pytest.approx(4.5)

    @pytest.mark.asyncio
    async def test_unreadable_quantity_emits_reason_not_a_guess(self):
        """수량을 읽을 수 없으면 수량을 지어내지 않고 사유를 남긴다."""
        result = await self._run("abc")
        sym = result["passed_symbols"][0]
        assert "sell_quantity" not in sym
        sr = result["symbol_results"][0]
        assert "sell_quantity_unavailable_reason" in sr
        assert "abc" in sr["sell_quantity_unavailable_reason"]

    @pytest.mark.asyncio
    async def test_zero_quantity_emits_reason(self):
        result = await self._run(0)
        assert "sell_quantity" not in result["passed_symbols"][0]
        assert "sell_quantity_unavailable_reason" in result["symbol_results"][0]

    @pytest.mark.asyncio
    async def test_quantity_key_alias_is_read(self):
        """'qty' 가 없고 'quantity' 만 있는 포지션도 절반 계산이 된다."""
        result = await drawdown_protection_condition(
            positions=[{
                "symbol": "AAPL", "pnl_rate": -15.0, "current_price": 131.25,
                "quantity": 7, "market_code": "82",
            }],
            fields={"max_drawdown_pct": -10.0, "action": "reduce_half"},
        )
        assert result["passed_symbols"][0]["sell_quantity"] == pytest.approx(3.5)

    @pytest.mark.asyncio
    async def test_other_actions_do_not_carry_sell_quantity(self):
        """exit_all 은 종전대로 sell_quantity 를 싣지 않는다(회귀 방지)."""
        result = await drawdown_protection_condition(
            positions=[{
                "symbol": "AAPL", "pnl_rate": -15.0, "current_price": 131.25,
                "qty": 10, "market_code": "82",
            }],
            fields={"max_drawdown_pct": -10.0, "action": "exit_all"},
        )
        assert "sell_quantity" not in result["passed_symbols"][0]


class TestReduceHalfBelowOneShareIsNotSilent:
    """Z4 — 절반 축소 수량이 1주 미만이면 **주문이 만들어지지 않는다**는 사실을 드러낸다.

    주문 송신부 ``NewOrderNodeExecutor._normalize_order`` 는 ``int(raw_quantity)``
    로 정수부만 주문하고, 정수부가 0 이면 ``None`` 을 돌려 주문을 만들지 않는다.
    라이브 실측(executor 직접 호출, 2026-09-12):
    quantity 0.5 → None, 0.999 → None, 1.0 → quantity 1,
    1.5 → quantity 1 + fractional_remainder 0.5.

    따라서 1주 보유에서 reduce_half(=0.5주)는 **아무 일도 일어나지 않는다**.
    이번 수정은 동작을 바꾸지 않는다(수량은 그대로 0.5) — 그 무동작이
    ``reduce_skipped_reason`` 으로 드러나게만 한다. 정책(현행 유지 / 전량 청산
    승격 / 알림)은 오너 판단 사항이다.
    """

    @staticmethod
    async def _run(qty):
        return await drawdown_protection_condition(
            positions=[{
                "symbol": "AAPL", "pnl_rate": -15.0, "current_price": 131.25,
                "qty": qty, "market_code": "82",
            }],
            fields={"max_drawdown_pct": -10.0, "action": "reduce_half"},
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("qty,half", [(1, 0.5), (0.532, 0.266), (1.9, 0.95)])
    async def test_sub_one_share_half_leaves_reason(self, qty, half):
        result = await self._run(qty)
        sr = result["symbol_results"][0]
        assert sr["sell_quantity"] == pytest.approx(half), "수량을 올리거나 자르지 않는다"
        assert result["passed_symbols"][0]["sell_quantity"] == pytest.approx(half)
        assert "1주 미만" in sr["reduce_skipped_reason"]
        assert repr(qty) in sr["reduce_skipped_reason"]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("qty", [2, 10, 3.5])
    async def test_one_share_or_more_has_no_reason(self, qty):
        result = await self._run(qty)
        sr = result["symbol_results"][0]
        assert sr["sell_quantity"] >= 1
        assert "reduce_skipped_reason" not in sr

    @pytest.mark.asyncio
    async def test_unreadable_quantity_is_a_different_event(self):
        """'못 읽음' 은 축소 무동작과 다른 사건 — 사유 키가 갈린다."""
        result = await self._run("n/a")
        sr = result["symbol_results"][0]
        assert "sell_quantity_unavailable_reason" in sr
        assert "reduce_skipped_reason" not in sr
        assert "sell_quantity" not in sr

    @pytest.mark.asyncio
    async def test_exit_all_action_is_untouched(self):
        """reduce_half 전용 사유다 — 다른 action 에는 붙지 않는다."""
        result = await drawdown_protection_condition(
            positions=[{
                "symbol": "AAPL", "pnl_rate": -15.0, "current_price": 131.25,
                "qty": 1, "market_code": "82",
            }],
            fields={"max_drawdown_pct": -10.0, "action": "exit_all"},
        )
        sr = result["symbol_results"][0]
        assert "reduce_skipped_reason" not in sr

    def test_schema_declares_the_reason(self):
        assert "reduce_skipped_reason" in DRAWDOWN_PROTECTION_SCHEMA.output_fields


class TestOrderSenderTruncationIsReal:
    """Z4 전제의 라이브 고정 — 0 < 수량 < 1 이면 주문이 만들어지지 않는다.

    이 사실은 추정이 아니라 엔진 송신부를 직접 호출해 확인한 것이다. 엔진이
    설치되지 않은 환경에서는 skip 된다.
    """

    def test_normalize_order_builds_nothing_below_one_share(self):
        executor_mod = pytest.importorskip(
            "programgarden.executor",
            reason="engine package not installed; live-truth pin skipped",
        )
        ex = executor_mod.NewOrderNodeExecutor()

        def norm(q):
            return ex._normalize_order(
                {"symbol": "AAPL", "exchange": "NASDAQ", "quantity": q, "price": 10.0}, {}
            )

        assert norm(0.5) is None, "0.5주 주문이 만들어졌다 — Z4 전제가 바뀌었다"
        assert norm(0.999) is None
        assert norm(1.0)["quantity"] == 1
        floored = norm(1.5)
        assert floored["quantity"] == 1
        assert floored["fractional_remainder"] == pytest.approx(0.5)
