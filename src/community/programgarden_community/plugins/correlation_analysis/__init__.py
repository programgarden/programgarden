"""
CorrelationAnalysis (상관관계 분석) 플러그인

종목 간 롤링 상관계수 계산. 분산 투자 검증 및 페어 트레이딩 탐색.

입력 형식:
- data: 플랫 배열 (2개 이상 종목 데이터 포함)
  [{symbol: "AAPL", date: "20260116", close: 150}, {symbol: "MSFT", ...}, ...]
- fields: {lookback, threshold, direction, method}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


CORRELATION_ANALYSIS_SCHEMA = PluginSchema(
    id="CorrelationAnalysis",
    name="Correlation Analysis",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Calculates rolling correlation between assets. Used for diversification verification and pairs trading detection.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "lookback": {
            "type": "int",
            "default": 60,
            "title": "Lookback Period",
            "description": "Rolling correlation window",
            "ge": 10,
            "le": 252,
        },
        "threshold": {
            "type": "float",
            "default": 0.8,
            "title": "Correlation Threshold",
            "description": "Correlation threshold for filtering",
            "ge": -1.0,
            "le": 1.0,
        },
        "direction": {
            "type": "string",
            "default": "above",
            "title": "Direction",
            "description": "above: high correlation (pairs), below: low correlation (diversification)",
            "enum": ["above", "below"],
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
    tags=["correlation", "diversification", "pairs", "portfolio"],
    locales={
        "ko": {
            "name": "상관관계 분석 (Correlation Analysis)",
            "description": "종목 간 롤링 상관계수를 계산합니다. 포트폴리오 분산 투자 검증이나 페어 트레이딩 대상 탐색에 활용됩니다.",
            "fields.lookback": "롤링 상관계수 계산 기간",
            "fields.threshold": "상관계수 필터링 임계값",
            "fields.direction": "방향 (above: 고상관=페어, below: 저상관=분산)",
            "fields.method": "상관계수 계산 방법 (피어슨/스피어만)",
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


async def correlation_analysis_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """상관관계 분석 조건 평가"""
    mapping = field_mapping or {}
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")

    lookback = fields.get("lookback", 60)
    threshold = fields.get("threshold", 0.8)
    direction = fields.get("direction", "above")
    method = fields.get("method", "pearson")

    if not data or not isinstance(data, list):
        return {
            "passed_symbols": [], "failed_symbols": [],
            "symbol_results": [], "values": [],
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

    # 각 종목의 날짜별 종가 맵
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
            "symbol_results": [],
            "values": [],
            "result": False,
            "analysis": {"error": "Need at least 2 symbols for correlation analysis"},
        }

    # 모든 페어의 상관계수 계산
    passed, failed, symbol_results, values = [], [], [], []
    pair_correlations = []

    for i in range(len(all_symbols)):
        for j in range(i + 1, len(all_symbols)):
            sym_a = all_symbols[i]
            sym_b = all_symbols[j]

            dates_a = set(symbol_price_by_date[sym_a].keys())
            dates_b = set(symbol_price_by_date[sym_b].keys())
            common_dates = sorted(dates_a & dates_b)

            if len(common_dates) < lookback:
                continue

            # 최근 lookback 기간
            recent_dates = common_dates[-lookback:]
            prices_a = [symbol_price_by_date[sym_a][d] for d in recent_dates]
            prices_b = [symbol_price_by_date[sym_b][d] for d in recent_dates]

            # 수익률로 변환
            returns_a = [(prices_a[k] - prices_a[k - 1]) / prices_a[k - 1] for k in range(1, len(prices_a)) if prices_a[k - 1] > 0]
            returns_b = [(prices_b[k] - prices_b[k - 1]) / prices_b[k - 1] for k in range(1, len(prices_b)) if prices_b[k - 1] > 0]

            min_len = min(len(returns_a), len(returns_b))
            if min_len < 10:
                continue

            returns_a = returns_a[-min_len:]
            returns_b = returns_b[-min_len:]

            if method == "spearman":
                corr = _spearman_correlation(returns_a, returns_b)
            else:
                corr = _pearson_correlation(returns_a, returns_b)

            corr = round(corr, 4)
            pair_correlations.append({
                "symbol_a": sym_a, "symbol_b": sym_b,
                "correlation": corr,
                "exchange_a": symbol_exchange_map.get(sym_a, "UNKNOWN"),
                "exchange_b": symbol_exchange_map.get(sym_b, "UNKNOWN"),
            })

    # 결과 집계: 각 종목이 threshold 조건을 만족하는 페어가 있는지
    symbol_max_corr: Dict[str, float] = {}
    symbol_best_pair: Dict[str, str] = {}

    for pair in pair_correlations:
        for key in ["symbol_a", "symbol_b"]:
            sym = pair[key]
            other = pair["symbol_b"] if key == "symbol_a" else pair["symbol_a"]
            corr = abs(pair["correlation"])
            if sym not in symbol_max_corr or corr > symbol_max_corr[sym]:
                symbol_max_corr[sym] = pair["correlation"]
                symbol_best_pair[sym] = other

    target_symbols = symbols or [{"symbol": s, "exchange": symbol_exchange_map.get(s, "UNKNOWN")} for s in all_symbols]

    for sym_info in target_symbols:
        symbol = sym_info.get("symbol", "") if isinstance(sym_info, dict) else str(sym_info)
        exchange = sym_info.get("exchange", "UNKNOWN") if isinstance(sym_info, dict) else "UNKNOWN"
        sym_dict = {"symbol": symbol, "exchange": exchange}

        max_corr = symbol_max_corr.get(symbol)
        best_pair = symbol_best_pair.get(symbol, "")

        if max_corr is None:
            failed.append(sym_dict)
            symbol_results.append({"symbol": symbol, "exchange": exchange, "error": "No correlation data"})
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        if direction == "above":
            passed_condition = max_corr > threshold
        else:
            passed_condition = max_corr < threshold

        if passed_condition:
            passed.append(sym_dict)
        else:
            failed.append(sym_dict)

        symbol_results.append({
            "symbol": symbol, "exchange": exchange,
            "max_correlation": max_corr, "best_pair": best_pair,
            "passed": passed_condition,
        })

        time_series = [{
            "correlation": max_corr, "best_pair": best_pair,
            "signal": "buy" if passed_condition else None, "side": "long",
        }]
        values.append({"symbol": symbol, "exchange": exchange, "time_series": time_series})

    return {
        "passed_symbols": passed, "failed_symbols": failed,
        "symbol_results": symbol_results, "values": values,
        "result": len(passed) > 0,
        "pair_correlations": pair_correlations,
        "analysis": {
            "indicator": "CorrelationAnalysis",
            "lookback": lookback, "threshold": threshold,
            "direction": direction, "method": method,
            "total_pairs": len(pair_correlations),
        },
    }


__all__ = ["correlation_analysis_condition", "CORRELATION_ANALYSIS_SCHEMA"]
