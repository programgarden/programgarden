"""
MaxPositionLimit (최대 포지션 한도) 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.max_position_limit import (
    max_position_limit_condition,
    MAX_POSITION_LIMIT_SCHEMA,
)


class TestMaxPositionLimitPlugin:
    """MaxPositionLimit 플러그인 테스트"""

    @pytest.fixture
    def positions_normal(self):
        """정상 포지션 (3종목)"""
        return [
            {"symbol": "AAPL", "current_price": 150, "qty": 10, "market_value": 1500, "market_code": "82"},
            {"symbol": "MSFT", "current_price": 400, "qty": 5, "market_value": 2000, "market_code": "82"},
            {"symbol": "GOOG", "current_price": 170, "qty": 8, "market_value": 1360, "market_code": "82"},
        ]

    @pytest.fixture
    def positions_heavy(self):
        """비중 쏠림 포지션"""
        return [
            {"symbol": "AAPL", "current_price": 150, "qty": 100, "market_value": 15000, "market_code": "82"},
            {"symbol": "MSFT", "current_price": 400, "qty": 2, "market_value": 800, "market_code": "82"},
            {"symbol": "GOOG", "current_price": 170, "qty": 1, "market_value": 170, "market_code": "82"},
        ]

    @pytest.mark.asyncio
    async def test_within_limits(self, positions_normal):
        """한도 이내"""
        result = await max_position_limit_condition(
            positions=positions_normal,
            fields={"max_positions": 10, "max_single_weight_pct": 50},
        )
        assert result["result"] is False  # 위반 없음

    @pytest.mark.asyncio
    async def test_count_exceeded(self, positions_normal):
        """종목 수 초과"""
        result = await max_position_limit_condition(
            positions=positions_normal,
            fields={"max_positions": 2, "action": "warn"},
        )
        assert result["result"] is True
        assert result["analysis"]["count_exceeded"] is True

    @pytest.mark.asyncio
    async def test_value_exceeded(self, positions_normal):
        """총 가치 초과"""
        result = await max_position_limit_condition(
            positions=positions_normal,
            fields={"max_total_value": 3000, "action": "warn"},
        )
        assert result["result"] is True
        assert result["analysis"]["value_exceeded"] is True

    @pytest.mark.asyncio
    async def test_weight_exceeded(self, positions_heavy):
        """개별 비중 초과"""
        result = await max_position_limit_condition(
            positions=positions_heavy,
            fields={"max_single_weight_pct": 50, "action": "warn"},
        )
        assert result["result"] is True
        assert result["analysis"]["overweight_count"] >= 1

    @pytest.mark.asyncio
    async def test_exit_excess_action(self, positions_normal):
        """초과분 청산 액션"""
        result = await max_position_limit_condition(
            positions=positions_normal,
            fields={"max_positions": 2, "action": "exit_excess"},
        )
        exit_syms = [sr for sr in result["symbol_results"] if sr["action_taken"] == "exit"]
        assert len(exit_syms) >= 1

    @pytest.mark.asyncio
    async def test_block_new_action(self, positions_normal):
        """신규 매수 차단 액션"""
        result = await max_position_limit_condition(
            positions=positions_normal,
            fields={"max_positions": 2, "action": "block_new"},
        )
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_no_positions(self):
        """포지션 없음"""
        result = await max_position_limit_condition(positions=[], fields={})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_market_value_fallback(self):
        """market_value 없을 때 current_price * qty"""
        positions = [
            {"symbol": "AAPL", "current_price": 100, "qty": 10, "market_code": "82"},
        ]
        result = await max_position_limit_condition(
            positions=positions,
            fields={"max_positions": 10},
        )
        sr = result["symbol_results"][0]
        assert sr["market_value"] == 1000

    @pytest.mark.asyncio
    async def test_analysis_detail(self, positions_normal):
        """분석 결과 상세"""
        result = await max_position_limit_condition(
            positions=positions_normal,
            fields={"max_positions": 10},
        )
        a = result["analysis"]
        assert a["indicator"] == "MaxPositionLimit"
        assert a["position_count"] == 3
        assert a["total_value"] > 0

    def test_schema(self):
        """스키마 검증"""
        assert MAX_POSITION_LIMIT_SCHEMA.id == "MaxPositionLimit"
        assert MAX_POSITION_LIMIT_SCHEMA.category == "position"
        assert "max_positions" in MAX_POSITION_LIMIT_SCHEMA.fields_schema
        assert "max_total_value" in MAX_POSITION_LIMIT_SCHEMA.fields_schema
        assert "max_single_weight_pct" in MAX_POSITION_LIMIT_SCHEMA.fields_schema
        assert "action" in MAX_POSITION_LIMIT_SCHEMA.fields_schema



class TestUnreadablePositionValues:
    """V3 [MAJOR] — ``market_value = current_price * qty`` 뒤 ``float(market_value)`` 였던 경로.

    current_price='150.0'(정상 숫자 문자열)/qty=100 이면 곱셈이 문자열 반복('150.0'×100)이
    되고 float() 에서 ValueError 로 죽었다(실측 2026-09-12) — **정상값으로도** 죽었다.
    'n/a'·None 은 곱셈에서 TypeError. (전수 계약은 test_position_field_coercion_regression.py.)
    """

    @pytest.mark.asyncio
    async def test_numeric_string_price_no_longer_repeats_string(self):
        result = await max_position_limit_condition(
            positions=[{"symbol": "AAPL", "current_price": "150.0", "qty": 100, "market_code": "82"}],
            fields={"max_positions": 10},
        )
        sr = result["symbol_results"][0]
        assert sr["market_value"] == 15000.0
        assert sr["current_price"] == 150.0
        assert result["analysis"]["total_value"] == 15000.0

    @pytest.mark.asyncio
    @pytest.mark.parametrize("raw", ["n/a", None], ids=repr)
    async def test_unreadable_price_without_market_value_is_skipped_with_reason(self, raw):
        result = await max_position_limit_condition(
            positions=[
                {"symbol": "AAPL", "current_price": raw, "qty": 100, "market_code": "82"},
                {"symbol": "MSFT", "current_price": 400, "qty": 5, "market_code": "82"},
            ],
            fields={"max_positions": 10, "max_single_weight_pct": 50},
        )
        aapl = next(sr for sr in result["symbol_results"] if sr["symbol"] == "AAPL")
        assert aapl["action_taken"] == "skip"
        assert f"current_price={raw!r}" in aapl["reason"]
        assert "market_value" not in aapl and "weight_pct" not in aapl  # 0 으로 지어내지 않는다
        # 못 읽은 포지션은 총액·비중에서 빠진다 — MSFT 가 100% 가 된다(그게 읽은 값의 사실이다).
        msft = next(sr for sr in result["symbol_results"] if sr["symbol"] == "MSFT")
        assert msft["weight_pct"] == 100.0
        assert result["analysis"]["total_value"] == 2000.0
        assert result["analysis"]["unreadable_count"] == 1
        assert result["analysis"]["position_count"] == 2  # 포지션인 건 사실이다

    @pytest.mark.asyncio
    async def test_unreadable_qty_is_skipped_with_reason(self):
        result = await max_position_limit_condition(
            positions=[{"symbol": "AAPL", "current_price": 150.0, "qty": "n/a", "market_code": "82"}],
            fields={},
        )
        sr = result["symbol_results"][0]
        assert sr["action_taken"] == "skip"
        assert "qty='n/a'" in sr["reason"]
        assert result["passed_symbols"] == []

    @pytest.mark.asyncio
    async def test_unreadable_price_with_readable_market_value_still_evaluates(self):
        """market_value 로 금액은 읽혔다 — 현재가만 표시에서 빠지고 사유가 남는다."""
        result = await max_position_limit_condition(
            positions=[{"symbol": "AAPL", "current_price": "n/a", "qty": 100, "market_value": 15000, "market_code": "82"}],
            fields={},
        )
        sr = result["symbol_results"][0]
        assert sr["market_value"] == 15000.0
        assert "current_price" not in sr
        assert "current_price='n/a'" in sr["current_price_unavailable_reason"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
