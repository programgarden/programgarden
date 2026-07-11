"""
GrahamNumber 플러그인 테스트 (직접 import — 레지스트리 비의존).
"""

import math
import pytest
from programgarden_community.plugins.graham_number import (
    graham_number_condition,
    GRAHAM_SCHEMA,
    compute_graham_number,
)


class TestGrahamSchema:
    def test_schema_id_category(self):
        assert GRAHAM_SCHEMA.id == "GrahamNumber"
        assert GRAHAM_SCHEMA.category == "technical"

    def test_products_stock(self):
        assert "overseas_stock" in GRAHAM_SCHEMA.products

    def test_output_fields_no_symbol(self):
        of = GRAHAM_SCHEMA.output_fields
        assert of
        assert "symbol" not in of and "exchange" not in of

    def test_description_flags_mismatch(self):
        desc = GRAHAM_SCHEMA.description.lower()
        assert "fundamental" in desc and "technical" in desc


class TestGrahamHappyPath:
    @pytest.mark.asyncio
    async def test_eps_per_pbr_undervalued(self):
        # eps=10, per=8 -> price=80; pbr=1 -> bvps=80
        # graham = sqrt(22.5*10*80) = sqrt(18000) ~= 134.16 > 80 -> undervalued
        data = [{"symbol": "AAPL", "exchange": "NASDAQ", "eps": 10, "per": 8, "pbr": 1}]
        result = await graham_number_condition(data=data, fields={})
        sr = result["symbol_results"][0]
        assert sr["price"] == 80.0
        assert sr["bvps"] == 80.0
        assert math.isclose(sr["graham_number"], math.sqrt(18000), rel_tol=1e-4)
        assert sr["undervalued"] is True
        assert sr["margin_pct"] > 0
        assert result["result"] is True
        assert {s["symbol"] for s in result["passed_symbols"]} == {"AAPL"}

    @pytest.mark.asyncio
    async def test_overvalued_fails(self):
        # eps=2, per=40 -> price=80; pbr=8 -> bvps=10
        # graham = sqrt(22.5*2*10) = sqrt(450) ~= 21.2 < 80 -> overvalued
        data = [{"symbol": "OVR", "exchange": "NASDAQ", "eps": 2, "per": 40, "pbr": 8}]
        result = await graham_number_condition(data=data, fields={})
        sr = result["symbol_results"][0]
        assert sr["undervalued"] is False
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_current_price_fallback(self):
        # no per -> price falls back to current_price=50, pbr=1 -> bvps=50
        # graham = sqrt(22.5*10*50)=sqrt(11250) ~= 106 > 50 -> undervalued
        data = [{"symbol": "FB", "exchange": "NASDAQ", "eps": 10, "pbr": 1, "current_price": 50}]
        result = await graham_number_condition(data=data, fields={})
        sr = result["symbol_results"][0]
        assert sr["price"] == 50.0
        assert sr["undervalued"] is True

    @pytest.mark.asyncio
    async def test_margin_of_safety_tightens(self):
        # undervalued base, but a large margin_of_safety can flip to fail
        data = [{"symbol": "AAPL", "exchange": "NASDAQ", "eps": 10, "per": 8, "pbr": 1}]
        # graham ~134, price 80; buy_threshold = 134*(1-0.5)=67 < 80 -> not undervalued
        result = await graham_number_condition(data=data, fields={"margin_of_safety": 0.5})
        sr = result["symbol_results"][0]
        assert sr["undervalued"] is False


class TestGrahamBoundaries:
    @pytest.mark.asyncio
    async def test_empty_data_error(self):
        result = await graham_number_condition(data=[], fields={})
        assert result["result"] is False
        assert "error" in result["analysis"]

    @pytest.mark.asyncio
    async def test_negative_eps_missing_reason(self):
        data = [{"symbol": "NEG", "exchange": "NASDAQ", "eps": -1, "per": 10, "pbr": 1}]
        result = await graham_number_condition(data=data, fields={})
        sr = result["symbol_results"][0]
        assert sr["graham_number"] is None
        assert sr["missing_reason"] == "non_positive_eps"
        assert sr["undervalued"] is None

    @pytest.mark.asyncio
    async def test_non_positive_bvps_missing_reason(self):
        # pbr <= 0 -> bvps cannot be derived
        data = [{"symbol": "BVP", "exchange": "NASDAQ", "eps": 5, "per": 10, "pbr": 0}]
        result = await graham_number_condition(data=data, fields={})
        sr = result["symbol_results"][0]
        assert sr["missing_reason"] == "non_positive_bvps"

    @pytest.mark.asyncio
    async def test_non_positive_price_missing_reason(self):
        # eps positive but per=0 and no current_price -> price None -> non_positive_price
        data = [{"symbol": "PRC", "exchange": "NASDAQ", "eps": 5, "per": 0, "pbr": 1}]
        result = await graham_number_condition(data=data, fields={})
        sr = result["symbol_results"][0]
        assert sr["missing_reason"] == "non_positive_price"


class TestGrahamUnit:
    def test_compute_graham_number(self):
        assert math.isclose(compute_graham_number(10, 80), math.sqrt(18000), rel_tol=1e-9)

    def test_compute_graham_number_nonpositive(self):
        assert compute_graham_number(-1, 10) is None
        assert compute_graham_number(10, 0) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
