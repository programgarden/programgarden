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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
