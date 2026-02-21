"""
CorrelationGuard (상관관계 가드) 플러그인

포트폴리오 상관관계 모니터링. 상관도가 임계치를 초과하면
regime 전환(히스테리시스) 및 포지션 축소를 추천합니다.

입력 형식:
- data: 플랫 배열 (2개 이상 종목 데이터 포함)
- fields: {lookback, correlation_threshold, recovery_threshold, action, reduce_by_pct, method}
"""

from typing import List, Dict, Any, Optional, Set
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


# risk_features 선언
risk_features: Set[str] = {"state", "events"}

CORRELATION_GUARD_SCHEMA = PluginSchema(
    id="CorrelationGuard",
    name="Correlation Guard",
    category=PluginCategory.POSITION,
    version="1.0.0",
    description="Monitors portfolio correlation regime. Triggers risk reduction when average correlation exceeds threshold. Uses hysteresis to prevent regime flipping.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "lookback": {
            "type": "int",
            "default": 60,
            "title": "Lookback Period",
            "description": "Rolling correlation window",
            "ge": 20,
            "le": 252,
        },
        "correlation_threshold": {
            "type": "float",
            "default": 0.8,
            "title": "Correlation Threshold",
            "description": "Threshold to enter high-correlation regime",
            "ge": 0.3,
            "le": 0.99,
        },
        "recovery_threshold": {
            "type": "float",
            "default": 0.6,
            "title": "Recovery Threshold",
            "description": "Threshold to return to normal regime",
            "ge": 0.1,
            "le": 0.95,
        },
        "action": {
            "type": "string",
            "default": "reduce_pct",
            "title": "Action",
            "description": "Action on high correlation",
            "enum": ["reduce_pct", "alert_only", "exit_highest"],
        },
        "reduce_by_pct": {
            "type": "float",
            "default": 30.0,
            "title": "Reduce By (%)",
            "description": "Position reduction percentage (when action=reduce_pct)",
            "ge": 10.0,
            "le": 80.0,
        },
        "method": {
            "type": "string",
            "default": "pearson",
            "title": "Method",
            "description": "Correlation calculation method",
            "enum": ["pearson", "spearman"],
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close"],
    optional_fields=[],
    tags=["correlation", "guard", "regime", "risk_management", "diversification"],
    locales={
        "ko": {
            "name": "상관관계 가드 (Correlation Guard)",
            "description": "포트폴리오의 상관관계 레짐을 모니터링합니다. 평균 상관계수가 임계값을 초과하면 위험 축소 조치를 취합니다. 히스테리시스를 적용하여 레짐 전환 빈도를 줄입니다.",
            "fields.lookback": "롤링 상관계수 계산 기간",
            "fields.correlation_threshold": "고상관 레짐 진입 임계값",
            "fields.recovery_threshold": "정상 레짐 복귀 임계값",
            "fields.action": "조치 (reduce_pct/alert_only/exit_highest)",
            "fields.reduce_by_pct": "포지션 축소 비율 (%)",
            "fields.method": "상관계수 계산 방법",
        },
    },
)


def _pearson_correlation(x: List[float], y: List[float]) -> float:
    """피어슨 상관계수 계산"""
    n = len(x)
    if n < 2 or n != len(y):
        return 0.0

    mean_x = sum(x) / n
    mean_y = sum(y) / n

    cov = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    std_x = (sum((xi - mean_x) ** 2 for xi in x)) ** 0.5
    std_y = (sum((yi - mean_y) ** 2 for yi in y)) ** 0.5

    if std_x == 0 or std_y == 0:
        return 0.0

    return cov / (std_x * std_y)


def _spearman_correlation(x: List[float], y: List[float]) -> float:
    """스피어만 순위 상관계수 계산"""
    n = len(x)
    if n < 2 or n != len(y):
        return 0.0

    def _rank(values):
        sorted_indices = sorted(range(len(values)), key=lambda i: values[i])
        ranks = [0.0] * len(values)
        for rank, idx in enumerate(sorted_indices):
            ranks[idx] = rank + 1.0
        return ranks

    rank_x = _rank(x)
    rank_y = _rank(y)
    return _pearson_correlation(rank_x, rank_y)


async def correlation_guard_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
    positions: Optional[Dict[str, Any]] = None,
    context: Any = None,
    **kwargs,
) -> Dict[str, Any]:
    """상관관계 가드 조건 평가"""
    mapping = field_mapping or {}
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")

    lookback = fields.get("lookback", 60)
    corr_threshold = fields.get("correlation_threshold", 0.8)
    recovery_threshold = fields.get("recovery_threshold", 0.6)
    action = fields.get("action", "reduce_pct")
    reduce_by = fields.get("reduce_by_pct", 30.0)
    method = fields.get("method", "pearson")

    if not data or not isinstance(data, list):
        return {
            "passed_symbols": [], "failed_symbols": [],
            "symbol_results": [], "values": [], "pair_correlations": [],
            "result": False, "analysis": {"error": "No data provided"},
        }

    # 종목별 그룹화
    symbol_data_map: Dict[str, List[Dict]] = {}
    symbol_exchange_map: Dict[str, str] = {}
    for row in data:
        if not isinstance(row, dict):
            continue
        sym = row.get(symbol_field, "")
        if not sym:
            continue
        if sym not in symbol_data_map:
            symbol_data_map[sym] = []
            symbol_exchange_map[sym] = row.get(exchange_field, "UNKNOWN")
        symbol_data_map[sym].append(row)

    # 날짜별 종가 맵
    symbol_price_by_date: Dict[str, Dict[str, float]] = {}
    for sym, rows in symbol_data_map.items():
        price_map = {}
        for row in rows:
            date = row.get(date_field, "")
            price = row.get(close_field)
            if date and price is not None:
                try:
                    price_map[date] = float(price)
                except (ValueError, TypeError):
                    pass
        symbol_price_by_date[sym] = price_map

    all_symbols = list(symbol_data_map.keys())
    if len(all_symbols) < 2:
        return {
            "passed_symbols": [], "failed_symbols": [],
            "symbol_results": [], "values": [], "pair_correlations": [],
            "result": False,
            "analysis": {"error": "Need at least 2 symbols for correlation guard"},
        }

    # 모든 페어의 상관계수 계산
    pair_correlations = []
    symbol_max_corr: Dict[str, float] = {}
    symbol_correlated_with: Dict[str, str] = {}

    calc_fn = _spearman_correlation if method == "spearman" else _pearson_correlation

    for i in range(len(all_symbols)):
        for j in range(i + 1, len(all_symbols)):
            sym_a = all_symbols[i]
            sym_b = all_symbols[j]

            dates_a = set(symbol_price_by_date[sym_a].keys())
            dates_b = set(symbol_price_by_date[sym_b].keys())
            common_dates = sorted(dates_a & dates_b)

            if len(common_dates) < lookback:
                continue

            recent_dates = common_dates[-lookback:]
            prices_a = [symbol_price_by_date[sym_a][d] for d in recent_dates]
            prices_b = [symbol_price_by_date[sym_b][d] for d in recent_dates]

            # 수익률 변환
            returns_a = [
                (prices_a[k] - prices_a[k - 1]) / prices_a[k - 1]
                for k in range(1, len(prices_a)) if prices_a[k - 1] > 0
            ]
            returns_b = [
                (prices_b[k] - prices_b[k - 1]) / prices_b[k - 1]
                for k in range(1, len(prices_b)) if prices_b[k - 1] > 0
            ]

            min_len = min(len(returns_a), len(returns_b))
            if min_len < 10:
                continue

            returns_a = returns_a[-min_len:]
            returns_b = returns_b[-min_len:]

            corr = round(calc_fn(returns_a, returns_b), 4)
            pair_correlations.append({
                "symbol_a": sym_a, "symbol_b": sym_b,
                "correlation": corr,
            })

            # 각 종목별 최대 상관계수 업데이트
            for sym, other in [(sym_a, sym_b), (sym_b, sym_a)]:
                abs_corr = abs(corr)
                if sym not in symbol_max_corr or abs_corr > abs(symbol_max_corr[sym]):
                    symbol_max_corr[sym] = corr
                    symbol_correlated_with[sym] = other

    # 평균 상관계수
    if pair_correlations:
        avg_correlation = round(
            sum(abs(p["correlation"]) for p in pair_correlations) / len(pair_correlations), 4
        )
    else:
        avg_correlation = 0.0

    # regime 결정 (히스테리시스)
    prev_regime = "normal"
    has_risk_tracker = context and hasattr(context, "risk_tracker") and context.risk_tracker

    if has_risk_tracker:
        try:
            state = context.risk_tracker.get_state("correlation_guard_regime")
            if state:
                prev_regime = state
        except Exception:
            pass

    if avg_correlation >= corr_threshold:
        regime = "high_correlation"
    elif avg_correlation <= recovery_threshold:
        regime = "normal"
    else:
        regime = prev_regime  # 히스테리시스: 이전 상태 유지

    triggered = regime == "high_correlation"

    # state 저장
    if has_risk_tracker:
        try:
            context.risk_tracker.set_state("correlation_guard_regime", regime)
        except Exception:
            pass

    # risk_event 기록
    if triggered and has_risk_tracker:
        try:
            context.risk_tracker.record_event(
                event_type="high_correlation",
                symbol="PORTFOLIO",
                data={"avg_correlation": avg_correlation, "threshold": corr_threshold, "action": action},
            )
        except Exception:
            pass

    # 결과 집계
    passed, failed, symbol_results, values = [], [], [], []
    target_symbols = symbols or [{"symbol": s, "exchange": symbol_exchange_map.get(s, "UNKNOWN")} for s in all_symbols]

    # exit_highest: 가장 높은 상관계수를 가진 종목 찾기
    highest_corr_symbol = None
    if triggered and action == "exit_highest" and symbol_max_corr:
        highest_corr_symbol = max(symbol_max_corr, key=lambda s: abs(symbol_max_corr[s]))

    for sym_info in target_symbols:
        symbol = sym_info.get("symbol", "") if isinstance(sym_info, dict) else str(sym_info)
        exchange = sym_info.get("exchange", "UNKNOWN") if isinstance(sym_info, dict) else "UNKNOWN"
        sym_dict = {"symbol": symbol, "exchange": exchange}

        max_corr = symbol_max_corr.get(symbol)
        correlated_with = symbol_correlated_with.get(symbol, "")

        action_taken = "hold"
        if triggered:
            if action == "exit_highest" and symbol == highest_corr_symbol:
                action_taken = "exit"
                passed.append(sym_dict)
            elif action == "reduce_pct":
                action_taken = f"reduce_{reduce_by}%"
                passed.append(sym_dict)
            elif action == "alert_only":
                action_taken = "alert"
                failed.append(sym_dict)
            else:
                failed.append(sym_dict)
        else:
            failed.append(sym_dict)

        symbol_results.append({
            "symbol": symbol, "exchange": exchange,
            "max_correlation": max_corr if max_corr is not None else 0.0,
            "correlated_with": correlated_with,
            "regime": regime,
            "action_taken": action_taken,
        })

        time_series = [{
            "correlation": max_corr if max_corr is not None else 0.0,
            "regime": regime,
            "signal": "sell" if action_taken not in ("hold", "alert") else None,
            "side": "short" if action_taken not in ("hold", "alert") else None,
        }]
        values.append({"symbol": symbol, "exchange": exchange, "time_series": time_series})

    return {
        "passed_symbols": passed, "failed_symbols": failed,
        "symbol_results": symbol_results, "values": values,
        "pair_correlations": pair_correlations,
        "result": len(passed) > 0,
        "analysis": {
            "indicator": "CorrelationGuard",
            "avg_correlation": avg_correlation,
            "regime": regime,
            "threshold": corr_threshold,
            "recovery_threshold": recovery_threshold,
            "triggered": triggered,
            "method": method,
            "total_pairs": len(pair_correlations),
        },
    }


__all__ = ["correlation_guard_condition", "CORRELATION_GUARD_SCHEMA", "risk_features"]
