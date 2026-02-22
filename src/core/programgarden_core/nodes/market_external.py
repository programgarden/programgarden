"""
ProgramGarden Core - External Market Data Nodes

credential 불필요, 무료 외부 API 기반 시장 데이터 노드:
- CurrencyRateNode: 환율 조회 (frankfurter.app, ECB 기반)
- FearGreedIndexNode: CNN 공포/탐욕 지수
- VIXDataNode: CBOE VIX 변동성 지수 (Yahoo Finance)
"""

from typing import Optional, List, Literal, Dict, Any, ClassVar, TYPE_CHECKING
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

    # Rate limit: 1분 간격
    _rate_limit: ClassVar[Optional[RateLimitConfig]] = RateLimitConfig(
        min_interval_sec=60,
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
        """환율 데이터 조회"""
        import aiohttp
        import asyncio

        targets = ",".join(self.target_currencies)
        url = f"https://api.frankfurter.app/latest?from={self.base_currency}&to={targets}"

        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as resp:
                    if resp.status == 429:
                        raise ExternalAPIRateLimitError("HTTP 429: Rate limit exceeded")
                    if resp.status >= 500:
                        raise ExternalAPIError(f"HTTP {resp.status}: Server error")
                    if resp.status >= 400:
                        text = await resp.text()
                        raise ExternalAPIError(f"HTTP {resp.status}: {text[:200]}")

                    data = await resp.json()

        except (ExternalAPIError, ExternalAPIRateLimitError, ExternalAPINetworkError, ExternalAPITimeoutError):
            raise
        except aiohttp.ClientError as e:
            raise ExternalAPINetworkError(f"Network error: {e}")
        except asyncio.TimeoutError:
            raise ExternalAPITimeoutError("Request timeout after 30s")

        # 응답 파싱: {"amount":1.0, "base":"USD", "date":"2026-02-20", "rates":{"KRW":1449.66}}
        api_rates = data.get("rates", {})
        date_str = data.get("date", "")

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

    # Rate limit: 1분 간격
    _rate_limit: ClassVar[Optional[RateLimitConfig]] = RateLimitConfig(
        min_interval_sec=60,
        max_concurrent=1,
        on_throttle="queue",
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
        """CNN 공포/탐욕 지수 조회"""
        import aiohttp
        import asyncio

        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; ProgramGarden/1.0)",
            "Accept": "application/json",
        }

        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 429:
                        raise ExternalAPIRateLimitError("HTTP 429: Rate limit exceeded")
                    if resp.status >= 500:
                        raise ExternalAPIError(f"HTTP {resp.status}: Server error")
                    if resp.status >= 400:
                        text = await resp.text()
                        raise ExternalAPIError(f"HTTP {resp.status}: {text[:200]}")

                    data = await resp.json()

        except (ExternalAPIError, ExternalAPIRateLimitError, ExternalAPINetworkError, ExternalAPITimeoutError):
            raise
        except aiohttp.ClientError as e:
            raise ExternalAPINetworkError(f"Network error: {e}")
        except asyncio.TimeoutError:
            raise ExternalAPITimeoutError("Request timeout after 30s")

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


class VIXDataNode(BaseNode):
    """
    CBOE VIX 변동성 지수 노드 (Yahoo Finance)

    credential 불필요. VIX 지수를 조회합니다.
    VIX > 30 = 시장 공포 구간 → 포지션 사이징 축소/헤지에 활용.

    Example DSL:
        {
            "id": "vix",
            "type": "VIXDataNode",
            "include_history": true
        }
    """

    type: Literal["VIXDataNode"] = "VIXDataNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.VIXDataNode.description"
    _img_url: ClassVar[str] = "https://cdn.programgarden.io/nodes/vix.svg"

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

    # Rate limit: 1분 간격
    _rate_limit: ClassVar[Optional[RateLimitConfig]] = RateLimitConfig(
        min_interval_sec=60,
        max_concurrent=1,
        on_throttle="queue",
    )

    # === SETTINGS ===
    include_history: bool = Field(
        default=False,
        description="최근 이력 포함 여부",
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
        OutputPort(name="vix", type="number", description="i18n:outputs.VIXDataNode.vix"),
        OutputPort(name="level", type="string", description="i18n:outputs.VIXDataNode.level"),
        OutputPort(name="history", type="array", description="i18n:outputs.VIXDataNode.history"),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import (
            FieldSchema, FieldType, FieldCategory, ExpressionMode, UIComponent,
        )
        return {
            "include_history": FieldSchema(
                name="include_history",
                type=FieldType.BOOLEAN,
                description="i18n:fields.VIXDataNode.include_history",
                default=False,
                required=False,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                ui_component=UIComponent.CHECKBOX,
                expected_type="bool",
            ),
            "resilience": FieldSchema(
                name="resilience",
                type=FieldType.OBJECT,
                description="i18n:fields.VIXDataNode.resilience",
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
        """VIX 지수 조회"""
        import aiohttp
        import asyncio
        from datetime import datetime, timezone

        # Yahoo Finance 비공식 API
        range_param = "1mo" if self.include_history else "5d"
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX?range={range_param}&interval=1d"
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; ProgramGarden/1.0)",
        }

        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 429:
                        raise ExternalAPIRateLimitError("HTTP 429: Rate limit exceeded")
                    if resp.status >= 500:
                        raise ExternalAPIError(f"HTTP {resp.status}: Server error")
                    if resp.status >= 400:
                        text = await resp.text()
                        raise ExternalAPIError(f"HTTP {resp.status}: {text[:200]}")

                    data = await resp.json()

        except (ExternalAPIError, ExternalAPIRateLimitError, ExternalAPINetworkError, ExternalAPITimeoutError):
            raise
        except aiohttp.ClientError as e:
            raise ExternalAPINetworkError(f"Network error: {e}")
        except asyncio.TimeoutError:
            raise ExternalAPITimeoutError("Request timeout after 30s")

        # 응답 파싱
        result = data.get("chart", {}).get("result", [])
        if not result:
            raise ExternalAPIError("Empty response from Yahoo Finance")

        chart_data = result[0]
        meta = chart_data.get("meta", {})
        current_vix = meta.get("regularMarketPrice", 0)

        # VIX 레벨 판별
        level = self._classify_vix_level(current_vix)

        # 이력 데이터
        history = []
        if self.include_history:
            timestamps = chart_data.get("timestamp", [])
            indicators = chart_data.get("indicators", {})
            quotes = indicators.get("quote", [{}])[0] if indicators.get("quote") else {}
            closes = quotes.get("close", [])

            for i, ts in enumerate(timestamps):
                if i < len(closes) and closes[i] is not None:
                    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                    history.append({
                        "date": dt.strftime("%Y-%m-%d"),
                        "close": round(closes[i], 2),
                    })

        return {
            "vix": round(current_vix, 2),
            "level": level,
            "history": history,
        }

    @staticmethod
    def _classify_vix_level(vix: float) -> str:
        """VIX 값을 레벨로 분류"""
        if vix < 15:
            return "low"
        elif vix < 25:
            return "moderate"
        elif vix < 35:
            return "high"
        else:
            return "extreme"

    def is_retryable_error(self, error: Exception) -> Optional[RetryableError]:
        return _classify_retryable_error(error)
