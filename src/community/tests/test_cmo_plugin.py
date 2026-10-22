"""
CMO (Chande Momentum Oscillator) 플러그인 테스트 (direct import)
"""

import pytest

from programgarden_community.plugins.cmo import (
    cmo_condition,
    calculate_cmo,
    calculate_cmo_series,
    CMO_SCHEMA,
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


class TestCMOMath:

    def test_strictly_increasing_is_plus_100(self):
        """모든 변화가 상승 → up만 존재, down=0 → CMO = +100 (정확 hand-check)."""
        cmo = calculate_cmo([float(100 + i) for i in range(20)], 9)
        assert cmo == pytest.approx(100.0, abs=1e-9)

    def test_strictly_decreasing_is_minus_100(self):
        cmo = calculate_cmo([float(100 - i) for i in range(20)], 9)
        assert cmo == pytest.approx(-100.0, abs=1e-9)

    def test_insufficient_returns_none(self):
        assert calculate_cmo([100.0, 101.0], 9) is None

    def test_flat_window_returns_none(self):
        assert calculate_cmo([100.0] * 20, 9) is None

    def test_series_length_and_warmup(self):
        series = calculate_cmo_series([float(100 + i) for i in range(30)], 9)
        assert len(series) == 30
        assert series[8] is None  # index < period → warmup
        assert series[9] is not None


class TestCMOCondition:

    @pytest.mark.asyncio
    async def test_happy_path_oversold(self):
        """하락 추세 30봉 → CMO 음수, oversold 방향 통과, 시계열 non-empty."""
        price = 200.0
        closes = []
        for _ in range(30):
            price *= 0.97
            closes.append(price)
        data = _bars(closes)
        result = await cmo_condition(
            data=data,
            fields={"period": 9, "threshold": 50, "direction": "oversold"},
        )
        assert result["result"] is True
        sr = result["symbol_results"][0]
        assert sr["cmo"] is not None
        assert sr["cmo"] < -50  # deep oversold on a sustained decline
        ts = result["values"][0]["time_series"]
        assert len(ts) > 0
        assert all("cmo" in bar and "signal" in bar for bar in ts)
        assert any(bar["signal"] == "buy" for bar in ts)

    @pytest.mark.asyncio
    async def test_overbought_direction(self):
        price = 100.0
        closes = []
        for _ in range(30):
            price *= 1.03
            closes.append(price)
        result = await cmo_condition(
            data=_bars(closes),
            fields={"period": 9, "threshold": 50, "direction": "overbought"},
        )
        assert result["result"] is True
        assert result["symbol_results"][0]["cmo"] > 50

    @pytest.mark.asyncio
    async def test_empty_data(self):
        result = await cmo_condition(data=[], fields={"period": 9, "direction": "oversold"})
        assert result["result"] is False
        assert "error" in result["analysis"]

    @pytest.mark.asyncio
    async def test_insufficient_bars_explicit_reason(self):
        data = _bars([100 + i for i in range(5)])
        result = await cmo_condition(data=data, fields={"period": 9, "direction": "oversold"})
        assert result["result"] is False
        assert len(result["failed_symbols"]) == 1
        assert "insufficient_data" in result["symbol_results"][0]["error"]

    @pytest.mark.asyncio
    async def test_constant_series_explicit_reason(self):
        """상수 시계열 → 분모 0 → 명시 flat_series reason (silent 아님)."""
        data = _bars([100.0] * 15)
        result = await cmo_condition(data=data, fields={"period": 9, "direction": "oversold"})
        assert result["result"] is False
        sr = result["symbol_results"][0]
        assert sr["cmo"] is None
        assert "flat_series" in sr["error"]


class TestCMOSchema:

    def test_schema_identity(self):
        assert CMO_SCHEMA.id == "CMO"
        assert CMO_SCHEMA.category == "technical"
        assert "period" in CMO_SCHEMA.fields_schema
        assert "direction" in CMO_SCHEMA.fields_schema

    def test_output_fields_valid(self):
        of = CMO_SCHEMA.output_fields
        assert of
        assert "symbol" not in of and "exchange" not in of
        for meta in of.values():
            assert meta.get("type") in {"float", "int", "str", "bool", "list", "dict"}
            assert meta.get("description", "").strip()
