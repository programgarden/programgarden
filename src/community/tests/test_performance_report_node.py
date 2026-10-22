"""
PerformanceReportNode (quantstats) 테스트.

- 스키마/등록 + 5 AI-meta + 3 version ClassVar (enforcement 은 별도 metadata 테스트)
- happy-path: equity/returns → 지표 산출, drawdown_series 방출, JSON 유한
- benchmark → beta/alpha
- <3 관측치 → metrics=None + insufficient_data (dry_run 안전)
- Agg backend 강제
- 미설치/부분설치 extra → MissingDependencyError(.extra/.transitive/install_hint)
"""

import builtins
import json
import os

import pytest

from programgarden_core.exceptions import MissingDependencyError
from programgarden_community.nodes.analysis import PerformanceReportNode


def _equity_with_drawdown(n=60):
    """상승→하락→회복 자산곡선 (실제 낙폭 존재)."""
    rows = []
    price = 100.0
    for i in range(n):
        if i < 20:
            price *= 1.01
        elif i < 35:
            price *= 0.985   # 낙폭 구간
        else:
            price *= 1.008
        rows.append({"date": f"2024-03-{(i % 28) + 1:02d}", "close": round(price, 4),
                     "seq": i})
    # 날짜 유니크 보장 위해 순차 날짜 재구성
    import datetime as _dt
    base = _dt.date(2024, 1, 1)
    for i, r in enumerate(rows):
        r["date"] = (base + _dt.timedelta(days=i)).isoformat()
    return rows


class TestSchemaAndMetadata:
    def test_type_and_category(self):
        node = PerformanceReportNode(id="p")
        assert node.type == "PerformanceReportNode"
        assert node.category.value == "analysis"

    def test_version_classvars_declared_in_dict(self):
        # 상속 fallback 차단: 클래스 본문에 직접 선언
        for attr in ("_version", "_updated_at", "_change_note"):
            assert attr in PerformanceReportNode.__dict__, f"{attr} not declared on class"

    def test_ai_meta_shape(self):
        assert set(PerformanceReportNode._usage) >= {"when_to_use", "when_not_to_use", "typical_scenarios"}
        assert len(PerformanceReportNode._features) >= 2
        assert len(PerformanceReportNode._examples) >= 2
        for ex in PerformanceReportNode._examples:
            assert "workflow_snippet" in ex


class TestHappyPath:
    @pytest.mark.asyncio
    async def test_equity_metrics_and_drawdown(self):
        node = PerformanceReportNode(id="p", data=_equity_with_drawdown(), data_kind="equity", value_field="close")
        res = await node.execute(None)
        m = res["metrics"]
        assert m is not None
        assert set(m) >= {"sharpe", "sortino", "max_drawdown", "cagr", "volatility", "calmar"}
        assert m["max_drawdown"] is not None and m["max_drawdown"] < 0, "real drawdown expected"
        assert len(res["drawdown_series"]) > 0
        assert res["drawdown_series"][0].keys() >= {"date", "drawdown"}
        # JSON 유한 (NaN/inf 없음)
        assert json.dumps(res, allow_nan=False)
        assert res["summary"]["has_benchmark"] is False

    @pytest.mark.asyncio
    async def test_returns_kind(self):
        data = [{"date": f"2024-04-{i + 1:02d}", "value": (0.006 if i % 2 == 0 else -0.004)} for i in range(30)]
        node = PerformanceReportNode(id="p", data=data, data_kind="returns", value_field="value")
        res = await node.execute(None)
        assert res["metrics"]["sharpe"] is not None
        assert res["summary"]["data_kind"] == "returns"

    @pytest.mark.asyncio
    async def test_benchmark_beta_alpha(self):
        data = [{"date": f"2024-05-{i + 1:02d}", "value": (0.007 if i % 2 == 0 else -0.003)} for i in range(30)]
        bench = [{"date": f"2024-05-{i + 1:02d}", "value": (0.005 if i % 2 == 0 else -0.002)} for i in range(30)]
        node = PerformanceReportNode(id="p", data=data, data_kind="returns", value_field="value", benchmark=bench)
        res = await node.execute(None)
        assert "beta" in res["metrics"] and res["metrics"]["beta"] is not None
        assert "alpha" in res["metrics"]
        assert res["summary"]["has_benchmark"] is True


class TestGuards:
    @pytest.mark.asyncio
    async def test_insufficient_data(self):
        node = PerformanceReportNode(id="p", data=[{"close": 100}, {"close": 101}], data_kind="equity")
        res = await node.execute(None)
        assert res["metrics"] is None
        assert res["summary"]["error"]["reason"] == "insufficient_data"
        assert res["drawdown_series"] == []
        assert json.dumps(res, allow_nan=False)

    @pytest.mark.asyncio
    async def test_agg_backend_forced(self, monkeypatch):
        monkeypatch.delenv("MPLBACKEND", raising=False)
        node = PerformanceReportNode(id="p", data=_equity_with_drawdown(), data_kind="equity")
        await node.execute(None)
        assert os.environ.get("MPLBACKEND") == "Agg"


class TestMissingDependency:
    @pytest.mark.asyncio
    async def test_extra_not_installed(self, monkeypatch):
        real_import = builtins.__import__

        def fake_import(name, *a, **k):
            if name.startswith("quantstats"):
                raise ModuleNotFoundError("No module named 'quantstats'", name="quantstats")
            return real_import(name, *a, **k)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        node = PerformanceReportNode(id="p", data=_equity_with_drawdown(), data_kind="equity")
        with pytest.raises(MissingDependencyError) as ei:
            await node.execute(None)
        assert ei.value.extra == "perf"
        assert ei.value.transitive is False
        assert "perf" in ei.value.install_hint

    @pytest.mark.asyncio
    async def test_transitive_missing(self, monkeypatch):
        real_import = builtins.__import__

        def fake_import(name, *a, **k):
            if name == "pandas":
                raise ModuleNotFoundError("No module named 'pandas'", name="pandas")
            return real_import(name, *a, **k)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        node = PerformanceReportNode(id="p", data=_equity_with_drawdown(), data_kind="equity")
        with pytest.raises(MissingDependencyError) as ei:
            await node.execute(None)
        assert ei.value.extra == "perf"
        assert ei.value.transitive is True
        assert ei.value.package == "pandas"
