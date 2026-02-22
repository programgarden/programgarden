"""
CurrencyRateNode, FearGreedIndexNode, VIXDataNode 단위 테스트

테스트 대상:
1. 노드 모델 생성 및 타입/카테고리 검증
2. 입출력 포트 검증
3. FieldSchema 검증
4. NodeTypeRegistry 등록 확인
5. is_tool_enabled / as_tool_schema
6. execute() (mock API 응답)
7. resilience (is_retryable_error)
8. rate_limit / connection_rules
"""

import sys
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

# core 패키지에 aiohttp가 없으므로 mock 모듈 주입
_mock_aiohttp = MagicMock()
_mock_aiohttp.ClientTimeout = MagicMock
_mock_aiohttp.ClientError = Exception
if "aiohttp" not in sys.modules:
    sys.modules["aiohttp"] = _mock_aiohttp

from programgarden_core.nodes.market_external import (
    CurrencyRateNode,
    FearGreedIndexNode,
    VIXDataNode,
    ExternalAPIError,
    ExternalAPIRateLimitError,
    ExternalAPINetworkError,
    ExternalAPITimeoutError,
    _classify_retryable_error,
)
from programgarden_core.nodes.base import NodeCategory, RetryableError


# ============================================================
# CurrencyRateNode 테스트
# ============================================================

class TestCurrencyRateNodeModel:
    """CurrencyRateNode 모델 테스트"""

    def test_node_has_correct_type(self):
        node = CurrencyRateNode(id="fx1")
        assert node.type == "CurrencyRateNode"

    def test_node_category_is_market(self):
        node = CurrencyRateNode(id="fx1")
        assert node.category == NodeCategory.MARKET

    def test_node_description_is_i18n_key(self):
        node = CurrencyRateNode(id="fx1")
        assert node.description.startswith("i18n:")

    def test_node_default_base_currency(self):
        node = CurrencyRateNode(id="fx1")
        assert node.base_currency == "USD"

    def test_node_default_target_currencies(self):
        node = CurrencyRateNode(id="fx1")
        assert node.target_currencies == ["KRW"]

    def test_node_custom_currencies(self):
        node = CurrencyRateNode(id="fx1", base_currency="EUR", target_currencies=["USD", "JPY"])
        assert node.base_currency == "EUR"
        assert node.target_currencies == ["USD", "JPY"]

    def test_node_is_tool_enabled(self):
        assert CurrencyRateNode.is_tool_enabled() is True

    def test_resilience_retry_enabled_by_default(self):
        node = CurrencyRateNode(id="fx1")
        assert node.resilience.retry.enabled is True
        assert node.resilience.retry.max_retries == 3


class TestCurrencyRateNodePorts:
    """CurrencyRateNode 입출력 포트 검증"""

    def test_input_ports(self):
        node = CurrencyRateNode(id="fx1")
        input_names = [p.name for p in node._inputs]
        assert "trigger" in input_names

    def test_output_ports(self):
        node = CurrencyRateNode(id="fx1")
        output_names = [p.name for p in node._outputs]
        assert "rates" in output_names
        assert "krw_rate" in output_names

    def test_rates_port_type(self):
        node = CurrencyRateNode(id="fx1")
        rates_port = next(p for p in node._outputs if p.name == "rates")
        assert rates_port.type == "array"

    def test_krw_rate_port_type(self):
        node = CurrencyRateNode(id="fx1")
        krw_port = next(p for p in node._outputs if p.name == "krw_rate")
        assert krw_port.type == "number"


class TestCurrencyRateNodeFieldSchema:
    """CurrencyRateNode FieldSchema 검증"""

    def test_field_schema_keys(self):
        schema = CurrencyRateNode.get_field_schema()
        assert "base_currency" in schema
        assert "target_currencies" in schema
        assert "resilience" in schema

    def test_base_currency_is_enum(self):
        schema = CurrencyRateNode.get_field_schema()
        type_val = schema["base_currency"].type
        val = type_val.value if hasattr(type_val, 'value') else str(type_val)
        assert val == "enum"

    def test_base_currency_enum_values(self):
        schema = CurrencyRateNode.get_field_schema()
        assert "USD" in schema["base_currency"].enum_values
        assert "KRW" in schema["base_currency"].enum_values

    def test_target_currencies_is_array(self):
        schema = CurrencyRateNode.get_field_schema()
        type_val = schema["target_currencies"].type
        val = type_val.value if hasattr(type_val, 'value') else str(type_val)
        assert val == "array"


class TestCurrencyRateNodeExecute:
    """CurrencyRateNode execute() 테스트 (mock)"""

    @pytest.fixture
    def mock_api_response(self):
        return {
            "amount": 1.0,
            "base": "USD",
            "date": "2026-02-20",
            "rates": {"KRW": 1449.66, "JPY": 155.21},
        }

    @pytest.mark.asyncio
    async def test_execute_returns_rates(self, mock_api_response):
        node = CurrencyRateNode(id="fx1", target_currencies=["KRW", "JPY"])

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=mock_api_response)
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await node.execute(None)

        assert len(result["rates"]) == 2
        assert result["krw_rate"] == 1449.66

    @pytest.mark.asyncio
    async def test_execute_rates_structure(self, mock_api_response):
        node = CurrencyRateNode(id="fx1", target_currencies=["KRW", "JPY"])

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=mock_api_response)
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await node.execute(None)

        rate_item = result["rates"][0]
        assert "base" in rate_item
        assert "target" in rate_item
        assert "rate" in rate_item
        assert "timestamp" in rate_item

    @pytest.mark.asyncio
    async def test_execute_krw_rate_zero_when_not_in_targets(self):
        node = CurrencyRateNode(id="fx1", target_currencies=["EUR"])
        api_resp = {"amount": 1.0, "base": "USD", "date": "2026-02-20", "rates": {"EUR": 0.85}}

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=api_resp)
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await node.execute(None)

        assert result["krw_rate"] == 0

    @pytest.mark.asyncio
    async def test_execute_raises_on_server_error(self):
        node = CurrencyRateNode(id="fx1")

        mock_resp = AsyncMock()
        mock_resp.status = 500
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            with pytest.raises(ExternalAPIError, match="HTTP 500"):
                await node.execute(None)

    @pytest.mark.asyncio
    async def test_execute_raises_on_rate_limit(self):
        node = CurrencyRateNode(id="fx1")

        mock_resp = AsyncMock()
        mock_resp.status = 429
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            with pytest.raises(ExternalAPIRateLimitError):
                await node.execute(None)


# ============================================================
# FearGreedIndexNode 테스트
# ============================================================

class TestFearGreedIndexNodeModel:
    """FearGreedIndexNode 모델 테스트"""

    def test_node_has_correct_type(self):
        node = FearGreedIndexNode(id="fgi1")
        assert node.type == "FearGreedIndexNode"

    def test_node_category_is_market(self):
        node = FearGreedIndexNode(id="fgi1")
        assert node.category == NodeCategory.MARKET

    def test_node_description_is_i18n_key(self):
        node = FearGreedIndexNode(id="fgi1")
        assert node.description.startswith("i18n:")

    def test_node_is_tool_enabled(self):
        assert FearGreedIndexNode.is_tool_enabled() is True

    def test_resilience_retry_enabled_by_default(self):
        node = FearGreedIndexNode(id="fgi1")
        assert node.resilience.retry.enabled is True


class TestFearGreedIndexNodePorts:
    """FearGreedIndexNode 입출력 포트 검증"""

    def test_input_ports(self):
        node = FearGreedIndexNode(id="fgi1")
        input_names = [p.name for p in node._inputs]
        assert "trigger" in input_names

    def test_output_ports(self):
        node = FearGreedIndexNode(id="fgi1")
        output_names = [p.name for p in node._outputs]
        assert "value" in output_names
        assert "label" in output_names
        assert "previous_close" in output_names

    def test_value_port_type(self):
        node = FearGreedIndexNode(id="fgi1")
        port = next(p for p in node._outputs if p.name == "value")
        assert port.type == "number"

    def test_label_port_type(self):
        node = FearGreedIndexNode(id="fgi1")
        port = next(p for p in node._outputs if p.name == "label")
        assert port.type == "string"


class TestFearGreedIndexNodeFieldSchema:
    """FearGreedIndexNode FieldSchema 검증"""

    def test_field_schema_has_resilience_only(self):
        schema = FearGreedIndexNode.get_field_schema()
        assert "resilience" in schema
        assert len(schema) == 1  # 설정 필드 없이 resilience만


class TestFearGreedIndexNodeLabel:
    """FearGreedIndexNode 라벨 정규화 테스트"""

    def test_normalize_extreme_fear(self):
        assert FearGreedIndexNode._normalize_label("Extreme Fear", 10) == "Extreme Fear"

    def test_normalize_fear(self):
        assert FearGreedIndexNode._normalize_label("Fear", 30) == "Fear"

    def test_normalize_neutral(self):
        assert FearGreedIndexNode._normalize_label("Neutral", 50) == "Neutral"

    def test_normalize_greed(self):
        assert FearGreedIndexNode._normalize_label("Greed", 65) == "Greed"

    def test_normalize_extreme_greed(self):
        assert FearGreedIndexNode._normalize_label("Extreme Greed", 90) == "Extreme Greed"

    def test_fallback_to_score_extreme_fear(self):
        assert FearGreedIndexNode._normalize_label("", 15) == "Extreme Fear"

    def test_fallback_to_score_fear(self):
        assert FearGreedIndexNode._normalize_label("", 35) == "Fear"

    def test_fallback_to_score_neutral(self):
        assert FearGreedIndexNode._normalize_label("", 50) == "Neutral"

    def test_fallback_to_score_greed(self):
        assert FearGreedIndexNode._normalize_label("", 65) == "Greed"

    def test_fallback_to_score_extreme_greed(self):
        assert FearGreedIndexNode._normalize_label("", 85) == "Extreme Greed"


class TestFearGreedIndexNodeExecute:
    """FearGreedIndexNode execute() 테스트 (mock)"""

    @pytest.fixture
    def mock_api_response(self):
        return {
            "fear_and_greed": {
                "score": 32.5,
                "rating": "Fear",
                "previous_close": 35.0,
            }
        }

    @pytest.mark.asyncio
    async def test_execute_returns_value(self, mock_api_response):
        node = FearGreedIndexNode(id="fgi1")

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=mock_api_response)
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await node.execute(None)

        assert result["value"] == 32.5
        assert result["label"] == "Fear"
        assert result["previous_close"] == 35.0

    @pytest.mark.asyncio
    async def test_execute_with_missing_rating(self):
        node = FearGreedIndexNode(id="fgi1")
        api_resp = {"fear_and_greed": {"score": 80, "previous_close": 75}}

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=api_resp)
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await node.execute(None)

        assert result["value"] == 80
        assert result["label"] == "Extreme Greed"

    @pytest.mark.asyncio
    async def test_execute_raises_on_server_error(self):
        node = FearGreedIndexNode(id="fgi1")

        mock_resp = AsyncMock()
        mock_resp.status = 503
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            with pytest.raises(ExternalAPIError, match="HTTP 503"):
                await node.execute(None)


# ============================================================
# VIXDataNode 테스트
# ============================================================

class TestVIXDataNodeModel:
    """VIXDataNode 모델 테스트"""

    def test_node_has_correct_type(self):
        node = VIXDataNode(id="vix1")
        assert node.type == "VIXDataNode"

    def test_node_category_is_market(self):
        node = VIXDataNode(id="vix1")
        assert node.category == NodeCategory.MARKET

    def test_node_description_is_i18n_key(self):
        node = VIXDataNode(id="vix1")
        assert node.description.startswith("i18n:")

    def test_node_default_include_history(self):
        node = VIXDataNode(id="vix1")
        assert node.include_history is False

    def test_node_custom_include_history(self):
        node = VIXDataNode(id="vix1", include_history=True)
        assert node.include_history is True

    def test_node_is_tool_enabled(self):
        assert VIXDataNode.is_tool_enabled() is True

    def test_resilience_retry_enabled_by_default(self):
        node = VIXDataNode(id="vix1")
        assert node.resilience.retry.enabled is True


class TestVIXDataNodePorts:
    """VIXDataNode 입출력 포트 검증"""

    def test_input_ports(self):
        node = VIXDataNode(id="vix1")
        input_names = [p.name for p in node._inputs]
        assert "trigger" in input_names

    def test_output_ports(self):
        node = VIXDataNode(id="vix1")
        output_names = [p.name for p in node._outputs]
        assert "vix" in output_names
        assert "level" in output_names
        assert "history" in output_names

    def test_vix_port_type(self):
        node = VIXDataNode(id="vix1")
        port = next(p for p in node._outputs if p.name == "vix")
        assert port.type == "number"

    def test_level_port_type(self):
        node = VIXDataNode(id="vix1")
        port = next(p for p in node._outputs if p.name == "level")
        assert port.type == "string"

    def test_history_port_type(self):
        node = VIXDataNode(id="vix1")
        port = next(p for p in node._outputs if p.name == "history")
        assert port.type == "array"


class TestVIXDataNodeFieldSchema:
    """VIXDataNode FieldSchema 검증"""

    def test_field_schema_keys(self):
        schema = VIXDataNode.get_field_schema()
        assert "include_history" in schema
        assert "resilience" in schema

    def test_include_history_is_boolean(self):
        schema = VIXDataNode.get_field_schema()
        type_val = schema["include_history"].type
        val = type_val.value if hasattr(type_val, 'value') else str(type_val)
        assert val == "boolean"


class TestVIXDataNodeLevel:
    """VIXDataNode 레벨 분류 테스트"""

    def test_low(self):
        assert VIXDataNode._classify_vix_level(12) == "low"

    def test_moderate(self):
        assert VIXDataNode._classify_vix_level(20) == "moderate"

    def test_high(self):
        assert VIXDataNode._classify_vix_level(30) == "high"

    def test_extreme(self):
        assert VIXDataNode._classify_vix_level(40) == "extreme"

    def test_boundary_low(self):
        assert VIXDataNode._classify_vix_level(14.99) == "low"

    def test_boundary_moderate(self):
        assert VIXDataNode._classify_vix_level(15) == "moderate"

    def test_boundary_high(self):
        assert VIXDataNode._classify_vix_level(25) == "high"

    def test_boundary_extreme(self):
        assert VIXDataNode._classify_vix_level(35) == "extreme"


class TestVIXDataNodeExecute:
    """VIXDataNode execute() 테스트 (mock)"""

    @pytest.fixture
    def mock_api_response(self):
        return {
            "chart": {
                "result": [{
                    "meta": {
                        "regularMarketPrice": 19.09,
                    },
                    "timestamp": [1708300800, 1708387200, 1708473600],
                    "indicators": {
                        "quote": [{
                            "close": [18.5, 19.2, 19.09],
                        }],
                    },
                }],
                "error": None,
            }
        }

    @pytest.mark.asyncio
    async def test_execute_returns_vix(self, mock_api_response):
        node = VIXDataNode(id="vix1")

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=mock_api_response)
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await node.execute(None)

        assert result["vix"] == 19.09
        assert result["level"] == "moderate"
        assert result["history"] == []  # include_history=False

    @pytest.mark.asyncio
    async def test_execute_with_history(self, mock_api_response):
        node = VIXDataNode(id="vix1", include_history=True)

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=mock_api_response)
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await node.execute(None)

        assert result["vix"] == 19.09
        assert len(result["history"]) == 3
        assert "date" in result["history"][0]
        assert "close" in result["history"][0]

    @pytest.mark.asyncio
    async def test_execute_empty_result_raises(self):
        node = VIXDataNode(id="vix1")
        api_resp = {"chart": {"result": [], "error": None}}

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=api_resp)
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            with pytest.raises(ExternalAPIError, match="Empty response"):
                await node.execute(None)

    @pytest.mark.asyncio
    async def test_execute_raises_on_rate_limit(self):
        node = VIXDataNode(id="vix1")

        mock_resp = AsyncMock()
        mock_resp.status = 429
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            with pytest.raises(ExternalAPIRateLimitError):
                await node.execute(None)


# ============================================================
# 공통: retryable error 분류 테스트
# ============================================================

class TestRetryableErrorClassification:
    """_classify_retryable_error 테스트"""

    def test_timeout_error(self):
        err = ExternalAPITimeoutError("Request timeout after 30s")
        assert _classify_retryable_error(err) == RetryableError.TIMEOUT

    def test_rate_limit_error(self):
        err = ExternalAPIRateLimitError("HTTP 429: Rate limit exceeded")
        assert _classify_retryable_error(err) == RetryableError.RATE_LIMIT

    def test_network_error(self):
        err = ExternalAPINetworkError("Network error: Connection refused")
        assert _classify_retryable_error(err) == RetryableError.NETWORK_ERROR

    def test_server_error_500(self):
        err = ExternalAPIError("HTTP 500: Server error")
        assert _classify_retryable_error(err) == RetryableError.SERVER_ERROR

    def test_server_error_503(self):
        err = ExternalAPIError("HTTP 503: Service unavailable")
        assert _classify_retryable_error(err) == RetryableError.SERVER_ERROR

    def test_non_retryable_error(self):
        err = ExternalAPIError("HTTP 404: Not found")
        assert _classify_retryable_error(err) is None

    def test_is_retryable_error_method(self):
        """노드 인스턴스의 is_retryable_error 메서드 테스트"""
        node = CurrencyRateNode(id="fx1")
        err = ExternalAPITimeoutError("timeout")
        assert node.is_retryable_error(err) == RetryableError.TIMEOUT


# ============================================================
# Rate limit / Connection rules 테스트
# ============================================================

class TestRateLimitAndConnectionRules:
    """Rate limit 및 연결 규칙 검증"""

    def test_currency_rate_node_rate_limit(self):
        assert CurrencyRateNode._rate_limit is not None
        assert CurrencyRateNode._rate_limit.min_interval_sec == 60

    def test_fear_greed_node_rate_limit(self):
        assert FearGreedIndexNode._rate_limit is not None
        assert FearGreedIndexNode._rate_limit.min_interval_sec == 60

    def test_vix_node_rate_limit(self):
        assert VIXDataNode._rate_limit is not None
        assert VIXDataNode._rate_limit.min_interval_sec == 60

    def test_currency_rate_node_connection_rules(self):
        rules = CurrencyRateNode._connection_rules
        assert len(rules) == 1
        assert "ThrottleNode" in rules[0].required_intermediate

    def test_fear_greed_node_connection_rules(self):
        rules = FearGreedIndexNode._connection_rules
        assert len(rules) == 1
        assert "ThrottleNode" in rules[0].required_intermediate

    def test_vix_node_connection_rules(self):
        rules = VIXDataNode._connection_rules
        assert len(rules) == 1
        assert "ThrottleNode" in rules[0].required_intermediate


# ============================================================
# NodeTypeRegistry 등록 테스트
# ============================================================

class TestMarketExternalNodeRegistry:
    """NodeTypeRegistry 등록 검증"""

    def test_currency_rate_node_registered(self):
        from programgarden_core.registry.node_registry import NodeTypeRegistry
        registry = NodeTypeRegistry()
        assert registry.get("CurrencyRateNode") is not None

    def test_fear_greed_node_registered(self):
        from programgarden_core.registry.node_registry import NodeTypeRegistry
        registry = NodeTypeRegistry()
        assert registry.get("FearGreedIndexNode") is not None

    def test_vix_node_registered(self):
        from programgarden_core.registry.node_registry import NodeTypeRegistry
        registry = NodeTypeRegistry()
        assert registry.get("VIXDataNode") is not None

    def test_currency_rate_node_schema(self):
        from programgarden_core.registry.node_registry import NodeTypeRegistry
        registry = NodeTypeRegistry()
        schema = registry.get_schema("CurrencyRateNode")
        assert schema is not None
        assert schema.category == "market"
        assert schema.product_scope == "all"

    def test_fear_greed_node_schema(self):
        from programgarden_core.registry.node_registry import NodeTypeRegistry
        registry = NodeTypeRegistry()
        schema = registry.get_schema("FearGreedIndexNode")
        assert schema is not None
        assert schema.category == "market"

    def test_vix_node_schema(self):
        from programgarden_core.registry.node_registry import NodeTypeRegistry
        registry = NodeTypeRegistry()
        schema = registry.get_schema("VIXDataNode")
        assert schema is not None
        assert schema.category == "market"

    def test_all_three_in_market_category(self):
        from programgarden_core.registry.node_registry import NodeTypeRegistry
        registry = NodeTypeRegistry()
        market_types = registry.list_types(category="market")
        assert "CurrencyRateNode" in market_types
        assert "FearGreedIndexNode" in market_types
        assert "VIXDataNode" in market_types

    def test_currency_rate_node_rate_limit_in_schema(self):
        from programgarden_core.registry.node_registry import NodeTypeRegistry
        registry = NodeTypeRegistry()
        schema = registry.get_schema("CurrencyRateNode")
        assert schema.rate_limit is not None
        assert schema.rate_limit["min_interval_sec"] == 60

    def test_connection_rules_in_schema(self):
        from programgarden_core.registry.node_registry import NodeTypeRegistry
        registry = NodeTypeRegistry()
        schema = registry.get_schema("CurrencyRateNode")
        assert len(schema.connection_rules) == 1


# ============================================================
# AI Tool Schema 테스트
# ============================================================

class TestMarketExternalToolSchema:
    """AI Tool 스키마 검증"""

    def test_currency_rate_tool_schema(self):
        schema = CurrencyRateNode.as_tool_schema()
        assert schema["tool_name"] == "currency_rate"
        assert schema["node_type"] == "CurrencyRateNode"
        assert "base_currency" in schema["parameters"]
        assert "target_currencies" in schema["parameters"]

    def test_fear_greed_tool_schema(self):
        schema = FearGreedIndexNode.as_tool_schema()
        assert schema["tool_name"] == "fear_greed_index"
        assert schema["node_type"] == "FearGreedIndexNode"

    def test_vix_tool_schema(self):
        schema = VIXDataNode.as_tool_schema()
        assert schema["tool_name"] == "vix_data"
        assert schema["node_type"] == "VIXDataNode"
        assert "include_history" in schema["parameters"]

    def test_tool_schemas_have_returns(self):
        for node_cls in [CurrencyRateNode, FearGreedIndexNode, VIXDataNode]:
            schema = node_cls.as_tool_schema()
            assert "returns" in schema
            assert len(schema["returns"]) > 0
