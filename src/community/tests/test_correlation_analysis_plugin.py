"""
CorrelationAnalysis (상관관계 분석) 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.correlation_analysis import (
    correlation_analysis_condition,
    CORRELATION_ANALYSIS_SCHEMA,
    _pearson_correlation,
    _spearman_correlation,
)


class TestCorrelationAnalysisPlugin:
    """CorrelationAnalysis 플러그인 테스트"""

    @pytest.fixture
    def mock_data_high_correlation(self):
        """고상관 종목 페어 (AAPL, MSFT - 같은 방향)"""
        data = []
        for i in range(70):
            date = f"2025{(i // 30) + 1:02d}{(i % 30) + 1:02d}"
            data.append({"symbol": "AAPL", "exchange": "NASDAQ", "date": date, "close": 150 + i * 1.5})
            data.append({"symbol": "MSFT", "exchange": "NASDAQ", "date": date, "close": 400 + i * 2.0})
        return data

    @pytest.fixture
    def mock_data_low_correlation(self):
        """저상관 종목 페어 (AAPL 상승, XOM 횡보)"""
        data = []
        import math
        for i in range(70):
            date = f"2025{(i // 30) + 1:02d}{(i % 30) + 1:02d}"
            data.append({"symbol": "AAPL", "exchange": "NASDAQ", "date": date, "close": 150 + i * 1.5})
            data.append({"symbol": "XOM", "exchange": "NYSE", "date": date, "close": 100 + math.sin(i / 3) * 5})
        return data

    @pytest.fixture
    def mock_data_three_symbols(self):
        """3종목 데이터"""
        data = []
        for i in range(70):
            date = f"2025{(i // 30) + 1:02d}{(i % 30) + 1:02d}"
            data.append({"symbol": "AAPL", "exchange": "NASDAQ", "date": date, "close": 150 + i * 1.5})
            data.append({"symbol": "MSFT", "exchange": "NASDAQ", "date": date, "close": 400 + i * 2.0})
            data.append({"symbol": "GOOG", "exchange": "NASDAQ", "date": date, "close": 170 + i * 1.8})
        return data

    # === 유틸 함수 테스트 ===
    def test_pearson_perfect_correlation(self):
        x = [1, 2, 3, 4, 5]
        y = [2, 4, 6, 8, 10]
        assert abs(_pearson_correlation(x, y) - 1.0) < 0.001

    def test_pearson_negative_correlation(self):
        x = [1, 2, 3, 4, 5]
        y = [10, 8, 6, 4, 2]
        assert abs(_pearson_correlation(x, y) - (-1.0)) < 0.001

    def test_spearman_perfect_rank_correlation(self):
        x = [1, 2, 3, 4, 5]
        y = [10, 20, 30, 40, 50]
        assert abs(_spearman_correlation(x, y) - 1.0) < 0.001

    def test_correlation_empty_data(self):
        assert _pearson_correlation([], []) == 0.0

    # === 조건 평가 테스트 ===
    @pytest.mark.asyncio
    async def test_high_correlation_detected(self, mock_data_high_correlation):
        result = await correlation_analysis_condition(
            data=mock_data_high_correlation,
            fields={"lookback": 60, "threshold": 0.8, "direction": "above", "method": "pearson"},
        )
        assert result["result"] is True
        assert len(result["pair_correlations"]) > 0

    @pytest.mark.asyncio
    async def test_low_correlation_filter(self, mock_data_low_correlation):
        result = await correlation_analysis_condition(
            data=mock_data_low_correlation,
            fields={"lookback": 60, "threshold": 0.3, "direction": "below", "method": "pearson"},
        )
        assert isinstance(result["result"], bool)

    @pytest.mark.asyncio
    async def test_spearman_method(self, mock_data_high_correlation):
        result = await correlation_analysis_condition(
            data=mock_data_high_correlation,
            fields={"lookback": 60, "method": "spearman"},
        )
        assert isinstance(result["result"], bool)

    @pytest.mark.asyncio
    async def test_three_symbol_pairs(self, mock_data_three_symbols):
        result = await correlation_analysis_condition(
            data=mock_data_three_symbols,
            fields={"lookback": 60},
        )
        # 3 symbols = 3 pairs (A-B, A-C, B-C)
        assert len(result["pair_correlations"]) == 3

    @pytest.mark.asyncio
    async def test_single_symbol_error(self):
        data = [{"symbol": "AAPL", "exchange": "NASDAQ", "date": f"202501{i + 1:02d}", "close": 150 + i} for i in range(30)]
        result = await correlation_analysis_condition(data=data, fields={})
        assert result["result"] is False
        assert "error" in result["analysis"]

    @pytest.mark.asyncio
    async def test_empty_data(self):
        result = await correlation_analysis_condition(data=[], fields={})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_output_structure(self, mock_data_high_correlation):
        result = await correlation_analysis_condition(
            data=mock_data_high_correlation,
            fields={"lookback": 60},
        )
        assert "pair_correlations" in result
        assert result["analysis"]["indicator"] == "CorrelationAnalysis"
        for pc in result["pair_correlations"]:
            assert "symbol_a" in pc
            assert "symbol_b" in pc
            assert -1 <= pc["correlation"] <= 1
