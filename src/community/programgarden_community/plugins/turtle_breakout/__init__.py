"""
Turtle Breakout (터틀 브레이크아웃) 플러그인

Richard Dennis & William Eckhardt (1983) 터틀 트레이딩 시스템.
돈치안 채널 돌파 진입 + ATR 기반 스탑/포지션 사이징.

시스템 1: 20일 고가 돌파 진입, 10일 저가 돌파 청산
시스템 2: 55일 고가 돌파 진입, 20일 저가 돌파 청산

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, close, high, low, ...}, ...]
- fields: {system, entry_period, exit_period, atr_period, stop_atr_multiple, direction}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


TURTLE_BREAKOUT_SCHEMA = PluginSchema(
    id="TurtleBreakout",
    name="Turtle Breakout",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Donchian Channel breakout entry with ATR-based stop loss. System 1 (20/10 days) is faster, System 2 (55/20 days) catches stronger trends. Provides entry/exit signals and stop price for position sizing.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "system": {
            "type": "string",
            "default": "system1",
            "title": "System",
            "description": "Turtle system preset: system1 (20-day entry/10-day exit), system2 (55-day entry/20-day exit)",
            "enum": ["system1", "system2"],
        },
        "entry_period": {
            "type": "int",
            "default": 20,
            "title": "Entry Period",
            "description": "Donchian channel period for entry signal (overrides system default)",
            "ge": 10,
            "le": 100,
        },
        "exit_period": {
            "type": "int",
            "default": 10,
            "title": "Exit Period",
            "description": "Donchian channel period for exit signal (overrides system default)",
            "ge": 5,
            "le": 50,
        },
        "atr_period": {
            "type": "int",
            "default": 20,
            "title": "ATR Period",
            "description": "ATR period for N (noise) calculation used in stop and sizing",
            "ge": 10,
            "le": 50,
        },
        "stop_atr_multiple": {
            "type": "float",
            "default": 2.0,
            "title": "Stop ATR Multiple",
            "description": "Stop distance in ATR units (2N is standard turtle rule)",
            "ge": 1.0,
            "le": 4.0,
        },
        "direction": {
            "type": "string",
            "default": "both",
            "title": "Direction",
            "description": "Trading direction: long only, short only, or both",
            "enum": ["long", "short", "both"],
        },
        "filter_last_signal": {
            "type": "bool",
            "default": True,
            "title": "Filter Last Signal",
            "description": "System 1 original rule: skip entry if previous trade in this direction was profitable",
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close", "high", "low"],
    optional_fields=["open", "volume"],
    tags=["turtle", "donchian", "breakout", "trend", "atr", "dennis"],
    output_fields={
        "entry_signal": {"type": "str", "description": "Entry signal: 'long', 'short', or 'none'"},
        "exit_signal": {"type": "str", "description": "Exit signal: 'exit_long', 'exit_short', or 'none'"},
        "atr_value": {"type": "float", "description": "Current ATR (N) value for position sizing"},
        "stop_price": {"type": "float", "description": "Initial stop price based on ATR multiple"},
        "channel_high": {"type": "float", "description": "Upper Donchian channel level (entry period)"},
        "channel_low": {"type": "float", "description": "Lower Donchian channel level (entry period)"},
        "current_close": {"type": "float", "description": "Latest closing price"},
    },
    locales={
        "ko": {
            "name": "터틀 브레이크아웃",
            "description": "돈치안 채널 돌파 진입 + ATR 기반 스탑 (Dennis & Eckhardt 1983). 시스템1(20/10일)은 빠른 신호, 시스템2(55/20일)는 더 강한 추세만 포착합니다.",
            "fields.system": "터틀 시스템 (system1: 20/10일, system2: 55/20일)",
            "fields.entry_period": "진입 돈치안 채널 기간",
            "fields.exit_period": "청산 돈치안 채널 기간",
            "fields.atr_period": "ATR(N) 계산 기간",
            "fields.stop_atr_multiple": "스탑 ATR 배수 (기본 2N)",
            "fields.direction": "매매 방향 (long/short/both)",
            "fields.filter_last_signal": "직전 수익 신호 필터 (시스템1 원본 규칙)",
        },
    },
)


def _calculate_atr(highs: List[float], lows: List[float], closes: List[float], period: int) -> Optional[float]:
    """Wilder's ATR 계산"""
    if len(highs) < period + 1:
        return None

    trs = []
    for i in range(1, len(highs)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)

    if len(trs) < period:
        return None

    atr = sum(trs[:period]) / period
    for i in range(period, len(trs)):
        atr = (atr * (period - 1) + trs[i]) / period

    return round(atr, 4)


def _donchian_high(highs: List[float], period: int) -> Optional[float]:
    """돈치안 채널 고점"""
    if len(highs) < period:
        return None
    return max(highs[-period:])


def _donchian_low(lows: List[float], period: int) -> Optional[float]:
    """돈치안 채널 저점"""
    if len(lows) < period:
        return None
    return min(lows[-period:])


def _detect_entry_exit(
    closes: List[float],
    highs: List[float],
    lows: List[float],
    entry_period: int,
    exit_period: int,
    direction: str,
) -> tuple:
    """현재 바의 진입/청산 신호 감지"""
    current_close = closes[-1]

    # 현재 바 제외한 이전 bars로 채널 계산
    prev_highs = highs[-entry_period - 1:-1]
    prev_lows = lows[-entry_period - 1:-1]

    entry_channel_high = max(prev_highs) if len(prev_highs) >= entry_period else None
    entry_channel_low = min(prev_lows) if len(prev_lows) >= entry_period else None

    prev_exit_highs = highs[-exit_period - 1:-1]
    prev_exit_lows = lows[-exit_period - 1:-1]

    exit_channel_high = max(prev_exit_highs) if len(prev_exit_highs) >= exit_period else None
    exit_channel_low = min(prev_exit_lows) if len(prev_exit_lows) >= exit_period else None

    entry_signal = "none"
    exit_signal = "none"

    if entry_channel_high is not None and entry_channel_low is not None:
        if direction in ("long", "both") and current_close > entry_channel_high:
            entry_signal = "long_entry"
        elif direction in ("short", "both") and current_close < entry_channel_low:
            entry_signal = "short_entry"

    if exit_channel_high is not None and exit_channel_low is not None:
        if direction in ("long", "both") and current_close < exit_channel_low:
            exit_signal = "long_exit"
        elif direction in ("short", "both") and current_close > exit_channel_high:
            exit_signal = "short_exit"

    return entry_signal, exit_signal, entry_channel_high, entry_channel_low, exit_channel_high, exit_channel_low


async def turtle_breakout_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """터틀 브레이크아웃 조건 평가"""
    mapping = field_mapping or {}
    close_field = mapping.get("close_field", "close")
    high_field = mapping.get("high_field", "high")
    low_field = mapping.get("low_field", "low")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")
    open_field = mapping.get("open_field", "open")
    volume_field = mapping.get("volume_field", "volume")

    # 시스템 프리셋 기반 기본값
    system = fields.get("system", "system1")
    system_defaults = {
        "system1": {"entry_period": 20, "exit_period": 10},
        "system2": {"entry_period": 55, "exit_period": 20},
    }
    defaults = system_defaults.get(system, system_defaults["system1"])
    entry_period = fields.get("entry_period", defaults["entry_period"])
    exit_period = fields.get("exit_period", defaults["exit_period"])
    atr_period = fields.get("atr_period", 20)
    stop_atr_multiple = fields.get("stop_atr_multiple", 2.0)
    direction = fields.get("direction", "both")

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

    min_required = max(entry_period, exit_period, atr_period) + 2
    passed, failed, symbol_results, values = [], [], [], []

    for sym_info in target_symbols:
        symbol, exchange = sym_info["symbol"], sym_info["exchange"]
        sym_dict = {"symbol": symbol, "exchange": exchange}
        rows = symbol_data_map.get(symbol, [])

        if not rows or len(rows) < min_required:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol, "exchange": exchange,
                "entry_signal": "none", "exit_signal": "none",
                "error": f"Insufficient data: need {min_required}, got {len(rows)}",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))
        highs, lows, closes = [], [], []
        for row in rows_sorted:
            try:
                highs.append(float(row.get(high_field) or 0))
                lows.append(float(row.get(low_field) or 0))
                closes.append(float(row.get(close_field) or 0))
            except (ValueError, TypeError):
                pass

        if len(closes) < min_required:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol, "exchange": exchange,
                "entry_signal": "none", "exit_signal": "none",
                "error": "Insufficient price data",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        # 현재 신호 계산
        atr_value = _calculate_atr(highs, lows, closes, atr_period)
        entry_signal, exit_signal, ch_high, ch_low, ex_high, ex_low = _detect_entry_exit(
            closes, highs, lows, entry_period, exit_period, direction
        )

        # 스탑 가격
        stop_price = None
        if atr_value and entry_signal != "none":
            if entry_signal == "long_entry":
                stop_price = round(closes[-1] - stop_atr_multiple * atr_value, 4)
            else:
                stop_price = round(closes[-1] + stop_atr_multiple * atr_value, 4)

        # 시계열 생성
        ts_start = max(entry_period + 1, exit_period + 1)
        time_series = []
        for i in range(ts_start, len(rows_sorted)):
            row = rows_sorted[i]
            bar_closes = closes[:i + 1]
            bar_highs = highs[:i + 1]
            bar_lows = lows[:i + 1]

            bar_entry, bar_exit, bar_ch_high, bar_ch_low, _, _ = _detect_entry_exit(
                bar_closes, bar_highs, bar_lows, entry_period, exit_period, direction
            )

            time_series.append({
                date_field: row.get(date_field, ""),
                open_field: row.get(open_field),
                high_field: row.get(high_field),
                low_field: row.get(low_field),
                close_field: row.get(close_field),
                volume_field: row.get(volume_field),
                "channel_high": round(bar_ch_high, 4) if bar_ch_high else None,
                "channel_low": round(bar_ch_low, 4) if bar_ch_low else None,
                "entry_signal": bar_entry,
                "exit_signal": bar_exit,
            })

        values.append({"symbol": symbol, "exchange": exchange, "time_series": time_series})

        symbol_results.append({
            "symbol": symbol, "exchange": exchange,
            "entry_signal": entry_signal,
            "exit_signal": exit_signal,
            "atr_value": atr_value,
            "stop_price": stop_price,
            "channel_high": round(ch_high, 4) if ch_high else None,
            "channel_low": round(ch_low, 4) if ch_low else None,
            "current_close": closes[-1],
        })

        has_signal = entry_signal != "none"
        (passed if has_signal else failed).append(sym_dict)

    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "symbol_results": symbol_results,
        "values": values,
        "result": len(passed) > 0,
        "analysis": {
            "indicator": "TurtleBreakout",
            "system": system,
            "entry_period": entry_period,
            "exit_period": exit_period,
            "atr_period": atr_period,
            "stop_atr_multiple": stop_atr_multiple,
            "direction": direction,
        },
    }


__all__ = ["turtle_breakout_condition", "_calculate_atr", "_donchian_high", "_donchian_low", "TURTLE_BREAKOUT_SCHEMA"]
