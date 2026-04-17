"""
Profit Target (익절) 플러그인

입력 형식:
- positions: RealAccountNode의 positions 출력 (list[dict])
  예: [{"symbol": "AAPL", "pnl_rate": 6.3, "current_price": 150.0, ...}, ...]
- fields: {target_percent}

※ 시계열 데이터(data) 불필요 - positions의 pnl_rate를 직접 사용
"""

from typing import Any, Dict, List, Optional

from programgarden_core.registry import PluginSchema
from programgarden_core.registry.plugin_registry import PluginCategory, ProductType


PROFIT_TARGET_SCHEMA = PluginSchema(
    id="ProfitTarget",
    name="Profit Target",
    category=PluginCategory.POSITION,
    version="3.1.0",
    description="Checks if holdings have reached the target profit rate. Example: Sell to realize profit when gain exceeds 5%.",
    products=[ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
    fields_schema={
        "target_percent": {"type": "float", "default": 5.0, "title": "Target Profit (%)"},
    },
    required_data=["positions"],  # 시계열 데이터 불필요, positions만 필요
    # items { from, extract } 필수 필드 (v3.0.0+) - positions 사용 시 빈 배열
    required_fields=[],  # positions 플러그인은 items 불필요
    optional_fields=[],
    tags=["exit", "profit", "realtime"],
    output_fields={
        "pnl_rate": {"type": "float", "description": "Current P&L rate (%)"},
        "current_price": {"type": "float", "description": "Current market price"},
        "target_percent": {"type": "float", "description": "Profit target threshold (%)"},
        "reached": {"type": "bool", "description": "Whether profit target was reached (pnl_rate >= target_percent)"},
    },
    locales={
        "ko": {
            "name": "목표 수익률 (Profit Target)",
            "description": "보유 종목이 목표 수익률에 도달했는지 확인합니다. 예: 5% 이상 수익이 나면 매도하여 수익 실현.",
            "fields.target_percent": "목표 수익률 (%)",
        },
    },
)


async def profit_target_condition(
    positions: Optional[List[Dict[str, Any]]] = None,
    fields: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> dict:
    """
    익절 조건 플러그인

    Args:
        positions: RealAccountNode의 positions 출력 (list[dict])
                   [{"symbol": "AAPL", "pnl_rate": 6.3, "current_price": 150.0, ...}, ...]
        fields: {target_percent: 목표 수익률 %}

    Returns:
        passed_symbols: 목표 수익률 달성 종목
        failed_symbols: 미달성 종목
        symbol_results: 종목별 상세 결과
    """
    if fields is None:
        fields = {}

    target_percent = fields.get("target_percent", fields.get("percent", 5.0))

    positions = positions or []
    if not positions:
        return {
            "passed_symbols": [],
            "failed_symbols": [],
            "symbol_results": [],
            "values": [],
            "result": False,
            "error": "positions 데이터가 없습니다. RealAccountNode 또는 AccountNode의 positions를 연결하세요.",
        }

    passed, failed, symbol_results = [], [], []

    for pos_data in positions:
        symbol = pos_data.get("symbol")
        if not symbol:
            continue
        # positions에서 직접 pnl_rate 사용 (이미 계산되어 있음)
        pnl_rate = pos_data.get("pnl_rate", 0)
        current_price = pos_data.get("current_price", 0)
        exchange = pos_data.get("exchange") or pos_data.get("market_code", "UNKNOWN")

        exchange_map = {"81": "NYSE", "82": "NASDAQ", "83": "AMEX"}
        exchange_name = exchange_map.get(str(exchange), exchange)

        sym_dict = {"exchange": exchange_name, "symbol": symbol}

        symbol_results.append({
            "symbol": symbol,
            "exchange": exchange_name,
            "pnl_rate": round(pnl_rate, 2),
            "current_price": current_price,
            "target_percent": target_percent,
            "reached": pnl_rate >= target_percent,
        })

        if pnl_rate >= target_percent:
            passed.append(sym_dict)
        else:
            failed.append(sym_dict)

    return {
        "passed_symbols": passed,
        "failed_symbols": failed,
        "symbol_results": symbol_results,
        "values": [],  # 시계열 데이터 없음
        "result": len(passed) > 0,
        "analysis": {
            "indicator": "ProfitTarget",
            "target_percent": target_percent,
            "total_positions": len(positions),
            "reached_count": len(passed),
        },
    }


__all__ = ["profit_target_condition", "PROFIT_TARGET_SCHEMA"]
