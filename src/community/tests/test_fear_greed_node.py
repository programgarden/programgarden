"""
FearGreedIndexNode 단위 테스트 (community 패키지)

core에서 community로 이동된 FearGreedIndexNode 검증.

테스트 대상:
1. 노드 모델 생성 및 타입/카테고리
2. 입출력 포트
3. FieldSchema
4. 라벨 정규화 로직
5. execute() (mock API)
6. rate_limit / connection_rules
"""

import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# core 패키지에 aiohttp가 없으므로 mock 모듈 주입
_mock_aiohttp = MagicMock()
_mock_aiohttp.ClientTimeout = MagicMock
_mock_aiohttp.ClientError = Exception
if "aiohttp" not in sys.modules:
    sys.modules["aiohttp"] = _mock_aiohttp

from programgarden_community.nodes.market.fear_greed import FearGreedIndexNode
from programgarden_core.nodes.base import NodeCategory
from programgarden_core.nodes.market_external import ExternalAPIError


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

    def test_field_schema_has_resilience_and_timeout(self):
        schema = FearGreedIndexNode.get_field_schema()
        assert "resilience" in schema
        assert "timeout_seconds" in schema
        assert len(schema) == 2


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


class TestFearGreedRateLimitAndRules:
    """Rate limit 및 연결 규칙"""

    def test_rate_limit(self):
        """L-2: CNN 비공식 API → 5분 간격"""
        assert FearGreedIndexNode._rate_limit is not None
        assert FearGreedIndexNode._rate_limit.min_interval_sec == 300

    def test_connection_rules(self):
        rules = FearGreedIndexNode._connection_rules
        assert len(rules) == 1
        assert "ThrottleNode" in rules[0].required_intermediate


class TestFearGreedToolSchema:
    """AI Tool 스키마 검증"""

    def test_tool_schema(self):
        schema = FearGreedIndexNode.as_tool_schema()
        assert schema["tool_name"] == "fear_greed_index"
        assert schema["node_type"] == "FearGreedIndexNode"

    def test_tool_schema_has_returns(self):
        schema = FearGreedIndexNode.as_tool_schema()
        assert "returns" in schema
        assert len(schema["returns"]) > 0
