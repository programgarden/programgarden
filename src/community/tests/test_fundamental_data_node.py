"""
FundamentalDataNode 단위 테스트

FMP API 기반 재무 데이터 노드 검증.

테스트 대상:
1. 노드 모델 생성 및 타입/카테고리
2. 입출력 포트
3. FieldSchema
4. execute() profile / key_metrics / income_statement / balance_sheet (mock API)
5. 일괄 조회 (5종목 배치)
6. 에러 처리 (API 키 없음, 종목 없음, 서버 에러, rate limit)
7. rate_limit / connection_rules
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

from programgarden_community.nodes.market.fmp import FundamentalDataNode
from programgarden_core.nodes.base import NodeCategory
from programgarden_core.nodes.market_external import (
    ExternalAPIError,
    ExternalAPIRateLimitError,
)


# ============================================================
# 모델 테스트
# ============================================================

class TestFundamentalDataNodeModel:
    """FundamentalDataNode 모델 테스트"""

    def test_node_has_correct_type(self):
        node = FundamentalDataNode(id="fmp1")
        assert node.type == "FundamentalDataNode"

    def test_node_category_is_market(self):
        node = FundamentalDataNode(id="fmp1")
        assert node.category == NodeCategory.MARKET

    def test_node_description_is_i18n_key(self):
        node = FundamentalDataNode(id="fmp1")
        assert node.description.startswith("i18n:")

    def test_node_is_tool_enabled(self):
        assert FundamentalDataNode.is_tool_enabled() is True

    def test_default_data_type(self):
        node = FundamentalDataNode(id="fmp1")
        assert node.data_type == "profile"

    def test_default_period(self):
        node = FundamentalDataNode(id="fmp1")
        assert node.period == "annual"

    def test_default_limit(self):
        node = FundamentalDataNode(id="fmp1")
        assert node.limit == 1

    def test_resilience_retry_enabled_by_default(self):
        node = FundamentalDataNode(id="fmp1")
        assert node.resilience.retry.enabled is True


# ============================================================
# 포트 테스트
# ============================================================

class TestFundamentalDataNodePorts:
    """FundamentalDataNode 입출력 포트 검증"""

    def test_input_ports(self):
        node = FundamentalDataNode(id="fmp1")
        input_names = [p.name for p in node._inputs]
        assert "trigger" in input_names
        assert "symbols" in input_names

    def test_output_ports(self):
        node = FundamentalDataNode(id="fmp1")
        output_names = [p.name for p in node._outputs]
        assert "data" in output_names
        assert "summary" in output_names

    def test_data_port_type(self):
        node = FundamentalDataNode(id="fmp1")
        port = next(p for p in node._outputs if p.name == "data")
        assert port.type == "array"

    def test_summary_port_type(self):
        node = FundamentalDataNode(id="fmp1")
        port = next(p for p in node._outputs if p.name == "summary")
        assert port.type == "object"


# ============================================================
# FieldSchema 테스트
# ============================================================

class TestFundamentalDataNodeFieldSchema:
    """FundamentalDataNode FieldSchema 검증"""

    def test_field_schema_keys(self):
        schema = FundamentalDataNode.get_field_schema()
        assert "credential_id" in schema
        assert "symbols" in schema
        assert "data_type" in schema
        assert "period" in schema
        assert "limit" in schema
        assert "resilience" in schema

    def test_data_type_enum_values(self):
        schema = FundamentalDataNode.get_field_schema()
        assert "profile" in schema["data_type"].enum_values
        assert "income_statement" in schema["data_type"].enum_values
        assert "balance_sheet" in schema["data_type"].enum_values
        assert "key_metrics" in schema["data_type"].enum_values


# ============================================================
# Execute 테스트 (mock API)
# ============================================================

def _make_mock_session(json_data, status=200):
    """mock aiohttp session 생성"""
    mock_resp = AsyncMock()
    mock_resp.status = status
    mock_resp.json = AsyncMock(return_value=json_data)
    mock_resp.text = AsyncMock(return_value="error")
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    mock_session = AsyncMock()
    mock_session.get = MagicMock(return_value=mock_resp)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    return mock_session


class TestFundamentalDataNodeExecuteProfile:
    """profile data_type 실행 테스트"""

    @pytest.mark.asyncio
    async def test_execute_profile_returns_data(self):
        node = FundamentalDataNode(
            id="fmp1",
            symbols=[{"symbol": "AAPL", "exchange": "NASDAQ"}],
            data_type="profile",
        )
        node._api_key = "test_key"

        mock_response = [
            {
                "symbol": "AAPL",
                "companyName": "Apple Inc.",
                "exchangeShortName": "NASDAQ",
                "sector": "Technology",
                "mktCap": 3500000000000,
                "pe": 28.5,
                "pb": 45.2,
                "eps": 6.42,
                "roe": 1.56,
                "roa": 0.28,
                "lastDiv": 0.005,
                "beta": 1.24,
            }
        ]

        session = _make_mock_session(mock_response)
        with patch("aiohttp.ClientSession", return_value=session):
            result = await node.execute(None)

        assert len(result["data"]) == 1
        assert result["data"][0]["symbol"] == "AAPL"
        assert result["data"][0]["exchange"] == "NASDAQ"
        assert result["data"][0]["company_name"] == "Apple Inc."
        assert result["data"][0]["per"] == 28.5
        assert result["data"][0]["market_cap"] == 3500000000000
        assert result["summary"]["data_type"] == "profile"
        assert result["summary"]["symbol_count"] == 1

    @pytest.mark.asyncio
    async def test_execute_profile_multiple_symbols(self):
        node = FundamentalDataNode(
            id="fmp1",
            symbols=[
                {"symbol": "AAPL", "exchange": "NASDAQ"},
                {"symbol": "MSFT", "exchange": "NASDAQ"},
            ],
            data_type="profile",
        )
        node._api_key = "test_key"

        mock_response = [
            {"symbol": "AAPL", "companyName": "Apple", "exchangeShortName": "NASDAQ"},
            {"symbol": "MSFT", "companyName": "Microsoft", "exchangeShortName": "NASDAQ"},
        ]

        session = _make_mock_session(mock_response)
        with patch("aiohttp.ClientSession", return_value=session):
            result = await node.execute(None)

        assert len(result["data"]) == 2
        assert result["summary"]["symbol_count"] == 2


class TestFundamentalDataNodeExecuteKeyMetrics:
    """key_metrics data_type 실행 테스트"""

    @pytest.mark.asyncio
    async def test_execute_key_metrics(self):
        node = FundamentalDataNode(
            id="fmp1",
            symbols=[{"symbol": "AAPL", "exchange": "NASDAQ"}],
            data_type="key_metrics",
            period="annual",
            limit=1,
        )
        node._api_key = "test_key"

        mock_response = [
            {
                "date": "2025-09-30",
                "enterpriseValue": 3600000000000,
                "ebitPerShare": 8.5,
                "investedCapital": 200000000000,
                "enterpriseValueOverEBITDA": 25.3,
                "roe": 1.56,
                "roic": 0.60,
                "revenuePerShare": 24.5,
                "netDebtToEBITDA": 0.5,
            }
        ]

        session = _make_mock_session(mock_response)
        with patch("aiohttp.ClientSession", return_value=session):
            result = await node.execute(None)

        assert len(result["data"]) == 1
        data = result["data"][0]
        assert data["symbol"] == "AAPL"
        assert data["exchange"] == "NASDAQ"
        assert data["enterprise_value"] == 3600000000000
        assert data["ev_to_ebitda"] == 25.3


class TestFundamentalDataNodeExecuteFinancialStatement:
    """재무제표 data_type 실행 테스트"""

    @pytest.mark.asyncio
    async def test_execute_income_statement(self):
        node = FundamentalDataNode(
            id="fmp1",
            symbols=[{"symbol": "AAPL", "exchange": "NASDAQ"}],
            data_type="income_statement",
        )
        node._api_key = "test_key"

        mock_response = [
            {
                "date": "2025-09-30",
                "revenue": 400000000000,
                "netIncome": 100000000000,
                "ebitda": 130000000000,
            }
        ]

        session = _make_mock_session(mock_response)
        with patch("aiohttp.ClientSession", return_value=session):
            result = await node.execute(None)

        assert len(result["data"]) == 1
        assert result["data"][0]["symbol"] == "AAPL"
        assert result["data"][0]["exchange"] == "NASDAQ"
        assert result["summary"]["data_type"] == "income_statement"

    @pytest.mark.asyncio
    async def test_execute_balance_sheet(self):
        node = FundamentalDataNode(
            id="fmp1",
            symbols=[{"symbol": "AAPL", "exchange": "NASDAQ"}],
            data_type="balance_sheet",
        )
        node._api_key = "test_key"

        mock_response = [
            {
                "date": "2025-09-30",
                "totalAssets": 350000000000,
                "totalStockholdersEquity": 65000000000,
            }
        ]

        session = _make_mock_session(mock_response)
        with patch("aiohttp.ClientSession", return_value=session):
            result = await node.execute(None)

        assert len(result["data"]) == 1
        assert result["summary"]["data_type"] == "balance_sheet"


# ============================================================
# 에러 처리 테스트
# ============================================================

class TestFundamentalDataNodeErrors:
    """에러 처리 검증"""

    @pytest.mark.asyncio
    async def test_no_api_key_raises(self):
        node = FundamentalDataNode(
            id="fmp1",
            symbols=[{"symbol": "AAPL", "exchange": "NASDAQ"}],
        )
        # _api_key not set
        with pytest.raises(ExternalAPIError, match="API key not provided"):
            await node.execute(None)

    @pytest.mark.asyncio
    async def test_no_symbols_raises(self):
        node = FundamentalDataNode(id="fmp1", symbols=[])
        node._api_key = "test_key"
        with pytest.raises(ExternalAPIError, match="No symbols"):
            await node.execute(None)

    @pytest.mark.asyncio
    async def test_server_error_raises(self):
        node = FundamentalDataNode(
            id="fmp1",
            symbols=[{"symbol": "AAPL", "exchange": "NASDAQ"}],
        )
        node._api_key = "test_key"

        session = _make_mock_session({}, status=500)
        with patch("aiohttp.ClientSession", return_value=session):
            with pytest.raises(ExternalAPIError, match="HTTP 500"):
                await node.execute(None)

    @pytest.mark.asyncio
    async def test_rate_limit_error_raises(self):
        node = FundamentalDataNode(
            id="fmp1",
            symbols=[{"symbol": "AAPL", "exchange": "NASDAQ"}],
        )
        node._api_key = "test_key"

        session = _make_mock_session({}, status=429)
        with patch("aiohttp.ClientSession", return_value=session):
            with pytest.raises(ExternalAPIRateLimitError):
                await node.execute(None)

    @pytest.mark.asyncio
    async def test_forbidden_error_raises(self):
        node = FundamentalDataNode(
            id="fmp1",
            symbols=[{"symbol": "AAPL", "exchange": "NASDAQ"}],
        )
        node._api_key = "invalid_key"

        session = _make_mock_session({}, status=403)
        with patch("aiohttp.ClientSession", return_value=session):
            with pytest.raises(ExternalAPIError, match="403"):
                await node.execute(None)


# ============================================================
# Rate limit / Connection rules
# ============================================================

class TestFundamentalDataNodeRules:
    """Rate limit 및 연결 규칙"""

    def test_rate_limit(self):
        """L-2: FMP → 60초 간격"""
        assert FundamentalDataNode._rate_limit is not None
        assert FundamentalDataNode._rate_limit.min_interval_sec == 60

    def test_connection_rules(self):
        rules = FundamentalDataNode._connection_rules
        assert len(rules) == 1
        assert "ThrottleNode" in rules[0].required_intermediate


# ============================================================
# Tool Schema
# ============================================================

class TestFundamentalDataToolSchema:
    """AI Tool 스키마 검증"""

    def test_tool_schema(self):
        schema = FundamentalDataNode.as_tool_schema()
        assert schema["tool_name"] == "fundamental_data"
        assert schema["node_type"] == "FundamentalDataNode"

    def test_tool_schema_has_returns(self):
        schema = FundamentalDataNode.as_tool_schema()
        assert "returns" in schema
        assert len(schema["returns"]) > 0
