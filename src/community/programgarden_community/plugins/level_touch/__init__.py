"""
Level Touch (레벨 터치/돌파) 플러그인

S/R 레벨에 대한 터치/돌파/역할전환을 판별하고, 이력을 risk_tracker state로 추적합니다.

- SupportResistanceLevels와 연계: 자동 감지된 레벨을 입력으로 받거나 수동 설정 가능
- 3가지 모드: first_touch (첫 터치), role_reversal (역할 전환), cluster_bounce (클러스터 반등)
- risk_tracker state로 레벨별 터치/돌파/전환 이력 누적 관리

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, high, low, close, ...}, ...]
- fields: {levels, touch_tolerance, breakout_threshold, confirm_bars, mode}
"""

import json
from typing import List, Dict, Any, Optional, Set
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


# risk_features 선언 (레벨 터치/돌파 이력 추적)
risk_features: Set[str] = {"state"}

LEVEL_TOUCH_SCHEMA = PluginSchema(
    id="LevelTouch",
    name="Level Touch",
    category=PluginCategory.TECHNICAL,
    version="1.0.0",
    description="Detects touches, breakouts, and role reversals at support/resistance levels. Tracks level interaction history using risk_tracker state. Supports three modes: first_touch (strongest signal on first retouch), role_reversal (signal when broken level acts as opposite), cluster_bounce (bounce at strong clustered zones).",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "levels": {
            "type": "string",
            "default": "[]",
            "title": "Levels",
            "description": "JSON array of {price, type} objects. type: support/resistance. Can be connected from SupportResistanceLevels output.",
        },
        "touch_tolerance": {
            "type": "float",
            "default": 0.01,
            "title": "Touch Tolerance",
            "description": "Price range (as percentage) to detect a level touch",
            "ge": 0.003,
            "le": 0.03,
        },
        "breakout_threshold": {
            "type": "float",
            "default": 0.015,
            "title": "Breakout Threshold",
            "description": "Price range (as percentage) to confirm a level breakout",
            "ge": 0.005,
            "le": 0.05,
        },
        "confirm_bars": {
            "type": "int",
            "default": 2,
            "title": "Confirm Bars",
            "description": "Number of bars price must stay beyond level to confirm breakout",
            "ge": 1,
            "le": 5,
        },
        "mode": {
            "type": "string",
            "default": "first_touch",
            "title": "Mode",
            "description": "first_touch: signal on first retouch, role_reversal: signal when broken level reverses role, cluster_bounce: signal on bounce at strong cluster zones",
            "enum": ["first_touch", "role_reversal", "cluster_bounce"],
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "high", "low", "close"],
    optional_fields=["open", "volume"],
    tags=["support", "resistance", "touch", "breakout", "role_reversal"],
    output_fields={
        "current_price": {"type": "float", "description": "Latest closing price"},
        "mode": {"type": "str", "description": "Active detection mode: 'first_touch', 'role_reversal', or 'cluster_bounce'"},
        "level_events": {"type": "list", "description": "List of level interaction events detected for each configured level"},
        "signal": {"type": "str", "description": "Strongest trading signal generated: 'buy', 'sell', or None"},
    },
    locales={
        "ko": {
            "name": "레벨 터치/돌파",
            "description": "지지/저항 레벨에서의 터치, 돌파, 역할 전환을 감지합니다. risk_tracker를 통해 레벨별 상호작용 이력을 누적 관리합니다. 첫 터치, 역할 전환, 클러스터 반등 3가지 모드를 지원합니다.",
            "fields.levels": "레벨 배열 (JSON: [{price, type}, ...]). SupportResistanceLevels 출력 연결 가능",
            "fields.touch_tolerance": "터치 인식 범위 (퍼센트)",
            "fields.breakout_threshold": "돌파 확인 범위 (퍼센트)",
            "fields.confirm_bars": "돌파 확인 봉 수",
            "fields.mode": "모드 (first_touch: 첫 터치, role_reversal: 역할 전환, cluster_bounce: 클러스터 반등)",
        },
    },
)


def _parse_levels(levels_input: Any) -> List[Dict[str, Any]]:
    """
    levels 입력을 파싱하여 표준 형식으로 변환

    지원 형식:
    - JSON 문자열: '[{"price": 150, "type": "support"}, ...]'
    - dict 리스트: [{"price": 150, "type": "support"}, ...]
    - SupportResistanceLevels symbol_results 연결: [{"clusters": [...], ...}]
    """
    if not levels_input:
        return []

    # 문자열이면 JSON 파싱
    if isinstance(levels_input, str):
        try:
            levels_input = json.loads(levels_input)
        except (json.JSONDecodeError, ValueError):
            return []

    if not isinstance(levels_input, list):
        return []

    parsed = []
    for item in levels_input:
        if not isinstance(item, dict):
            continue

        # SupportResistanceLevels symbol_results 형식: clusters 배열 포함
        if "clusters" in item and isinstance(item["clusters"], list):
            for cluster in item["clusters"]:
                if isinstance(cluster, dict) and "price" in cluster:
                    parsed.append({
                        "price": float(cluster["price"]),
                        "type": cluster.get("type", "support"),
                        "touch_count": cluster.get("touch_count", 1),
                    })
        # 직접 레벨 형식: {price, type}
        elif "price" in item:
            try:
                parsed.append({
                    "price": float(item["price"]),
                    "type": item.get("type", "support"),
                    "touch_count": item.get("touch_count", 1),
                })
            except (ValueError, TypeError):
                continue

    return parsed


def _load_level_state(
    context: Any,
    symbol: str,
    level_price: float,
) -> Dict[str, Any]:
    """risk_tracker에서 레벨 상태 로드"""
    default_state = {
        "touch_count": 0,
        "broken": False,
        "original_type": None,
        "reversed": False,
        "last_touch_date": None,
    }

    has_tracker = context and hasattr(context, "risk_tracker") and context.risk_tracker
    if not has_tracker:
        return default_state

    key = f"sr_level_{symbol}_{round(level_price, 2)}"
    try:
        saved = context.risk_tracker.load_state(key)
        if saved and isinstance(saved, dict):
            return {**default_state, **saved}
    except Exception:
        pass

    return default_state


def _save_level_state(
    context: Any,
    symbol: str,
    level_price: float,
    state: Dict[str, Any],
) -> None:
    """risk_tracker에 레벨 상태 저장"""
    has_tracker = context and hasattr(context, "risk_tracker") and context.risk_tracker
    if not has_tracker:
        return

    key = f"sr_level_{symbol}_{round(level_price, 2)}"
    try:
        context.risk_tracker.save_state(key, state)
    except Exception:
        pass


def detect_touch(
    current_price: float,
    level_price: float,
    tolerance: float = 0.01,
) -> bool:
    """현재가가 레벨 tolerance 내에 있는지 판별"""
    if level_price <= 0:
        return False
    distance = abs(current_price - level_price) / level_price
    return distance <= tolerance


def detect_breakout(
    closes: List[float],
    level_price: float,
    level_type: str,
    threshold: float = 0.015,
    confirm_bars: int = 2,
) -> bool:
    """
    돌파 판별: 종가가 레벨을 관통 + confirm_bars 봉 유지

    - support 돌파: 종가가 레벨 아래로 threshold 이상 돌파
    - resistance 돌파: 종가가 레벨 위로 threshold 이상 돌파
    """
    if len(closes) < confirm_bars or level_price <= 0:
        return False

    recent = closes[-confirm_bars:]

    if level_type == "support":
        # 지지선 하향 돌파: 모든 확인 봉이 레벨 아래 threshold 이상
        return all(
            (level_price - c) / level_price >= threshold
            for c in recent
        )
    elif level_type == "resistance":
        # 저항선 상향 돌파: 모든 확인 봉이 레벨 위 threshold 이상
        return all(
            (c - level_price) / level_price >= threshold
            for c in recent
        )

    return False


def detect_role_reversal(
    current_price: float,
    level_price: float,
    original_type: str,
    tolerance: float = 0.01,
) -> bool:
    """
    역할 전환 판별: 돌파된 레벨이 반대 역할로 작동

    - 저항선 상향 돌파 후 → 가격이 레벨 위에서 레벨로 되돌림 (지지로 전환)
    - 지지선 하향 돌파 후 → 가격이 레벨 아래에서 레벨로 되돌림 (저항으로 전환)
    """
    if level_price <= 0:
        return False

    distance = abs(current_price - level_price) / level_price
    if distance > tolerance:
        return False

    if original_type == "resistance":
        # 저항 돌파 후 지지로 전환: 가격이 레벨 위(또는 근접)
        return current_price >= level_price * (1 - tolerance)
    elif original_type == "support":
        # 지지 돌파 후 저항으로 전환: 가격이 레벨 아래(또는 근접)
        return current_price <= level_price * (1 + tolerance)

    return False


async def level_touch_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
    context: Any = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Level Touch 조건 평가
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

    levels_raw = fields.get("levels", "[]")
    touch_tolerance = fields.get("touch_tolerance", 0.01)
    breakout_threshold = fields.get("breakout_threshold", 0.015)
    confirm_bars = fields.get("confirm_bars", 2)
    mode = fields.get("mode", "first_touch")

    # 레벨 파싱
    parsed_levels = _parse_levels(levels_raw)

    if not data or not isinstance(data, list):
        return {
            "passed_symbols": [],
            "failed_symbols": [],
            "symbol_results": [],
            "values": [],
            "result": False,
            "analysis": {"error": "No data provided"},
        }

    if not parsed_levels:
        return {
            "passed_symbols": [],
            "failed_symbols": [],
            "symbol_results": [],
            "values": [],
            "result": False,
            "analysis": {"error": "No valid levels provided"},
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
                "level_events": [],
                "signal": None,
                "error": "No data",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))

        # 종가 리스트 추출
        closes = []
        for row in rows_sorted:
            try:
                closes.append(float(row.get(close_field, 0)))
            except (ValueError, TypeError):
                closes.append(0)

        if not closes or closes[-1] <= 0:
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol,
                "exchange": exchange,
                "level_events": [],
                "signal": None,
                "error": "Invalid close data",
            })
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        current_price = closes[-1]
        current_date = rows_sorted[-1].get(date_field, "")

        # 각 레벨별 이벤트 평가
        level_events = []
        sym_signal = None

        for level in parsed_levels:
            level_price = level["price"]
            level_type = level["type"]
            cluster_strength = level.get("touch_count", 1)

            if level_price <= 0:
                continue

            # state 로드
            state = _load_level_state(context, symbol, level_price)
            if state["original_type"] is None:
                state["original_type"] = level_type

            # 터치 판별
            is_touching = detect_touch(current_price, level_price, touch_tolerance)

            # 돌파 판별
            is_broken = detect_breakout(
                closes, level_price, level_type, breakout_threshold, confirm_bars
            )

            # 상태 업데이트
            event = {
                "level_price": level_price,
                "level_type": level_type,
                "original_type": state["original_type"],
                "is_touching": is_touching,
                "is_broken": is_broken or state["broken"],
                "touch_count": state["touch_count"],
                "reversed": state["reversed"],
                "signal": None,
            }

            if is_touching:
                state["touch_count"] += 1
                state["last_touch_date"] = current_date

            if is_broken and not state["broken"]:
                state["broken"] = True

            # 역할 전환 감지
            if state["broken"] and is_touching:
                is_reversed = detect_role_reversal(
                    current_price, level_price, state["original_type"], touch_tolerance
                )
                if is_reversed:
                    state["reversed"] = True
                    event["reversed"] = True

            # 모드별 신호 생성
            if mode == "first_touch":
                # 첫 재접촉: 터치 횟수가 1일 때 (state 업데이트 후)
                if is_touching and state["touch_count"] == 1:
                    if level_type == "support":
                        event["signal"] = "buy"
                    elif level_type == "resistance":
                        event["signal"] = "sell"

            elif mode == "role_reversal":
                # 돌파 후 역할 전환 확인
                if state["broken"] and state["reversed"] and is_touching:
                    if state["original_type"] == "resistance":
                        # 저항 돌파 후 지지로 전환 → 매수
                        event["signal"] = "buy"
                    elif state["original_type"] == "support":
                        # 지지 돌파 후 저항으로 전환 → 매도
                        event["signal"] = "sell"

            elif mode == "cluster_bounce":
                # 클러스터(강한 레벨)에서의 반등
                if is_touching and cluster_strength >= 2:
                    if level_type == "support":
                        event["signal"] = "buy"
                    elif level_type == "resistance":
                        event["signal"] = "sell"

            event["touch_count"] = state["touch_count"]

            # state 저장
            _save_level_state(context, symbol, level_price, state)

            level_events.append(event)

            # 가장 강한 신호 선택 (첫 번째 유효 신호)
            if event["signal"] and not sym_signal:
                sym_signal = event["signal"]

        # symbol_results 구성
        symbol_results.append({
            "symbol": symbol,
            "exchange": exchange,
            "current_price": current_price,
            "mode": mode,
            "level_events": level_events,
            "signal": sym_signal,
        })

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
                "signal": None,
                "side": "long",
            }
            # 마지막 봉에 신호 표시
            if i == len(rows_sorted) - 1 and sym_signal:
                entry["signal"] = sym_signal
            time_series.append(entry)

        values.append({
            "symbol": symbol,
            "exchange": exchange,
            "time_series": time_series,
        })

        # 조건 평가
        if sym_signal:
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
            "indicator": "LevelTouch",
            "mode": mode,
            "touch_tolerance": touch_tolerance,
            "breakout_threshold": breakout_threshold,
            "confirm_bars": confirm_bars,
            "level_count": len(parsed_levels),
        },
    }


__all__ = [
    "level_touch_condition",
    "detect_touch",
    "detect_breakout",
    "detect_role_reversal",
    "LEVEL_TOUCH_SCHEMA",
    "risk_features",
]
