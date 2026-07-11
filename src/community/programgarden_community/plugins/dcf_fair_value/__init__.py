"""
DCF Fair Value (2단계 현금흐름할인) 플러그인

2-stage Discounted Cash Flow 로 주당 내재가치(fair value)를 추정하고,
현재가 대비 안전마진을 적용해 저평가 여부를 판정합니다.

  Stage 1: FCF 를 growth_rate 로 years 년간 성장시켜 각 연도 FCF 를 할인
  Terminal: 마지막 FCF 를 (1+terminal_growth)/(r-terminal_growth) 로 영구가치화
  fair_value_per_share = (Σ PV(FCF) + PV(Terminal)) / shares_outstanding

⚠️ 필수 upstream 입력 `fcf` (자유현금흐름):
FundamentalDataNode (FMP) 는 cash_flow (data_type) 를 **제공하지 않으므로**
fcf 를 만들 수 없습니다. 반드시 상류에서 fcf 를 주입해야 하며(companion:
programmer_example/dcf_cashflow_datapath.py — HTTPRequestNode(FMP
cash-flow-statement) → FieldMappingNode(freeCashFlow→fcf) → 본 플러그인),
fcf 가 없으면 per-symbol missing_reason 을 반환합니다 (숨은 추정 금지).

입력 형식 (종목당 1행):
- data: [{symbol, exchange, fcf, shares_outstanding, current_price}, ...]
- fields: {growth_rate, discount_rate, terminal_growth, years, margin_of_safety}

r <= terminal_growth 이면 terminal value 발산 → analysis.error (config 오류).
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


DCF_SCHEMA = PluginSchema(
    id="DCFFairValue",
    name="DCF Fair Value",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description=(
        "Fundamental value screener (registered under TECHNICAL until a FUNDAMENTAL "
        "category exists). Two-stage Discounted Cash Flow: projects free cash flow at "
        "growth_rate for `years`, discounts at discount_rate, adds a Gordon terminal value, "
        "and divides by shares to get fair value per share. REQUIRES an upstream `fcf` input — "
        "FundamentalDataNode does NOT provide free cash flow, so fcf must be supplied via a "
        "cash-flow data path (see dcf_cashflow_datapath companion); missing fcf yields a "
        "per-symbol missing_reason with no hidden estimation. discount_rate <= terminal_growth "
        "returns analysis.error."
    ),
    products=[ProductType.OVERSEAS_STOCK],
    fields_schema={
        "growth_rate": {
            "type": "float",
            "default": 0.10,
            "title": "Growth Rate",
            "description": "Stage-1 annual FCF growth rate (0.10 = 10%)",
            "ge": -0.5,
            "le": 1.0,
        },
        "discount_rate": {
            "type": "float",
            "default": 0.09,
            "title": "Discount Rate (r)",
            "description": "Discount rate / required return (0.09 = 9%). Must exceed terminal_growth",
            "ge": 0.0,
            "le": 1.0,
        },
        "terminal_growth": {
            "type": "float",
            "default": 0.025,
            "title": "Terminal Growth",
            "description": "Perpetual growth rate after the projection window (0.025 = 2.5%)",
            "ge": -0.1,
            "le": 0.1,
        },
        "years": {
            "type": "int",
            "default": 10,
            "title": "Projection Years",
            "description": "Number of explicit stage-1 projection years",
            "ge": 1,
            "le": 30,
        },
        "margin_of_safety": {
            "type": "float",
            "default": 0.25,
            "title": "Margin of Safety",
            "description": "Fractional discount below fair value required to flag undervalued (0.25 = 25%)",
            "ge": 0.0,
            "le": 0.9,
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange"],
    optional_fields=["fcf", "shares_outstanding", "current_price"],
    tags=["dcf", "value", "fundamental", "intrinsic-value", "cash-flow"],
    output_fields={
        "fair_value": {"type": "float", "description": "Estimated intrinsic value per share from the 2-stage DCF"},
        "current_price": {"type": "float", "description": "Current market price used for the undervalued check"},
        "buy_price": {"type": "float", "description": "fair_value * (1 - margin_of_safety) — the disciplined buy ceiling"},
        "margin_pct": {"type": "float", "description": "Upside to fair value vs price (%), positive = undervalued"},
        "undervalued": {"type": "bool", "description": "True when current_price is at/below buy_price"},
    },
    locales={
        "ko": {
            "name": "DCF 적정가치",
            "description": (
                "펀더멘털 밸류 스크리너 (FUNDAMENTAL 카테고리가 생기기 전까지 TECHNICAL 로 등록). "
                "2단계 DCF 로 주당 내재가치를 추정합니다. `fcf` 는 필수 상류 입력이며 "
                "FundamentalDataNode 는 이를 제공하지 않으므로 현금흐름 데이터경로로 주입해야 합니다"
                "(companion 참고). fcf 결측 시 per-symbol missing_reason 을 반환합니다. "
                "discount_rate <= terminal_growth 이면 analysis.error."
            ),
            "fields.growth_rate": "1단계 연간 FCF 성장률 (0.10 = 10%)",
            "fields.discount_rate": "할인율/요구수익률 (terminal_growth 보다 커야 함)",
            "fields.terminal_growth": "예측기간 이후 영구 성장률",
            "fields.years": "명시적 1단계 예측 연수",
            "fields.margin_of_safety": "저평가 판정에 필요한 적정가 대비 할인율",
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


def compute_dcf_fair_value(
    fcf: float,
    shares: float,
    growth_rate: float,
    discount_rate: float,
    terminal_growth: float,
    years: int,
) -> Optional[float]:
    """
    2단계 DCF 주당 내재가치.

    호출 전 discount_rate > terminal_growth 및 shares > 0 를 보장할 것.
    """
    if shares <= 0:
        return None

    r = discount_rate
    pv_sum = 0.0
    projected_fcf = fcf
    last_fcf = fcf
    for t in range(1, years + 1):
        projected_fcf = projected_fcf * (1.0 + growth_rate)
        pv_sum += projected_fcf / ((1.0 + r) ** t)
        last_fcf = projected_fcf

    # Gordon terminal value at year N, discounted back to present
    terminal_value = last_fcf * (1.0 + terminal_growth) / (r - terminal_growth)
    pv_terminal = terminal_value / ((1.0 + r) ** years)

    total_value = pv_sum + pv_terminal
    return total_value / shares


async def dcf_fair_value_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
    context: Any = None,
    **kwargs,
) -> Dict[str, Any]:
    """DCF 적정가치 조건 평가 (종목별 독립)"""
    mapping = field_mapping or {}
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")
    fcf_field = mapping.get("fcf_field", "fcf")
    shares_field = mapping.get("shares_field", "shares_outstanding")
    price_field = mapping.get("price_field", "current_price")

    growth_rate = _safe_float(fields.get("growth_rate", 0.10), 0.10)
    discount_rate = _safe_float(fields.get("discount_rate", 0.09), 0.09)
    terminal_growth = _safe_float(fields.get("terminal_growth", 0.025), 0.025)
    years = int(fields.get("years", 10))
    margin_of_safety = _safe_float(fields.get("margin_of_safety", 0.25), 0.25) or 0.0

    # === config 오류: r <= terminal_growth → terminal value 발산 ===
    if discount_rate <= terminal_growth:
        return {
            "passed_symbols": [], "failed_symbols": [],
            "symbol_results": [], "values": [],
            "result": False,
            "analysis": {
                "error": "discount_rate must be greater than terminal_growth (Gordon terminal value diverges otherwise)",
                "indicator": "DCFFairValue",
                "discount_rate": discount_rate,
                "terminal_growth": terminal_growth,
            },
        }

    if not data or not isinstance(data, list):
        return {
            "passed_symbols": [], "failed_symbols": [],
            "symbol_results": [], "values": [],
            "result": False,
            "analysis": {"error": "No data provided", "indicator": "DCFFairValue"},
        }

    passed, failed, symbol_results, values = [], [], [], []
    seen_symbols = set()
    valid_count = 0
    fcf_missing_count = 0

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

        fcf = _safe_float(row.get(fcf_field))
        shares = _safe_float(row.get(shares_field))
        current_price = _safe_float(row.get(price_field))

        # === fcf 필수 (숨은 추정 금지) ===
        if fcf is None:
            fcf_missing_count += 1
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": sym, "exchange": exchange,
                "fair_value": None, "current_price": current_price,
                "buy_price": None, "margin_pct": None, "undervalued": None,
                "missing_reason": "fcf_unavailable",
                "detail": "fcf is required upstream; FundamentalDataNode does not provide free cash flow",
            })
            continue

        if shares is None or shares <= 0:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": sym, "exchange": exchange,
                "fair_value": None, "current_price": current_price,
                "buy_price": None, "margin_pct": None, "undervalued": None,
                "missing_reason": "invalid_shares_outstanding",
            })
            continue

        fair_value = compute_dcf_fair_value(
            fcf, shares, growth_rate, discount_rate, terminal_growth, years
        )
        if fair_value is None or fair_value != fair_value:  # None/NaN 가드
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": sym, "exchange": exchange,
                "fair_value": None, "current_price": current_price,
                "buy_price": None, "margin_pct": None, "undervalued": None,
                "missing_reason": "dcf_computation_failed",
            })
            continue

        valid_count += 1
        buy_price = fair_value * (1.0 - margin_of_safety)

        # current_price 없으면 저평가 판정 불가 (silent 금지 → missing_reason)
        if current_price is None or current_price <= 0:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": sym, "exchange": exchange,
                "fair_value": round(fair_value, 4),
                "current_price": None,
                "buy_price": round(buy_price, 4),
                "margin_pct": None, "undervalued": None,
                "missing_reason": "current_price_unavailable",
            })
            continue

        undervalued = current_price <= buy_price
        margin_pct = round((fair_value - current_price) / current_price * 100, 2)

        symbol_results.append({
            "symbol": sym, "exchange": exchange,
            "fair_value": round(fair_value, 4),
            "current_price": round(current_price, 4),
            "buy_price": round(buy_price, 4),
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
            "indicator": "DCFFairValue",
            "growth_rate": growth_rate,
            "discount_rate": discount_rate,
            "terminal_growth": terminal_growth,
            "years": years,
            "margin_of_safety": margin_of_safety,
            "total_symbols": len(seen_symbols),
            "valid_symbols": valid_count,
            "fcf_missing_count": fcf_missing_count,
            "passed_count": len(passed),
        },
    }


__all__ = [
    "dcf_fair_value_condition",
    "DCF_SCHEMA",
    "compute_dcf_fair_value",
    "_safe_float",
]
