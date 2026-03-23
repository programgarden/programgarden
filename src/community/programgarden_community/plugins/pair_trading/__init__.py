"""
PairTrading (페어 트레이딩) 플러그인

2종목 스프레드 Z-Score 기반 평균회귀 매매신호 생성.
CorrelationAnalysis와 차별: 상관계수 측정이 아닌 진입/청산 신호 생성.

입력 형식:
- data: 플랫 배열 (2종목 데이터 포함)
- fields: {symbol_a, symbol_b, lookback, entry_z, exit_z, spread_method, correlation_min}

※ 다중 종목 플러그인 - ConditionNode auto-iterate 제약 → NodeRunner 테스트 권장
"""

import math
from typing import List, Dict, Any, Optional, Set
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


# risk_features 선언 (페어 상태 추적)
risk_features: Set[str] = {"state"}

PAIR_TRADING_SCHEMA = PluginSchema(
    id="PairTrading",
    name="Pair Trading",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Generates mean-reversion trading signals for a pair of correlated symbols based on spread Z-Score. Entry when Z exceeds threshold, exit when Z reverts. Validates pair correlation before generating signals.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "symbol_a": {
            "type": "string",
            "default": "",
            "title": "Symbol A",
            "description": "First symbol of the pair",
        },
        "symbol_b": {
            "type": "string",
            "default": "",
            "title": "Symbol B",
            "description": "Second symbol of the pair",
        },
        "lookback": {
            "type": "int",
            "default": 60,
            "title": "Lookback Period",
            "description": "Rolling window for spread statistics",
            "ge": 20,
            "le": 252,
        },
        "entry_z": {
            "type": "float",
            "default": 2.0,
            "title": "Entry Z-Score",
            "description": "Z-Score threshold for entry signal",
            "ge": 1.0,
            "le": 4.0,
        },
        "exit_z": {
            "type": "float",
            "default": 0.5,
            "title": "Exit Z-Score",
            "description": "Z-Score threshold for exit signal (mean reversion)",
            "ge": 0.0,
            "le": 2.0,
        },
        "spread_method": {
            "type": "string",
            "default": "ratio",
            "title": "Spread Method",
            "description": "Spread calculation method",
            "enum": ["ratio", "log_ratio", "difference"],
        },
        "correlation_min": {
            "type": "float",
            "default": 0.5,
            "title": "Min Correlation",
            "description": "Minimum correlation required to generate signals",
            "ge": 0.0,
            "le": 1.0,
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close"],
    optional_fields=[],
    tags=["pair", "spread", "statistical_arbitrage", "mean_reversion", "correlation"],
    output_fields={
        "z_score": {"type": "float", "description": "Z-Score of the current spread relative to its rolling mean"},
        "spread": {"type": "float", "description": "Current spread value between the two symbols"},
        "mean_spread": {"type": "float", "description": "Rolling mean of the spread"},
        "std_spread": {"type": "float", "description": "Rolling standard deviation of the spread"},
        "correlation": {"type": "float", "description": "Pearson correlation between the two symbols' returns"},
        "signal": {"type": "str", "description": "Trading signal: 'long_a_short_b', 'short_a_long_b', 'exit', or None"},
        "current_price": {"type": "float", "description": "Latest closing price of this symbol"},
    },
    locales={
        "ko": {
            "name": "페어 트레이딩",
            "description": "상관관계 높은 2종목의 스프레드 Z-Score 기반 평균회귀 매매신호를 생성합니다. Z-Score가 임계값을 넘으면 진입, 평균 회귀하면 청산합니다.",
            "fields.symbol_a": "페어 종목 A",
            "fields.symbol_b": "페어 종목 B",
            "fields.lookback": "롤링 윈도우 기간",
            "fields.entry_z": "진입 Z-Score 임계값",
            "fields.exit_z": "청산 Z-Score 임계값",
            "fields.spread_method": "스프레드 계산 방식 (ratio/log_ratio/difference)",
            "fields.correlation_min": "최소 상관계수",
        },
    },
)


def _pearson_correlation(x: List[float], y: List[float]) -> float:
    """피어슨 상관계수"""
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


def _calculate_spread(price_a: float, price_b: float, method: str) -> Optional[float]:
    """스프레드 계산"""
    if price_b <= 0:
        return None
    if method == "ratio":
        return price_a / price_b
    elif method == "log_ratio":
        if price_a <= 0:
            return None
        return math.log(price_a / price_b)
    else:  # difference
        return price_a - price_b


async def pair_trading_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
    context: Any = None,
    **kwargs,
) -> Dict[str, Any]:
    """페어 트레이딩 조건 평가"""
    mapping = field_mapping or {}
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")

    symbol_a = fields.get("symbol_a", "")
    symbol_b = fields.get("symbol_b", "")
    lookback = fields.get("lookback", 60)
    entry_z = fields.get("entry_z", 2.0)
    exit_z = fields.get("exit_z", 0.5)
    spread_method = fields.get("spread_method", "ratio")
    correlation_min = fields.get("correlation_min", 0.5)

    if not data or not isinstance(data, list):
        return {
            "passed_symbols": [], "failed_symbols": [],
            "symbol_results": [], "values": [],
            "result": False,
            "analysis": {"error": "No data provided"},
        }

    # 종목별 데이터 그룹화
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

    # symbol_a/b가 비어있으면 데이터에서 자동 결정 (처음 2종목)
    all_syms = list(symbol_data_map.keys())
    if not symbol_a and len(all_syms) >= 1:
        symbol_a = all_syms[0]
    if not symbol_b and len(all_syms) >= 2:
        symbol_b = all_syms[1]

    if not symbol_a or not symbol_b or symbol_a == symbol_b:
        return {
            "passed_symbols": [], "failed_symbols": [],
            "symbol_results": [], "values": [],
            "result": False,
            "analysis": {"error": "Need exactly 2 different symbols for pair trading"},
        }

    # 날짜별 종가 맵
    def _price_by_date(sym: str) -> Dict[str, float]:
        rows = symbol_data_map.get(sym, [])
        price_map = {}
        for row in rows:
            d = row.get(date_field, "")
            p = row.get(close_field)
            if d and p is not None:
                try:
                    price_map[d] = float(p)
                except (ValueError, TypeError):
                    pass
        return price_map

    prices_a = _price_by_date(symbol_a)
    prices_b = _price_by_date(symbol_b)

    if not prices_a or not prices_b:
        return {
            "passed_symbols": [], "failed_symbols": [],
            "symbol_results": [], "values": [],
            "result": False,
            "analysis": {"error": f"No data for {symbol_a if not prices_a else symbol_b}"},
        }

    common_dates = sorted(set(prices_a.keys()) & set(prices_b.keys()))

    if len(common_dates) < lookback:
        return {
            "passed_symbols": [], "failed_symbols": [],
            "symbol_results": [], "values": [],
            "result": False,
            "analysis": {"error": f"Insufficient common data: need {lookback}, got {len(common_dates)}"},
        }

    # 수익률 기반 상관계수
    pa_list = [prices_a[d] for d in common_dates]
    pb_list = [prices_b[d] for d in common_dates]

    returns_a = [(pa_list[i] - pa_list[i - 1]) / pa_list[i - 1] for i in range(1, len(pa_list)) if pa_list[i - 1] > 0]
    returns_b = [(pb_list[i] - pb_list[i - 1]) / pb_list[i - 1] for i in range(1, len(pb_list)) if pb_list[i - 1] > 0]
    min_len = min(len(returns_a), len(returns_b))
    correlation = _pearson_correlation(returns_a[-min_len:], returns_b[-min_len:]) if min_len >= 10 else 0.0
    correlation = round(correlation, 4)

    if abs(correlation) < correlation_min:
        exchange_a = symbol_exchange_map.get(symbol_a, "UNKNOWN")
        exchange_b = symbol_exchange_map.get(symbol_b, "UNKNOWN")
        return {
            "passed_symbols": [],
            "failed_symbols": [
                {"symbol": symbol_a, "exchange": exchange_a},
                {"symbol": symbol_b, "exchange": exchange_b},
            ],
            "symbol_results": [
                {"symbol": symbol_a, "exchange": exchange_a, "correlation": correlation, "error": "Below min correlation"},
                {"symbol": symbol_b, "exchange": exchange_b, "correlation": correlation, "error": "Below min correlation"},
            ],
            "values": [],
            "result": False,
            "analysis": {
                "indicator": "PairTrading",
                "correlation": correlation,
                "correlation_min": correlation_min,
                "error": f"Correlation {correlation} < min {correlation_min}",
            },
        }

    # 스프레드 계산 + Z-Score
    recent_dates = common_dates[-lookback:]
    spreads = []
    for d in recent_dates:
        sp = _calculate_spread(prices_a[d], prices_b[d], spread_method)
        if sp is not None:
            spreads.append(sp)

    if len(spreads) < lookback:
        return {
            "passed_symbols": [], "failed_symbols": [],
            "symbol_results": [], "values": [],
            "result": False,
            "analysis": {"error": "Insufficient spread data"},
        }

    mean_spread = sum(spreads) / len(spreads)
    variance = sum((s - mean_spread) ** 2 for s in spreads) / len(spreads)
    std_spread = math.sqrt(variance)

    current_spread = spreads[-1]
    z_score = (current_spread - mean_spread) / std_spread if std_spread > 0 else 0.0
    z_score = round(z_score, 4)

    # 신호 생성
    signal = None
    if z_score > entry_z:
        signal = "short_a_long_b"  # A 고평가, B 저평가
    elif z_score < -entry_z:
        signal = "long_a_short_b"  # A 저평가, B 고평가
    elif abs(z_score) < exit_z:
        signal = "exit"

    # state 저장
    has_risk_tracker = context and hasattr(context, "risk_tracker") and context.risk_tracker
    if has_risk_tracker and signal:
        try:
            context.risk_tracker.set_state(f"pair_{symbol_a}_{symbol_b}", signal)
        except Exception:
            pass

    # 결과 구성
    exchange_a = symbol_exchange_map.get(symbol_a, "UNKNOWN")
    exchange_b = symbol_exchange_map.get(symbol_b, "UNKNOWN")

    passed, failed = [], []
    if signal and signal != "exit":
        passed.append({"symbol": symbol_a, "exchange": exchange_a})
        passed.append({"symbol": symbol_b, "exchange": exchange_b})
    else:
        failed.append({"symbol": symbol_a, "exchange": exchange_a})
        failed.append({"symbol": symbol_b, "exchange": exchange_b})

    symbol_results = [
        {
            "symbol": symbol_a, "exchange": exchange_a,
            "z_score": z_score, "spread": round(current_spread, 6),
            "mean_spread": round(mean_spread, 6), "std_spread": round(std_spread, 6),
            "correlation": correlation, "signal": signal,
            "current_price": prices_a.get(common_dates[-1]),
            "side": "short" if signal == "short_a_long_b" else ("long" if signal == "long_a_short_b" else None),
        },
        {
            "symbol": symbol_b, "exchange": exchange_b,
            "z_score": z_score, "spread": round(current_spread, 6),
            "mean_spread": round(mean_spread, 6), "std_spread": round(std_spread, 6),
            "correlation": correlation, "signal": signal,
            "current_price": prices_b.get(common_dates[-1]),
            "side": "long" if signal == "short_a_long_b" else ("short" if signal == "long_a_short_b" else None),
        },
    ]

    # 스프레드 시계열
    spread_time_series = []
    for i, d in enumerate(recent_dates):
        if i < len(spreads):
            sp = spreads[i]
            sp_z = (sp - mean_spread) / std_spread if std_spread > 0 else 0.0
            spread_time_series.append({
                "date": d,
                "spread": round(sp, 6),
                "z_score": round(sp_z, 4),
                "price_a": prices_a.get(d),
                "price_b": prices_b.get(d),
            })

    values = [
        {"symbol": symbol_a, "exchange": exchange_a, "time_series": spread_time_series},
        {"symbol": symbol_b, "exchange": exchange_b, "time_series": spread_time_series},
    ]

    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "symbol_results": symbol_results,
        "values": values,
        "result": len(passed) > 0,
        "analysis": {
            "indicator": "PairTrading",
            "symbol_a": symbol_a, "symbol_b": symbol_b,
            "correlation": correlation,
            "z_score": z_score,
            "spread": round(current_spread, 6),
            "mean_spread": round(mean_spread, 6),
            "std_spread": round(std_spread, 6),
            "signal": signal,
            "spread_method": spread_method,
            "lookback": lookback,
        },
    }


__all__ = ["pair_trading_condition", "PAIR_TRADING_SCHEMA", "risk_features"]
