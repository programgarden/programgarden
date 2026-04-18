"""
Dynamic Plugin: ScalableTrailingStop

연속형(continuous) 트레일링 스탑. HWM 수익률에 따라 0.1% 단위로 trail 거리가 매끄럽게 변한다.

공식:
    hwm_ratio = (hwm_price - entry) / entry * 100         # HWM 수익률 (%)
    current_ratio = (current_price - entry) / entry * 100  # 현재 수익률 (%)

    if hwm_ratio <= 0:
        stop_ratio = -initial_stop_pct        # 초기 고정 손절 (기본 -5%)
    else:
        trail_distance = max(min_trail_pct, hwm_ratio * trail_factor)
        stop_ratio = hwm_ratio - trail_distance

    signal = "sell" if current_ratio <= stop_ratio else "hold"

기본값:
    initial_stop_pct = 5.0      (초기 손절 5%)
    min_trail_pct    = 4.0      (최소 trail 거리 4%)
    trail_factor     = 0.35     (HWM * 0.35)

검증 (초기 5%, min 4%, factor 0.35):
    HWM   0% → stop -5.0%
    HWM   5% → stop  1.0% (4% trail)
    HWM  10% → stop  6.0% (4% trail)
    HWM  15% → stop  9.75% (5.25% trail)
    HWM  20% → stop 13.0% (7% trail)
    HWM  30% → stop 19.5% (10.5% trail)

risk_features = {"hwm"} 선언으로 WorkflowRiskTracker가 자동 활성화되며
context.risk_tracker.get_hwm(symbol)으로 HWM/현재가를 조회한다.

POSITION 카테고리 — positions 배열(list[dict])을 입력으로 받으며
positions에 `high_pnl_rate` 필드가 없는 실제 계좌 데이터에서도 작동한다.

시장 시간 판단은 MarketStatusNode(JIF) 로 이관되어 본 플러그인에서 분리됨.
"""

from typing import Any, Dict, List, Optional, Set

from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


risk_features: Set[str] = {"hwm"}


SCHEMA = PluginSchema(
    id="Dynamic_ScalableTrailingStop",
    name="Scalable Trailing Stop",
    category=PluginCategory.POSITION,
    version="1.0.0",
    description=(
        "연속형 트레일링 스탑. HWM 수익률이 커질수록 trail 거리가 0.1% 단위로 "
        "매끄럽게 확장되어 수익 구간별로 스케일러블하게 손절/익절 라인을 잡는다."
    ),
    products=[ProductType.OVERSEAS_STOCK],
    fields_schema={
        "initial_stop_pct": {
            "type": "float",
            "default": 5.0,
            "title": "Initial Stop (%)",
            "description": "HWM 수익률이 0 이하일 때 적용되는 초기 고정 손절폭 (%)",
        },
        "min_trail_pct": {
            "type": "float",
            "default": 4.0,
            "title": "Min Trail (%)",
            "description": "HWM 수익 발생 후 trail의 최소 거리 (%)",
        },
        "trail_factor": {
            "type": "float",
            "default": 0.35,
            "title": "Trail Factor",
            "description": "trail 거리 = max(min_trail, HWM% * trail_factor)",
        },
    },
    required_data=["positions"],
    required_fields=[],
    tags=["exit", "trailing", "risk", "continuous"],
    output_fields={
        "signal": {"type": "str", "description": "'sell' or 'hold'"},
        "quantity": {"type": "float", "description": "Position quantity (held shares)"},
        "hwm_ratio": {"type": "float", "description": "HWM profit ratio (%)"},
        "current_ratio": {"type": "float", "description": "Current profit ratio (%)"},
        "stop_ratio": {"type": "float", "description": "Stop threshold ratio (%)"},
        "trail_distance": {"type": "float", "description": "Distance from HWM to stop (%)"},
    },
    locales={
        "ko": {
            "name": "스케일러블 트레일링 스탑",
            "description": "HWM 수익률에 따라 trail 거리가 연속적으로 변하는 동적 트레일링 스탑.",
            "fields.initial_stop_pct": "초기 고정 손절 (%)",
            "fields.min_trail_pct": "최소 trail 거리 (%)",
            "fields.trail_factor": "HWM 대비 trail 스케일 비율",
        },
    },
)


def _compute_stop_ratio(
    hwm_ratio: float,
    initial_stop_pct: float,
    min_trail_pct: float,
    trail_factor: float,
) -> tuple[float, float]:
    """stop_ratio(진입가 대비 %), trail_distance(HWM 대비 %) 계산."""
    if hwm_ratio <= 0:
        return -abs(initial_stop_pct), 0.0
    trail_distance = max(min_trail_pct, hwm_ratio * trail_factor)
    return hwm_ratio - trail_distance, trail_distance


async def scalable_trailing_stop_condition(
    positions: Optional[List[Dict[str, Any]]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
    fields: Optional[Dict[str, Any]] = None,
    context: Any = None,
    **kwargs,
) -> dict:
    fields = fields or {}
    initial_stop = float(fields.get("initial_stop_pct", 5.0))
    min_trail = float(fields.get("min_trail_pct", 4.0))
    trail_factor = float(fields.get("trail_factor", 0.35))

    positions = positions or []

    # symbols 바인딩만 있고 positions가 없으면 risk_tracker로 대체
    tracker = getattr(context, "risk_tracker", None) if context else None

    passed: List[Dict[str, str]] = []
    failed: List[Dict[str, str]] = []
    results: List[Dict[str, Any]] = []

    # positions 기반 iteration (우선순위 1)
    items = positions
    if not items and symbols:
        items = [{"symbol": s.get("symbol"), "exchange": s.get("exchange", "")} for s in symbols]

    if not items:
        return {
            "passed_symbols": [],
            "failed_symbols": [],
            "symbol_results": [],
            "values": [],
            "result": False,
            "error": "positions/symbols 데이터가 없습니다.",
        }

    for pos in items:
        symbol = pos.get("symbol")
        if not symbol:
            continue
        exchange = pos.get("exchange", "") or ""

        entry = float(pos.get("avg_price") or 0)
        current = float(pos.get("current_price") or 0)
        quantity = pos.get("quantity", 0)

        # HWM은 tracker에서 (시세 tick마다 자동 업데이트됨)
        hwm_price = 0.0
        if tracker:
            hwm_state = tracker.get_hwm(symbol)
            if hwm_state:
                if entry <= 0:
                    entry = float(getattr(hwm_state, "position_avg_price", 0) or 0)
                if current <= 0:
                    current = float(getattr(hwm_state, "current_price", 0) or 0)
                hwm_price = float(getattr(hwm_state, "hwm_price", 0) or 0)

        if entry <= 0 or current <= 0:
            failed.append({"symbol": symbol, "exchange": exchange})
            results.append({
                "symbol": symbol, "exchange": exchange,
                "signal": "hold", "reason": "가격 데이터 부족",
            })
            continue

        # HWM이 없으면 현재가/진입가 중 큰 값으로 대체 (보수적)
        if hwm_price <= 0:
            hwm_price = max(current, entry)

        hwm_ratio = (hwm_price - entry) / entry * 100.0
        current_ratio = (current - entry) / entry * 100.0

        stop_ratio, trail_distance = _compute_stop_ratio(
            hwm_ratio, initial_stop, min_trail, trail_factor,
        )

        triggered = current_ratio <= stop_ratio

        entry_dict = {
            "symbol": symbol,
            "exchange": exchange,
            "quantity": quantity,
            "hwm_ratio": round(hwm_ratio, 2),
            "current_ratio": round(current_ratio, 2),
            "stop_ratio": round(stop_ratio, 2),
            "trail_distance": round(trail_distance, 2),
            "hwm_price": round(hwm_price, 4),
            "entry_price": round(entry, 4),
            "current_price": round(current, 4),
            "signal": "sell" if triggered else "hold",
            "triggered": triggered,
        }
        results.append(entry_dict)
        if triggered:
            passed.append({"symbol": symbol, "exchange": exchange, "quantity": quantity})
        else:
            failed.append({"symbol": symbol, "exchange": exchange})

    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "symbol_results": results,
        "values": [],
        "result": len(passed) > 0,
        "analysis": {
            "indicator": "ScalableTrailingStop",
            "initial_stop_pct": initial_stop,
            "min_trail_pct": min_trail,
            "trail_factor": trail_factor,
            "total": len(items),
            "triggered": len(passed),
        },
    }


__all__ = ["scalable_trailing_stop_condition", "SCHEMA", "risk_features"]
