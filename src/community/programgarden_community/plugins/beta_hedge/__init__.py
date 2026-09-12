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

상태(strategy_state)·이벤트 경로 — 2026-09-12 수정
--------------------------------------------------------------------------------
계산된 포트폴리오 베타를 ``portfolio_beta`` 키에 저장하고(값 float → 트래커 'float'
타입으로 그대로 왕복), 헷지가 필요하면 ``beta_deviation`` 위험 이벤트를 남긴다. 상태는
**write-only** 다 — 이 플러그인은 되읽지 않는다. 키는 노드별로 나뉘지 않는다(같은
워크플로우에 BetaHedge 노드를 둘 이상 두면 마지막 값이 남는다).

2026-09-12 이전에는 실제 트래커 ``programgarden.database.workflow_risk_tracker.
WorkflowRiskTracker`` 에 없는 ``set_state``/``record_event`` 를 불렀고 ``except: pass``
가 그 AttributeError 를 삼켜 상태도 이벤트도 **한 번도 기록되지 않았다**(data 기반
분기는 예전부터 context 를 넘겼으므로 라이브에서도 같은 경로였다 — 코드 대조 기준).
이제 실제 이름 ``save_state`` / ``record_risk_event(event_type, severity, symbol, exchange,
details, node_id)`` 를 동기 호출하고, 실패는 삼키지 않고 logger.warning 으로 남긴다.
``load_state``/``save_state``/``delete_state`` 셋이 전부 없는 트래커 변종이면 크래시
대신 **무상태로 강등**한다(저장·이벤트 생략). dry_run 에서는 트래커가 뜨지 않는다.
"""

import logging
from typing import List, Dict, Any, Optional, Set
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType

from .._position_qty import coerce_qty

logger = logging.getLogger(__name__)


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
        "beta_contribution": {"type": "float", "description": "This symbol's contribution to portfolio beta (beta x position market value when positions are provided, otherwise the equal-weight share)"},
        "beta_contribution_unavailable_reason": {"type": "str", "description": "Present instead of beta_contribution when the held quantity or current price could not be read (same values weight depends on)"},
        "weight": {"type": "float", "description": "Position market value (available when positions are provided; fractional share counts are kept, not truncated)"},
        "weight_unavailable_reason": {"type": "str", "description": "Present instead of weight when the held quantity or current price could not be read"},
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
    portfolio_beta: Optional[float] = None
    portfolio_beta_unavailable_reason: Optional[str] = None
    if position_map:
        total_value = 0.0
        weighted_beta = 0.0
        unreadable_symbols: List[str] = []
        for bd in beta_data:
            sym = bd["symbol"]
            if sym in position_map:
                pos = position_map[sym]
                # 수량/가격을 int()·float() 로 직접 자르지 않는다 — int(0.532)=0 이라
                # 소수점 주식 포지션이 가중치 0 으로 빠져 포트폴리오 베타를 왜곡했고,
                # 문자열 쓰레기 값에는 ValueError 로 죽었다. 공용 헬퍼는 못 읽으면
                # None 을 준다(_position_qty.coerce_qty).
                qty = coerce_qty(pos.get("qty", pos.get("quantity", 0)))
                price = coerce_qty(pos.get("current_price", 0))
                if qty is None or price is None:
                    unreadable_symbols.append(sym)
                    continue  # 읽을 수 없는 포지션은 가중치에서 제외(0 으로 뭉개지 않음)
                pos_value = price * qty
                weighted_beta += bd["beta"] * pos_value
                total_value += pos_value
        if total_value > 0:
            portfolio_beta = round(weighted_beta / total_value, 4)
        else:
            # 가중평균의 분모가 0 이다 — '베타가 0' 이 아니라 **값이 없다**.
            # 구 코드는 여기서 0 을 지어냈고, 그 0 이 그대로 beta_deviation 을 지나
            # hedge_needed=True 라는 거짓 신호(target_beta 와의 거리)까지 만들었다.
            # 심볼 수준 weight 와 같은 규약으로 값을 싣지 않고 사유를 남긴다.
            portfolio_beta_unavailable_reason = (
                "포지션 가중 포트폴리오 베타를 계산할 수 없음 — 가중치 합(총 포지션 금액)이 0"
            )
            if unreadable_symbols:
                portfolio_beta_unavailable_reason += (
                    f" (수량/가격을 읽을 수 없는 종목: {', '.join(unreadable_symbols)})"
                )
    else:
        # 동일 비중 가정
        portfolio_beta = round(sum(bd["beta"] for bd in beta_data) / len(beta_data), 4)

    # 헷지 필요 여부
    if portfolio_beta is None:
        # 판정 불가다. '헷지 불필요' 라는 결론을 지어내지 않기 위해 deviation 도
        # 싣지 않고, 아래 analysis 에 왜 판정을 못 했는지를 남긴다.
        beta_deviation = None
        hedge_needed = False
    else:
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

    # state / risk_event — 메서드 이름·호출 규약은 **실제 트래커**(WorkflowRiskTracker)에
    # 맞춘다: save_state / load_state / delete_state, record_risk_event(event_type, severity,
    # symbol, exchange, details, node_id) — 전부 동기. 종전의 set_state / record_event 는 실제
    # 클래스에 없는 이름이라 except 가 AttributeError 를 삼켜 상태도 이벤트도 **한 번도
    # 기록되지 않았다**. 필요한 메서드가 없는 트래커 변종이면 크래시 대신 그 경로만 끈다.
    _tracker = getattr(context, "risk_tracker", None) if context else None
    has_state = _tracker is not None and all(
        hasattr(_tracker, name) for name in ("load_state", "save_state", "delete_state")
    )
    has_events = _tracker is not None and hasattr(_tracker, "record_risk_event")

    if has_state and portfolio_beta is not None:
        # 계산되지 않은 베타를 상태에 저장하면 다음 회차가 그 거짓값을 읽는다.
        # 값은 float → 트래커 'float' 타입으로 그대로 왕복한다.
        try:
            if not _tracker.save_state("portfolio_beta", portfolio_beta):
                logger.warning(
                    "BetaHedge: 상태 저장 실패 (portfolio_beta) — 트래커가 False 를 돌려줌 "
                    "('state' feature 없음 또는 DB 쓰기 실패)"
                )
        except Exception as e:
            logger.warning(f"BetaHedge: 상태 저장 실패 (portfolio_beta): {e}")

    # risk_event 기록
    if hedge_needed and has_events:
        try:
            event_id = _tracker.record_risk_event(
                event_type="beta_deviation",
                severity="warning",
                symbol="PORTFOLIO",
                details={
                    "portfolio_beta": portfolio_beta,
                    "target_beta": target_beta,
                    "deviation": round(beta_deviation, 4),
                    "hedge_method": hedge_method,
                },
            )
            if event_id is None:
                logger.warning(
                    "BetaHedge: 위험 이벤트 기록 실패 (beta_deviation) — 트래커가 None 을 돌려줌 "
                    "('events' feature 없음 또는 INSERT 실패)"
                )
        except Exception as e:
            logger.warning(f"BetaHedge: 위험 이벤트 기록 실패 (beta_deviation): {e}")

    # 결과 정리
    for bd in beta_data:
        symbol = bd["symbol"]
        exchange = bd["exchange"]
        sym_dict = {"symbol": symbol, "exchange": exchange}

        result_info = {
            "symbol": symbol, "exchange": exchange,
            "beta": bd["beta"],
        }
        # 포트폴리오 내 비중(weight)과 그 비중으로 만든 기여도(beta_contribution)는
        # **같은 두 값(수량·가격)에서 나온다** — 그래서 가용성도 같이 간다. 구 코드는
        # weight 만 '못 읽으면 사유' 로 바꾸고 기여도는 옆에서 0 을 지어내, 같은
        # 회차 안에서 "금액은 못 읽었는데 기여도는 0" 이라는 모순을 냈다.
        if symbol in position_map:
            pos = position_map[symbol]
            qty = coerce_qty(pos.get("qty", pos.get("quantity", 0)))
            price = coerce_qty(pos.get("current_price", 0))
            if qty is None or price is None:
                unavailable_reason = (
                    "포지션 금액을 계산할 수 없음 "
                    f"(current_price={pos.get('current_price')!r}, "
                    f"qty={pos.get('qty', pos.get('quantity'))!r})"
                )
                result_info["weight_unavailable_reason"] = unavailable_reason
                result_info["beta_contribution_unavailable_reason"] = unavailable_reason
            else:
                pos_value = price * qty
                result_info["weight"] = round(pos_value, 2)
                # pos_value 가 0 이면(수량 0 · 가격 0) 기여도 0 은 **읽은 값에서 나온
                # 계산 결과**다 — 지어낸 값이 아니므로 그대로 싣는다.
                result_info["beta_contribution"] = round(bd["beta"] * pos_value, 2)
        else:
            # positions 에 없는 종목: 포트폴리오 베타와 같은 '동일 비중' 가정을 쓴다.
            result_info["beta_contribution"] = round(bd["beta"] / len(beta_data), 4)

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

        ts_row = {
            "beta": bd["beta"],
            "signal": "sell" if hedge_needed else None,
            "side": "short" if hedge_needed else None,
        }
        if portfolio_beta is not None:
            ts_row["portfolio_beta"] = portfolio_beta
        time_series = [ts_row]
        values.append({"symbol": symbol, "exchange": exchange, "time_series": time_series})

    analysis: Dict[str, Any] = {
        "indicator": "BetaHedge",
        "market_symbol": market_symbol,
        "target_beta": target_beta,
        "beta_tolerance": beta_tolerance,
        "hedge_needed": hedge_needed,
        "hedge_method": hedge_method,
        "total_symbols": len(beta_data),
    }
    if portfolio_beta is None:
        # 값을 지어내는 대신 왜 없는지를 싣는다. hedge_needed=False 는 '헷지가
        # 필요 없다' 가 아니라 '판정하지 못했다' 는 뜻임을 여기서 읽을 수 있다.
        analysis["portfolio_beta_unavailable_reason"] = portfolio_beta_unavailable_reason
        analysis["hedge_needed_undetermined"] = True
    else:
        analysis["portfolio_beta"] = portfolio_beta

    result_dict = {
        "passed_symbols": passed, "failed_symbols": failed,
        "symbol_results": symbol_results, "values": values,
        "result": hedge_needed,
        "analysis": analysis,
    }

    if hedge_recommendation:
        result_dict["hedge_recommendation"] = hedge_recommendation

    return result_dict


__all__ = ["beta_hedge_condition", "BETA_HEDGE_SCHEMA", "risk_features"]
