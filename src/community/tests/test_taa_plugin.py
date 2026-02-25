"""
TacticalAssetAllocation (전술적 자산배분) 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.tactical_asset_allocation import (
    taa_condition,
    _calculate_sma,
    TAA_SCHEMA,
)


def _make_price_data(symbol, count, base=100.0, trend="flat"):
    """가격 데이터 생성"""
    data = []
    for i in range(count):
        if trend == "up":
            close = base + i * 0.5
        elif trend == "down":
            close = base - i * 0.5
        else:
            close = base + (i % 10 - 5) * 0.2
        data.append({
            "symbol": symbol, "exchange": "NASDAQ",
            "date": f"20{20 + i // 365:02d}{(i % 12) + 1:02d}{(i % 28) + 1:02d}",
            "open": close - 0.3,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": 1000000,
        })
    return data


def _make_sma_breakout_data(symbol, sma_period, above=True):
    """SMA 위/아래 데이터 생성"""
    data = []
    # sma_period 동안 100 유지
    for i in range(sma_period):
        data.append({
            "symbol": symbol, "exchange": "NASDAQ",
            "date": f"20250{(i // 28) + 1:02d}{(i % 28) + 1:02d}",
            "close": 100.0,
            "open": 99.5, "high": 101.0, "low": 99.0, "volume": 1000000,
        })
    # 마지막 바에서 SMA 위 또는 아래로 이동
    final_close = 120.0 if above else 80.0
    data.append({
        "symbol": symbol, "exchange": "NASDAQ",
        "date": "20250901",
        "close": final_close,
        "open": final_close - 1, "high": final_close + 1, "low": final_close - 2,
        "volume": 1000000,
    })
    return data


class TestTAASMAHelpers:
    """SMA 헬퍼 테스트"""

    def test_calculate_sma_basic(self):
        """기본 SMA 계산"""
        prices = [100.0, 102.0, 98.0, 101.0, 99.0]
        sma = _calculate_sma(prices, period=5)
        assert sma == pytest.approx(100.0)

    def test_calculate_sma_insufficient(self):
        """데이터 부족 시 None"""
        sma = _calculate_sma([100.0, 102.0], period=5)
        assert sma is None

    def test_calculate_sma_single(self):
        """단일 데이터 SMA"""
        sma = _calculate_sma([100.0], period=1)
        assert sma == 100.0

    def test_calculate_sma_uptrend(self):
        """상승 추세 SMA"""
        prices = list(range(1, 11))  # 1~10
        sma = _calculate_sma(prices, period=10)
        assert sma == 5.5


class TestTACTICALAssetAllocation:
    """TacticalAssetAllocation 조건 테스트"""

    @pytest.mark.asyncio
    async def test_above_sma_signal(self):
        """SMA 위 = above_sma 신호"""
        data = _make_sma_breakout_data("AAPL", sma_period=50, above=True)
        result = await taa_condition(
            data=data,
            fields={"sma_period": 50, "signal_mode": "binary"},
        )
        assert result["result"] is True
        assert len(result["passed_symbols"]) == 1
        sr = result["symbol_results"][0]
        assert sr["trend_signal"] == "above_sma"
        assert sr["allocation"] == 1.0

    @pytest.mark.asyncio
    async def test_below_sma_signal(self):
        """SMA 아래 = below_sma 신호"""
        data = _make_sma_breakout_data("AAPL", sma_period=50, above=False)
        result = await taa_condition(
            data=data,
            fields={"sma_period": 50, "signal_mode": "binary"},
        )
        assert result["result"] is False
        assert len(result["failed_symbols"]) == 1
        sr = result["symbol_results"][0]
        assert sr["trend_signal"] == "below_sma"
        assert sr["allocation"] == 0.0

    @pytest.mark.asyncio
    async def test_distance_pct_calculation(self):
        """SMA 대비 거리 % 계산"""
        data = _make_sma_breakout_data("AAPL", sma_period=50, above=True)
        result = await taa_condition(
            data=data,
            fields={"sma_period": 50},
        )
        sr = result["symbol_results"][0]
        assert "distance_pct" in sr
        if sr["trend_signal"] == "above_sma":
            assert sr["distance_pct"] > 0

    @pytest.mark.asyncio
    async def test_scaled_mode(self):
        """scaled 모드 - 0~1 사이 allocation"""
        data = _make_sma_breakout_data("AAPL", sma_period=50, above=True)
        result = await taa_condition(
            data=data,
            fields={"sma_period": 50, "signal_mode": "scaled"},
        )
        sr = result["symbol_results"][0]
        assert "allocation" in sr
        if sr["allocation"] is not None:
            assert 0.0 <= sr["allocation"] <= 1.0

    @pytest.mark.asyncio
    async def test_margin_pct_neutral_zone(self):
        """margin_pct - 중립 구간"""
        # 가격이 SMA와 거의 동일할 때 margin_pct > 0이면 neutral
        data = []
        for i in range(51):
            data.append({
                "symbol": "AAPL", "exchange": "NASDAQ",
                "date": f"20250{(i // 28) + 1:02d}{(i % 28) + 1:02d}",
                "close": 100.0,  # 모든 가격 동일 = SMA와 동일
                "open": 99.5, "high": 101.0, "low": 99.0, "volume": 1000000,
            })
        result = await taa_condition(
            data=data,
            fields={"sma_period": 50, "margin_pct": 2.0},  # SMA ± 2% 중립
        )
        sr = result["symbol_results"][0]
        # 가격 = SMA이므로 margin 안에 있어 neutral
        assert sr["trend_signal"] == "neutral"

    @pytest.mark.asyncio
    async def test_insufficient_data(self):
        """데이터 부족"""
        data = _make_price_data("AAPL", count=50)
        result = await taa_condition(
            data=data,
            fields={"sma_period": 200},
        )
        sr = result["symbol_results"][0]
        assert sr["trend_signal"] == "insufficient_data"
        assert "error" in sr

    @pytest.mark.asyncio
    async def test_empty_data(self):
        """빈 데이터"""
        result = await taa_condition(data=[], fields={})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_multi_symbol(self):
        """다종목 처리"""
        data_above = _make_sma_breakout_data("AAPL", sma_period=50, above=True)
        data_below = _make_sma_breakout_data("TSLA", sma_period=50, above=False)
        result = await taa_condition(
            data=data_above + data_below,
            fields={"sma_period": 50},
        )
        assert len(result["passed_symbols"]) + len(result["failed_symbols"]) == 2

    @pytest.mark.asyncio
    async def test_monthly_rebalance_check(self):
        """monthly 리밸런싱 체크 모드"""
        # 1년치 데이터 생성 (다양한 월)
        data = []
        for i in range(250):
            close = 100.0 + i * 0.1  # 완만한 상승
            data.append({
                "symbol": "SPY", "exchange": "NYSE",
                "date": f"20250{(i % 12) + 1:02d}{(i % 28) + 1:02d}",
                "close": close, "open": close - 0.5,
                "high": close + 1.0, "low": close - 1.0, "volume": 5000000,
            })
        result = await taa_condition(
            data=data,
            fields={"sma_period": 200, "rebalance_check": "monthly"},
        )
        assert "symbol_results" in result
        sr = result["symbol_results"][0]
        assert "trend_signal" in sr

    @pytest.mark.asyncio
    async def test_time_series_format(self):
        """time_series 출력 형식"""
        data = _make_price_data("AAPL", count=210)
        result = await taa_condition(
            data=data,
            fields={"sma_period": 200},
        )
        for val in result["values"]:
            assert "time_series" in val
            if val["time_series"]:
                row = val["time_series"][0]
                assert "sma_value" in row
                assert "trend_signal" in row
                assert "allocation" in row

    @pytest.mark.asyncio
    async def test_sma_value_present(self):
        """sma_value 결과에 포함"""
        data = _make_sma_breakout_data("AAPL", sma_period=50)
        result = await taa_condition(
            data=data,
            fields={"sma_period": 50},
        )
        sr = result["symbol_results"][0]
        assert "sma_value" in sr
        if sr["sma_value"]:
            assert sr["sma_value"] > 0

    def test_schema(self):
        """스키마 검증"""
        assert TAA_SCHEMA.id == "TacticalAssetAllocation"
        assert "sma_period" in TAA_SCHEMA.fields_schema
        assert "signal_mode" in TAA_SCHEMA.fields_schema
        assert "rebalance_check" in TAA_SCHEMA.fields_schema
        assert "margin_pct" in TAA_SCHEMA.fields_schema


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
