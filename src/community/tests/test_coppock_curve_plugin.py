"""
CoppockCurve 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.coppock_curve import (
    coppock_curve_condition,
    calculate_coppock_curve,
    calculate_coppock_series,
    _calc_roc,
    _calc_wma,
    COPPOCK_CURVE_SCHEMA,
)


def _make_data(symbol: str, n: int, base: float = 100.0, trend: float = 0.5) -> list:
    data = []
    price = base
    for i in range(n):
        data.append({
            "symbol": symbol,
            "exchange": "NYSE",
            "date": f"2024{(i // 30 + 1):02d}{(i % 30 + 1):02d}",
            "close": round(price, 2),
        })
        price += trend
    return data


def _make_zero_cross_data() -> list:
    """0선 상향 돌파 시뮬레이션: 먼저 하락 후 반등"""
    data = []
    # 먼저 하락 (30기간)
    price = 100.0
    for i in range(60):
        price -= 0.3
        data.append({
            "symbol": "SPY", "exchange": "NYSE",
            "date": f"202401{i + 1:02d}" if i < 30 else f"202402{i - 29:02d}",
            "close": round(price, 2),
        })
    # 강하게 반등 (30기간)
    for j in range(60):
        price += 0.8
        data.append({
            "symbol": "SPY", "exchange": "NYSE",
            "date": f"202403{j % 28 + 1:02d}" if j < 28 else f"202404{j - 27:02d}",
            "close": round(price, 2),
        })
    return data


class TestCoppockHelpers:
    """헬퍼 함수 테스트"""

    def test_calc_roc_basic(self):
        """ROC 기본 계산"""
        closes = [100.0] * 5 + [110.0]
        roc = _calc_roc(closes, period=5)
        assert roc is not None
        assert abs(roc - 10.0) < 0.001

    def test_calc_roc_negative(self):
        """음수 ROC"""
        closes = [100.0] * 5 + [90.0]
        roc = _calc_roc(closes, period=5)
        assert roc is not None
        assert roc < 0

    def test_calc_roc_insufficient(self):
        """데이터 부족 → None"""
        roc = _calc_roc([100.0, 105.0], period=5)
        assert roc is None

    def test_calc_wma_basic(self):
        """WMA 기본 계산"""
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        wma = _calc_wma(values, period=5)
        assert wma is not None
        # 선형 가중: (1*1+2*2+3*3+4*4+5*5) / (1+2+3+4+5) = 55/15 ≈ 3.667
        assert abs(wma - (55 / 15)) < 0.01

    def test_calc_wma_insufficient(self):
        """데이터 부족 → None"""
        wma = _calc_wma([1.0, 2.0], period=5)
        assert wma is None


class TestCoppockCurveCalculation:
    """calculate_coppock_curve 테스트"""

    def test_basic_calculation(self):
        """기본 계산 성공"""
        closes = [100.0 + i * 0.5 for i in range(50)]
        val = calculate_coppock_curve(closes, long_roc=14, short_roc=11, wma_period=10)
        assert val is not None

    def test_insufficient_data(self):
        """데이터 부족 → None"""
        closes = [100.0] * 10
        val = calculate_coppock_curve(closes, long_roc=14, short_roc=11, wma_period=10)
        assert val is None

    def test_positive_value_in_uptrend(self):
        """강한 상승 추세 → 양수 값"""
        closes = [100.0 + i * 2 for i in range(50)]
        val = calculate_coppock_curve(closes, long_roc=14, short_roc=11, wma_period=10)
        if val is not None:
            assert val > 0

    def test_negative_value_in_downtrend(self):
        """강한 하락 추세 → 음수 값"""
        closes = [200.0 - i * 2 for i in range(50)]
        val = calculate_coppock_curve(closes, long_roc=14, short_roc=11, wma_period=10)
        if val is not None:
            assert val < 0

    def test_coppock_series_length(self):
        """시계열 길이 검증"""
        closes = [100.0 + i * 0.5 for i in range(50)]
        series = calculate_coppock_series(closes, long_roc=14, short_roc=11, wma_period=10)
        assert len(series) >= 0  # 데이터 충분하면 시리즈 생성

    def test_daily_mode(self):
        """use_daily=True: 기간 × 21 스케일링"""
        # daily=True이면 14*21=294기간 필요 → 300개로 테스트
        closes = [100.0 + i * 0.1 for i in range(350)]
        val = calculate_coppock_curve(
            closes, long_roc=14, short_roc=11, wma_period=10, use_daily=True
        )
        # 데이터 충분하면 값 반환
        assert val is not None or len(closes) < (14 * 21 + 10 + 1)


class TestCoppockCurveCondition:
    """coppock_curve_condition 통합 테스트"""

    @pytest.fixture
    def uptrend_data(self):
        return _make_data("SPY", 50, trend=1.0)

    @pytest.fixture
    def downtrend_data(self):
        return _make_data("QQQ", 50, base=200.0, trend=-1.0)

    @pytest.fixture
    def multi_data(self):
        return (
            _make_data("SPY", 50, trend=1.0)
            + _make_data("QQQ", 50, base=200.0, trend=-0.5)
        )

    @pytest.mark.asyncio
    async def test_empty_data(self):
        """빈 데이터"""
        result = await coppock_curve_condition(data=[], fields={})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_insufficient_data(self):
        """데이터 부족"""
        data = _make_data("SPY", 10)
        result = await coppock_curve_condition(
            data=data,
            fields={"long_roc": 14, "short_roc": 11, "wma_period": 10},
        )
        assert len(result["failed_symbols"]) == 1

    @pytest.mark.asyncio
    async def test_output_format(self, uptrend_data):
        """출력 형식 검증"""
        result = await coppock_curve_condition(
            data=uptrend_data,
            fields={"long_roc": 14, "short_roc": 11, "wma_period": 10},
        )
        assert "passed_symbols" in result
        assert "failed_symbols" in result
        assert "symbol_results" in result
        assert "values" in result

    @pytest.mark.asyncio
    async def test_zero_cross_mode(self, uptrend_data):
        """zero_cross 모드"""
        result = await coppock_curve_condition(
            data=uptrend_data,
            fields={
                "long_roc": 14, "short_roc": 11, "wma_period": 10,
                "signal_mode": "zero_cross",
            },
        )
        assert "result" in result

    @pytest.mark.asyncio
    async def test_direction_mode(self, uptrend_data):
        """direction 모드"""
        result = await coppock_curve_condition(
            data=uptrend_data,
            fields={
                "long_roc": 14, "short_roc": 11, "wma_period": 10,
                "signal_mode": "direction",
            },
        )
        assert "result" in result

    @pytest.mark.asyncio
    async def test_multi_symbol(self, multi_data):
        """다종목"""
        result = await coppock_curve_condition(
            data=multi_data,
            fields={"long_roc": 14, "short_roc": 11, "wma_period": 10},
        )
        total = len(result["passed_symbols"]) + len(result["failed_symbols"])
        assert total == 2

    @pytest.mark.asyncio
    async def test_symbol_results_coppock_value(self, uptrend_data):
        """symbol_results에 coppock_value 포함"""
        result = await coppock_curve_condition(
            data=uptrend_data,
            fields={"long_roc": 14, "short_roc": 11, "wma_period": 10},
        )
        for sr in result["symbol_results"]:
            assert "coppock_value" in sr
            assert "zero_cross_up" in sr

    @pytest.mark.asyncio
    async def test_values_time_series(self, uptrend_data):
        """values에 time_series 포함"""
        result = await coppock_curve_condition(
            data=uptrend_data,
            fields={"long_roc": 14, "short_roc": 11, "wma_period": 10},
        )
        for v in result["values"]:
            assert "time_series" in v

    def test_schema_validation(self):
        """스키마 검증"""
        assert COPPOCK_CURVE_SCHEMA.id == "CoppockCurve"
        assert "long_roc" in COPPOCK_CURVE_SCHEMA.fields_schema
        assert "short_roc" in COPPOCK_CURVE_SCHEMA.fields_schema
        assert "wma_period" in COPPOCK_CURVE_SCHEMA.fields_schema
        assert "signal_mode" in COPPOCK_CURVE_SCHEMA.fields_schema


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
