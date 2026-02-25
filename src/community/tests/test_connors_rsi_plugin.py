"""
ConnorsRSI 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.connors_rsi import (
    connors_rsi_condition,
    calculate_connors_rsi,
    _calc_rsi,
    _calc_streak,
    _calc_percentile_rank,
    CONNORS_RSI_SCHEMA,
)


def _make_data(symbol: str, n: int, base: float = 100.0, trend: float = 0.0) -> list:
    data = []
    price = base
    for i in range(n):
        data.append({
            "symbol": symbol,
            "exchange": "NASDAQ",
            "date": f"2024{(i // 30 + 1):02d}{(i % 30 + 1):02d}",
            "close": round(price, 2),
        })
        price += trend
    return data


def _make_oversold_data(n_stable: int = 110, n_drop: int = 5) -> list:
    """과매도 조건 데이터 생성 (안정 후 급락)"""
    data = []
    price = 100.0
    for i in range(n_stable):
        data.append({
            "symbol": "AAPL", "exchange": "NASDAQ",
            "date": f"2024{(i // 28 + 1):02d}{(i % 28 + 1):02d}",
            "close": price + (i % 2) * 0.1,
        })
    # 급락
    for j in range(n_drop):
        data.append({
            "symbol": "AAPL", "exchange": "NASDAQ",
            "date": f"202504{j + 1:02d}",
            "close": price - (j + 1) * 2.0,
        })
    return data


class TestConnorsRSIComponents:
    """컴포넌트 개별 테스트"""

    def test_calc_rsi_basic(self):
        """RSI 기본 계산"""
        closes = [100.0] * 10 + [101.0]
        rsi = _calc_rsi(closes, period=3)
        assert rsi is not None
        assert 0 <= rsi <= 100

    def test_calc_rsi_all_gains(self):
        """순수 상승 → RSI 100"""
        closes = [100.0 + i for i in range(10)]
        rsi = _calc_rsi(closes, period=3)
        assert rsi == 100.0

    def test_calc_rsi_all_losses(self):
        """순수 하락 → RSI 0"""
        closes = [100.0 - i for i in range(10)]
        rsi = _calc_rsi(closes, period=3)
        assert rsi == 0.0

    def test_calc_streak_consecutive_up(self):
        """연속 상승 streak"""
        closes = [100.0, 101.0, 102.0, 103.0]
        streak = _calc_streak(closes)
        assert streak == 3

    def test_calc_streak_consecutive_down(self):
        """연속 하락 streak"""
        closes = [103.0, 102.0, 101.0, 100.0]
        streak = _calc_streak(closes)
        assert streak == -3

    def test_calc_streak_mixed(self):
        """상승 후 하락 → 현재 streak은 하락분만"""
        closes = [100.0, 101.0, 102.0, 101.0]
        streak = _calc_streak(closes)
        assert streak == -1

    def test_calc_percentile_rank(self):
        """백분위 순위 계산"""
        returns = [0.01, 0.02, 0.03, -0.01, -0.02, -0.05]
        rank = _calc_percentile_rank(returns)
        assert 0.0 <= rank <= 100.0

    def test_calc_percentile_rank_lowest(self):
        """최저 수익률 → 낮은 백분위"""
        returns = [0.01, 0.02, 0.03, 0.04, -0.10]
        rank = _calc_percentile_rank(returns)
        assert rank < 25.0  # 최저이므로 낮은 백분위


class TestConnorsRSICalculation:
    """calculate_connors_rsi 테스트"""

    def test_connors_rsi_range(self):
        """ConnorsRSI는 0~100 범위"""
        import random
        random.seed(42)
        closes = [100.0]
        for _ in range(120):
            closes.append(closes[-1] * (1 + random.uniform(-0.02, 0.02)))
        result = calculate_connors_rsi(closes, rsi_period=3, streak_period=2, pct_rank_period=100)
        if result:
            assert 0.0 <= result["connors_rsi"] <= 100.0

    def test_connors_rsi_components_present(self):
        """3개 컴포넌트 모두 반환"""
        closes = [100.0 + i * 0.1 for i in range(120)]
        result = calculate_connors_rsi(closes, rsi_period=3, streak_period=2, pct_rank_period=100)
        if result:
            assert "rsi_component" in result
            assert "streak_rsi_component" in result
            assert "pct_rank_component" in result
            assert "connors_rsi" in result

    def test_connors_rsi_insufficient(self):
        """데이터 부족 → None"""
        result = calculate_connors_rsi([100.0] * 10, rsi_period=3, streak_period=2, pct_rank_period=100)
        assert result is None

    def test_connors_rsi_average(self):
        """ConnorsRSI = (RSI + StreakRSI + PctRank) / 3"""
        closes = [100.0 + i * 0.1 for i in range(120)]
        result = calculate_connors_rsi(closes, rsi_period=3, streak_period=2, pct_rank_period=100)
        if result:
            expected = (result["rsi_component"] + result["streak_rsi_component"] + result["pct_rank_component"]) / 3.0
            assert abs(result["connors_rsi"] - expected) < 0.01


class TestConnorsRSICondition:
    """connors_rsi_condition 통합 테스트"""

    @pytest.fixture
    def oversold_data(self):
        return _make_oversold_data()

    @pytest.fixture
    def multi_data(self):
        data1 = _make_data("AAPL", 130)
        data2 = _make_data("TSLA", 130, base=200.0)
        return data1 + data2

    @pytest.mark.asyncio
    async def test_empty_data(self):
        """빈 데이터 처리"""
        result = await connors_rsi_condition(data=[], fields={})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_insufficient_data(self):
        """데이터 부족"""
        data = _make_data("AAPL", 20)
        result = await connors_rsi_condition(
            data=data,
            fields={"rsi_period": 3, "streak_period": 2, "pct_rank_period": 100},
        )
        assert len(result["failed_symbols"]) == 1

    @pytest.mark.asyncio
    async def test_output_format(self, multi_data):
        """출력 형식 검증"""
        result = await connors_rsi_condition(
            data=multi_data,
            fields={"rsi_period": 3, "streak_period": 2, "pct_rank_period": 100},
        )
        assert "passed_symbols" in result
        assert "failed_symbols" in result
        assert "symbol_results" in result
        assert "values" in result

    @pytest.mark.asyncio
    async def test_above_direction(self, multi_data):
        """above 방향: CRSI > (100 - threshold)"""
        result = await connors_rsi_condition(
            data=multi_data,
            fields={
                "rsi_period": 3, "streak_period": 2, "pct_rank_period": 100,
                "threshold": 10.0, "direction": "above",
            },
        )
        assert "result" in result

    @pytest.mark.asyncio
    async def test_symbol_results_components(self, multi_data):
        """symbol_results에 3개 컴포넌트 포함"""
        result = await connors_rsi_condition(
            data=multi_data,
            fields={"rsi_period": 3, "streak_period": 2, "pct_rank_period": 100},
        )
        for sr in result["symbol_results"]:
            if sr.get("connors_rsi") is not None:
                assert "rsi_component" in sr
                assert "streak_rsi_component" in sr
                assert "pct_rank_component" in sr

    @pytest.mark.asyncio
    async def test_multi_symbol_count(self, multi_data):
        """다종목: 2개 종목 처리"""
        result = await connors_rsi_condition(
            data=multi_data,
            fields={"rsi_period": 3, "streak_period": 2, "pct_rank_period": 100},
        )
        total = len(result["passed_symbols"]) + len(result["failed_symbols"])
        assert total == 2

    @pytest.mark.asyncio
    async def test_threshold_boundary(self, multi_data):
        """threshold=50 → 모든 종목이 어느 쪽에든 분류됨"""
        result = await connors_rsi_condition(
            data=multi_data,
            fields={
                "rsi_period": 3, "streak_period": 2, "pct_rank_period": 100,
                "threshold": 50.0, "direction": "below",
            },
        )
        total = len(result["passed_symbols"]) + len(result["failed_symbols"])
        assert total == 2

    def test_schema_validation(self):
        """스키마 검증"""
        assert CONNORS_RSI_SCHEMA.id == "ConnorsRSI"
        assert "rsi_period" in CONNORS_RSI_SCHEMA.fields_schema
        assert "streak_period" in CONNORS_RSI_SCHEMA.fields_schema
        assert "pct_rank_period" in CONNORS_RSI_SCHEMA.fields_schema
        assert "threshold" in CONNORS_RSI_SCHEMA.fields_schema
        assert "direction" in CONNORS_RSI_SCHEMA.fields_schema

    @pytest.mark.asyncio
    async def test_custom_parameters(self, multi_data):
        """커스텀 파라미터"""
        result = await connors_rsi_condition(
            data=multi_data,
            fields={
                "rsi_period": 5, "streak_period": 3, "pct_rank_period": 50,
                "threshold": 20.0, "direction": "below",
            },
        )
        total = len(result["passed_symbols"]) + len(result["failed_symbols"])
        assert total == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
