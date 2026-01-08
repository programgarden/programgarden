"""
Strategy Conditions - 전략 조건 플러그인

ConditionNode에서 사용하는 조건 플러그인을 등록합니다.
각 플러그인은 매수/매도 신호를 생성합니다.

플러그인 목록:
- RSI: RSI 과매수/과매도 조건
- MACD: MACD 크로스오버 조건
- BollingerBands: 볼린저밴드 이탈 조건
- VolumeSpike: 거래량 급증 조건
- ProfitTarget: 목표 수익률 도달 (익절)
- StopLoss: 손절 조건
- MovingAverageCross: 이동평균선 골든/데드 크로스
- DualMomentum: 듀얼 모멘텀 (절대+상대)
"""

from typing import Optional, List


def register_strategy_condition_plugins() -> None:
    """전략 조건 플러그인 등록"""
    from programgarden_core.registry import PluginRegistry, PluginSchema
    from programgarden_core.registry.plugin_registry import PluginCategory, ProductType
    
    registry = PluginRegistry()
    
    # === RSI ===
    from .rsi import rsi_condition, RSI_SCHEMA
    registry.register(
        plugin_id="RSI",
        plugin_callable=rsi_condition,
        schema=RSI_SCHEMA,
    )
    
    # === MACD ===
    from .macd import macd_condition, MACD_SCHEMA
    registry.register(
        plugin_id="MACD",
        plugin_callable=macd_condition,
        schema=MACD_SCHEMA,
    )
    
    # === BollingerBands ===
    from .bollinger_bands import bollinger_condition, BOLLINGER_SCHEMA
    registry.register(
        plugin_id="BollingerBands",
        plugin_callable=bollinger_condition,
        schema=BOLLINGER_SCHEMA,
    )
    
    # === VolumeSpike ===
    from .volume_spike import volume_spike_condition, VOLUME_SPIKE_SCHEMA
    registry.register(
        plugin_id="VolumeSpike",
        plugin_callable=volume_spike_condition,
        schema=VOLUME_SPIKE_SCHEMA,
    )
    
    # === ProfitTarget ===
    from .profit_target import profit_target_condition, PROFIT_TARGET_SCHEMA
    registry.register(
        plugin_id="ProfitTarget",
        plugin_callable=profit_target_condition,
        schema=PROFIT_TARGET_SCHEMA,
    )
    
    # === StopLoss ===
    from .stop_loss import stop_loss_condition, STOP_LOSS_SCHEMA
    registry.register(
        plugin_id="StopLoss",
        plugin_callable=stop_loss_condition,
        schema=STOP_LOSS_SCHEMA,
    )
    
    # === MovingAverageCross ===
    from .ma_cross import ma_cross_condition, MA_CROSS_SCHEMA
    registry.register(
        plugin_id="MovingAverageCross",
        plugin_callable=ma_cross_condition,
        schema=MA_CROSS_SCHEMA,
    )
    
    # === DualMomentum ===
    from .dual_momentum import dual_momentum_condition, DUAL_MOMENTUM_SCHEMA
    registry.register(
        plugin_id="DualMomentum",
        plugin_callable=dual_momentum_condition,
        schema=DUAL_MOMENTUM_SCHEMA,
    )


__all__ = ["register_strategy_condition_plugins"]
