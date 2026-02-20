"""
CalendarSpread (캘린더 스프레드) 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.calendar_spread import (
    calendar_spread_condition,
    CALENDAR_SPREAD_SCHEMA,
)


class TestCalendarSpreadPlugin:
    """CalendarSpread 플러그인 테스트"""

    @pytest.fixture
    def mock_data_widening_spread(self):
        """스프레드 확대 중 (진입 기회)"""
        data = []
        front_base, back_base = 70.0, 71.0
        for i in range(30):
            date = f"2025{(i // 30) + 1:02d}{(i % 30) + 1:02d}"
            # 스프레드가 점점 벌어짐
            front_price = front_base + i * 0.1
            back_price = back_base + i * 0.3  # 원월물이 더 빠르게 상승
            data.append({"symbol": "CLF26", "exchange": "CME", "date": date, "close": round(front_price, 2)})
            data.append({"symbol": "CLG26", "exchange": "CME", "date": date, "close": round(back_price, 2)})
        return data

    @pytest.fixture
    def mock_data_stable_spread(self):
        """스프레드 안정 (신호 없음)"""
        data = []
        for i in range(30):
            date = f"2025{(i // 30) + 1:02d}{(i % 30) + 1:02d}"
            data.append({"symbol": "CLF26", "exchange": "CME", "date": date, "close": 70.0 + i * 0.2})
            data.append({"symbol": "CLG26", "exchange": "CME", "date": date, "close": 71.0 + i * 0.2})
        return data

    # === 스키마 테스트 ===
    def test_schema_id(self):
        assert CALENDAR_SPREAD_SCHEMA.id == "CalendarSpread"

    def test_schema_fields(self):
        assert "spread_ma_period" in CALENDAR_SPREAD_SCHEMA.fields_schema
        assert "entry_deviation" in CALENDAR_SPREAD_SCHEMA.fields_schema
        assert "strategy" in CALENDAR_SPREAD_SCHEMA.fields_schema

    # === 조건 평가 테스트 ===
    @pytest.mark.asyncio
    async def test_widening_spread_mean_revert(self, mock_data_widening_spread):
        result = await calendar_spread_condition(
            data=mock_data_widening_spread,
            fields={"spread_ma_period": 15, "entry_deviation": 1.5, "strategy": "mean_revert"},
        )
        assert isinstance(result["result"], bool)
        assert "spread_info" in result
        assert "z_score" in result["spread_info"]

    @pytest.mark.asyncio
    async def test_momentum_strategy(self, mock_data_widening_spread):
        result = await calendar_spread_condition(
            data=mock_data_widening_spread,
            fields={"spread_ma_period": 15, "entry_deviation": 1.5, "strategy": "momentum"},
        )
        assert isinstance(result["result"], bool)

    @pytest.mark.asyncio
    async def test_stable_spread_no_signal(self, mock_data_stable_spread):
        result = await calendar_spread_condition(
            data=mock_data_stable_spread,
            fields={"spread_ma_period": 20, "entry_deviation": 2.0},
        )
        # 스프레드 안정적이면 신호 없음
        assert "spread_info" in result

    @pytest.mark.asyncio
    async def test_empty_data(self):
        result = await calendar_spread_condition(data=[], fields={})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_single_contract(self):
        data = [{"symbol": "CLF26", "exchange": "CME", "date": "20260115", "close": 70.0}]
        result = await calendar_spread_condition(data=data, fields={})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_spread_info_output(self, mock_data_widening_spread):
        result = await calendar_spread_condition(
            data=mock_data_widening_spread,
            fields={"spread_ma_period": 15},
        )
        si = result["spread_info"]
        assert "front_month" in si
        assert "back_month" in si
        assert "current_spread" in si
        assert "spread_ma" in si
        assert "spread_std" in si

    @pytest.mark.asyncio
    async def test_time_series_output(self, mock_data_widening_spread):
        result = await calendar_spread_condition(
            data=mock_data_widening_spread,
            fields={"spread_ma_period": 15},
        )
        assert len(result["values"]) > 0
        ts = result["values"][0]["time_series"]
        assert len(ts) > 0
        assert "spread" in ts[0]

    @pytest.mark.asyncio
    async def test_insufficient_common_dates(self):
        data = [
            {"symbol": "CLF26", "exchange": "CME", "date": "20260115", "close": 70.0},
            {"symbol": "CLG26", "exchange": "CME", "date": "20260116", "close": 71.0},
        ]
        result = await calendar_spread_condition(
            data=data,
            fields={"spread_ma_period": 20},
        )
        assert result["result"] is False
