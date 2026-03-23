"""
VolatilityPositionSizing (변동성 기반 포지션 사이징) 플러그인

변동성 역비례 포지션 사이징. 목표 변동성 대비 자동 비중 조절.
자산별 동일한 위험 기여도를 보장합니다.

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, close, ...}, ...]
- fields: {target_volatility, vol_lookback, max_position_pct, min_position_pct, scaling_method}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


VOLATILITY_POSITION_SIZING_SCHEMA = PluginSchema(
    id="VolatilityPositionSizing",
    name="Volatility Position Sizing",
    category=PluginCategory.POSITION,
    version="1.0.0",
    description="Adjusts position size inversely proportional to asset volatility. Ensures equal risk contribution per position regardless of asset volatility.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "target_volatility": {
            "type": "float",
            "default": 15.0,
            "title": "Target Volatility (%)",
            "description": "Annual volatility target for the portfolio",
            "ge": 1.0,
            "le": 50.0,
        },
        "vol_lookback": {
            "type": "int",
            "default": 20,
            "title": "Volatility Lookback",
            "description": "Lookback period for realized volatility calculation",
            "ge": 5,
            "le": 252,
        },
        "max_position_pct": {
            "type": "float",
            "default": 20.0,
            "title": "Max Position (%)",
            "description": "Maximum position size as portfolio percentage",
            "ge": 1.0,
            "le": 100.0,
        },
        "min_position_pct": {
            "type": "float",
            "default": 2.0,
            "title": "Min Position (%)",
            "description": "Minimum position size as portfolio percentage",
            "ge": 0.0,
            "le": 50.0,
        },
        "scaling_method": {
            "type": "string",
            "default": "inverse_vol",
            "title": "Scaling Method",
            "description": "Position sizing method",
            "enum": ["inverse_vol", "vol_target", "equal_risk"],
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close"],
    optional_fields=[],
    tags=["position_sizing", "volatility", "risk_management"],
    output_fields={
        "volatility": {"type": "float", "description": "Annualized realized volatility of the symbol (%)"},
        "position_pct": {"type": "float", "description": "Recommended position size as portfolio percentage (%)"},
        "target_volatility": {"type": "float", "description": "Target annual volatility used for sizing (%)"},
        "scaling_method": {"type": "str", "description": "Sizing method applied: 'inverse_vol', 'vol_target', or 'equal_risk'"},
    },
    locales={
        "ko": {
            "name": "변동성 기반 포지션 사이징",
            "description": "자산의 변동성에 반비례하여 포지션 크기를 조절합니다. 변동성이 높은 자산은 작은 비중, 낮은 자산은 큰 비중으로 자산별 동일한 위험 기여도를 보장합니다.",
            "fields.target_volatility": "목표 연간 변동성 (%)",
            "fields.vol_lookback": "변동성 계산 기간",
            "fields.max_position_pct": "최대 포지션 비중 (%)",
            "fields.min_position_pct": "최소 포지션 비중 (%)",
            "fields.scaling_method": "사이징 방식 (inverse_vol/vol_target/equal_risk)",
        },
    },
)


def _calculate_realized_volatility(prices: List[float], lookback: int) -> float:
    """실현 변동성 계산 (연율화)"""
    if len(prices) < lookback + 1:
        return 0.0

    recent_prices = prices[-(lookback + 1):]
    returns = [(recent_prices[i] - recent_prices[i - 1]) / recent_prices[i - 1]
               for i in range(1, len(recent_prices))
               if recent_prices[i - 1] > 0]

    if len(returns) < 2:
        return 0.0

    mean_r = sum(returns) / len(returns)
    variance = sum((r - mean_r) ** 2 for r in returns) / (len(returns) - 1)
    daily_vol = variance ** 0.5
    annual_vol = daily_vol * (252 ** 0.5)  # 연율화
    return annual_vol * 100  # 퍼센트


async def volatility_position_sizing_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """변동성 기반 포지션 사이징 조건 평가"""
    mapping = field_mapping or {}
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")

    target_vol = fields.get("target_volatility", 15.0)
    vol_lookback = fields.get("vol_lookback", 20)
    max_pos = fields.get("max_position_pct", 20.0)
    min_pos = fields.get("min_position_pct", 2.0)
    scaling_method = fields.get("scaling_method", "inverse_vol")

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
    vol_data = []

    # 1단계: 각 종목의 변동성 계산
    for sym_info in symbols:
        symbol = sym_info.get("symbol", "") if isinstance(sym_info, dict) else str(sym_info)
        exchange = sym_info.get("exchange", "UNKNOWN") if isinstance(sym_info, dict) else "UNKNOWN"

        rows = symbol_data_map.get(symbol, [])
        if not rows:
            continue

        rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))
        prices = [float(r.get(close_field, 0)) for r in rows_sorted if r.get(close_field) is not None]

        vol = _calculate_realized_volatility(prices, vol_lookback)
        if vol > 0:
            vol_data.append({"symbol": symbol, "exchange": exchange, "volatility": vol, "prices": prices})

    if not vol_data:
        return {
            "passed_symbols": [], "failed_symbols": [],
            "symbol_results": [], "values": [],
            "result": False, "analysis": {"error": "No valid volatility data"},
        }

    # 2단계: 포지션 비중 계산
    if scaling_method == "inverse_vol":
        # 변동성 역수 비례 배분
        inv_vols = [1.0 / v["volatility"] for v in vol_data]
        total_inv_vol = sum(inv_vols)
        for i, vd in enumerate(vol_data):
            raw_weight = (inv_vols[i] / total_inv_vol * 100) if total_inv_vol > 0 else (100.0 / len(vol_data))
            vd["position_pct"] = max(min_pos, min(max_pos, round(raw_weight, 2)))

    elif scaling_method == "vol_target":
        # 목표 변동성 대비 비중
        for vd in vol_data:
            raw_weight = target_vol / vd["volatility"] * (100.0 / len(vol_data))
            vd["position_pct"] = max(min_pos, min(max_pos, round(raw_weight, 2)))

    else:  # equal_risk
        # 동일 위험 기여도
        inv_vols = [1.0 / v["volatility"] for v in vol_data]
        total_inv_vol = sum(inv_vols)
        for i, vd in enumerate(vol_data):
            raw_weight = (inv_vols[i] / total_inv_vol * 100) if total_inv_vol > 0 else (100.0 / len(vol_data))
            vd["position_pct"] = max(min_pos, min(max_pos, round(raw_weight, 2)))

    # 3단계: 결과 정리
    for vd in vol_data:
        symbol = vd["symbol"]
        exchange = vd["exchange"]
        sym_dict = {"symbol": symbol, "exchange": exchange}

        # 모든 종목이 passed (포지션 사이징 결과 제공)
        passed.append(sym_dict)

        symbol_results.append({
            "symbol": symbol, "exchange": exchange,
            "volatility": round(vd["volatility"], 2),
            "position_pct": vd["position_pct"],
            "target_volatility": target_vol,
            "scaling_method": scaling_method,
        })

        time_series = [{
            "volatility": round(vd["volatility"], 2),
            "position_pct": vd["position_pct"],
            "signal": "buy",
            "side": "long",
        }]
        values.append({"symbol": symbol, "exchange": exchange, "time_series": time_series})

    return {
        "passed_symbols": passed, "failed_symbols": failed,
        "symbol_results": symbol_results, "values": values,
        "result": len(passed) > 0,
        "analysis": {
            "indicator": "VolatilityPositionSizing",
            "target_volatility": target_vol,
            "vol_lookback": vol_lookback,
            "scaling_method": scaling_method,
            "total_symbols": len(vol_data),
        },
    }


__all__ = ["volatility_position_sizing_condition", "VOLATILITY_POSITION_SIZING_SCHEMA"]
