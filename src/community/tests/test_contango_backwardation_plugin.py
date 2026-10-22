"""
ContangoBackwardation (콘탱고/백워데이션) 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.contango_backwardation import (
    contango_backwardation_condition,
    CONTANGO_BACKWARDATION_SCHEMA,
    _parse_contract_order,
)


class TestContangoBackwardationPlugin:
    """ContangoBackwardation 플러그인 테스트"""

    @pytest.fixture
    def mock_data_contango(self):
        """콘탱고 상태 (원월물 > 근월물)"""
        return [
            {"symbol": "CLF26", "exchange": "CME", "date": "20260115", "close": 70.0},
            {"symbol": "CLG26", "exchange": "CME", "date": "20260115", "close": 71.5},
            {"symbol": "CLH26", "exchange": "CME", "date": "20260115", "close": 73.0},
        ]

    @pytest.fixture
    def mock_data_backwardation(self):
        """백워데이션 상태 (근월물 > 원월물)"""
        return [
            {"symbol": "CLF26", "exchange": "CME", "date": "20260115", "close": 75.0},
            {"symbol": "CLG26", "exchange": "CME", "date": "20260115", "close": 73.5},
            {"symbol": "CLH26", "exchange": "CME", "date": "20260115", "close": 72.0},
        ]

    @pytest.fixture
    def mock_data_flat(self):
        """거의 평탄 (스프레드 임계 미달)"""
        return [
            {"symbol": "CLF26", "exchange": "CME", "date": "20260115", "close": 70.0},
            {"symbol": "CLG26", "exchange": "CME", "date": "20260115", "close": 70.1},
        ]

    # === 유틸 함수 테스트 ===
    def test_parse_contract_order_standard(self):
        assert _parse_contract_order("CLF26") == 202601

    def test_parse_contract_order_february(self):
        assert _parse_contract_order("CLG26") == 202602

    def test_parse_contract_order_december(self):
        assert _parse_contract_order("CLZ25") == 202512

    def test_parse_contract_order_long_prefix(self):
        assert _parse_contract_order("HMCEG26") == 202602

    def test_parse_contract_order_invalid(self):
        assert _parse_contract_order("AB") is None

    def test_parse_contract_order_invalid_month(self):
        assert _parse_contract_order("CLA26") is None  # A is not a valid month code

    # === 조건 평가 테스트 ===
    @pytest.mark.asyncio
    async def test_contango_detected(self, mock_data_contango):
        result = await contango_backwardation_condition(
            data=mock_data_contango,
            fields={"structure": "contango", "spread_threshold": 0.5},
        )
        assert result["result"] is True
        assert result["term_structure"]["structure"] == "contango"
        assert result["term_structure"]["total_spread_pct"] > 0

    @pytest.mark.asyncio
    async def test_backwardation_detected(self, mock_data_backwardation):
        result = await contango_backwardation_condition(
            data=mock_data_backwardation,
            fields={"structure": "backwardation", "spread_threshold": 0.5},
        )
        assert result["result"] is True
        assert result["term_structure"]["structure"] == "backwardation"
        assert result["term_structure"]["total_spread_pct"] < 0

    @pytest.mark.asyncio
    async def test_any_structure(self, mock_data_contango):
        result = await contango_backwardation_condition(
            data=mock_data_contango,
            fields={"structure": "any", "spread_threshold": 0.5},
        )
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_wrong_structure_filter(self, mock_data_contango):
        result = await contango_backwardation_condition(
            data=mock_data_contango,
            fields={"structure": "backwardation", "spread_threshold": 0.5},
        )
        # contango인데 backwardation 탐지 → 통과 안됨
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_flat_below_threshold(self, mock_data_flat):
        result = await contango_backwardation_condition(
            data=mock_data_flat,
            fields={"structure": "any", "spread_threshold": 0.5},
        )
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_empty_data(self):
        result = await contango_backwardation_condition(data=[], fields={})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_single_contract(self):
        data = [{"symbol": "CLF26", "exchange": "CME", "date": "20260115", "close": 70.0}]
        result = await contango_backwardation_condition(data=data, fields={})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_spread_details(self, mock_data_contango):
        result = await contango_backwardation_condition(
            data=mock_data_contango,
            fields={"structure": "any", "spread_threshold": 0.1},
        )
        assert "spreads" in result["term_structure"]
        assert len(result["term_structure"]["spreads"]) == 2  # 3 contracts = 2 adjacent pairs

    @pytest.mark.asyncio
    async def test_output_structure(self, mock_data_contango):
        result = await contango_backwardation_condition(
            data=mock_data_contango,
            fields={},
        )
        assert "term_structure" in result
        assert result["analysis"]["indicator"] == "ContangoBackwardation"
        assert "front_month" in result["term_structure"]
        assert "back_month" in result["term_structure"]

    @pytest.mark.asyncio
    async def test_futures_only_product(self):
        from programgarden_core.registry.plugin_registry import ProductType
        assert ProductType.OVERSEAS_FUTURES in CONTANGO_BACKWARDATION_SCHEMA.products
        assert ProductType.OVERSEAS_STOCK not in CONTANGO_BACKWARDATION_SCHEMA.products
