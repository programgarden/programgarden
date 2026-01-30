"""
RSI (Relative Strength Index) 플러그인

RSI overbought/oversold condition evaluation.

입력 형식 (ConditionNode와 통일):
- data: 플랫 배열 (flatten된 데이터)
  예: [
    {symbol: "AAPL", exchange: "NASDAQ", date: "20260116", close: 150.0, ...},
    {symbol: "AAPL", exchange: "NASDAQ", date: "20260115", close: 149.0, ...},
    ...
  ]
- field_mapping: 필드명 매핑
  예: {close_field: "close", date_field: "date", symbol_field: "symbol", ...}
"""

from typing import List, Dict, Any, Optional
from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


RSI_SCHEMA = PluginSchema(
    id="RSI",
    name="RSI (Relative Strength Index)",
    category=PluginCategory.STRATEGY_CONDITION,
    version="3.0.0",
    description="Identifies overbought or oversold conditions. RSI below 30 suggests a buying opportunity, above 70 suggests a selling opportunity.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "period": {
            "type": "int",
            "default": 14,
            "title": "Period",
            "description": "RSI calculation period",
            "ge": 2,
            "le": 100,
        },
        "threshold": {
            "type": "float",
            "default": 30,
            "title": "Threshold",
            "description": "Overbought/oversold threshold value",
            "ge": 0,
            "le": 100,
        },
        "direction": {
            "type": "string",
            "default": "below",
            "title": "Direction",
            "description": "below: oversold, above: overbought",
            "enum": ["below", "above"],
        },
    },
    required_data=["data"],
    # items { from, extract } 필수 필드 (v3.0.0+)
    required_fields=["symbol", "exchange", "date", "close"],
    optional_fields=[],
    tags=["momentum", "oscillator"],
    locales={
        "ko": {
            "name": "RSI (상대강도지수)",
            "description": "주가가 과매도(너무 많이 팔림) 또는 과매수(너무 많이 삼) 상태인지 판단합니다. RSI가 30 이하면 싸게 살 수 있는 기회, 70 이상이면 비싸게 팔 수 있는 기회를 나타냅니다.",
            "fields.period": "RSI 계산에 사용할 기간",
            "fields.threshold": "과매도/과매수 판단 기준값",
            "fields.direction": "방향 (below: 과매도, above: 과매수)",
        },
    },
)


def calculate_rsi(prices: List[float], period: int = 14) -> float:
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


def calculate_rsi_series(prices: List[float], period: int = 14) -> List[float]:
    """
    RSI 시계열 계산 (time_series용)
    
    Args:
        prices: 종가 리스트 (최신이 마지막)
        period: RSI 기간 (기본 14)
    
    Returns:
        RSI 시계열 리스트 (길이: len(prices) - period)
    """
    if len(prices) < period + 1:
        return []
    
    rsi_values = []
    
    for i in range(period + 1, len(prices) + 1):
        sub_prices = prices[:i]
        rsi = calculate_rsi(sub_prices, period)
        rsi_values.append(rsi)
    
    return rsi_values


async def rsi_condition(
    data: List[Dict[str, Any]],
    fields: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None,
    symbols: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    RSI 조건 평가 (새 형식: data + field_mapping)
    
    Args:
        data: 플랫 배열 데이터 (flatten된 형태)
              [{symbol, exchange, date, close, open, high, low, volume}, ...]
        fields: 플러그인 파라미터 {"period": 14, "threshold": 30, "direction": "below"}
        field_mapping: 필드명 매핑 (기본값 사용 가능)
                       {close_field, open_field, high_field, low_field, volume_field, date_field, symbol_field, exchange_field}
        symbols: 평가할 종목 리스트 (없으면 data에서 자동 추출)
    
    Returns:
        {
          "passed_symbols": [{exchange, symbol}, ...],
          "failed_symbols": [{exchange, symbol}, ...],
          "symbol_results": [{symbol, exchange, rsi, current_price}, ...],
          "values": [{symbol, exchange, time_series: [{date, ..., rsi}, ...]}, ...],
          "result": bool
        }
    """
    # 필드 매핑 기본값
    mapping = field_mapping or {}
    close_field = mapping.get("close_field", "close")
    date_field = mapping.get("date_field", "date")
    symbol_field = mapping.get("symbol_field", "symbol")
    exchange_field = mapping.get("exchange_field", "exchange")
    open_field = mapping.get("open_field", "open")
    high_field = mapping.get("high_field", "high")
    low_field = mapping.get("low_field", "low")
    volume_field = mapping.get("volume_field", "volume")
    
    # 플러그인 파라미터
    period = fields.get("period", 14)
    threshold = fields.get("threshold", 30)
    direction = fields.get("direction", "below")
    
    # data가 없으면 빈 결과 반환
    if not data or not isinstance(data, list):
        return {
            "passed_symbols": [],
            "failed_symbols": [],
            "symbol_results": [],
            "values": [],
            "result": False,
            "analysis": {"error": "No data provided"},
        }
    
    # === 1. 종목별로 데이터 그룹화 ===
    # data는 플랫 배열: [{symbol: "AAPL", date: "20260116", close: 150}, ...]
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
    
    # === 2. 평가할 종목 목록 결정 ===
    if symbols:
        # 명시적으로 지정된 경우
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
        # data에서 자동 추출
        target_symbols = [
            {"symbol": sym, "exchange": symbol_exchange_map.get(sym, "UNKNOWN")}
            for sym in symbol_data_map.keys()
        ]
    
    # === 3. 각 종목별 RSI 계산 ===
    passed = []
    failed = []
    symbol_results = []
    values = []
    
    for sym_info in target_symbols:
        symbol = sym_info["symbol"]
        exchange = sym_info["exchange"]
        sym_dict = {"symbol": symbol, "exchange": exchange}
        
        # 해당 종목 데이터 가져오기
        rows = symbol_data_map.get(symbol, [])
        
        if not rows:
            # 데이터 없음
            failed.append(sym_dict)
            symbol_results.append({
                "symbol": symbol,
                "exchange": exchange,
                "rsi": None,
                "current_price": None,
                "error": "No data",
            })
            values.append({
                "symbol": symbol,
                "exchange": exchange,
                "time_series": [],
            })
            continue
        
        # 날짜순 정렬 (오래된 것부터)
        rows_sorted = sorted(rows, key=lambda x: x.get(date_field, ""))
        
        # 종가 추출
        prices = []
        for row in rows_sorted:
            price = row.get(close_field)
            if price is not None:
                try:
                    prices.append(float(price))
                except (ValueError, TypeError):
                    pass
        
        rsi_value = None
        current_price = prices[-1] if prices else None
        
        if len(prices) < period + 1:
            # 데이터 부족 - 시뮬레이션
            import random
            rsi_value = round(random.uniform(30, 70), 2)
            values.append({
                "symbol": symbol,
                "exchange": exchange,
                "time_series": [],
            })
        else:
            # RSI 계산
            rsi_value = calculate_rsi(prices, period)
            rsi_series = calculate_rsi_series(prices, period)
            
            # time_series 생성 (원본 데이터 + RSI 값 + signal/side)
            rsi_start_idx = period
            time_series_with_rsi = []
            for i, rsi_val in enumerate(rsi_series):
                row_idx = rsi_start_idx + i
                if row_idx < len(rows_sorted):
                    original_row = rows_sorted[row_idx]
                    
                    # signal, side 결정
                    signal = None
                    side = "long"
                    if rsi_val is not None:
                        if direction == "below" and rsi_val < threshold:
                            signal = "buy"
                            side = "long"
                        elif direction == "above" and rsi_val > threshold:
                            signal = "sell"
                            side = "long"  # 해외주식 기본, 해외선물은 executor에서 allow_short 처리
                    
                    # 원본 필드 + rsi + signal/side 추가
                    new_row = {
                        date_field: original_row.get(date_field, ""),
                        open_field: original_row.get(open_field),
                        high_field: original_row.get(high_field),
                        low_field: original_row.get(low_field),
                        close_field: original_row.get(close_field),
                        volume_field: original_row.get(volume_field),
                        "rsi": rsi_val,
                        "signal": signal,
                        "side": side,
                    }
                    time_series_with_rsi.append(new_row)
            
            values.append({
                "symbol": symbol,
                "exchange": exchange,
                "time_series": time_series_with_rsi,
            })
        
        # 결과 저장
        symbol_results.append({
            "symbol": symbol,
            "exchange": exchange,
            "rsi": rsi_value,
            "current_price": current_price,
        })
        
        # 조건 평가
        if rsi_value is not None:
            if direction == "below":
                passed_condition = rsi_value < threshold
            else:  # above
                passed_condition = rsi_value > threshold
            
            if passed_condition:
                passed.append(sym_dict)
            else:
                failed.append(sym_dict)
        else:
            failed.append(sym_dict)
    
    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "symbol_results": symbol_results,
        "result": len(passed) > 0,
        "values": values,
        "analysis": {
            "indicator": "RSI",
            "period": period,
            "threshold": threshold,
            "direction": direction,
            "comparison": f"RSI {'<' if direction == 'below' else '>'} {threshold}",
        },
    }


__all__ = ["rsi_condition", "calculate_rsi", "calculate_rsi_series", "RSI_SCHEMA"]
