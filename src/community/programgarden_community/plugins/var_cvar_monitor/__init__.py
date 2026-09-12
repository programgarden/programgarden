"""
VarCvarMonitor (VaR/CVaR 모니터) 플러그인

Value at Risk(VaR)와 Conditional VaR(CVaR, Expected Shortfall) 계산.
한도 초과 시 위험 이벤트 기록 및 포지션 축소 추천.

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, close, ...}, ...]
- positions (선택): 보유 포지션 (list[dict]) — 달러 VaR 계산용
  예: [{"symbol": "AAPL", "current_price": 150.0, "qty": 100, ...}, ...]
- fields: {lookback, confidence_level, var_method, time_horizon, alert_threshold_pct, action}

미검증 경로 주의 — ``positions`` 인자
------------------------------------
이 플러그인은 ``required_data=["data"]`` 라 실행기에서 **data 기반 분기**로 돈다.
그 분기(``ConditionNodeExecutor._execute_condition_plugin``, programgarden/executor.py)
가 만드는 plugin_kwargs 는 ``{data, fields, field_mapping, symbols}`` 이고
(시그니처에 ``context`` 가 있으면 context 추가, 그리고 인자로 들어온 경우에만
``held_symbols``/``position_data``), **``positions`` 키는 없다** — 유일한 호출부
(같은 파일 ``ConditionNodeExecutor.execute``)도 ``held_symbols``/``position_data``
를 넘기지 않는다. 따라서 워크플로우 실행 경로에서 ``positions`` 는 항상 ``None``
이고, ``var_dollar``/``position_value``/``reduce_position`` 의 ``sell_quantity``
는 그 경로에서 **산출되지 않는다**(관측: 위 두 심볼의 코드 읽기, 2026-09-12).
아래 positions 분기는 라이브러리를 직접 호출하는 코드와 테스트에서만 돈다 —
즉 실행기 경로에 대해서는 미검증이다. (실행기가 positions 를 넘기게 하는 수정은
이 플러그인의 범위 밖이다.)
"""

from typing import List, Dict, Any, Optional, Set
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType

from .._position_qty import below_broker_lot, coerce_qty, half_position_qty


# risk_features 선언
risk_features: Set[str] = {"events"}

VAR_CVAR_MONITOR_SCHEMA = PluginSchema(
    id="VarCvarMonitor",
    name="VaR/CVaR Monitor",
    category=PluginCategory.POSITION,
    version="1.0.0",
    description="Calculates Value at Risk (VaR) and Conditional VaR (CVaR/Expected Shortfall). Monitors portfolio risk and triggers alerts when thresholds are breached.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "lookback": {
            "type": "int",
            "default": 60,
            "title": "Lookback Period",
            "description": "Number of periods for VaR calculation",
            "ge": 20,
            "le": 500,
        },
        "confidence_level": {
            "type": "float",
            "default": 95.0,
            "title": "Confidence Level (%)",
            "description": "VaR confidence level",
            "enum": [90.0, 95.0, 99.0],
        },
        "var_method": {
            "type": "string",
            "default": "historical",
            "title": "VaR Method",
            "description": "VaR calculation method",
            "enum": ["historical", "parametric"],
        },
        "time_horizon": {
            "type": "int",
            "default": 1,
            "title": "Time Horizon (days)",
            "description": "VaR time horizon in trading days",
            "ge": 1,
            "le": 10,
        },
        "alert_threshold_pct": {
            "type": "float",
            "default": 5.0,
            "title": "Alert Threshold (%)",
            "description": "VaR threshold to trigger alert",
            "ge": 1.0,
            "le": 30.0,
        },
        "action": {
            "type": "string",
            "default": "alert_only",
            "title": "Action",
            "description": "Action when VaR exceeds threshold",
            "enum": ["alert_only", "reduce_position", "exit_all"],
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close"],
    optional_fields=[],
    tags=["var", "cvar", "risk", "monitoring", "expected_shortfall"],
    output_fields={
        "var_pct": {"type": "float", "description": "Value at Risk over the configured time horizon (%)"},
        "cvar_pct": {"type": "float", "description": "Conditional VaR (Expected Shortfall) over the time horizon (%)"},
        "breached": {"type": "bool", "description": "Whether VaR exceeds the alert threshold"},
        "var_dollar": {"type": "float", "description": "Dollar VaR of the position (available when positions are provided; fractional share counts are kept, not truncated)"},
        "position_value": {"type": "float", "description": "Total position market value (available when positions are provided; fractional share counts are kept, not truncated)"},
        "position_value_unavailable_reason": {"type": "str", "description": "Present instead of var_dollar/position_value when the held quantity or current price could not be read"},
        "sell_quantity": {"type": "float", "description": "Quantity to sell - a number ONLY on the 'reduce_position' action: exactly half of the held quantity, never rounded up and never above the held quantity (fractional halves are kept; the order node truncates to the broker lot and reports the remainder). NOT always a number: on the 'exit_all' action this key carries the literal string \"all\" instead, meaning the whole position (that string is emitted on passed_symbols for the downstream order node to bind, never in symbol_results). Consumers must accept both shapes"},
        "sell_quantity_unavailable_reason": {"type": "str", "description": "Present only when an action needing a quantity triggered but the held quantity could not be read, so no sell quantity was emitted"},
        "reduce_skipped_reason": {"type": "str", "description": "Present when the 'reduce_position' half quantity is below 1 share: the order node truncates to the integer part (0) and builds no order, so the reduction silently does nothing this round"},
    },
    locales={
        "ko": {
            "name": "VaR/CVaR 모니터",
            "description": "VaR(Value at Risk)와 CVaR(조건부 VaR, Expected Shortfall)을 계산합니다. 포트폴리오 위험을 모니터링하고 한도 초과 시 경고를 발생시킵니다.",
            "fields.lookback": "VaR 계산 기간",
            "fields.confidence_level": "신뢰수준 (%)",
            "fields.var_method": "VaR 계산 방법 (historical/parametric)",
            "fields.time_horizon": "위험 기간 (영업일)",
            "fields.alert_threshold_pct": "경고 임계값 (%)",
            "fields.action": "조치 (alert_only/reduce_position/exit_all)",
        },
    },
)


# z-score 매핑 (정규분포)
_Z_SCORES = {90.0: 1.282, 95.0: 1.645, 99.0: 2.326}


def _calculate_historical_var(returns: List[float], confidence: float) -> float:
    """Historical VaR 계산 (백분위수 방식)"""
    if not returns:
        return 0.0
    sorted_returns = sorted(returns)
    idx = int(len(sorted_returns) * (1 - confidence / 100))
    idx = max(0, min(idx, len(sorted_returns) - 1))
    return abs(sorted_returns[idx])


def _calculate_parametric_var(returns: List[float], confidence: float) -> float:
    """Parametric VaR 계산 (정규분포 가정)"""
    if len(returns) < 2:
        return 0.0
    mean_r = sum(returns) / len(returns)
    variance = sum((r - mean_r) ** 2 for r in returns) / (len(returns) - 1)
    sigma = variance ** 0.5
    z = _Z_SCORES.get(confidence, 1.645)
    var = abs(mean_r - z * sigma)
    return var


async def var_cvar_monitor_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
    positions: Optional[List[Dict[str, Any]]] = None,
    context: Any = None,
    **kwargs,
) -> Dict[str, Any]:
    """VaR/CVaR 모니터 조건 평가"""
    # positions를 symbol → dict 매핑으로 변환 (list[dict] 컨벤션)
    position_map: Dict[str, Dict[str, Any]] = {}
    if positions:
        for p in positions:
            if isinstance(p, dict) and p.get("symbol"):
                position_map[p["symbol"]] = p

    mapping = field_mapping or {}
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")

    lookback = fields.get("lookback", 60)
    confidence = fields.get("confidence_level", 95.0)
    var_method = fields.get("var_method", "historical")
    time_horizon = fields.get("time_horizon", 1)
    alert_threshold = fields.get("alert_threshold_pct", 5.0)
    action = fields.get("action", "alert_only")

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
        symbols = [{"symbol": s, "exchange": symbol_exchange_map.get(s, "UNKNOWN")} for s in symbol_data_map]

    passed, failed, symbol_results, values = [], [], [], []
    breached_count = 0
    all_vars = []

    for sym_info in symbols:
        symbol = sym_info.get("symbol", "") if isinstance(sym_info, dict) else str(sym_info)
        exchange = sym_info.get("exchange", "UNKNOWN") if isinstance(sym_info, dict) else "UNKNOWN"
        sym_dict = {"symbol": symbol, "exchange": exchange}

        rows = symbol_data_map.get(symbol, [])
        if not rows:
            failed.append(sym_dict)
            symbol_results.append({"symbol": symbol, "exchange": exchange, "error": "No data"})
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))
        prices = [float(r.get(close_field, 0)) for r in rows_sorted if r.get(close_field) is not None]

        if len(prices) < lookback + 1:
            failed.append(sym_dict)
            symbol_results.append({"symbol": symbol, "exchange": exchange, "error": "Insufficient data"})
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        recent_prices = prices[-(lookback + 1):]
        returns = [
            (recent_prices[i] - recent_prices[i - 1]) / recent_prices[i - 1]
            for i in range(1, len(recent_prices))
            if recent_prices[i - 1] > 0
        ]

        if not returns:
            failed.append(sym_dict)
            symbol_results.append({"symbol": symbol, "exchange": exchange, "error": "No valid returns"})
            values.append({"symbol": symbol, "exchange": exchange, "time_series": []})
            continue

        # VaR 계산
        if var_method == "parametric":
            var_1d = _calculate_parametric_var(returns, confidence)
        else:
            var_1d = _calculate_historical_var(returns, confidence)

        # N-day VaR (시간 스케일링)
        var_nd = var_1d * (time_horizon ** 0.5)
        var_pct = round(var_nd * 100, 4)

        # CVaR: VaR 이하 수익률의 평균 (더 보수적)
        var_cutoff = -var_1d
        tail_returns = [r for r in returns if r <= var_cutoff]
        if tail_returns:
            cvar_1d = abs(sum(tail_returns) / len(tail_returns))
        else:
            cvar_1d = var_1d
        cvar_nd = cvar_1d * (time_horizon ** 0.5)
        cvar_pct = round(cvar_nd * 100, 4)

        # 한도 초과 여부
        breached = var_pct > alert_threshold

        result_info = {
            "symbol": symbol, "exchange": exchange,
            "var_pct": var_pct,
            "cvar_pct": cvar_pct,
            "breached": breached,
        }

        # positions가 있으면 달러 VaR 계산.
        # 수량은 int() 로 자르지 않는다 — 0.532주(LS 해외주식 소수점 주식) 포지션이
        # int(0.532)=0 이 되어 150달러 x 0.532 = 79.8달러짜리 포지션이 0.0 으로
        # 보고됐다(관측: 이 파일의 수정 전 코드로 재현, 2026-09-12).
        if symbol in position_map:
            pos = position_map[symbol]
            current_price = coerce_qty(pos.get("current_price", 0))
            qty = coerce_qty(pos.get("qty", pos.get("quantity", 0)))
            if current_price is None or qty is None:
                # 못 읽은 값을 0 으로 뭉개면 '포지션 가치 0' 이라는 거짓 사실이 된다.
                # 왜 못 실었는지를 남긴다 ('안 보낸 필드는 안 보냈다고 표시' 규약).
                result_info["position_value_unavailable_reason"] = (
                    "포지션 금액을 계산할 수 없음 "
                    f"(current_price={pos.get('current_price')!r}, "
                    f"qty={pos.get('qty', pos.get('quantity'))!r})"
                )
            else:
                position_value = current_price * qty
                result_info["var_dollar"] = round(position_value * var_nd, 2)
                result_info["position_value"] = round(position_value, 2)

        all_vars.append(var_pct)

        if breached:
            breached_count += 1
            if action == "exit_all":
                sym_dict["sell_quantity"] = "all"
            elif action == "reduce_position":
                if symbol in position_map:
                    raw_qty = position_map[symbol].get(
                        "qty", position_map[symbol].get("quantity", 0)
                    )
                    # 구 코드 ``max(1, qty // 2)`` 는 0.532주 보유에서 1주 매도를
                    # 실어 보냈다(보유 초과). 공용 헬퍼로 통일 — 절단·바닥올림 없음,
                    # 상한은 보유량 (_position_qty.half_position_qty).
                    half = half_position_qty(raw_qty)
                    if half is None:
                        result_info["sell_quantity_unavailable_reason"] = (
                            f"보유 수량을 읽을 수 없어 축소 수량을 싣지 않음 (qty={raw_qty!r})"
                        )
                    else:
                        sym_dict["sell_quantity"] = half
                        result_info["sell_quantity"] = half
                        # 0 < 절반 < 1 이면 주문 송신부가 정수부 0 으로 접어 주문
                        # 자체를 만들지 않는다(_position_qty.below_broker_lot).
                        # 수량은 그대로 둔다 — 정수화·올림은 송신부의 규약이다.
                        # 다만 '축소했다고 보고했는데 아무 일도 없었다' 를 없애기
                        # 위해 사유를 드러낸다.
                        if below_broker_lot(half):
                            result_info["reduce_skipped_reason"] = (
                                f"축소 수량 {half!r} 주는 1주 미만이라 주문 송신부가 정수부(0)로 "
                                f"접어 주문을 만들지 않는다 — 보유 {raw_qty!r} 주에서 실제 축소가 "
                                "일어나지 않는다"
                            )
                else:
                    # positions 에 해당 종목이 없으면 수량을 지어내지 않는다.
                    result_info["sell_quantity_unavailable_reason"] = (
                        "positions 입력에 해당 종목이 없어 축소 수량을 싣지 않음"
                    )
            passed.append(sym_dict)

            # risk_event 기록
            if context and hasattr(context, "risk_tracker") and context.risk_tracker:
                try:
                    # 🔴 record_event 는 실제 트래커에 없는 메서드다 (관측 2026-09-12):
                    #    WorkflowRiskTracker 의 실제 이름은 record_risk_event 다. 아래 except 가
                    #    AttributeError 를 삼키므로 이 위험 이벤트는 **한 건도 기록되지 않는다**.
                    #    메서드명 정렬은 이 플러그인 밖(엔진) 수정이라 여기서 고치지 않는다 — 미검증.
                    context.risk_tracker.record_event(
                        event_type="var_breach",
                        symbol=symbol,
                        data={"var_pct": var_pct, "threshold": alert_threshold, "action": action},
                    )
                except Exception:
                    pass
        else:
            failed.append(sym_dict)

        symbol_results.append(result_info)
        time_series = [{
            "var_pct": var_pct,
            "cvar_pct": cvar_pct,
            "breached": breached,
            "signal": "sell" if breached else None,
            "side": "short" if breached else None,
        }]
        values.append({"symbol": symbol, "exchange": exchange, "time_series": time_series})

    # 포트폴리오 VaR (단순 합산 - 상관관계 무시)
    portfolio_var_pct = round(sum(all_vars) / len(all_vars), 4) if all_vars else 0
    portfolio_cvar_pct = round(
        sum(sr["cvar_pct"] for sr in symbol_results if "cvar_pct" in sr) / max(len(symbol_results), 1), 4
    )

    return {
        "passed_symbols": passed, "failed_symbols": failed,
        "symbol_results": symbol_results, "values": values,
        "result": len(passed) > 0,
        "analysis": {
            "indicator": "VarCvarMonitor",
            "var_method": var_method,
            "confidence_level": confidence,
            "time_horizon": time_horizon,
            "alert_threshold_pct": alert_threshold,
            "portfolio_var_pct": portfolio_var_pct,
            "portfolio_cvar_pct": portfolio_cvar_pct,
            "breached_count": breached_count,
            "total_symbols": len(symbol_results),
        },
    }


__all__ = ["var_cvar_monitor_condition", "VAR_CVAR_MONITOR_SCHEMA", "risk_features"]
