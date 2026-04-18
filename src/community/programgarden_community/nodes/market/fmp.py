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
    _img_url: ClassVar[str] = ""

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Screen stocks by fundamental quality metrics (P/E, ROE, EPS, market cap) before applying technical entry signals",
            "Implement value-investing strategies (e.g. Magic Formula — combine high ROIC with low EV/EBITDA) using key_metrics data",
            "Provide company profile data to an AIAgentNode for fundamental analysis or sector comparison",
            "Pull quarterly or annual income statements for ratio-based filters in a ScreenerNode → FundamentalDataNode pipeline",
        ],
        "when_not_to_use": [
            "When broker-integrated fundamental data is sufficient — OverseasStockFundamentalNode (LS-based) is preferred for live trading workflows since it does not require a separate API key",
            "For high-frequency or intraday analysis — fundamental data changes quarterly at most; calling this node per tick is wasteful",
            "For domestic (Korean) stocks — this node covers international equities via FMP; use KoreaStockFundamentalNode for KOSPI/KOSDAQ",
        ],
        "typical_scenarios": [
            "WatchlistNode → FundamentalDataNode (profile) → ConditionNode (filter by P/E < 20) → OverseasStockNewOrderNode",
            "MarketUniverseNode → FundamentalDataNode (key_metrics) → FieldMappingNode (rank by ROIC) → ScreenerNode",
            "FundamentalDataNode (income_statement) → AIAgentNode (summarize revenue trend)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Four data types via Financial Modeling Prep API: 'profile' (company overview + valuation ratios), 'key_metrics' (ROIC, EV/EBITDA, net debt), 'income_statement', and 'balance_sheet'",
        "Credential-based API key management — FMP API key stored in a 'fmp_api' credential, never embedded in workflow JSON",
        "Batch profile fetch (up to 5 symbols per request) with automatic batching for larger symbol lists",
        "Supports 'annual' and 'quarter' period options with configurable record limit (1–10) for income_statement and balance_sheet types",
        "is_tool_enabled=True — AI Agent can invoke this node as a tool to fetch fundamentals on demand during analysis",
        "Distinct from OverseasStockFundamentalNode: FundamentalDataNode uses FMP (no broker required), OverseasStockFundamentalNode uses LS Securities API (broker required)",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Calling FundamentalDataNode on every workflow cycle for intraday trading",
            "reason": "Fundamental data is quarterly; repeated calls waste FMP API quota (250 calls/day on the free tier) and add latency without updating the data.",
            "alternative": "Call FundamentalDataNode once at workflow start or on a daily schedule; cache results in SQLiteNode for the rest of the session.",
        },
        {
            "pattern": "Confusing FundamentalDataNode with OverseasStockFundamentalNode",
            "reason": "OverseasStockFundamentalNode uses the LS Securities broker connection and does not require an FMP API key. Using FundamentalDataNode unnecessarily introduces an external dependency.",
            "alternative": "Use OverseasStockFundamentalNode for LS-connected workflows. Reserve FundamentalDataNode for fundamentals not available through LS (e.g. detailed income statements, ROIC).",
        },
        {
            "pattern": "Passing more than 5 symbols at once expecting a single batched response",
            "reason": "FMP profile endpoint batches up to 5 symbols. For key_metrics and financial statements, requests are issued per-symbol sequentially; large lists trigger long execution times and quota exhaustion.",
            "alternative": "Pre-filter your watchlist to a focused set (5–10 names) using ScreenerNode or ConditionNode before calling FundamentalDataNode.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Filter watchlist by P/E ratio",
            "description": "Fetch company profiles for a watchlist and keep only stocks with P/E below 20 for further technical analysis.",
            "workflow_snippet": {
                "id": "fmp_pe_filter",
                "name": "FMP PE Filter",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {
                        "id": "fundamental",
                        "type": "FundamentalDataNode",
                        "credential_id": "fmp_cred",
                        "symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}, {"symbol": "MSFT", "exchange": "NASDAQ"}],
                        "data_type": "profile",
                    },
                    {"id": "display", "type": "TableDisplayNode", "data": "{{ nodes.fundamental.data }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "fundamental"},
                    {"from": "fundamental", "to": "display"},
                ],
                "credentials": [
                    {
                        "credential_id": "broker_cred",
                        "type": "broker_ls_overseas_stock",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    },
                    {
                        "credential_id": "fmp_cred",
                        "type": "fmp_api",
                        "data": [
                            {"key": "api_key", "value": "", "type": "password", "label": "FMP API Key"},
                        ],
                    },
                ],
            },
            "expected_output": "data: list of company profile dicts with symbol, per, pbr, roe, market_cap fields. summary: {data_type, symbol_count, record_count}.",
        },
        {
            "title": "Key metrics for value screening",
            "description": "Pull annual key metrics for two candidates and display them for manual review before running a value-ranking model.",
            "workflow_snippet": {
                "id": "fmp_key_metrics",
                "name": "FMP Key Metrics",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {
                        "id": "metrics",
                        "type": "FundamentalDataNode",
                        "credential_id": "fmp_cred",
                        "symbols": [{"symbol": "GOOG", "exchange": "NASDAQ"}, {"symbol": "META", "exchange": "NASDAQ"}],
                        "data_type": "key_metrics",
                        "period": "annual",
                        "limit": 1,
                    },
                    {"id": "display", "type": "TableDisplayNode", "data": "{{ nodes.metrics.data }}"},
                ],
                "edges": [
                    {"from": "start", "to": "metrics"},
                    {"from": "metrics", "to": "display"},
                ],
                "credentials": [
                    {
                        "credential_id": "fmp_cred",
                        "type": "fmp_api",
                        "data": [
                            {"key": "api_key", "value": "", "type": "password", "label": "FMP API Key"},
                        ],
                    }
                ],
            },
            "expected_output": "data: list of key metric dicts with roic, ev_to_ebitda, roe, net_debt per symbol. summary: {data_type='key_metrics', symbol_count=2, record_count=2}.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "Provide 'symbols' as a list of {symbol, exchange} dicts. The 'symbols' input port also accepts upstream array output (e.g. from WatchlistNode) via expression binding. Choose 'data_type' to control which FMP endpoint is called. 'period' and 'limit' apply only to income_statement, balance_sheet, and key_metrics.",
        "output_consumption": "Consume 'data' (list[dict]) as the primary output — each element is a normalized record for one symbol. Pipe to FieldMappingNode for column renaming, to ConditionNode for ratio-based filtering, or to TableDisplayNode for review. 'summary' provides high-level counts (symbol_count, record_count) useful for validation.",
        "common_combinations": [
            "WatchlistNode → FundamentalDataNode (profile) → FieldMappingNode → ConditionNode (ratio filter)",
            "FundamentalDataNode (key_metrics) → AIAgentNode (value ranking prompt)",
            "FundamentalDataNode (income_statement) → SQLiteNode (cache quarterly data)",
        ],
        "pitfalls": [
            "FMP free tier allows ~250 API calls per day — use SQLiteNode caching to avoid exhausting quota during testing.",
            "'per' (P/E ratio) and 'pbr' fields can be 0 when FMP does not have the data; guard against division by zero in ConditionNode expressions.",
            "The 'exchange' field in profile output uses FMP's short name (e.g. 'NASDAQ', 'NYSE') which may differ from the LS Securities exchange codes — align before cross-referencing.",
        ],
    }

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
