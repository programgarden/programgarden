"""
ATR (Average True Range) 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.atr import (
    atr_condition,
    calculate_atr,
    calculate_atr_series,
    calculate_true_range,
    ATR_SCHEMA,
)


class TestATRPlugin:
    """ATR 플러그인 테스트"""

    @pytest.fixture
    def mock_symbols(self):
        """테스트용 종목 리스트"""
        return [
            {"symbol": "AAPL", "exchange": "NASDAQ"},
            {"symbol": "NVDA", "exchange": "NASDAQ"},
        ]

    @pytest.fixture
    def mock_data_breakout_up(self):
        """상단 돌파 데이터"""
        data = []
        price = 100.0
        for i in range(20):
            # 전반부: 안정적 움직임
            if i < 15:
                high = price + 2
                low = price - 2
                close = price + 0.5
            else:
                # 후반부: 급등 (ATR 상단 돌파)
                high = price + 10
                low = price
                close = price + 8
                price = close

            data.append({
                "symbol": "AAPL",
                "exchange": "NASDAQ",
                "date": f"202501{i+1:02d}",
                "open": price,
                "high": high,
                "low": low,
                "close": close,
                "volume": 1000000,
            })
            price = close
        return data

    @pytest.fixture
    def mock_data_breakout_down(self):
        """하단 돌파 데이터"""
        data = []
        price = 150.0
        for i in range(20):
            # 전반부: 안정적 움직임
            if i < 15:
                high = price + 2
                low = price - 2
                close = price - 0.5
            else:
                # 후반부: 급락 (ATR 하단 돌파)
                high = price
                low = price - 10
                close = price - 8
                price = close

            data.append({
                "symbol": "NVDA",
                "exchange": "NASDAQ",
                "date": f"202501{i+1:02d}",
                "open": price,
                "high": high,
                "low": low,
                "close": close,
                "volume": 2000000,
            })
            price = close
        return data

    @pytest.fixture
    def mock_data_normal(self):
        """일반 데이터 (밴드 내)"""
        data = []
        price = 100.0
        for i in range(20):
            # 안정적 움직임 (ATR 밴드 내)
            high = price + 1
            low = price - 1
            close = price + 0.2 if i % 2 == 0 else price - 0.2

            data.append({
                "symbol": "AAPL",
                "exchange": "NASDAQ",
                "date": f"202501{i+1:02d}",
                "open": price,
                "high": high,
                "low": low,
                "close": close,
                "volume": 1000000,
            })
            price = close
        return data

    def test_calculate_true_range(self):
        """True Range 계산 테스트"""
        # Case 1: H-L이 가장 큰 경우
        tr = calculate_true_range(high=110, low=100, prev_close=105)
        assert tr == 10, f"Expected TR=10, got {tr}"

        # Case 2: |H-PC|가 가장 큰 경우
        tr = calculate_true_range(high=115, low=108, prev_close=100)
        assert tr == 15, f"Expected TR=15, got {tr}"

        # Case 3: |L-PC|가 가장 큰 경우
        tr = calculate_true_range(high=102, low=95, prev_close=110)
        assert tr == 15, f"Expected TR=15, got {tr}"

    def test_calculate_atr(self):
        """ATR 계산 테스트"""
        # 15일간 데이터 (period=14 -> 최소 15일 필요)
        highs = [100 + i for i in range(15)]
        lows = [95 + i for i in range(15)]
        closes = [98 + i for i in range(15)]

        atr = calculate_atr(highs, lows, closes, period=14)

        assert atr > 0, "ATR should be positive"
        assert isinstance(atr, float), "ATR should be float"

    def test_calculate_atr_insufficient_data(self):
        """데이터 부족 시"""
        highs = [100, 101, 102]
        lows = [98, 99, 100]
        closes = [99, 100, 101]

        atr = calculate_atr(highs, lows, closes, period=14)
        # 데이터 부족 시 가능한 범위로 계산
        assert atr >= 0

    def test_calculate_atr_series(self):
        """ATR 시계열 계산 테스트"""
        # 20일간 데이터
        highs = [100 + i * 0.5 for i in range(20)]
        lows = [95 + i * 0.5 for i in range(20)]
        closes = [98 + i * 0.5 for i in range(20)]

        series = calculate_atr_series(highs, lows, closes, period=14)

        assert len(series) > 0, "Should return non-empty series"

        for atr_val in series:
            assert atr_val > 0

    @pytest.mark.asyncio
    async def test_breakout_up_condition(self, mock_data_breakout_up):
        """상단 돌파 조건 테스트"""
        result = await atr_condition(
            data=mock_data_breakout_up,
            fields={
                "period": 14,
                "multiplier": 2.0,
                "direction": "breakout_up",
            },
        )

        assert "passed_symbols" in result
        assert "failed_symbols" in result
        assert "symbol_results" in result
        assert "values" in result
        assert "result" in result

    @pytest.mark.asyncio
    async def test_breakout_down_condition(self, mock_data_breakout_down):
        """하단 돌파 조건 테스트"""
        result = await atr_condition(
            data=mock_data_breakout_down,
            fields={
                "period": 14,
                "multiplier": 2.0,
                "direction": "breakout_down",
            },
        )

        assert "passed_symbols" in result
        assert "failed_symbols" in result
        assert "symbol_results" in result

    @pytest.mark.asyncio
    async def test_symbol_results_format(self, mock_data_normal):
        """symbol_results 형식 확인"""
        result = await atr_condition(
            data=mock_data_normal,
            fields={
                "period": 14,
                "multiplier": 2.0,
                "direction": "breakout_up",
            },
        )

        for sr in result["symbol_results"]:
            assert "symbol" in sr
            assert "exchange" in sr
            # atr, upper_band, lower_band 값 또는 error
            if "error" not in sr:
                assert "atr" in sr
                assert "upper_band" in sr
                assert "lower_band" in sr

    @pytest.mark.asyncio
    async def test_values_time_series_format(self, mock_data_normal):
        """values의 time_series 형식 확인"""
        result = await atr_condition(
            data=mock_data_normal,
            fields={
                "period": 14,
                "multiplier": 2.0,
                "direction": "breakout_up",
            },
        )

        assert len(result["values"]) >= 1

        for val in result["values"]:
            assert "symbol" in val
            assert "exchange" in val
            assert "time_series" in val

            if val["time_series"]:
                for row in val["time_series"]:
                    assert "atr" in row
                    assert "upper_band" in row
                    assert "lower_band" in row

    @pytest.mark.asyncio
    async def test_auto_extract_symbols(self, mock_data_normal):
        """symbols 없이 data에서 자동 추출"""
        result = await atr_condition(
            data=mock_data_normal,
            fields={
                "period": 14,
                "multiplier": 2.0,
                "direction": "breakout_up",
            },
        )

        assert len(result["symbol_results"]) >= 1

    @pytest.mark.asyncio
    async def test_empty_data(self):
        """빈 데이터"""
        result = await atr_condition(
            data=[],
            fields={
                "period": 14,
                "multiplier": 2.0,
                "direction": "breakout_up",
            },
        )

        assert len(result["passed_symbols"]) == 0
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_insufficient_data(self):
        """데이터 부족 케이스"""
        # 10일 데이터 (최소 15일 필요: period=14 + 1)
        data = []
        for i in range(10):
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

        result = await atr_condition(
            data=data,
            fields={
                "period": 14,
                "multiplier": 2.0,
                "direction": "breakout_up",
            },
            symbols=[{"symbol": "AAPL", "exchange": "NASDAQ"}],
        )

        # 데이터 부족으로 실패해야 함
        assert len(result["failed_symbols"]) == 1
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_multiplier_effect(self, mock_data_normal):
        """multiplier에 따른 밴드 폭 변화"""
        result_2x = await atr_condition(
            data=mock_data_normal,
            fields={"period": 14, "multiplier": 2.0, "direction": "breakout_up"},
        )

        result_3x = await atr_condition(
            data=mock_data_normal,
            fields={"period": 14, "multiplier": 3.0, "direction": "breakout_up"},
        )

        if result_2x["symbol_results"] and result_3x["symbol_results"]:
            sr_2x = result_2x["symbol_results"][0]
            sr_3x = result_3x["symbol_results"][0]

            if "upper_band" in sr_2x and "upper_band" in sr_3x:
                # 3x multiplier는 더 넓은 밴드를 가짐
                band_width_2x = sr_2x["upper_band"] - sr_2x["lower_band"]
                band_width_3x = sr_3x["upper_band"] - sr_3x["lower_band"]
                assert band_width_3x > band_width_2x

    def test_schema(self):
        """스키마 검증"""
        assert ATR_SCHEMA.id == "ATR"
        assert ATR_SCHEMA.version == "1.0.0"
        assert "period" in ATR_SCHEMA.fields_schema
        assert "multiplier" in ATR_SCHEMA.fields_schema
        assert "direction" in ATR_SCHEMA.fields_schema


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
