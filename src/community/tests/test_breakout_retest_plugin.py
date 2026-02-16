"""
BreakoutRetest (돌파 후 되돌림) 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.breakout_retest import (
    breakout_retest_condition,
    find_breakout_level,
    detect_retest,
    BREAKOUT_RETEST_SCHEMA,
)


class TestBreakoutRetestPlugin:
    """BreakoutRetest 플러그인 테스트"""

    @pytest.fixture
    def mock_data_bullish_breakout(self):
        """상향 돌파 후 되돌림 데이터"""
        data = []
        # 횡보 구간 (20일, 저항 = 110)
        for i in range(20):
            data.append({
                "symbol": "AAPL",
                "exchange": "NASDAQ",
                "date": f"2025{(i // 28) + 1:02d}{(i % 28) + 1:02d}",
                "open": 105,
                "high": 110,
                "low": 100,
                "close": 105 + (i % 3 - 1),
                "volume": 1000000,
            })
        # 돌파 (3일, 저항선 위로)
        for i in range(3):
            data.append({
                "symbol": "AAPL",
                "exchange": "NASDAQ",
                "date": f"202501{21 + i}",
                "open": 110 + i,
                "high": 115 + i,
                "low": 109 + i,
                "close": 112 + i,
                "volume": 2000000,
            })
        # 되돌림 (2일, 다시 저항선 근처로)
        for i in range(2):
            data.append({
                "symbol": "AAPL",
                "exchange": "NASDAQ",
                "date": f"202501{24 + i}",
                "open": 112 - i,
                "high": 113 - i,
                "low": 109,
                "close": 110.5,
                "volume": 1500000,
            })
        return data

    @pytest.fixture
    def mock_data_bearish_breakout(self):
        """하향 돌파 후 되돌림 데이터"""
        data = []
        # 횡보 구간 (20일, 지지 = 100)
        for i in range(20):
            data.append({
                "symbol": "TSLA",
                "exchange": "NASDAQ",
                "date": f"2025{(i // 28) + 1:02d}{(i % 28) + 1:02d}",
                "open": 105,
                "high": 110,
                "low": 100,
                "close": 105 + (i % 3 - 1),
                "volume": 1000000,
            })
        # 하향 돌파 (3일, 지지선 아래로)
        for i in range(3):
            data.append({
                "symbol": "TSLA",
                "exchange": "NASDAQ",
                "date": f"202501{21 + i}",
                "open": 100 - i,
                "high": 101 - i,
                "low": 95 - i,
                "close": 98 - i,
                "volume": 2000000,
            })
        # 되돌림 (2일, 다시 지지선 근처로)
        for i in range(2):
            data.append({
                "symbol": "TSLA",
                "exchange": "NASDAQ",
                "date": f"202501{24 + i}",
                "open": 97 + i,
                "high": 100,
                "low": 96,
                "close": 99.5,
                "volume": 1500000,
            })
        return data

    @pytest.fixture
    def mock_data_multi_symbol(self):
        """다종목 데이터"""
        data = []
        for sym, base in [("AAPL", 100), ("TSLA", 200)]:
            for i in range(30):
                data.append({
                    "symbol": sym,
                    "exchange": "NASDAQ",
                    "date": f"2025{(i // 28) + 1:02d}{(i % 28) + 1:02d}",
                    "high": base + 10,
                    "low": base,
                    "close": base + 5 + (i % 3 - 1),
                })
        return data

    def test_find_breakout_level(self):
        """돌파 레벨 찾기"""
        # 상향 돌파 시나리오
        highs = [100 + (i % 5) for i in range(25)]
        lows = [95 + (i % 5) for i in range(25)]
        closes = [97 + (i % 5) for i in range(20)] + [105, 106, 107, 108, 109]

        result = find_breakout_level(highs, lows, closes, lookback=20)
        assert "resistance" in result
        assert "support" in result
        assert "breakout_type" in result
        assert "breakout_level" in result

    def test_find_breakout_level_insufficient_data(self):
        """데이터 부족"""
        result = find_breakout_level([100], [95], [97], lookback=20)
        assert result["breakout_type"] is None

    def test_detect_retest_bullish(self):
        """상향 돌파 후 되돌림 감지"""
        assert detect_retest(110.5, 110, "bullish", threshold=0.02) is True
        assert detect_retest(115, 110, "bullish", threshold=0.02) is False  # 너무 멀리
        assert detect_retest(108, 110, "bullish", threshold=0.02) is False  # 레벨 아래

    def test_detect_retest_bearish(self):
        """하향 돌파 후 되돌림 감지"""
        assert detect_retest(99.5, 100, "bearish", threshold=0.02) is True
        assert detect_retest(95, 100, "bearish", threshold=0.02) is False  # 너무 멀리
        assert detect_retest(102, 100, "bearish", threshold=0.02) is False  # 레벨 위

    def test_detect_retest_no_breakout(self):
        """돌파 없는 경우"""
        assert detect_retest(100, None, "bullish") is False
        assert detect_retest(100, 0, "bullish") is False

    @pytest.mark.asyncio
    async def test_bullish_condition(self, mock_data_bullish_breakout):
        """상향 돌파 후 매수 조건"""
        result = await breakout_retest_condition(
            data=mock_data_bullish_breakout,
            fields={"lookback": 20, "retest_threshold": 0.02, "direction": "bullish"},
        )

        assert "passed_symbols" in result
        assert "failed_symbols" in result
        assert "symbol_results" in result
        assert "values" in result

    @pytest.mark.asyncio
    async def test_bearish_condition(self, mock_data_bearish_breakout):
        """하향 돌파 후 매도 조건"""
        result = await breakout_retest_condition(
            data=mock_data_bearish_breakout,
            fields={"lookback": 20, "retest_threshold": 0.02, "direction": "bearish"},
        )

        assert "passed_symbols" in result
        assert "failed_symbols" in result

    @pytest.mark.asyncio
    async def test_multi_symbol(self, mock_data_multi_symbol):
        """다종목 처리"""
        result = await breakout_retest_condition(
            data=mock_data_multi_symbol,
            fields={"lookback": 20, "retest_threshold": 0.02, "direction": "bullish"},
        )

        total = len(result["passed_symbols"]) + len(result["failed_symbols"])
        assert total == 2
        assert len(result["values"]) == 2

    @pytest.mark.asyncio
    async def test_empty_data(self):
        """빈 데이터"""
        result = await breakout_retest_condition(
            data=[],
            fields={"lookback": 20, "retest_threshold": 0.02, "direction": "bullish"},
        )
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_insufficient_data(self):
        """데이터 부족"""
        data = [
            {"symbol": "AAPL", "exchange": "NASDAQ", "date": f"2025010{i}",
             "high": 105, "low": 95, "close": 100}
            for i in range(1, 6)
        ]
        result = await breakout_retest_condition(
            data=data,
            fields={"lookback": 20, "retest_threshold": 0.02, "direction": "bullish"},
        )
        assert len(result["failed_symbols"]) == 1

    @pytest.mark.asyncio
    async def test_time_series_format(self, mock_data_bullish_breakout):
        """time_series 출력 형식"""
        result = await breakout_retest_condition(
            data=mock_data_bullish_breakout,
            fields={"lookback": 20, "retest_threshold": 0.02, "direction": "bullish"},
        )

        for val in result["values"]:
            assert "time_series" in val
            if val["time_series"]:
                row = val["time_series"][0]
                assert "resistance" in row
                assert "support" in row
                assert "breakout_level" in row

    def test_schema(self):
        """스키마 검증"""
        assert BREAKOUT_RETEST_SCHEMA.id == "BreakoutRetest"
        assert BREAKOUT_RETEST_SCHEMA.version == "1.0.0"
        assert "lookback" in BREAKOUT_RETEST_SCHEMA.fields_schema
        assert "retest_threshold" in BREAKOUT_RETEST_SCHEMA.fields_schema
        assert "direction" in BREAKOUT_RETEST_SCHEMA.fields_schema


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
