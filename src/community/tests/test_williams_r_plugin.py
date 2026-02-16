"""
Williams %R 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.williams_r import (
    williams_r_condition,
    calculate_williams_r,
    calculate_williams_r_series,
    WILLIAMS_R_SCHEMA,
)


class TestWilliamsRPlugin:

    def test_calculate_williams_r_basic(self):
        """기본 %R 계산"""
        highs = [float(100 + i) for i in range(14)]
        lows = [float(95 + i) for i in range(14)]
        closes = [float(98 + i) for i in range(14)]

        wr = calculate_williams_r(highs, lows, closes, 14)
        assert wr is not None
        assert -100 <= wr <= 0

    def test_calculate_williams_r_insufficient_data(self):
        """데이터 부족"""
        wr = calculate_williams_r([100, 101], [95, 96], [98, 99], 14)
        assert wr is None

    def test_calculate_williams_r_oversold(self):
        """과매도 상태 (하락 추세)"""
        # 최근 종가가 기간 내 최저가에 가까워야 과매도
        highs = [float(110)] * 14
        lows = [float(90)] * 14
        closes = [float(90)] * 13 + [float(91)]  # 종가 ≈ 최저가

        wr = calculate_williams_r(highs, lows, closes, 14)
        assert wr is not None
        assert wr <= -80  # 과매도

    def test_calculate_williams_r_overbought(self):
        """과매수 상태 (상승 추세)"""
        highs = [float(100 + i) for i in range(14)]
        lows = [float(90 + i) for i in range(14)]
        closes = list(highs)  # 종가 = 최고가

        wr = calculate_williams_r(highs, lows, closes, 14)
        assert wr is not None
        assert wr >= -20  # 과매수

    def test_calculate_williams_r_series(self):
        """시계열 계산"""
        highs = [float(100 + i * 0.5) for i in range(30)]
        lows = [float(95 + i * 0.5) for i in range(30)]
        closes = [float(98 + i * 0.5) for i in range(30)]

        series = calculate_williams_r_series(highs, lows, closes, 14)
        assert len(series) > 0
        for entry in series:
            assert "williams_r" in entry
            assert -100 <= entry["williams_r"] <= 0

    @pytest.mark.asyncio
    async def test_oversold_condition(self):
        """과매도 조건"""
        data = []
        price = 200.0
        for i in range(30):
            price *= 0.98
            data.append({
                "symbol": "AAPL", "exchange": "NASDAQ",
                "date": f"202501{i+1:02d}",
                "high": round(price * 1.01, 2),
                "low": round(price * 0.99, 2),
                "close": round(price, 2),
                "volume": 1000000,
            })

        result = await williams_r_condition(
            data=data,
            fields={"period": 14, "threshold": -80, "direction": "oversold"},
        )
        assert "passed_symbols" in result
        assert "failed_symbols" in result
        assert "symbol_results" in result
        assert "values" in result
        assert "result" in result
        assert "analysis" in result

    @pytest.mark.asyncio
    async def test_overbought_condition(self):
        """과매수 조건"""
        data = []
        price = 100.0
        for i in range(30):
            price *= 1.02
            data.append({
                "symbol": "AAPL", "exchange": "NASDAQ",
                "date": f"202501{i+1:02d}",
                "high": round(price * 1.01, 2),
                "low": round(price * 0.99, 2),
                "close": round(price, 2),
                "volume": 1000000,
            })

        result = await williams_r_condition(
            data=data,
            fields={"period": 14, "threshold": -80, "direction": "overbought"},
        )
        assert "passed_symbols" in result

    @pytest.mark.asyncio
    async def test_empty_data(self):
        """빈 데이터"""
        result = await williams_r_condition(data=[], fields={"period": 14, "direction": "oversold"})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_insufficient_data(self):
        """데이터 부족"""
        data = [{"symbol": "AAPL", "exchange": "NASDAQ", "date": f"20250{i+1:02d}01",
                 "high": 105, "low": 95, "close": 100} for i in range(5)]
        result = await williams_r_condition(
            data=data,
            fields={"period": 14, "direction": "oversold"},
            symbols=[{"symbol": "AAPL", "exchange": "NASDAQ"}],
        )
        assert len(result["failed_symbols"]) == 1

    @pytest.mark.asyncio
    async def test_time_series_format(self):
        """time_series 형식"""
        data = []
        price = 100.0
        for i in range(30):
            price *= 0.99
            data.append({"symbol": "AAPL", "exchange": "NASDAQ", "date": f"202501{i+1:02d}",
                         "high": round(price * 1.01, 2), "low": round(price * 0.99, 2),
                         "close": round(price, 2), "volume": 1000000})

        result = await williams_r_condition(data=data, fields={"period": 14, "direction": "oversold"})
        for val in result["values"]:
            if val["time_series"]:
                row = val["time_series"][0]
                assert "williams_r" in row
                assert "signal" in row
                assert "side" in row

    def test_schema(self):
        assert WILLIAMS_R_SCHEMA.id == "WilliamsR"
        assert "period" in WILLIAMS_R_SCHEMA.fields_schema
        assert "threshold" in WILLIAMS_R_SCHEMA.fields_schema
        assert "direction" in WILLIAMS_R_SCHEMA.fields_schema
