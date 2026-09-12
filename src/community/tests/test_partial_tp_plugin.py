"""
PartialTakeProfit 플러그인 테스트

🔴 이 파일의 ``MockRiskTracker`` 는 **실제 클래스에 없는 메서드를 제공한다** (관측 2026-09-12)
------------------------------------------------------------------------------------------
실제 트래커 ``programgarden.database.workflow_risk_tracker.WorkflowRiskTracker`` 의
실제 인터페이스와 대조한 결과:

| 목이 제공하는 이름 | 실제 클래스 | 비고 |
|---|---|---|
| ``get_state``   | **없음** | 실제 이름은 ``load_state`` (동기) |
| ``set_state``   | **없음** | 실제 이름은 ``save_state`` (동기) |
| ``delete_state``| 있음     | 단 **동기** 메서드 — 플러그인은 ``await`` 한다 |
| ``record_event``| **없음** | 실제 이름은 ``record_risk_event`` |

즉 아래 상태 관련 테스트들은 '플러그인이 라이브에서 실제로 상태를 저장·복원한다'
를 증명하지 않는다 — **목이 약속한 계약대로 플러그인이 호출한다**는 것만 증명한다.
라이브에서는 (가) 실제 트래커를 넘기면 ``AttributeError`` 로 죽고, (나) 애초에
실행기가 positions 기반 플러그인에 ``context`` 를 넘기지 않아 상태 경로가 아예
돌지 않는다(플러그인 모듈 docstring 의 '상태 경로' 절 참조).
목을 실제 시그니처로 맞추는 수정은 이번 회차 범위 밖이다 — 후속 필요.
"""

import pytest
from programgarden_community.plugins.partial_take_profit import (
    partial_take_profit_condition,
    PARTIAL_TAKE_PROFIT_SCHEMA,
)


class MockRiskTracker:
    """strategy_state **목 계약** 모킹 — 실제 WorkflowRiskTracker 인터페이스가 아니다.

    ``get_state``/``set_state`` 는 실제 클래스에 없는 이름이고(실제: ``load_state``/
    ``save_state``, 둘 다 동기), ``delete_state`` 는 이름은 같지만 실제로는 동기
    메서드다. 파일 상단 주석 참조.
    """
    def __init__(self):
        self._state = {}

    async def get_state(self, key):
        return self._state.get(key)

    async def set_state(self, key, value):
        self._state[key] = value

    async def delete_state(self, key):
        self._state.pop(key, None)


class MockContext:
    def __init__(self, risk_tracker=None):
        self.risk_tracker = risk_tracker


class TestPartialTakeProfitPlugin:

    @pytest.mark.asyncio
    async def test_level_triggered(self):
        """1단계 익절 트리거 (context 경로는 목 계약 — 라이브에서는 context 가 오지 않는다)"""
        tracker = MockRiskTracker()
        context = MockContext(tracker)

        positions = [
            {"symbol": "AAPL", "pnl_rate": 6.0, "qty": 100, "market_code": "82"},
        ]
        result = await partial_take_profit_condition(
            positions=positions,
            fields={"levels": [{"pnl_pct": 5, "sell_pct": 50}, {"pnl_pct": 10, "sell_pct": 30}]},
            context=context,
        )
        assert result["result"] is True
        assert len(result["passed_symbols"]) == 1
        sr = result["symbol_results"][0]
        assert sr["sell_quantity"] == 50  # 100 * 50%
        assert sr["level_index"] == 0
        assert sr["remaining_levels"] == 1

    @pytest.mark.asyncio
    async def test_no_level_triggered(self):
        """수익률 부족으로 미트리거"""
        positions = [
            {"symbol": "AAPL", "pnl_rate": 3.0, "qty": 100, "market_code": "82"},
        ]
        result = await partial_take_profit_condition(
            positions=positions,
            fields={"levels": [{"pnl_pct": 5, "sell_pct": 50}]},
        )
        assert result["result"] is False
        assert len(result["failed_symbols"]) == 1

    @pytest.mark.asyncio
    async def test_completed_level_skip(self):
        """[목 계약 — 라이브 아님] 완료된 단계 건너뛰기 — 목이 복원해 준 completed_levels 를 플러그인이 읽는지만 본다"""
        tracker = MockRiskTracker()
        tracker._state["partial_tp.AAPL.completed_levels"] = [0]
        tracker._state["partial_tp.AAPL.original_qty"] = 100
        context = MockContext(tracker)

        positions = [
            {"symbol": "AAPL", "pnl_rate": 6.0, "qty": 50, "market_code": "82"},
        ]
        result = await partial_take_profit_condition(
            positions=positions,
            fields={"levels": [{"pnl_pct": 5, "sell_pct": 50}, {"pnl_pct": 10, "sell_pct": 30}]},
            context=context,
        )
        # 1단계(idx=0) 완료됨, pnl 6% < 10% (2단계) → 미트리거
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_second_level_triggered(self):
        """[목 계약 — 라이브 아님] 2단계 익절 트리거 (1단계 완료 상태) — 상태 복원은 목이 해 준 것이다"""
        tracker = MockRiskTracker()
        tracker._state["partial_tp.AAPL.completed_levels"] = [0]
        tracker._state["partial_tp.AAPL.original_qty"] = 100
        context = MockContext(tracker)

        positions = [
            {"symbol": "AAPL", "pnl_rate": 12.0, "qty": 50, "market_code": "82"},
        ]
        result = await partial_take_profit_condition(
            positions=positions,
            fields={"levels": [{"pnl_pct": 5, "sell_pct": 50}, {"pnl_pct": 10, "sell_pct": 30}]},
            context=context,
        )
        assert result["result"] is True
        sr = result["symbol_results"][0]
        assert sr["level_index"] == 1
        assert sr["sell_quantity"] == 30  # original_qty(100) * 30%

    @pytest.mark.asyncio
    async def test_position_closed_clears_state(self):
        """[목 계약 — 라이브 아님] 포지션 청산 시 상태 삭제 — 실제 delete_state 는 동기라 await 하면 라이브에서 죽는다"""
        tracker = MockRiskTracker()
        tracker._state["partial_tp.AAPL.completed_levels"] = [0]
        tracker._state["partial_tp.AAPL.original_qty"] = 100
        context = MockContext(tracker)

        positions = [
            {"symbol": "AAPL", "pnl_rate": 0, "qty": 0, "market_code": "82"},
        ]
        await partial_take_profit_condition(positions=positions, fields={}, context=context)
        assert "partial_tp.AAPL.completed_levels" not in tracker._state
        assert "partial_tp.AAPL.original_qty" not in tracker._state

    @pytest.mark.asyncio
    async def test_without_context(self):
        """context 없이 실행 — **이것이 현재 라이브 실행기의 실제 모습이다**

        실행기의 positions 분기가 context 를 넘기지 않으므로 라이브는 항상 이
        경로다. 매 호출이 level_index=0 을 다시 트리거한다(상태 없음).
        """
        positions = [
            {"symbol": "AAPL", "pnl_rate": 8.0, "qty": 100, "market_code": "82"},
        ]
        result = await partial_take_profit_condition(
            positions=positions,
            fields={"levels": [{"pnl_pct": 5, "sell_pct": 50}]},
        )
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_empty_positions(self):
        """빈 포지션"""
        result = await partial_take_profit_condition(positions=[], fields={})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_levels_json_string(self):
        """levels를 JSON 문자열로 전달"""
        positions = [{"symbol": "AAPL", "pnl_rate": 6.0, "qty": 100, "market_code": "82"}]
        result = await partial_take_profit_condition(
            positions=positions,
            fields={"levels": '[{"pnl_pct": 5, "sell_pct": 50}]'},
        )
        assert "passed_symbols" in result
        assert "analysis" in result

    def test_schema(self):
        assert PARTIAL_TAKE_PROFIT_SCHEMA.id == "PartialTakeProfit"
        cat = PARTIAL_TAKE_PROFIT_SCHEMA.category
        assert (cat.value if hasattr(cat, 'value') else cat) == "position"
        assert "levels" in PARTIAL_TAKE_PROFIT_SCHEMA.fields_schema


class TestSellQuantityWiring:
    """E3: passed_symbols 에 부분 청산 수량(quantity)/방향(close_side) 탑재"""

    @pytest.mark.asyncio
    async def test_passed_symbol_carries_partial_qty_and_close_side(self):
        positions = [
            {"symbol": "AAPL", "pnl_rate": 6.0, "qty": 100, "market_code": "82"},
        ]
        result = await partial_take_profit_condition(
            positions=positions,
            fields={"levels": [{"pnl_pct": 5, "sell_pct": 50}]},
        )
        ps = result["passed_symbols"][0]
        # 부분 익절이므로 passed_symbols.quantity = 계산된 sell_quantity (50)
        assert ps["quantity"] == 50
        assert ps["quantity"] == result["symbol_results"][0]["sell_quantity"]
        # 기본 청산 방향은 sell
        assert ps["close_side"] == "sell"

    @pytest.mark.asyncio
    async def test_close_side_from_position_for_futures_short(self):
        # 숏 선물 포지션은 close_side=buy 로 청산 — positions 가 실은 값을 그대로 전달
        positions = [
            {"symbol": "ESH26", "pnl_rate": 6.0, "quantity": 4,
             "exchange": "CME", "close_side": "buy"},
        ]
        result = await partial_take_profit_condition(
            positions=positions,
            fields={"levels": [{"pnl_pct": 5, "sell_pct": 50}]},
        )
        ps = result["passed_symbols"][0]
        assert ps["close_side"] == "buy"
        assert ps["quantity"] == 2  # 4 * 50%


class TestFractionalPartialQuantity:
    """소수 포지션의 부분 익절이 절단돼 사라지면 안 된다.

    구 코드는 ``int(original_qty * sell_pct / 100)`` 이라 0.532주 × 50% = 0.266 이
    0 으로 잘렸고, ``if sell_quantity > 0`` 게이트에 걸려 단계가 통째로
    건너뛰어졌다(상태도 갱신되지 않아 매 실행 반복). LS 는 해외주식 소수점 주식을
    지원한다(출처: 오너 진술 2026-09-12). 정수화는 주문 송신부
    (_normalize_order)의 명시적 규약이다 — 정수부만 주문하고 잔량은
    fractional_remainder 로, 정수부가 0 이면 FRACTIONAL_ONLY 로 사유를 남긴다.
    """

    @pytest.mark.asyncio
    async def test_fractional_position_is_not_skipped(self):
        positions = [
            {"symbol": "AAPL", "pnl_rate": 6.0, "qty": 0.532, "market_code": "82"},
        ]
        result = await partial_take_profit_condition(
            positions=positions,
            fields={"levels": [{"pnl_pct": 5, "sell_pct": 50}]},
        )
        assert result["result"] is True  # 구 코드는 False (조용한 스킵)
        ps = result["passed_symbols"][0]
        assert ps["quantity"] == pytest.approx(0.266)
        sr = result["symbol_results"][0]
        assert sr["action"] == "sell"
        assert sr["sell_quantity"] == pytest.approx(0.266)

    @pytest.mark.asyncio
    async def test_decimal_quantity_position(self):
        from decimal import Decimal

        positions = [
            {"symbol": "AAPL", "pnl_rate": 6.0, "qty": Decimal("0.532"), "market_code": "82"},
        ]
        result = await partial_take_profit_condition(
            positions=positions,
            fields={"levels": [{"pnl_pct": 5, "sell_pct": 50}]},
        )
        assert result["passed_symbols"][0]["quantity"] == pytest.approx(0.266)

    @pytest.mark.asyncio
    async def test_fractional_remainder_of_integer_position(self):
        """9주 × 30% = 2.7 — 2 로 자르지 않는다(잔량 판단은 주문 송신부 몫)."""
        positions = [
            {"symbol": "AAPL", "pnl_rate": 6.0, "qty": 9, "market_code": "82"},
        ]
        result = await partial_take_profit_condition(
            positions=positions,
            fields={"levels": [{"pnl_pct": 5, "sell_pct": 30}]},
        )
        assert result["passed_symbols"][0]["quantity"] == pytest.approx(2.7)

    @pytest.mark.asyncio
    async def test_integer_result_stays_int(self):
        """정수로 떨어지면 종전대로 int (직렬화 모양 유지)."""
        positions = [
            {"symbol": "AAPL", "pnl_rate": 6.0, "qty": 100, "market_code": "82"},
        ]
        result = await partial_take_profit_condition(
            positions=positions,
            fields={"levels": [{"pnl_pct": 5, "sell_pct": 50}]},
        )
        qty = result["passed_symbols"][0]["quantity"]
        assert qty == 50 and isinstance(qty, int)

    @pytest.mark.asyncio
    async def test_never_exceeds_held_quantity(self):
        """기준 수량이 보유량보다 커도 보유량 상한을 넘지 않는다(기존 가드 유지)."""
        tracker = MockRiskTracker()
        tracker._state["partial_tp.AAPL.original_qty"] = 100
        context = MockContext(tracker)
        positions = [
            {"symbol": "AAPL", "pnl_rate": 6.0, "qty": 3, "market_code": "82"},
        ]
        result = await partial_take_profit_condition(
            positions=positions,
            fields={"levels": [{"pnl_pct": 5, "sell_pct": 90}]},  # 100*90% = 90 > 보유 3
            context=context,
        )
        assert result["passed_symbols"][0]["quantity"] == 3

    @pytest.mark.asyncio
    async def test_decimal_original_qty_state_is_used(self):
        """[목 계약 — 라이브 아님] Decimal 로 저장된 기준 수량도 읽는다(구 isinstance(int,float) 는 놓쳤다).

        라이브에서는 get_state 가 아예 호출되지 않으므로(모듈 docstring 참조) 이
        분기는 목 위에서만 검증된다.
        """
        from decimal import Decimal

        tracker = MockRiskTracker()
        tracker._state["partial_tp.AAPL.original_qty"] = Decimal("10")
        tracker._state["partial_tp.AAPL.completed_levels"] = [0]
        context = MockContext(tracker)
        positions = [
            {"symbol": "AAPL", "pnl_rate": 11.0, "qty": 5, "market_code": "82"},
        ]
        result = await partial_take_profit_condition(
            positions=positions,
            fields={"levels": [{"pnl_pct": 5, "sell_pct": 50},
                               {"pnl_pct": 10, "sell_pct": 30}]},
            context=context,
        )
        # 기준 10 × 30% = 3 (현재 보유 5 기준이면 1.5 가 나온다)
        assert result["passed_symbols"][0]["quantity"] == 3

    @pytest.mark.asyncio
    async def test_zero_sell_pct_leaves_reason(self):
        """진짜 0 인 경우는 스킵하되 숫자가 담긴 사유를 남긴다."""
        positions = [
            {"symbol": "AAPL", "pnl_rate": 6.0, "qty": 10, "market_code": "82"},
        ]
        result = await partial_take_profit_condition(
            positions=positions,
            fields={"levels": [{"pnl_pct": 5, "sell_pct": 0}]},
        )
        sr = result["symbol_results"][0]
        assert sr["action"] == "skip"
        assert sr["sell_quantity"] == 0
        assert "0" in sr["reason"] and "10" in sr["reason"]

    @pytest.mark.asyncio
    async def test_unreadable_sell_pct_leaves_reason(self):
        """비율을 읽을 수 없으면 수량을 지어내지 않고 사유를 남긴다."""
        positions = [
            {"symbol": "AAPL", "pnl_rate": 6.0, "qty": 10, "market_code": "82"},
        ]
        result = await partial_take_profit_condition(
            positions=positions,
            fields={"levels": [{"pnl_pct": 5, "sell_pct": "절반"}]},
        )
        assert result["result"] is False
        sr = result["symbol_results"][0]
        assert sr["action"] == "skip"
        assert "읽을 수 없어" in sr["reason"]
        assert "sell_quantity" not in sr


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestLiveStatePathIsDead:
    """상태 경로가 라이브에서 죽어 있다는 **실제 동작**을 고정한다 (X4, 관측 2026-09-12).

    실행기의 positions 기반 분기(``ConditionNodeExecutor.execute``)는 plugin_kwargs
    를 ``{"positions", "fields"}`` 로 고정해 ``context`` 를 넘기지 않는다. 따라서
    라이브 호출은 항상 context=None 이고, 아래처럼 같은 단계가 매 사이클 재발동한다.

    이 테스트가 초록인 것은 '정상' 이라는 뜻이 아니라 '아직 깨진 채다' 라는 뜻이다.
    실행기가 context 를 넘기도록 고쳐지면 이 테스트가 빨개져야 하고, 그때 플러그인
    docstring 의 '미검증' 문구도 함께 걷어내면 된다. 근본 수정은 이번 회차 범위 밖.
    """

    @pytest.mark.asyncio
    async def test_same_level_retriggers_every_cycle_without_context(self):
        positions = [{"symbol": "AAPL", "pnl_rate": 6.0, "qty": 100, "market_code": "82"}]
        levels = [{"pnl_pct": 5, "sell_pct": 50}]

        seen = []
        for _ in range(3):
            result = await partial_take_profit_condition(
                positions=positions, fields={"levels": levels},
            )
            sr = result["symbol_results"][0]
            seen.append((sr["level_index"], sr["sell_quantity"]))

        assert seen == [(0, 50), (0, 50), (0, 50)], (
            "상태가 저장·복원되지 않아 매 사이클 같은 단계가 재발동한다. "
            f"관측: {seen}"
        )

    @pytest.mark.asyncio
    async def test_real_tracker_would_crash_on_the_state_path(self):
        """실제 트래커를 넘기면 상태 경로가 AttributeError 로 즉사한다."""
        mod = pytest.importorskip(
            "programgarden.database.workflow_risk_tracker",
            reason="engine package not installed; live-truth pin skipped",
        )
        import tempfile, os

        tracker = mod.WorkflowRiskTracker(
            db_path=os.path.join(tempfile.mkdtemp(), "rt.db"),
            job_id="pin", product="overseas_stock", provider="ls",
            trading_mode="real", features={"state"},
        )

        class RealCtx:
            risk_tracker = tracker

        with pytest.raises(AttributeError, match="get_state"):
            await partial_take_profit_condition(
                positions=[{"symbol": "AAPL", "pnl_rate": 6.0, "qty": 100, "market_code": "82"}],
                fields={"levels": [{"pnl_pct": 5, "sell_pct": 50}]},
                context=RealCtx(),
            )


class TestUnreadableQuantityIsReachable:
    """Z1 — '수량을 못 읽었다' 사유가 **실제로 도달 가능**해야 한다 (관측 2026-09-12).

    구 코드는 pos_data 원값을 그대로 ``if qty <= 0:`` 에 넣었다. 파이썬에서
    ``'n/a' <= 0`` · ``'100' <= 0`` · ``None <= 0`` 는 전부 TypeError 다(직접 실행
    확인) — 그래서 수량이 숫자가 아니면 이 플러그인은 그 줄에서 **통째로 죽었고**,
    아래 사유 분기는 수량에 대해 한 번도 도달할 수 없었다.
    """

    @staticmethod
    async def _run(qty):
        return await partial_take_profit_condition(
            positions=[{"symbol": "AAPL", "pnl_rate": 6.5, "qty": qty, "market_code": "82"}],
            fields={"levels": [{"pnl_pct": 5, "sell_pct": 50}]},
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("qty", ["n/a", None, "", float("nan")])
    async def test_unreadable_quantity_leaves_reason_instead_of_crashing(self, qty):
        result = await self._run(qty)  # 구 코드: TypeError
        sr = result["symbol_results"][0]
        assert sr["action"] == "skip"
        assert "보유 수량을 읽을 수 없어" in sr["reason"]
        assert repr(qty) in sr["reason"], "원값이 사유에 그대로 남아야 진단이 된다"
        assert "sell_quantity" not in sr
        assert result["passed_symbols"] == []
        assert result["failed_symbols"][0]["symbol"] == "AAPL"

    @pytest.mark.asyncio
    async def test_numeric_string_quantity_is_read_not_crashed(self):
        """'100' 은 읽을 수 있는 수량이다 — 구 코드는 여기서도 TypeError 로 죽었다."""
        result = await self._run("100")
        sr = result["symbol_results"][0]
        assert sr["action"] == "sell"
        assert sr["qty"] == 100
        assert sr["sell_quantity"] == 50

    @pytest.mark.asyncio
    async def test_readable_zero_is_still_cleared_not_skipped(self):
        """'0' 과 '못 읽음' 은 다른 사건이다 — 0 은 종전대로 청산 완료(cleared)."""
        result = await self._run(0)
        sr = result["symbol_results"][0]
        assert sr["action"] == "cleared"
        assert sr["reason"] == "Position closed"


class TestPartialSellBelowOneShareIsNotSilent:
    """Z4 — 1주 미만 부분 익절 수량은 주문이 만들어지지 않는다는 사실을 드러낸다.

    주문 송신부 ``NewOrderNodeExecutor._normalize_order`` 는 ``int(raw_quantity)``
    로 정수부만 주문하고 정수부가 0 이면 ``None`` 을 돌린다 — 라이브 실측:
    quantity 0.5 → None, 0.999 → None, 1.0 → quantity 1, 1.5 → quantity 1 +
    fractional_remainder 0.5 (executor 직접 호출, 2026-09-12).
    동작은 바꾸지 않는다(수량은 그대로) — 조용한 무동작만 드러낸다.
    """

    @staticmethod
    async def _run(qty, sell_pct=50):
        return await partial_take_profit_condition(
            positions=[{"symbol": "AAPL", "pnl_rate": 6.5, "qty": qty, "market_code": "82"}],
            fields={"levels": [{"pnl_pct": 5, "sell_pct": sell_pct}]},
        )

    @pytest.mark.asyncio
    async def test_sub_one_share_sell_leaves_reason(self):
        result = await self._run(0.532)  # 0.532 x 50% = 0.266 주
        sr = result["symbol_results"][0]
        assert sr["action"] == "sell"
        assert sr["sell_quantity"] == pytest.approx(0.266)  # 수량은 그대로 둔다
        assert "reduce_skipped_reason" in sr
        assert "1주 미만" in sr["reduce_skipped_reason"]

    @pytest.mark.asyncio
    async def test_one_share_or_more_has_no_reason(self):
        result = await self._run(10)  # 10 x 50% = 5 주
        sr = result["symbol_results"][0]
        assert sr["sell_quantity"] == 5
        assert "reduce_skipped_reason" not in sr

    @pytest.mark.asyncio
    async def test_schema_declares_the_reason(self):
        assert "reduce_skipped_reason" in PARTIAL_TAKE_PROFIT_SCHEMA.output_fields
