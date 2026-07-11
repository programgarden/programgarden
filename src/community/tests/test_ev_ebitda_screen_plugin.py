"""
EVEBITDAScreen 플러그인 테스트 (직접 import — 레지스트리 비의존).
"""

import pytest
from programgarden_community.plugins.ev_ebitda_screen import (
    ev_ebitda_screen_condition,
    EV_EBITDA_SCHEMA,
)


def _rows(pairs):
    """pairs: [(symbol, ev_to_ebitda), ...]"""
    return [{"symbol": s, "exchange": "NASDAQ", "ev_to_ebitda": m} for s, m in pairs]


class TestEVSchema:
    def test_schema_id_category(self):
        assert EV_EBITDA_SCHEMA.id == "EVEBITDAScreen"
        assert EV_EBITDA_SCHEMA.category == "technical"

    def test_products_stock(self):
        assert "overseas_stock" in EV_EBITDA_SCHEMA.products

    def test_output_fields_no_symbol(self):
        of = EV_EBITDA_SCHEMA.output_fields
        assert of
        assert "symbol" not in of and "exchange" not in of

    def test_description_flags_mismatch_and_differentiates(self):
        desc = EV_EBITDA_SCHEMA.description.lower()
        assert "fundamental" in desc and "technical" in desc
        # must differentiate from magic formula
        assert "magicformula" in desc or "magic formula" in desc


class TestEVHappyPath:
    @pytest.mark.asyncio
    async def test_threshold_only(self):
        data = _rows([("A", 6), ("B", 8), ("C", 12), ("D", 5)])
        result = await ev_ebitda_screen_condition(data=data, fields={"max_ev_ebitda": 10.0})
        passed = {s["symbol"] for s in result["passed_symbols"]}
        assert passed == {"A", "B", "D"}  # C (12) excluded
        assert result["result"] is True
        assert result["analysis"]["cross_sectional"] is False

    @pytest.mark.asyncio
    async def test_top_n_ranks_lowest(self):
        data = _rows([("A", 6), ("B", 8), ("C", 12), ("D", 5)])
        result = await ev_ebitda_screen_condition(
            data=data, fields={"max_ev_ebitda": 10.0, "top_n": 2}
        )
        passed = {s["symbol"] for s in result["passed_symbols"]}
        # lowest 2 under threshold: D(5), A(6)
        assert passed == {"D", "A"}
        assert result["analysis"]["cross_sectional"] is True
        # ranks assigned cross-sectionally (1 = cheapest overall)
        rank_of = {sr["symbol"]: sr["rank"] for sr in result["symbol_results"]}
        assert rank_of["D"] == 1
        assert rank_of["A"] == 2

    @pytest.mark.asyncio
    async def test_ev_to_ebitda_value_reported(self):
        data = _rows([("A", 6.5)])
        result = await ev_ebitda_screen_condition(data=data, fields={"max_ev_ebitda": 10})
        sr = result["symbol_results"][0]
        assert sr["ev_to_ebitda"] == 6.5
        assert sr["passed"] is True

    @pytest.mark.asyncio
    async def test_computed_from_ev_and_ebitda(self):
        data = [{"symbol": "X", "exchange": "NASDAQ", "enterprise_value": 90, "ebitda": 10}]
        result = await ev_ebitda_screen_condition(data=data, fields={"max_ev_ebitda": 10})
        sr = result["symbol_results"][0]
        assert sr["ev_to_ebitda"] == 9.0
        assert sr["passed"] is True


class TestEVBoundaries:
    @pytest.mark.asyncio
    async def test_empty_data_error(self):
        result = await ev_ebitda_screen_condition(data=[], fields={})
        assert result["result"] is False
        assert "error" in result["analysis"]

    @pytest.mark.asyncio
    async def test_negative_multiple_missing_reason(self):
        data = _rows([("NEG", -3)])
        result = await ev_ebitda_screen_condition(data=data, fields={"max_ev_ebitda": 10})
        sr = result["symbol_results"][0]
        assert sr["missing_reason"] == "non_positive_ev_ebitda"
        assert sr["passed"] is False

    @pytest.mark.asyncio
    async def test_ebitda_non_positive_missing_reason(self):
        # EBITDA <= 0 -> multiple cannot be computed -> missing_reason
        data = [{"symbol": "Z", "exchange": "NASDAQ", "enterprise_value": 100, "ebitda": 0}]
        result = await ev_ebitda_screen_condition(data=data, fields={"max_ev_ebitda": 10})
        sr = result["symbol_results"][0]
        assert sr["missing_reason"] == "ev_ebitda_unavailable"

    @pytest.mark.asyncio
    async def test_all_above_threshold_no_pass(self):
        data = _rows([("A", 20), ("B", 30)])
        result = await ev_ebitda_screen_condition(data=data, fields={"max_ev_ebitda": 10})
        assert result["result"] is False
        assert len(result["passed_symbols"]) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
