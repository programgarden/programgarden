"""
RelativeStrength (상대 강도) 플러그인

벤치마크 대비 상대 성과를 비교하여 섹터 로테이션/종목 필터링.

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, close, ...}, ...]
  벤치마크 종목 데이터도 함께 포함되어야 함
- fields: {lookback, benchmark_symbol, rank_method, threshold, direction}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


RELATIVE_STRENGTH_SCHEMA = PluginSchema(
    id="RelativeStrength",
    name="Relative Strength",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Compares asset performance against a benchmark over a lookback period. Identifies leaders and laggards for rotation strategies.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "lookback": {
            "type": "int",
            "default": 63,
            "title": "Lookback Period",
            "description": "Period for performance comparison (63 ≈ 3 months)",
            "ge": 5,
            "le": 504,
        },
        "benchmark_symbol": {
            "type": "string",
            "default": "SPY",
            "title": "Benchmark Symbol",
            "description": "Benchmark symbol to compare against",
        },
        "rank_method": {
            "type": "string",
            "default": "percentile",
            "title": "Ranking Method",
            "description": "Method to calculate relative strength score",
            "enum": ["percentile", "z_score", "raw"],
        },
        "threshold": {
            "type": "float",
            "default": 0.0,
            "title": "Threshold",
            "description": "Minimum RS score to pass (raw: 0=same as benchmark, percentile: 50=median)",
        },
        "direction": {
            "type": "string",
            "default": "above",
            "title": "Direction",
            "description": "above: outperformers, below: underperformers",
            "enum": ["above", "below"],
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close"],
    optional_fields=[],
    tags=["relative_strength", "rotation", "benchmark", "ranking"],
    output_fields={
        "rs_score": {"type": "float", "description": "Relative strength score (percentile 0-100, z_score, or raw excess return)"},
        "rs_raw": {"type": "float", "description": "Raw relative return vs benchmark (asset_return - benchmark_return, %)"},
        "asset_return": {"type": "float", "description": "Asset return over lookback period (%)"},
        "benchmark_return": {"type": "float", "description": "Benchmark return over lookback period (%)"},
    },
    locales={
        "ko": {
            "name": "상대 강도 (Relative Strength)",
            "description": "벤치마크(SPY 등) 대비 자산의 상대적 성과를 비교합니다. 섹터 로테이션 전략이나 강세 종목 선별에 활용됩니다.",
            "fields.lookback": "비교 기간 (63 ≈ 3개월)",
            "fields.benchmark_symbol": "벤치마크 종목",
            "fields.rank_method": "순위 산정 방식 (백분위/Z점수/원시값)",
            "fields.threshold": "통과 기준값",
            "fields.direction": "방향 (above: 아웃퍼포머, below: 언더퍼포머)",
        },
    },
)


async def relative_strength_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """상대 강도 조건 평가"""
    mapping = field_mapping or {}
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")

    lookback = fields.get("lookback", 63)
    benchmark_symbol = fields.get("benchmark_symbol", "SPY")
    rank_method = fields.get("rank_method", "percentile")
    threshold = fields.get("threshold", 0.0)
    direction = fields.get("direction", "above")

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
        symbols = [{"symbol": s, "exchange": symbol_exchange_map.get(s, "UNKNOWN")} for s in symbol_data_map if s != benchmark_symbol]

    # 벤치마크 수익률 계산
    benchmark_return = 0.0
    if benchmark_symbol in symbol_data_map:
        bm_sorted = sorted(symbol_data_map[benchmark_symbol], key=lambda x: x.get(date_field, ""))
        bm_prices = [float(r.get(close_field, 0)) for r in bm_sorted if r.get(close_field) is not None]
        if len(bm_prices) > lookback:
            benchmark_return = (bm_prices[-1] - bm_prices[-lookback - 1]) / bm_prices[-lookback - 1] * 100

    # 각 종목 수익률 계산
    passed, failed, symbol_results, values = [], [], [], []
    rs_scores = []

    for sym_info in symbols:
        symbol = sym_info.get("symbol", "") if isinstance(sym_info, dict) else str(sym_info)
        exchange = sym_info.get("exchange", "UNKNOWN") if isinstance(sym_info, dict) else "UNKNOWN"
        sym_dict = {"symbol": symbol, "exchange": exchange}

        if symbol == benchmark_symbol:
            continue

        rows = symbol_data_map.get(symbol, [])
        if not rows:
            failed.append(sym_dict)
            symbol_results.append({"symbol": symbol, "exchange": exchange, "error": "No data"})
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))
        prices = [float(r.get(close_field, 0)) for r in rows_sorted if r.get(close_field) is not None]

        if len(prices) <= lookback:
            failed.append(sym_dict)
            symbol_results.append({"symbol": symbol, "exchange": exchange, "error": "insufficient_data"})
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        asset_return = (prices[-1] - prices[-lookback - 1]) / prices[-lookback - 1] * 100
        rs_raw = asset_return - benchmark_return
        rs_scores.append({"symbol": symbol, "exchange": exchange, "rs_raw": rs_raw, "asset_return": asset_return})

    # percentile/z_score 계산
    if rs_scores:
        raw_values = [s["rs_raw"] for s in rs_scores]
        mean_rs = sum(raw_values) / len(raw_values)
        std_rs = (sum((v - mean_rs) ** 2 for v in raw_values) / len(raw_values)) ** 0.5 if len(raw_values) > 1 else 1.0

        for score_info in rs_scores:
            symbol = score_info["symbol"]
            exchange = score_info["exchange"]
            rs_raw = score_info["rs_raw"]
            asset_return = score_info["asset_return"]
            sym_dict = {"symbol": symbol, "exchange": exchange}

            if rank_method == "percentile":
                below_count = sum(1 for v in raw_values if v <= rs_raw)
                rs_score = round(below_count / len(raw_values) * 100, 2)
            elif rank_method == "z_score":
                rs_score = round((rs_raw - mean_rs) / std_rs, 2) if std_rs > 0 else 0.0
            else:
                rs_score = round(rs_raw, 2)

            if direction == "above":
                passed_condition = rs_score > threshold
            else:
                passed_condition = rs_score < threshold

            if passed_condition:
                passed.append(sym_dict)
            else:
                failed.append(sym_dict)

            symbol_results.append({
                "symbol": symbol, "exchange": exchange,
                "rs_score": rs_score, "rs_raw": round(rs_raw, 2),
                "asset_return": round(asset_return, 2),
                "benchmark_return": round(benchmark_return, 2),
            })

            # time_series
            rows_sorted = sorted(symbol_data_map.get(symbol, []), key=lambda x: x.get(date_field, ""))
            time_series = []
            if rows_sorted:
                last_row = rows_sorted[-1]
                signal = "buy" if passed_condition and direction == "above" else ("sell" if passed_condition and direction == "below" else None)
                time_series.append({
                    date_field: last_row.get(date_field, ""),
                    close_field: last_row.get(close_field),
                    "rs_score": rs_score,
                    "rs_raw": round(rs_raw, 2),
                    "signal": signal,
                    "side": "long",
                })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": time_series})

    # 랭킹
    ranking = sorted(
        [{"symbol": s["symbol"], "rs_score": next((r["rs_score"] for r in symbol_results if r.get("symbol") == s["symbol"]), 0)} for s in rs_scores],
        key=lambda x: x["rs_score"],
        reverse=True,
    )

    return {
        "passed_symbols": passed, "failed_symbols": failed,
        "symbol_results": symbol_results, "values": values,
        "result": len(passed) > 0, "ranking": ranking,
        "analysis": {
            "indicator": "RelativeStrength",
            "lookback": lookback, "benchmark_symbol": benchmark_symbol,
            "rank_method": rank_method, "threshold": threshold, "direction": direction,
            "benchmark_return": round(benchmark_return, 2),
        },
    }


__all__ = ["relative_strength_condition", "RELATIVE_STRENGTH_SCHEMA"]
