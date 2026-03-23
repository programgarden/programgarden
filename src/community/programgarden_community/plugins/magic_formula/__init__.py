"""
Magic Formula (마법공식) 플러그인

Joel Greenblatt (2005) "The Little Book That Beats the Market".
자본수익률(ROC) 순위 + 이익수익률(EY) 순위 합산으로 "싸고 좋은 기업" 선별.

Simplified 모드: ROE 순위 + 1/PER 순위 합산 (FundamentalDataNode 데이터 활용)
Full 모드: EBIT/IC 순위 + EBIT/EV 순위 합산 (외부 재무데이터 필요)

※ 다중 종목 플러그인 - ConditionNode auto-iterate 제약 → NodeRunner 테스트 권장

입력 형식:
- data: 플랫 배열 (재무 데이터) [{symbol, exchange, per, roe, ...}, ...] (simplified)
        또는 [{symbol, exchange, ebit, enterprise_value, invested_capital, ...}, ...] (full)
- fields: {mode, top_n, top_pct, min_market_cap, exclude_financials, exclude_utilities}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


MAGIC_FORMULA_SCHEMA = PluginSchema(
    id="MagicFormula",
    name="Magic Formula",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Joel Greenblatt's Magic Formula (2005). Ranks stocks by combined ROC (quality) + EY (cheapness). Simplified mode uses ROE + 1/PER (available from FundamentalDataNode). Full mode uses EBIT/IC + EBIT/EV for precise calculation. Multi-symbol plugin.",
    products=[ProductType.OVERSEAS_STOCK],
    fields_schema={
        "mode": {
            "type": "string",
            "default": "simplified",
            "title": "Mode",
            "description": "simplified: ROE + 1/PER ranking (FundamentalDataNode compatible). full: EBIT/IC + EBIT/EV ranking",
            "enum": ["simplified", "full"],
        },
        "top_n": {
            "type": "int",
            "default": 30,
            "title": "Top N",
            "description": "Number of top-ranked stocks to select (0 to use top_pct instead)",
            "ge": 1,
            "le": 100,
        },
        "top_pct": {
            "type": "float",
            "default": 0.0,
            "title": "Top Percentile (%)",
            "description": "Top percentile to select (0 to use top_n instead)",
            "ge": 0.0,
            "le": 50.0,
        },
        "min_market_cap": {
            "type": "float",
            "default": 0.0,
            "title": "Min Market Cap",
            "description": "Minimum market cap filter in USD (0 = no filter). e.g., 1e9 for $1B+",
            "ge": 0.0,
        },
        "exclude_financials": {
            "type": "bool",
            "default": True,
            "title": "Exclude Financials",
            "description": "Exclude financial sector stocks (banks, insurance, etc.) per original Greenblatt rule",
        },
        "exclude_utilities": {
            "type": "bool",
            "default": True,
            "title": "Exclude Utilities",
            "description": "Exclude utility sector stocks per original Greenblatt rule",
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange"],
    optional_fields=["per", "roe", "ebit", "enterprise_value", "invested_capital", "market_cap", "sector"],
    tags=["magic-formula", "greenblatt", "value", "fundamental", "ranking", "multi-symbol"],
    output_fields={
        "roc_rank": {"type": "int", "description": "Rank by Return on Capital (lower = better quality)"},
        "ey_rank": {"type": "int", "description": "Rank by Earnings Yield (lower = cheaper valuation)"},
        "combined_rank": {"type": "int", "description": "Combined Magic Formula rank (roc_rank + ey_rank, lower = better)"},
        "roc_value": {"type": "float", "description": "Actual Return on Capital value (EBIT/IC or ROE)"},
        "ey_value": {"type": "float", "description": "Actual Earnings Yield value (EBIT/EV or 1/PER)"},
    },
    locales={
        "ko": {
            "name": "마법공식",
            "description": "Joel Greenblatt의 마법공식 (2005). 자본수익률(ROC) 순위 + 이익수익률(EY) 순위 합산으로 '싸고 좋은 기업'을 선별합니다. Simplified: ROE + 1/PER, Full: EBIT/IC + EBIT/EV",
            "fields.mode": "모드 (simplified: ROE+PER, full: EBIT/EV+EBIT/IC)",
            "fields.top_n": "선별할 상위 종목 수 (0이면 top_pct 사용)",
            "fields.top_pct": "선별할 상위 백분위 (0이면 top_n 사용)",
            "fields.min_market_cap": "최소 시가총액 필터 (USD, 0=필터 없음)",
            "fields.exclude_financials": "금융업 제외 (원본 규칙)",
            "fields.exclude_utilities": "유틸리티 제외 (원본 규칙)",
        },
    },
)

# 제외 섹터 키워드
FINANCIAL_KEYWORDS = {"financial", "bank", "insurance", "investment", "asset management", "credit", "mortgage"}
UTILITY_KEYWORDS = {"utility", "utilities", "electric", "water", "gas", "power"}


def _is_financial(sector: str) -> bool:
    """금융업 여부"""
    if not sector:
        return False
    sector_lower = sector.lower()
    return any(kw in sector_lower for kw in FINANCIAL_KEYWORDS)


def _is_utility(sector: str) -> bool:
    """유틸리티 여부"""
    if not sector:
        return False
    sector_lower = sector.lower()
    return any(kw in sector_lower for kw in UTILITY_KEYWORDS)


def _safe_float(value: Any, default: float = None) -> Optional[float]:
    """안전한 float 변환"""
    if value is None:
        return default
    try:
        f = float(value)
        return f if not (f != f) else default  # NaN 체크
    except (ValueError, TypeError):
        return default


def _rank_list(values: List[tuple], reverse: bool = True) -> Dict[str, int]:
    """(symbol, value) 리스트를 순위 딕셔너리로 변환 (낮은 순위 = 좋음)"""
    sorted_vals = sorted(values, key=lambda x: x[1], reverse=reverse)
    ranks = {}
    for i, (sym, _) in enumerate(sorted_vals):
        ranks[sym] = i + 1
    return ranks


async def magic_formula_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """마법공식 조건 평가 (다중 종목)"""
    mapping = field_mapping or {}
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")

    mode = fields.get("mode", "simplified")
    top_n = fields.get("top_n", 30)
    top_pct = fields.get("top_pct", 0.0)
    min_market_cap = fields.get("min_market_cap", 0.0)
    exclude_financials = fields.get("exclude_financials", True)
    exclude_utilities = fields.get("exclude_utilities", True)

    if not data or not isinstance(data, list):
        return {
            "passed_symbols": [], "failed_symbols": [],
            "symbol_results": [], "values": [],
            "result": False,
            "analysis": {"error": "No data provided"},
        }

    # 종목별 최신 데이터 추출 (fundamental data - 각 종목 1개 row)
    symbol_data_map: Dict[str, Dict] = {}
    symbol_exchange_map: Dict[str, str] = {}

    for row in data:
        if not isinstance(row, dict):
            continue
        sym = row.get(symbol_field, "")
        if not sym:
            continue
        # 여러 행이 있으면 마지막 행 사용
        symbol_data_map[sym] = row
        symbol_exchange_map[sym] = row.get(exchange_field, "UNKNOWN")

    if not symbol_data_map:
        return {
            "passed_symbols": [], "failed_symbols": [],
            "symbol_results": [], "values": [],
            "result": False,
            "analysis": {"error": "No valid symbol data"},
        }

    # ROC와 EY 계산
    roc_values = []  # (symbol, roc_value)
    ey_values = []   # (symbol, ey_value)
    symbol_info: Dict[str, Dict] = {}

    for sym, row in symbol_data_map.items():
        exchange = symbol_exchange_map.get(sym, "UNKNOWN")
        sector = row.get("sector", "")
        market_cap = _safe_float(row.get("market_cap"), 0.0)

        # 필터 적용
        if min_market_cap > 0 and market_cap is not None and market_cap < min_market_cap:
            symbol_info[sym] = {
                "symbol": sym, "exchange": exchange,
                "filtered": True, "filter_reason": "below_min_market_cap",
            }
            continue

        if exclude_financials and _is_financial(sector):
            symbol_info[sym] = {
                "symbol": sym, "exchange": exchange,
                "filtered": True, "filter_reason": "financial_sector",
            }
            continue

        if exclude_utilities and _is_utility(sector):
            symbol_info[sym] = {
                "symbol": sym, "exchange": exchange,
                "filtered": True, "filter_reason": "utility_sector",
            }
            continue

        if mode == "simplified":
            # Simplified: ROC = ROE, EY = 1/PER
            roe = _safe_float(row.get("roe"))
            per = _safe_float(row.get("per"))

            roc_val = roe  # ROE as proxy for ROC
            ey_val = (1.0 / per) if (per and per > 0) else None  # 1/PER as EY

            if roc_val is None or ey_val is None:
                symbol_info[sym] = {
                    "symbol": sym, "exchange": exchange,
                    "filtered": False, "missing_data": True,
                    "roc_value": roc_val, "ey_value": ey_val,
                }
                continue

        else:  # full mode
            # Full: ROC = EBIT / Invested Capital, EY = EBIT / EV
            ebit = _safe_float(row.get("ebit"))
            ev = _safe_float(row.get("enterprise_value"))
            ic = _safe_float(row.get("invested_capital"))

            if ebit is None:
                symbol_info[sym] = {
                    "symbol": sym, "exchange": exchange,
                    "filtered": False, "missing_data": True,
                }
                continue

            roc_val = (ebit / ic) if (ic and ic > 0) else None
            ey_val = (ebit / ev) if (ev and ev > 0) else None

            if roc_val is None or ey_val is None:
                symbol_info[sym] = {
                    "symbol": sym, "exchange": exchange,
                    "filtered": False, "missing_data": True,
                    "roc_value": roc_val, "ey_value": ey_val,
                }
                continue

        roc_values.append((sym, roc_val))
        ey_values.append((sym, ey_val))
        symbol_info[sym] = {
            "symbol": sym, "exchange": exchange,
            "filtered": False, "missing_data": False,
            "roc_value": round(roc_val, 6),
            "ey_value": round(ey_val, 6),
            "sector": sector,
            "market_cap": market_cap,
        }

    # 순위 계산 (높은 값 = 낮은 순위 번호 = 좋음)
    roc_ranks = _rank_list(roc_values, reverse=True)
    ey_ranks = _rank_list(ey_values, reverse=True)

    # 합산 순위 계산
    valid_symbols = [sym for sym, _ in roc_values]
    combined_list = []
    for sym in valid_symbols:
        roc_r = roc_ranks.get(sym, 9999)
        ey_r = ey_ranks.get(sym, 9999)
        combined = roc_r + ey_r
        combined_list.append((sym, combined, roc_r, ey_r))
        symbol_info[sym]["roc_rank"] = roc_r
        symbol_info[sym]["ey_rank"] = ey_r
        symbol_info[sym]["combined_rank"] = combined

    # 합산 순위로 정렬 (낮을수록 좋음)
    combined_list.sort(key=lambda x: x[1])

    # 상위 N% 또는 top_n 선별
    if top_pct > 0:
        n_select = max(1, int(len(combined_list) * top_pct / 100))
    else:
        n_select = min(top_n, len(combined_list)) if top_n > 0 else len(combined_list)

    selected = {sym for sym, _, _, _ in combined_list[:n_select]}

    # 결과 구성
    passed, failed, symbol_results, values = [], [], [], []

    for sym, row_data in symbol_data_map.items():
        exchange = symbol_exchange_map.get(sym, "UNKNOWN")
        sym_dict = {"symbol": sym, "exchange": exchange}
        info = symbol_info.get(sym, {})

        result_entry = {
            "symbol": sym,
            "exchange": exchange,
            "roc_rank": info.get("roc_rank"),
            "ey_rank": info.get("ey_rank"),
            "combined_rank": info.get("combined_rank"),
            "roc_value": info.get("roc_value"),
            "ey_value": info.get("ey_value"),
        }

        if info.get("filtered"):
            result_entry["filter_reason"] = info.get("filter_reason")
        if info.get("missing_data"):
            result_entry["missing_data"] = True

        symbol_results.append(result_entry)
        values.append({"symbol": sym, "exchange": exchange, "time_series": []})

        if sym in selected:
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
            "indicator": "MagicFormula",
            "mode": mode,
            "top_n": top_n,
            "top_pct": top_pct,
            "total_symbols": len(symbol_data_map),
            "valid_symbols": len(valid_symbols),
            "selected_count": len(selected),
            "exclude_financials": exclude_financials,
            "exclude_utilities": exclude_utilities,
        },
    }


__all__ = ["magic_formula_condition", "_is_financial", "_is_utility", "_rank_list", "MAGIC_FORMULA_SCHEMA"]
