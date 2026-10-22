"""
ContangoBackwardation (콘탱고/백워데이션) 플러그인 - 선물 전용

선물 월물 간 가격 비교로 선물 기간구조(term structure) 판별.
콘탱고: 원월물 > 근월물 (정상), 백워데이션: 근월물 > 원월물 (역전)

입력 형식:
- data: 플랫 배열 (다른 월물의 시세 데이터 포함)
  [{symbol: "CLF26", close: 70.5, ...}, {symbol: "CLG26", close: 71.2, ...}, ...]
- fields: {structure, spread_threshold}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


CONTANGO_BACKWARDATION_SCHEMA = PluginSchema(
    id="ContangoBackwardation",
    name="Contango/Backwardation Detector",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Detects futures term structure (contango vs backwardation) by comparing front month vs back month prices. Identifies carry trade opportunities and roll timing.",
    products=[ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "structure": {
            "type": "string",
            "default": "any",
            "title": "Target Structure",
            "description": "Which structure to detect",
            "enum": ["contango", "backwardation", "any"],
        },
        "spread_threshold": {
            "type": "float",
            "default": 0.5,
            "title": "Spread Threshold (%)",
            "description": "Minimum spread percentage to trigger signal",
            "ge": 0.0,
            "le": 20.0,
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close"],
    optional_fields=[],
    tags=["futures", "contango", "backwardation", "term_structure", "spread"],
    output_fields={
        "price": {"type": "float", "description": "Latest close price of this contract"},
        "contract_order": {"type": "int", "description": "Contract expiry order (YYYYMM format)"},
        "structure": {"type": "str", "description": "Detected term structure: 'contango' or 'backwardation'"},
        "spread_pct": {"type": "float", "description": "Spread percentage between front and back month contracts"},
        "significant": {"type": "bool", "description": "Whether the spread exceeds the threshold"},
    },
    locales={
        "ko": {
            "name": "콘탱고/백워데이션 탐지",
            "description": "선물 근월물과 원월물의 가격을 비교하여 기간구조(콘탱고/백워데이션)를 판별합니다. 캐리 트레이드 기회와 롤오버 타이밍 판단에 활용됩니다.",
            "fields.structure": "탐지 대상 (contango/backwardation/any)",
            "fields.spread_threshold": "최소 스프레드 비율 (%)",
        },
    },
)

# 선물 월물 코드 매핑 (알파벳 → 월)
MONTH_CODES = {
    "F": 1, "G": 2, "H": 3, "J": 4, "K": 5, "M": 6,
    "N": 7, "Q": 8, "U": 9, "V": 10, "X": 11, "Z": 12,
}


def _parse_contract_order(symbol: str) -> Optional[int]:
    """선물 심볼에서 만기 순서 추출 (예: CLF26 → 202601, HMCEG26 → 202602)"""
    if len(symbol) < 3:
        return None

    # 뒤에서 2자리가 연도, 그 앞 1자리가 월물 코드
    year_part = symbol[-2:]
    month_code = symbol[-3]

    if month_code not in MONTH_CODES:
        return None

    try:
        year = int(year_part) + 2000
        month = MONTH_CODES[month_code]
        return year * 100 + month
    except ValueError:
        return None


async def contango_backwardation_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """콘탱고/백워데이션 조건 평가"""
    mapping = field_mapping or {}
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")

    structure = fields.get("structure", "any")
    spread_threshold = fields.get("spread_threshold", 0.5)

    if not data or not isinstance(data, list):
        return {
            "passed_symbols": [], "failed_symbols": [],
            "symbol_results": [], "values": [],
            "result": False, "analysis": {"error": "No data provided"},
        }

    # 종목별 최근 종가 추출
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

    # 각 종목의 최근 종가와 만기 순서
    contracts = []
    for sym, rows in symbol_data_map.items():
        order = _parse_contract_order(sym)
        if order is None:
            continue

        rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))
        if not rows_sorted:
            continue

        last_row = rows_sorted[-1]
        price = last_row.get(close_field)
        if price is None:
            continue

        try:
            contracts.append({
                "symbol": sym,
                "exchange": symbol_exchange_map.get(sym, "UNKNOWN"),
                "order": order,
                "price": float(price),
                "date": last_row.get(date_field, ""),
            })
        except (ValueError, TypeError):
            continue

    if len(contracts) < 2:
        return {
            "passed_symbols": [], "failed_symbols": [],
            "symbol_results": [],
            "values": [],
            "result": False,
            "analysis": {"error": "Need at least 2 futures contracts for term structure analysis"},
        }

    # 만기 순서대로 정렬
    contracts.sort(key=lambda x: x["order"])

    # 인접 월물 간 스프레드 계산
    passed, failed, symbol_results, values = [], [], [], []
    spreads = []

    front = contracts[0]
    back = contracts[-1]

    spread_pct = (back["price"] - front["price"]) / front["price"] * 100 if front["price"] > 0 else 0
    spread_pct = round(spread_pct, 4)

    detected_structure = "contango" if spread_pct > 0 else "backwardation"
    abs_spread = abs(spread_pct)

    for contract in contracts:
        sym = contract["symbol"]
        exchange = contract["exchange"]
        sym_dict = {"symbol": sym, "exchange": exchange}

        significant = abs_spread >= spread_threshold
        if structure == "any":
            passed_condition = significant
        elif structure == "contango":
            passed_condition = significant and detected_structure == "contango"
        else:
            passed_condition = significant and detected_structure == "backwardation"

        if passed_condition:
            passed.append(sym_dict)
        else:
            failed.append(sym_dict)

        symbol_results.append({
            "symbol": sym, "exchange": exchange,
            "price": contract["price"],
            "contract_order": contract["order"],
            "structure": detected_structure,
            "spread_pct": spread_pct,
            "significant": significant,
        })

        time_series = [{
            date_field: contract["date"],
            close_field: contract["price"],
            "structure": detected_structure,
            "spread_pct": spread_pct,
            "signal": "buy" if passed_condition and detected_structure == "backwardation" else ("sell" if passed_condition and detected_structure == "contango" else None),
            "side": "long",
        }]
        values.append({"symbol": sym, "exchange": exchange, "time_series": time_series})

    # 전체 기간구조 정보
    spreads = []
    for i in range(1, len(contracts)):
        pair_spread = (contracts[i]["price"] - contracts[i - 1]["price"]) / contracts[i - 1]["price"] * 100
        spreads.append({
            "front": contracts[i - 1]["symbol"],
            "back": contracts[i]["symbol"],
            "spread_pct": round(pair_spread, 4),
        })

    return {
        "passed_symbols": passed, "failed_symbols": failed,
        "symbol_results": symbol_results, "values": values,
        "result": len(passed) > 0,
        "term_structure": {
            "structure": detected_structure,
            "front_month": front["symbol"],
            "back_month": back["symbol"],
            "total_spread_pct": spread_pct,
            "spreads": spreads,
        },
        "analysis": {
            "indicator": "ContangoBackwardation",
            "structure": structure,
            "detected": detected_structure,
            "spread_threshold": spread_threshold,
            "spread_pct": spread_pct,
        },
    }


__all__ = ["contango_backwardation_condition", "CONTANGO_BACKWARDATION_SCHEMA"]
