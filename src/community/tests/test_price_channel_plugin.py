"""
Price Channel (Donchian Channel) 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.price_channel import (
    price_channel_condition,
    calculate_channel,
    calculate_channel_series,
    PRICE_CHANNEL_SCHEMA,
)


class TestPriceChannelPlugin:
    """PriceChannel 플러그인 테스트"""

    @pytest.fixture
    def mock_symbols(self):
        """테스트용 종목 리스트"""
        return [
            {"symbol": "AAPL", "exchange": "NASDAQ"},
            {"symbol": "NVDA", "exchange": "NASDAQ"},
        ]

    @pytest.fixture
    def mock_data_breakout_high(self):
        """상단 채널 돌파 데이터"""
        data = []
        for i in range(25):
            # 전반부: 100~110 범위로 채널 형성
            if i < 21:
                high = 110
                low = 100
                close = 105
            else:
                # 마지막 몇 개: 종가가 이전 채널 상단을 돌파
                # 고가와 종가를 점진적으로 높여 마지막 종가가 채널 상단 초과
                step = i - 20
                high = 115 + step * 5  # 115, 120, 125, 130
                low = 108 + step * 3
                close = 112 + step * 5  # 112, 117, 122, 127

            data.append({
                "symbol": "AAPL",
                "exchange": "NASDAQ",
                "date": f"202501{i+1:02d}",
                "open": close - 1,
                "high": high,
                "low": low,
                "close": close,
                "volume": 1000000,
            })
        return data

    @pytest.fixture
    def mock_data_breakout_low(self):
        """하단 채널 이탈 데이터"""
        data = []
        for i in range(25):
            # 전반부: 100~110 범위로 채널 형성
            if i < 21:
                high = 110
                low = 100
                close = 105
            else:
                # 마지막 몇 개: 종가가 이전 채널 하단을 이탈
                # 저가와 종가를 점진적으로 낮춰 마지막 종가가 채널 하단 미만
                step = i - 20
                high = 98 - step * 3
                low = 95 - step * 5  # 90, 85, 80, 75
                close = 93 - step * 5  # 88, 83, 78, 73

            data.append({
                "symbol": "NVDA",
                "exchange": "NASDAQ",
                "date": f"202501{i+1:02d}",
                "open": close + 1,
                "high": high,
                "low": low,
                "close": close,
                "volume": 2000000,
            })
        return data

    @pytest.fixture
    def mock_data_in_channel(self):
        """채널 내 데이터 (돌파 없음)"""
        data = []
        for i in range(25):
            # 100~110 범위 유지
            high = 110
            low = 100
            close = 105 + (i % 3 - 1)  # 104~106

            data.append({
                "symbol": "AAPL",
                "exchange": "NASDAQ",
                "date": f"202501{i+1:02d}",
                "open": close,
                "high": high,
                "low": low,
                "close": close,
                "volume": 1000000,
            })
        return data

    def test_calculate_channel(self):
        """채널 계산 테스트"""
        highs = [100, 105, 110, 108, 112, 115, 113, 118, 120, 117,
                 115, 114, 116, 118, 120, 119, 121, 123, 122, 125]
        lows = [95, 98, 102, 100, 105, 108, 106, 110, 112, 110,
                108, 107, 109, 111, 113, 112, 114, 116, 115, 118]

        channel = calculate_channel(highs, lows, period=20)

        assert channel["upper"] == 125, f"Expected upper=125, got {channel['upper']}"
        assert channel["lower"] == 95, f"Expected lower=95, got {channel['lower']}"
        assert channel["middle"] == 110, f"Expected middle=110, got {channel['middle']}"

    def test_calculate_channel_insufficient_data(self):
        """데이터 부족 시 기본값 반환"""
        highs = [100, 105, 110]
        lows = [95, 98, 102]

        channel = calculate_channel(highs, lows, period=20)

        assert channel["upper"] == 0.0
        assert channel["lower"] == 0.0
        assert channel["middle"] == 0.0

    def test_calculate_channel_series(self):
        """채널 시계열 계산 테스트"""
        highs = [100 + i for i in range(25)]
        lows = [95 + i for i in range(25)]

        series = calculate_channel_series(highs, lows, period=20)

        # 현재 봉 제외 방식: 인덱스 20~24에 대해 계산 = 5개
        assert len(series) == 5, f"Expected 5 entries, got {len(series)}"

        for entry in series:
            assert "upper" in entry
            assert "lower" in entry
            assert "middle" in entry
            assert entry["upper"] > entry["lower"]

    @pytest.mark.asyncio
    async def test_breakout_high_condition(self, mock_data_breakout_high):
        """상단 채널 돌파 조건 테스트"""
        result = await price_channel_condition(
            data=mock_data_breakout_high,
            fields={
                "period": 20,
                "direction": "breakout_high",
            },
        )

        assert "passed_symbols" in result
        assert "failed_symbols" in result
        assert "symbol_results" in result
        assert "values" in result
        assert "result" in result

        # 상단 돌파 발생 -> AAPL이 passed에 있어야 함
        passed_syms = [s["symbol"] for s in result["passed_symbols"]]
        assert "AAPL" in passed_syms, f"Expected AAPL in passed, got {passed_syms}"

    @pytest.mark.asyncio
    async def test_breakout_low_condition(self, mock_data_breakout_low):
        """하단 채널 이탈 조건 테스트"""
        result = await price_channel_condition(
            data=mock_data_breakout_low,
            fields={
                "period": 20,
                "direction": "breakout_low",
            },
        )

        assert "passed_symbols" in result
        assert "failed_symbols" in result

        # 하단 이탈 발생 -> NVDA가 passed에 있어야 함
        passed_syms = [s["symbol"] for s in result["passed_symbols"]]
        assert "NVDA" in passed_syms, f"Expected NVDA in passed, got {passed_syms}"

    @pytest.mark.asyncio
    async def test_no_breakout(self, mock_data_in_channel):
        """채널 내 (돌파 없음) 조건 테스트"""
        result = await price_channel_condition(
            data=mock_data_in_channel,
            fields={
                "period": 20,
                "direction": "breakout_high",
            },
        )

        # 돌파 없음 -> 모두 failed
        assert len(result["passed_symbols"]) == 0
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_symbol_results_format(self, mock_data_in_channel):
        """symbol_results 형식 확인"""
        result = await price_channel_condition(
            data=mock_data_in_channel,
            fields={
                "period": 20,
                "direction": "breakout_high",
            },
        )

        for sr in result["symbol_results"]:
            assert "symbol" in sr
            assert "exchange" in sr
            if "error" not in sr:
                assert "upper_channel" in sr
                assert "lower_channel" in sr
                assert "middle_channel" in sr
                assert "current_price" in sr

    @pytest.mark.asyncio
    async def test_values_time_series_format(self, mock_data_in_channel):
        """values의 time_series 형식 확인"""
        result = await price_channel_condition(
            data=mock_data_in_channel,
            fields={
                "period": 20,
                "direction": "breakout_high",
            },
        )

        assert len(result["values"]) >= 1

        for val in result["values"]:
            assert "symbol" in val
            assert "exchange" in val
            assert "time_series" in val

            if val["time_series"]:
                for row in val["time_series"]:
                    assert "upper_channel" in row
                    assert "lower_channel" in row
                    assert "middle_channel" in row
                    assert "signal" in row

    @pytest.mark.asyncio
    async def test_auto_extract_symbols(self, mock_data_in_channel):
        """symbols 없이 data에서 자동 추출"""
        result = await price_channel_condition(
            data=mock_data_in_channel,
            fields={
                "period": 20,
                "direction": "breakout_high",
            },
        )

        assert len(result["symbol_results"]) >= 1

    @pytest.mark.asyncio
    async def test_empty_data(self):
        """빈 데이터"""
        result = await price_channel_condition(
            data=[],
            fields={
                "period": 20,
                "direction": "breakout_high",
            },
        )

        assert len(result["passed_symbols"]) == 0
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_insufficient_data(self):
        """데이터 부족 케이스"""
        # 15일 데이터 (최소 20일 필요)
        data = []
        for i in range(15):
            data.append({
                "symbol": "AAPL",
                "exchange": "NASDAQ",
                "date": f"202501{i+1:02d}",
                "open": 100,
                "high": 105,
                "low": 95,
                "close": 100,
                "volume": 1000000,
            })

        result = await price_channel_condition(
            data=data,
            fields={
                "period": 20,
                "direction": "breakout_high",
            },
            symbols=[{"symbol": "AAPL", "exchange": "NASDAQ"}],
        )

        # 데이터 부족으로 실패해야 함
        assert len(result["failed_symbols"]) == 1
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_multiple_symbols(self, mock_data_breakout_high, mock_data_breakout_low):
        """다중 종목 테스트"""
        # 두 데이터 합치기
        combined_data = mock_data_breakout_high + mock_data_breakout_low

        result = await price_channel_condition(
            data=combined_data,
            fields={
                "period": 20,
                "direction": "breakout_high",
            },
            symbols=[
                {"symbol": "AAPL", "exchange": "NASDAQ"},
                {"symbol": "NVDA", "exchange": "NASDAQ"},
            ],
        )

        # AAPL: 상단 돌파 -> passed
        # NVDA: 상단 돌파 없음 (하단 이탈) -> failed
        passed_syms = [s["symbol"] for s in result["passed_symbols"]]
        failed_syms = [s["symbol"] for s in result["failed_symbols"]]

        assert "AAPL" in passed_syms
        assert "NVDA" in failed_syms

    def test_schema(self):
        """스키마 검증"""
        assert PRICE_CHANNEL_SCHEMA.id == "PriceChannel"
        assert PRICE_CHANNEL_SCHEMA.version == "1.0.0"
        assert "period" in PRICE_CHANNEL_SCHEMA.fields_schema
        assert "direction" in PRICE_CHANNEL_SCHEMA.fields_schema


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
