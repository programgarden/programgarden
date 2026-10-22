"""
Schaff Trend Cycle (STC) 플러그인 테스트 (direct import)
"""

import math

import pytest

from programgarden_community.plugins.schaff_trend_cycle import (
    schaff_trend_cycle_condition,
    calculate_stc_series,
    SCHAFF_TREND_CYCLE_SCHEMA,
)


def _bars(closes, symbol="AAPL", exchange="NASDAQ"):
    out = []
    for i, c in enumerate(closes):
        out.append({
            "symbol": symbol,
            "exchange": exchange,
            "date": f"2025{(i // 28) + 1:02d}{(i % 28) + 1:02d}",
            "open": c,
            "high": c * 1.01,
            "low": c * 0.99,
            "close": c,
            "volume": 1_000_000,
        })
    return out


def _noisy_uptrend(n=80, drift=0.8, amp=3.0, base=100.0):
    return [base + i * drift + amp * math.sin(i / 3.0) for i in range(n)]


class TestSTCMath:

    def test_stc_bounded_0_100(self):
        """STC 는 정의상 0..100 범위 (double stochastic) — 참조 속성."""
        stc = calculate_stc_series(_noisy_uptrend(80), 23, 50, 10)
        vals = [v for v in stc if v is not None]
        assert len(vals) > 0
        assert all(0.0 <= v <= 100.0 for v in vals)

    def test_recent_up_cycle_high_down_cycle_low(self):
        """STC 는 최근 사이클 위치 반영: 마지막 구간이 상승 마감 → >50, 하락 마감 → <50.

        (거시 추세가 아니라 최근 스윙 방향을 측정한다 — hand-reasoned reference.)
        """
        # rising history, then a sharp sustained final rise → recent up cycle
        bullish = [200 - i * 0.9 for i in range(60)] + [200 - 60 * 0.9 + i * 2.5 for i in range(1, 25)]
        up = calculate_stc_series(bullish, 23, 50, 10)
        up_last = [v for v in up if v is not None][-1]
        assert up_last > 50.0

        # rising history, then a sharp sustained final decline → recent down cycle
        bearish = [100 + i * 0.9 for i in range(60)] + [100 + 60 * 0.9 - i * 2.5 for i in range(1, 25)]
        down = calculate_stc_series(bearish, 23, 50, 10)
        down_last = [v for v in down if v is not None][-1]
        assert down_last < 50.0


class TestSTCCondition:

    @pytest.mark.asyncio
    async def test_happy_path_uptrend_long(self):
        """80-bar 노이즈 상승 → STC>50, long 통과, 시계열 non-empty + signal field."""
        data = _bars(_noisy_uptrend(80))
        result = await schaff_trend_cycle_condition(data=data, fields={"direction": "long"})
        assert result["result"] is True
        sr = result["symbol_results"][0]
        assert sr["stc"] is not None
        assert 0.0 <= sr["stc"] <= 100.0
        assert sr["stc"] > 50.0
        ts = result["values"][0]["time_series"]
        assert len(ts) > 0
        assert all("stc" in bar and "signal" in bar for bar in ts)

    @pytest.mark.asyncio
    async def test_band_cross_signals(self):
        """상승→하락 전환 → lower/upper 밴드 교차로 buy/sell 신호 발생."""
        up = _noisy_uptrend(70, drift=0.9)
        down = [up[-1] - i * 0.9 + 2 * math.sin(i / 2.5) for i in range(1, 50)]
        data = _bars(up + down)
        result = await schaff_trend_cycle_condition(data=data, fields={})
        ts = result["values"][0]["time_series"]
        signals = {bar["signal"] for bar in ts}
        assert "buy" in signals
        assert "sell" in signals

    @pytest.mark.asyncio
    async def test_empty_data(self):
        result = await schaff_trend_cycle_condition(data=[], fields={})
        assert result["result"] is False
        assert "error" in result["analysis"]

    @pytest.mark.asyncio
    async def test_insufficient_bars_explicit_reason(self):
        """<slow+cycle bars → 명시 insufficient_data."""
        data = _bars([100 + i for i in range(30)])  # default needs 60
        result = await schaff_trend_cycle_condition(data=data, fields={})
        assert result["result"] is False
        assert len(result["failed_symbols"]) == 1
        assert "insufficient_data" in result["symbol_results"][0]["error"]

    @pytest.mark.asyncio
    async def test_constant_series_explicit_reason(self):
        data = _bars([100.0] * 65)  # >= min_required so flat check is reached
        result = await schaff_trend_cycle_condition(data=data, fields={})
        assert result["result"] is False
        sr = result["symbol_results"][0]
        assert sr["stc"] is None
        assert "flat_series" in sr["error"]


class TestSTCSchema:

    def test_schema_identity(self):
        assert SCHAFF_TREND_CYCLE_SCHEMA.id == "SchaffTrendCycle"
        assert SCHAFF_TREND_CYCLE_SCHEMA.category == "technical"
        assert "cycle" in SCHAFF_TREND_CYCLE_SCHEMA.fields_schema

    def test_output_fields_valid(self):
        of = SCHAFF_TREND_CYCLE_SCHEMA.output_fields
        assert of
        assert "symbol" not in of and "exchange" not in of
        for meta in of.values():
            assert meta.get("type") in {"float", "int", "str", "bool", "list", "dict"}
            assert meta.get("description", "").strip()
