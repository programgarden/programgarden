"""
MaxPositionLimit (최대 포지션 한도) 플러그인

보유 종목 수/총금액/개별 비중 vs 한도를 비교합니다.
POSITION Type A (positions 기반, StopLoss 패턴).

입력 형식:
- positions: 보유 포지션 {symbol: {current_price, qty, market_value, ...}}
- fields: {max_positions, max_total_value, max_single_weight_pct, action}
"""

from typing import Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


MAX_POSITION_LIMIT_SCHEMA = PluginSchema(
    id="MaxPositionLimit",
    name="Max Position Limit",
    category=PluginCategory.POSITION,
    version="1.0.0",
    description="Enforces position limits: max number of positions, max total portfolio value, and max single position weight. Triggers warning, blocking, or exit actions when limits are exceeded.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "max_positions": {
            "type": "int",
            "default": 10,
            "title": "Max Positions",
            "description": "Maximum number of positions allowed",
            "ge": 1,
            "le": 100,
        },
        "max_total_value": {
            "type": "float",
            "default": 0,
            "title": "Max Total Value",
            "description": "Maximum total portfolio value (0 = unlimited)",
            "ge": 0,
        },
        "max_single_weight_pct": {
            "type": "float",
            "default": 20.0,
            "title": "Max Single Weight (%)",
            "description": "Maximum single position weight as percentage of total",
            "ge": 1.0,
            "le": 100.0,
        },
        "action": {
            "type": "string",
            "default": "warn",
            "title": "Action",
            "description": "Action when limit exceeded",
            "enum": ["warn", "block_new", "exit_excess"],
        },
    },
    required_data=["positions"],
    required_fields=[],
    optional_fields=[],
    tags=["position", "limit", "risk", "weight", "portfolio"],
    output_fields={
        "current_price": {"type": "float", "description": "Current market price of this position"},
        "market_value": {"type": "float", "description": "Total market value of this position"},
        "weight_pct": {"type": "float", "description": "Position weight as percentage of total portfolio (%)"},
        "is_overweight": {"type": "bool", "description": "Whether this position exceeds the single position weight limit"},
        "action_taken": {"type": "str", "description": "Action taken: 'exit', 'reduce', 'block_new', 'warn', or 'hold'"},
    },
    locales={
        "ko": {
            "name": "최대 포지션 한도",
            "description": "포지션 한도를 관리합니다: 최대 보유 종목 수, 최대 총 포트폴리오 가치, 최대 단일 포지션 비중. 한도 초과 시 경고, 신규 매수 차단, 초과분 청산 등의 조치를 취합니다.",
            "fields.max_positions": "최대 보유 종목 수",
            "fields.max_total_value": "최대 총 포트폴리오 가치 (0 = 무제한)",
            "fields.max_single_weight_pct": "최대 단일 포지션 비중 (%)",
            "fields.action": "조치 (warn: 경고, block_new: 신규 매수 차단, exit_excess: 초과분 청산)",
        },
    },
)


async def max_position_limit_condition(
    positions: Optional[Dict[str, Any]] = None,
    fields: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """최대 포지션 한도 조건 평가"""
    if positions is None:
        positions = {}
    if fields is None:
        fields = {}

    max_positions = fields.get("max_positions", 10)
    max_total_value = fields.get("max_total_value", 0)
    max_single_weight_pct = fields.get("max_single_weight_pct", 20.0)
    action = fields.get("action", "warn")

    if not positions:
        return {
            "passed_symbols": [], "failed_symbols": [],
            "symbol_results": [], "values": [],
            "result": False,
            "analysis": {"error": "No positions data"},
        }

    # 포지션 정보 수집
    position_count = len(positions)
    total_value = 0
    symbol_values: Dict[str, float] = {}

    for symbol, pos_data in positions.items():
        market_value = pos_data.get("market_value", 0)
        if market_value == 0:
            current_price = pos_data.get("current_price", 0)
            qty = pos_data.get("qty", 0)
            market_value = current_price * qty
        symbol_values[symbol] = market_value
        total_value += market_value

    # 위반 확인
    violations = []
    count_exceeded = position_count > max_positions
    value_exceeded = max_total_value > 0 and total_value > max_total_value

    if count_exceeded:
        violations.append(f"Position count {position_count} > max {max_positions}")
    if value_exceeded:
        violations.append(f"Total value {total_value:.0f} > max {max_total_value:.0f}")

    # 개별 비중 초과 체크
    overweight_symbols = []
    if total_value > 0:
        for symbol, value in symbol_values.items():
            weight_pct = value / total_value * 100
            if weight_pct > max_single_weight_pct:
                overweight_symbols.append(symbol)
                violations.append(f"{symbol} weight {weight_pct:.1f}% > max {max_single_weight_pct}%")

    any_violation = len(violations) > 0

    # 결과 구성
    passed, failed, symbol_results = [], [], []

    for symbol, pos_data in positions.items():
        current_price = pos_data.get("current_price", 0)
        exchange = pos_data.get("market_code", "UNKNOWN")
        exchange_map = {"81": "NYSE", "82": "NASDAQ", "83": "AMEX"}
        exchange_name = exchange_map.get(exchange, exchange)
        sym_dict = {"symbol": symbol, "exchange": exchange_name}

        value = symbol_values.get(symbol, 0)
        weight_pct = (value / total_value * 100) if total_value > 0 else 0
        is_overweight = weight_pct > max_single_weight_pct

        action_taken = "hold"
        is_passed = False

        if any_violation:
            if action == "exit_excess":
                if is_overweight or (count_exceeded and symbol in _excess_symbols(positions, max_positions, symbol_values)):
                    action_taken = "exit"
                    is_passed = True
                else:
                    action_taken = "hold"
            elif action == "block_new":
                action_taken = "block_new"
                is_passed = True  # all positions flagged
            else:  # warn
                action_taken = "warn"
                is_passed = True  # flagged

        symbol_results.append({
            "symbol": symbol, "exchange": exchange_name,
            "current_price": current_price,
            "market_value": round(value, 2),
            "weight_pct": round(weight_pct, 2),
            "is_overweight": is_overweight,
            "action_taken": action_taken,
        })

        if is_passed:
            passed.append(sym_dict)
        else:
            failed.append(sym_dict)

    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "symbol_results": symbol_results,
        "values": [],
        "result": any_violation,
        "analysis": {
            "indicator": "MaxPositionLimit",
            "position_count": position_count,
            "max_positions": max_positions,
            "total_value": round(total_value, 2),
            "max_total_value": max_total_value,
            "max_single_weight_pct": max_single_weight_pct,
            "count_exceeded": count_exceeded,
            "value_exceeded": value_exceeded,
            "overweight_count": len(overweight_symbols),
            "violations": violations,
            "action": action,
        },
    }


def _excess_symbols(positions: Dict[str, Any], max_positions: int, symbol_values: Dict[str, float]) -> set:
    """초과 종목 선별 (가치 가장 작은 순)"""
    if len(positions) <= max_positions:
        return set()
    sorted_syms = sorted(symbol_values.keys(), key=lambda s: symbol_values[s])
    excess_count = len(positions) - max_positions
    return set(sorted_syms[:excess_count])


__all__ = ["max_position_limit_condition", "MAX_POSITION_LIMIT_SCHEMA"]
