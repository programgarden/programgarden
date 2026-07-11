"""
Piotroski F-Score (피오트로스키 F-스코어) 플러그인

Joseph Piotroski (2000) "Value Investing: The Use of Historical Financial
Statement Information to Separate Winners from Losers".
9개 재무 신호로 기업의 재무 건전성을 0~9점으로 채점 (높을수록 우량).

⚠️ 축소역량 (REDUCED 7/9):
FundamentalDataNode (FMP) 는 cash_flow (data_type) 를 제공하지 않으므로
영업현금흐름(CFO) 의존 2신호(#2 CFO>0, #4 발생액 CFO>ROA)는 채점 불가.
따라서 본 플러그인은 max_score=7 로 축소 채점하고, 생략 신호를
analysis.skipped_signals / analysis.note 로 명시합니다 (숨은 추정 금지).
정식 9/9 는 CFO 데이터가 확보되는 후속에서 활성화됩니다.

입력 형식 (income_statement + balance_sheet 를 symbol/year 로 병합한 플랫 배열):
- data: [{symbol, exchange, calendarYear, netIncome, totalAssets, longTermDebt,
          totalCurrentAssets, totalCurrentLiabilities, weightedAverageShsOut,
          revenue, grossProfit}, ...]  (종목당 최소 2개 연도 필요)
- fields: {min_score}

※ 다중 종목 플러그인 - ConditionNode auto-iterate 는 종목별로 1행만 넘겨
  연도 비교가 불가하므로, 종목 전체를 단일 호출로 넘기거나 NodeRunner 사용.
  (companion: programmer_example/piotroski_income_balance_merge.py)
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


# CFO(영업현금흐름) 의존으로 획득불가한 2신호 (max_score 7/9 축소)
SKIPPED_SIGNALS = ["cfo_positive", "accruals"]
MAX_SCORE = 7

REDUCED_NOTE = (
    "Reduced 7/9 Piotroski F-Score: the 2 operating-cash-flow signals "
    "(cfo_positive, accruals) are skipped because FundamentalDataNode does not "
    "expose operating cash flow. Provide CFO upstream to enable the full 9/9 score."
)


PIOTROSKI_SCHEMA = PluginSchema(
    id="PiotroskiFScore",
    name="Piotroski F-Score",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description=(
        "Fundamental value screener (registered under TECHNICAL until a FUNDAMENTAL "
        "category exists). Piotroski F-Score (2000) scores balance-sheet/income-statement "
        "health across 9 binary signals. This build scores a REDUCED 7/9: the two operating "
        "cash-flow signals (cfo_positive, accruals) are skipped because FundamentalDataNode "
        "provides no cash-flow data. Merge income_statement + balance_sheet by symbol/year and "
        "feed 2+ years per symbol. Multi-symbol plugin."
    ),
    products=[ProductType.OVERSEAS_STOCK],
    fields_schema={
        "min_score": {
            "type": "int",
            "default": 5,
            "title": "Min Score",
            "description": "Minimum F-Score (out of 7) required to pass a symbol",
            "ge": 0,
            "le": 7,
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange"],
    optional_fields=[
        "calendarYear", "netIncome", "totalAssets", "longTermDebt",
        "totalCurrentAssets", "totalCurrentLiabilities", "weightedAverageShsOut",
        "revenue", "grossProfit",
    ],
    tags=["piotroski", "f-score", "value", "fundamental", "quality", "multi-symbol"],
    output_fields={
        "f_score": {"type": "int", "description": "Piotroski F-Score (0-7 in this reduced build)"},
        "max_score": {"type": "int", "description": "Maximum attainable score (7 while CFO signals are skipped)"},
        "signals": {"type": "dict", "description": "Per-signal boolean breakdown of the 7 scored signals"},
        "year": {"type": "str", "description": "Most recent fiscal period used"},
        "prior_year": {"type": "str", "description": "Prior fiscal period used for year-over-year signals"},
    },
    locales={
        "ko": {
            "name": "피오트로스키 F-스코어",
            "description": (
                "펀더멘털 밸류 스크리너 (FUNDAMENTAL 카테고리가 생기기 전까지 TECHNICAL 로 등록). "
                "Piotroski F-Score(2000)로 재무 건전성을 9개 신호로 채점합니다. 본 빌드는 CFO 데이터 "
                "부재로 현금흐름 의존 2신호(cfo_positive, accruals)를 제외한 7/9 축소 점수를 산출합니다. "
                "income_statement+balance_sheet 를 종목/연도로 병합해 종목당 2개 이상 연도를 넣으세요."
            ),
            "fields.min_score": "종목 통과에 필요한 최소 F-Score (7점 만점)",
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
    if f != f or f in (float("inf"), float("-inf")):  # NaN/inf 체크
        return default
    return f


def _pick(row: Dict[str, Any], candidates: List[str]) -> Optional[float]:
    """여러 후보 키 중 첫 번째로 존재하는 숫자 값 반환"""
    for key in candidates:
        if key in row and row[key] is not None:
            v = _safe_float(row[key])
            if v is not None:
                return v
    return None


def _period_key(row: Dict[str, Any], year_field: str) -> str:
    """정렬용 기간 키 (calendarYear 우선, 없으면 date)"""
    y = row.get(year_field)
    if y is not None:
        return str(y)
    return str(row.get("date", ""))


def _ratio(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    """0-safe 나눗셈"""
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def _score_symbol(current: Dict[str, Any], prior: Dict[str, Any]) -> Dict[str, Any]:
    """
    2개 연도(current=최신, prior=직전)로 7신호 채점.

    Returns:
        {"f_score": int, "signals": {...}, "missing_reason": str|None}
    """
    # === 원자료 추출 (여러 FMP 필드명 후보 허용) ===
    net_income_c = _pick(current, ["netIncome", "net_income"])
    total_assets_c = _pick(current, ["totalAssets", "total_assets"])
    total_assets_p = _pick(prior, ["totalAssets", "total_assets"])
    net_income_p = _pick(prior, ["netIncome", "net_income"])

    ltd_c = _pick(current, ["longTermDebt", "long_term_debt"])
    ltd_p = _pick(prior, ["longTermDebt", "long_term_debt"])

    ca_c = _pick(current, ["totalCurrentAssets", "total_current_assets"])
    cl_c = _pick(current, ["totalCurrentLiabilities", "total_current_liabilities"])
    ca_p = _pick(prior, ["totalCurrentAssets", "total_current_assets"])
    cl_p = _pick(prior, ["totalCurrentLiabilities", "total_current_liabilities"])

    shares_c = _pick(current, ["weightedAverageShsOut", "sharesOutstanding", "shares_outstanding"])
    shares_p = _pick(prior, ["weightedAverageShsOut", "sharesOutstanding", "shares_outstanding"])

    revenue_c = _pick(current, ["revenue", "totalRevenue"])
    revenue_p = _pick(prior, ["revenue", "totalRevenue"])
    gp_c = _pick(current, ["grossProfit", "gross_profit"])
    gp_p = _pick(prior, ["grossProfit", "gross_profit"])

    # 핵심 결측(총자산 없이는 대부분 신호 불가) → missing_reason
    if total_assets_c is None or total_assets_p is None:
        return {"f_score": None, "signals": {}, "missing_reason": "missing_total_assets"}

    signals: Dict[str, Optional[bool]] = {}

    # 파생 지표
    roa_c = _ratio(net_income_c, total_assets_c)
    roa_p = _ratio(net_income_p, total_assets_p)
    lev_c = _ratio(ltd_c, total_assets_c)
    lev_p = _ratio(ltd_p, total_assets_p)
    cr_c = _ratio(ca_c, cl_c)
    cr_p = _ratio(ca_p, cl_p)
    gm_c = _ratio(gp_c, revenue_c)
    gm_p = _ratio(gp_p, revenue_p)
    at_c = _ratio(revenue_c, total_assets_c)
    at_p = _ratio(revenue_p, total_assets_p)

    # 신호 채점 (None 은 데이터 결측 → 0점, 별도 결측 신호는 False)
    signals["positive_roa"] = bool(roa_c is not None and roa_c > 0)
    signals["roa_increase"] = bool(roa_c is not None and roa_p is not None and roa_c > roa_p)
    signals["lower_leverage"] = bool(lev_c is not None and lev_p is not None and lev_c < lev_p)
    signals["higher_current_ratio"] = bool(cr_c is not None and cr_p is not None and cr_c > cr_p)
    signals["no_dilution"] = bool(shares_c is not None and shares_p is not None and shares_c <= shares_p)
    signals["higher_gross_margin"] = bool(gm_c is not None and gm_p is not None and gm_c > gm_p)
    signals["higher_asset_turnover"] = bool(at_c is not None and at_p is not None and at_c > at_p)

    f_score = sum(1 for v in signals.values() if v)
    return {"f_score": f_score, "signals": signals, "missing_reason": None}


async def piotroski_f_score_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
    context: Any = None,
    **kwargs,
) -> Dict[str, Any]:
    """피오트로스키 F-스코어 조건 평가 (다중 종목, 종목당 2+ 연도)"""
    mapping = field_mapping or {}
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")
    year_field = mapping.get("year_field", "calendarYear")

    min_score = int(fields.get("min_score", 5))

    if not data or not isinstance(data, list):
        return {
            "passed_symbols": [], "failed_symbols": [],
            "symbol_results": [], "values": [],
            "result": False,
            "analysis": {
                "error": "No data provided",
                "indicator": "PiotroskiFScore",
                "max_score": MAX_SCORE,
                "skipped_signals": list(SKIPPED_SIGNALS),
                "note": REDUCED_NOTE,
            },
        }

    # 종목별 그룹화
    symbol_rows: Dict[str, List[Dict[str, Any]]] = {}
    symbol_exchange: Dict[str, str] = {}
    for row in data:
        if not isinstance(row, dict):
            continue
        sym = row.get(symbol_field, "")
        if not sym:
            continue
        symbol_rows.setdefault(sym, []).append(row)
        if sym not in symbol_exchange:
            symbol_exchange[sym] = row.get(exchange_field, "UNKNOWN")

    if not symbol_rows:
        return {
            "passed_symbols": [], "failed_symbols": [],
            "symbol_results": [], "values": [],
            "result": False,
            "analysis": {
                "error": "No valid symbol data",
                "indicator": "PiotroskiFScore",
                "max_score": MAX_SCORE,
                "skipped_signals": list(SKIPPED_SIGNALS),
                "note": REDUCED_NOTE,
            },
        }

    passed, failed, symbol_results, values = [], [], [], []

    for sym, rows in symbol_rows.items():
        exchange = symbol_exchange.get(sym, "UNKNOWN")
        sym_dict = {"symbol": sym, "exchange": exchange}
        values.append({"symbol": sym, "exchange": exchange, "time_series": []})

        # 연도 내림차순 정렬 (최신 우선)
        rows_sorted = sorted(rows, key=lambda r: _period_key(r, year_field), reverse=True)

        if len(rows_sorted) < 2:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": sym, "exchange": exchange,
                "f_score": None, "max_score": MAX_SCORE,
                "missing_reason": "insufficient_years",
                "detail": "Piotroski F-Score needs at least 2 fiscal years per symbol",
            })
            continue

        current, prior = rows_sorted[0], rows_sorted[1]
        scored = _score_symbol(current, prior)

        if scored["missing_reason"] is not None:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": sym, "exchange": exchange,
                "f_score": None, "max_score": MAX_SCORE,
                "missing_reason": scored["missing_reason"],
                "year": _period_key(current, year_field),
                "prior_year": _period_key(prior, year_field),
            })
            continue

        f_score = scored["f_score"]
        result_entry = {
            "symbol": sym, "exchange": exchange,
            "f_score": f_score,
            "max_score": MAX_SCORE,
            "signals": scored["signals"],
            "year": _period_key(current, year_field),
            "prior_year": _period_key(prior, year_field),
        }
        symbol_results.append(result_entry)

        if f_score >= min_score:
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
            "indicator": "PiotroskiFScore",
            "max_score": MAX_SCORE,
            "skipped_signals": list(SKIPPED_SIGNALS),
            "note": REDUCED_NOTE,
            "min_score": min_score,
            "total_symbols": len(symbol_rows),
            "passed_count": len(passed),
        },
    }


__all__ = [
    "piotroski_f_score_condition",
    "PIOTROSKI_SCHEMA",
    "MAX_SCORE",
    "SKIPPED_SIGNALS",
    "_score_symbol",
    "_safe_float",
]
