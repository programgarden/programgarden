"""
MomentumRank (모멘텀 순위) 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.momentum_rank import (
    momentum_rank_condition,
    _calculate_momentum,
    MOMENTUM_RANK_SCHEMA,
)


def _make_multi_symbol_data(symbols_data, days=70):
    """다종목 테스트 데이터 생성"""
    data = []
    for sym, exchange, base, trend in symbols_data:
        for i in range(days):
            data.append({
                "symbol": sym, "exchange": exchange,
                "date": f"2025{(i // 28) + 1:02d}{(i % 28) + 1:02d}",
                "close": base + trend * i,
            })
    return data


class TestMomentumRankPlugin:
    """MomentumRank 플러그인 테스트"""

    @pytest.fixture
    def multi_data(self):
        """다종목 데이터 (5종목, 다른 모멘텀)"""
        return _make_multi_symbol_data([
            ("AAPL", "NASDAQ", 100, 1.0),   # 강한 상승
            ("MSFT", "NASDAQ", 200, 0.5),   # 중간 상승
            ("GOOG", "NASDAQ", 150, 0.2),   # 약한 상승
            ("TSLA", "NASDAQ", 300, -0.3),  # 약한 하락
            ("AMZN", "NASDAQ", 180, -1.0),  # 강한 하락
        ])

    def test_calculate_momentum_simple(self):
        """단순 모멘텀"""
        prices = [100, 110]
        m = _calculate_momentum(prices, "simple")
        assert m == pytest.approx(10.0)

    def test_calculate_momentum_log(self):
        """로그 모멘텀"""
        prices = [100, 110]
        m = _calculate_momentum(prices, "log")
        assert m is not None and m > 0

    def test_calculate_momentum_risk_adjusted(self):
        """위험조정 모멘텀"""
        prices = list(range(100, 120))
        m = _calculate_momentum(prices, "risk_adjusted")
        assert m is not None

    def test_calculate_momentum_insufficient(self):
        """데이터 부족"""
        m = _calculate_momentum([100], "simple")
        assert m is None

    def test_calculate_momentum_exclude_recent(self):
        """최근 N일 제외"""
        prices = [100, 105, 110, 90]  # 마지막 급락
        m_with = _calculate_momentum(prices, "simple", exclude_recent=0)
        m_without = _calculate_momentum(prices, "simple", exclude_recent=1)
        assert m_with is not None and m_without is not None
        assert m_without > m_with  # 급락 제외하면 모멘텀 더 높음

    @pytest.mark.asyncio
    async def test_top_n_selection(self, multi_data):
        """상위 N개 선별"""
        result = await momentum_rank_condition(
            data=multi_data,
            fields={"lookback": 63, "top_n": 2, "selection": "top", "momentum_type": "simple"},
        )
        assert len(result["passed_symbols"]) == 2
        passed_syms = {s["symbol"] for s in result["passed_symbols"]}
        assert "AAPL" in passed_syms  # 가장 높은 모멘텀

    @pytest.mark.asyncio
    async def test_bottom_selection(self, multi_data):
        """하위 N개 선별"""
        result = await momentum_rank_condition(
            data=multi_data,
            fields={"lookback": 63, "top_n": 2, "selection": "bottom"},
        )
        assert len(result["passed_symbols"]) == 2
        passed_syms = {s["symbol"] for s in result["passed_symbols"]}
        assert "AMZN" in passed_syms  # 가장 낮은 모멘텀

    @pytest.mark.asyncio
    async def test_top_pct_selection(self, multi_data):
        """상위 N% 선별"""
        result = await momentum_rank_condition(
            data=multi_data,
            fields={"lookback": 63, "top_n": 0, "top_pct": 40, "selection": "top"},
        )
        # 5종목의 40% = 2종목
        assert len(result["passed_symbols"]) == 2

    @pytest.mark.asyncio
    async def test_rank_in_results(self, multi_data):
        """순위 정보 포함"""
        result = await momentum_rank_condition(
            data=multi_data,
            fields={"lookback": 63, "top_n": 5, "selection": "top"},
        )
        ranked = [sr for sr in result["symbol_results"] if "rank" in sr]
        assert len(ranked) == 5

    @pytest.mark.asyncio
    async def test_empty_data(self):
        """빈 데이터"""
        result = await momentum_rank_condition(data=[], fields={})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_analysis_output(self, multi_data):
        """분석 결과 포맷"""
        result = await momentum_rank_condition(
            data=multi_data,
            fields={"lookback": 63, "top_n": 2},
        )
        assert result["analysis"]["indicator"] == "MomentumRank"
        assert result["analysis"]["total_symbols"] == 5
        assert result["analysis"]["selected_count"] == 2

    def test_schema(self):
        """스키마 검증"""
        assert MOMENTUM_RANK_SCHEMA.id == "MomentumRank"
        assert "lookback" in MOMENTUM_RANK_SCHEMA.fields_schema
        assert "top_n" in MOMENTUM_RANK_SCHEMA.fields_schema
        assert "selection" in MOMENTUM_RANK_SCHEMA.fields_schema
        assert "momentum_type" in MOMENTUM_RANK_SCHEMA.fields_schema


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
