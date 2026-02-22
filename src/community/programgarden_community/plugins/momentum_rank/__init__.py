"""
MomentumRank (모멘텀 순위) 플러그인

유니버스 전체 종목의 모멘텀(수익률)을 계산하고 순위를 매겨 상위/하위 N개를 선별합니다.
DualMomentum과 차별: 개별 조건 판단이 아닌 유니버스 전체 순위 기반 필터.

입력 형식:
- data: 플랫 배열 (다종목 데이터 포함)
- fields: {lookback, top_n, top_pct, selection, momentum_type, exclude_recent}

※ 다중 종목 플러그인 - ConditionNode auto-iterate 제약 → NodeRunner 테스트 권장
"""

import math
from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


MOMENTUM_RANK_SCHEMA = PluginSchema(
    id="MomentumRank",
    name="Momentum Rank",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Ranks all symbols by momentum (return) and selects top/bottom N or N%. Supports simple, log, and risk-adjusted momentum types. Optionally excludes recent days to avoid short-term mean reversion.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "lookback": {
            "type": "int",
            "default": 63,
            "title": "Lookback Period",
            "description": "Momentum calculation period (trading days)",
            "ge": 5,
            "le": 504,
        },
        "top_n": {
            "type": "int",
            "default": 5,
            "title": "Top N",
            "description": "Number of top symbols to select (0 to use top_pct instead)",
            "ge": 0,
            "le": 100,
        },
        "top_pct": {
            "type": "float",
            "default": 0,
            "title": "Top Percentile (%)",
            "description": "Top percentile to select (0 to use top_n instead)",
            "ge": 0,
            "le": 100,
        },
        "selection": {
            "type": "string",
            "default": "top",
            "title": "Selection",
            "description": "Select top (highest momentum) or bottom (lowest momentum)",
            "enum": ["top", "bottom"],
        },
        "momentum_type": {
            "type": "string",
            "default": "simple",
            "title": "Momentum Type",
            "description": "Momentum calculation method",
            "enum": ["simple", "log", "risk_adjusted"],
        },
        "exclude_recent": {
            "type": "int",
            "default": 0,
            "title": "Exclude Recent Days",
            "description": "Exclude most recent N days from momentum (avoids short-term mean reversion)",
            "ge": 0,
            "le": 21,
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close"],
    optional_fields=[],
    tags=["momentum", "rank", "screening", "universe", "selection"],
    locales={
        "ko": {
            "name": "모멘텀 순위",
            "description": "유니버스 전체 종목의 모멘텀(수익률)을 계산하고 순위를 매겨 상위/하위 N개 또는 N%를 선별합니다. 단순, 로그, 위험조정 모멘텀 방식을 지원합니다.",
            "fields.lookback": "모멘텀 계산 기간 (거래일)",
            "fields.top_n": "선별할 상위 종목 수 (0이면 top_pct 사용)",
            "fields.top_pct": "선별할 상위 백분위 (0이면 top_n 사용)",
            "fields.selection": "선별 방향 (top: 최상위, bottom: 최하위)",
            "fields.momentum_type": "모멘텀 계산 방식 (simple/log/risk_adjusted)",
            "fields.exclude_recent": "최근 N일 제외 (단기 평균회귀 방지)",
        },
    },
)


def _calculate_momentum(prices: List[float], momentum_type: str = "simple", exclude_recent: int = 0) -> Optional[float]:
    """
    모멘텀 계산

    Args:
        prices: 종가 리스트 (오래된→최신)
        momentum_type: simple/log/risk_adjusted
        exclude_recent: 최근 N일 제외

    Returns:
        모멘텀 값 또는 None
    """
    if exclude_recent > 0 and len(prices) > exclude_recent:
        prices = prices[:-exclude_recent]

    if len(prices) < 2:
        return None

    start_price = prices[0]
    end_price = prices[-1]

    if start_price <= 0:
        return None

    if momentum_type == "simple":
        return (end_price - start_price) / start_price * 100

    elif momentum_type == "log":
        return math.log(end_price / start_price) * 100

    elif momentum_type == "risk_adjusted":
        returns = [(prices[i] - prices[i - 1]) / prices[i - 1] for i in range(1, len(prices)) if prices[i - 1] > 0]
        if not returns:
            return None
        mean_ret = sum(returns) / len(returns)
        if len(returns) < 2:
            return mean_ret * 100
        variance = sum((r - mean_ret) ** 2 for r in returns) / len(returns)
        std = math.sqrt(variance)
        if std == 0:
            return mean_ret * 100
        return (mean_ret / std) * 100  # 샤프 비율 유사

    return None


async def momentum_rank_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """모멘텀 순위 조건 평가"""
    mapping = field_mapping or {}
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")

    lookback = fields.get("lookback", 63)
    top_n = fields.get("top_n", 5)
    top_pct = fields.get("top_pct", 0)
    selection = fields.get("selection", "top")
    momentum_type = fields.get("momentum_type", "simple")
    exclude_recent = fields.get("exclude_recent", 0)

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

    # 각 종목 모멘텀 계산
    momentum_list = []
    for sym, rows in symbol_data_map.items():
        rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))
        closes = []
        for row in rows_sorted:
            try:
                closes.append(float(row.get(close_field, 0)))
            except (ValueError, TypeError):
                pass

        if len(closes) < lookback:
            momentum_list.append({
                "symbol": sym,
                "exchange": symbol_exchange_map.get(sym, "UNKNOWN"),
                "momentum": None,
                "error": f"Insufficient data: need {lookback}, got {len(closes)}",
            })
            continue

        recent_closes = closes[-lookback:]
        momentum = _calculate_momentum(recent_closes, momentum_type, exclude_recent)
        momentum_list.append({
            "symbol": sym,
            "exchange": symbol_exchange_map.get(sym, "UNKNOWN"),
            "momentum": round(momentum, 4) if momentum is not None else None,
            "start_price": recent_closes[0],
            "end_price": recent_closes[-1] if exclude_recent == 0 else recent_closes[-(exclude_recent + 1)],
            "current_price": closes[-1],
        })

    # 유효한 모멘텀만 추출 후 순위 매기기
    valid = [m for m in momentum_list if m["momentum"] is not None]
    reverse = selection == "top"
    valid.sort(key=lambda x: x["momentum"], reverse=reverse)

    # 순위 부여
    for i, item in enumerate(valid):
        item["rank"] = i + 1

    # 선별: top_pct 우선, 아니면 top_n
    if top_pct > 0:
        n_select = max(1, int(len(valid) * top_pct / 100))
    else:
        n_select = min(top_n, len(valid)) if top_n > 0 else len(valid)

    selected = set(v["symbol"] for v in valid[:n_select])

    passed, failed, symbol_results, values = [], [], [], []
    for item in momentum_list:
        sym = item["symbol"]
        exchange = item["exchange"]
        sym_dict = {"symbol": sym, "exchange": exchange}

        symbol_results.append(item)
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
            "indicator": "MomentumRank",
            "lookback": lookback,
            "top_n": top_n,
            "top_pct": top_pct,
            "selection": selection,
            "momentum_type": momentum_type,
            "exclude_recent": exclude_recent,
            "total_symbols": len(momentum_list),
            "valid_symbols": len(valid),
            "selected_count": len(passed),
        },
    }


__all__ = ["momentum_rank_condition", "MOMENTUM_RANK_SCHEMA"]
