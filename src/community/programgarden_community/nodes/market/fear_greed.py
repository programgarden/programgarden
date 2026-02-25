"""
ProgramGarden Community - FearGreedIndexNode

CNN 공포/탐욕 지수 노드.
credential 불필요, 설정 없이 놓기만 하면 동작합니다.
시장 심리의 대표 지표 (0=극단적 공포, 100=극단적 탐욕).

사용 예시:
    {
        "id": "fgi",
        "type": "FearGreedIndexNode"
    }
"""

from typing import Optional, List, Literal, Dict, Any, ClassVar, Tuple, TYPE_CHECKING
from pydantic import Field

if TYPE_CHECKING:
    from programgarden_core.models.field_binding import FieldSchema

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
    RetryableError,
)
from programgarden_core.models.resilience import (
    ResilienceConfig,
    RetryConfig,
    FallbackConfig,
    FallbackMode,
)
from programgarden_core.models.connection_rule import (
    ConnectionRule,
    ConnectionSeverity,
    RateLimitConfig,
    REALTIME_SOURCE_NODE_TYPES,
)
from programgarden_core.nodes.market_external import (
    _fetch_json_with_fallback,
    _classify_retryable_error,
)


class FearGreedIndexNode(BaseNode):
    """
    CNN 공포/탐욕 지수 노드

    credential 불필요. 설정 없이 놓기만 하면 동작합니다.
    시장 심리의 대표 지표 (0=극단적 공포, 100=극단적 탐욕).

    Example DSL:
        {
            "id": "fgi",
            "type": "FearGreedIndexNode"
        }
    """

    type: Literal["FearGreedIndexNode"] = "FearGreedIndexNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.FearGreedIndexNode.description"
    _img_url: ClassVar[str] = "https://cdn.programgarden.io/nodes/feargreed.svg"

    # 실시간 노드에서 직접 연결 차단
    _connection_rules: ClassVar[List[ConnectionRule]] = [
        ConnectionRule(
            deny_direct_from=REALTIME_SOURCE_NODE_TYPES,
            required_intermediate="ThrottleNode",
            severity=ConnectionSeverity.WARNING,
            reason="i18n:connection_rules.realtime_to_external_api.reason",
            suggestion="i18n:connection_rules.realtime_to_external_api.suggestion",
        ),
    ]

    # L-2: CNN 비공식 API → 보수적 5분 간격
    _rate_limit: ClassVar[Optional[RateLimitConfig]] = RateLimitConfig(
        min_interval_sec=300,
        max_concurrent=1,
        on_throttle="queue",
    )

    # === SETTINGS ===
    timeout_seconds: int = Field(
        default=30,
        ge=5,
        le=120,
        description="i18n:fields.FearGreedIndexNode.timeout_seconds",
    )

    # === Resilience ===
    resilience: ResilienceConfig = Field(
        default_factory=lambda: ResilienceConfig(
            retry=RetryConfig(enabled=True, max_retries=3),
            fallback=FallbackConfig(mode=FallbackMode.ERROR),
        ),
        description="재시도 및 실패 처리 설정",
    )

    @classmethod
    def is_tool_enabled(cls) -> bool:
        return True

    _inputs: List[InputPort] = [
        InputPort(name="trigger", type="signal", description="i18n:ports.trigger", required=False),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="value", type="number", description="i18n:outputs.FearGreedIndexNode.value"),
        OutputPort(name="label", type="string", description="i18n:outputs.FearGreedIndexNode.label"),
        OutputPort(name="previous_close", type="number", description="i18n:outputs.FearGreedIndexNode.previous_close"),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import (
            FieldSchema, FieldType, FieldCategory, ExpressionMode, UIComponent,
        )
        return {
            "timeout_seconds": FieldSchema(
                name="timeout_seconds",
                type=FieldType.NUMBER,
                description="i18n:fields.FearGreedIndexNode.timeout_seconds",
                default=30,
                min=5,
                max=120,
                required=False,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
            ),
            "resilience": FieldSchema(
                name="resilience",
                type=FieldType.OBJECT,
                description="i18n:fields.FearGreedIndexNode.resilience",
                required=False,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                ui_component=UIComponent.CUSTOM_RESILIENCE_EDITOR,
                object_schema=[
                    {"name": "retry.enabled", "type": "BOOLEAN", "default": True, "description": "자동 재시도 활성화"},
                    {"name": "retry.max_retries", "type": "INTEGER", "default": 3, "min_value": 1, "max_value": 10, "description": "최대 재시도 횟수"},
                    {"name": "fallback.mode", "type": "ENUM", "default": "error", "enum_values": ["error", "skip", "default_value"], "description": "모든 재시도 실패 시 동작"},
                ],
                group="resilience",
            ),
        }

    async def execute(self, context: Any) -> Dict[str, Any]:
        """CNN 공포/탐욕 지수 조회 (L-1: 단일 provider, 대안 API 없음)"""
        _CNN_HEADERS = {
            "User-Agent": "Mozilla/5.0 (compatible; ProgramGarden/1.0)",
            "Accept": "application/json",
        }

        urls: List[Tuple[str, str, Optional[Dict[str, str]]]] = [
            (
                "https://production.dataviz.cnn.io/index/fearandgreed/graphdata",
                "CNN",
                _CNN_HEADERS,
            ),
        ]

        data = await _fetch_json_with_fallback(urls, self.timeout_seconds)

        # 응답 파싱
        fng = data.get("fear_and_greed", {})
        score = fng.get("score", 0)
        rating = fng.get("rating", "")
        previous_close = fng.get("previous_close", 0)

        # rating → label 매핑
        label = self._normalize_label(rating, score)

        return {
            "value": round(score, 1),
            "label": label,
            "previous_close": round(previous_close, 1) if previous_close else 0,
        }

    @staticmethod
    def _normalize_label(rating: str, score: float) -> str:
        """API rating 문자열을 표준 라벨로 정규화"""
        if rating:
            r = rating.lower().replace(" ", "_")
            label_map = {
                "extreme_fear": "Extreme Fear",
                "fear": "Fear",
                "neutral": "Neutral",
                "greed": "Greed",
                "extreme_greed": "Extreme Greed",
            }
            if r in label_map:
                return label_map[r]

        # rating이 없으면 score 기반 판별
        if score <= 25:
            return "Extreme Fear"
        elif score <= 45:
            return "Fear"
        elif score <= 55:
            return "Neutral"
        elif score <= 75:
            return "Greed"
        else:
            return "Extreme Greed"

    def is_retryable_error(self, error: Exception) -> Optional[RetryableError]:
        return _classify_retryable_error(error)
