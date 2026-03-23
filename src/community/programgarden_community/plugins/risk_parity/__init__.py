"""
RiskParity (리스크 패리티) 플러그인

변동성 역비례 포트폴리오 비중 배분. 모든 자산이 동일한 위험을 기여하도록 조절.

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, close, ...}, ...]
- fields: {lookback, target_volatility, method, min_weight_pct, max_weight_pct}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


RISK_PARITY_SCHEMA = PluginSchema(
    id="RiskParity",
    name="Risk Parity",
    category=PluginCategory.POSITION,
    version="1.0.0",
    description="Allocates portfolio weights so each asset contributes equal risk. Supports inverse volatility and equal risk contribution methods.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "lookback": {
            "type": "int",
            "default": 60,
            "title": "Lookback Period",
            "description": "Lookback period for volatility calculation",
            "ge": 20,
            "le": 500,
        },
        "target_volatility": {
            "type": "float",
            "default": 15.0,
            "title": "Target Volatility (%)",
            "description": "Target annual portfolio volatility",
            "ge": 1.0,
            "le": 50.0,
        },
        "method": {
            "type": "string",
            "default": "inverse_vol",
            "title": "Method",
            "description": "Risk parity allocation method",
            "enum": ["inverse_vol", "equal_risk_contribution"],
        },
        "min_weight_pct": {
            "type": "float",
            "default": 2.0,
            "title": "Min Weight (%)",
            "description": "Minimum allocation weight per asset",
            "ge": 0.0,
            "le": 50.0,
        },
        "max_weight_pct": {
            "type": "float",
            "default": 40.0,
            "title": "Max Weight (%)",
            "description": "Maximum allocation weight per asset",
            "ge": 1.0,
            "le": 100.0,
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close"],
    optional_fields=[],
    tags=["risk_parity", "portfolio", "allocation", "volatility"],
    output_fields={
        "volatility": {"type": "float", "description": "Annualized realized volatility of the symbol (%)"},
        "weight_pct": {"type": "float", "description": "Risk parity portfolio weight for this symbol (%)"},
        "risk_contribution_pct": {"type": "float", "description": "Percentage of total portfolio risk contributed by this symbol (%)"},
    },
    locales={
        "ko": {
            "name": "리스크 패리티 (Risk Parity)",
            "description": "각 자산이 포트폴리오에 동일한 위험을 기여하도록 비중을 배분합니다. 변동성 역비례(Inverse Vol)와 동일 위험 기여도(ERC) 방식을 지원합니다.",
            "fields.lookback": "변동성 계산 기간",
            "fields.target_volatility": "목표 연간 포트폴리오 변동성 (%)",
            "fields.method": "배분 방식 (inverse_vol / equal_risk_contribution)",
            "fields.min_weight_pct": "최소 배분 비중 (%)",
            "fields.max_weight_pct": "최대 배분 비중 (%)",
        },
    },
)


def _calculate_realized_volatility(prices: List[float], lookback: int) -> float:
    """실현 변동성 계산 (연율화)"""
    if len(prices) < lookback + 1:
        return 0.0

    recent_prices = prices[-(lookback + 1):]
    returns = [
        (recent_prices[i] - recent_prices[i - 1]) / recent_prices[i - 1]
        for i in range(1, len(recent_prices))
        if recent_prices[i - 1] > 0
    ]

    if len(returns) < 2:
        return 0.0

    mean_r = sum(returns) / len(returns)
    variance = sum((r - mean_r) ** 2 for r in returns) / (len(returns) - 1)
    daily_vol = variance ** 0.5
    annual_vol = daily_vol * (252 ** 0.5)
    return annual_vol * 100  # 퍼센트


async def risk_parity_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
    context: Any = None,
    **kwargs,
) -> Dict[str, Any]:
    """리스크 패리티 포지션 배분 조건 평가"""
    mapping = field_mapping or {}
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")

    lookback = fields.get("lookback", 60)
    target_vol = fields.get("target_volatility", 15.0)
    method = fields.get("method", "inverse_vol")
    min_wt = fields.get("min_weight_pct", 2.0)
    max_wt = fields.get("max_weight_pct", 40.0)

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

    # 1단계: 종목별 변동성 계산
    vol_data = []
    for sym_info in symbols:
        symbol = sym_info.get("symbol", "") if isinstance(sym_info, dict) else str(sym_info)
        exchange = sym_info.get("exchange", "UNKNOWN") if isinstance(sym_info, dict) else "UNKNOWN"

        rows = symbol_data_map.get(symbol, [])
        if not rows:
            continue

        rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))
        prices = [float(r.get(close_field, 0)) for r in rows_sorted if r.get(close_field) is not None]

        vol = _calculate_realized_volatility(prices, lookback)
        if vol > 0:
            vol_data.append({"symbol": symbol, "exchange": exchange, "volatility": vol})

    if not vol_data:
        return {
            "passed_symbols": [], "failed_symbols": [],
            "symbol_results": [], "values": [],
            "result": False, "analysis": {"error": "No valid volatility data"},
        }

    n = len(vol_data)

    # 2단계: 비중 계산
    if method == "equal_risk_contribution":
        # ERC: 각 자산의 위험기여도가 동일하도록 배분
        # 상관관계 무시한 단순화 버전: inverse_vol과 동일하게 변동성 역비례
        # (정확한 ERC는 반복 최적화 필요하지만, 상관관계 없으면 inverse_vol과 동일)
        inv_vols = [1.0 / v["volatility"] for v in vol_data]
        total_inv = sum(inv_vols)
        raw_weights = [(iv / total_inv * 100) if total_inv > 0 else (100.0 / n) for iv in inv_vols]
    else:
        # inverse_vol: 변동성 역수 비례
        inv_vols = [1.0 / v["volatility"] for v in vol_data]
        total_inv = sum(inv_vols)
        raw_weights = [(iv / total_inv * 100) if total_inv > 0 else (100.0 / n) for iv in inv_vols]

    # 3단계: clamp 적용
    clamped_weights = [max(min_wt, min(max_wt, w)) for w in raw_weights]

    # 4단계: 정규화 (합계 = 100%)
    total_clamped = sum(clamped_weights)
    if total_clamped > 0:
        normalized_weights = [round(w / total_clamped * 100, 2) for w in clamped_weights]
    else:
        normalized_weights = [round(100.0 / n, 2)] * n

    # 5단계: 포트폴리오 변동성 계산
    portfolio_vol = sum(
        (normalized_weights[i] / 100) * vol_data[i]["volatility"]
        for i in range(n)
    )

    # 6단계: 결과 정리
    passed, failed, symbol_results, values = [], [], [], []

    for i, vd in enumerate(vol_data):
        symbol = vd["symbol"]
        exchange = vd["exchange"]
        weight = normalized_weights[i]
        sym_dict = {"symbol": symbol, "exchange": exchange}

        # 위험기여도 계산 (단순화: weight × vol)
        risk_contribution = (weight / 100) * vd["volatility"]
        risk_contribution_pct = round(risk_contribution / portfolio_vol * 100, 2) if portfolio_vol > 0 else 0

        passed.append(sym_dict)
        symbol_results.append({
            "symbol": symbol, "exchange": exchange,
            "volatility": round(vd["volatility"], 2),
            "weight_pct": weight,
            "risk_contribution_pct": risk_contribution_pct,
        })

        time_series = [{
            "weight_pct": weight,
            "volatility": round(vd["volatility"], 2),
            "signal": "buy",
            "side": "long",
        }]
        values.append({"symbol": symbol, "exchange": exchange, "time_series": time_series})

    return {
        "passed_symbols": passed, "failed_symbols": failed,
        "symbol_results": symbol_results, "values": values,
        "result": len(passed) > 0,
        "analysis": {
            "indicator": "RiskParity",
            "method": method,
            "target_volatility": target_vol,
            "total_symbols": n,
            "portfolio_volatility": round(portfolio_vol, 2),
        },
    }


__all__ = ["risk_parity_condition", "RISK_PARITY_SCHEMA"]
