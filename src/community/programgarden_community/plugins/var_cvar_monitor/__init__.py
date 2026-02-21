"""
VarCvarMonitor (VaR/CVaR 모니터) 플러그인

Value at Risk(VaR)와 Conditional VaR(CVaR, Expected Shortfall) 계산.
한도 초과 시 위험 이벤트 기록 및 포지션 축소 추천.

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, close, ...}, ...]
- positions (선택): {symbol: {current_price, qty, ...}} - 달러 VaR 계산용
- fields: {lookback, confidence_level, var_method, time_horizon, alert_threshold_pct, action}
"""

from typing import List, Dict, Any, Optional, Set
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


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
    positions: Optional[Dict[str, Any]] = None,
    context: Any = None,
    **kwargs,
) -> Dict[str, Any]:
    """VaR/CVaR 모니터 조건 평가"""
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

        # positions가 있으면 달러 VaR 계산
        if positions and symbol in positions:
            pos = positions[symbol]
            current_price = float(pos.get("current_price", 0))
            qty = int(pos.get("qty", 0))
            position_value = current_price * qty
            result_info["var_dollar"] = round(position_value * var_nd, 2)
            result_info["position_value"] = round(position_value, 2)

        all_vars.append(var_pct)

        if breached:
            breached_count += 1
            if action == "exit_all":
                sym_dict["sell_quantity"] = "all"
            elif action == "reduce_position":
                if positions and symbol in positions:
                    qty = int(positions[symbol].get("qty", 0))
                    sym_dict["sell_quantity"] = max(1, qty // 2)
            passed.append(sym_dict)

            # risk_event 기록
            if context and hasattr(context, "risk_tracker") and context.risk_tracker:
                try:
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
