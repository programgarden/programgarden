"""
동적 플러그인 예제 10종

기존 community 플러그인 패턴을 따른 register_dynamic() 예제.
ConditionNode의 plugin 필드로 참조하여 워크플로우에서 사용 가능.

사용법:
    from programgarden_core.registry import PluginRegistry
    from examples.dynamic_plugins import register_all

    register_all()  # 10종 일괄 등록

카테고리별 구성:
  TECHNICAL (7종): SimpleRSI, SimpleMACD, SimpleBollinger, SimpleMACross,
                   SimpleVolumeSpike, SimpleDoji, SimpleATR
  POSITION  (3종): SimpleStopLoss, SimpleProfitTarget, SimpleTrailingStop
"""
