"""live_bot custom plugins.

사용법:
    from plugins import register_all
    register_all()
"""

from programgarden_core.registry import PluginRegistry

from .scalable_trailing_stop import (
    SCHEMA as SCALABLE_TRAILING_STOP_SCHEMA,
    scalable_trailing_stop_condition,
    risk_features as scalable_trailing_stop_risk_features,
)


def register_all() -> None:
    registry = PluginRegistry()

    # 이미 등록됐으면 skip (reload 안전)
    if SCALABLE_TRAILING_STOP_SCHEMA.id not in registry._plugins:
        registry.register_dynamic(
            plugin_id=SCALABLE_TRAILING_STOP_SCHEMA.id,
            plugin_callable=scalable_trailing_stop_condition,
            schema=SCALABLE_TRAILING_STOP_SCHEMA,
        )

    # risk_features 전파 (plugin_registry가 이 속성을 읽어서 risk_tracker에 등록)
    # 모듈 레벨 risk_features 변수는 executor의 _collect_risk_features가 plugin 모듈을 조회해 수집
    import sys
    mod = sys.modules[__name__ + ".scalable_trailing_stop"]
    # executor가 plugin_registry._plugins[plugin_id][version] callable의 __module__ 로 찾으므로 별도 처리 불필요
    _ = mod


__all__ = ["register_all"]
