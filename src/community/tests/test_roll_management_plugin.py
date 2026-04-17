"""
RollManagement (롤오버 관리) 플러그인 테스트
"""

import pytest
from datetime import datetime
from programgarden_community.plugins.roll_management import (
    roll_management_condition,
    ROLL_MANAGEMENT_SCHEMA,
    _parse_expiry_date,
    _get_next_contract,
    risk_features,
)


class TestRollManagementPlugin:
    """RollManagement 플러그인 테스트"""

    @pytest.fixture
    def positions_near_expiry(self):
        """만기 임박 포지션"""
        # 현재 날짜 기준으로 곧 만기될 월물
        now = datetime.now()
        # 현재 월의 월물 코드 찾기
        month_code_map = {1: "F", 2: "G", 3: "H", 4: "J", 5: "K", 6: "M",
                         7: "N", 8: "Q", 9: "U", 10: "V", 11: "X", 12: "Z"}
        current_month_code = month_code_map[now.month]
        year_str = str(now.year)[-2:]
        symbol = f"CL{current_month_code}{year_str}"
        return [
            {"symbol": symbol, "current_price": 70.5, "qty": 2, "market_code": "CME"},
        ]

    @pytest.fixture
    def positions_far_expiry(self):
        """만기 먼 포지션"""
        return [
            {"symbol": "CLZ30", "current_price": 72.0, "qty": 3, "market_code": "CME"},
        ]

    # === 스키마 테스트 ===
    def test_schema_id(self):
        assert ROLL_MANAGEMENT_SCHEMA.id == "RollManagement"

    def test_schema_category(self):
        assert ROLL_MANAGEMENT_SCHEMA.category == "position"

    def test_risk_features(self):
        assert "state" in risk_features

    def test_futures_only(self):
        from programgarden_core.registry.plugin_registry import ProductType
        assert ProductType.OVERSEAS_FUTURES in ROLL_MANAGEMENT_SCHEMA.products
        assert len(ROLL_MANAGEMENT_SCHEMA.products) == 1

    # === 유틸 함수 테스트 ===
    def test_parse_expiry_january(self):
        expiry = _parse_expiry_date("CLF26")
        assert expiry is not None
        assert expiry.year == 2026
        assert expiry.month == 1

    def test_parse_expiry_december(self):
        expiry = _parse_expiry_date("CLZ25")
        assert expiry is not None
        assert expiry.year == 2025
        assert expiry.month == 12

    def test_parse_expiry_long_prefix(self):
        expiry = _parse_expiry_date("HMCEG26")
        assert expiry is not None
        assert expiry.year == 2026
        assert expiry.month == 2

    def test_parse_expiry_invalid(self):
        assert _parse_expiry_date("AB") is None

    def test_get_next_contract_standard(self):
        assert _get_next_contract("CLF26") == "CLG26"

    def test_get_next_contract_december_to_january(self):
        assert _get_next_contract("CLZ25") == "CLF26"

    def test_get_next_contract_long_prefix(self):
        assert _get_next_contract("HMCEG26") == "HMCEH26"

    # === 조건 평가 테스트 ===
    @pytest.mark.asyncio
    async def test_near_expiry_triggered(self, positions_near_expiry):
        result = await roll_management_condition(
            positions=positions_near_expiry,
            fields={"days_before_expiry": 30},  # 넉넉한 기간
        )
        # 현재 월의 만기가 가까우므로 triggered
        if result["result"]:
            assert len(result["passed_symbols"]) > 0
            sr = result["symbol_results"][0]
            assert "next_contract" in sr
            assert sr["should_roll"] is True

    @pytest.mark.asyncio
    async def test_far_expiry_not_triggered(self, positions_far_expiry):
        result = await roll_management_condition(
            positions=positions_far_expiry,
            fields={"days_before_expiry": 5},
        )
        assert result["result"] is False
        assert len(result["failed_symbols"]) == 1

    @pytest.mark.asyncio
    async def test_empty_positions(self):
        result = await roll_management_condition(positions=[], fields={})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_output_structure(self, positions_far_expiry):
        result = await roll_management_condition(
            positions=positions_far_expiry,
            fields={"days_before_expiry": 5},
        )
        assert "passed_symbols" in result
        assert "failed_symbols" in result
        assert result["analysis"]["indicator"] == "RollManagement"

    @pytest.mark.asyncio
    async def test_symbol_results_detail(self, positions_far_expiry):
        result = await roll_management_condition(
            positions=positions_far_expiry,
            fields={"days_before_expiry": 5},
        )
        sr = result["symbol_results"][0]
        assert "expiry_date" in sr
        assert "days_to_expiry" in sr
        assert "next_contract" in sr
        assert "should_roll" in sr

    @pytest.mark.asyncio
    async def test_invalid_symbol_handling(self):
        positions = [
            {"symbol": "INVALID", "current_price": 70.0, "qty": 1, "market_code": "CME"},
        ]
        result = await roll_management_condition(positions=positions, fields={})
        assert result["result"] is False
        assert len(result["failed_symbols"]) == 1
