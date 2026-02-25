"""
Volatility Breakout (변동성 돌파) 플러그인

Larry Williams의 변동성 돌파 전략.
돌파 기준가 = 당일 시가 + (전일 고가 - 전일 저가) × K
당일 고가가 돌파 기준가를 상회하면 매수 신호.

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, open, close, high, low, ...}, ...]
- fields: {k_factor, atr_adaptive, atr_period, direction, exit_mode, noise_filter}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


VOLATILITY_BREAKOUT_SCHEMA = PluginSchema(
    id="VolatilityBreakout",
    name="Volatility Breakout",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Larry Williams' Volatility Breakout strategy. Breakout price = today's open + (yesterday's high - low) × K. Signal when today's high exceeds breakout price. K value (0.4-0.6) is the key parameter.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "k_factor": {
            "type": "float",
            "default": 0.5,
            "title": "K Factor",
            "description": "Breakout multiplier: breakout_price = open + k × (prev_high - prev_low). Typical range 0.4-0.6",
            "ge": 0.1,
            "le": 1.0,
        },
        "atr_adaptive": {
            "type": "bool",
            "default": False,
            "title": "ATR Adaptive",
            "description": "Automatically adjust K based on ATR volatility level",
        },
        "atr_period": {
            "type": "int",
            "default": 14,
            "title": "ATR Period",
            "description": "ATR period for adaptive K and noise filtering",
            "ge": 5,
            "le": 50,
        },
        "direction": {
            "type": "string",
            "default": "long",
            "title": "Direction",
            "description": "Signal direction: long (upward breakout), short (downward breakout), or both",
            "enum": ["long", "short", "both"],
        },
        "exit_mode": {
            "type": "string",
            "default": "close",
            "title": "Exit Mode",
            "description": "Exit strategy: close (end of day), next_open (next day open), trailing (trailing stop)",
            "enum": ["close", "next_open", "trailing"],
        },
        "noise_filter": {
            "type": "bool",
            "default": True,
            "title": "Noise Filter",
            "description": "Apply volume-based noise filter (only signal when volume > 5-day average)",
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "open", "close", "high", "low"],
    optional_fields=["volume"],
    tags=["volatility", "breakout", "williams", "intraday", "range"],
    locales={
        "ko": {
            "name": "변동성 돌파",
            "description": "Larry Williams의 변동성 돌파 전략. 돌파 기준가 = 시가 + (전일 고저차) × K. K값(0.4~0.6)이 핵심 파라미터입니다.",
            "fields.k_factor": "돌파 배율 (돌파가 = 시가 + K × 전일 고저차)",
            "fields.atr_adaptive": "ATR 기반 K값 자동 조정",
            "fields.atr_period": "ATR 계산 기간",
            "fields.direction": "방향 (long: 상향 돌파, short: 하향 돌파, both: 양방향)",
            "fields.exit_mode": "청산 방식 (close: 당일 종가, next_open: 다음날 시가, trailing: 트레일링)",
            "fields.noise_filter": "거래량 필터 (5일 평균 이상일 때만 신호)",
        },
    },
)


def _calculate_atr(highs: List[float], lows: List[float], closes: List[float], period: int) -> Optional[float]:
    """ATR 계산 (Wilder's smoothing)"""
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


def _compute_breakout_price(open_price: float, prev_range: float, k: float) -> float:
    """돌파 기준가 계산"""
    return round(open_price + k * prev_range, 4)


def _adaptive_k(k_factor: float, atr: float, close: float) -> float:
    """ATR 기반 K값 조정"""
    if close <= 0 or atr is None:
        return k_factor
    atr_pct = atr / close
    # 변동성이 높으면 K를 줄이고 (보수적), 낮으면 늘린다 (공격적)
    if atr_pct > 0.03:
        return max(0.2, k_factor * 0.7)
    elif atr_pct < 0.01:
        return min(0.8, k_factor * 1.3)
    return k_factor


async def volatility_breakout_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """변동성 돌파 조건 평가"""
    mapping = field_mapping or {}
    close_field = mapping.get("close_field", "close")
    high_field = mapping.get("high_field", "high")
    low_field = mapping.get("low_field", "low")
    open_field = mapping.get("open_field", "open")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")
    volume_field = mapping.get("volume_field", "volume")

    k_factor = fields.get("k_factor", 0.5)
    atr_adaptive = fields.get("atr_adaptive", False)
    atr_period = fields.get("atr_period", 14)
    direction = fields.get("direction", "long")
    noise_filter = fields.get("noise_filter", True)

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

    min_required = max(atr_period + 2, 6)  # 최소 atr_period + 2
    passed, failed, symbol_results, values = [], [], [], []

    for sym_info in target_symbols:
        symbol, exchange = sym_info["symbol"], sym_info["exchange"]
        sym_dict = {"symbol": symbol, "exchange": exchange}
        rows = symbol_data_map.get(symbol, [])

        if not rows or len(rows) < 2:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol, "exchange": exchange,
                "signal": "none",
                "error": f"Insufficient data: need at least 2 bars, got {len(rows)}",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))

        opens, highs, lows, closes, volumes = [], [], [], [], []
        for row in rows_sorted:
            try:
                opens.append(float(row.get(open_field) or 0))
                highs.append(float(row.get(high_field) or 0))
                lows.append(float(row.get(low_field) or 0))
                closes.append(float(row.get(close_field) or 0))
                vol = row.get(volume_field)
                volumes.append(float(vol) if vol is not None else 0.0)
            except (ValueError, TypeError):
                opens.append(0.0)
                highs.append(0.0)
                lows.append(0.0)
                closes.append(0.0)
                volumes.append(0.0)

        if len(closes) < 2:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol, "exchange": exchange,
                "signal": "none", "error": "Insufficient price data",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        # ATR 계산
        atr_value = _calculate_atr(highs, lows, closes, atr_period) if len(closes) > atr_period else None

        # 실효 K 계산
        effective_k = k_factor
        if atr_adaptive and atr_value and closes[-1] > 0:
            effective_k = _adaptive_k(k_factor, atr_value, closes[-1])

        # 현재 바 (최신) 신호 계산
        today_row = rows_sorted[-1]
        prev_row = rows_sorted[-2]

        today_open = opens[-1]
        today_high = highs[-1]
        today_low = lows[-1]
        today_close = closes[-1]
        today_vol = volumes[-1]

        prev_high = highs[-2]
        prev_low = lows[-2]
        prev_range = prev_high - prev_low

        long_breakout_price = _compute_breakout_price(today_open, prev_range, effective_k)
        short_breakout_price = today_open - effective_k * prev_range

        # 거래량 필터
        volume_ok = True
        if noise_filter and len(volumes) >= 5:
            avg_vol = sum(volumes[-6:-1]) / 5 if len(volumes) >= 6 else sum(volumes[:-1]) / max(1, len(volumes) - 1)
            volume_ok = today_vol >= avg_vol * 0.8 if avg_vol > 0 else True

        # 신호 판정
        signal = "none"
        if direction in ("long", "both") and today_high > long_breakout_price and volume_ok:
            signal = "long_entry"
        elif direction in ("short", "both") and today_low < short_breakout_price and volume_ok:
            signal = "short_entry"

        # 시계열 생성
        time_series = []
        for i in range(1, len(rows_sorted)):
            row = rows_sorted[i]
            p_range = highs[i - 1] - lows[i - 1]
            bar_open = opens[i]
            bar_high = highs[i]
            bar_low = lows[i]
            bar_vol = volumes[i]

            # K 계산 (ATR adaptive는 전체 데이터 필요)
            bar_k = k_factor
            if atr_adaptive and atr_value and closes[i] > 0:
                bar_k = _adaptive_k(k_factor, atr_value, closes[i])

            bar_breakout = _compute_breakout_price(bar_open, p_range, bar_k)
            bar_short_breakout = bar_open - bar_k * p_range

            # 거래량 필터
            bar_vol_ok = True
            if noise_filter and i >= 5:
                avg = sum(volumes[i - 5:i]) / 5
                bar_vol_ok = bar_vol >= avg * 0.8 if avg > 0 else True

            bar_signal = "none"
            if direction in ("long", "both") and bar_high > bar_breakout and bar_vol_ok:
                bar_signal = "long_entry"
            elif direction in ("short", "both") and bar_low < bar_short_breakout and bar_vol_ok:
                bar_signal = "short_entry"

            time_series.append({
                date_field: row.get(date_field, ""),
                open_field: row.get(open_field),
                high_field: row.get(high_field),
                low_field: row.get(low_field),
                close_field: row.get(close_field),
                volume_field: row.get(volume_field),
                "breakout_price": bar_breakout,
                "prev_range": round(p_range, 4),
                "signal": bar_signal,
                "k_used": round(bar_k, 4),
            })

        values.append({"symbol": symbol, "exchange": exchange, "time_series": time_series})

        symbol_results.append({
            "symbol": symbol, "exchange": exchange,
            "signal": signal,
            "breakout_price": long_breakout_price,
            "short_breakout_price": round(short_breakout_price, 4),
            "prev_range": round(prev_range, 4),
            "current_high": today_high,
            "current_low": today_low,
            "current_close": today_close,
            "k_used": round(effective_k, 4),
            "atr_value": atr_value,
        })

        has_signal = signal != "none"
        (passed if has_signal else failed).append(sym_dict)

    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "symbol_results": symbol_results,
        "values": values,
        "result": len(passed) > 0,
        "analysis": {
            "indicator": "VolatilityBreakout",
            "k_factor": k_factor,
            "atr_adaptive": atr_adaptive,
            "direction": direction,
            "noise_filter": noise_filter,
        },
    }


__all__ = ["volatility_breakout_condition", "_calculate_atr", "_compute_breakout_price", "VOLATILITY_BREAKOUT_SCHEMA"]
