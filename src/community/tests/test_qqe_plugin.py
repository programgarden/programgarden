"""
QQE (Quantitative Qualitative Estimation) 플러그인 테스트 (direct import)
"""

import pytest

from programgarden_community.plugins.qqe import (
    qqe_condition,
    calculate_qqe_series,
    _wilder_rsi,
    QQE_SCHEMA,
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


class TestQQEMath:

    def test_wilder_rsi_increasing_is_100(self):
        """모든 봉 상승 → losses=0 → Wilder RSI = 100 (정확 hand-check reference)."""
        rsi = _wilder_rsi([float(100 + i) for i in range(40)], 14)
        assert rsi[-1] == pytest.approx(100.0, abs=1e-9)

    def test_increasing_series_trend_and_rsima(self):
        """상승 → rsi_ma=100, trend=+1, qqe 라인 정의됨 (참조값)."""
        qqe, trend, rsima = calculate_qqe_series([float(100 + i) for i in range(40)], 14, 5, 4.236)
        emitted = [(q, t, r) for q, t, r in zip(qqe, trend, rsima) if q is not None]
        assert emitted, "expected emitted QQE values after warmup"
        q_last, t_last, r_last = emitted[-1]
        assert r_last == pytest.approx(100.0, abs=1e-9)
        assert t_last == 1
        assert q_last == pytest.approx(100.0, abs=1e-6)

    def test_warmup_is_none(self):
        qqe, trend, rsima = calculate_qqe_series([float(100 + i) for i in range(40)], 14, 5, 4.236)
        assert qqe[0] is None
        assert trend[0] is None


class TestQQECondition:

    @pytest.mark.asyncio
    async def test_happy_path_uptrend_long(self):
        """40-bar 상승 → trend=+1, long 통과, rsi_ma≈100, 시계열 non-empty + signal field."""
        data = _bars([float(100 + i) for i in range(40)])
        result = await qqe_condition(data=data, fields={"direction": "long"})
        assert result["result"] is True
        sr = result["symbol_results"][0]
        assert sr["trend"] == 1
        assert sr["rsi_ma"] == pytest.approx(100.0, abs=1e-6)
        assert sr["qqe"] is not None
        ts = result["values"][0]["time_series"]
        assert len(ts) > 0
        assert all("qqe" in bar and "trend" in bar and "signal" in bar for bar in ts)

    @pytest.mark.asyncio
    async def test_trend_flip_sell_signal(self):
        """상승 후 급락 → trend 이 -1 로 전환하며 sell 신호, short 방향 통과."""
        up = [100 + i * 1.2 for i in range(40)]
        down = [up[-1] - i * 3.0 for i in range(1, 35)]
        data = _bars(up + down)
        result = await qqe_condition(data=data, fields={"direction": "short"})
        assert result["result"] is True
        assert result["symbol_results"][0]["trend"] == -1
        ts = result["values"][0]["time_series"]
        assert any(bar["signal"] == "sell" for bar in ts)

    @pytest.mark.asyncio
    async def test_empty_data(self):
        result = await qqe_condition(data=[], fields={})
        assert result["result"] is False
        assert "error" in result["analysis"]

    @pytest.mark.asyncio
    async def test_insufficient_bars_explicit_reason(self):
        """<2*rsi_period+sf bars → 명시 insufficient_data."""
        data = _bars([100 + i for i in range(20)])  # default needs 33
        result = await qqe_condition(data=data, fields={})
        assert result["result"] is False
        assert len(result["failed_symbols"]) == 1
        assert "insufficient_data" in result["symbol_results"][0]["error"]

    @pytest.mark.asyncio
    async def test_constant_series_explicit_reason(self):
        data = _bars([100.0] * 40)  # >= min_required so flat check is reached
        result = await qqe_condition(data=data, fields={})
        assert result["result"] is False
        sr = result["symbol_results"][0]
        assert sr["trend"] is None
        assert "flat_series" in sr["error"]


class TestQQESchema:

    def test_schema_identity(self):
        assert QQE_SCHEMA.id == "QQE"
        assert QQE_SCHEMA.category == "technical"
        assert "rsi_period" in QQE_SCHEMA.fields_schema

    def test_output_fields_valid(self):
        of = QQE_SCHEMA.output_fields
        assert of
        assert "symbol" not in of and "exchange" not in of
        for meta in of.values():
            assert meta.get("type") in {"float", "int", "str", "bool", "list", "dict"}
            assert meta.get("description", "").strip()
