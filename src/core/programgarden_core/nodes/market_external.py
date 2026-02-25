"""
ProgramGarden Core - External Market Data Nodes

credential 불필요, 무료 외부 API 기반 시장 데이터 노드:
- CurrencyRateNode: 환율 조회 (frankfurter.app, ECB 기반)

FearGreedIndexNode → community 패키지로 이동 (programgarden_community.nodes.market.fear_greed)
VIXDataNode → 삭제 (Yahoo Finance CDN 차단 위험, 사용처 없음)
"""

import logging
from typing import Optional, List, Literal, Dict, Any, ClassVar, Tuple, TYPE_CHECKING
from pydantic import Field

logger = logging.getLogger("programgarden_core.market_external")

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


class ExternalAPIError(Exception):
    """외부 API 서버 에러 - 재시도 가능"""
    pass


class ExternalAPIRateLimitError(Exception):
    """외부 API Rate Limit 에러 - 재시도 가능"""
    pass


class ExternalAPINetworkError(Exception):
    """네트워크 연결 에러 - 재시도 가능"""
    pass


class ExternalAPITimeoutError(Exception):
    """요청 타임아웃 에러 - 재시도 가능"""
    pass


# 공통 retryable error 판별 함수
def _classify_retryable_error(error: Exception) -> Optional[RetryableError]:
    """외부 API 에러가 재시도 가능한지 판별"""
    error_str = str(error).lower()

    if "timeout" in error_str or "timed out" in error_str:
        return RetryableError.TIMEOUT
    if "429" in error_str or "rate limit" in error_str:
        return RetryableError.RATE_LIMIT
    if "connection" in error_str or "network" in error_str or "unreachable" in error_str:
        return RetryableError.NETWORK_ERROR
    if any(code in error_str for code in ["500", "502", "503", "504"]):
        return RetryableError.SERVER_ERROR

    return None


async def _fetch_json_with_fallback(
    urls: List[Tuple[str, str, Optional[Dict[str, str]]]],
    timeout_seconds: int = 30,
) -> Dict[str, Any]:
    """
    URL 목록을 순차 시도하여 JSON 응답을 반환 (L-1: fallback provider).

    Args:
        urls: [(url, provider_name, headers), ...] 순서대로 시도
        timeout_seconds: 요청 타임아웃 (초)

    Returns:
        JSON 응답 dict

    Raises:
        ExternalAPIError 등: 모든 provider 실패 시 마지막 에러 raise
    """
    import aiohttp
    import asyncio

    last_error: Optional[Exception] = None

    for i, (url, provider, headers) in enumerate(urls):
        try:
            timeout = aiohttp.ClientTimeout(total=timeout_seconds)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 429:
                        raise ExternalAPIRateLimitError(
                            f"[{provider}] HTTP 429: Rate limit exceeded"
                        )
                    if resp.status >= 500:
                        raise ExternalAPIError(
                            f"[{provider}] HTTP {resp.status}: Server error"
                        )
                    if resp.status >= 400:
                        text = await resp.text()
                        raise ExternalAPIError(
                            f"[{provider}] HTTP {resp.status}: {text[:200]}"
                        )

                    try:
                        data = await resp.json()
                    except (ValueError, Exception) as je:
                        text = await resp.text()
                        raise ExternalAPIError(
                            f"[{provider}] JSON parse failed: {je} (response: {text[:200]})"
                        )

            return data

        except (ExternalAPIRateLimitError, ExternalAPIError, ExternalAPINetworkError, ExternalAPITimeoutError) as e:
            last_error = e
            if i < len(urls) - 1:
                next_provider = urls[i + 1][1]
                logger.warning(
                    "%s 실패 (%s), fallback으로 %s 시도",
                    provider, e, next_provider,
                )
                continue
            raise

        except aiohttp.ClientError as e:
            last_error = ExternalAPINetworkError(f"[{provider}] Network error: {e}")
            if i < len(urls) - 1:
                next_provider = urls[i + 1][1]
                logger.warning(
                    "%s 네트워크 에러 (%s), fallback으로 %s 시도",
                    provider, e, next_provider,
                )
                continue
            raise last_error

        except asyncio.TimeoutError:
            last_error = ExternalAPITimeoutError(
                f"[{provider}] Request timeout after {timeout_seconds}s"
            )
            if i < len(urls) - 1:
                next_provider = urls[i + 1][1]
                logger.warning(
                    "%s 타임아웃 (%ds), fallback으로 %s 시도",
                    provider, timeout_seconds, next_provider,
                )
                continue
            raise last_error

    # unreachable, but for type safety
    raise last_error or ExternalAPIError("No providers available")


class CurrencyRateNode(BaseNode):
    """
    환율 조회 노드 (frankfurter.app, ECB 기반)

    credential 불필요. 기준 통화 대비 대상 통화의 환율을 조회합니다.
    해외투자 시 환율 변동 감지 및 전략 조정에 활용합니다.

    Example DSL:
        {
            "id": "fx",
            "type": "CurrencyRateNode",
            "base_currency": "USD",
            "target_currencies": ["KRW", "JPY"]
        }
    """

    type: Literal["CurrencyRateNode"] = "CurrencyRateNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.CurrencyRateNode.description"
    _img_url: ClassVar[str] = "https://cdn.programgarden.io/nodes/currency.svg"

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

    # L-2: ECB 환율은 하루 1회 업데이트 → 30초 간격이면 충분
    _rate_limit: ClassVar[Optional[RateLimitConfig]] = RateLimitConfig(
        min_interval_sec=30,
        max_concurrent=1,
        on_throttle="queue",
    )

    # === PARAMETERS ===
    base_currency: str = Field(
        default="USD",
        description="기준 통화 (USD, EUR, JPY 등)",
    )
    target_currencies: List[str] = Field(
        default_factory=lambda: ["KRW"],
        description="대상 통화 목록",
    )

    # === SETTINGS ===
    timeout_seconds: int = Field(
        default=30,
        ge=5,
        le=120,
        description="i18n:fields.CurrencyRateNode.timeout_seconds",
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
        OutputPort(name="rates", type="array", description="i18n:outputs.CurrencyRateNode.rates"),
        OutputPort(name="krw_rate", type="number", description="i18n:outputs.CurrencyRateNode.krw_rate"),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import (
            FieldSchema, FieldType, FieldCategory, ExpressionMode, UIComponent,
        )
        return {
            "base_currency": FieldSchema(
                name="base_currency",
                type=FieldType.ENUM,
                description="i18n:fields.CurrencyRateNode.base_currency",
                default="USD",
                required=True,
                enum_values=["USD", "EUR", "JPY", "GBP", "CHF", "CAD", "AUD", "CNY", "HKD", "SGD", "KRW"],
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
            ),
            "target_currencies": FieldSchema(
                name="target_currencies",
                type=FieldType.ARRAY,
                array_item_type=FieldType.STRING,
                description="i18n:fields.CurrencyRateNode.target_currencies",
                default=["KRW"],
                required=True,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                ui_options={
                    "multiple": True,
                    "options": ["KRW", "USD", "EUR", "JPY", "GBP", "CHF", "CAD", "AUD", "CNY", "HKD", "SGD"],
                },
                expected_type="list[str]",
            ),
            "timeout_seconds": FieldSchema(
                name="timeout_seconds",
                type=FieldType.NUMBER,
                description="i18n:fields.CurrencyRateNode.timeout_seconds",
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
                description="i18n:fields.CurrencyRateNode.resilience",
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
        """환율 데이터 조회 (L-1: fallback provider 지원)"""
        targets = ",".join(self.target_currencies)

        # L-1: Primary (frankfurter.app) → Fallback (open.er-api.com)
        urls: List[Tuple[str, str, Optional[Dict[str, str]]]] = [
            (
                f"https://api.frankfurter.app/latest?from={self.base_currency}&to={targets}",
                "frankfurter.app",
                None,
            ),
            (
                f"https://open.er-api.com/v6/latest/{self.base_currency}",
                "open.er-api.com",
                None,
            ),
        ]

        data = await _fetch_json_with_fallback(urls, self.timeout_seconds)

        # 응답 파싱 (provider별 형식 차이 처리)
        if "rates" in data and "date" in data:
            # frankfurter.app 형식: {"amount":1.0, "base":"USD", "date":"...", "rates":{"KRW":1449}}
            api_rates = data.get("rates", {})
            date_str = data.get("date", "")
        elif "rates" in data and "time_last_update_utc" in data:
            # open.er-api.com 형식: {"base":"USD", "rates":{"KRW":1449}, "time_last_update_utc":"..."}
            all_rates = data.get("rates", {})
            # open.er-api.com은 모든 통화를 반환 → target만 필터링
            api_rates = {k: v for k, v in all_rates.items() if k in self.target_currencies}
            date_str = data.get("time_last_update_utc", "")
        else:
            api_rates = data.get("rates", {})
            date_str = ""

        rates = []
        krw_rate = None
        for target, rate in api_rates.items():
            rates.append({
                "base": self.base_currency,
                "target": target,
                "rate": rate,
                "timestamp": date_str,
            })
            if target == "KRW":
                krw_rate = rate

        # KRW가 target에 없으면 0
        if krw_rate is None:
            krw_rate = 0

        return {
            "rates": rates,
            "krw_rate": krw_rate,
        }

    def is_retryable_error(self, error: Exception) -> Optional[RetryableError]:
        return _classify_retryable_error(error)


