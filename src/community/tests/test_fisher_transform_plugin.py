"""
Fisher Transform 플러그인 테스트 (direct import — 레지스트리 등록 이전 검증)
"""

import math

import pytest

from programgarden_community.plugins.fisher_transform import (
    fisher_transform_condition,
    calculate_fisher_series,
    FISHER_TRANSFORM_SCHEMA,
)


def _bars(closes, symbol="AAPL", exchange="NASDAQ"):
    """Build a flat OHLC row array from a close series (high/low straddle close)."""
    out = []
    for i, c in enumerate(closes):
        out.append({
            "symbol": symbol,
            "exchange": exchange,
            "date": f"2025{(i // 28) + 1:02d}{(i % 28) + 1:02d}",
            "open": c,
            "high": c + 1.0,
            "low": c - 1.0,
            "close": c,
            "volume": 1_000_000,
        })
    return out


class TestFisherTransformMath:

    def test_hand_computed_single_value(self):
        """lookback=2, medians=[10,20] → x=1, val=0.33, Fisher=0.5*ln(1.33/0.67)≈0.34279."""
        series = calculate_fisher_series([10.0, 20.0], 2)
        assert series[0] is None  # warmup
        expected = 0.5 * math.log(1.33 / 0.67)
        assert series[1] == pytest.approx(expected, abs=1e-9)

    def test_increasing_is_positive_and_monotonic(self):
        """Strictly increasing median → every normalized x=1 → Fisher strictly rising, positive."""
        series = calculate_fisher_series([float(100 + i) for i in range(20)], 9)
        vals = [v for v in series if v is not None]
        assert vals[-1] > 0
        assert all(b > a for a, b in zip(vals, vals[1:]))


class TestFisherTransformCondition:

    @pytest.mark.asyncio
    async def test_happy_path_uptrend_long(self):
        """30-bar rising series → Fisher > 0, long passes, non-empty series with signal field."""
        data = _bars([100 + i for i in range(30)])
        result = await fisher_transform_condition(data=data, fields={"lookback": 9, "direction": "long"})

        assert result["result"] is True
        assert {"symbol": "AAPL", "exchange": "NASDAQ"} in result["passed_symbols"]

        sr = result["symbol_results"][0]
        assert sr["fisher"] is not None
        assert sr["fisher"] > 0  # bullish

        ts = result["values"][0]["time_series"]
        assert len(ts) > 0
        assert all("fisher" in bar and "signal" in bar and "side" in bar for bar in ts)

    @pytest.mark.asyncio
    async def test_zero_cross_signals(self):
        """Oscillating price → Fisher crosses zero → at least one buy and one sell signal."""
        osc = [100 + 10 * math.sin(i / 3.0) for i in range(40)]
        data = _bars(osc)
        result = await fisher_transform_condition(data=data, fields={"lookback": 9})
        ts = result["values"][0]["time_series"]
        signals = {bar["signal"] for bar in ts}
        assert "buy" in signals
        assert "sell" in signals

    @pytest.mark.asyncio
    async def test_short_direction(self):
        """Downtrend + direction short → Fisher < 0 passes."""
        data = _bars([100 - i for i in range(30)])
        result = await fisher_transform_condition(data=data, fields={"lookback": 9, "direction": "short"})
        assert result["result"] is True
        assert result["symbol_results"][0]["fisher"] < 0

    @pytest.mark.asyncio
    async def test_empty_data(self):
        """빈 데이터 → result False + 명시 analysis.error (silent 금지)."""
        result = await fisher_transform_condition(data=[], fields={"lookback": 9})
        assert result["result"] is False
        assert result["passed_symbols"] == []
        assert "error" in result["analysis"]

    @pytest.mark.asyncio
    async def test_insufficient_bars_explicit_reason(self):
        """<lookback+1 bars → 명시 insufficient_data, silent drop 아님."""
        data = _bars([100 + i for i in range(5)])
        result = await fisher_transform_condition(data=data, fields={"lookback": 9})
        assert result["result"] is False
        assert len(result["failed_symbols"]) == 1
        assert "insufficient_data" in result["symbol_results"][0]["error"]
        assert result["values"][0]["time_series"] == []

    @pytest.mark.asyncio
    async def test_constant_series_explicit_reason(self):
        """상수 시계열 → 명시 flat_series reason (silent 0/None 흡수 금지)."""
        data = _bars([100.0] * 15)
        result = await fisher_transform_condition(data=data, fields={"lookback": 9})
        assert result["result"] is False
        sr = result["symbol_results"][0]
        assert sr["fisher"] is None
        assert "flat_series" in sr["error"]


class TestFisherTransformSchema:

    def test_schema_identity(self):
        assert FISHER_TRANSFORM_SCHEMA.id == "FisherTransform"
        assert FISHER_TRANSFORM_SCHEMA.category == "technical"

    def test_schema_products(self):
        prods = [p.value if hasattr(p, "value") else p for p in FISHER_TRANSFORM_SCHEMA.products]
        assert "overseas_stock" in prods
        assert "overseas_futures" in prods

    def test_output_fields_valid(self):
        of = FISHER_TRANSFORM_SCHEMA.output_fields
        assert of, "output_fields must not be empty"
        assert "symbol" not in of and "exchange" not in of
        for meta in of.values():
            assert meta.get("type") in {"float", "int", "str", "bool", "list", "dict"}
            assert meta.get("description", "").strip()
