"""
EV/EBITDA Screen (기업가치배수 스크린) 플러그인

EV/EBITDA (Enterprise Value ÷ EBITDA) 는 자본구조에 중립적인 밸류에이션 배수로,
낮을수록 싸다고 본다. 본 플러그인은 단순 임계값 스크린(0 < EV/EBITDA <= max)이며,
선택적으로 top_n 최저 배수 랭킹을 제공한다.

Magic Formula 와의 차이 (중복 아님):
- MagicFormula: EV/EBITDA(또는 EY) 를 자본수익률(ROC) 순위와 **합산**한 복합 랭킹.
- EVEBITDAScreen: EV/EBITDA **단일** 배수만 보는 standalone 저평가 스크린 +
  선택적 최저-N 랭킹. 품질 축(ROC/ROE)을 섞지 않는다.

입력 형식 (재무 스냅샷 플랫 배열, 종목당 1행):
- data: [{symbol, exchange, ev_to_ebitda}, ...]
        (ev_to_ebitda 미제공 시 enterprise_value / ebitda 로 계산)
- fields: {max_ev_ebitda, top_n}

⚠️ top_n>0 랭킹은 교차종목(cross-sectional) 계산 — 심볼 >100 배치 청킹 시 청크별
   오정렬이 발생하므로 심볼 ≤100 또는 NodeRunner 단일 호출로 사용할 것.
   EBITDA<=0 이거나 배수<=0 이면 per-symbol missing_reason (음수 배수는 무의미).
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


EV_EBITDA_SCHEMA = PluginSchema(
    id="EVEBITDAScreen",
    name="EV/EBITDA Screen",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description=(
        "Fundamental value screener (registered under TECHNICAL until a FUNDAMENTAL "
        "category exists). Standalone EV/EBITDA valuation screen: passes symbols with "
        "0 < EV/EBITDA <= max_ev_ebitda and optionally ranks the lowest-N cheapest multiples. "
        "Unlike MagicFormula (which COMBINES EV/EBITDA with a return-on-capital rank), this "
        "screen looks at the EV/EBITDA multiple alone with no quality axis. top_n ranking is "
        "cross-sectional, so use <=100 symbols or a single NodeRunner call to avoid chunked "
        "mis-ranking. Non-positive EBITDA/multiple yields a per-symbol missing_reason."
    ),
    products=[ProductType.OVERSEAS_STOCK],
    fields_schema={
        "max_ev_ebitda": {
            "type": "float",
            "default": 10.0,
            "title": "Max EV/EBITDA",
            "description": "Maximum EV/EBITDA multiple to pass (inclusive). Lower = stricter/cheaper",
            "ge": 0.1,
            "le": 100.0,
        },
        "top_n": {
            "type": "int",
            "default": 0,
            "title": "Top N (cheapest)",
            "description": "If > 0, keep only the N lowest EV/EBITDA symbols among those under the threshold (cross-sectional)",
            "ge": 0,
            "le": 100,
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange"],
    optional_fields=["ev_to_ebitda", "enterprise_value", "ebitda"],
    tags=["ev-ebitda", "value", "fundamental", "valuation", "multiple", "multi-symbol"],
    output_fields={
        "ev_to_ebitda": {"type": "float", "description": "EV/EBITDA multiple screened for this symbol"},
        "rank": {"type": "int", "description": "Cross-sectional rank by lowest EV/EBITDA (1 = cheapest); null when top_n=0"},
        "passed": {"type": "bool", "description": "True when the symbol satisfies the screen (and top_n cut if set)"},
    },
    locales={
        "ko": {
            "name": "EV/EBITDA 스크린",
            "description": (
                "펀더멘털 밸류 스크리너 (FUNDAMENTAL 카테고리가 생기기 전까지 TECHNICAL 로 등록). "
                "EV/EBITDA 단일 배수 저평가 스크린: 0 < EV/EBITDA <= max_ev_ebitda 를 통과시키고 "
                "선택적으로 최저-N 배수를 랭킹합니다. MagicFormula(EV/EBITDA 를 자본수익률 순위와 "
                "합산)와 달리 품질 축 없이 배수만 봅니다. top_n 랭킹은 교차종목 계산이므로 심볼 ≤100 "
                "또는 NodeRunner 단일 호출로 사용하세요. EBITDA/배수 가 0 이하면 missing_reason 반환."
            ),
            "fields.max_ev_ebitda": "통과 최대 EV/EBITDA 배수 (낮을수록 엄격/저평가)",
            "fields.top_n": "0 초과 시 임계값 통과 종목 중 최저 배수 N개만 선별 (교차종목)",
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


async def ev_ebitda_screen_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
    context: Any = None,
    **kwargs,
) -> Dict[str, Any]:
    """EV/EBITDA 스크린 조건 평가 (다중 종목, top_n 은 교차종목)"""
    mapping = field_mapping or {}
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")
    multiple_field = mapping.get("ev_ebitda_field", "ev_to_ebitda")
    ev_field = mapping.get("ev_field", "enterprise_value")
    ebitda_field = mapping.get("ebitda_field", "ebitda")

    max_ev_ebitda = _safe_float(fields.get("max_ev_ebitda", 10.0), 10.0)
    top_n = int(fields.get("top_n", 0))

    if not data or not isinstance(data, list):
        return {
            "passed_symbols": [], "failed_symbols": [],
            "symbol_results": [], "values": [],
            "result": False,
            "analysis": {"error": "No data provided", "indicator": "EVEBITDAScreen"},
        }

    # 1단계: 배수 산출 + 결측/경계 분류
    seen_symbols = set()
    valid: List[Dict[str, Any]] = []  # 유효한 양수 배수 종목
    invalid_results: List[Dict[str, Any]] = []  # missing_reason 종목
    invalid_symbols: List[Dict[str, str]] = []
    order: List[str] = []  # 입력 순서 보존
    exchange_of: Dict[str, str] = {}

    for row in data:
        if not isinstance(row, dict):
            continue
        sym = row.get(symbol_field, "")
        if not sym or sym in seen_symbols:
            continue
        seen_symbols.add(sym)
        order.append(sym)

        exchange = row.get(exchange_field, "UNKNOWN")
        exchange_of[sym] = exchange

        multiple = _safe_float(row.get(multiple_field))
        if multiple is None:
            ev = _safe_float(row.get(ev_field))
            ebitda = _safe_float(row.get(ebitda_field))
            if ev is not None and ebitda is not None and ebitda > 0:
                multiple = ev / ebitda

        # EBITDA<=0 → 음수 배수, 또는 배수<=0 → 무의미 → missing_reason
        if multiple is None:
            invalid_results.append({
                "symbol": sym, "exchange": exchange,
                "ev_to_ebitda": None, "rank": None, "passed": False,
                "missing_reason": "ev_ebitda_unavailable",
            })
            invalid_symbols.append({"symbol": sym, "exchange": exchange})
            continue
        if multiple <= 0:
            invalid_results.append({
                "symbol": sym, "exchange": exchange,
                "ev_to_ebitda": round(multiple, 4), "rank": None, "passed": False,
                "missing_reason": "non_positive_ev_ebitda",
            })
            invalid_symbols.append({"symbol": sym, "exchange": exchange})
            continue

        valid.append({"symbol": sym, "exchange": exchange, "ev_to_ebitda": multiple})

    # 2단계: 임계값 필터
    under_threshold = [v for v in valid if v["ev_to_ebitda"] <= max_ev_ebitda]

    # 3단계: 교차종목 랭킹 (최저 배수 = rank 1)
    ranked = sorted(valid, key=lambda v: v["ev_to_ebitda"])
    rank_of = {v["symbol"]: i + 1 for i, v in enumerate(ranked)}

    # 4단계: 선별 집합 결정
    cross_sectional = top_n > 0
    if cross_sectional:
        # 임계값 통과 종목 중 최저 배수 top_n 개
        under_sorted = sorted(under_threshold, key=lambda v: v["ev_to_ebitda"])
        selected = {v["symbol"] for v in under_sorted[:top_n]}
    else:
        selected = {v["symbol"] for v in under_threshold}

    # 5단계: 결과 구성 (입력 순서 보존, invalid 포함)
    passed, failed, symbol_results, values = [], [], [], []
    invalid_by_symbol = {r["symbol"]: r for r in invalid_results}
    valid_by_symbol = {v["symbol"]: v for v in valid}

    for sym in order:
        exchange = exchange_of.get(sym, "UNKNOWN")
        sym_dict = {"symbol": sym, "exchange": exchange}
        values.append({"symbol": sym, "exchange": exchange, "time_series": []})

        if sym in invalid_by_symbol:
            symbol_results.append(invalid_by_symbol[sym])
            failed.append(sym_dict)
            continue

        v = valid_by_symbol[sym]
        is_selected = sym in selected
        symbol_results.append({
            "symbol": sym, "exchange": exchange,
            "ev_to_ebitda": round(v["ev_to_ebitda"], 4),
            "rank": rank_of.get(sym) if cross_sectional else None,
            "passed": is_selected,
        })
        if is_selected:
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
            "indicator": "EVEBITDAScreen",
            "max_ev_ebitda": max_ev_ebitda,
            "top_n": top_n,
            "cross_sectional": cross_sectional,
            "total_symbols": len(order),
            "valid_symbols": len(valid),
            "under_threshold_count": len(under_threshold),
            "selected_count": len(selected),
            "passed_count": len(passed),
        },
    }


__all__ = [
    "ev_ebitda_screen_condition",
    "EV_EBITDA_SCHEMA",
    "_safe_float",
]
