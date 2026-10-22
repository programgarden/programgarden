"""
PortfolioOptimizer (평균-분산 포트폴리오 최적화) 플러그인 — PyPortfolioOpt 백엔드.

Efficient Frontier 기반 평균-분산 최적화. method enum:
- max_sharpe: 샤프비율 최대화
- min_volatility: 분산(변동성) 최소화
- efficient_risk: 목표 변동성 하에서 수익 최대화

⚠️ HRP(계층적 리스크 패리티)는 scipy 1.18 의 hierarchy._LINKAGE_METHODS 제거로
pyportfolioopt HRPOpt 가 AttributeError → 본 플러그인 method enum 에서 제외.
(RiskParity 플러그인과의 중복 우려도 이로써 자연 해소.)

RiskParity 와의 차별화: RiskParity 는 각 자산의 위험기여도를 균등화(inverse-vol/ERC)하는
반면, PortfolioOptimizer 는 Efficient Frontier 위에서 샤프 최대화 / 분산 최소화를 수행한다.

⚠️ 교차종목(cross-sectional) 플러그인: 공분산 행렬이 전 종목을 함께 봐야 하므로
ConditionNode 단일 호출에 ≤100 종목만 전달하거나 NodeRunner 로 실행하라. 심볼 >100 이면
executor 가 100개 청크로 분할(execute_batched)하여 청크별로 공분산을 오계산한다(무음 오류).

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, close, ...}, ...]
- fields: {method, lookback, target_volatility, risk_free_rate, min_weight_pct, max_weight_pct}

heavy 의존성: 'portfolio' extra (pip install 'programgarden-community[portfolio]').
미설치/부분설치 시 MissingDependencyError(무음 no-op 금지). 헤비 import 는 함수 내부 lazy.
"""

from typing import List, Dict, Any, Optional
import math

from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType
from programgarden_core.exceptions import MissingDependencyError


PORTFOLIO_OPTIMIZER_SCHEMA = PluginSchema(
    id="PortfolioOptimizer",
    name="Portfolio Optimizer (PyPortfolioOpt)",
    category=PluginCategory.POSITION,
    version="1.0.0",
    description=(
        "Mean-variance portfolio optimization on the Efficient Frontier via PyPortfolioOpt. "
        "Methods: max_sharpe (maximize Sharpe), min_volatility (minimize variance), "
        "efficient_risk (maximize return at a target volatility). HRP is intentionally "
        "excluded (scipy 1.18 broke pyportfolioopt HRPOpt). Distinct from the RiskParity "
        "plugin, which equalizes each asset's risk contribution (inverse-vol/ERC) rather "
        "than optimizing the frontier. Cross-sectional: pass <=100 symbols in one "
        "ConditionNode call (or use NodeRunner) — >100 triggers executor batching that "
        "corrupts the cross-symbol covariance. Requires the 'portfolio' extra "
        "(pip install 'programgarden-community[portfolio]')."
    ),
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "method": {
            "type": "string",
            "default": "max_sharpe",
            "title": "Optimization Method",
            "description": "max_sharpe / min_volatility / efficient_risk (HRP excluded — scipy 1.18 incompat)",
            "enum": ["max_sharpe", "min_volatility", "efficient_risk"],
        },
        "lookback": {
            "type": "int",
            "default": 252,
            "title": "Lookback Period",
            "description": "Number of most-recent price observations per symbol used to estimate returns/covariance",
            "ge": 30,
            "le": 2000,
        },
        "target_volatility": {
            "type": "float",
            "default": 15.0,
            "title": "Target Volatility (%)",
            "description": "Annual target volatility for efficient_risk method (ignored by other methods)",
            "ge": 1.0,
            "le": 100.0,
        },
        "risk_free_rate": {
            "type": "float",
            "default": 2.0,
            "title": "Risk-Free Rate (%)",
            "description": "Annual risk-free rate for max_sharpe and Sharpe reporting",
            "ge": 0.0,
            "le": 50.0,
        },
        "min_weight_pct": {
            "type": "float",
            "default": 0.0,
            "title": "Min Weight (%)",
            "description": "Lower bound per asset weight (long-only). 0 = allow zero allocation",
            "ge": 0.0,
            "le": 100.0,
        },
        "max_weight_pct": {
            "type": "float",
            "default": 100.0,
            "title": "Max Weight (%)",
            "description": "Upper bound per asset weight",
            "ge": 1.0,
            "le": 100.0,
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close"],
    optional_fields=[],
    tags=["portfolio", "optimization", "efficient_frontier", "mean_variance", "max_sharpe", "allocation"],
    output_fields={
        "weight_pct": {"type": "float", "description": "Optimized portfolio weight for this symbol (%)"},
        "signal": {"type": "str", "description": "buy if weight > 0 else hold"},
        "side": {"type": "str", "description": "long"},
    },
    locales={
        "ko": {
            "name": "포트폴리오 최적화 (PyPortfolioOpt)",
            "description": (
                "Efficient Frontier 기반 평균-분산 포트폴리오 최적화. method: max_sharpe(샤프 최대화)/"
                "min_volatility(분산 최소화)/efficient_risk(목표 변동성 하 수익 최대화). HRP 는 scipy 1.18 "
                "비호환으로 제외. RiskParity(위험기여도 균등화)와 달리 프론티어 위에서 최적화. 교차종목 "
                "플러그인이므로 ≤100 종목 또는 NodeRunner 사용. 'portfolio' extra 필요."
            ),
            "fields.method": "최적화 방식 (max_sharpe / min_volatility / efficient_risk)",
            "fields.lookback": "종목별 최근 가격 관측치 수 (수익률·공분산 추정용)",
            "fields.target_volatility": "efficient_risk 목표 연간 변동성 (%)",
            "fields.risk_free_rate": "무위험 수익률 (%) — max_sharpe·샤프 계산용",
            "fields.min_weight_pct": "자산별 최소 비중 (%)",
            "fields.max_weight_pct": "자산별 최대 비중 (%)",
        },
    },
)


def _safe_float(x: Any) -> Optional[float]:
    """숫자 변환 실패/NaN/inf → None (숨은 0 흡수 금지)."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if math.isnan(v) or math.isinf(v):
        return None
    return v


def _sanitize(x: Any, digits: int = 4) -> Optional[float]:
    v = _safe_float(x)
    if v is None:
        return None
    return round(v, digits)


def _empty(reason: str) -> Dict[str, Any]:
    return {
        "passed_symbols": [], "failed_symbols": [],
        "symbol_results": [], "values": [],
        "result": False, "analysis": {"indicator": "PortfolioOptimizer", "error": reason},
    }


async def portfolio_optimizer_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
    context: Any = None,
    **kwargs,
) -> Dict[str, Any]:
    """PyPortfolioOpt Efficient Frontier 포지션 배분."""
    mapping = field_mapping or {}
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")

    method = fields.get("method", "max_sharpe")
    lookback = int(fields.get("lookback", 252))
    target_vol = _safe_float(fields.get("target_volatility", 15.0)) or 15.0
    rf = (_safe_float(fields.get("risk_free_rate", 2.0)) or 0.0) / 100.0
    min_wt = (_safe_float(fields.get("min_weight_pct", 0.0)) or 0.0) / 100.0
    max_wt = (_safe_float(fields.get("max_weight_pct", 100.0)) or 1.0) / 100.0

    if not data or not isinstance(data, list):
        return _empty("No data provided")

    # 종목별 그룹화 (날짜 오름차순)
    symbol_rows: Dict[str, List[Dict]] = {}
    symbol_exchange: Dict[str, str] = {}
    for row in data:
        if not isinstance(row, dict):
            continue
        sym = row.get(symbol_field, "")
        if not sym:
            continue
        symbol_rows.setdefault(sym, []).append(row)
        symbol_exchange.setdefault(sym, row.get(exchange_field, "UNKNOWN"))

    if not symbol_rows:
        return _empty("No symbols in data")

    dropped: List[Dict[str, str]] = []
    price_map: Dict[str, Dict[str, float]] = {}  # symbol -> {date: close}
    for sym, rows in symbol_rows.items():
        rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))
        series: Dict[str, float] = {}
        for r in rows_sorted:
            d = r.get(date_field)
            c = _safe_float(r.get(close_field))
            if d is None or c is None or c <= 0:
                continue
            series[str(d)] = c
        # 최근 lookback 관측치만
        if len(series) > lookback:
            keep = sorted(series.keys())[-lookback:]
            series = {k: series[k] for k in keep}
        if len(series) < 20:
            dropped.append({"symbol": sym, "exchange": symbol_exchange.get(sym, "UNKNOWN"),
                            "reason": "insufficient_history"})
            continue
        price_map[sym] = series

    if len(price_map) < 2:
        res = _empty("Need >=2 symbols with sufficient aligned price history")
        res["failed_symbols"] = [{"symbol": d["symbol"], "exchange": d["exchange"]} for d in dropped]
        res["analysis"]["dropped_symbols"] = dropped
        return res

    # 심볼 >100 경고 (executor batching 오염 방지 문서화 — 여기선 방출 경고)
    warning = None
    if len(price_map) > 100:
        warning = ("received >100 symbols in one call — executor batching may corrupt "
                   "cross-symbol covariance; use NodeRunner or split to <=100")

    # === heavy import (lazy) ===
    try:
        import pandas as pd
        from pypfopt import EfficientFrontier, expected_returns, risk_models
    except ImportError as e:
        missing = (getattr(e, "name", "") or "").split(".")[0]
        if missing in ("pypfopt", "", None):
            raise MissingDependencyError(
                "pyportfolioopt not installed",
                extra="portfolio", package="pyportfolioopt",
                install_hint="pip install 'programgarden-community[portfolio]'",
            )
        raise MissingDependencyError(
            f"portfolio extra present but transitive dependency '{missing}' missing (partial/broken install)",
            extra="portfolio", package=missing, transitive=True,
            install_hint="pip install 'programgarden-community[portfolio]' --force-reinstall",
        )

    # 와이드 가격 행렬 (index=date, columns=symbol) — 정렬 불가 종목 dropna
    prices = pd.DataFrame(price_map)  # columns=symbol, index=date(union)
    prices = prices.sort_index()
    before_cols = set(prices.columns)
    aligned = prices.dropna(axis=1)
    after_cols = set(aligned.columns)
    for sym in (before_cols - after_cols):
        dropped.append({"symbol": sym, "exchange": symbol_exchange.get(sym, "UNKNOWN"),
                        "reason": "no_overlap"})

    if aligned.shape[1] < 2 or aligned.shape[0] < 20:
        res = _empty("Insufficient aligned observations after intersection (need >=2 symbols, >=20 rows)")
        res["failed_symbols"] = [{"symbol": d["symbol"], "exchange": d["exchange"]} for d in dropped]
        res["analysis"]["dropped_symbols"] = dropped
        if warning:
            res["analysis"]["warning"] = warning
        return res

    # === Efficient Frontier 최적화 ===
    try:
        mu = expected_returns.mean_historical_return(aligned)
        S = risk_models.CovarianceShrinkage(aligned).ledoit_wolf()
        ef = EfficientFrontier(mu, S, weight_bounds=(min_wt, max_wt))
        if method == "min_volatility":
            ef.min_volatility()
        elif method == "efficient_risk":
            ef.efficient_risk(target_volatility=target_vol / 100.0)
        else:  # max_sharpe (default)
            ef.max_sharpe(risk_free_rate=rf)
        cleaned = ef.clean_weights()
        perf = ef.portfolio_performance(risk_free_rate=rf)  # (ret, vol, sharpe)
    except Exception as e:  # noqa: BLE001 — OptimizationError 포함 전부 명시 error 로 (무음 금지)
        res = _empty(f"optimization failed ({method}): {type(e).__name__}: {e}")
        res["failed_symbols"] = [{"symbol": d["symbol"], "exchange": d["exchange"]} for d in dropped]
        res["analysis"]["dropped_symbols"] = dropped
        res["analysis"]["method"] = method
        if warning:
            res["analysis"]["warning"] = warning
        return res

    passed, symbol_results, values = [], [], []
    for sym in aligned.columns:
        w = _sanitize((cleaned.get(sym, 0.0)) * 100.0, 2) or 0.0
        exchange = symbol_exchange.get(sym, "UNKNOWN")
        signal = "buy" if w > 0 else "hold"
        passed.append({"symbol": sym, "exchange": exchange})
        symbol_results.append({"symbol": sym, "exchange": exchange, "weight_pct": w,
                               "signal": signal, "side": "long"})
        values.append({"symbol": sym, "exchange": exchange,
                       "time_series": [{"weight_pct": w, "signal": signal, "side": "long"}]})

    failed = [{"symbol": d["symbol"], "exchange": d["exchange"]} for d in dropped]

    analysis = {
        "indicator": "PortfolioOptimizer",
        "method": method,
        "total_symbols": len(passed),
        "expected_return_pct": _sanitize(perf[0] * 100.0, 2),
        "volatility_pct": _sanitize(perf[1] * 100.0, 2),
        "sharpe": _sanitize(perf[2], 3),
    }
    if dropped:
        analysis["dropped_symbols"] = dropped
    if warning:
        analysis["warning"] = warning

    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "symbol_results": symbol_results,
        "values": values,
        "result": len(passed) > 0,
        "analysis": analysis,
    }


__all__ = ["portfolio_optimizer_condition", "PORTFOLIO_OPTIMIZER_SCHEMA"]
