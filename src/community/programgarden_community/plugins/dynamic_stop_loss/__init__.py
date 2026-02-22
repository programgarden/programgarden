"""
DynamicStopLoss (동적 손절) 플러그인

ATR 기반 변동성 적응형 손절가 산출.
StopLoss와 차별: 고정% 대신 변동성(ATR)에 따라 손절 폭이 자동 조절.

입력 형식 (POSITION Type B - data + positions 하이브리드):
- data: 시계열 데이터 (ATR 계산용) [{symbol, exchange, date, close, high, low, ...}]
- positions: 보유 포지션 {symbol: {current_price, avg_price, qty, ...}}
- fields: {atr_period, atr_multiplier, use_positions, trailing}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


DYNAMIC_STOP_LOSS_SCHEMA = PluginSchema(
    id="DynamicStopLoss",
    name="Dynamic Stop Loss",
    category=PluginCategory.POSITION,
    version="1.0.0",
    description="ATR-based dynamic stop loss. Calculates stop price based on current volatility rather than fixed percentage. Higher volatility = wider stop, lower volatility = tighter stop. Supports trailing mode.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "atr_period": {
            "type": "int",
            "default": 14,
            "title": "ATR Period",
            "description": "ATR calculation period",
            "ge": 5,
            "le": 50,
        },
        "atr_multiplier": {
            "type": "float",
            "default": 2.0,
            "title": "ATR Multiplier",
            "description": "ATR multiplier for stop distance",
            "ge": 0.5,
            "le": 5.0,
        },
        "use_positions": {
            "type": "bool",
            "default": True,
            "title": "Use Positions",
            "description": "Use position entry price as reference (True) or current price (False)",
        },
        "trailing": {
            "type": "bool",
            "default": False,
            "title": "Trailing Mode",
            "description": "Use trailing stop (highest price as reference instead of entry price)",
        },
    },
    required_data=["data", "positions"],
    required_fields=["symbol", "exchange", "date", "close", "high", "low"],
    optional_fields=[],
    tags=["stop_loss", "atr", "dynamic", "volatility", "exit"],
    locales={
        "ko": {
            "name": "동적 손절 (Dynamic Stop Loss)",
            "description": "ATR 기반 변동성 적응형 손절입니다. 고정 비율 대신 현재 변동성에 따라 손절 폭이 자동 조절됩니다. 변동성이 높으면 넓은 손절, 낮으면 좁은 손절입니다.",
            "fields.atr_period": "ATR 계산 기간",
            "fields.atr_multiplier": "ATR 배수 (손절 거리)",
            "fields.use_positions": "포지션 진입가 기준 사용 여부",
            "fields.trailing": "트레일링 모드 (최고가 기준)",
        },
    },
)


def _calculate_atr(highs: List[float], lows: List[float], closes: List[float], period: int) -> Optional[float]:
    """ATR 계산 (최신값)"""
    if len(highs) < 2 or len(highs) != len(lows) or len(highs) != len(closes):
        return None

    trs = [highs[0] - lows[0]]
    for i in range(1, len(highs)):
        trs.append(max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        ))

    if len(trs) < period:
        return None

    # Wilder 방식 ATR
    atr = sum(trs[:period]) / period
    for i in range(period, len(trs)):
        atr = (atr * (period - 1) + trs[i]) / period

    return atr


async def dynamic_stop_loss_condition(
    data: Optional[List[Dict[str, Any]]] = None,
    positions: Optional[Dict[str, Any]] = None,
    fields: Optional[Dict[str, Any]] = None,
    field_mapping: Optional[Dict[str, str]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """동적 손절 조건 평가"""
    if data is None:
        data = []
    if positions is None:
        positions = {}
    if fields is None:
        fields = {}

    mapping = field_mapping or {}
    close_field = mapping.get("close_field", "close")
    high_field = mapping.get("high_field", "high")
    low_field = mapping.get("low_field", "low")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")

    atr_period = fields.get("atr_period", 14)
    atr_multiplier = fields.get("atr_multiplier", 2.0)
    use_positions = fields.get("use_positions", True)
    trailing = fields.get("trailing", False)

    if not positions:
        return {
            "passed_symbols": [], "failed_symbols": [],
            "symbol_results": [], "values": [],
            "result": False,
            "analysis": {"error": "No positions data"},
        }

    # data에서 종목별 시계열 구축
    symbol_data_map: Dict[str, List[Dict]] = {}
    for row in data:
        if not isinstance(row, dict):
            continue
        sym = row.get(symbol_field, "")
        if not sym:
            continue
        if sym not in symbol_data_map:
            symbol_data_map[sym] = []
        symbol_data_map[sym].append(row)

    passed, failed, symbol_results = [], [], []

    for symbol, pos_data in positions.items():
        current_price = pos_data.get("current_price", 0)
        avg_price = pos_data.get("avg_price", current_price)
        exchange = pos_data.get("market_code", "UNKNOWN")

        exchange_map = {"81": "NYSE", "82": "NASDAQ", "83": "AMEX"}
        exchange_name = exchange_map.get(exchange, exchange)
        sym_dict = {"symbol": symbol, "exchange": exchange_name}

        # ATR 계산
        rows = symbol_data_map.get(symbol, [])
        atr = None

        if rows:
            rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))
            highs, lows, closes = [], [], []
            for row in rows_sorted:
                try:
                    highs.append(float(row.get(high_field, 0)))
                    lows.append(float(row.get(low_field, 0)))
                    closes.append(float(row.get(close_field, 0)))
                except (ValueError, TypeError):
                    pass

            if len(highs) >= atr_period + 1:
                atr = _calculate_atr(highs, lows, closes, atr_period)

        if atr is None:
            # ATR 계산 불가 → fallback: 현재가의 2% 사용
            atr = current_price * 0.02

        stop_distance = atr * atr_multiplier

        # 기준가 결정
        if trailing:
            # 트레일링: 데이터의 최고가 기준
            if rows:
                rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))
                high_prices = []
                for row in rows_sorted:
                    try:
                        high_prices.append(float(row.get(high_field, 0)))
                    except (ValueError, TypeError):
                        pass
                reference_price = max(high_prices) if high_prices else current_price
            else:
                reference_price = current_price
        elif use_positions:
            reference_price = avg_price
        else:
            reference_price = current_price

        stop_price = reference_price - stop_distance
        triggered = current_price <= stop_price
        stop_pct = ((stop_price - reference_price) / reference_price * 100) if reference_price > 0 else 0

        result_info = {
            "symbol": symbol, "exchange": exchange_name,
            "current_price": current_price,
            "avg_price": avg_price,
            "reference_price": round(reference_price, 4),
            "atr": round(atr, 4),
            "stop_distance": round(stop_distance, 4),
            "stop_price": round(stop_price, 4),
            "stop_pct": round(stop_pct, 2),
            "triggered": triggered,
        }
        symbol_results.append(result_info)

        if triggered:
            passed.append(sym_dict)
        else:
            failed.append(sym_dict)

    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "symbol_results": symbol_results,
        "values": [],
        "result": len(passed) > 0,
        "analysis": {
            "indicator": "DynamicStopLoss",
            "atr_period": atr_period,
            "atr_multiplier": atr_multiplier,
            "use_positions": use_positions,
            "trailing": trailing,
            "total_positions": len(positions),
            "triggered_count": len(passed),
        },
    }


__all__ = ["dynamic_stop_loss_condition", "DYNAMIC_STOP_LOSS_SCHEMA"]
