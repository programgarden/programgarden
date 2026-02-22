"""
MarketInternals (시장 내부 지표) 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.market_internals import (
    market_internals_condition,
    _calculate_advance_decline,
    _calculate_above_ma_pct,
    _calculate_new_high_low_ratio,
    MARKET_INTERNALS_SCHEMA,
)


def _make_universe_data(num_symbols=10, days=60, trend="mixed"):
    """유니버스 테스트 데이터 생성"""
    data = []
    for j in range(num_symbols):
        sym = f"SYM{j:02d}"
        base = 100 + j * 10
        for i in range(days):
            if trend == "bullish":
                close = base + i * 0.5
            elif trend == "bearish":
                close = base - i * 0.3
            else:  # mixed
                if j < num_symbols // 2:
                    close = base + i * 0.5
                else:
                    close = base - i * 0.3
            data.append({
                "symbol": sym, "exchange": "NASDAQ",
                "date": f"2025{(i // 28) + 1:02d}{(i % 28) + 1:02d}",
                "close": close,
            })
    return data


class TestMarketInternalsPlugin:
    """MarketInternals 플러그인 테스트"""

    @pytest.fixture
    def bullish_data(self):
        """강세장 데이터"""
        return _make_universe_data(10, 60, "bullish")

    @pytest.fixture
    def bearish_data(self):
        """약세장 데이터"""
        return _make_universe_data(10, 60, "bearish")

    @pytest.fixture
    def mixed_data(self):
        """혼조세 데이터"""
        return _make_universe_data(10, 60, "mixed")

    def test_advance_decline_all_up(self):
        """전종목 상승"""
        closes = {f"S{i}": [100, 101, 102] for i in range(5)}
        ratio = _calculate_advance_decline(closes, lookback=1)
        assert ratio == 100.0

    def test_advance_decline_all_down(self):
        """전종목 하락"""
        closes = {f"S{i}": [100, 99, 98] for i in range(5)}
        ratio = _calculate_advance_decline(closes, lookback=1)
        assert ratio == 0.0

    def test_above_ma_pct(self):
        """MA 위 종목 비율"""
        closes = {
            "UP": list(range(100, 160)),  # 상승 → MA 위
            "DOWN": list(range(160, 100, -1)),  # 하락 → MA 아래
        }
        pct = _calculate_above_ma_pct(closes, ma_period=20)
        assert pct == 50.0  # 1/2

    def test_new_high_low_ratio(self):
        """신고가 종목 비율"""
        closes = {
            "UP": list(range(100, 160)),  # 최근 최고가
            "FLAT": [100] * 60,  # 평탄 → 최고가이긴 함 (같은 값)
        }
        ratio = _calculate_new_high_low_ratio(closes, period=52)
        assert ratio >= 50.0

    @pytest.mark.asyncio
    async def test_bullish_advance_decline(self, bullish_data):
        """강세장에서 상승/하락 비율 높음"""
        result = await market_internals_condition(
            data=bullish_data,
            fields={"metric": "advance_decline_ratio", "threshold": 50, "direction": "above"},
        )
        assert result["result"] is True
        assert result["market_health"]["advance_decline_ratio"] > 50

    @pytest.mark.asyncio
    async def test_bearish_advance_decline(self, bearish_data):
        """약세장에서 상승/하락 비율 낮음"""
        result = await market_internals_condition(
            data=bearish_data,
            fields={"metric": "advance_decline_ratio", "threshold": 50, "direction": "below"},
        )
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_composite_metric(self, mixed_data):
        """복합 점수"""
        result = await market_internals_condition(
            data=mixed_data,
            fields={"metric": "composite", "threshold": 50, "direction": "above"},
        )
        assert "market_health" in result
        assert "composite" in result["market_health"]

    @pytest.mark.asyncio
    async def test_empty_data(self):
        """빈 데이터"""
        result = await market_internals_condition(data=[], fields={})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_single_symbol(self):
        """단일 종목 (최소 2종목 필요)"""
        data = [{"symbol": "AAPL", "exchange": "NASDAQ", "date": f"2025010{i}", "close": 100 + i} for i in range(1, 10)]
        result = await market_internals_condition(data=data, fields={})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_market_health_output(self, bullish_data):
        """market_health 필드 확인"""
        result = await market_internals_condition(
            data=bullish_data,
            fields={"metric": "advance_decline_ratio"},
        )
        mh = result["market_health"]
        assert "advance_decline_ratio" in mh
        assert "above_ma_pct" in mh
        assert "new_high_low_ratio" in mh
        assert "composite" in mh

    def test_schema(self):
        """스키마 검증"""
        assert MARKET_INTERNALS_SCHEMA.id == "MarketInternals"
        assert "metric" in MARKET_INTERNALS_SCHEMA.fields_schema
        assert len(MARKET_INTERNALS_SCHEMA.fields_schema["metric"]["enum"]) == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
