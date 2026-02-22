"""
PairTrading (페어 트레이딩) 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.pair_trading import (
    pair_trading_condition,
    _pearson_correlation,
    _calculate_spread,
    PAIR_TRADING_SCHEMA,
    risk_features,
)


def _make_correlated_pair(days=70, correlation="high"):
    """상관 페어 데이터 생성"""
    data = []
    for i in range(days):
        close_a = 100 + i * 0.5 + (i % 3 - 1) * 0.3
        if correlation == "high":
            close_b = 200 + i * 1.0 + (i % 3 - 1) * 0.5
        elif correlation == "diverged":
            # 최근 스프레드 확대
            if i < days - 10:
                close_b = 200 + i * 1.0 + (i % 3 - 1) * 0.5
            else:
                close_b = 200 + i * 1.0 - (i - (days - 10)) * 3
        else:  # low
            close_b = 200 + (i % 7 - 3) * 5
        data.append({
            "symbol": "AAPL", "exchange": "NASDAQ",
            "date": f"2025{(i // 28) + 1:02d}{(i % 28) + 1:02d}",
            "close": close_a,
        })
        data.append({
            "symbol": "MSFT", "exchange": "NASDAQ",
            "date": f"2025{(i // 28) + 1:02d}{(i % 28) + 1:02d}",
            "close": close_b,
        })
    return data


class TestPairTradingPlugin:
    """PairTrading 플러그인 테스트"""

    @pytest.fixture
    def correlated_data(self):
        """높은 상관 페어"""
        return _make_correlated_pair(70, "high")

    @pytest.fixture
    def diverged_data(self):
        """스프레드 확대 페어"""
        return _make_correlated_pair(70, "diverged")

    @pytest.fixture
    def uncorrelated_data(self):
        """낮은 상관 페어"""
        return _make_correlated_pair(70, "low")

    def test_pearson_correlation(self):
        """피어슨 상관계수"""
        x = [1, 2, 3, 4, 5]
        y = [2, 4, 6, 8, 10]
        corr = _pearson_correlation(x, y)
        assert abs(corr - 1.0) < 0.001

    def test_pearson_negative(self):
        """음의 상관"""
        x = [1, 2, 3, 4, 5]
        y = [10, 8, 6, 4, 2]
        corr = _pearson_correlation(x, y)
        assert abs(corr - (-1.0)) < 0.001

    def test_calculate_spread_ratio(self):
        """스프레드 계산 - ratio"""
        sp = _calculate_spread(100, 200, "ratio")
        assert sp == pytest.approx(0.5)

    def test_calculate_spread_log_ratio(self):
        """스프레드 계산 - log_ratio"""
        sp = _calculate_spread(100, 100, "log_ratio")
        assert sp == pytest.approx(0.0)

    def test_calculate_spread_difference(self):
        """스프레드 계산 - difference"""
        sp = _calculate_spread(100, 200, "difference")
        assert sp == pytest.approx(-100.0)

    @pytest.mark.asyncio
    async def test_correlated_pair(self, correlated_data):
        """상관 높은 페어 분석"""
        result = await pair_trading_condition(
            data=correlated_data,
            fields={"symbol_a": "AAPL", "symbol_b": "MSFT", "lookback": 60},
        )
        assert "symbol_results" in result
        assert len(result["symbol_results"]) == 2
        assert result["symbol_results"][0]["correlation"] > 0.5

    @pytest.mark.asyncio
    async def test_auto_detect_symbols(self, correlated_data):
        """종목 자동 감지"""
        result = await pair_trading_condition(
            data=correlated_data,
            fields={"lookback": 60},  # symbol_a/b 미지정
        )
        assert "symbol_results" in result
        assert len(result["symbol_results"]) == 2

    @pytest.mark.asyncio
    async def test_low_correlation_rejected(self, uncorrelated_data):
        """낮은 상관 페어 거부"""
        result = await pair_trading_condition(
            data=uncorrelated_data,
            fields={"symbol_a": "AAPL", "symbol_b": "MSFT", "lookback": 60, "correlation_min": 0.8},
        )
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_empty_data(self):
        """빈 데이터"""
        result = await pair_trading_condition(data=[], fields={})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_analysis_output(self, correlated_data):
        """분석 결과 포맷"""
        result = await pair_trading_condition(
            data=correlated_data,
            fields={"symbol_a": "AAPL", "symbol_b": "MSFT", "lookback": 60},
        )
        assert result["analysis"]["indicator"] == "PairTrading"
        assert "z_score" in result["analysis"]
        assert "correlation" in result["analysis"]

    def test_risk_features(self):
        """risk_features 선언"""
        assert "state" in risk_features

    def test_schema(self):
        """스키마 검증"""
        assert PAIR_TRADING_SCHEMA.id == "PairTrading"
        assert "symbol_a" in PAIR_TRADING_SCHEMA.fields_schema
        assert "symbol_b" in PAIR_TRADING_SCHEMA.fields_schema
        assert "entry_z" in PAIR_TRADING_SCHEMA.fields_schema
        assert "spread_method" in PAIR_TRADING_SCHEMA.fields_schema


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
