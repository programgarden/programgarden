"""
CCI 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.cci import (
    cci_condition,
    calculate_cci,
    calculate_cci_series,
    CCI_SCHEMA,
)


class TestCCIPlugin:

    def test_calculate_cci_basic(self):
        """기본 CCI 계산"""
        highs = [float(100 + i) for i in range(20)]
        lows = [float(95 + i) for i in range(20)]
        closes = [float(98 + i) for i in range(20)]

        cci = calculate_cci(highs, lows, closes, 20)
        assert cci is not None

    def test_calculate_cci_insufficient_data(self):
        """데이터 부족"""
        cci = calculate_cci([100, 101], [95, 96], [98, 99], 20)
        assert cci is None

    def test_calculate_cci_range(self):
        """CCI 범위 확인 (극단적 편차일 때)"""
        # 꾸준한 상승 추세 -> 양의 CCI
        highs = [float(100 + i * 2) for i in range(20)]
        lows = [float(95 + i * 2) for i in range(20)]
        closes = [float(98 + i * 2) for i in range(20)]

        cci = calculate_cci(highs, lows, closes, 20)
        assert cci is not None
        assert cci > 0  # 상승 추세이므로 양수

    def test_calculate_cci_series(self):
        """CCI 시계열"""
        highs = [float(100 + i * 0.5) for i in range(30)]
        lows = [float(95 + i * 0.5) for i in range(30)]
        closes = [float(98 + i * 0.5) for i in range(30)]

        series = calculate_cci_series(highs, lows, closes, 20)
        assert len(series) > 0
        for entry in series:
            assert "cci" in entry
            assert "typical_price" in entry

    @pytest.mark.asyncio
    async def test_oversold_condition(self):
        """과매도 조건"""
        data = []
        price = 200.0
        for i in range(30):
            price *= 0.97
            data.append({
                "symbol": "AAPL", "exchange": "NASDAQ",
                "date": f"202501{i+1:02d}",
                "high": round(price * 1.01, 2),
                "low": round(price * 0.99, 2),
                "close": round(price, 2),
                "volume": 1000000,
            })

        result = await cci_condition(
            data=data,
            fields={"period": 20, "threshold": 100, "direction": "oversold"},
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
            price *= 1.03
            data.append({
                "symbol": "AAPL", "exchange": "NASDAQ",
                "date": f"202501{i+1:02d}",
                "high": round(price * 1.01, 2),
                "low": round(price * 0.99, 2),
                "close": round(price, 2),
                "volume": 1000000,
            })

        result = await cci_condition(
            data=data,
            fields={"period": 20, "threshold": 100, "direction": "overbought"},
        )
        assert "passed_symbols" in result

    @pytest.mark.asyncio
    async def test_empty_data(self):
        """빈 데이터"""
        result = await cci_condition(data=[], fields={"period": 20, "direction": "oversold"})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_insufficient_data(self):
        """데이터 부족"""
        data = [{"symbol": "AAPL", "exchange": "NASDAQ", "date": f"2025010{i+1}",
                 "high": 105, "low": 95, "close": 100} for i in range(5)]
        result = await cci_condition(
            data=data,
            fields={"period": 20, "direction": "oversold"},
            symbols=[{"symbol": "AAPL", "exchange": "NASDAQ"}],
        )
        assert len(result["failed_symbols"]) == 1

    @pytest.mark.asyncio
    async def test_time_series_format(self):
        """time_series 형식"""
        data = []
        price = 100.0
        for i in range(30):
            price *= 0.98
            data.append({"symbol": "AAPL", "exchange": "NASDAQ", "date": f"202501{i+1:02d}",
                         "high": round(price * 1.01, 2), "low": round(price * 0.99, 2),
                         "close": round(price, 2), "volume": 1000000})

        result = await cci_condition(data=data, fields={"period": 20, "direction": "oversold"})
        for val in result["values"]:
            if val["time_series"]:
                row = val["time_series"][0]
                assert "cci" in row
                assert "typical_price" in row
                assert "signal" in row

    def test_schema(self):
        assert CCI_SCHEMA.id == "CCI"
        assert "period" in CCI_SCHEMA.fields_schema
        assert "threshold" in CCI_SCHEMA.fields_schema
        assert "direction" in CCI_SCHEMA.fields_schema
