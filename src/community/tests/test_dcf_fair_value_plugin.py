"""
DCFFairValue 플러그인 테스트 (직접 import — 레지스트리 비의존).
"""

import pytest
from programgarden_community.plugins.dcf_fair_value import (
    dcf_fair_value_condition,
    DCF_SCHEMA,
    compute_dcf_fair_value,
)


class TestDCFSchema:
    def test_schema_id_category(self):
        assert DCF_SCHEMA.id == "DCFFairValue"
        assert DCF_SCHEMA.category == "technical"

    def test_products_stock(self):
        assert "overseas_stock" in DCF_SCHEMA.products

    def test_output_fields_no_symbol(self):
        of = DCF_SCHEMA.output_fields
        assert of
        assert "symbol" not in of and "exchange" not in of

    def test_description_flags_mismatch_and_fcf(self):
        desc = DCF_SCHEMA.description.lower()
        assert "fundamental" in desc and "technical" in desc
        # description must state FundamentalDataNode does not provide fcf
        assert "fcf" in desc or "free cash flow" in desc
        assert "fundamentaldatanode" in desc


class TestDCFHappyPath:
    @pytest.mark.asyncio
    async def test_fcf_shares_price_undervalued(self):
        data = [{
            "symbol": "AAPL", "exchange": "NASDAQ",
            "fcf": 100.0, "shares_outstanding": 10.0, "current_price": 50.0,
        }]
        result = await dcf_fair_value_condition(data=data, fields={})
        sr = result["symbol_results"][0]
        assert sr["fair_value"] is not None and sr["fair_value"] > 0
        assert sr["current_price"] == 50.0
        # fair value per share should be well above $50 with these cash flows
        assert sr["undervalued"] is True
        assert sr["margin_pct"] > 0
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_overvalued_fails(self):
        # very high price relative to fair value
        data = [{
            "symbol": "OVR", "exchange": "NASDAQ",
            "fcf": 1.0, "shares_outstanding": 100.0, "current_price": 9999.0,
        }]
        result = await dcf_fair_value_condition(data=data, fields={})
        sr = result["symbol_results"][0]
        assert sr["undervalued"] is False
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_analysis_reports_fcf_missing_count(self):
        data = [
            {"symbol": "A", "exchange": "NASDAQ", "fcf": 100, "shares_outstanding": 10, "current_price": 50},
            {"symbol": "B", "exchange": "NASDAQ", "shares_outstanding": 10, "current_price": 50},  # no fcf
        ]
        result = await dcf_fair_value_condition(data=data, fields={})
        assert result["analysis"]["fcf_missing_count"] == 1


class TestDCFBoundaries:
    @pytest.mark.asyncio
    async def test_empty_data_error(self):
        result = await dcf_fair_value_condition(data=[], fields={})
        assert result["result"] is False
        assert "error" in result["analysis"]

    @pytest.mark.asyncio
    async def test_r_leq_terminal_growth_error(self):
        data = [{"symbol": "A", "exchange": "NASDAQ", "fcf": 100, "shares_outstanding": 10, "current_price": 50}]
        result = await dcf_fair_value_condition(
            data=data,
            fields={"discount_rate": 0.02, "terminal_growth": 0.025},
        )
        assert result["result"] is False
        assert "error" in result["analysis"]
        assert "terminal_growth" in result["analysis"]["error"]

    @pytest.mark.asyncio
    async def test_fcf_absent_missing_reason(self):
        data = [{"symbol": "NOFCF", "exchange": "NASDAQ", "shares_outstanding": 10, "current_price": 50}]
        result = await dcf_fair_value_condition(data=data, fields={})
        sr = result["symbol_results"][0]
        assert sr["fair_value"] is None
        assert sr["missing_reason"] == "fcf_unavailable"
        assert "FundamentalDataNode" in sr.get("detail", "")

    @pytest.mark.asyncio
    async def test_invalid_shares_missing_reason(self):
        data = [{"symbol": "SH", "exchange": "NASDAQ", "fcf": 100, "shares_outstanding": 0, "current_price": 50}]
        result = await dcf_fair_value_condition(data=data, fields={})
        sr = result["symbol_results"][0]
        assert sr["missing_reason"] == "invalid_shares_outstanding"

    @pytest.mark.asyncio
    async def test_price_absent_missing_reason(self):
        data = [{"symbol": "NP", "exchange": "NASDAQ", "fcf": 100, "shares_outstanding": 10}]
        result = await dcf_fair_value_condition(data=data, fields={})
        sr = result["symbol_results"][0]
        # fair value computed, but no price to compare -> explicit reason (no silent pass)
        assert sr["fair_value"] is not None
        assert sr["missing_reason"] == "current_price_unavailable"
        assert sr["undervalued"] is None


class TestDCFUnit:
    def test_compute_positive(self):
        v = compute_dcf_fair_value(100.0, 10.0, 0.10, 0.09, 0.025, 10)
        assert v is not None and v > 0

    def test_compute_zero_shares(self):
        assert compute_dcf_fair_value(100.0, 0.0, 0.10, 0.09, 0.025, 10) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
