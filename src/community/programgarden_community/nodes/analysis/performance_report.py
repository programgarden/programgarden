"""
ProgramGarden Community - PerformanceReportNode (quantstats)

백테스트/실계좌 수익 시계열(equity/returns/prices)로부터 성과·리스크 지표를
산출하는 분석 노드. quantstats 백엔드(perf extra), matplotlib Agg(헤드리스) 강제.

- heavy import(quantstats/pandas/matplotlib)는 execute() 내부 lazy → base(no-extras)
  격리 유지(모듈 top-level 에 heavy import 없음).
- 미설치/부분설치 extra → MissingDependencyError(무음 no-op 금지, install hint 동봉).
- <3 관측치 → metrics=None + summary.error.reason="insufficient_data"(dry_run 안전).
- NaN/inf → None sanitize(JSON 직렬화 가능).

사용 예시:
    {
        "id": "perf",
        "type": "PerformanceReportNode",
        "data": "{{ nodes.backtest.equity_curve }}",
        "data_kind": "equity"
    }
"""

import logging
from typing import Optional, List, Literal, Dict, Any, ClassVar
from pydantic import Field

logger = logging.getLogger("programgarden_community.nodes.analysis.performance_report")

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
)
from programgarden_core.exceptions import MissingDependencyError

try:  # FieldSchema는 타입힌트/스키마용 — 런타임 heavy 아님
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from programgarden_core.models.field_binding import FieldSchema
except Exception:  # pragma: no cover
    pass


_INSTALL_HINT = "pip install 'programgarden-community[perf]'"


class PerformanceReportNode(BaseNode):
    """성과·리스크 리포트 노드 (quantstats)."""

    type: Literal["PerformanceReportNode"] = "PerformanceReportNode"
    category: NodeCategory = NodeCategory.ANALYSIS
    description: str = "i18n:nodes.PerformanceReportNode.description"
    _img_url: ClassVar[str] = ""

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Compute risk/return metrics (Sharpe, Sortino, max drawdown, CAGR, volatility, Calmar) from a backtest equity curve or a live-account P&L series",
            "Produce a drawdown time series to visualize with a LineChartNode after a BacktestEngineNode run",
            "Estimate beta and alpha of a strategy against a benchmark return series",
        ],
        "when_not_to_use": [
            "For generating trade signals or sizing orders — this node only reports on an already-produced return/equity series",
            "For real-time per-tick evaluation — feed it a completed series once (e.g. at end of backtest or on a daily schedule), not on every tick",
            "When you only need a single ratio already produced by a POSITION plugin (SharpeRatioMonitor, SortinoRatio, CalmarRatio) inside the trading loop",
        ],
        "typical_scenarios": [
            "BacktestEngineNode → PerformanceReportNode (data_kind='equity') → TableDisplayNode",
            "SQLiteNode (daily equity) → PerformanceReportNode → LineChartNode (drawdown_series)",
            "PerformanceReportNode (returns + benchmark) → TableDisplayNode (beta/alpha)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "quantstats-backed metrics: Sharpe, Sortino, max drawdown, CAGR, annualized volatility, Calmar — all NaN/inf sanitized to null for JSON safety",
        "Accepts three input kinds via data_kind: 'equity' (equity curve), 'prices' (price level), or 'returns' (periodic returns) — converts to returns internally",
        "Headless by design: forces the matplotlib 'Agg' backend before importing quantstats, so it runs on servers with no display",
        "Optional benchmark series yields beta and alpha (quantstats greeks)",
        "Requires the optional 'perf' extra; a missing or partially-installed extra raises a structured MissingDependencyError with an install hint instead of silently no-op'ing",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Passing fewer than 3 observations and expecting metrics",
            "reason": "Risk ratios are undefined on 1–2 points; the node returns metrics=null with summary.error.reason='insufficient_data' rather than fabricating a value.",
            "alternative": "Feed a full equity/return series (dozens+ of observations). Guard downstream nodes on summary.error being absent.",
        },
        {
            "pattern": "Calling PerformanceReportNode on every real-time tick",
            "reason": "It recomputes the full report over the whole series each call; per-tick use wastes CPU and re-imports quantstats.",
            "alternative": "Run it once when a backtest completes, or on a daily ScheduleNode, and cache the result.",
        },
        {
            "pattern": "Feeding prices but leaving data_kind='returns'",
            "reason": "Treating price levels as returns produces meaningless metrics (huge 'returns' equal to the price magnitudes).",
            "alternative": "Set data_kind to 'equity' or 'prices' for level series; use 'returns' only for periodic return series.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Sharpe & drawdown from an equity curve",
            "description": "Report risk/return metrics from an inline equity curve and display the metrics table.",
            "workflow_snippet": {
                "id": "perf_equity_report",
                "name": "Performance Report (equity)",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {
                        "id": "perf",
                        "type": "PerformanceReportNode",
                        "data": [
                            {"date": "2024-01-01", "close": 100.0},
                            {"date": "2024-01-02", "close": 101.0},
                            {"date": "2024-01-03", "close": 100.5},
                            {"date": "2024-01-04", "close": 102.0},
                            {"date": "2024-01-05", "close": 103.5},
                        ],
                        "data_kind": "equity",
                        "value_field": "close",
                    },
                    {"id": "display", "type": "TableDisplayNode", "data": "{{ nodes.perf.metrics }}"},
                ],
                "edges": [
                    {"from": "start", "to": "perf"},
                    {"from": "perf", "to": "display"},
                ],
            },
            "expected_output": "metrics: {sharpe, sortino, max_drawdown, cagr, volatility, calmar}. drawdown_series: [{date, drawdown}]. summary: {observations, data_kind, has_benchmark:false}.",
        },
        {
            "title": "Beta/alpha vs a benchmark",
            "description": "Compute strategy beta and alpha against a benchmark return series.",
            "workflow_snippet": {
                "id": "perf_benchmark_report",
                "name": "Performance Report (benchmark)",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {
                        "id": "perf",
                        "type": "PerformanceReportNode",
                        "data": [
                            {"date": "2024-01-01", "value": 0.004},
                            {"date": "2024-01-02", "value": -0.002},
                            {"date": "2024-01-03", "value": 0.006},
                            {"date": "2024-01-04", "value": 0.001},
                            {"date": "2024-01-05", "value": -0.003},
                        ],
                        "data_kind": "returns",
                        "value_field": "value",
                        "benchmark": [
                            {"date": "2024-01-01", "value": 0.003},
                            {"date": "2024-01-02", "value": -0.001},
                            {"date": "2024-01-03", "value": 0.004},
                            {"date": "2024-01-04", "value": 0.0},
                            {"date": "2024-01-05", "value": -0.002},
                        ],
                    },
                    {"id": "display", "type": "TableDisplayNode", "data": "{{ nodes.perf.metrics }}"},
                ],
                "edges": [
                    {"from": "start", "to": "perf"},
                    {"from": "perf", "to": "display"},
                ],
            },
            "expected_output": "metrics includes beta and alpha alongside the base ratios. summary.has_benchmark: true.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "Bind 'data' to an array of numbers or of {date, <value_field>} dicts (e.g. an equity curve from BacktestEngineNode). Set 'data_kind' to 'equity'/'prices' for level series or 'returns' for periodic returns. 'value_field' names the numeric key when rows are dicts (auto-falls back to close/value/equity/return). Optional 'benchmark' enables beta/alpha.",
        "output_consumption": "Consume 'metrics' (object) as the primary numeric result, 'drawdown_series' (array of {date, drawdown}) for charting, 'report' (formatted text) for display, and 'summary' (counts + optional error) for validation. On insufficient data, metrics is null and summary.error.reason is 'insufficient_data'.",
        "common_combinations": [
            "BacktestEngineNode → PerformanceReportNode → TableDisplayNode",
            "PerformanceReportNode → LineChartNode (drawdown_series)",
            "SQLiteNode (equity history) → PerformanceReportNode",
        ],
        "pitfalls": [
            "Requires the 'perf' extra: pip install 'programgarden-community[perf]'. Without it the node raises MissingDependencyError.",
            "Needs a DatetimeIndex internally — provide a 'date' field per row for accurate drawdown dates; otherwise a synthetic daily index is used.",
            "At least 3 observations are required; fewer yields metrics=null with an explicit insufficient_data reason.",
        ],
    }

    # === PARAMETERS ===
    data: Any = Field(
        default_factory=list,
        description="i18n:fields.PerformanceReportNode.data",
    )
    data_kind: str = Field(
        default="equity",
        description="i18n:fields.PerformanceReportNode.data_kind",
    )
    value_field: str = Field(
        default="close",
        description="i18n:fields.PerformanceReportNode.value_field",
    )
    benchmark: Any = Field(
        default=None,
        description="i18n:fields.PerformanceReportNode.benchmark",
    )
    periods_per_year: int = Field(
        default=252,
        ge=1,
        le=525600,
        description="i18n:fields.PerformanceReportNode.periods_per_year",
    )
    risk_free_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="i18n:fields.PerformanceReportNode.risk_free_rate",
    )

    _inputs: List[InputPort] = [
        InputPort(name="trigger", type="signal", description="i18n:ports.trigger", required=False),
        InputPort(name="data", type="array", description="i18n:fields.PerformanceReportNode.data", required=False),
        InputPort(name="benchmark", type="array", description="i18n:fields.PerformanceReportNode.benchmark", required=False),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="metrics", type="object", description="i18n:outputs.PerformanceReportNode.metrics"),
        OutputPort(name="report", type="string", description="i18n:outputs.PerformanceReportNode.report"),
        OutputPort(name="drawdown_series", type="array", description="i18n:outputs.PerformanceReportNode.drawdown_series"),
        OutputPort(name="summary", type="object", description="i18n:outputs.PerformanceReportNode.summary"),
    ]

    _version: ClassVar[str] = "1.0.0"
    _updated_at: ClassVar[str] = "2026-07-11"
    _change_note: ClassVar[Optional[str]] = "Initial release: quantstats-backed performance/risk report (perf extra)."

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import (
            FieldSchema, FieldType, FieldCategory, ExpressionMode,
        )
        return {
            "data": FieldSchema(
                name="data",
                type=FieldType.ARRAY,
                description="i18n:fields.PerformanceReportNode.data",
                required=True,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
                expected_type="list",
            ),
            "data_kind": FieldSchema(
                name="data_kind",
                type=FieldType.ENUM,
                description="i18n:fields.PerformanceReportNode.data_kind",
                default="equity",
                required=False,
                enum_values=["equity", "prices", "returns"],
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
            ),
            "value_field": FieldSchema(
                name="value_field",
                type=FieldType.STRING,
                description="i18n:fields.PerformanceReportNode.value_field",
                default="close",
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                expected_type="str",
            ),
            "benchmark": FieldSchema(
                name="benchmark",
                type=FieldType.ARRAY,
                description="i18n:fields.PerformanceReportNode.benchmark",
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
                expected_type="list",
            ),
            "periods_per_year": FieldSchema(
                name="periods_per_year",
                type=FieldType.NUMBER,
                description="i18n:fields.PerformanceReportNode.periods_per_year",
                default=252,
                min=1,
                max=525600,
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
            ),
            "risk_free_rate": FieldSchema(
                name="risk_free_rate",
                type=FieldType.NUMBER,
                description="i18n:fields.PerformanceReportNode.risk_free_rate",
                default=0.0,
                min=0.0,
                max=1.0,
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
            ),
        }

    # ---- helpers ----
    @staticmethod
    def _finite(x: Any, digits: int = 4) -> Optional[float]:
        import math
        try:
            v = float(x)
        except (TypeError, ValueError):
            return None
        if math.isnan(v) or math.isinf(v):
            return None
        return round(v, digits)

    @staticmethod
    def _extract(rows: Any, value_field: str):
        """rows(list of number|dict) → (dates, values). 숫자 실패 시 건너뜀."""
        import math
        dates: List[Any] = []
        vals: List[float] = []
        if not isinstance(rows, list):
            return dates, vals
        fallbacks = (value_field, "close", "value", "equity", "nav", "return", "ret", "pnl")
        for row in rows:
            v = None
            d = None
            if isinstance(row, (int, float)):
                v = float(row)
            elif isinstance(row, dict):
                for k in fallbacks:
                    if k in row and row[k] is not None:
                        try:
                            v = float(row[k])
                        except (TypeError, ValueError):
                            v = None
                        break
                d = row.get("date") or row.get("datetime") or row.get("time")
            if v is None or math.isnan(v) or math.isinf(v):
                continue
            dates.append(d)
            vals.append(v)
        return dates, vals

    def _load_qs(self):
        """quantstats + pandas lazy import (Agg 강제, 부분설치 구분)."""
        import os
        os.environ.setdefault("MPLBACKEND", "Agg")  # headless — import 전
        try:
            import pandas as pd  # noqa
            import quantstats as qs  # noqa
        except ImportError as e:
            missing = (getattr(e, "name", "") or "").split(".")[0]
            if missing in ("quantstats", "", None):
                raise MissingDependencyError(
                    "quantstats not installed",
                    extra="perf", package="quantstats",
                    install_hint=_INSTALL_HINT, node_id=self.id,
                )
            raise MissingDependencyError(
                f"perf extra present but transitive dependency '{missing}' missing (partial/broken install)",
                extra="perf", package=missing, transitive=True,
                install_hint=f"{_INSTALL_HINT} --force-reinstall  # ensure setuptools/matplotlib present",
                node_id=self.id,
            )
        return pd, qs

    def _build_returns(self, pd, rows: Any):
        """rows → pandas 수익률 Series(DatetimeIndex). data_kind 반영."""
        dates, vals = self._extract(rows, self.value_field)
        if len(vals) < 2:
            return None, len(vals)
        # DatetimeIndex 구성 (drawdown 계열 quantstats 요구)
        idx = None
        if all(d is not None for d in dates) and len(dates) == len(vals):
            try:
                idx = pd.to_datetime(dates)
                if idx.isna().any():
                    idx = None
            except Exception:
                idx = None
        if idx is None:
            idx = pd.date_range("2000-01-01", periods=len(vals), freq="D")
        series = pd.Series(vals, index=idx).sort_index()
        if self.data_kind == "returns":
            returns = series
        else:  # equity / prices
            returns = series.pct_change().dropna()
        return returns, len(vals)

    async def execute(self, context: Any) -> Dict[str, Any]:
        pd, qs = self._load_qs()

        returns, n_obs = self._build_returns(pd, self.data)
        if returns is None or len(returns) < 3:
            return {
                "metrics": None,
                "report": None,
                "drawdown_series": [],
                "summary": {
                    "observations": n_obs,
                    "data_kind": self.data_kind,
                    "has_benchmark": bool(self.benchmark),
                    "error": {"reason": "insufficient_data",
                              "message": "need >=3 observations for performance metrics"},
                },
            }

        ppy = int(self.periods_per_year)
        rf = float(self.risk_free_rate)

        def _safe(fn, *a, **kw):
            try:
                return self._finite(fn(*a, **kw))
            except Exception as e:  # noqa: BLE001 — 지표 실패는 None(무음 NaN 금지)
                logger.debug("metric %s failed: %s", getattr(fn, "__name__", fn), e)
                return None

        metrics: Dict[str, Any] = {
            "sharpe": _safe(qs.stats.sharpe, returns, rf, ppy),
            "sortino": _safe(qs.stats.sortino, returns, rf, ppy),
            "max_drawdown": _safe(qs.stats.max_drawdown, returns),
            "cagr": _safe(qs.stats.cagr, returns),
            "volatility": _safe(qs.stats.volatility, returns, ppy),
            "calmar": _safe(qs.stats.calmar, returns),
        }

        # 벤치마크 → beta/alpha (인덱스 정렬)
        if self.benchmark:
            b_dates, b_vals = self._extract(self.benchmark, self.value_field)
            if len(b_vals) >= 2:
                nmin = min(len(returns), len(b_vals))
                # 동일 인덱스로 정렬(위치 기준) — 교차 정렬 실패 방지
                bench_ret = pd.Series(b_vals[:nmin], index=returns.index[:nmin])
                if self.data_kind != "returns":
                    bench_ret = bench_ret.pct_change().dropna()
                main = returns.iloc[:len(bench_ret)] if len(bench_ret) < len(returns) else returns.iloc[:nmin]
                try:
                    g = qs.stats.greeks(main, bench_ret)
                    metrics["beta"] = self._finite(g.get("beta"))
                    metrics["alpha"] = self._finite(g.get("alpha"))
                except Exception as e:  # noqa: BLE001
                    logger.debug("greeks failed: %s", e)
                    metrics["beta"] = None
                    metrics["alpha"] = None

        # drawdown series
        drawdown_series: List[Dict[str, Any]] = []
        try:
            dd = qs.stats.to_drawdown_series(returns)
            for ts, val in dd.items():
                fv = self._finite(val)
                if fv is None:
                    continue
                try:
                    date_str = ts.strftime("%Y-%m-%d")
                except Exception:
                    date_str = str(ts)
                drawdown_series.append({"date": date_str, "drawdown": fv})
        except Exception as e:  # noqa: BLE001
            logger.debug("drawdown series failed: %s", e)

        # human report
        lines = ["Performance Report"]
        for k, v in metrics.items():
            lines.append(f"  {k}: {v if v is not None else 'n/a'}")
        report = "\n".join(lines)

        summary = {
            "observations": n_obs,
            "return_points": int(len(returns)),
            "data_kind": self.data_kind,
            "periods_per_year": ppy,
            "risk_free_rate": rf,
            "has_benchmark": bool(self.benchmark),
        }

        return {
            "metrics": metrics,
            "report": report,
            "drawdown_series": drawdown_series,
            "summary": summary,
        }
