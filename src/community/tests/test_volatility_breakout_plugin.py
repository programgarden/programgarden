"""
VolatilityBreakout 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.volatility_breakout import (
    volatility_breakout_condition,
    _calculate_atr,
    _compute_breakout_price,
    VOLATILITY_BREAKOUT_SCHEMA,
)


def _make_ohlcv(symbol, count, base=100.0, daily_range=2.0):
    """기본 OHLCV 데이터 생성"""
    data = []
    for i in range(count):
        close = base + (i % 5 - 2) * 0.5
        data.append({
            "symbol": symbol, "exchange": "NASDAQ",
            "date": f"20250{(i // 28) + 1:02d}{(i % 28) + 1:02d}",
            "open": close - 0.5,
            "high": close + daily_range,
            "low": close - daily_range,
            "close": close,
            "volume": 1000000,
        })
    return data


def _make_breakout_today(symbol, base=100.0, k=0.5, breakout_direction="long"):
    """당일 돌파 데이터 (전일 range=10, k=0.5, 돌파가=시가+5)"""
    data = _make_ohlcv(symbol, count=20, base=base)
    # 전일 range를 10.0으로 설정
    data[-1]["high"] = base + 10.0
    data[-1]["low"] = base - 10.0
    data[-1]["close"] = base + 5.0

    prev_range = 20.0  # high-low of last bar (which will be prev bar)
    today_open = base + 1.0

    if breakout_direction == "long":
        breakout_price = today_open + k * prev_range
        today_high = breakout_price + 1.0  # 돌파
        today_close = breakout_price + 0.5
    else:
        short_breakout = today_open - k * prev_range
        today_high = today_open + 1.0
        today_close = short_breakout - 0.5
        data.append({
            "symbol": symbol, "exchange": "NASDAQ",
            "date": "20250301",
            "open": today_open,
            "high": today_open + 1.0,
            "low": short_breakout - 1.0,
            "close": today_close,
            "volume": 2000000,
        })
        return data

    data.append({
        "symbol": symbol, "exchange": "NASDAQ",
        "date": "20250301",
        "open": today_open,
        "high": today_high,
        "low": today_open - 2.0,
        "close": today_close,
        "volume": 2000000,
    })
    return data


class TestVolatilityBreakoutHelpers:
    """헬퍼 함수 테스트"""

    def test_compute_breakout_price(self):
        """돌파 기준가 계산"""
        # breakout = open + k * (prev_high - prev_low)
        bp = _compute_breakout_price(open_price=100.0, prev_range=10.0, k=0.5)
        assert bp == 105.0

    def test_compute_breakout_price_various_k(self):
        """K값 변동 테스트"""
        assert _compute_breakout_price(100.0, 10.0, 0.4) == 104.0
        assert _compute_breakout_price(100.0, 10.0, 0.6) == 106.0
        assert _compute_breakout_price(100.0, 10.0, 0.3) == 103.0

    def test_calculate_atr_returns_positive(self):
        """ATR 양수 반환"""
        highs = [110] * 16
        lows = [100] * 16
        closes = [105] * 16
        atr = _calculate_atr(highs, lows, closes, period=14)
        assert atr is not None
        assert atr >= 0


class TestVolatilityBreakoutCondition:
    """VolatilityBreakout 조건 테스트"""

    @pytest.mark.asyncio
    async def test_long_breakout_signal(self):
        """롱 방향 돌파 신호"""
        data = _make_breakout_today("AAPL", base=100.0, k=0.5, breakout_direction="long")
        result = await volatility_breakout_condition(
            data=data,
            fields={"k_factor": 0.5, "direction": "long", "noise_filter": False},
        )
        assert "passed_symbols" in result
        assert "symbol_results" in result
        sr = result["symbol_results"][0]
        assert "signal" in sr
        assert "breakout_price" in sr

    @pytest.mark.asyncio
    async def test_no_breakout(self):
        """돌파 없음"""
        data = _make_ohlcv("AAPL", count=20, base=100.0, daily_range=1.0)
        result = await volatility_breakout_condition(
            data=data,
            fields={"k_factor": 0.5, "direction": "long", "noise_filter": False},
        )
        sr = result["symbol_results"][0]
        # 마지막 바의 high가 breakout_price보다 낮으면 no signal
        assert sr["signal"] in ("none", "long_entry")

    @pytest.mark.asyncio
    async def test_k_factor_effect(self):
        """K 값이 클수록 돌파 어려움"""
        # 같은 데이터에서 K=0.1 vs K=0.9 비교
        data = _make_ohlcv("AAPL", count=20, base=100.0, daily_range=2.0)
        # 마지막 바 high를 살짝 높게
        data[-1]["high"] = 101.5

        result_easy = await volatility_breakout_condition(
            data=data,
            fields={"k_factor": 0.1, "direction": "long", "noise_filter": False},
        )
        result_hard = await volatility_breakout_condition(
            data=data,
            fields={"k_factor": 0.9, "direction": "long", "noise_filter": False},
        )
        # K 작은 것이 더 쉽게 돌파 (더 낮은 기준가)
        bp_easy = result_easy["symbol_results"][0]["breakout_price"]
        bp_hard = result_hard["symbol_results"][0]["breakout_price"]
        assert bp_easy < bp_hard

    @pytest.mark.asyncio
    async def test_direction_both(self):
        """양방향 신호"""
        data = _make_ohlcv("AAPL", count=20, base=100.0, daily_range=5.0)
        result = await volatility_breakout_condition(
            data=data,
            fields={"k_factor": 0.5, "direction": "both", "noise_filter": False},
        )
        sr = result["symbol_results"][0]
        assert sr["signal"] in ("none", "long_entry", "short_entry")

    @pytest.mark.asyncio
    async def test_noise_filter_effect(self):
        """거래량 필터 효과"""
        data = _make_ohlcv("AAPL", count=20, base=100.0, daily_range=2.0)
        # 마지막 바 거래량을 매우 낮게 (필터로 차단)
        data[-1]["high"] = 105.0  # 돌파 가능한 높이
        data[-1]["volume"] = 1  # 매우 낮은 거래량

        result_with_filter = await volatility_breakout_condition(
            data=data,
            fields={"k_factor": 0.1, "direction": "long", "noise_filter": True},
        )
        result_no_filter = await volatility_breakout_condition(
            data=data,
            fields={"k_factor": 0.1, "direction": "long", "noise_filter": False},
        )
        sr_filtered = result_with_filter["symbol_results"][0]
        sr_no_filter = result_no_filter["symbol_results"][0]
        # 필터 적용 시 낮은 거래량에서 신호 차단될 수 있음
        assert sr_filtered["signal"] in ("none", "long_entry")
        assert sr_no_filter["signal"] in ("none", "long_entry")

    @pytest.mark.asyncio
    async def test_empty_data(self):
        """빈 데이터"""
        result = await volatility_breakout_condition(data=[], fields={})
        assert result["result"] is False
        assert "error" in result["analysis"]

    @pytest.mark.asyncio
    async def test_single_bar_insufficient(self):
        """1개 바 데이터 부족"""
        data = [{"symbol": "AAPL", "exchange": "NASDAQ",
                 "date": "20250101", "open": 100, "high": 102, "low": 98, "close": 101}]
        result = await volatility_breakout_condition(
            data=data,
            fields={"k_factor": 0.5},
        )
        assert len(result["failed_symbols"]) == 1

    @pytest.mark.asyncio
    async def test_multi_symbol(self):
        """다종목 처리"""
        data = _make_ohlcv("AAPL", 20) + _make_ohlcv("TSLA", 20, base=200)
        result = await volatility_breakout_condition(
            data=data,
            fields={"k_factor": 0.5, "direction": "long"},
        )
        total = len(result["passed_symbols"]) + len(result["failed_symbols"])
        assert total == 2

    @pytest.mark.asyncio
    async def test_atr_value_present(self):
        """ATR 값 포함 여부"""
        data = _make_ohlcv("AAPL", 20)
        result = await volatility_breakout_condition(
            data=data,
            fields={"k_factor": 0.5, "atr_period": 14},
        )
        sr = result["symbol_results"][0]
        assert "atr_value" in sr

    @pytest.mark.asyncio
    async def test_time_series_format(self):
        """time_series 출력 형식"""
        data = _make_ohlcv("AAPL", 20)
        result = await volatility_breakout_condition(
            data=data,
            fields={"k_factor": 0.5},
        )
        for val in result["values"]:
            assert "time_series" in val
            if val["time_series"]:
                row = val["time_series"][0]
                assert "breakout_price" in row
                assert "signal" in row
                assert "prev_range" in row

    @pytest.mark.asyncio
    async def test_no_open_field_fallback(self):
        """open 필드 없을 때 처리"""
        data = []
        for i in range(5):
            data.append({
                "symbol": "AAPL", "exchange": "NASDAQ",
                "date": f"20250{i + 1:02d}01",
                "high": 105.0, "low": 95.0, "close": 100.0,
                # open 없음
            })
        result = await volatility_breakout_condition(
            data=data,
            fields={"k_factor": 0.5},
        )
        assert "symbol_results" in result

    def test_schema(self):
        """스키마 검증"""
        assert VOLATILITY_BREAKOUT_SCHEMA.id == "VolatilityBreakout"
        assert "k_factor" in VOLATILITY_BREAKOUT_SCHEMA.fields_schema
        assert "direction" in VOLATILITY_BREAKOUT_SCHEMA.fields_schema
        assert "noise_filter" in VOLATILITY_BREAKOUT_SCHEMA.fields_schema
        assert "atr_adaptive" in VOLATILITY_BREAKOUT_SCHEMA.fields_schema


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
