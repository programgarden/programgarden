"""
BetaHedge (베타 헷지) 플러그인

포트폴리오 베타 모니터링 및 헷지 추천.
시장 대비 베타가 목표 범위를 벗어나면 인버스 ETF 또는 고베타 종목 축소를 추천합니다.

입력 형식:
- data: 플랫 배열 [{symbol, exchange, date, close, ...}, ...]
  - 반드시 market_symbol (기본: SPY) 데이터가 포함되어야 함
- positions (선택): 보유 포지션 (list[dict]) — 포트폴리오 베타 계산용
  예: [{"symbol": "AAPL", "current_price": 150.0, "qty": 100, ...}, ...]
- fields: {lookback, market_symbol, target_beta, beta_tolerance, hedge_method, ...}
"""

from typing import List, Dict, Any, Optional, Set
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


# risk_features 선언
risk_features: Set[str] = {"state", "events"}

BETA_HEDGE_SCHEMA = PluginSchema(
    id="BetaHedge",
    name="Beta Hedge",
    category=PluginCategory.POSITION,
    version="1.0.0",
    description="Monitors portfolio beta against market benchmark. Recommends hedging via inverse ETF or high-beta stock reduction when portfolio beta deviates from target.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "lookback": {
            "type": "int",
            "default": 120,
            "title": "Lookback Period",
            "description": "Lookback period for beta calculation",
            "ge": 30,
            "le": 500,
        },
        "market_symbol": {
            "type": "string",
            "default": "SPY",
            "title": "Market Symbol",
            "description": "Market benchmark symbol (must be included in data)",
        },
        "target_beta": {
            "type": "float",
            "default": 1.0,
            "title": "Target Beta",
            "description": "Target portfolio beta",
            "ge": -1.0,
            "le": 3.0,
        },
        "beta_tolerance": {
            "type": "float",
            "default": 0.2,
            "title": "Beta Tolerance",
            "description": "Acceptable deviation from target beta",
            "ge": 0.05,
            "le": 1.0,
        },
        "hedge_method": {
            "type": "string",
            "default": "long_inverse_etf",
            "title": "Hedge Method",
            "description": "Hedging strategy when beta exceeds tolerance",
            "enum": ["long_inverse_etf", "reduce_high_beta"],
        },
        "inverse_etf_symbol": {
            "type": "string",
            "default": "SH",
            "title": "Inverse ETF Symbol",
            "description": "Inverse ETF symbol (when hedge_method=long_inverse_etf)",
        },
        "max_hedge_pct": {
            "type": "float",
            "default": 30.0,
            "title": "Max Hedge (%)",
            "description": "Maximum portfolio percentage allocated to hedge",
            "ge": 5.0,
            "le": 50.0,
        },
    },
    required_data=["data"],
    required_fields=["symbol", "exchange", "date", "close"],
    optional_fields=[],
    tags=["beta", "hedge", "market_neutral", "risk_management"],
    output_fields={
        "beta": {"type": "float", "description": "Calculated beta of this symbol relative to the market benchmark"},
        "beta_contribution": {"type": "float", "description": "This symbol's contribution to portfolio beta"},
        "weight": {"type": "float", "description": "Position market value (available when positions are provided)"},
    },
    locales={
        "ko": {
            "name": "베타 헷지 (Beta Hedge)",
            "description": "포트폴리오의 시장 베타를 모니터링합니다. 베타가 목표 범위를 벗어나면 인버스 ETF 매수 또는 고베타 종목 축소를 추천합니다.",
            "fields.lookback": "베타 계산 기간",
            "fields.market_symbol": "시장 벤치마크 심볼",
            "fields.target_beta": "목표 포트폴리오 베타",
            "fields.beta_tolerance": "허용 베타 편차",
            "fields.hedge_method": "헷지 방법 (long_inverse_etf/reduce_high_beta)",
            "fields.inverse_etf_symbol": "인버스 ETF 심볼",
            "fields.max_hedge_pct": "최대 헷지 비중 (%)",
        },
    },
)


def _calculate_returns(prices: List[float]) -> List[float]:
    """일별 수익률 계산"""
    if len(prices) < 2:
        return []
    return [
        (prices[i] - prices[i - 1]) / prices[i - 1]
        for i in range(1, len(prices))
        if prices[i - 1] > 0
    ]


def _calculate_beta(stock_returns: List[float], market_returns: List[float]) -> float:
    """베타 계산: cov(stock, market) / var(market)"""
    n = min(len(stock_returns), len(market_returns))
    if n < 10:
        return 0.0

    sr = stock_returns[-n:]
    mr = market_returns[-n:]

    mean_s = sum(sr) / n
    mean_m = sum(mr) / n

    cov = sum((sr[i] - mean_s) * (mr[i] - mean_m) for i in range(n)) / (n - 1)
    var_m = sum((mr[i] - mean_m) ** 2 for i in range(n)) / (n - 1)

    if var_m == 0:
        return 0.0

    return cov / var_m


async def beta_hedge_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
    positions: Optional[List[Dict[str, Any]]] = None,
    context: Any = None,
    **kwargs,
) -> Dict[str, Any]:
    """베타 헷지 조건 평가"""
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

    lookback = fields.get("lookback", 120)
    market_symbol = fields.get("market_symbol", "SPY")
    target_beta = fields.get("target_beta", 1.0)
    beta_tolerance = fields.get("beta_tolerance", 0.2)
    hedge_method = fields.get("hedge_method", "long_inverse_etf")
    inverse_etf = fields.get("inverse_etf_symbol", "SH")
    max_hedge_pct = fields.get("max_hedge_pct", 30.0)

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

    # 마켓 데이터 추출
    if market_symbol not in symbol_data_map:
        return {
            "passed_symbols": [], "failed_symbols": [],
            "symbol_results": [], "values": [],
            "result": False,
            "analysis": {"error": f"Market symbol '{market_symbol}' not found in data"},
        }

    market_rows = sorted(symbol_data_map[market_symbol], key=lambda x: x.get(date_field, ""))
    market_date_price: Dict[str, float] = {}
    for row in market_rows:
        date = row.get(date_field, "")
        price = row.get(close_field)
        if date and price is not None:
            try:
                market_date_price[date] = float(price)
            except (ValueError, TypeError):
                pass

    # 개별 종목 베타 계산 (마켓 심볼 제외)
    if not symbols:
        symbols = [
            {"symbol": s, "exchange": symbol_exchange_map.get(s, "UNKNOWN")}
            for s in symbol_data_map if s != market_symbol
        ]

    passed, failed, symbol_results, values = [], [], [], []
    beta_data = []

    for sym_info in symbols:
        symbol = sym_info.get("symbol", "") if isinstance(sym_info, dict) else str(sym_info)
        exchange = sym_info.get("exchange", "UNKNOWN") if isinstance(sym_info, dict) else "UNKNOWN"

        if symbol == market_symbol:
            continue

        rows = symbol_data_map.get(symbol, [])
        if not rows:
            continue

        rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))
        stock_date_price: Dict[str, float] = {}
        for row in rows_sorted:
            date = row.get(date_field, "")
            price = row.get(close_field)
            if date and price is not None:
                try:
                    stock_date_price[date] = float(price)
                except (ValueError, TypeError):
                    pass

        # 공통 날짜로 정렬
        common_dates = sorted(set(stock_date_price.keys()) & set(market_date_price.keys()))
        if len(common_dates) < lookback:
            continue

        recent_dates = common_dates[-lookback:]
        stock_prices = [stock_date_price[d] for d in recent_dates]
        market_prices = [market_date_price[d] for d in recent_dates]

        stock_returns = _calculate_returns(stock_prices)
        market_returns = _calculate_returns(market_prices)

        beta = _calculate_beta(stock_returns, market_returns)
        beta_data.append({
            "symbol": symbol, "exchange": exchange,
            "beta": round(beta, 4),
        })

    if not beta_data:
        return {
            "passed_symbols": [], "failed_symbols": [],
            "symbol_results": [], "values": [],
            "result": False, "analysis": {"error": "No valid beta data"},
        }

    # 포트폴리오 베타 계산
    if position_map:
        total_value = 0
        weighted_beta = 0
        for bd in beta_data:
            sym = bd["symbol"]
            if sym in position_map:
                pos = position_map[sym]
                qty = int(pos.get("qty", pos.get("quantity", 0)))
                pos_value = float(pos.get("current_price", 0)) * qty
                weighted_beta += bd["beta"] * pos_value
                total_value += pos_value
        portfolio_beta = weighted_beta / total_value if total_value > 0 else 0
    else:
        # 동일 비중 가정
        portfolio_beta = sum(bd["beta"] for bd in beta_data) / len(beta_data)

    portfolio_beta = round(portfolio_beta, 4)

    # 헷지 필요 여부
    beta_deviation = portfolio_beta - target_beta
    hedge_needed = abs(beta_deviation) > beta_tolerance

    # 헷지 추천
    hedge_recommendation = None
    if hedge_needed and beta_deviation > 0:
        # 베타가 목표 대비 높음 → 헷지 필요
        if hedge_method == "long_inverse_etf":
            # 필요한 인버스 ETF 비중 = (portfolio_beta - target_beta) / (1 + portfolio_beta) * 100
            suggested_pct = min(max_hedge_pct, round(abs(beta_deviation) / (1 + abs(portfolio_beta)) * 100, 2))
            hedge_recommendation = {
                "action": "buy_inverse_etf",
                "inverse_etf": inverse_etf,
                "suggested_allocation_pct": suggested_pct,
            }
        else:
            # reduce_high_beta: 가장 높은 베타 종목 축소
            highest_beta = max(beta_data, key=lambda x: x["beta"])
            hedge_recommendation = {
                "action": "reduce_high_beta",
                "target_symbol": highest_beta["symbol"],
                "target_beta": highest_beta["beta"],
                "reduce_by_pct": min(max_hedge_pct, round(abs(beta_deviation) * 20, 2)),
            }

    # state 저장
    has_risk_tracker = context and hasattr(context, "risk_tracker") and context.risk_tracker
    if has_risk_tracker:
        try:
            context.risk_tracker.set_state("portfolio_beta", portfolio_beta)
        except Exception:
            pass

    # risk_event 기록
    if hedge_needed and has_risk_tracker:
        try:
            context.risk_tracker.record_event(
                event_type="beta_deviation",
                symbol="PORTFOLIO",
                data={
                    "portfolio_beta": portfolio_beta,
                    "target_beta": target_beta,
                    "deviation": round(beta_deviation, 4),
                    "hedge_method": hedge_method,
                },
            )
        except Exception:
            pass

    # 결과 정리
    for bd in beta_data:
        symbol = bd["symbol"]
        exchange = bd["exchange"]
        sym_dict = {"symbol": symbol, "exchange": exchange}

        # 포트폴리오 내 비중 기반 기여도
        if symbol in position_map:
            pos = position_map[symbol]
            qty = int(pos.get("qty", pos.get("quantity", 0)))
            pos_value = float(pos.get("current_price", 0)) * qty
            beta_contribution = round(bd["beta"] * pos_value, 2) if pos_value > 0 else 0
        else:
            beta_contribution = round(bd["beta"] / len(beta_data), 4)

        result_info = {
            "symbol": symbol, "exchange": exchange,
            "beta": bd["beta"],
            "beta_contribution": beta_contribution,
        }
        if symbol in position_map:
            pos = position_map[symbol]
            qty = int(pos.get("qty", pos.get("quantity", 0)))
            result_info["weight"] = round(
                float(pos.get("current_price", 0)) * qty, 2
            )

        symbol_results.append(result_info)

        if hedge_needed and hedge_method == "reduce_high_beta":
            highest = max(beta_data, key=lambda x: x["beta"])
            if symbol == highest["symbol"]:
                passed.append(sym_dict)
            else:
                failed.append(sym_dict)
        elif hedge_needed:
            passed.append(sym_dict)
        else:
            failed.append(sym_dict)

        time_series = [{
            "beta": bd["beta"],
            "portfolio_beta": portfolio_beta,
            "signal": "sell" if hedge_needed else None,
            "side": "short" if hedge_needed else None,
        }]
        values.append({"symbol": symbol, "exchange": exchange, "time_series": time_series})

    result_dict = {
        "passed_symbols": passed, "failed_symbols": failed,
        "symbol_results": symbol_results, "values": values,
        "result": hedge_needed,
        "analysis": {
            "indicator": "BetaHedge",
            "market_symbol": market_symbol,
            "portfolio_beta": portfolio_beta,
            "target_beta": target_beta,
            "beta_tolerance": beta_tolerance,
            "hedge_needed": hedge_needed,
            "hedge_method": hedge_method,
            "total_symbols": len(beta_data),
        },
    }

    if hedge_recommendation:
        result_dict["hedge_recommendation"] = hedge_recommendation

    return result_dict


__all__ = ["beta_hedge_condition", "BETA_HEDGE_SCHEMA", "risk_features"]
