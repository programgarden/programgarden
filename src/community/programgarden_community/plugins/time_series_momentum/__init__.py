"""
TimeSeriesMomentum (시계열 모멘텀) 플러그인

개별 자산의 과거 N일 수익률 부호에 따라 매수/매도 결정.
수익률 > 0 → 롱(매수), 수익률 < 0 → 숏(매도) 또는 청산.
참고: Moskowitz, Ooi, Pedersen (2012), "Time Series Momentum", Journal of Financial Economics

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, close, ...}, ...]
- fields: {lookback_days, signal_mode, volatility_adjust, vol_target}
"""

import math
from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


TSMOM_SCHEMA = PluginSchema(
    id="TimeSeriesMomentum",
    name="Time Series Momentum",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Individual asset momentum based on past N-day return sign. Long when return > 0, short/exit when return < 0. Optionally scales signal by volatility target. Based on Moskowitz, Ooi, Pedersen (2012).",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "lookback_days": {
            "type": "int",
            "default": 252,
            "title": "Lookback Days",
            "description": "Lookback period for return calculation",
            "ge": 20,
            "le": 504,
        },
        "signal_mode": {
            "type": "string",
            "default": "binary",
            "title": "Signal Mode",
            "description": "binary: long/short only, scaled: signal proportional to return",
            "enum": ["binary", "scaled"],
        },
        "volatility_adjust": {
            "type": "bool",
            "default": True,
            "title": "Volatility Adjust",
            "description": "Scale signal by volatility target",
        },
        "vol_target": {
            "type": "float",
            "default": 0.15,
            "title": "Volatility Target",
            "description": "Target annualized volatility (0.01~0.50)",
            "ge": 0.01,
            "le": 0.50,
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close"],
    optional_fields=["volume"],
    tags=["momentum", "time-series", "tsmom", "trend-following"],
    output_fields={
        "momentum_return": {"type": "float", "description": "Raw momentum return over the lookback period (fractional)"},
        "signal": {"type": "str", "description": "Momentum signal: 'long', 'short', or 'neutral'"},
        "vol_adjusted_signal": {"type": "float", "description": "Volatility-adjusted signal scaled to target volatility"},
        "current_price": {"type": "float", "description": "Latest closing price"},
    },
    locales={
        "ko": {
            "name": "시계열 모멘텀",
            "description": "개별 자산의 과거 수익률 부호로 매매 방향 결정 (Moskowitz et al. 2012). 변동성 조정으로 포지션 크기를 표준화합니다.",
            "fields.lookback_days": "룩백 기간 (일)",
            "fields.signal_mode": "신호 모드 (binary: 이진, scaled: 수익률 비례)",
            "fields.volatility_adjust": "변동성 조정 여부",
            "fields.vol_target": "목표 변동성 (연율화)",
        },
    },
)


def _calc_annualized_vol(returns: List[float]) -> float:
    """연율화 변동성 계산 (일별 수익률 리스트 입력)"""
    if len(returns) < 2:
        return 0.0
    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    daily_vol = math.sqrt(variance)
    return daily_vol * math.sqrt(252)


def calculate_tsmom(
    closes: List[float],
    lookback_days: int = 252,
    signal_mode: str = "binary",
    volatility_adjust: bool = True,
    vol_target: float = 0.15,
) -> Optional[Dict[str, Any]]:
    """
    TimeSeriesMomentum 계산

    Args:
        closes: 종가 리스트 (오래된→최신)
        lookback_days: 룩백 기간
        signal_mode: "binary" or "scaled"
        volatility_adjust: 변동성 조정 여부
        vol_target: 목표 변동성

    Returns:
        {"momentum_return": float, "signal": str, "vol_adjusted_signal": float} 또는 None
    """
    if len(closes) < lookback_days + 1:
        return None

    price_now = closes[-1]
    price_past = closes[-(lookback_days + 1)]

    if price_past <= 0:
        return None

    momentum_return = (price_now / price_past) - 1.0

    # 신호 결정
    if signal_mode == "binary":
        signal = "long" if momentum_return > 0 else ("short" if momentum_return < 0 else "neutral")
        raw_signal = 1.0 if momentum_return > 0 else (-1.0 if momentum_return < 0 else 0.0)
    else:  # scaled
        raw_signal = momentum_return
        if momentum_return > 0:
            signal = "long"
        elif momentum_return < 0:
            signal = "short"
        else:
            signal = "neutral"

    # 변동성 조정
    vol_adjusted_signal = raw_signal
    if volatility_adjust:
        # 최근 60일 일별 수익률로 변동성 계산
        vol_window = min(60, len(closes) - 1)
        daily_returns = []
        for i in range(len(closes) - vol_window, len(closes)):
            if closes[i - 1] > 0:
                daily_returns.append(closes[i] / closes[i - 1] - 1.0)

        ann_vol = _calc_annualized_vol(daily_returns)
        if ann_vol > 0:
            vol_adjusted_signal = raw_signal * (vol_target / ann_vol)
        # 신호를 [-2, 2] 범위로 클램핑
        vol_adjusted_signal = max(-2.0, min(2.0, vol_adjusted_signal))

    return {
        "momentum_return": round(momentum_return, 6),
        "signal": signal,
        "vol_adjusted_signal": round(vol_adjusted_signal, 4),
    }


async def time_series_momentum_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    TimeSeriesMomentum 조건 평가

    Args:
        data: 플랫 배열 데이터
        fields: {lookback_days, signal_mode, volatility_adjust, vol_target}
        field_mapping: 필드명 매핑
        symbols: 평가할 종목 리스트

    Returns:
        표준 플러그인 결과 (passed_symbols, failed_symbols, symbol_results, values, result)
    """
    mapping = field_mapping or {}
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")
    open_field = mapping.get("open_field", "open")
    high_field = mapping.get("high_field", "high")
    low_field = mapping.get("low_field", "low")
    volume_field = mapping.get("volume_field", "volume")

    lookback_days = fields.get("lookback_days", 252)
    signal_mode = fields.get("signal_mode", "binary")
    volatility_adjust = fields.get("volatility_adjust", True)
    vol_target = fields.get("vol_target", 0.15)

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
        symbol = sym_info["symbol"]
        exchange = sym_info["exchange"]
        sym_dict = {"symbol": symbol, "exchange": exchange}

        rows = symbol_data_map.get(symbol, [])
        min_required = lookback_days + 2  # lookback_days + 최소 1개 이상

        if not rows or len(rows) < min_required:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol, "exchange": exchange,
                "momentum_return": None,
                "signal": "neutral",
                "vol_adjusted_signal": 0.0,
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
                "momentum_return": None,
                "signal": "neutral",
                "vol_adjusted_signal": 0.0,
                "error": f"Insufficient price data: need {min_required}, got {len(closes)}",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        # 현재 TSMOM 계산
        tsmom_result = calculate_tsmom(
            closes, lookback_days, signal_mode, volatility_adjust, vol_target
        )

        if tsmom_result is None:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol, "exchange": exchange,
                "momentum_return": None, "signal": "neutral", "vol_adjusted_signal": 0.0,
                "error": "Calculation failed",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        # time_series: 주요 포인트만 (마지막 N개)
        time_series = []
        ts_window = min(len(rows_sorted), lookback_days + 10)
        for i in range(len(rows_sorted) - ts_window, len(rows_sorted)):
            if i < lookback_days + 1:
                continue
            ts_closes = closes[:i + 1]
            ts_result = calculate_tsmom(ts_closes, lookback_days, signal_mode, volatility_adjust, vol_target)
            if ts_result:
                original_row = rows_sorted[i]
                time_series.append({
                    date_field: original_row.get(date_field, ""),
                    close_field: original_row.get(close_field),
                    "momentum_return": ts_result["momentum_return"],
                    "signal": ts_result["signal"],
                    "vol_adjusted_signal": ts_result["vol_adjusted_signal"],
                })

        values.append({"symbol": symbol, "exchange": exchange, "time_series": time_series})

        symbol_results.append({
            "symbol": symbol, "exchange": exchange,
            "momentum_return": tsmom_result["momentum_return"],
            "signal": tsmom_result["signal"],
            "vol_adjusted_signal": tsmom_result["vol_adjusted_signal"],
            "current_price": closes[-1],
        })

        # 조건 평가: signal == "long"이면 통과
        passed_condition = tsmom_result["signal"] == "long"
        (passed if passed_condition else failed).append(sym_dict)

    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "symbol_results": symbol_results,
        "values": values,
        "result": len(passed) > 0,
        "analysis": {
            "indicator": "TimeSeriesMomentum",
            "lookback_days": lookback_days,
            "signal_mode": signal_mode,
            "volatility_adjust": volatility_adjust,
            "vol_target": vol_target,
        },
    }


__all__ = ["time_series_momentum_condition", "calculate_tsmom", "TSMOM_SCHEMA"]
