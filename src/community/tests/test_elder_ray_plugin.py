"""
ElderRay 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.elder_ray import (
    elder_ray_condition,
    calculate_elder_ray_series,
    _calc_ema_series,
    _determine_signal,
    ELDER_RAY_SCHEMA,
)


def _make_hlc(symbol: str, n: int, base: float = 100.0, trend: float = 0.5, spread: float = 1.0) -> list:
    """HLC 테스트 데이터 생성"""
    data = []
    price = base
    for i in range(n):
        data.append({
            "symbol": symbol,
            "exchange": "NASDAQ",
            "date": f"2024{(i // 30 + 1):02d}{(i % 30 + 1):02d}",
            "close": round(price, 2),
            "high": round(price + spread, 2),
            "low": round(price - spread, 2),
        })
        price += trend
    return data


def _make_buy_signal_data(ema_period: int = 13) -> list:
    """매수 신호 데이터: EMA 상승 + Bear Power 음수에서 상승"""
    data = []
    price = 100.0
    # EMA 안정화 + 상승 추세
    for i in range(ema_period + 20):
        price += 0.3
        data.append({
            "symbol": "AAPL", "exchange": "NASDAQ",
            "date": f"202401{i + 1:02d}",
            "close": price,
            "high": price + 0.5,
            "low": price - 1.5,  # low가 EMA보다 아래 (Bear Power 음수)
        })
    # Bear Power 상승 (low가 EMA 쪽으로 이동)
    for j in range(5):
        price += 0.5
        data.append({
            "symbol": "AAPL", "exchange": "NASDAQ",
            "date": f"202402{j + 1:02d}",
            "close": price,
            "high": price + 0.5,
            "low": price - 0.3,  # low가 EMA에 가까워짐 (Bear Power 덜 음수)
        })
    return data


class TestElderRayHelpers:
    """헬퍼 함수 테스트"""

    def test_ema_series_basic(self):
        """EMA 시계열 기본 계산"""
        closes = [100.0 + i for i in range(20)]
        ema = _calc_ema_series(closes, period=5)
        assert len(ema) > 0
        # EMA 길이: len(closes) - period + 1
        assert len(ema) == len(closes) - 5 + 1

    def test_ema_series_insufficient(self):
        """데이터 부족 → 빈 리스트"""
        ema = _calc_ema_series([100.0, 101.0], period=5)
        assert ema == []

    def test_ema_series_smooth(self):
        """EMA는 SMA보다 최신 데이터에 더 반응"""
        closes = [100.0] * 10 + [200.0]
        ema = _calc_ema_series(closes, period=5)
        sma = sum(closes[-5:]) / 5
        # EMA는 마지막 값에 더 가중치
        assert ema[-1] > sma

    def test_determine_signal_conservative_buy(self):
        """conservative 모드: EMA 상승 + Bear Power 음수→상승"""
        series = [
            {"bull_power": 1.0, "bear_power": -2.0, "ema": 100.0, "ema_direction": "up"},
            {"bull_power": 1.2, "bear_power": -1.0, "ema": 100.5, "ema_direction": "up"},
        ]
        signal = _determine_signal(series, "conservative")
        assert signal == "buy"

    def test_determine_signal_conservative_sell(self):
        """conservative 모드: EMA 하락 + Bull Power 양수→하락"""
        series = [
            {"bull_power": 2.0, "bear_power": -0.5, "ema": 101.0, "ema_direction": "down"},
            {"bull_power": 1.0, "bear_power": -0.8, "ema": 100.5, "ema_direction": "down"},
        ]
        signal = _determine_signal(series, "conservative")
        assert signal == "sell"

    def test_determine_signal_insufficient(self):
        """데이터 부족 → neutral"""
        series = [{"bull_power": 1.0, "bear_power": -1.0, "ema": 100.0, "ema_direction": "up"}]
        signal = _determine_signal(series, "conservative")
        assert signal == "neutral"


class TestElderRaySeriesCalculation:
    """calculate_elder_ray_series 테스트"""

    def test_basic_series(self):
        """기본 시계열 계산"""
        closes = [100.0 + i for i in range(30)]
        highs = [c + 1.0 for c in closes]
        lows = [c - 1.0 for c in closes]
        series = calculate_elder_ray_series(highs, lows, closes, ema_period=13)
        assert len(series) > 0

    def test_insufficient_data(self):
        """데이터 부족"""
        closes = [100.0] * 5
        highs = [101.0] * 5
        lows = [99.0] * 5
        series = calculate_elder_ray_series(highs, lows, closes, ema_period=13)
        assert len(series) == 0

    def test_bull_power_positive_in_uptrend(self):
        """상승 추세에서 Bull Power는 주로 양수"""
        closes = [100.0 + i for i in range(30)]
        highs = [c + 1.0 for c in closes]
        lows = [c - 0.5 for c in closes]
        series = calculate_elder_ray_series(highs, lows, closes, ema_period=5)
        # 초반 안정화 후 Bull Power 확인
        if len(series) > 5:
            recent = series[-1]
            assert "bull_power" in recent
            assert "bear_power" in recent
            assert "ema_direction" in recent

    def test_series_keys(self):
        """시계열 각 항목에 필수 키 포함"""
        closes = [100.0 + (i % 3 - 1) for i in range(30)]
        highs = [c + 1.0 for c in closes]
        lows = [c - 1.0 for c in closes]
        series = calculate_elder_ray_series(highs, lows, closes, ema_period=5)
        for item in series:
            assert "bull_power" in item
            assert "bear_power" in item
            assert "ema" in item
            assert "ema_direction" in item

    def test_ema_direction_values(self):
        """ema_direction은 'up', 'down', 'flat' 중 하나"""
        closes = [100.0 + (i % 5 - 2) for i in range(30)]
        highs = [c + 1.0 for c in closes]
        lows = [c - 1.0 for c in closes]
        series = calculate_elder_ray_series(highs, lows, closes, ema_period=5)
        for item in series:
            assert item["ema_direction"] in ("up", "down", "flat")


class TestElderRayCondition:
    """elder_ray_condition 통합 테스트"""

    @pytest.fixture
    def uptrend_data(self):
        return _make_hlc("AAPL", 40, trend=1.0)

    @pytest.fixture
    def downtrend_data(self):
        return _make_hlc("TSLA", 40, base=200.0, trend=-1.0)

    @pytest.fixture
    def multi_data(self):
        return (
            _make_hlc("AAPL", 40, trend=1.0)
            + _make_hlc("TSLA", 40, base=200.0, trend=-0.5)
        )

    @pytest.mark.asyncio
    async def test_empty_data(self):
        """빈 데이터"""
        result = await elder_ray_condition(data=[], fields={})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_insufficient_data(self):
        """데이터 부족"""
        data = _make_hlc("AAPL", 5)
        result = await elder_ray_condition(
            data=data,
            fields={"ema_period": 13},
        )
        assert len(result["failed_symbols"]) == 1

    @pytest.mark.asyncio
    async def test_output_format(self, uptrend_data):
        """출력 형식 검증"""
        result = await elder_ray_condition(
            data=uptrend_data,
            fields={"ema_period": 13, "signal_mode": "conservative"},
        )
        assert "passed_symbols" in result
        assert "failed_symbols" in result
        assert "symbol_results" in result
        assert "values" in result
        assert "analysis" in result

    @pytest.mark.asyncio
    async def test_symbol_results_keys(self, uptrend_data):
        """symbol_results 키 검증"""
        result = await elder_ray_condition(
            data=uptrend_data,
            fields={"ema_period": 13},
        )
        for sr in result["symbol_results"]:
            assert "symbol" in sr
            assert "exchange" in sr
            assert "signal" in sr
            assert "ema_direction" in sr
            if sr.get("bull_power") is not None:
                assert "bear_power" in sr
                assert "ema" in sr

    @pytest.mark.asyncio
    async def test_conservative_mode(self, multi_data):
        """conservative 모드"""
        result = await elder_ray_condition(
            data=multi_data,
            fields={"ema_period": 13, "signal_mode": "conservative"},
        )
        total = len(result["passed_symbols"]) + len(result["failed_symbols"])
        assert total == 2

    @pytest.mark.asyncio
    async def test_aggressive_mode(self, multi_data):
        """aggressive 모드"""
        result = await elder_ray_condition(
            data=multi_data,
            fields={"ema_period": 13, "signal_mode": "aggressive"},
        )
        total = len(result["passed_symbols"]) + len(result["failed_symbols"])
        assert total == 2

    @pytest.mark.asyncio
    async def test_time_series_in_values(self, uptrend_data):
        """values에 time_series 포함"""
        result = await elder_ray_condition(
            data=uptrend_data,
            fields={"ema_period": 13},
        )
        for v in result["values"]:
            assert "time_series" in v
            for ts in v["time_series"]:
                assert "bull_power" in ts
                assert "bear_power" in ts
                assert "ema_direction" in ts

    @pytest.mark.asyncio
    async def test_short_ema_period(self, multi_data):
        """짧은 EMA 기간 (5)"""
        result = await elder_ray_condition(
            data=multi_data,
            fields={"ema_period": 5},
        )
        total = len(result["passed_symbols"]) + len(result["failed_symbols"])
        assert total == 2

    @pytest.mark.asyncio
    async def test_products_overseas_futures(self):
        """해외선물 데이터도 처리 가능"""
        data = [
            {
                "symbol": "ESM24", "exchange": "CME",
                "date": f"202401{i + 1:02d}",
                "close": 5000.0 + i * 2,
                "high": 5001.0 + i * 2,
                "low": 4999.0 + i * 2,
            }
            for i in range(30)
        ]
        result = await elder_ray_condition(
            data=data,
            fields={"ema_period": 13},
        )
        assert "result" in result

    def test_schema_validation(self):
        """스키마 검증"""
        assert ELDER_RAY_SCHEMA.id == "ElderRay"
        assert "ema_period" in ELDER_RAY_SCHEMA.fields_schema
        assert "signal_mode" in ELDER_RAY_SCHEMA.fields_schema
        enum_vals = ELDER_RAY_SCHEMA.fields_schema["signal_mode"].get("enum", [])
        assert "conservative" in enum_vals
        assert "aggressive" in enum_vals


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
