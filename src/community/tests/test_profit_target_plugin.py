"""
ProfitTarget (익절) 플러그인 테스트

E1: target_percent 부호 검증 (양수만 허용, 비양수는 명확한 에러로 거절)
E3: 청산 주문 수량(quantity)/청산 방향(close_side) 탑재
"""

import pytest

from programgarden_community.plugins.profit_target import (
    profit_target_condition,
    PROFIT_TARGET_SCHEMA,
)


# ── E1: target_percent 부호 검증 ──


class TestProfitTargetSignValidation:
    """양수만 허용 — 0 이하는 raise"""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("bad", [0, 0.0, -3.0, -3, -100.0])
    async def test_non_positive_raises(self, bad):
        """target_percent <= 0 이면 ValueError"""
        with pytest.raises(ValueError) as exc:
            await profit_target_condition(
                positions=[{"symbol": "AAPL", "pnl_rate": 6.0}],
                fields={"target_percent": bad},
            )
        msg = str(exc.value)
        assert "positive" in msg
        assert "StopLoss" in msg or "TrailingStop" in msg

    @pytest.mark.asyncio
    async def test_non_positive_raises_even_without_positions(self):
        """포지션이 없어도 config 오류(부호)는 즉시 raise (fail-fast)"""
        with pytest.raises(ValueError):
            await profit_target_condition(positions=[], fields={"target_percent": -5.0})

    @pytest.mark.asyncio
    async def test_non_numeric_raises(self):
        """숫자로 변환 불가한 target_percent 는 ValueError"""
        with pytest.raises(ValueError):
            await profit_target_condition(
                positions=[{"symbol": "AAPL", "pnl_rate": 6.0}],
                fields={"target_percent": "abc"},
            )

    @pytest.mark.asyncio
    async def test_valid_positive_string_coerced(self):
        """문자열 양수도 float 로 강제되어 정상 동작"""
        result = await profit_target_condition(
            positions=[{"symbol": "AAPL", "pnl_rate": 6.0, "quantity": 10}],
            fields={"target_percent": "5.0"},
        )
        assert result["result"] is True
        assert result["analysis"]["target_percent"] == 5.0

    @pytest.mark.asyncio
    async def test_valid_positive_triggers(self):
        """정상 양수 임계값 — 익절 발동"""
        result = await profit_target_condition(
            positions=[{"symbol": "AAPL", "pnl_rate": 6.3, "quantity": 10}],
            fields={"target_percent": 5.0},
        )
        assert result["result"] is True
        assert len(result["passed_symbols"]) == 1

    @pytest.mark.asyncio
    async def test_valid_positive_no_trigger(self):
        """정상 양수 임계값 — 미달"""
        result = await profit_target_condition(
            positions=[{"symbol": "AAPL", "pnl_rate": 2.0, "quantity": 10}],
            fields={"target_percent": 5.0},
        )
        assert result["result"] is False
        assert len(result["passed_symbols"]) == 0

    def test_schema_hint_positive(self):
        """fields_schema 에 양수 힌트(gt=0) 표현"""
        assert PROFIT_TARGET_SCHEMA.fields_schema["target_percent"]["gt"] == 0.0


# ── E3: 청산 수량/방향 탑재 ──


class TestSellQuantityWiring:
    """passed_symbols 가 {{ item.quantity }}/{{ item.close_side }} 를 공급"""

    @pytest.mark.asyncio
    async def test_passed_symbol_carries_quantity_and_close_side(self):
        result = await profit_target_condition(
            positions=[{"symbol": "AAPL", "pnl_rate": 6.0, "quantity": 12,
                        "close_side": "sell", "market_code": "82"}],
            fields={"target_percent": 5.0},
        )
        ps = result["passed_symbols"][0]
        assert ps["symbol"] == "AAPL"
        assert ps["exchange"] == "NASDAQ"
        assert ps["quantity"] == 12
        assert ps["close_side"] == "sell"

    @pytest.mark.asyncio
    async def test_quantity_falls_back_to_qty_alias(self):
        result = await profit_target_condition(
            positions=[{"symbol": "AAPL", "pnl_rate": 6.0, "qty": 9, "market_code": "82"}],
            fields={"target_percent": 5.0},
        )
        assert result["passed_symbols"][0]["quantity"] == 9


class TestFractionalQuantityPassthrough:
    """소수 수량 포지션은 절단 없이 그대로 실려야 한다(전량 청산 플러그인).

    ProfitTarget 은 계산 없이 포지션의 quantity 를 그대로 싣기 때문에 원래도
    절단이 없었다 — 이 테스트는 나중에 int() 정수화가 끼어드는 회귀를 막는 잠금이다.
    (LS 해외주식 소수점 주식 — 출처: 오너 진술 2026-09-12. 정수화는 주문 송신부
    _normalize_order 의 명시적 규약이다.)
    """

    @pytest.mark.asyncio
    async def test_fractional_quantity_is_not_truncated(self):
        result = await profit_target_condition(
            positions=[{"symbol": "AAPL", "pnl_rate": 6.0, "quantity": 0.532,
                        "market_code": "82"}],
            fields={"target_percent": 5.0},
        )
        assert result["passed_symbols"][0]["quantity"] == pytest.approx(0.532)

    @pytest.mark.asyncio
    async def test_decimal_quantity_is_passed_through(self):
        from decimal import Decimal

        result = await profit_target_condition(
            positions=[{"symbol": "AAPL", "pnl_rate": 6.0,
                        "quantity": Decimal("9.5"), "market_code": "82"}],
            fields={"target_percent": 5.0},
        )
        assert result["passed_symbols"][0]["quantity"] == Decimal("9.5")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
