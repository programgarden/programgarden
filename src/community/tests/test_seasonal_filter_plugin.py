"""
SeasonalFilter 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.seasonal_filter import (
    seasonal_filter_condition,
    _parse_months,
    _parse_date,
    _days_to_transition,
    SEASONAL_FILTER_SCHEMA,
)


def _make_data(symbol, month, day=15, year=2025):
    """특정 월의 데이터 생성"""
    date_str = f"{year}{month:02d}{day:02d}"
    return [
        {"symbol": symbol, "exchange": "NASDAQ",
         "date": date_str, "close": 100.0, "open": 99.0, "high": 101.0, "low": 99.0}
    ]


def _make_multi_data(symbol, months, year=2025):
    """여러 월에 걸친 데이터 생성 (최신 월 = 마지막)"""
    data = []
    for month in months:
        data.append({
            "symbol": symbol, "exchange": "NASDAQ",
            "date": f"{year}{month:02d}15",
            "close": 100.0 + month,
            "open": 99.0, "high": 102.0, "low": 98.0,
        })
    return data


class TestSeasonalHelpers:
    """헬퍼 함수 테스트"""

    def test_parse_months_halloween(self):
        """핼로윈 buy_months 파싱"""
        months = _parse_months("11,12,1,2,3,4")
        assert months == {11, 12, 1, 2, 3, 4}

    def test_parse_months_custom(self):
        """커스텀 월 파싱"""
        months = _parse_months("3,6,9,12")
        assert months == {3, 6, 9, 12}

    def test_parse_months_empty(self):
        """빈 문자열"""
        months = _parse_months("")
        assert months == set()

    def test_parse_months_invalid(self):
        """유효하지 않은 값 무시"""
        months = _parse_months("1,abc,13,0")
        assert months == {1}

    def test_parse_date_yyyymmdd(self):
        """YYYYMMDD 형식 파싱"""
        result = _parse_date("20251115")
        assert result == (2025, 11, 15)

    def test_parse_date_iso(self):
        """YYYY-MM-DD 형식 파싱"""
        result = _parse_date("2025-11-15")
        assert result == (2025, 11, 15)

    def test_parse_date_invalid(self):
        """유효하지 않은 날짜"""
        result = _parse_date("invalid")
        assert result is None

    def test_parse_date_empty(self):
        """빈 문자열"""
        result = _parse_date("")
        assert result is None

    def test_days_to_transition_november(self):
        """11월 → 5월로 전환 (핼로윈 buy 기간 종료)"""
        buy_months = {11, 12, 1, 2, 3, 4}
        # 11월 15일, buy_months 안 → 다음 전환은 5월 1일
        days = _days_to_transition(2025, 11, 15, buy_months)
        assert days > 0
        # 11월: 30-15=15일 남음 + 12월(31) + 1월(31) + 2월(28) + 3월(31) + 4월(30) = 166
        assert days == 15 + 31 + 31 + 28 + 31 + 30

    def test_days_to_transition_may(self):
        """5월 → 11월로 전환 (sell 기간)"""
        buy_months = {11, 12, 1, 2, 3, 4}
        days = _days_to_transition(2025, 5, 1, buy_months)
        assert days > 0
        # 5: 30 + 6:30 + 7:31 + 8:31 + 9:30 + 10:31 = 183
        assert days == 30 + 30 + 31 + 31 + 30 + 31


class TestSeasonalFilterCondition:
    """SeasonalFilter 조건 테스트"""

    @pytest.mark.asyncio
    async def test_buy_period_november(self):
        """11월 = buy_period (핼로윈 전략)"""
        data = _make_data("AAPL", month=11, day=15)
        result = await seasonal_filter_condition(
            data=data,
            fields={"strategy": "halloween"},
        )
        assert result["result"] is True
        assert len(result["passed_symbols"]) == 1
        sr = result["symbol_results"][0]
        assert sr["seasonal_signal"] == "buy_period"
        assert sr["current_month"] == 11

    @pytest.mark.asyncio
    async def test_sell_period_may(self):
        """5월 = sell_period (핼로윈 전략)"""
        data = _make_data("AAPL", month=5, day=15)
        result = await seasonal_filter_condition(
            data=data,
            fields={"strategy": "halloween"},
        )
        assert result["result"] is False
        assert len(result["failed_symbols"]) == 1
        sr = result["symbol_results"][0]
        assert sr["seasonal_signal"] == "sell_period"
        assert sr["current_month"] == 5

    @pytest.mark.asyncio
    async def test_halloween_all_months(self):
        """핼로윈 전략 전체 월 테스트"""
        buy_months = {11, 12, 1, 2, 3, 4}
        sell_months = {5, 6, 7, 8, 9, 10}

        for month in range(1, 13):
            data = _make_data("AAPL", month=month)
            result = await seasonal_filter_condition(
                data=data,
                fields={"strategy": "halloween"},
            )
            sr = result["symbol_results"][0]
            if month in buy_months:
                assert sr["seasonal_signal"] == "buy_period"
                assert result["result"] is True
            elif month in sell_months:
                assert sr["seasonal_signal"] == "sell_period"
                assert result["result"] is False

    @pytest.mark.asyncio
    async def test_custom_strategy(self):
        """커스텀 월 범위"""
        data = _make_data("AAPL", month=3)
        result = await seasonal_filter_condition(
            data=data,
            fields={
                "strategy": "custom",
                "buy_months": "1,2,3",
                "sell_months": "7,8,9",
            },
        )
        assert result["result"] is True
        sr = result["symbol_results"][0]
        assert sr["seasonal_signal"] == "buy_period"

    @pytest.mark.asyncio
    async def test_southern_hemisphere_shift(self):
        """남반구 6개월 시프트"""
        # 북반구 11월(buy) → 남반구 5월(shifted buy)
        data_nov = _make_data("ASX", month=11)
        data_may = _make_data("ASX", month=5)

        result_nov_north = await seasonal_filter_condition(
            data=data_nov, fields={"strategy": "halloween", "hemisphere": "northern"}
        )
        result_may_south = await seasonal_filter_condition(
            data=data_may, fields={"strategy": "halloween", "hemisphere": "southern"}
        )

        assert result_nov_north["result"] is True  # 북반구 11월 = buy
        assert result_may_south["result"] is True  # 남반구 5월 = buy (shifted)

    @pytest.mark.asyncio
    async def test_days_to_transition_present_in_result(self):
        """days_to_transition 결과에 포함"""
        data = _make_data("AAPL", month=11, day=15)
        result = await seasonal_filter_condition(
            data=data,
            fields={"strategy": "halloween"},
        )
        sr = result["symbol_results"][0]
        assert "days_to_transition" in sr
        assert isinstance(sr["days_to_transition"], int)
        assert sr["days_to_transition"] > 0

    @pytest.mark.asyncio
    async def test_empty_data(self):
        """빈 데이터"""
        result = await seasonal_filter_condition(data=[], fields={})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_multi_symbol_different_results(self):
        """다종목 - 다른 날짜 데이터"""
        data = (
            _make_data("AAPL", month=11)
            + _make_data("TSLA", month=5)
        )
        result = await seasonal_filter_condition(
            data=data,
            fields={"strategy": "halloween"},
        )
        assert len(result["passed_symbols"]) == 1   # 11월 = buy
        assert len(result["failed_symbols"]) == 1   # 5월 = sell

    @pytest.mark.asyncio
    async def test_multi_month_data_uses_latest(self):
        """여러 월 데이터에서 최신 날짜 기준"""
        # 1월, 3월 데이터 → 최신(3월)로 판단
        data = _make_multi_data("AAPL", months=[1, 3])
        result = await seasonal_filter_condition(
            data=data,
            fields={"strategy": "halloween"},
        )
        sr = result["symbol_results"][0]
        assert sr["current_month"] == 3  # 최신 = 3월 (buy_period)

    @pytest.mark.asyncio
    async def test_time_series_format(self):
        """time_series 출력 형식"""
        data = _make_multi_data("AAPL", months=[1, 3, 5, 11])
        result = await seasonal_filter_condition(
            data=data,
            fields={"strategy": "halloween"},
        )
        for val in result["values"]:
            assert "time_series" in val
            if val["time_series"]:
                row = val["time_series"][0]
                assert "seasonal_signal" in row
                assert "current_month" in row

    @pytest.mark.asyncio
    async def test_iso_date_format(self):
        """ISO 날짜 형식 (YYYY-MM-DD)"""
        data = [{"symbol": "AAPL", "exchange": "NASDAQ",
                 "date": "2025-11-15", "close": 100.0}]
        result = await seasonal_filter_condition(
            data=data,
            fields={"strategy": "halloween"},
        )
        sr = result["symbol_results"][0]
        assert sr["current_month"] == 11

    def test_schema(self):
        """스키마 검증"""
        assert SEASONAL_FILTER_SCHEMA.id == "SeasonalFilter"
        assert "strategy" in SEASONAL_FILTER_SCHEMA.fields_schema
        assert "buy_months" in SEASONAL_FILTER_SCHEMA.fields_schema
        assert "sell_months" in SEASONAL_FILTER_SCHEMA.fields_schema
        assert "hemisphere" in SEASONAL_FILTER_SCHEMA.fields_schema


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
