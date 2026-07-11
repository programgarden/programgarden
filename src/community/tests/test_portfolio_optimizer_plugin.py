"""
PortfolioOptimizer (PyPortfolioOpt) 플러그인 테스트.

- 스키마 (POSITION, method enum = max_sharpe/min_volatility/efficient_risk, HRP 제외)
- happy-path: >=2 종목 max_sharpe/min_volatility → weight 합 ~100, sharpe 산출
- empty / <2 종목 → result False + analysis.error (무음 아님)
- 미정렬 종목 dropna → analysis.dropped_symbols (무음 드랍 금지)
- 미설치/부분설치 extra → MissingDependencyError (.extra/.transitive/install_hint)
"""

import builtins
import pytest

from programgarden_core.exceptions import MissingDependencyError
from programgarden_community.plugins.portfolio_optimizer import (
    portfolio_optimizer_condition,
    PORTFOLIO_OPTIMIZER_SCHEMA,
)


def _series(symbol, exchange, start, drift_up, drift_dn, n=60):
    """결정적 가격 시계열 rows."""
    rows = []
    price = start
    for i in range(n):
        price *= drift_up if i % 2 == 0 else drift_dn
        date = f"2026{(i // 30) + 1:02d}{(i % 30) + 1:02d}"
        rows.append({"symbol": symbol, "exchange": exchange, "date": date, "close": round(price, 4)})
    return rows


@pytest.fixture
def three_symbols():
    """3 종목, 서로 다른 추세 (양의 기대수익 존재 → max_sharpe 해 존재)."""
    data = []
    data += _series("AAPL", "NASDAQ", 150.0, 1.012, 0.997)   # 강한 상승
    data += _series("MSFT", "NASDAQ", 300.0, 1.008, 0.998)   # 완만 상승
    data += _series("TSLA", "NASDAQ", 200.0, 1.02, 0.985)    # 고변동 상승
    return data


class TestSchema:
    def test_id_and_category(self):
        assert PORTFOLIO_OPTIMIZER_SCHEMA.id == "PortfolioOptimizer"
        assert PORTFOLIO_OPTIMIZER_SCHEMA.category == "position"

    def test_method_enum_excludes_hrp(self):
        methods = PORTFOLIO_OPTIMIZER_SCHEMA.fields_schema["method"]["enum"]
        assert set(methods) == {"max_sharpe", "min_volatility", "efficient_risk"}
        assert "hrp" not in [m.lower() for m in methods]

    def test_output_fields_no_common(self):
        of = PORTFOLIO_OPTIMIZER_SCHEMA.output_fields
        assert of and "weight_pct" in of
        assert "symbol" not in of and "exchange" not in of


class TestHappyPath:
    @pytest.mark.asyncio
    async def test_max_sharpe_weights_sum_100(self, three_symbols):
        res = await portfolio_optimizer_condition(three_symbols, {"method": "max_sharpe"})
        assert res["result"] is True
        assert len(res["passed_symbols"]) >= 2
        total = sum(r["weight_pct"] for r in res["symbol_results"])
        assert abs(total - 100.0) < 1.0, f"weights should sum ~100, got {total}"
        assert res["analysis"]["sharpe"] is not None
        assert res["analysis"]["method"] == "max_sharpe"
        # values 각 원소는 time_series 노출
        for v in res["values"]:
            assert "time_series" in v and v["time_series"][0]["side"] == "long"

    @pytest.mark.asyncio
    async def test_min_volatility(self, three_symbols):
        res = await portfolio_optimizer_condition(three_symbols, {"method": "min_volatility"})
        assert res["result"] is True
        total = sum(r["weight_pct"] for r in res["symbol_results"])
        assert abs(total - 100.0) < 1.0
        assert res["analysis"]["volatility_pct"] is not None

    @pytest.mark.asyncio
    async def test_efficient_risk(self, three_symbols):
        res = await portfolio_optimizer_condition(
            three_symbols, {"method": "efficient_risk", "target_volatility": 20.0})
        # 해가 존재하면 result True, 목표 미달 시 명시 error (무음 아님)
        assert res["result"] is True or "error" in res["analysis"]


class TestErrorBranches:
    @pytest.mark.asyncio
    async def test_empty_data(self):
        res = await portfolio_optimizer_condition([], {})
        assert res["result"] is False
        assert "error" in res["analysis"]

    @pytest.mark.asyncio
    async def test_single_symbol_insufficient(self):
        rows = _series("AAPL", "NASDAQ", 150.0, 1.01, 0.99)
        res = await portfolio_optimizer_condition(rows, {"method": "max_sharpe"})
        assert res["result"] is False
        assert "error" in res["analysis"]

    @pytest.mark.asyncio
    async def test_dropped_unaligned_symbol(self, three_symbols):
        # 한 종목에 관측치 부족(<20) → insufficient_history 드랍, 나머지로 최적화
        short = _series("SHORT", "NASDAQ", 100.0, 1.01, 0.99, n=5)
        res = await portfolio_optimizer_condition(three_symbols + short, {"method": "max_sharpe"})
        dropped_syms = {d["symbol"] for d in res["analysis"].get("dropped_symbols", [])}
        assert "SHORT" in dropped_syms
        assert res["result"] is True  # 나머지 3종목으로 최적화 성공


class TestMissingDependency:
    @pytest.mark.asyncio
    async def test_extra_not_installed(self, three_symbols, monkeypatch):
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name.startswith("pypfopt"):
                raise ModuleNotFoundError("No module named 'pypfopt'", name="pypfopt")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        with pytest.raises(MissingDependencyError) as ei:
            await portfolio_optimizer_condition(three_symbols, {"method": "max_sharpe"})
        err = ei.value
        assert err.extra == "portfolio"
        assert err.transitive is False
        assert "portfolio" in err.install_hint

    @pytest.mark.asyncio
    async def test_transitive_dependency_missing(self, three_symbols, monkeypatch):
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "pandas":
                raise ModuleNotFoundError("No module named 'pandas'", name="pandas")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        with pytest.raises(MissingDependencyError) as ei:
            await portfolio_optimizer_condition(three_symbols, {"method": "max_sharpe"})
        err = ei.value
        assert err.extra == "portfolio"
        assert err.transitive is True
        assert err.package == "pandas"
