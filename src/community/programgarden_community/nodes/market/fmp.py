"""
ProgramGarden Community - FundamentalDataNode (FMP API)

Financial Modeling Prep API를 활용하여 해외주식 재무 데이터를 조회하는 노드.
credential 기반 API 키 관리.

사용 예시:
    {
        "id": "fundamental",
        "type": "FundamentalDataNode",
        "credential_id": "fmp-cred",
        "symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}],
        "data_type": "profile"
    }

    credential "fmp-cred":
        {"api_key": "your_fmp_api_key_here"}
"""

import logging
from typing import Optional, List, Literal, Dict, Any, ClassVar, Tuple, TYPE_CHECKING
from pydantic import Field

logger = logging.getLogger("programgarden_community.nodes.market.fmp")

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
    _classify_retryable_error,
    ExternalAPIError,
    ExternalAPIRateLimitError,
    ExternalAPINetworkError,
    ExternalAPITimeoutError,
)


# FMP API base URL
_FMP_BASE_URL = "https://financialmodelingprep.com/api/v3"


class FundamentalDataNode(BaseNode):
    """
    해외주식 재무 데이터 조회 노드 (FMP API)

    Financial Modeling Prep API를 사용하여 기업 프로필, 재무제표,
    핵심 지표 등을 조회합니다. API 키가 필요합니다.

    Example DSL:
        {
            "id": "fundamental",
            "type": "FundamentalDataNode",
            "credential_id": "fmp-cred",
            "symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}],
            "data_type": "profile"
        }
    """

    type: Literal["FundamentalDataNode"] = "FundamentalDataNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.FundamentalDataNode.description"
    _img_url: ClassVar[str] = "https://cdn.programgarden.io/nodes/fundamental.svg"

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

    # L-2: FMP 무료 250건/일 → 60초 간격
    _rate_limit: ClassVar[Optional[RateLimitConfig]] = RateLimitConfig(
        min_interval_sec=60,
        max_concurrent=1,
        on_throttle="queue",
    )

    # === PARAMETERS ===
    credential_id: Optional[str] = Field(
        default=None,
        description="i18n:fields.FundamentalDataNode.credential_id",
    )
    symbols: List[Dict[str, str]] = Field(
        default_factory=list,
        description="i18n:fields.FundamentalDataNode.symbols",
    )
    data_type: str = Field(
        default="profile",
        description="i18n:fields.FundamentalDataNode.data_type",
    )
    period: str = Field(
        default="annual",
        description="i18n:fields.FundamentalDataNode.period",
    )
    limit: int = Field(
        default=1,
        ge=1,
        le=10,
        description="i18n:fields.FundamentalDataNode.limit",
    )

    # === SETTINGS ===
    timeout_seconds: int = Field(
        default=30,
        ge=5,
        le=120,
        description="i18n:fields.FundamentalDataNode.timeout_seconds",
    )

    # === Resilience ===
    resilience: ResilienceConfig = Field(
        default_factory=lambda: ResilienceConfig(
            retry=RetryConfig(enabled=True, max_retries=3),
            fallback=FallbackConfig(mode=FallbackMode.ERROR),
        ),
        description="재시도 및 실패 처리 설정",
    )

    # Credential에서 주입되는 API 키 (내부용)
    _api_key: Optional[str] = None

    @classmethod
    def is_tool_enabled(cls) -> bool:
        return True

    _inputs: List[InputPort] = [
        InputPort(name="trigger", type="signal", description="i18n:ports.trigger", required=False),
        InputPort(name="symbols", type="array", description="i18n:inputs.FundamentalDataNode.symbols", required=False),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="data", type="array", description="i18n:outputs.FundamentalDataNode.data"),
        OutputPort(name="summary", type="object", description="i18n:outputs.FundamentalDataNode.summary"),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import (
            FieldSchema, FieldType, FieldCategory, ExpressionMode, UIComponent,
        )
        return {
            "credential_id": FieldSchema(
                name="credential_id",
                type=FieldType.STRING,
                description="i18n:fields.FundamentalDataNode.credential_id",
                required=True,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                ui_component=UIComponent.CUSTOM_CREDENTIAL_SELECT,
                expected_type="str",
            ),
            "symbols": FieldSchema(
                name="symbols",
                type=FieldType.ARRAY,
                description="i18n:fields.FundamentalDataNode.symbols",
                required=True,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
                expected_type="list[dict]",
            ),
            "data_type": FieldSchema(
                name="data_type",
                type=FieldType.ENUM,
                description="i18n:fields.FundamentalDataNode.data_type",
                default="profile",
                required=True,
                enum_values=["profile", "income_statement", "balance_sheet", "key_metrics"],
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
            ),
            "period": FieldSchema(
                name="period",
                type=FieldType.ENUM,
                description="i18n:fields.FundamentalDataNode.period",
                default="annual",
                required=False,
                enum_values=["annual", "quarter"],
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
            ),
            "limit": FieldSchema(
                name="limit",
                type=FieldType.NUMBER,
                description="i18n:fields.FundamentalDataNode.limit",
                default=1,
                min=1,
                max=10,
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
            ),
            "timeout_seconds": FieldSchema(
                name="timeout_seconds",
                type=FieldType.NUMBER,
                description="i18n:fields.FundamentalDataNode.timeout_seconds",
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
                description="i18n:fields.FundamentalDataNode.resilience",
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
        """FMP API를 통한 재무 데이터 조회"""
        import aiohttp
        import asyncio

        # API 키 확인 (credential에서 주입됨)
        api_key = self._api_key
        if not api_key:
            raise ExternalAPIError("FMP API key not provided. Set credential_id with fmp_api type.")

        if not self.symbols:
            raise ExternalAPIError("No symbols specified for FundamentalDataNode.")

        # 심볼 목록 추출
        symbol_list = [s["symbol"] for s in self.symbols if "symbol" in s]
        if not symbol_list:
            raise ExternalAPIError("No valid symbols found in symbols list.")

        # data_type별 API 호출
        all_data = []
        timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)

        if self.data_type == "profile":
            # profile은 일괄 조회 가능 (최대 5종목)
            all_data = await self._fetch_profile(symbol_list, api_key, timeout)
        elif self.data_type == "key_metrics":
            all_data = await self._fetch_key_metrics(symbol_list, api_key, timeout)
        elif self.data_type == "income_statement":
            all_data = await self._fetch_financial_statement(
                symbol_list, api_key, timeout, "income-statement"
            )
        elif self.data_type == "balance_sheet":
            all_data = await self._fetch_financial_statement(
                symbol_list, api_key, timeout, "balance-sheet-statement"
            )
        else:
            raise ExternalAPIError(f"Unknown data_type: {self.data_type}")

        # summary 생성
        summary = {
            "data_type": self.data_type,
            "symbol_count": len(symbol_list),
            "record_count": len(all_data),
        }

        return {
            "data": all_data,
            "summary": summary,
        }

    async def _fetch_profile(
        self, symbols: List[str], api_key: str, timeout: Any
    ) -> List[Dict[str, Any]]:
        """기업 프로필 조회 (일괄 조회 가능)"""
        import aiohttp
        import asyncio

        results = []
        # 5종목씩 배치 (FMP 일괄 조회 한도)
        for i in range(0, len(symbols), 5):
            batch = symbols[i:i + 5]
            joined = ",".join(batch)
            url = f"{_FMP_BASE_URL}/profile/{joined}?apikey={api_key}"

            data = await self._fetch_api(url, timeout)

            if isinstance(data, list):
                for item in data:
                    results.append(self._normalize_profile(item))
            elif isinstance(data, dict):
                results.append(self._normalize_profile(data))

            # 배치 간 딜레이 (0.5초)
            if i + 5 < len(symbols):
                await asyncio.sleep(0.5)

        return results

    async def _fetch_key_metrics(
        self, symbols: List[str], api_key: str, timeout: Any
    ) -> List[Dict[str, Any]]:
        """핵심 재무 지표 조회"""
        import asyncio

        results = []
        for sym in symbols:
            url = (
                f"{_FMP_BASE_URL}/key-metrics/{sym}"
                f"?period={self.period}&limit={self.limit}&apikey={api_key}"
            )
            data = await self._fetch_api(url, timeout)

            if isinstance(data, list):
                for item in data:
                    normalized = self._normalize_key_metrics(item, sym)
                    results.append(normalized)

            if len(symbols) > 1:
                await asyncio.sleep(0.5)

        return results

    async def _fetch_financial_statement(
        self,
        symbols: List[str],
        api_key: str,
        timeout: Any,
        endpoint: str,
    ) -> List[Dict[str, Any]]:
        """재무제표 조회 (income-statement, balance-sheet-statement)"""
        import asyncio

        results = []
        for sym in symbols:
            url = (
                f"{_FMP_BASE_URL}/{endpoint}/{sym}"
                f"?period={self.period}&limit={self.limit}&apikey={api_key}"
            )
            data = await self._fetch_api(url, timeout)

            if isinstance(data, list):
                for item in data:
                    item["symbol"] = sym
                    # exchange 매칭
                    exchange = self._find_exchange(sym)
                    item["exchange"] = exchange
                    results.append(item)

            if len(symbols) > 1:
                await asyncio.sleep(0.5)

        return results

    async def _fetch_api(self, url: str, timeout: Any) -> Any:
        """FMP API 단일 요청"""
        import aiohttp

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as resp:
                    if resp.status == 429:
                        raise ExternalAPIRateLimitError(
                            f"[FMP] HTTP 429: Rate limit exceeded"
                        )
                    if resp.status == 403:
                        raise ExternalAPIError(
                            f"[FMP] HTTP 403: Invalid API key or access denied"
                        )
                    if resp.status >= 500:
                        raise ExternalAPIError(
                            f"[FMP] HTTP {resp.status}: Server error"
                        )
                    if resp.status >= 400:
                        text = await resp.text()
                        raise ExternalAPIError(
                            f"[FMP] HTTP {resp.status}: {text[:200]}"
                        )

                    try:
                        data = await resp.json()
                    except (ValueError, Exception) as je:
                        text = await resp.text()
                        raise ExternalAPIError(
                            f"[FMP] JSON parse failed: {je} (response: {text[:200]})"
                        )

            return data

        except (ExternalAPIRateLimitError, ExternalAPIError) as e:
            raise

        except aiohttp.ClientError as e:
            raise ExternalAPINetworkError(f"[FMP] Network error: {e}")

        except Exception as e:
            if isinstance(e, (ExternalAPIRateLimitError, ExternalAPIError, ExternalAPINetworkError)):
                raise
            raise ExternalAPIError(f"[FMP] Unexpected error: {e}")

    def _normalize_profile(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """FMP profile 응답을 표준 형식으로 정규화"""
        return {
            "symbol": raw.get("symbol", ""),
            "exchange": raw.get("exchangeShortName", raw.get("exchange", "")),
            "company_name": raw.get("companyName", ""),
            "sector": raw.get("sector", ""),
            "market_cap": raw.get("mktCap", 0),
            "per": raw.get("pe", 0) or 0,
            "pbr": raw.get("pb", 0) or 0,
            "eps": raw.get("eps", 0) or 0,
            "roe": raw.get("roe", 0) or 0,
            "roa": raw.get("roa", 0) or 0,
            "dividend_yield": raw.get("lastDiv", 0) or 0,
            "beta": raw.get("beta", 0) or 0,
        }

    def _normalize_key_metrics(self, raw: Dict[str, Any], symbol: str) -> Dict[str, Any]:
        """FMP key_metrics 응답을 표준 형식으로 정규화"""
        return {
            "symbol": symbol,
            "exchange": self._find_exchange(symbol),
            "date": raw.get("date", ""),
            "enterprise_value": raw.get("enterpriseValue", 0) or 0,
            "ebit": raw.get("ebitPerShare", 0) or 0,
            "invested_capital": raw.get("investedCapital", 0) or 0,
            "ev_to_ebitda": raw.get("enterpriseValueOverEBITDA", 0) or 0,
            "roe": raw.get("roe", 0) or 0,
            "roic": raw.get("roic", 0) or 0,
            "revenue_per_share": raw.get("revenuePerShare", 0) or 0,
            "net_debt": raw.get("netDebtToEBITDA", 0) or 0,
        }

    def _find_exchange(self, symbol: str) -> str:
        """symbols 목록에서 심볼의 exchange 찾기"""
        for s in self.symbols:
            if s.get("symbol") == symbol:
                return s.get("exchange", "")
        return ""

    def is_retryable_error(self, error: Exception) -> Optional[RetryableError]:
        return _classify_retryable_error(error)
