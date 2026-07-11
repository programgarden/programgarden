"""
Graham Number (그레이엄 넘버) 플러그인

Benjamin Graham "The Intelligent Investor".
방어적 투자자를 위한 적정주가 상한 추정:
    Graham Number = sqrt(22.5 * EPS * BVPS)
(22.5 = 최대 허용 PER 15 × 최대 허용 PBR 1.5)

주가가 Graham Number 보다 낮으면 저평가(매수 후보)로 판정.

입력 형식 (재무 스냅샷 플랫 배열, 종목당 1행 - auto-iterate 안전):
- data: [{symbol, exchange, eps, per, pbr, current_price?}, ...]
- fields: {margin_of_safety}

값 유도:
- price = per * eps  (per/eps 결측 시 current_price 폴백)
- bvps  = price / pbr
- eps<=0 / bvps<=0 / price<=0 → per-symbol missing_reason (음수 EPS 는 sqrt 불가)
"""

import math
from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


GRAHAM_SCHEMA = PluginSchema(
    id="GrahamNumber",
    name="Graham Number",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description=(
        "Fundamental value screener (registered under TECHNICAL until a FUNDAMENTAL "
        "category exists). Benjamin Graham's fair-value ceiling: sqrt(22.5 * EPS * BVPS). "
        "A stock trading below its Graham Number (optionally minus a margin of safety) is "
        "flagged as undervalued. Derives price = PER * EPS (falls back to current_price) and "
        "BVPS = price / PBR. Non-positive EPS/BVPS/price yield a per-symbol missing_reason "
        "(no square root of a negative). Single-row-per-symbol input is auto-iterate safe."
    ),
    products=[ProductType.OVERSEAS_STOCK],
    fields_schema={
        "margin_of_safety": {
            "type": "float",
            "default": 0.0,
            "title": "Margin of Safety",
            "description": "Fractional discount required below the Graham Number to pass (0.25 = buy only 25% under fair value)",
            "ge": 0.0,
            "le": 0.9,
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange"],
    optional_fields=["eps", "per", "pbr", "current_price"],
    tags=["graham", "value", "fundamental", "intrinsic-value", "defensive"],
    output_fields={
        "graham_number": {"type": "float", "description": "Graham Number fair-value ceiling = sqrt(22.5 * EPS * BVPS)"},
        "price": {"type": "float", "description": "Reference price used (PER * EPS or current_price fallback)"},
        "bvps": {"type": "float", "description": "Book value per share derived from price / PBR"},
        "margin_pct": {"type": "float", "description": "Upside to the Graham Number vs price (%), positive = undervalued"},
        "undervalued": {"type": "bool", "description": "True when price is below the Graham Number (minus margin of safety)"},
    },
    locales={
        "ko": {
            "name": "그레이엄 넘버",
            "description": (
                "펀더멘털 밸류 스크리너 (FUNDAMENTAL 카테고리가 생기기 전까지 TECHNICAL 로 등록). "
                "벤저민 그레이엄의 적정주가 상한: sqrt(22.5 * EPS * BVPS). 주가가 Graham Number "
                "(안전마진 반영) 아래면 저평가로 판정합니다. price=PER*EPS(폴백 current_price), "
                "BVPS=price/PBR. EPS/BVPS/price 가 0 이하면 per-symbol missing_reason 을 반환합니다."
            ),
            "fields.margin_of_safety": "Graham Number 대비 요구 할인율 (0.25 = 적정가보다 25% 낮을 때만 통과)",
        },
    },
)


def _safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    """안전한 float 변환 (NaN/inf → default)"""
    if value is None:
        return default
    try:
        f = float(value)
    except (ValueError, TypeError):
        return default
    if f != f or f in (float("inf"), float("-inf")):
        return default
    return f


def compute_graham_number(eps: float, bvps: float) -> Optional[float]:
    """Graham Number = sqrt(22.5 * EPS * BVPS). eps/bvps 는 양수 전제."""
    product = 22.5 * eps * bvps
    if product <= 0:
        return None
    return math.sqrt(product)


async def graham_number_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
    context: Any = None,
    **kwargs,
) -> Dict[str, Any]:
    """그레이엄 넘버 조건 평가 (종목별 독립 - auto-iterate 안전)"""
    mapping = field_mapping or {}
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")
    eps_field = mapping.get("eps_field", "eps")
    per_field = mapping.get("per_field", "per")
    pbr_field = mapping.get("pbr_field", "pbr")
    price_field = mapping.get("price_field", "current_price")

    margin_of_safety = _safe_float(fields.get("margin_of_safety", 0.0), 0.0) or 0.0

    if not data or not isinstance(data, list):
        return {
            "passed_symbols": [], "failed_symbols": [],
            "symbol_results": [], "values": [],
            "result": False,
            "analysis": {"error": "No data provided", "indicator": "GrahamNumber"},
        }

    passed, failed, symbol_results, values = [], [], [], []
    seen_symbols = set()
    valid_count = 0

    for row in data:
        if not isinstance(row, dict):
            continue
        sym = row.get(symbol_field, "")
        if not sym or sym in seen_symbols:
            continue
        seen_symbols.add(sym)

        exchange = row.get(exchange_field, "UNKNOWN")
        sym_dict = {"symbol": sym, "exchange": exchange}
        values.append({"symbol": sym, "exchange": exchange, "time_series": []})

        eps = _safe_float(row.get(eps_field))
        per = _safe_float(row.get(per_field))
        pbr = _safe_float(row.get(pbr_field))
        current_price = _safe_float(row.get(price_field))

        # price = per * eps, 폴백 current_price
        price = None
        if per is not None and eps is not None:
            price = per * eps
        if (price is None or price <= 0) and current_price is not None:
            price = current_price

        # bvps = price / pbr
        bvps = None
        if price is not None and pbr is not None and pbr > 0:
            bvps = price / pbr

        # 결측/경계: eps<=0 / bvps<=0 / price<=0 → missing_reason
        missing_reason = None
        if eps is None or eps <= 0:
            missing_reason = "non_positive_eps"
        elif price is None or price <= 0:
            missing_reason = "non_positive_price"
        elif bvps is None or bvps <= 0:
            missing_reason = "non_positive_bvps"

        if missing_reason is not None:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": sym, "exchange": exchange,
                "graham_number": None, "price": round(price, 4) if price is not None else None,
                "bvps": round(bvps, 4) if bvps is not None else None,
                "eps": round(eps, 4) if eps is not None else None,
                "margin_pct": None, "undervalued": None,
                "missing_reason": missing_reason,
            })
            continue

        graham_number = compute_graham_number(eps, bvps)
        if graham_number is None:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": sym, "exchange": exchange,
                "graham_number": None, "price": round(price, 4),
                "bvps": round(bvps, 4), "eps": round(eps, 4),
                "margin_pct": None, "undervalued": None,
                "missing_reason": "non_positive_bvps",
            })
            continue

        valid_count += 1
        buy_threshold = graham_number * (1.0 - margin_of_safety)
        undervalued = price <= buy_threshold
        margin_pct = round((graham_number - price) / price * 100, 2)

        symbol_results.append({
            "symbol": sym, "exchange": exchange,
            "graham_number": round(graham_number, 4),
            "price": round(price, 4),
            "bvps": round(bvps, 4),
            "eps": round(eps, 4),
            "margin_pct": margin_pct,
            "undervalued": undervalued,
        })

        if undervalued:
            passed.append(sym_dict)
        else:
            failed.append(sym_dict)

    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "symbol_results": symbol_results,
        "values": values,
        "result": len(passed) > 0,
        "analysis": {
            "indicator": "GrahamNumber",
            "margin_of_safety": margin_of_safety,
            "total_symbols": len(seen_symbols),
            "valid_symbols": valid_count,
            "passed_count": len(passed),
        },
    }


__all__ = [
    "graham_number_condition",
    "GRAHAM_SCHEMA",
    "compute_graham_number",
    "_safe_float",
]
