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
    ├── golden_ratio/     # TECHNICAL - 피보나치 되돌림
    ├── pivot_point/      # TECHNICAL - 피봇 포인트
    ├── mean_reversion/   # TECHNICAL - 평균 회귀
    ├── breakout_retest/  # TECHNICAL - 돌파 후 되돌림
    ├── three_line_strike/ # TECHNICAL - 삼선 타격
    ├── ichimoku_cloud/   # TECHNICAL - 일목균형표
    ├── vwap/             # TECHNICAL - VWAP
    ├── parabolic_sar/    # TECHNICAL - 파라볼릭 SAR
    ├── williams_r/       # TECHNICAL - 윌리엄스 %R
    ├── cci/              # TECHNICAL - CCI
    ├── supertrend/       # TECHNICAL - 슈퍼트렌드
    ├── keltner_channel/  # TECHNICAL - 켈트너 채널
    ├── trix/             # TECHNICAL - TRIX
    ├── cmf/              # TECHNICAL - 차이킨 자금흐름
    ├── engulfing/        # TECHNICAL - 장악형 패턴
    ├── hammer_shooting_star/ # TECHNICAL - 망치/유성형
    ├── doji/             # TECHNICAL - 도지
    ├── morning_evening_star/ # TECHNICAL - 샛별/석별형
    ├── stop_loss/        # POSITION - 손절
    ├── profit_target/    # POSITION - 익절
    ├── trailing_stop/    # POSITION - 트레일링 스탑
    ├── partial_take_profit/ # POSITION - 분할 익절
    └── time_based_exit/  # POSITION - 시간 기반 청산

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
    from .golden_ratio import GOLDEN_RATIO_SCHEMA, golden_ratio_condition
    from .pivot_point import PIVOT_POINT_SCHEMA, pivot_point_condition
    from .mean_reversion import MEAN_REVERSION_SCHEMA, mean_reversion_condition
    from .breakout_retest import BREAKOUT_RETEST_SCHEMA, breakout_retest_condition
    from .three_line_strike import THREE_LINE_STRIKE_SCHEMA, three_line_strike_condition
    from .ichimoku_cloud import ICHIMOKU_CLOUD_SCHEMA, ichimoku_cloud_condition
    from .vwap import VWAP_SCHEMA, vwap_condition
    from .parabolic_sar import PARABOLIC_SAR_SCHEMA, parabolic_sar_condition
    from .williams_r import WILLIAMS_R_SCHEMA, williams_r_condition
    from .cci import CCI_SCHEMA, cci_condition
    from .supertrend import SUPERTREND_SCHEMA, supertrend_condition
    from .keltner_channel import KELTNER_CHANNEL_SCHEMA, keltner_channel_condition
    from .trix import TRIX_SCHEMA, trix_condition
    from .cmf import CMF_SCHEMA, cmf_condition
    from .engulfing import ENGULFING_SCHEMA, engulfing_condition
    from .hammer_shooting_star import HAMMER_SHOOTING_STAR_SCHEMA, hammer_shooting_star_condition
    from .doji import DOJI_SCHEMA, doji_condition
    from .morning_evening_star import MORNING_EVENING_STAR_SCHEMA, morning_evening_star_condition

    # === POSITION 플러그인 ===
    from .stop_loss import STOP_LOSS_SCHEMA, stop_loss_condition
    from .profit_target import PROFIT_TARGET_SCHEMA, profit_target_condition
    from .trailing_stop import TRAILING_STOP_SCHEMA, trailing_stop_condition
    from .partial_take_profit import PARTIAL_TAKE_PROFIT_SCHEMA, partial_take_profit_condition
    from .time_based_exit import TIME_BASED_EXIT_SCHEMA, time_based_exit_condition

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
        ("GoldenRatio", golden_ratio_condition, GOLDEN_RATIO_SCHEMA),
        ("PivotPoint", pivot_point_condition, PIVOT_POINT_SCHEMA),
        ("MeanReversion", mean_reversion_condition, MEAN_REVERSION_SCHEMA),
        ("BreakoutRetest", breakout_retest_condition, BREAKOUT_RETEST_SCHEMA),
        ("ThreeLineStrike", three_line_strike_condition, THREE_LINE_STRIKE_SCHEMA),
        ("IchimokuCloud", ichimoku_cloud_condition, ICHIMOKU_CLOUD_SCHEMA),
        ("VWAP", vwap_condition, VWAP_SCHEMA),
        ("ParabolicSAR", parabolic_sar_condition, PARABOLIC_SAR_SCHEMA),
        ("WilliamsR", williams_r_condition, WILLIAMS_R_SCHEMA),
        ("CCI", cci_condition, CCI_SCHEMA),
        ("Supertrend", supertrend_condition, SUPERTREND_SCHEMA),
        ("KeltnerChannel", keltner_channel_condition, KELTNER_CHANNEL_SCHEMA),
        ("TRIX", trix_condition, TRIX_SCHEMA),
        ("CMF", cmf_condition, CMF_SCHEMA),
        ("Engulfing", engulfing_condition, ENGULFING_SCHEMA),
        ("HammerShootingStar", hammer_shooting_star_condition, HAMMER_SHOOTING_STAR_SCHEMA),
        ("Doji", doji_condition, DOJI_SCHEMA),
        ("MorningEveningStar", morning_evening_star_condition, MORNING_EVENING_STAR_SCHEMA),
    ]

    # POSITION 등록
    position_plugins = [
        ("StopLoss", stop_loss_condition, STOP_LOSS_SCHEMA),
        ("ProfitTarget", profit_target_condition, PROFIT_TARGET_SCHEMA),
        ("TrailingStop", trailing_stop_condition, TRAILING_STOP_SCHEMA),
        ("PartialTakeProfit", partial_take_profit_condition, PARTIAL_TAKE_PROFIT_SCHEMA),
        ("TimeBasedExit", time_based_exit_condition, TIME_BASED_EXIT_SCHEMA),
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
