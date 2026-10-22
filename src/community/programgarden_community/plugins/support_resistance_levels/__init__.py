"""
Support/Resistance Levels (지지/저항 레벨) 플러그인

OHLCV 히스토리에서 Swing High/Low 기반으로 지지/저항 레벨을 동적으로 감지하고,
비슷한 가격대의 레벨을 클러스터링하여 강도를 평가합니다.

- PivotPoint과 차별: 전일 HLC 공식이 아닌 실제 가격 구조(swing)에서 레벨 감지
- BreakoutRetest와 차별: 단순 고/저점이 아닌 클러스터링 + 강도 평가

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, high, low, close, ...}, ...]
- fields: {lookback, swing_strength, cluster_tolerance, min_cluster_size, proximity_threshold, direction}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


SUPPORT_RESISTANCE_LEVELS_SCHEMA = PluginSchema(
    id="SupportResistanceLevels",
    name="Support/Resistance Levels",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Dynamically detects support and resistance levels from swing highs/lows in price history. Clusters nearby levels into zones and evaluates zone strength by touch count. Generates signals when current price approaches strong S/R zones.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "lookback": {
            "type": "int",
            "default": 60,
            "title": "Lookback Period",
            "description": "Number of bars to analyze for swing point detection",
            "ge": 20,
            "le": 250,
        },
        "swing_strength": {
            "type": "int",
            "default": 5,
            "title": "Swing Strength",
            "description": "Number of bars on each side to confirm a swing high/low",
            "ge": 2,
            "le": 15,
        },
        "cluster_tolerance": {
            "type": "float",
            "default": 0.015,
            "title": "Cluster Tolerance",
            "description": "Price range (as percentage) to group nearby levels into a cluster zone",
            "ge": 0.005,
            "le": 0.05,
        },
        "min_cluster_size": {
            "type": "int",
            "default": 2,
            "title": "Min Cluster Size",
            "description": "Minimum number of levels to form a valid cluster zone",
            "ge": 1,
            "le": 5,
        },
        "proximity_threshold": {
            "type": "float",
            "default": 0.02,
            "title": "Proximity Threshold",
            "description": "How close current price must be to a level (as percentage) to generate a signal",
            "ge": 0.005,
            "le": 0.05,
        },
        "direction": {
            "type": "string",
            "default": "support",
            "title": "Direction",
            "description": "support: signal near support levels, resistance: signal near resistance levels, both: signal near any level",
            "enum": ["support", "resistance", "both"],
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "high", "low", "close"],
    optional_fields=["open", "volume"],
    tags=["support", "resistance", "swing", "cluster", "price_level"],
    output_fields={
        "current_price": {"type": "float", "description": "Latest closing price"},
        "direction": {"type": "str", "description": "Configured direction filter: 'support', 'resistance', or 'both'"},
        "levels": {"type": "list", "description": "Detected swing-based price levels (list of {price, type, date})"},
        "clusters": {"type": "list", "description": "Clustered S/R zones with touch count and price range"},
        "nearest": {"type": "dict", "description": "Nearest S/R level info including price, type, distance, and signal"},
    },
    locales={
        "ko": {
            "name": "지지/저항 레벨",
            "description": "가격 히스토리의 Swing High/Low를 분석하여 지지/저항 레벨을 동적으로 감지합니다. 비슷한 가격대의 레벨을 클러스터로 묶어 강도를 평가하고, 현재가가 강한 레벨에 근접할 때 신호를 생성합니다.",
            "fields.lookback": "스윙 포인트 탐색 기간 (봉 수)",
            "fields.swing_strength": "스윙 확인 범위 (양쪽 N봉)",
            "fields.cluster_tolerance": "클러스터 묶음 범위 (퍼센트)",
            "fields.min_cluster_size": "최소 클러스터 구성 레벨 수",
            "fields.proximity_threshold": "현재가 근접 신호 범위 (퍼센트)",
            "fields.direction": "방향 (support: 지지 레벨, resistance: 저항 레벨, both: 양쪽)",
        },
    },
)


def find_swing_points(
    highs: List[float],
    lows: List[float],
    dates: List[str],
    strength: int = 5,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Swing High/Low 감지

    N봉 전후 비교로 로컬 극점을 추출합니다.
    - swing_high: 양쪽 N봉보다 고가가 높은 봉
    - swing_low: 양쪽 N봉보다 저가가 낮은 봉

    Args:
        highs: 고가 리스트
        lows: 저가 리스트
        dates: 날짜 리스트
        strength: 양쪽 비교 봉 수

    Returns:
        {"swing_highs": [...], "swing_lows": [...]}
    """
    swing_highs = []
    swing_lows = []

    for i in range(strength, len(highs) - strength):
        # Swing High: 현재 고가가 양쪽 N봉의 고가보다 모두 높은지
        is_swing_high = all(
            highs[i] > highs[i - j] and highs[i] > highs[i + j]
            for j in range(1, strength + 1)
        )
        if is_swing_high:
            swing_highs.append({
                "price": highs[i],
                "index": i,
                "date": dates[i] if i < len(dates) else "",
                "type": "resistance",
            })

        # Swing Low: 현재 저가가 양쪽 N봉의 저가보다 모두 낮은지
        is_swing_low = all(
            lows[i] < lows[i - j] and lows[i] < lows[i + j]
            for j in range(1, strength + 1)
        )
        if is_swing_low:
            swing_lows.append({
                "price": lows[i],
                "index": i,
                "date": dates[i] if i < len(dates) else "",
                "type": "support",
            })

    return {"swing_highs": swing_highs, "swing_lows": swing_lows}


def cluster_levels(
    levels: List[Dict[str, Any]],
    tolerance: float = 0.015,
    min_size: int = 2,
) -> List[Dict[str, Any]]:
    """
    비슷한 가격대의 레벨을 클러스터로 묶기

    tolerance 범위 내 레벨들을 하나의 구역(zone)으로 합산합니다.
    - 구역 강도 = 구성 레벨 수 (touch_count)
    - 구역 가격 = 구성 레벨들의 평균

    Args:
        levels: 레벨 리스트 [{price, type, ...}, ...]
        tolerance: 클러스터 묶음 범위 (비율)
        min_size: 최소 클러스터 구성 수

    Returns:
        클러스터 리스트 [{price, type, touch_count, levels, ...}, ...]
    """
    if not levels:
        return []

    # 가격 기준 정렬
    sorted_levels = sorted(levels, key=lambda x: x["price"])
    clusters = []
    used = [False] * len(sorted_levels)

    for i, level in enumerate(sorted_levels):
        if used[i]:
            continue

        # 이 레벨을 중심으로 tolerance 범위 내 레벨 수집
        cluster_members = [level]
        used[i] = True

        for j in range(i + 1, len(sorted_levels)):
            if used[j]:
                continue
            price_diff = abs(sorted_levels[j]["price"] - level["price"])
            if level["price"] > 0 and price_diff / level["price"] <= tolerance:
                cluster_members.append(sorted_levels[j])
                used[j] = True

        # 최소 크기 이상인 클러스터만 유효
        if len(cluster_members) >= min_size:
            avg_price = sum(m["price"] for m in cluster_members) / len(cluster_members)
            # 클러스터 타입: 구성 레벨의 다수결
            type_counts = {}
            for m in cluster_members:
                t = m.get("type", "support")
                type_counts[t] = type_counts.get(t, 0) + 1
            cluster_type = max(type_counts, key=type_counts.get)

            clusters.append({
                "price": round(avg_price, 4),
                "type": cluster_type,
                "touch_count": len(cluster_members),
                "min_price": round(min(m["price"] for m in cluster_members), 4),
                "max_price": round(max(m["price"] for m in cluster_members), 4),
                "levels": cluster_members,
            })
        else:
            # 단일 레벨도 클러스터로 포함 (min_size=1일 때)
            if min_size <= 1:
                clusters.append({
                    "price": round(level["price"], 4),
                    "type": level.get("type", "support"),
                    "touch_count": 1,
                    "min_price": round(level["price"], 4),
                    "max_price": round(level["price"], 4),
                    "levels": cluster_members,
                })

    return sorted(clusters, key=lambda x: x["price"])


def find_nearest_levels(
    current_price: float,
    clusters: List[Dict[str, Any]],
    direction: str = "support",
    threshold: float = 0.02,
) -> Dict[str, Any]:
    """
    현재가에서 가장 가까운 S/R 레벨 찾기

    Args:
        current_price: 현재 가격
        clusters: 클러스터 리스트
        direction: "support", "resistance", "both"
        threshold: 근접 허용 범위 (비율)

    Returns:
        {nearest_support, nearest_resistance, is_near_level, signal, ...}
    """
    if not clusters or current_price <= 0:
        return {
            "nearest_support": None,
            "nearest_resistance": None,
            "is_near_level": False,
            "signal": None,
            "distance_pct": None,
        }

    # 방향별 필터링
    support_levels = [c for c in clusters if c["type"] == "support"]
    resistance_levels = [c for c in clusters if c["type"] == "resistance"]

    # 현재가 아래의 지지 레벨 중 가장 가까운 것
    nearest_support = None
    support_distance = float("inf")
    for level in support_levels:
        if level["price"] <= current_price:
            dist = (current_price - level["price"]) / current_price
            if dist < support_distance:
                support_distance = dist
                nearest_support = level

    # 현재가 위의 저항 레벨 중 가장 가까운 것
    nearest_resistance = None
    resistance_distance = float("inf")
    for level in resistance_levels:
        if level["price"] >= current_price:
            dist = (level["price"] - current_price) / current_price
            if dist < resistance_distance:
                resistance_distance = dist
                nearest_resistance = level

    # 근접 여부 판별 + 신호 생성
    is_near_level = False
    signal = None
    distance_pct = None
    near_level = None

    if direction == "support" or direction == "both":
        if nearest_support and support_distance <= threshold:
            is_near_level = True
            signal = "buy"
            distance_pct = round(support_distance * 100, 2)
            near_level = nearest_support

    if direction == "resistance" or direction == "both":
        if nearest_resistance and resistance_distance <= threshold:
            # both 모드에서 저항이 더 가까우면 저항 우선
            if not is_near_level or resistance_distance < support_distance:
                is_near_level = True
                signal = "sell"
                distance_pct = round(resistance_distance * 100, 2)
                near_level = nearest_resistance

    return {
        "nearest_support": {
            "price": nearest_support["price"],
            "touch_count": nearest_support["touch_count"],
            "distance_pct": round(support_distance * 100, 2),
        } if nearest_support else None,
        "nearest_resistance": {
            "price": nearest_resistance["price"],
            "touch_count": nearest_resistance["touch_count"],
            "distance_pct": round(resistance_distance * 100, 2),
        } if nearest_resistance else None,
        "is_near_level": is_near_level,
        "signal": signal,
        "distance_pct": distance_pct,
        "near_level": {
            "price": near_level["price"],
            "type": near_level["type"],
            "touch_count": near_level["touch_count"],
        } if near_level else None,
    }


async def support_resistance_levels_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Support/Resistance Levels 조건 평가
    """
    mapping = field_mapping or {}
    high_field = mapping.get("high_field", "high")
    low_field = mapping.get("low_field", "low")
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")
    open_field = mapping.get("open_field", "open")
    volume_field = mapping.get("volume_field", "volume")

    lookback = fields.get("lookback", 60)
    swing_strength = fields.get("swing_strength", 5)
    cluster_tolerance = fields.get("cluster_tolerance", 0.015)
    min_cluster_size = fields.get("min_cluster_size", 2)
    proximity_threshold = fields.get("proximity_threshold", 0.02)
    direction = fields.get("direction", "support")

    if not data or not isinstance(data, list):
        return {
            "passed_symbols": [],
            "failed_symbols": [],
            "symbol_results": [],
            "values": [],
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

    # 평가할 종목 결정
    if symbols:
        target_symbols = []
        for s in symbols:
            if isinstance(s, dict):
                target_symbols.append({
                    "symbol": s.get("symbol", ""),
                    "exchange": s.get("exchange", "UNKNOWN"),
                })
            else:
                target_symbols.append({"symbol": str(s), "exchange": "UNKNOWN"})
    else:
        target_symbols = [
            {"symbol": sym, "exchange": symbol_exchange_map.get(sym, "UNKNOWN")}
            for sym in symbol_data_map.keys()
        ]

    passed = []
    failed = []
    symbol_results = []
    values = []

    # swing point 감지에 최소 필요한 봉 수: swing_strength * 2 + 1
    min_required = swing_strength * 2 + 1

    for sym_info in target_symbols:
        symbol = sym_info["symbol"]
        exchange = sym_info["exchange"]
        sym_dict = {"symbol": symbol, "exchange": exchange}

        rows = symbol_data_map.get(symbol, [])

        if not rows:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol,
                "exchange": exchange,
                "levels": [],
                "clusters": [],
                "nearest": None,
                "error": "No data",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))

        # lookback 기간만큼만 사용
        if len(rows_sorted) > lookback:
            rows_sorted = rows_sorted[-lookback:]

        if len(rows_sorted) < min_required:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol,
                "exchange": exchange,
                "levels": [],
                "clusters": [],
                "nearest": None,
                "error": f"Insufficient data: need {min_required}, got {len(rows_sorted)}",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        # 데이터 추출
        highs = []
        lows = []
        closes = []
        dates = []

        for row in rows_sorted:
            try:
                h = float(row.get(high_field, 0))
                l = float(row.get(low_field, 0))
                c = float(row.get(close_field, 0))
                d = row.get(date_field, "")
                highs.append(h)
                lows.append(l)
                closes.append(c)
                dates.append(d)
            except (ValueError, TypeError):
                pass

        if len(highs) < min_required:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol,
                "exchange": exchange,
                "levels": [],
                "clusters": [],
                "nearest": None,
                "error": f"Insufficient valid data: {len(highs)}",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        # 1. Swing Point 감지
        swings = find_swing_points(highs, lows, dates, swing_strength)
        all_levels = swings["swing_highs"] + swings["swing_lows"]

        # 방향 필터링
        if direction == "support":
            filtered_levels = swings["swing_lows"]
        elif direction == "resistance":
            filtered_levels = swings["swing_highs"]
        else:
            filtered_levels = all_levels

        # 2. 클러스터링
        clusters = cluster_levels(filtered_levels, cluster_tolerance, min_cluster_size)

        # both 모드: 전체 레벨로 클러스터링
        all_clusters = cluster_levels(all_levels, cluster_tolerance, min_cluster_size)

        # 3. 현재가 근접 레벨 판별
        current_price = closes[-1] if closes else 0
        nearest_info = find_nearest_levels(
            current_price, all_clusters, direction, proximity_threshold
        )

        # symbol_results 구성
        sym_result = {
            "symbol": symbol,
            "exchange": exchange,
            "current_price": current_price,
            "direction": direction,
            "levels": [
                {"price": lv["price"], "type": lv["type"], "date": lv.get("date", "")}
                for lv in all_levels
            ],
            "clusters": [
                {
                    "price": c["price"],
                    "type": c["type"],
                    "touch_count": c["touch_count"],
                    "min_price": c["min_price"],
                    "max_price": c["max_price"],
                }
                for c in all_clusters
            ],
            "nearest": nearest_info,
        }
        symbol_results.append(sym_result)

        # time_series 생성
        time_series = []
        for i, row in enumerate(rows_sorted):
            entry = {
                date_field: row.get(date_field, ""),
                open_field: row.get(open_field),
                high_field: row.get(high_field),
                low_field: row.get(low_field),
                close_field: row.get(close_field),
                volume_field: row.get(volume_field),
                "is_swing_high": any(
                    sh["index"] == i for sh in swings["swing_highs"]
                ),
                "is_swing_low": any(
                    sl["index"] == i for sl in swings["swing_lows"]
                ),
                "signal": None,
                "side": "long",
            }
            # 마지막 봉에 근접 신호 표시
            if i == len(rows_sorted) - 1 and nearest_info["signal"]:
                entry["signal"] = nearest_info["signal"]
            time_series.append(entry)

        values.append({
            "symbol": symbol,
            "exchange": exchange,
            "time_series": time_series,
        })

        # 조건 평가: 현재가가 방향에 맞는 레벨 근접
        if nearest_info["is_near_level"]:
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
            "indicator": "SupportResistanceLevels",
            "lookback": lookback,
            "swing_strength": swing_strength,
            "cluster_tolerance": cluster_tolerance,
            "min_cluster_size": min_cluster_size,
            "proximity_threshold": proximity_threshold,
            "direction": direction,
        },
    }


__all__ = [
    "support_resistance_levels_condition",
    "find_swing_points",
    "cluster_levels",
    "find_nearest_levels",
    "SUPPORT_RESISTANCE_LEVELS_SCHEMA",
]
