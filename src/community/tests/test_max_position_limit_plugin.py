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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
