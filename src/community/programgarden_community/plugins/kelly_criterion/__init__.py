"""
KellyCriterion (켈리 기준) 플러그인

켈리 공식 기반 최적 포지션 비중 산출.
과거 수익률의 승률과 손익비로 수학적 최적 비중을 계산하고,
보수적 배수(fraction)를 적용합니다.

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, close, ...}, ...]
- fields: {lookback, kelly_fraction, min_position_pct, max_position_pct, return_period}
"""

from typing import List, Dict, Any, Optional, Set
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


# risk_features 선언 (선택적: 켈리 비중 이력 저장)
risk_features: Set[str] = {"state"}

KELLY_CRITERION_SCHEMA = PluginSchema(
    id="KellyCriterion",
    name="Kelly Criterion",
    category=PluginCategory.POSITION,
    version="1.0.0",
    description="Calculates optimal position size using Kelly Criterion. Uses win rate and payoff ratio from historical returns to determine mathematically optimal bet fraction.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "lookback": {
            "type": "int",
            "default": 60,
            "title": "Lookback Period",
            "description": "Number of periods for return calculation",
            "ge": 20,
            "le": 500,
        },
        "kelly_fraction": {
            "type": "float",
            "default": 0.25,
            "title": "Kelly Fraction",
            "description": "Fraction of full Kelly to apply (conservative scaling)",
            "ge": 0.1,
            "le": 1.0,
        },
        "min_position_pct": {
            "type": "float",
            "default": 2.0,
            "title": "Min Position (%)",
            "description": "Minimum position size as portfolio percentage",
            "ge": 0.0,
            "le": 50.0,
        },
        "max_position_pct": {
            "type": "float",
            "default": 25.0,
            "title": "Max Position (%)",
            "description": "Maximum position size as portfolio percentage",
            "ge": 1.0,
            "le": 100.0,
        },
        "return_period": {
            "type": "string",
            "default": "daily",
            "title": "Return Period",
            "description": "Period for return calculation",
            "enum": ["daily", "weekly"],
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close"],
    optional_fields=[],
    tags=["kelly", "position_sizing", "risk_management", "optimal"],
    locales={
        "ko": {
            "name": "켈리 기준 (Kelly Criterion)",
            "description": "켈리 공식으로 최적 포지션 비중을 산출합니다. 과거 수익률의 승률과 손익비를 기반으로 수학적 최적 베팅 비율을 계산하고, 보수적 배수를 적용합니다.",
            "fields.lookback": "수익률 계산 기간",
            "fields.kelly_fraction": "켈리 보수적 배수 (0.25 = Quarter Kelly)",
            "fields.min_position_pct": "최소 포지션 비중 (%)",
            "fields.max_position_pct": "최대 포지션 비중 (%)",
            "fields.return_period": "수익률 계산 주기 (daily/weekly)",
        },
    },
)


def _calculate_kelly_pct(returns: List[float]) -> float:
    """
    켈리 비율 계산.

    Kelly % = (W * R - (1 - W)) / R
    W = 승률, R = 평균수익/평균손실 (payoff ratio)

    Returns:
        켈리 비율 (0~1 사이, 음수면 0 반환)
    """
    if not returns:
        return 0.0

    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r < 0]

    if not wins or not losses:
        return 0.0

    win_rate = len(wins) / len(returns)
    avg_win = sum(wins) / len(wins)
    avg_loss = abs(sum(losses) / len(losses))

    if avg_loss == 0:
        return 0.0

    payoff_ratio = avg_win / avg_loss
    kelly = (win_rate * payoff_ratio - (1 - win_rate)) / payoff_ratio

    return max(0.0, kelly)


async def kelly_criterion_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
    context: Any = None,
    **kwargs,
) -> Dict[str, Any]:
    """켈리 기준 포지션 사이징 조건 평가"""
    mapping = field_mapping or {}
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")

    lookback = fields.get("lookback", 60)
    kelly_fraction = fields.get("kelly_fraction", 0.25)
    min_pos = fields.get("min_position_pct", 2.0)
    max_pos = fields.get("max_position_pct", 25.0)
    return_period = fields.get("return_period", "daily")

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

    if not symbols:
        symbols = [{"symbol": s, "exchange": symbol_exchange_map.get(s, "UNKNOWN")} for s in symbol_data_map]

    passed, failed, symbol_results, values = [], [], [], []

    for sym_info in symbols:
        symbol = sym_info.get("symbol", "") if isinstance(sym_info, dict) else str(sym_info)
        exchange = sym_info.get("exchange", "UNKNOWN") if isinstance(sym_info, dict) else "UNKNOWN"
        sym_dict = {"symbol": symbol, "exchange": exchange}

        rows = symbol_data_map.get(symbol, [])
        if not rows:
            failed.append(sym_dict)
            symbol_results.append({"symbol": symbol, "exchange": exchange, "error": "No data"})
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))
        prices = [float(r.get(close_field, 0)) for r in rows_sorted if r.get(close_field) is not None]

        if len(prices) < lookback + 1:
            failed.append(sym_dict)
            symbol_results.append({"symbol": symbol, "exchange": exchange, "error": "Insufficient data"})
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        recent_prices = prices[-(lookback + 1):]

        # 수익률 계산
        if return_period == "weekly":
            # 주간 수익률: 5일 간격
            step = 5
            returns = [
                (recent_prices[i] - recent_prices[i - step]) / recent_prices[i - step]
                for i in range(step, len(recent_prices))
                if recent_prices[i - step] > 0
            ]
        else:
            # 일별 수익률
            returns = [
                (recent_prices[i] - recent_prices[i - 1]) / recent_prices[i - 1]
                for i in range(1, len(recent_prices))
                if recent_prices[i - 1] > 0
            ]

        if not returns:
            failed.append(sym_dict)
            symbol_results.append({"symbol": symbol, "exchange": exchange, "error": "No valid returns"})
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        # 켈리 계산
        kelly_pct = _calculate_kelly_pct(returns)
        fractional_kelly = kelly_pct * kelly_fraction
        position_pct = max(min_pos, min(max_pos, round(fractional_kelly * 100, 2)))

        # 통계
        wins = [r for r in returns if r > 0]
        losses = [r for r in returns if r < 0]
        win_rate = len(wins) / len(returns) if returns else 0
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = abs(sum(losses) / len(losses)) if losses else 0
        payoff_ratio = avg_win / avg_loss if avg_loss > 0 else 0
        expected_value = win_rate * avg_win - (1 - win_rate) * avg_loss

        passed.append(sym_dict)
        symbol_results.append({
            "symbol": symbol, "exchange": exchange,
            "kelly_pct": round(kelly_pct * 100, 2),
            "fractional_kelly_pct": round(fractional_kelly * 100, 2),
            "position_pct": position_pct,
            "win_rate": round(win_rate, 4),
            "avg_win": round(avg_win, 6),
            "avg_loss": round(avg_loss, 6),
            "payoff_ratio": round(payoff_ratio, 4),
            "expected_value": round(expected_value, 6),
        })

        time_series = [{
            "kelly_pct": round(kelly_pct * 100, 2),
            "position_pct": position_pct,
            "signal": "buy",
            "side": "long",
        }]
        values.append({"symbol": symbol, "exchange": exchange, "time_series": time_series})

    return {
        "passed_symbols": passed, "failed_symbols": failed,
        "symbol_results": symbol_results, "values": values,
        "result": len(passed) > 0,
        "analysis": {
            "indicator": "KellyCriterion",
            "lookback": lookback,
            "kelly_fraction": kelly_fraction,
            "return_period": return_period,
            "total_symbols": len(symbol_results),
        },
    }


__all__ = ["kelly_criterion_condition", "KELLY_CRITERION_SCHEMA", "risk_features"]
