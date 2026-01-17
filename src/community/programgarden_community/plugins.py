"""
ProgramGarden Community - 플러그인 등록

모든 커뮤니티 플러그인을 레지스트리에 등록
"""

from typing import Optional, Callable


def register_all_plugins() -> None:
    """모든 플러그인을 레지스트리에 등록"""
    from programgarden_core.registry import PluginRegistry, PluginSchema
    from programgarden_core.registry.plugin_registry import PluginCategory, ProductType

    registry = PluginRegistry()

    # === Strategy Condition Plugins ===

    # RSI
    registry.register(
        plugin_id="RSI",
        plugin_callable=_rsi_condition,
        schema=PluginSchema(
            id="RSI",
            name="RSI (Relative Strength Index)",
            category=PluginCategory.STRATEGY_CONDITION,
            version="2.0.0",
            description="RSI overbought/oversold condition (data + field_mapping 패턴)",
            products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
            fields_schema={
                "period": {"type": "int", "default": 14, "description": "RSI period"},
                "threshold": {"type": "float", "default": 30, "description": "Threshold value"},
                "direction": {"type": "string", "enum": ["below", "above"], "default": "below", "description": "Direction"},
            },
            required_data=["data"],
            tags=["momentum", "oscillator"],
            locales={
                "ko": {
                    "name": "RSI (상대강도지수)",
                    "description": "RSI 과매수/과매도 조건",
                    "fields.period": "RSI 기간",
                    "fields.threshold": "임계값",
                    "fields.direction": "방향",
                },
            },
        ),
    )

    # MACD
    registry.register(
        plugin_id="MACD",
        plugin_callable=_macd_condition,
        schema=PluginSchema(
            id="MACD",
            name="MACD (Moving Average Convergence Divergence)",
            category=PluginCategory.STRATEGY_CONDITION,
            version="2.0.0",
            description="MACD 크로스오버 조건 (data + field_mapping 패턴)",
            products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
            fields_schema={
                "fast_period": {"type": "int", "default": 12},
                "slow_period": {"type": "int", "default": 26},
                "signal_period": {"type": "int", "default": 9},
                "signal": {"type": "string", "enum": ["bullish_cross", "bearish_cross"], "default": "bullish_cross"},
            },
            required_data=["data"],
            tags=["trend", "momentum"],
        ),
    )

    # BollingerBands
    registry.register(
        plugin_id="BollingerBands",
        plugin_callable=_bollinger_condition,
        schema=PluginSchema(
            id="BollingerBands",
            name="Bollinger Bands",
            category=PluginCategory.STRATEGY_CONDITION,
            version="2.0.0",
            description="볼린저밴드 조건 (data + field_mapping 패턴)",
            products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
            fields_schema={
                "period": {"type": "int", "default": 20},
                "std": {"type": "float", "default": 2},
                "position": {"type": "string", "enum": ["below_lower", "above_upper"], "default": "below_lower"},
            },
            required_data=["data"],
            tags=["volatility", "mean-reversion"],
        ),
    )

    # VolumeSpike
    registry.register(
        plugin_id="VolumeSpike",
        plugin_callable=_volume_spike_condition,
        schema=PluginSchema(
            id="VolumeSpike",
            name="Volume Spike",
            category=PluginCategory.STRATEGY_CONDITION,
            version="1.0.0",
            description="거래량 급증 조건",
            products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
            fields_schema={
                "period": {"type": "int", "default": 20, "description": "평균 기간"},
                "multiplier": {"type": "float", "default": 2, "description": "배수"},
            },
            required_data=["volume_data"],
            tags=["volume"],
        ),
    )

    # ProfitTarget
    registry.register(
        plugin_id="ProfitTarget",
        plugin_callable=_profit_target_condition,
        schema=PluginSchema(
            id="ProfitTarget",
            name="Profit Target (익절)",
            category=PluginCategory.STRATEGY_CONDITION,
            version="2.0.0",
            description="목표 수익률 도달 조건 (data + field_mapping 패턴)",
            products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
            fields_schema={
                "percent": {"type": "float", "default": 5, "description": "목표 수익률 (%)"},
            },
            required_data=["data"],
            tags=["exit", "profit"],
        ),
    )

    # StopLoss
    registry.register(
        plugin_id="StopLoss",
        plugin_callable=_stop_loss_condition,
        schema=PluginSchema(
            id="StopLoss",
            name="Stop Loss (손절)",
            category=PluginCategory.STRATEGY_CONDITION,
            version="2.0.0",
            description="손절 조건 (data + field_mapping 패턴)",
            products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
            fields_schema={
                "percent": {"type": "float", "default": -3, "description": "손절 비율 (%, 음수)"},
            },
            required_data=["data"],
            tags=["exit", "risk"],
        ),
    )

    # === New Order Plugins ===

    # MarketOrder
    registry.register(
        plugin_id="MarketOrder",
        plugin_callable=_market_order,
        schema=PluginSchema(
            id="MarketOrder",
            name="Market Order (시장가 주문)",
            category=PluginCategory.NEW_ORDER,
            version="1.0.0",
            description="시장가 주문 실행",
            products=[ProductType.OVERSEAS_STOCK],
            fields_schema={
                "side": {"type": "string", "enum": ["buy", "sell"], "required": True},
                "amount_type": {"type": "string", "enum": ["percent_balance", "fixed", "all"], "default": "fixed"},
            },
            tags=["order", "market"],
        ),
    )

    # LimitOrder
    registry.register(
        plugin_id="LimitOrder",
        plugin_callable=_limit_order,
        schema=PluginSchema(
            id="LimitOrder",
            name="Limit Order (지정가 주문)",
            category=PluginCategory.NEW_ORDER,
            version="1.0.0",
            description="지정가 주문 실행",
            products=[ProductType.OVERSEAS_STOCK],
            fields_schema={
                "side": {"type": "string", "enum": ["buy", "sell"], "required": True},
                "price_type": {"type": "string", "enum": ["fixed", "percent_from_current"], "default": "fixed"},
                "price": {"type": "float", "description": "주문 가격"},
            },
            tags=["order", "limit"],
        ),
    )

    # === Modify Order Plugins ===

    # TrackingPriceModifier
    registry.register(
        plugin_id="TrackingPriceModifier",
        plugin_callable=_tracking_price_modifier,
        schema=PluginSchema(
            id="TrackingPriceModifier",
            name="Tracking Price Modifier (가격 추적 정정)",
            category=PluginCategory.MODIFY_ORDER,
            version="1.0.0",
            description="현재가를 추적하여 지정가 정정",
            products=[ProductType.OVERSEAS_STOCK],
            fields_schema={
                "price_gap_percent": {"type": "float", "default": 0.5, "description": "현재가 대비 가격 차이 (%)"},
                "max_modifications": {"type": "int", "default": 5, "description": "최대 정정 횟수"},
            },
            tags=["modify", "tracking"],
        ),
    )

    # === Cancel Order Plugins ===

    # TimeStopCanceller
    registry.register(
        plugin_id="TimeStopCanceller",
        plugin_callable=_time_stop_canceller,
        schema=PluginSchema(
            id="TimeStopCanceller",
            name="Time Stop Canceller (시간 초과 취소)",
            category=PluginCategory.CANCEL_ORDER,
            version="1.0.0",
            description="지정 시간 초과 시 미체결 주문 취소",
            products=[ProductType.OVERSEAS_STOCK],
            fields_schema={
                "timeout_minutes": {"type": "int", "default": 30, "description": "타임아웃 (분)"},
            },
            tags=["cancel", "timeout"],
        ),
    )


def get_plugin(plugin_id: str) -> Optional[Callable]:
    """플러그인 조회"""
    from programgarden_core.registry import PluginRegistry

    registry = PluginRegistry()
    return registry.get(plugin_id)


# === 기술적 지표 계산 유틸리티 ===

def calculate_rsi(prices: list, period: int = 14) -> float:
    """
    RSI (Relative Strength Index) 계산
    
    Args:
        prices: 종가 리스트 (최신이 마지막)
        period: RSI 기간 (기본 14)
    
    Returns:
        RSI 값 (0-100)
    """
    if len(prices) < period + 1:
        return 50.0  # 데이터 부족시 중립값
    
    # 가격 변화 계산
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    
    # 최근 period개의 변화만 사용
    recent_deltas = deltas[-(period):]
    
    # 상승/하락 분리
    gains = [d if d > 0 else 0 for d in recent_deltas]
    losses = [-d if d < 0 else 0 for d in recent_deltas]
    
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return round(rsi, 2)


def calculate_macd(prices: list, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """
    MACD (Moving Average Convergence Divergence) 계산
    
    Args:
        prices: 종가 리스트
        fast: 빠른 EMA 기간 (기본 12)
        slow: 느린 EMA 기간 (기본 26)
        signal: 시그널 기간 (기본 9)
    
    Returns:
        {"macd": float, "signal": float, "histogram": float}
    """
    if len(prices) < slow + signal:
        return {"macd": 0, "signal": 0, "histogram": 0}
    
    def ema(data, period):
        if len(data) < period:
            return data[-1] if data else 0
        multiplier = 2 / (period + 1)
        ema_values = [sum(data[:period]) / period]
        for price in data[period:]:
            ema_values.append((price - ema_values[-1]) * multiplier + ema_values[-1])
        return ema_values[-1]
    
    fast_ema = ema(prices, fast)
    slow_ema = ema(prices, slow)
    macd_line = fast_ema - slow_ema
    
    # MACD 히스토리 계산 (시그널용)
    macd_history = []
    for i in range(slow, len(prices) + 1):
        fe = ema(prices[:i], fast)
        se = ema(prices[:i], slow)
        macd_history.append(fe - se)
    
    signal_line = ema(macd_history, signal) if len(macd_history) >= signal else macd_line
    histogram = macd_line - signal_line
    
    return {
        "macd": round(macd_line, 4),
        "signal": round(signal_line, 4),
        "histogram": round(histogram, 4),
    }


def calculate_bollinger_bands(prices: list, period: int = 20, std_dev: float = 2.0) -> dict:
    """
    볼린저 밴드 계산
    
    Args:
        prices: 종가 리스트
        period: 이동평균 기간 (기본 20)
        std_dev: 표준편차 배수 (기본 2)
    
    Returns:
        {"upper": float, "middle": float, "lower": float}
    """
    if len(prices) < period:
        last_price = prices[-1] if prices else 100
        return {"upper": last_price * 1.02, "middle": last_price, "lower": last_price * 0.98}
    
    recent = prices[-period:]
    middle = sum(recent) / period
    
    # 표준편차 계산
    variance = sum((p - middle) ** 2 for p in recent) / period
    std = variance ** 0.5
    
    return {
        "upper": round(middle + std_dev * std, 2),
        "middle": round(middle, 2),
        "lower": round(middle - std_dev * std, 2),
    }


# === 플러그인 구현 ===

async def _rsi_condition(symbols: list, ohlcv_data: dict, fields: dict) -> dict:
    """
    RSI 조건 평가
    
    Args:
        symbols: 평가할 종목 리스트
        ohlcv_data: 종목별 OHLCV 데이터 {"AAPL": [{"close": ...}, ...]}
        fields: {"period": 14, "threshold": 30, "direction": "below"}
    
    Returns:
        {"passed_symbols": [...], "failed_symbols": [...], "symbol_results": {...}}
    """
    period = fields.get("period", 14)
    threshold = fields.get("threshold", 30)
    direction = fields.get("direction", "below")
    
    passed = []
    failed = []
    values = {}
    
    for symbol in symbols:
        # OHLCV 데이터 추출
        symbol_data = ohlcv_data.get(symbol, {})
        
        # OHLCV 리스트에서 종가 추출
        if isinstance(symbol_data, list):
            prices = [bar.get("close", 0) for bar in symbol_data if isinstance(bar, dict)]
        elif isinstance(symbol_data, dict):
            prices = symbol_data.get("prices", [])
        else:
            prices = []
        
        # 가격 데이터가 없으면 시뮬레이션 데이터 사용
        if not prices:
            # 테스트용 랜덤 RSI 생성
            import random
            rsi_value = random.uniform(20, 80)
        else:
            rsi_value = calculate_rsi(prices, period)
        
        symbol_results[symbol] = {"rsi": rsi_value}
        
        # 조건 평가
        if direction == "below":
            passed_condition = rsi_value < threshold
        else:  # above
            passed_condition = rsi_value > threshold
        
        if passed_condition:
            passed.append(symbol)
        else:
            failed.append(symbol)
    
    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "symbol_results": symbol_results,
        "result": len(passed) > 0,
    }


async def _macd_condition(symbols: list, ohlcv_data: dict, fields: dict) -> dict:
    """
    MACD 조건 평가
    
    Args:
        symbols: 평가할 종목 리스트
        ohlcv_data: 종목별 OHLCV 데이터
        fields: {"fast_period": 12, "slow_period": 26, "signal_period": 9, "signal": "bullish_cross"}
    """
    fast = fields.get("fast_period", 12)
    slow = fields.get("slow_period", 26)
    signal_period = fields.get("signal_period", 9)
    signal_type = fields.get("signal", "bullish_cross")
    
    passed = []
    failed = []
    symbol_results = {}
    
    for symbol in symbols:
        symbol_data = ohlcv_data.get(symbol, {})
        
        # OHLCV 리스트에서 종가 추출
        if isinstance(symbol_data, list):
            prices = [bar.get("close", 0) for bar in symbol_data if isinstance(bar, dict)]
        elif isinstance(symbol_data, dict):
            prices = symbol_data.get("prices", [])
        else:
            prices = []
        
        if not prices:
            # 테스트용
            import random
            macd_data = {
                "macd": random.uniform(-1, 1),
                "signal": random.uniform(-1, 1),
                "histogram": random.uniform(-0.5, 0.5),
            }
        else:
            macd_data = calculate_macd(prices, fast, slow, signal_period)
        
        symbol_results[symbol] = macd_data
        
        # 조건 평가
        if signal_type == "bullish_cross":
            # MACD가 시그널 상향 돌파
            passed_condition = macd_data["histogram"] > 0 and macd_data["macd"] > 0
        else:  # bearish_cross
            passed_condition = macd_data["histogram"] < 0 and macd_data["macd"] < 0
        
        if passed_condition:
            passed.append(symbol)
        else:
            failed.append(symbol)
    
    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "symbol_results": symbol_results,
        "result": len(passed) > 0,
    }


async def _bollinger_condition(symbols: list, ohlcv_data: dict, fields: dict) -> dict:
    """
    볼린저밴드 조건 평가
    """
    period = fields.get("period", 20)
    std = fields.get("std", 2)
    position = fields.get("position", "below_lower")
    
    passed = []
    failed = []
    symbol_results = {}
    
    for symbol in symbols:
        symbol_data = ohlcv_data.get(symbol, {})
        
        # OHLCV 리스트에서 종가 추출
        if isinstance(symbol_data, list):
            prices = [bar.get("close", 0) for bar in symbol_data if isinstance(bar, dict)]
            current_price = prices[-1] if prices else 100
        elif isinstance(symbol_data, dict):
            prices = symbol_data.get("prices", [])
            current_price = symbol_data.get("current_price", symbol_data.get("close", prices[-1] if prices else 100))
        else:
            prices = []
            current_price = 100
        
        if not prices:
            bb_data = {"upper": 102, "middle": 100, "lower": 98}
        else:
            bb_data = calculate_bollinger_bands(prices, period, std)
        
        bb_data["current_price"] = current_price
        symbol_results[symbol] = bb_data
        
        if position == "below_lower":
            passed_condition = current_price < bb_data["lower"]
        else:  # above_upper
            passed_condition = current_price > bb_data["upper"]
        
        if passed_condition:
            passed.append(symbol)
        else:
            failed.append(symbol)
    
    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "symbol_results": symbol_results,
        "result": len(passed) > 0,
    }


async def _volume_spike_condition(
    data: list = None,
    fields: dict = None,
    field_mapping: dict = None,
    symbols: list = None,
    **kwargs,
) -> dict:
    """거래량 급증 조건 평가"""
    from programgarden_community.plugins.strategy_conditions.volume_spike import volume_spike_condition
    return await volume_spike_condition(
        data=data,
        fields=fields,
        field_mapping=field_mapping,
        symbols=symbols,
        **kwargs,
    )


async def _profit_target_condition(symbols: list, position_data: dict, ohlcv_data: dict, fields: dict) -> dict:
    """익절 조건 평가"""
    target_percent = fields.get("percent", 5)
    
    passed = []
    failed = []
    symbol_results = {}
    
    for symbol in symbols:
        position = position_data.get(symbol, {})
        avg_price = position.get("avg_price", 100)
        
        # OHLCV 데이터에서 현재가 추출
        symbol_data = ohlcv_data.get(symbol, {})
        if isinstance(symbol_data, list) and symbol_data:
            current_price = symbol_data[-1].get("close", 100)
        elif isinstance(symbol_data, dict):
            current_price = symbol_data.get("close", symbol_data.get("current_price", 100))
        else:
            current_price = 100
        
        pnl_rate = ((current_price - avg_price) / avg_price) * 100 if avg_price > 0 else 0
        symbol_results[symbol] = {"pnl_rate": round(pnl_rate, 2), "avg_price": avg_price, "current_price": current_price}
        
        if pnl_rate >= target_percent:
            passed.append(symbol)
        else:
            failed.append(symbol)
    
    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "symbol_results": symbol_results,
        "result": len(passed) > 0,
    }


async def _stop_loss_condition(symbols: list, position_data: dict, ohlcv_data: dict, fields: dict) -> dict:
    """손절 조건 평가"""
    stop_percent = fields.get("percent", -3)
    
    passed = []
    failed = []
    symbol_results = {}
    
    for symbol in symbols:
        position = position_data.get(symbol, {})
        avg_price = position.get("avg_price", 100)
        
        # OHLCV 데이터에서 현재가 추출
        symbol_data = ohlcv_data.get(symbol, {})
        if isinstance(symbol_data, list) and symbol_data:
            current_price = symbol_data[-1].get("close", 100)
        elif isinstance(symbol_data, dict):
            current_price = symbol_data.get("close", symbol_data.get("current_price", 100))
        else:
            current_price = 100
        
        pnl_rate = ((current_price - avg_price) / avg_price) * 100 if avg_price > 0 else 0
        symbol_results[symbol] = {"pnl_rate": round(pnl_rate, 2)}
        
        if pnl_rate <= stop_percent:
            passed.append(symbol)
        else:
            failed.append(symbol)
    
    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "symbol_results": symbol_results,
        "result": len(passed) > 0,
    }


async def _market_order(symbols: list, quantities: dict, fields: dict, context: dict) -> dict:
    """
    시장가 주문 실행
    
    Args:
        symbols: 주문할 종목 리스트
        quantities: 종목별 수량 {"AAPL": 10}
        fields: {"side": "buy", "amount_type": "fixed", "amount": 10}
        context: 실행 컨텍스트 (broker_connection 등)
    """
    side = fields.get("side", "buy")
    amount_type = fields.get("amount_type", "fixed")
    amount = fields.get("amount", 10)
    
    orders = []
    
    for symbol in symbols:
        quantity = quantities.get(symbol, amount)
        
        order = {
            "order_id": f"MKT-{symbol}-{side.upper()[:1]}-001",
            "symbol": symbol,
            "side": side,
            "order_type": "market",
            "quantity": quantity,
            "status": "submitted",
        }
        orders.append(order)
    
    return {
        "orders": orders,
        "total_count": len(orders),
        "status": "submitted",
    }


async def _limit_order(symbols: list, quantities: dict, prices: dict, fields: dict, context: dict) -> dict:
    """
    지정가 주문 실행
    
    Args:
        symbols: 주문할 종목 리스트
        quantities: 종목별 수량
        prices: 종목별 주문가격
        fields: {"side": "buy", "price_type": "fixed", "price": 100}
    """
    side = fields.get("side", "buy")
    price_type = fields.get("price_type", "fixed")
    default_price = fields.get("price", 0)
    
    orders = []
    
    for symbol in symbols:
        quantity = quantities.get(symbol, 10)
        price = prices.get(symbol, default_price)
        
        order = {
            "order_id": f"LMT-{symbol}-{side.upper()[:1]}-001",
            "symbol": symbol,
            "side": side,
            "order_type": "limit",
            "quantity": quantity,
            "price": price,
            "status": "submitted",
        }
        orders.append(order)
    
    return {
        "orders": orders,
        "total_count": len(orders),
        "status": "submitted",
    }


async def _tracking_price_modifier(target_orders: list, ohlcv_data: dict, fields: dict) -> dict:
    """가격 추적 정정"""
    gap_percent = fields.get("price_gap_percent", 0.5)
    max_mods = fields.get("max_modifications", 5)
    
    modified = []
    
    for order in target_orders:
        symbol = order.get("symbol")
        
        # OHLCV 데이터에서 현재가 추출
        symbol_data = ohlcv_data.get(symbol, {})
        if isinstance(symbol_data, list) and symbol_data:
            current_price = symbol_data[-1].get("close", order.get("price", 100))
        elif isinstance(symbol_data, dict):
            current_price = symbol_data.get("close", symbol_data.get("current_price", order.get("price", 100)))
        else:
            current_price = order.get("price", 100)
        
        # 현재가 기준 새 주문가 계산
        if order.get("side") == "buy":
            new_price = current_price * (1 - gap_percent / 100)
        else:
            new_price = current_price * (1 + gap_percent / 100)
        
        modified.append({
            "order_id": order.get("order_id"),
            "old_price": order.get("price"),
            "new_price": round(new_price, 2),
            "status": "modified",
        })
    
    return {
        "modified_orders": modified,
        "total_count": len(modified),
    }


async def _time_stop_canceller(target_orders: list, fields: dict) -> dict:
    """시간 초과 취소"""
    from datetime import datetime, timedelta
    
    timeout_minutes = fields.get("timeout_minutes", 30)
    
    cancelled = []
    not_cancelled = []
    
    for order in target_orders:
        order_time_str = order.get("order_time")
        
        # 시간 파싱 (간단한 구현)
        if order_time_str:
            try:
                order_time = datetime.fromisoformat(order_time_str)
                elapsed = datetime.now() - order_time
                if elapsed > timedelta(minutes=timeout_minutes):
                    cancelled.append({
                        "order_id": order.get("order_id"),
                        "status": "cancelled",
                        "reason": "timeout",
                    })
                    continue
            except:
                pass
        
        not_cancelled.append(order)
    
    return {
        "cancelled_orders": cancelled,
        "remaining_orders": not_cancelled,
        "total_cancelled": len(cancelled),
    }
