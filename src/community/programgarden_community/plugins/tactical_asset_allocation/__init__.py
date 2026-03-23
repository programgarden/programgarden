"""
Tactical Asset Allocation (전술적 자산배분) 플러그인

Mebane Faber (2007) "A Quantitative Approach to Tactical Asset Allocation", SSRN.
월말 기준, 자산 가격이 10개월(200일) SMA 위면 보유, 아래면 현금.
원래 5개 자산군 동일 비중이나 단일 자산 추세 필터로도 활용 가능.

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, close, ...}, ...]
- fields: {sma_period, signal_mode, rebalance_check, margin_pct}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


TAA_SCHEMA = PluginSchema(
    id="TacticalAssetAllocation",
    name="Tactical Asset Allocation",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="SMA-based trend filter for tactical asset allocation (Faber 2007). Hold when price > N-day SMA, go to cash when below. Simple 200-day SMA rule has outperformed buy-and-hold with lower drawdowns in 5-asset portfolio.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "sma_period": {
            "type": "int",
            "default": 200,
            "title": "SMA Period",
            "description": "Simple moving average period (200 days ≈ 10 months, original Faber paper)",
            "ge": 50,
            "le": 300,
        },
        "signal_mode": {
            "type": "string",
            "default": "binary",
            "title": "Signal Mode",
            "description": "binary: 1.0 (hold) or 0.0 (cash), scaled: 0.0-1.0 proportional to SMA distance",
            "enum": ["binary", "scaled"],
        },
        "rebalance_check": {
            "type": "string",
            "default": "daily",
            "title": "Rebalance Check",
            "description": "daily: check every bar, monthly: only check on last day of month (original paper)",
            "enum": ["daily", "monthly"],
        },
        "margin_pct": {
            "type": "float",
            "default": 0.0,
            "title": "Margin (%)",
            "description": "Neutral zone around SMA to prevent whipsawing (e.g., 1.0 = ±1% SMA band)",
            "ge": 0.0,
            "le": 5.0,
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close"],
    optional_fields=["open", "high", "low", "volume"],
    tags=["taa", "sma", "trend", "allocation", "faber", "asset-allocation"],
    output_fields={
        "trend_signal": {"type": "str", "description": "Trend signal: 'above_sma' (hold), 'below_sma' (cash), or 'insufficient_data'"},
        "sma_value": {"type": "float", "description": "Current SMA value"},
        "distance_pct": {"type": "float", "description": "Percentage distance of price from SMA"},
        "allocation": {"type": "float", "description": "Recommended allocation (0.0 = cash, 1.0 = fully invested)"},
        "current_close": {"type": "float", "description": "Latest closing price"},
    },
    locales={
        "ko": {
            "name": "전술적 자산배분",
            "description": "SMA 기반 자산배분 추세 필터 (Faber 2007). 가격 > N일 SMA: 보유(1.0), 가격 < N일 SMA: 현금(0.0). 원래 5개 자산군 동일비중이나 단일 자산 추세 필터로도 사용 가능합니다.",
            "fields.sma_period": "단순이동평균 기간 (200일 ≈ 10개월, 원본 논문 기준)",
            "fields.signal_mode": "신호 방식 (binary: 보유/현금, scaled: SMA 거리 비례)",
            "fields.rebalance_check": "리밸런싱 체크 (daily: 매일, monthly: 월말, 원본 논문)",
            "fields.margin_pct": "중립 구간 % (SMA 근처 잦은 전환 방지)",
        },
    },
)


def _calculate_sma(prices: List[float], period: int) -> Optional[float]:
    """단순이동평균 계산"""
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period


def _is_last_day_of_month(current_date: str, next_date: Optional[str]) -> bool:
    """현재 날짜가 월의 마지막 거래일인지 확인"""
    if not next_date:
        return True  # 데이터의 마지막이면 마지막 날로 간주
    # 다음 날짜가 다른 월이면 현재가 마지막 거래일
    current_month = current_date[:6] if len(current_date) >= 6 else ""
    next_month = next_date[:6] if len(next_date) >= 6 else ""

    if "-" in current_date and "-" in next_date:
        current_month = current_date[:7]
        next_month = next_date[:7]

    return current_month != next_month and bool(current_month)


async def taa_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """전술적 자산배분 조건 평가"""
    mapping = field_mapping or {}
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")
    open_field = mapping.get("open_field", "open")
    high_field = mapping.get("high_field", "high")
    low_field = mapping.get("low_field", "low")
    volume_field = mapping.get("volume_field", "volume")

    sma_period = fields.get("sma_period", 200)
    signal_mode = fields.get("signal_mode", "binary")
    rebalance_check = fields.get("rebalance_check", "daily")
    margin_pct = fields.get("margin_pct", 0.0)

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

    passed, failed, symbol_results, values = [], [], [], []

    for sym_info in target_symbols:
        symbol, exchange = sym_info["symbol"], sym_info["exchange"]
        sym_dict = {"symbol": symbol, "exchange": exchange}
        rows = symbol_data_map.get(symbol, [])

        if not rows or len(rows) < sma_period:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol, "exchange": exchange,
                "trend_signal": "insufficient_data",
                "error": f"Insufficient data: need {sma_period}, got {len(rows)}",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))

        closes = []
        for row in rows_sorted:
            try:
                closes.append(float(row.get(close_field) or 0))
            except (ValueError, TypeError):
                closes.append(0.0)

        if len(closes) < sma_period:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol, "exchange": exchange,
                "trend_signal": "insufficient_data",
                "error": "Insufficient price data",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        # 현재 SMA 및 신호
        current_close = closes[-1]
        sma_value = _calculate_sma(closes, sma_period)

        def _compute_signal(price: float, sma: float) -> tuple:
            """(trend_signal, allocation, distance_pct) 계산"""
            if sma <= 0:
                return "neutral", 0.5, 0.0
            dist = (price - sma) / sma * 100
            upper_band = sma * (1 + margin_pct / 100)
            lower_band = sma * (1 - margin_pct / 100)

            if price > upper_band:
                trend = "above_sma"
            elif price < lower_band:
                trend = "below_sma"
            else:
                trend = "neutral"

            if signal_mode == "binary":
                alloc = 1.0 if trend == "above_sma" else 0.0
            else:  # scaled
                # SMA 대비 거리 비례: 0.5 at SMA, 1.0 at +10% above SMA, 0.0 at -10% below SMA
                alloc = max(0.0, min(1.0, 0.5 + dist / 20.0))

            return trend, round(alloc, 4), round(dist, 4)

        current_trend, current_allocation, distance_pct = _compute_signal(current_close, sma_value)

        # monthly 체크: 최신 바가 월말인지 확인
        if rebalance_check == "monthly":
            latest_date = str(rows_sorted[-1].get(date_field, ""))
            is_month_end = _is_last_day_of_month(latest_date, None)
            if not is_month_end:
                current_trend = "non_rebalance_day"
                current_allocation = None

        # 시계열 생성
        time_series = []
        for i in range(sma_period - 1, len(rows_sorted)):
            row = rows_sorted[i]
            bar_closes = closes[:i + 1]
            bar_sma = _calculate_sma(bar_closes, sma_period)
            bar_close = closes[i]

            if bar_sma:
                bar_trend, bar_alloc, bar_dist = _compute_signal(bar_close, bar_sma)
            else:
                bar_trend, bar_alloc, bar_dist = "neutral", 0.5, 0.0

            # monthly 체크
            if rebalance_check == "monthly":
                cur_date = str(row.get(date_field, ""))
                nxt_date = str(rows_sorted[i + 1].get(date_field, "")) if i + 1 < len(rows_sorted) else None
                if not _is_last_day_of_month(cur_date, nxt_date):
                    bar_trend = "non_rebalance_day"

            time_series.append({
                date_field: row.get(date_field, ""),
                open_field: row.get(open_field),
                high_field: row.get(high_field),
                low_field: row.get(low_field),
                close_field: row.get(close_field),
                volume_field: row.get(volume_field),
                "sma_value": round(bar_sma, 4) if bar_sma else None,
                "distance_pct": bar_dist,
                "trend_signal": bar_trend,
                "allocation": bar_alloc,
            })

        values.append({"symbol": symbol, "exchange": exchange, "time_series": time_series})

        symbol_results.append({
            "symbol": symbol, "exchange": exchange,
            "trend_signal": current_trend,
            "sma_value": round(sma_value, 4) if sma_value else None,
            "distance_pct": distance_pct,
            "allocation": current_allocation,
            "current_close": current_close,
        })

        # above_sma이면 통과
        passed_condition = current_trend == "above_sma"
        (passed if passed_condition else failed).append(sym_dict)

    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "symbol_results": symbol_results,
        "values": values,
        "result": len(passed) > 0,
        "analysis": {
            "indicator": "TacticalAssetAllocation",
            "sma_period": sma_period,
            "signal_mode": signal_mode,
            "rebalance_check": rebalance_check,
            "margin_pct": margin_pct,
        },
    }


__all__ = ["taa_condition", "_calculate_sma", "TAA_SCHEMA"]
