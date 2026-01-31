"""
ProgramGarden Community - 플러그인 레지스트리

플러그인 자동 로딩 및 등록을 담당합니다.

폴더 구조:
    plugins/
    ├── rsi/              # TECHNICAL - RSI 지표
    ├── macd/             # TECHNICAL - MACD 지표
    ├── bollinger_bands/  # TECHNICAL - 볼린저밴드
    ├── volume_spike/     # TECHNICAL - 거래량 급증
    ├── ma_cross/         # TECHNICAL - 이동평균 크로스
    ├── dual_momentum/    # TECHNICAL - 듀얼 모멘텀
    ├── stochastic/       # TECHNICAL - 스토캐스틱
    ├── atr/              # TECHNICAL - ATR
    ├── price_channel/    # TECHNICAL - 가격 채널 (돈치안)
    ├── stop_loss/        # POSITION - 손절
    ├── profit_target/    # POSITION - 익절
    └── trailing_stop/    # POSITION - 트레일링 스탑

사용법:
    from programgarden_community.plugins import register_all_plugins, get_plugin

    register_all_plugins()
    schema = get_plugin("RSI")
"""

from typing import Optional, Dict, Any


def register_all_plugins() -> None:
    """
    모든 플러그인을 PluginRegistry에 등록합니다.
    """
    from programgarden_core.registry import PluginRegistry

    registry = PluginRegistry()

    # === TECHNICAL 플러그인 ===
    from .rsi import RSI_SCHEMA, rsi_condition
    from .macd import MACD_SCHEMA, macd_condition
    from .bollinger_bands import BOLLINGER_SCHEMA, bollinger_condition
    from .volume_spike import VOLUME_SPIKE_SCHEMA, volume_spike_condition
    from .ma_cross import MA_CROSS_SCHEMA, ma_cross_condition
    from .dual_momentum import DUAL_MOMENTUM_SCHEMA, dual_momentum_condition
    from .stochastic import STOCHASTIC_SCHEMA, stochastic_condition
    from .atr import ATR_SCHEMA, atr_condition
    from .price_channel import PRICE_CHANNEL_SCHEMA, price_channel_condition
    from .adx import ADX_SCHEMA, adx_condition
    from .obv import OBV_SCHEMA, obv_condition

    # === POSITION 플러그인 ===
    from .stop_loss import STOP_LOSS_SCHEMA, stop_loss_condition
    from .profit_target import PROFIT_TARGET_SCHEMA, profit_target_condition
    from .trailing_stop import TRAILING_STOP_SCHEMA, trailing_stop_condition

    # TECHNICAL 등록
    technical_plugins = [
        ("RSI", rsi_condition, RSI_SCHEMA),
        ("MACD", macd_condition, MACD_SCHEMA),
        ("BollingerBands", bollinger_condition, BOLLINGER_SCHEMA),
        ("VolumeSpike", volume_spike_condition, VOLUME_SPIKE_SCHEMA),
        ("MovingAverageCross", ma_cross_condition, MA_CROSS_SCHEMA),
        ("DualMomentum", dual_momentum_condition, DUAL_MOMENTUM_SCHEMA),
        ("Stochastic", stochastic_condition, STOCHASTIC_SCHEMA),
        ("ATR", atr_condition, ATR_SCHEMA),
        ("PriceChannel", price_channel_condition, PRICE_CHANNEL_SCHEMA),
        ("ADX", adx_condition, ADX_SCHEMA),
        ("OBV", obv_condition, OBV_SCHEMA),
    ]

    # POSITION 등록
    position_plugins = [
        ("StopLoss", stop_loss_condition, STOP_LOSS_SCHEMA),
        ("ProfitTarget", profit_target_condition, PROFIT_TARGET_SCHEMA),
        ("TrailingStop", trailing_stop_condition, TRAILING_STOP_SCHEMA),
    ]

    for plugin_id, plugin_callable, schema in technical_plugins + position_plugins:
        try:
            registry.register(
                plugin_id=plugin_id,
                plugin_callable=plugin_callable,
                schema=schema,
            )
        except ValueError:
            # 이미 등록된 경우 무시
            pass


def get_plugin(plugin_id: str) -> Optional[Dict[str, Any]]:
    """
    플러그인 스키마 조회

    Args:
        plugin_id: 플러그인 ID (예: "RSI", "MACD")

    Returns:
        플러그인 스키마 dict 또는 None
    """
    from programgarden_core.registry import PluginRegistry

    registry = PluginRegistry()
    schema = registry.get_schema(plugin_id)

    if schema:
        return {
            "id": schema.id,
            "name": schema.name,
            "category": schema.category.value if hasattr(schema.category, 'value') else schema.category,
            "version": schema.version,
            "description": schema.description,
            "products": [p.value if hasattr(p, 'value') else p for p in schema.products],
            "fields_schema": schema.fields_schema,
            "required_data": schema.required_data,
            "tags": schema.tags,
        }
    return None


def list_plugins(
    category: Optional[str] = None,
    product: Optional[str] = None,
) -> Dict[str, list]:
    """
    플러그인 목록 조회

    Args:
        category: 필터링할 카테고리 (technical, position)
        product: 필터링할 상품 (overseas_stock, overseas_futures 등)

    Returns:
        카테고리별 플러그인 ID 목록
    """
    from programgarden_core.registry import PluginRegistry

    registry = PluginRegistry()
    return registry.list_plugins(category=category, product=product)


__all__ = [
    "register_all_plugins",
    "get_plugin",
    "list_plugins",
]
