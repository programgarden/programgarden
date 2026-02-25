"""
MFI (Money Flow Index) 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.mfi import (
    mfi_condition,
    calculate_mfi,
    calculate_mfi_series,
    MFI_SCHEMA,
)


def _make_hlcv(symbol: str, n: int, base: float = 100.0, trend: float = 0.0) -> list:
    """OHLCV 테스트 데이터 생성"""
    data = []
    price = base
    for i in range(n):
        data.append({
            "symbol": symbol,
            "exchange": "NASDAQ",
            "date": f"2024{(i // 30 + 1):02d}{(i % 30 + 1):02d}",
            "close": round(price, 2),
            "high": round(price + 1.0, 2),
            "low": round(price - 1.0, 2),
            "volume": 1000000,
        })
        price += trend
    return data


def _make_oversold_data() -> list:
    """과매도 데이터 (가격 하락 + 볼륨 증가)"""
    data = []
    price = 100.0
    # 안정 구간
    for i in range(20):
        data.append({
            "symbol": "AAPL", "exchange": "NASDAQ",
            "date": f"202401{i + 1:02d}",
            "close": price, "high": price + 0.5, "low": price - 0.5,
            "volume": 500000,
        })
    # 하락 구간 (낮은 typical price, 높은 volume → negative MF 증가)
    for j in range(15):
        fall_price = price - (j + 1) * 2
        data.append({
            "symbol": "AAPL", "exchange": "NASDAQ",
            "date": f"202402{j + 1:02d}",
            "close": fall_price, "high": fall_price + 0.5, "low": fall_price - 0.5,
            "volume": 2000000,
        })
    return data


class TestMFICalculation:
    """calculate_mfi 단위 테스트"""

    def test_basic_mfi_range(self):
        """MFI는 0~100 범위"""
        highs = [101.0] * 20
        lows = [99.0] * 20
        closes = [100.0] * 20
        vols = [1000000.0] * 20
        mfi = calculate_mfi(highs, lows, closes, vols, period=14)
        assert mfi is not None
        assert 0.0 <= mfi <= 100.0

    def test_all_positive_flow(self):
        """모든 flow가 양성 → MFI 100"""
        highs = [100.0 + i for i in range(20)]
        lows = [99.0 + i for i in range(20)]
        closes = [100.0 + i for i in range(20)]
        vols = [1000000.0] * 20
        mfi = calculate_mfi(highs, lows, closes, vols, period=14)
        assert mfi == 100.0

    def test_all_negative_flow(self):
        """모든 flow가 음성 → MFI 낮음"""
        n = 20
        highs = [100.0 - i for i in range(n)]
        lows = [99.0 - i for i in range(n)]
        closes = [100.0 - i for i in range(n)]
        vols = [1000000.0] * n
        mfi = calculate_mfi(highs, lows, closes, vols, period=14)
        assert mfi is not None
        assert mfi < 50.0

    def test_insufficient_data(self):
        """데이터 부족 → None"""
        highs = [101.0] * 5
        lows = [99.0] * 5
        closes = [100.0] * 5
        vols = [1000000.0] * 5
        mfi = calculate_mfi(highs, lows, closes, vols, period=14)
        assert mfi is None

    def test_no_volume_fallback(self):
        """volume 없음 → 1.0으로 가정 (RSI와 동일하게 동작)"""
        highs = [100.0 + i for i in range(20)]
        lows = [99.0 + i for i in range(20)]
        closes = [100.0 + i for i in range(20)]
        vols_empty: list = []  # 빈 리스트 → 1.0으로 대체
        mfi = calculate_mfi(highs, lows, closes, vols_empty, period=14)
        assert mfi is not None
        assert 0.0 <= mfi <= 100.0

    def test_mfi_series_length(self):
        """MFI 시계열 길이 검증"""
        n = 30
        highs = [100.0 + (i % 5) for i in range(n)]
        lows = [99.0 + (i % 5) for i in range(n)]
        closes = [100.0 + (i % 5) for i in range(n)]
        vols = [1000000.0] * n
        series = calculate_mfi_series(highs, lows, closes, vols, period=14)
        assert len(series) == n - 14  # period+1 이후부터 계산

    def test_mfi_series_range(self):
        """MFI 시계열 모든 값이 0~100 범위"""
        import random
        random.seed(42)
        n = 50
        closes = [100.0]
        for _ in range(n - 1):
            closes.append(closes[-1] * (1 + random.uniform(-0.02, 0.02)))
        highs = [c + 1.0 for c in closes]
        lows = [c - 1.0 for c in closes]
        vols = [1000000.0] * n
        series = calculate_mfi_series(highs, lows, closes, vols, period=14)
        for v in series:
            assert 0.0 <= v <= 100.0


class TestMFICondition:
    """mfi_condition 통합 테스트"""

    @pytest.fixture
    def oversold_data(self):
        return _make_oversold_data()

    @pytest.fixture
    def rising_data(self):
        return _make_hlcv("GOOG", 40, base=150.0, trend=2.0)

    @pytest.fixture
    def multi_data(self):
        return (
            _make_hlcv("AAPL", 30, base=100.0, trend=0.0)
            + _make_hlcv("TSLA", 30, base=200.0, trend=0.0)
        )

    @pytest.mark.asyncio
    async def test_empty_data(self):
        """빈 데이터"""
        result = await mfi_condition(data=[], fields={})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_insufficient_data(self):
        """데이터 부족"""
        data = _make_hlcv("AAPL", 5)
        result = await mfi_condition(data=data, fields={"period": 14})
        assert len(result["failed_symbols"]) == 1

    @pytest.mark.asyncio
    async def test_overbought_direction(self, rising_data):
        """상승 추세 → overbought 방향 테스트"""
        result = await mfi_condition(
            data=rising_data,
            fields={"period": 14, "overbought": 80.0, "oversold": 20.0, "direction": "above"},
        )
        assert "result" in result

    @pytest.mark.asyncio
    async def test_output_format(self, multi_data):
        """출력 형식 검증"""
        result = await mfi_condition(
            data=multi_data,
            fields={"period": 14, "direction": "below"},
        )
        assert "passed_symbols" in result
        assert "failed_symbols" in result
        assert "symbol_results" in result
        assert "values" in result
        assert "analysis" in result

        for sr in result["symbol_results"]:
            assert "symbol" in sr
            assert "exchange" in sr
            if sr.get("mfi") is not None:
                assert 0.0 <= sr["mfi"] <= 100.0

    @pytest.mark.asyncio
    async def test_multi_symbol(self, multi_data):
        """다종목 처리"""
        result = await mfi_condition(
            data=multi_data,
            fields={"period": 14},
        )
        total = len(result["passed_symbols"]) + len(result["failed_symbols"])
        assert total == 2

    @pytest.mark.asyncio
    async def test_time_series_in_values(self, rising_data):
        """values에 time_series 포함"""
        result = await mfi_condition(
            data=rising_data,
            fields={"period": 14},
        )
        for v in result["values"]:
            assert "time_series" in v

    @pytest.mark.asyncio
    async def test_short_period(self, multi_data):
        """짧은 기간 (period=2)"""
        result = await mfi_condition(
            data=multi_data,
            fields={"period": 2},
        )
        total = len(result["passed_symbols"]) + len(result["failed_symbols"])
        assert total == 2

    @pytest.mark.asyncio
    async def test_no_volume_field(self):
        """volume 필드 없는 데이터"""
        data = []
        for i in range(30):
            data.append({
                "symbol": "AAPL", "exchange": "NASDAQ",
                "date": f"2024010{i % 9 + 1}",
                "close": 100.0 + i,
                "high": 101.0 + i,
                "low": 99.0 + i,
                # volume 필드 없음
            })
        result = await mfi_condition(data=data, fields={"period": 14})
        assert "result" in result

    def test_schema_validation(self):
        """스키마 검증"""
        assert MFI_SCHEMA.id == "MFI"
        assert "period" in MFI_SCHEMA.fields_schema
        assert "overbought" in MFI_SCHEMA.fields_schema
        assert "oversold" in MFI_SCHEMA.fields_schema
        assert "direction" in MFI_SCHEMA.fields_schema


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
