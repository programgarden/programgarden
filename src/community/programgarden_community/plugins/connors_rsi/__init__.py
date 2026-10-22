"""
ConnorsRSI 플러그인

3가지 컴포넌트의 가중 평균으로 극단적 단기 과매수/과매도 포착.
1. RSI(period) - 전통 RSI (기본 3일)
2. Streak RSI - 연속 상승/하락일수의 RSI (기본 2일)
3. Percentile Rank - 최근 수익률의 백분위 순위 (기본 100일)
ConnorsRSI = (RSI + StreakRSI + PctRank) / 3

참고: Larry Connors & Cesar Alvarez (2008), "Short Term Trading Strategies That Work"

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, close, ...}, ...]
- fields: {rsi_period, streak_period, pct_rank_period, threshold, direction, exit_threshold}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


CONNORS_RSI_SCHEMA = PluginSchema(
    id="ConnorsRSI",
    name="ConnorsRSI",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Composite RSI combining classic RSI, Streak RSI (consecutive up/down days RSI), and Percentile Rank. Identifies extreme short-term overbought/oversold conditions. Based on Connors & Alvarez (2008).",
    products=[ProductType.OVERSEAS_STOCK],
    fields_schema={
        "rsi_period": {
            "type": "int",
            "default": 3,
            "title": "RSI Period",
            "description": "Classic RSI calculation period",
            "ge": 2,
            "le": 14,
        },
        "streak_period": {
            "type": "int",
            "default": 2,
            "title": "Streak RSI Period",
            "description": "RSI period for consecutive up/down days",
            "ge": 2,
            "le": 10,
        },
        "pct_rank_period": {
            "type": "int",
            "default": 100,
            "title": "Percentile Rank Period",
            "description": "Lookback period for return percentile rank",
            "ge": 20,
            "le": 252,
        },
        "threshold": {
            "type": "float",
            "default": 10.0,
            "title": "Entry Threshold",
            "description": "ConnorsRSI threshold for entry (below for oversold, above for overbought)",
            "ge": 1.0,
            "le": 50.0,
        },
        "direction": {
            "type": "string",
            "default": "below",
            "title": "Direction",
            "description": "below: buy when CRSI < threshold (oversold), above: sell when CRSI > (100-threshold)",
            "enum": ["below", "above"],
        },
        "exit_threshold": {
            "type": "float",
            "default": 70.0,
            "title": "Exit Threshold",
            "description": "ConnorsRSI level to exit position",
            "ge": 50.0,
            "le": 99.0,
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close"],
    optional_fields=["open", "high", "low", "volume"],
    tags=["rsi", "connors", "short-term", "mean-reversion", "oversold"],
    output_fields={
        "connors_rsi": {"type": "float", "description": "ConnorsRSI composite value (0–100)"},
        "rsi_component": {"type": "float", "description": "Classic RSI component value"},
        "streak_rsi_component": {"type": "float", "description": "Streak RSI component value (consecutive up/down days)"},
        "pct_rank_component": {"type": "float", "description": "Percentile rank component value"},
        "streak_value": {"type": "float", "description": "Raw consecutive up/down streak count"},
        "current_price": {"type": "float", "description": "Latest closing price"},
    },
    locales={
        "ko": {
            "name": "코너스 RSI",
            "description": "RSI + 연속일수 RSI + 백분위 순위 결합. 극단적 단기 과매수/과매도 포착 (Connors 2008).",
            "fields.rsi_period": "RSI 기간",
            "fields.streak_period": "연속일수 RSI 기간",
            "fields.pct_rank_period": "백분위 순위 기간",
            "fields.threshold": "진입 임계값",
            "fields.direction": "방향 (below: 과매도 매수, above: 과매수 매도)",
            "fields.exit_threshold": "청산 임계값",
        },
    },
)


def _calc_rsi(closes: List[float], period: int) -> Optional[float]:
    """Wilder RSI 계산 (마지막 값)"""
    if len(closes) < period + 1:
        return None

    gains = []
    losses = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0.0))
        losses.append(max(-diff, 0.0))

    if len(gains) < period:
        return None

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100.0 - (100.0 / (1.0 + rs)), 4)


def _calc_streak(closes: List[float]) -> int:
    """연속 상승/하락일수 계산 (양수=연속상승, 음수=연속하락)"""
    if len(closes) < 2:
        return 0
    streak = 0
    for i in range(len(closes) - 1, 0, -1):
        if closes[i] > closes[i - 1]:
            if streak < 0:
                break
            streak += 1
        elif closes[i] < closes[i - 1]:
            if streak > 0:
                break
            streak -= 1
        else:
            break
    return streak


def _calc_percentile_rank(returns: List[float]) -> float:
    """현재 수익률의 백분위 순위 (0~100)"""
    if len(returns) < 2:
        return 50.0
    current = returns[-1]
    count_below = sum(1 for r in returns[:-1] if r < current)
    return round(count_below / (len(returns) - 1) * 100.0, 4)


def calculate_connors_rsi(
    closes: List[float],
    rsi_period: int = 3,
    streak_period: int = 2,
    pct_rank_period: int = 100,
) -> Optional[Dict[str, Any]]:
    """
    ConnorsRSI 계산

    Returns:
        {"connors_rsi": float, "rsi_component": float, "streak_rsi_component": float, "pct_rank_component": float}
        또는 None (데이터 부족)
    """
    min_required = max(rsi_period, streak_period, pct_rank_period) + 2
    if len(closes) < min_required:
        return None

    # Component 1: RSI(rsi_period)
    rsi_val = _calc_rsi(closes, rsi_period)
    if rsi_val is None:
        return None

    # Component 2: Streak RSI
    streak = _calc_streak(closes)
    # streak을 수치로 변환하여 RSI 계산
    streak_series = [float(streak)] * (streak_period + 1)  # dummy for min required
    # 실제로는 streak 값의 시계열을 RSI로 계산
    streak_rsi = _calc_streak_rsi(closes, streak_period)
    if streak_rsi is None:
        return None

    # Component 3: Percentile Rank
    if len(closes) < pct_rank_period + 1:
        return None

    returns_window = []
    for i in range(len(closes) - pct_rank_period - 1, len(closes)):
        if i > 0 and closes[i - 1] > 0:
            returns_window.append(closes[i] / closes[i - 1] - 1.0)

    pct_rank = _calc_percentile_rank(returns_window)

    connors_rsi = round((rsi_val + streak_rsi + pct_rank) / 3.0, 4)

    return {
        "connors_rsi": connors_rsi,
        "rsi_component": rsi_val,
        "streak_rsi_component": streak_rsi,
        "pct_rank_component": pct_rank,
        "streak_value": streak,
    }


def _calc_streak_rsi(closes: List[float], streak_period: int) -> Optional[float]:
    """
    연속 상승/하락일수 시계열의 RSI 계산
    """
    if len(closes) < streak_period + 3:
        return None

    # 연속일수 시계열 생성
    streak_series = []
    for i in range(1, len(closes) + 1):
        s = _calc_streak(closes[:i])
        streak_series.append(float(s))

    # streak_series의 RSI 계산
    if len(streak_series) < streak_period + 1:
        return None

    gains = []
    losses = []
    for i in range(1, len(streak_series)):
        diff = streak_series[i] - streak_series[i - 1]
        gains.append(max(diff, 0.0))
        losses.append(max(-diff, 0.0))

    if len(gains) < streak_period:
        return None

    avg_gain = sum(gains[:streak_period]) / streak_period
    avg_loss = sum(losses[:streak_period]) / streak_period

    for i in range(streak_period, len(gains)):
        avg_gain = (avg_gain * (streak_period - 1) + gains[i]) / streak_period
        avg_loss = (avg_loss * (streak_period - 1) + losses[i]) / streak_period

    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return round(100.0 - (100.0 / (1.0 + rs)), 4)


async def connors_rsi_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    ConnorsRSI 조건 평가

    Args:
        data: 플랫 배열 데이터
        fields: {rsi_period, streak_period, pct_rank_period, threshold, direction, exit_threshold}
        field_mapping: 필드명 매핑
        symbols: 평가할 종목 리스트

    Returns:
        표준 플러그인 결과
    """
    mapping = field_mapping or {}
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")
    open_field = mapping.get("open_field", "open")
    volume_field = mapping.get("volume_field", "volume")

    rsi_period = fields.get("rsi_period", 3)
    streak_period = fields.get("streak_period", 2)
    pct_rank_period = fields.get("pct_rank_period", 100)
    threshold = fields.get("threshold", 10.0)
    direction = fields.get("direction", "below")
    exit_threshold = fields.get("exit_threshold", 70.0)

    if not data or not isinstance(data, list):
        return {
            "passed_symbols": [], "failed_symbols": [],
            "symbol_results": [], "values": [],
            "result": False,
            "analysis": {"error": "No data provided"},
        }

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

    if symbols:
        target_symbols = [
            {"symbol": s.get("symbol", ""), "exchange": s.get("exchange", "UNKNOWN")}
            if isinstance(s, dict) else {"symbol": str(s), "exchange": "UNKNOWN"}
            for s in symbols
        ]
    else:
        target_symbols = [
            {"symbol": sym, "exchange": symbol_exchange_map.get(sym, "UNKNOWN")}
            for sym in symbol_data_map.keys()
        ]

    passed, failed, symbol_results, values = [], [], [], []
    min_required = max(rsi_period, streak_period, pct_rank_period) + 2

    for sym_info in target_symbols:
        symbol = sym_info["symbol"]
        exchange = sym_info["exchange"]
        sym_dict = {"symbol": symbol, "exchange": exchange}

        rows = symbol_data_map.get(symbol, [])

        if not rows or len(rows) < min_required:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol, "exchange": exchange,
                "connors_rsi": None,
                "error": f"Insufficient data: need {min_required}, got {len(rows)}",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))

        closes = []
        for row in rows_sorted:
            try:
                closes.append(float(row.get(close_field, 0)))
            except (ValueError, TypeError):
                pass

        if len(closes) < min_required:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol, "exchange": exchange,
                "connors_rsi": None,
                "error": f"Insufficient price data",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        crsi_result = calculate_connors_rsi(closes, rsi_period, streak_period, pct_rank_period)

        if crsi_result is None:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol, "exchange": exchange,
                "connors_rsi": None,
                "error": "Calculation failed",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        # time_series: 최근 포인트들
        time_series = []
        ts_start = max(min_required, len(rows_sorted) - 10)
        for i in range(ts_start, len(rows_sorted)):
            ts_closes = closes[:i + 1]
            ts_result = calculate_connors_rsi(ts_closes, rsi_period, streak_period, pct_rank_period)
            if ts_result:
                original_row = rows_sorted[i]
                time_series.append({
                    date_field: original_row.get(date_field, ""),
                    close_field: original_row.get(close_field),
                    "connors_rsi": ts_result["connors_rsi"],
                    "rsi_component": ts_result["rsi_component"],
                    "streak_rsi_component": ts_result["streak_rsi_component"],
                    "pct_rank_component": ts_result["pct_rank_component"],
                })

        values.append({"symbol": symbol, "exchange": exchange, "time_series": time_series})

        symbol_results.append({
            "symbol": symbol, "exchange": exchange,
            "connors_rsi": crsi_result["connors_rsi"],
            "rsi_component": crsi_result["rsi_component"],
            "streak_rsi_component": crsi_result["streak_rsi_component"],
            "pct_rank_component": crsi_result["pct_rank_component"],
            "streak_value": crsi_result["streak_value"],
            "current_price": closes[-1],
        })

        # 조건 평가
        crsi = crsi_result["connors_rsi"]
        if direction == "below":
            passed_condition = crsi < threshold
        else:  # above
            passed_condition = crsi > (100.0 - threshold)

        (passed if passed_condition else failed).append(sym_dict)

    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "symbol_results": symbol_results,
        "values": values,
        "result": len(passed) > 0,
        "analysis": {
            "indicator": "ConnorsRSI",
            "rsi_period": rsi_period,
            "streak_period": streak_period,
            "pct_rank_period": pct_rank_period,
            "threshold": threshold,
            "direction": direction,
            "exit_threshold": exit_threshold,
        },
    }


__all__ = [
    "connors_rsi_condition",
    "calculate_connors_rsi",
    "_calc_rsi",
    "_calc_streak",
    "_calc_streak_rsi",
    "_calc_percentile_rank",
    "CONNORS_RSI_SCHEMA",
]
