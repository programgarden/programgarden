"""
StopLoss (손절) 플러그인 테스트

E1: stop_percent 부호 검증 (음수만 허용, 비음수는 명확한 에러로 거절)
E3: 청산 주문 수량(quantity)/청산 방향(close_side) 탑재
"""

import pytest

from programgarden_community.plugins.stop_loss import (
    stop_loss_condition,
    STOP_LOSS_SCHEMA,
)


# ── E1: stop_percent 부호 검증 ──


class TestStopLossSignValidation:
    """음수만 허용 — 0 이상은 raise"""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("bad", [0, 0.0, 3.0, 3, 100.0])
    async def test_non_negative_raises(self, bad):
        """stop_percent >= 0 이면 ValueError"""
        with pytest.raises(ValueError) as exc:
            await stop_loss_condition(
                positions=[{"symbol": "AAPL", "pnl_rate": -5.0}],
                fields={"stop_percent": bad},
            )
        msg = str(exc.value)
        assert "negative" in msg
        # 수익 구간 청산 대안 안내가 포함되어야 한다
        assert "ProfitTarget" in msg or "TrailingStop" in msg

    @pytest.mark.asyncio
    async def test_non_negative_raises_even_without_positions(self):
        """포지션이 없어도 config 오류(부호)는 즉시 raise (fail-fast)"""
        with pytest.raises(ValueError):
            await stop_loss_condition(positions=[], fields={"stop_percent": 5.0})

    @pytest.mark.asyncio
    async def test_non_numeric_raises(self):
        """숫자로 변환 불가한 stop_percent 는 ValueError"""
        with pytest.raises(ValueError):
            await stop_loss_condition(
                positions=[{"symbol": "AAPL", "pnl_rate": -5.0}],
                fields={"stop_percent": "abc"},
            )

    @pytest.mark.asyncio
    async def test_valid_negative_string_coerced(self):
        """문자열 음수도 float 로 강제되어 정상 동작"""
        result = await stop_loss_condition(
            positions=[{"symbol": "AAPL", "pnl_rate": -5.0, "quantity": 10}],
            fields={"stop_percent": "-3.0"},
        )
        assert result["result"] is True
        assert result["analysis"]["stop_percent"] == -3.0

    @pytest.mark.asyncio
    async def test_valid_negative_triggers(self):
        """정상 음수 임계값 — 손절 발동"""
        result = await stop_loss_condition(
            positions=[{"symbol": "AAPL", "pnl_rate": -5.2, "quantity": 10}],
            fields={"stop_percent": -3.0},
        )
        assert result["result"] is True
        assert len(result["passed_symbols"]) == 1

    @pytest.mark.asyncio
    async def test_valid_negative_no_trigger(self):
        """정상 음수 임계값 — 미도달"""
        result = await stop_loss_condition(
            positions=[{"symbol": "AAPL", "pnl_rate": -1.0, "quantity": 10}],
            fields={"stop_percent": -3.0},
        )
        assert result["result"] is False
        assert len(result["passed_symbols"]) == 0

    def test_schema_hint_negative(self):
        """fields_schema 에 음수 힌트(lt=0) 표현"""
        assert STOP_LOSS_SCHEMA.fields_schema["stop_percent"]["lt"] == 0.0


# ── E3: 청산 수량/방향 탑재 ──


class TestSellQuantityWiring:
    """passed_symbols 가 {{ item.quantity }}/{{ item.close_side }} 를 공급"""

    @pytest.mark.asyncio
    async def test_passed_symbol_carries_quantity_and_close_side(self):
        result = await stop_loss_condition(
            positions=[{"symbol": "AAPL", "pnl_rate": -5.0, "quantity": 12,
                        "close_side": "sell", "market_code": "82"}],
            fields={"stop_percent": -3.0},
        )
        ps = result["passed_symbols"][0]
        assert ps["symbol"] == "AAPL"
        assert ps["exchange"] == "NASDAQ"  # market_code 82 → NASDAQ
        assert ps["quantity"] == 12
        assert ps["close_side"] == "sell"

    @pytest.mark.asyncio
    async def test_quantity_falls_back_to_qty_alias(self):
        # 일부 소스는 quantity 대신 qty 를 싣는다 (해외주식 REST 별칭)
        result = await stop_loss_condition(
            positions=[{"symbol": "AAPL", "pnl_rate": -5.0, "qty": 9, "market_code": "82"}],
            fields={"stop_percent": -3.0},
        )
        assert result["passed_symbols"][0]["quantity"] == 9

    @pytest.mark.asyncio
    async def test_futures_short_close_side_preserved(self):
        # 해외선물 숏 포지션은 close_side=buy 로 청산
        result = await stop_loss_condition(
            positions=[{"symbol": "ESH26", "pnl_rate": -5.0, "quantity": 3,
                        "exchange": "CME", "close_side": "buy"}],
            fields={"stop_percent": -3.0},
        )
        ps = result["passed_symbols"][0]
        assert ps["quantity"] == 3
        assert ps["close_side"] == "buy"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
