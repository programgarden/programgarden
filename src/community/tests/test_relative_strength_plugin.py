"""
RelativeStrength (상대 강도) 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.relative_strength import (
    relative_strength_condition,
    RELATIVE_STRENGTH_SCHEMA,
)


class TestRelativeStrengthPlugin:
    """RelativeStrength 플러그인 테스트"""

    @pytest.fixture
    def mock_data_with_benchmark(self):
        """벤치마크(SPY) + 아웃퍼포머(AAPL) + 언더퍼포머(XOM)"""
        data = []
        spy_price, aapl_price, xom_price = 100.0, 100.0, 100.0
        for i in range(70):
            spy_price *= 1.003
            aapl_price *= 1.006  # 벤치마크 대비 2배 성과
            xom_price *= 1.001  # 벤치마크 대비 열세
            date = f"2025{(i // 30) + 1:02d}{(i % 30) + 1:02d}"
            data.append({"symbol": "SPY", "exchange": "NYSE", "date": date, "close": round(spy_price, 2)})
            data.append({"symbol": "AAPL", "exchange": "NASDAQ", "date": date, "close": round(aapl_price, 2)})
            data.append({"symbol": "XOM", "exchange": "NYSE", "date": date, "close": round(xom_price, 2)})
        return data

    # === 스키마 테스트 ===
    def test_schema_id(self):
        assert RELATIVE_STRENGTH_SCHEMA.id == "RelativeStrength"

    def test_schema_category(self):
        assert RELATIVE_STRENGTH_SCHEMA.category == "technical"

    def test_schema_fields(self):
        assert "lookback" in RELATIVE_STRENGTH_SCHEMA.fields_schema
        assert "benchmark_symbol" in RELATIVE_STRENGTH_SCHEMA.fields_schema
        assert "rank_method" in RELATIVE_STRENGTH_SCHEMA.fields_schema

    # === 조건 평가 테스트 ===
    @pytest.mark.asyncio
    async def test_outperformer_detection(self, mock_data_with_benchmark):
        result = await relative_strength_condition(
            data=mock_data_with_benchmark,
            fields={"lookback": 60, "benchmark_symbol": "SPY", "rank_method": "raw", "threshold": 0.0, "direction": "above"},
        )
        passed_syms = [s["symbol"] for s in result["passed_symbols"]]
        assert "AAPL" in passed_syms

    @pytest.mark.asyncio
    async def test_underperformer_detection(self, mock_data_with_benchmark):
        result = await relative_strength_condition(
            data=mock_data_with_benchmark,
            fields={"lookback": 60, "benchmark_symbol": "SPY", "rank_method": "raw", "threshold": 0.0, "direction": "below"},
        )
        passed_syms = [s["symbol"] for s in result["passed_symbols"]]
        assert "XOM" in passed_syms

    @pytest.mark.asyncio
    async def test_percentile_method(self, mock_data_with_benchmark):
        result = await relative_strength_condition(
            data=mock_data_with_benchmark,
            fields={"lookback": 60, "benchmark_symbol": "SPY", "rank_method": "percentile", "threshold": 50, "direction": "above"},
        )
        assert isinstance(result["result"], bool)
        for sr in result["symbol_results"]:
            if "rs_score" in sr:
                assert 0 <= sr["rs_score"] <= 100

    @pytest.mark.asyncio
    async def test_z_score_method(self, mock_data_with_benchmark):
        result = await relative_strength_condition(
            data=mock_data_with_benchmark,
            fields={"lookback": 60, "benchmark_symbol": "SPY", "rank_method": "z_score", "threshold": 0.0},
        )
        assert isinstance(result["result"], bool)

    @pytest.mark.asyncio
    async def test_ranking_output(self, mock_data_with_benchmark):
        result = await relative_strength_condition(
            data=mock_data_with_benchmark,
            fields={"lookback": 60, "benchmark_symbol": "SPY"},
        )
        assert "ranking" in result
        assert len(result["ranking"]) > 0

    @pytest.mark.asyncio
    async def test_empty_data(self):
        result = await relative_strength_condition(data=[], fields={})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_no_benchmark_in_data(self):
        data = [{"symbol": "AAPL", "exchange": "NASDAQ", "date": f"2025{(i // 30) + 1:02d}{(i % 30) + 1:02d}", "close": 150 + i} for i in range(70)]
        result = await relative_strength_condition(
            data=data,
            fields={"lookback": 60, "benchmark_symbol": "SPY"},
        )
        # benchmark 없어도 동작해야 함 (benchmark_return=0)
        assert "symbol_results" in result

    @pytest.mark.asyncio
    async def test_analysis_output(self, mock_data_with_benchmark):
        result = await relative_strength_condition(
            data=mock_data_with_benchmark,
            fields={"lookback": 60, "benchmark_symbol": "SPY"},
        )
        assert result["analysis"]["indicator"] == "RelativeStrength"
        assert "benchmark_return" in result["analysis"]

    @pytest.mark.asyncio
    async def test_benchmark_excluded_from_results(self, mock_data_with_benchmark):
        result = await relative_strength_condition(
            data=mock_data_with_benchmark,
            fields={"lookback": 60, "benchmark_symbol": "SPY"},
        )
        result_symbols = [sr["symbol"] for sr in result["symbol_results"]]
        assert "SPY" not in result_symbols
