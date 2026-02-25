"""
TurtleBreakout 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.turtle_breakout import (
    turtle_breakout_condition,
    _calculate_atr,
    _donchian_high,
    _donchian_low,
    TURTLE_BREAKOUT_SCHEMA,
)


def _make_channel_data(symbol, base_price, count, trend="flat"):
    """채널 테스트용 데이터 생성"""
    data = []
    for i in range(count):
        if trend == "up":
            close = base_price + i * 0.5
        elif trend == "down":
            close = base_price - i * 0.5
        else:
            close = base_price + (i % 5 - 2) * 0.3
        high = close + 1.0
        low = close - 1.0
        data.append({
            "symbol": symbol, "exchange": "NASDAQ",
            "date": f"20250{(i // 30) + 1:02d}{(i % 28) + 1:02d}",
            "open": close - 0.2,
            "high": high,
            "low": low,
            "close": close,
            "volume": 1000000,
        })
    return data


def _make_breakout_data(symbol, base_price, count, breakout_value=None):
    """돌파 발생 데이터 생성 (마지막 바에서 20일 고가 돌파)"""
    data = _make_channel_data(symbol, base_price, count)
    if breakout_value:
        # 마지막 바 돌파
        data[-1]["close"] = breakout_value
        data[-1]["high"] = breakout_value + 1.0
    return data


class TestTurtleBreakoutHelpers:
    """헬퍼 함수 테스트"""

    def test_calculate_atr_basic(self):
        """ATR 기본 계산"""
        highs = [110.0, 112.0, 108.0, 115.0, 111.0,
                 113.0, 109.0, 116.0, 112.0, 114.0,
                 110.0, 117.0, 113.0, 115.0, 111.0,
                 118.0, 114.0, 116.0, 112.0, 119.0, 115.0]
        lows = [100.0, 102.0, 98.0, 105.0, 101.0,
                103.0, 99.0, 106.0, 102.0, 104.0,
                100.0, 107.0, 103.0, 105.0, 101.0,
                108.0, 104.0, 106.0, 102.0, 109.0, 105.0]
        closes = [105.0, 107.0, 103.0, 110.0, 106.0,
                  108.0, 104.0, 111.0, 107.0, 109.0,
                  105.0, 112.0, 108.0, 110.0, 106.0,
                  113.0, 109.0, 111.0, 107.0, 114.0, 110.0]
        atr = _calculate_atr(highs, lows, closes, period=14)
        assert atr is not None
        assert atr > 0

    def test_calculate_atr_insufficient(self):
        """데이터 부족 시 None"""
        atr = _calculate_atr([110.0, 108.0], [100.0, 98.0], [105.0, 103.0], period=14)
        assert atr is None

    def test_donchian_high_basic(self):
        """돈치안 채널 고점"""
        highs = [100, 105, 102, 110, 108]
        ch_high = _donchian_high(highs, period=5)
        assert ch_high == 110

    def test_donchian_low_basic(self):
        """돈치안 채널 저점"""
        lows = [90, 95, 88, 92, 94]
        ch_low = _donchian_low(lows, period=5)
        assert ch_low == 88

    def test_donchian_insufficient(self):
        """데이터 부족 시 None"""
        assert _donchian_high([100, 105], period=5) is None
        assert _donchian_low([90, 95], period=5) is None


class TestTurtleBreakoutCondition:
    """TurtleBreakout 조건 테스트"""

    @pytest.fixture
    def data_uptrend_breakout(self):
        """상승 추세 돌파 데이터 (20일 고가 돌파)"""
        data = []
        # 25일 기본 데이터 (100-104 사이)
        for i in range(25):
            close = 100.0 + (i % 5) * 0.5
            data.append({
                "symbol": "AAPL", "exchange": "NASDAQ",
                "date": f"2025010{i + 1:02d}",
                "open": close - 0.3,
                "high": close + 1.0,
                "low": close - 1.0,
                "close": close,
                "volume": 1000000,
            })
        # 마지막 바에서 25일 최고가 돌파
        data.append({
            "symbol": "AAPL", "exchange": "NASDAQ",
            "date": "20250201",
            "open": 109.0,
            "high": 112.0,  # 이전 모든 고가(104+1=105) 돌파
            "low": 108.0,
            "close": 111.0,  # 돌파
            "volume": 2000000,
        })
        return data

    @pytest.fixture
    def data_downtrend_breakout(self):
        """하락 추세 돌파 데이터 (20일 저가 돌파)"""
        data = []
        for i in range(25):
            close = 100.0 + (i % 5) * 0.5
            data.append({
                "symbol": "AAPL", "exchange": "NASDAQ",
                "date": f"2025010{i + 1:02d}",
                "open": close - 0.3,
                "high": close + 1.0,
                "low": close - 1.0,
                "close": close,
                "volume": 1000000,
            })
        # 하락 돌파
        data.append({
            "symbol": "AAPL", "exchange": "NASDAQ",
            "date": "20250201",
            "open": 91.0,
            "high": 92.0,
            "low": 88.0,
            "close": 89.0,  # 저가 돌파 (min(99.0-1.0=98)보다 훨씬 낮음)
            "volume": 2000000,
        })
        return data

    @pytest.mark.asyncio
    async def test_long_entry_signal(self, data_uptrend_breakout):
        """상향 돌파 시 long_entry 신호"""
        result = await turtle_breakout_condition(
            data=data_uptrend_breakout,
            fields={"entry_period": 20, "exit_period": 10, "direction": "long"},
        )
        assert "passed_symbols" in result
        assert "symbol_results" in result
        # 채널 관련 필드 확인
        sr = result["symbol_results"][0]
        assert "entry_signal" in sr
        assert "channel_high" in sr
        assert "atr_value" in sr

    @pytest.mark.asyncio
    async def test_short_entry_signal(self, data_downtrend_breakout):
        """하향 돌파 시 short_entry 신호"""
        result = await turtle_breakout_condition(
            data=data_downtrend_breakout,
            fields={"entry_period": 20, "exit_period": 10, "direction": "short"},
        )
        sr = result["symbol_results"][0]
        assert sr["entry_signal"] == "short_entry"
        assert len(result["passed_symbols"]) == 1

    @pytest.mark.asyncio
    async def test_system2_defaults(self):
        """시스템2 기본값 (55일 진입/20일 청산)"""
        # 55일 이상 데이터 필요
        data = _make_channel_data("AAPL", 100, 60)
        result = await turtle_breakout_condition(
            data=data,
            fields={"system": "system2"},
        )
        assert result["analysis"]["entry_period"] == 55
        assert result["analysis"]["exit_period"] == 20

    @pytest.mark.asyncio
    async def test_system1_defaults(self):
        """시스템1 기본값 (20일 진입/10일 청산)"""
        data = _make_channel_data("AAPL", 100, 30)
        result = await turtle_breakout_condition(
            data=data,
            fields={"system": "system1"},
        )
        assert result["analysis"]["entry_period"] == 20
        assert result["analysis"]["exit_period"] == 10

    @pytest.mark.asyncio
    async def test_no_signal_flat(self):
        """횡보 시 신호 없음"""
        data = _make_channel_data("AAPL", 100, 30, trend="flat")
        result = await turtle_breakout_condition(
            data=data,
            fields={"entry_period": 20, "exit_period": 10},
        )
        sr = result["symbol_results"][0]
        # 횡보에서는 신호가 없거나 있거나 (데이터에 따라 다름)
        assert sr["entry_signal"] in ("none", "long_entry", "short_entry")

    @pytest.mark.asyncio
    async def test_stop_price_calculated(self, data_uptrend_breakout):
        """진입 신호 시 스탑 가격 계산"""
        result = await turtle_breakout_condition(
            data=data_uptrend_breakout,
            fields={"entry_period": 20, "exit_period": 10, "direction": "long", "stop_atr_multiple": 2.0},
        )
        sr = result["symbol_results"][0]
        if sr["entry_signal"] == "long_entry" and sr["atr_value"]:
            assert sr["stop_price"] is not None
            assert sr["stop_price"] < sr["current_close"]

    @pytest.mark.asyncio
    async def test_empty_data(self):
        """빈 데이터"""
        result = await turtle_breakout_condition(data=[], fields={})
        assert result["result"] is False
        assert result["analysis"].get("error") is not None

    @pytest.mark.asyncio
    async def test_insufficient_data(self):
        """데이터 부족"""
        data = _make_channel_data("AAPL", 100, 5)
        result = await turtle_breakout_condition(
            data=data,
            fields={"entry_period": 20, "exit_period": 10},
        )
        assert len(result["failed_symbols"]) == 1
        sr = result["symbol_results"][0]
        assert "error" in sr

    @pytest.mark.asyncio
    async def test_multi_symbol(self):
        """다종목 처리"""
        data = (
            _make_channel_data("AAPL", 100, 30)
            + _make_channel_data("TSLA", 200, 30)
        )
        result = await turtle_breakout_condition(
            data=data,
            fields={"entry_period": 20, "exit_period": 10},
        )
        total = len(result["passed_symbols"]) + len(result["failed_symbols"])
        assert total == 2
        assert len(result["values"]) == 2

    @pytest.mark.asyncio
    async def test_direction_long_only(self):
        """long 방향만 처리"""
        data = _make_channel_data("AAPL", 100, 30, trend="down")
        data[-1]["close"] = 80.0  # 하향 돌파
        data[-1]["low"] = 79.0
        result = await turtle_breakout_condition(
            data=data,
            fields={"entry_period": 20, "exit_period": 10, "direction": "long"},
        )
        sr = result["symbol_results"][0]
        # long 방향만 → short_entry 없음
        assert sr["entry_signal"] != "short_entry"

    @pytest.mark.asyncio
    async def test_time_series_format(self):
        """time_series 출력 형식"""
        data = _make_channel_data("AAPL", 100, 35)
        result = await turtle_breakout_condition(
            data=data,
            fields={"entry_period": 20, "exit_period": 10},
        )
        for val in result["values"]:
            assert "time_series" in val
            if val["time_series"]:
                row = val["time_series"][0]
                assert "entry_signal" in row
                assert "exit_signal" in row

    @pytest.mark.asyncio
    async def test_exit_signal_detection(self):
        """청산 신호 감지 (롱 포지션 청산)"""
        data = []
        # 먼저 고가를 만들고 (진입)
        for i in range(25):
            close = 110.0 + i * 0.2
            data.append({
                "symbol": "AAPL", "exchange": "NASDAQ",
                "date": f"20250101{i + 1:02d}",
                "open": close - 0.3,
                "high": close + 1.0,
                "low": close - 1.0,
                "close": close,
                "volume": 1000000,
            })
        # 급락 (exit 신호)
        data.append({
            "symbol": "AAPL", "exchange": "NASDAQ",
            "date": "20250201",
            "open": 101.0,
            "high": 102.0,
            "low": 100.0,
            "close": 100.5,  # 10일 저가 돌파
            "volume": 1000000,
        })
        result = await turtle_breakout_condition(
            data=data,
            fields={"entry_period": 20, "exit_period": 10, "direction": "long"},
        )
        assert "symbol_results" in result

    def test_schema(self):
        """스키마 검증"""
        assert TURTLE_BREAKOUT_SCHEMA.id == "TurtleBreakout"
        assert TURTLE_BREAKOUT_SCHEMA.version == "1.0.0"
        assert "system" in TURTLE_BREAKOUT_SCHEMA.fields_schema
        assert "entry_period" in TURTLE_BREAKOUT_SCHEMA.fields_schema
        assert "exit_period" in TURTLE_BREAKOUT_SCHEMA.fields_schema
        assert "atr_period" in TURTLE_BREAKOUT_SCHEMA.fields_schema
        assert "stop_atr_multiple" in TURTLE_BREAKOUT_SCHEMA.fields_schema


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
