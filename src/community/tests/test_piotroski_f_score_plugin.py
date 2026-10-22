"""
PiotroskiFScore 플러그인 테스트 (직접 import — 레지스트리 비의존).
"""

import pytest
from programgarden_community.plugins.piotroski_f_score import (
    piotroski_f_score_condition,
    PIOTROSKI_SCHEMA,
    MAX_SCORE,
    SKIPPED_SIGNALS,
    _score_symbol,
)


def _year(sym, exchange, year, *, net_income, total_assets, ltd,
          ca, cl, shares, revenue, gross_profit):
    return {
        "symbol": sym, "exchange": exchange, "calendarYear": str(year),
        "netIncome": net_income, "totalAssets": total_assets,
        "longTermDebt": ltd, "totalCurrentAssets": ca,
        "totalCurrentLiabilities": cl, "weightedAverageShsOut": shares,
        "revenue": revenue, "grossProfit": gross_profit,
    }


def _strong_symbol(sym="AAPL", exchange="NASDAQ"):
    """모든 7신호 True 인 종목 (2년치)."""
    return [
        # current (2023) — 개선된 값
        _year(sym, exchange, 2023, net_income=100, total_assets=1000, ltd=200,
              ca=600, cl=300, shares=1000, revenue=1000, gross_profit=400),
        # prior (2022)
        _year(sym, exchange, 2022, net_income=80, total_assets=1000, ltd=250,
              ca=500, cl=300, shares=1000, revenue=900, gross_profit=315),
    ]


def _weak_symbol(sym="WEAK", exchange="NASDAQ"):
    """모든 7신호 False 인 종목 (2년치)."""
    return [
        _year(sym, exchange, 2023, net_income=-50, total_assets=1000, ltd=300,
              ca=200, cl=300, shares=1200, revenue=800, gross_profit=80),
        _year(sym, exchange, 2022, net_income=20, total_assets=1000, ltd=200,
              ca=400, cl=300, shares=1000, revenue=1000, gross_profit=200),
    ]


class TestPiotroskiSchema:
    def test_schema_id_and_category(self):
        assert PIOTROSKI_SCHEMA.id == "PiotroskiFScore"
        # PluginSchema use_enum_values=True → category is a string
        assert PIOTROSKI_SCHEMA.category == "technical"

    def test_schema_products_stock(self):
        assert "overseas_stock" in PIOTROSKI_SCHEMA.products

    def test_output_fields_nonempty_no_symbol(self):
        of = PIOTROSKI_SCHEMA.output_fields
        assert of, "output_fields must not be empty"
        assert "symbol" not in of and "exchange" not in of

    def test_description_flags_category_mismatch(self):
        desc = PIOTROSKI_SCHEMA.description.lower()
        assert "fundamental" in desc
        assert "technical" in desc


class TestPiotroskiHappyPath:
    @pytest.mark.asyncio
    async def test_two_year_two_symbol(self):
        data = _strong_symbol() + _weak_symbol()
        result = await piotroski_f_score_condition(data=data, fields={"min_score": 5})

        # f_score <= 7 for every scored symbol
        scores = {sr["symbol"]: sr["f_score"] for sr in result["symbol_results"]}
        for sym, sc in scores.items():
            if sc is not None:
                assert 0 <= sc <= MAX_SCORE

        assert scores["AAPL"] == 7
        assert scores["WEAK"] == 0

        passed = {s["symbol"] for s in result["passed_symbols"]}
        assert "AAPL" in passed
        assert "WEAK" not in passed
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_skipped_signals_and_max_score_present(self):
        data = _strong_symbol()
        result = await piotroski_f_score_condition(data=data, fields={})
        analysis = result["analysis"]
        assert analysis["max_score"] == 7
        assert analysis["skipped_signals"] == list(SKIPPED_SIGNALS)
        assert analysis["skipped_signals"] == ["cfo_positive", "accruals"]
        assert analysis.get("note")

    @pytest.mark.asyncio
    async def test_signals_have_seven_keys_no_cfo(self):
        result = await piotroski_f_score_condition(data=_strong_symbol(), fields={})
        signals = result["symbol_results"][0]["signals"]
        assert len(signals) == 7
        assert "cfo_positive" not in signals
        assert "accruals" not in signals


class TestPiotroskiBoundaries:
    @pytest.mark.asyncio
    async def test_empty_data_returns_error(self):
        result = await piotroski_f_score_condition(data=[], fields={})
        assert result["result"] is False
        assert "error" in result["analysis"]
        # even on error the reduced-score metadata is surfaced
        assert result["analysis"]["max_score"] == 7

    @pytest.mark.asyncio
    async def test_single_year_missing_reason(self):
        """cfo 부재(항상) + 1년치만 → insufficient_years missing_reason, max_score=7."""
        data = _strong_symbol()[:1]  # 1개 연도만
        result = await piotroski_f_score_condition(data=data, fields={})
        sr = result["symbol_results"][0]
        assert sr["f_score"] is None
        assert sr["missing_reason"] == "insufficient_years"
        assert sr["max_score"] == 7
        assert result["analysis"]["note"]

    @pytest.mark.asyncio
    async def test_missing_total_assets_missing_reason(self):
        rows = _strong_symbol()
        # 최신 연도 totalAssets 제거
        rows[0].pop("totalAssets")
        result = await piotroski_f_score_condition(data=rows, fields={})
        sr = result["symbol_results"][0]
        assert sr["f_score"] is None
        assert sr["missing_reason"] == "missing_total_assets"

    @pytest.mark.asyncio
    async def test_max_score_never_exceeds_seven(self):
        # even a perfect symbol caps at 7 (cfo signals skipped)
        result = await piotroski_f_score_condition(data=_strong_symbol(), fields={})
        assert result["symbol_results"][0]["f_score"] <= 7


class TestPiotroskiUnit:
    def test_score_symbol_strong(self):
        rows = _strong_symbol()
        scored = _score_symbol(rows[0], rows[1])
        assert scored["missing_reason"] is None
        assert scored["f_score"] == 7

    def test_score_symbol_weak(self):
        rows = _weak_symbol()
        scored = _score_symbol(rows[0], rows[1])
        assert scored["f_score"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
