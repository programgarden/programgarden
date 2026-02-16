"""
PivotPoint (피봇 포인트) 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.pivot_point import (
    pivot_point_condition,
    calculate_pivot_standard,
    calculate_pivot_fibonacci,
    calculate_pivot_camarilla,
    find_nearest_level,
    PIVOT_POINT_SCHEMA,
)


class TestPivotPointPlugin:
    """PivotPoint 플러그인 테스트"""

    @pytest.fixture
    def mock_data_near_support(self):
        """지지선 근처 데이터"""
        # 전일: H=110, L=100, C=105 → PP=105, S1=100, S2=95
        # 당일 종가를 S1(100) 근처로 설정
        data = [
            {"symbol": "AAPL", "exchange": "NASDAQ", "date": "20250101",
             "open": 103, "high": 110, "low": 100, "close": 105, "volume": 1000000},
            {"symbol": "AAPL", "exchange": "NASDAQ", "date": "20250102",
             "open": 102, "high": 103, "low": 99, "close": 100.5, "volume": 1200000},
        ]
        return data

    @pytest.fixture
    def mock_data_near_resistance(self):
        """저항선 근처 데이터"""
        # 전일: H=110, L=100, C=105 → PP=105, R1=110, R2=115
        # 당일 종가를 R1(110) 근처로 설정
        data = [
            {"symbol": "AAPL", "exchange": "NASDAQ", "date": "20250101",
             "open": 103, "high": 110, "low": 100, "close": 105, "volume": 1000000},
            {"symbol": "AAPL", "exchange": "NASDAQ", "date": "20250102",
             "open": 108, "high": 111, "low": 107, "close": 110, "volume": 1500000},
        ]
        return data

    @pytest.fixture
    def mock_data_multi_day(self):
        """여러 날 데이터"""
        data = []
        prices = [(100, 95, 98), (102, 97, 100), (105, 99, 103),
                   (108, 101, 106), (110, 103, 107)]
        for i, (h, l, c) in enumerate(prices):
            data.append({
                "symbol": "AAPL",
                "exchange": "NASDAQ",
                "date": f"2025010{i+1}",
                "open": c - 1,
                "high": h,
                "low": l,
                "close": c,
                "volume": 1000000,
            })
        return data

    @pytest.fixture
    def mock_data_multi_symbol(self):
        """다종목 데이터"""
        data = []
        for sym, offset in [("AAPL", 0), ("TSLA", 100)]:
            for i in range(5):
                data.append({
                    "symbol": sym,
                    "exchange": "NASDAQ",
                    "date": f"2025010{i+1}",
                    "high": 110 + offset + i,
                    "low": 100 + offset + i,
                    "close": 105 + offset + i,
                })
        return data

    def test_calculate_pivot_standard(self):
        """Standard 피봇 계산"""
        result = calculate_pivot_standard(110, 100, 105)
        assert result["pp"] == pytest.approx(105.0, abs=0.01)
        assert result["r1"] == pytest.approx(110.0, abs=0.01)
        assert result["s1"] == pytest.approx(100.0, abs=0.01)
        assert result["r2"] == pytest.approx(115.0, abs=0.01)
        assert result["s2"] == pytest.approx(95.0, abs=0.01)

    def test_calculate_pivot_fibonacci(self):
        """Fibonacci 피봇 계산"""
        result = calculate_pivot_fibonacci(110, 100, 105)
        pp = 105.0
        diff = 10.0
        assert result["pp"] == pytest.approx(pp, abs=0.01)
        assert result["r1"] == pytest.approx(pp + 0.382 * diff, abs=0.01)
        assert result["s1"] == pytest.approx(pp - 0.382 * diff, abs=0.01)
        assert result["r2"] == pytest.approx(pp + 0.618 * diff, abs=0.01)
        assert result["s2"] == pytest.approx(pp - 0.618 * diff, abs=0.01)

    def test_calculate_pivot_camarilla(self):
        """Camarilla 피봇 계산"""
        result = calculate_pivot_camarilla(110, 100, 105)
        diff = 10.0
        assert result["pp"] == pytest.approx(105.0, abs=0.01)
        assert result["r1"] == pytest.approx(105 + diff * 1.1 / 12, abs=0.01)
        assert result["s1"] == pytest.approx(105 - diff * 1.1 / 12, abs=0.01)

    def test_find_nearest_level_support(self):
        """가장 가까운 지지 레벨 찾기"""
        levels = {"pp": 105, "s1": 100, "s2": 95, "r1": 110, "r2": 115, "s3": 90, "r3": 120}
        result = find_nearest_level(101, levels, "support")
        assert result["level_name"] == "s1"
        assert result["level_price"] == 100

    def test_find_nearest_level_resistance(self):
        """가장 가까운 저항 레벨 찾기"""
        levels = {"pp": 105, "s1": 100, "s2": 95, "r1": 110, "r2": 115, "s3": 90, "r3": 120}
        result = find_nearest_level(108, levels, "resistance")
        assert result["level_name"] == "r1"
        assert result["level_price"] == 110

    @pytest.mark.asyncio
    async def test_support_condition(self, mock_data_near_support):
        """지지선 조건 테스트"""
        result = await pivot_point_condition(
            data=mock_data_near_support,
            fields={"pivot_type": "standard", "direction": "support", "tolerance": 0.01},
        )

        assert "passed_symbols" in result
        assert "failed_symbols" in result
        assert "symbol_results" in result
        assert "values" in result

    @pytest.mark.asyncio
    async def test_resistance_condition(self, mock_data_near_resistance):
        """저항선 조건 테스트"""
        result = await pivot_point_condition(
            data=mock_data_near_resistance,
            fields={"pivot_type": "standard", "direction": "resistance", "tolerance": 0.01},
        )

        assert "passed_symbols" in result
        assert "failed_symbols" in result

    @pytest.mark.asyncio
    async def test_fibonacci_type(self, mock_data_multi_day):
        """Fibonacci 타입 테스트"""
        result = await pivot_point_condition(
            data=mock_data_multi_day,
            fields={"pivot_type": "fibonacci", "direction": "support"},
        )

        assert len(result["symbol_results"]) == 1
        if "pp" in result["symbol_results"][0]:
            assert result["symbol_results"][0]["pivot_type"] == "fibonacci"

    @pytest.mark.asyncio
    async def test_camarilla_type(self, mock_data_multi_day):
        """Camarilla 타입 테스트"""
        result = await pivot_point_condition(
            data=mock_data_multi_day,
            fields={"pivot_type": "camarilla", "direction": "support"},
        )

        assert len(result["symbol_results"]) == 1

    @pytest.mark.asyncio
    async def test_multi_symbol(self, mock_data_multi_symbol):
        """다종목 처리"""
        result = await pivot_point_condition(
            data=mock_data_multi_symbol,
            fields={"pivot_type": "standard", "direction": "support"},
        )

        total = len(result["passed_symbols"]) + len(result["failed_symbols"])
        assert total == 2
        assert len(result["values"]) == 2

    @pytest.mark.asyncio
    async def test_empty_data(self):
        """빈 데이터"""
        result = await pivot_point_condition(
            data=[],
            fields={"pivot_type": "standard", "direction": "support"},
        )
        assert result["result"] is False
        assert len(result["passed_symbols"]) == 0

    @pytest.mark.asyncio
    async def test_insufficient_data(self):
        """데이터 부족 (1일만)"""
        data = [
            {"symbol": "AAPL", "exchange": "NASDAQ", "date": "20250101",
             "high": 110, "low": 100, "close": 105},
        ]
        result = await pivot_point_condition(
            data=data,
            fields={"pivot_type": "standard", "direction": "support"},
        )
        assert len(result["failed_symbols"]) == 1

    @pytest.mark.asyncio
    async def test_time_series_format(self, mock_data_multi_day):
        """time_series 출력 형식"""
        result = await pivot_point_condition(
            data=mock_data_multi_day,
            fields={"pivot_type": "standard", "direction": "support"},
        )

        for val in result["values"]:
            assert "time_series" in val
            if val["time_series"]:
                row = val["time_series"][0]
                assert "pp" in row
                assert "r1" in row
                assert "s1" in row
                assert "nearest_level" in row
                assert "distance_pct" in row

    def test_schema(self):
        """스키마 검증"""
        assert PIVOT_POINT_SCHEMA.id == "PivotPoint"
        assert PIVOT_POINT_SCHEMA.version == "1.0.0"
        assert "pivot_type" in PIVOT_POINT_SCHEMA.fields_schema
        assert "direction" in PIVOT_POINT_SCHEMA.fields_schema
        assert "tolerance" in PIVOT_POINT_SCHEMA.fields_schema


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
