"""
OverseasStockFundamentalNode Executor 테스트

테스트 대상:
1. FundamentalNodeExecutor 등록 확인
2. g3104 모킹 필드 매핑 검증
3. 에러 처리 (missing symbols, missing connection)
4. Resolver 검증 (StockBroker + FundamentalNode)

실행:
    cd src/programgarden && poetry run pytest tests/test_fundamental_node.py -v
"""

import pytest
import asyncio
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

from programgarden.resolver import WorkflowResolver


class TestFundamentalNodeExecutorRegistration:
    """FundamentalNodeExecutor 등록 검증"""

    def test_executor_registered(self):
        """FundamentalNodeExecutor가 executor 맵에 등록되어 있는지"""
        from programgarden import WorkflowExecutor

        executor = WorkflowExecutor()
        executors = executor._executors
        assert "OverseasStockFundamentalNode" in executors

    def test_executor_is_fundamental_type(self):
        """등록된 executor가 FundamentalNodeExecutor 인스턴스인지"""
        from programgarden import WorkflowExecutor
        from programgarden.executor import FundamentalNodeExecutor

        executor = WorkflowExecutor()
        assert isinstance(
            executor._executors["OverseasStockFundamentalNode"],
            FundamentalNodeExecutor,
        )


class TestFundamentalNodeExecutorLogic:
    """FundamentalNodeExecutor 실행 로직 검증"""

    @pytest.fixture
    def mock_context(self):
        """모킹된 ExecutionContext"""
        ctx = MagicMock()
        ctx.log = MagicMock()
        ctx.get_output = MagicMock(return_value=None)
        ctx.get_credential = MagicMock(return_value={
            "appkey": "test_key",
            "appsecret": "test_secret",
            "paper_trading": False,
        })
        return ctx

    @pytest.mark.asyncio
    async def test_missing_symbols_returns_error(self, mock_context):
        """symbols가 없으면 에러 반환"""
        from programgarden.executor import FundamentalNodeExecutor

        executor = FundamentalNodeExecutor()
        result = await executor.execute(
            node_id="fund1",
            node_type="OverseasStockFundamentalNode",
            config={},
            context=mock_context,
        )
        assert "error" in result
        assert result["values"] == []

    @pytest.mark.asyncio
    async def test_missing_connection_returns_error(self, mock_context):
        """connection이 없으면 에러 반환"""
        from programgarden.executor import FundamentalNodeExecutor

        executor = FundamentalNodeExecutor()
        result = await executor.execute(
            node_id="fund1",
            node_type="OverseasStockFundamentalNode",
            config={
                "symbols": [{"exchange": "NASDAQ", "symbol": "AAPL"}],
            },
            context=mock_context,
        )
        assert "error" in result
        assert "connection" in result["error"].lower() or "Missing" in result["error"]

    @pytest.mark.asyncio
    async def test_g3104_field_mapping(self, mock_context):
        """g3104 응답 필드가 올바르게 매핑되는지"""
        from programgarden.executor import FundamentalNodeExecutor

        # g3104 응답 모킹
        mock_block = MagicMock()
        mock_block.engname = "Apple Inc"
        mock_block.induname = "Technology"
        mock_block.nation_name = "United States"
        mock_block.exchange_name = "NASDAQ"
        mock_block.clos = 185.50
        mock_block.pcls = 183.00
        mock_block.volume = 50000000
        mock_block.perv = 28.5
        mock_block.epsv = 6.42
        mock_block.shareprc = 2850000000000
        mock_block.share = 15400000000
        mock_block.high52p = "199.62"
        mock_block.low52p = "124.17"
        mock_block.exrate = 1380.50

        mock_response = MagicMock()
        mock_response.block = mock_block

        mock_g3104 = MagicMock()
        mock_g3104.req.return_value = mock_response

        mock_market = MagicMock()
        mock_market.g3104.return_value = mock_g3104

        mock_api = MagicMock()
        mock_api.market.return_value = mock_market

        mock_ls = MagicMock()
        mock_ls.overseas_stock.return_value = mock_api

        with patch("programgarden.executor.ensure_ls_login") as mock_login:
            mock_login.return_value = (mock_ls, True, None)

            executor = FundamentalNodeExecutor()
            result = await executor.execute(
                node_id="fund1",
                node_type="OverseasStockFundamentalNode",
                config={
                    "symbols": [{"exchange": "NASDAQ", "symbol": "AAPL"}],
                    "connection": {"product": "overseas_stock", "provider": "ls-sec.co.kr"},
                },
                context=mock_context,
            )

        assert "error" not in result
        assert len(result["values"]) == 1

        val = result["values"][0]
        assert val["symbol"] == "AAPL"
        assert val["exchange"] == "NASDAQ"
        assert val["name"] == "Apple Inc"
        assert val["industry"] == "Technology"
        assert val["nation"] == "United States"
        assert val["exchange_name"] == "NASDAQ"
        assert val["current_price"] == 185.50
        assert val["volume"] == 50000000
        assert val["per"] == 28.5
        assert val["eps"] == 6.42
        assert val["market_cap"] == 2850000000000
        assert val["shares_outstanding"] == 15400000000
        assert val["high_52w"] == 199.62
        assert val["low_52w"] == 124.17
        assert val["exchange_rate"] == 1380.50
        # 등락률 검증: (185.50 - 183.00) / 183.00 * 100 = 1.37%
        assert abs(val["change_percent"] - 1.37) < 0.01

    @pytest.mark.asyncio
    async def test_multiple_symbols(self, mock_context):
        """여러 종목 동시 조회"""
        from programgarden.executor import FundamentalNodeExecutor

        mock_block = MagicMock()
        mock_block.engname = "Test Corp"
        mock_block.induname = "Tech"
        mock_block.nation_name = "US"
        mock_block.exchange_name = "NASDAQ"
        mock_block.clos = 100.0
        mock_block.pcls = 100.0
        mock_block.volume = 1000
        mock_block.perv = 10.0
        mock_block.epsv = 5.0
        mock_block.shareprc = 100000
        mock_block.share = 1000
        mock_block.high52p = "150.0"
        mock_block.low52p = "50.0"
        mock_block.exrate = 1300.0

        mock_response = MagicMock()
        mock_response.block = mock_block

        mock_g3104 = MagicMock()
        mock_g3104.req.return_value = mock_response

        mock_market = MagicMock()
        mock_market.g3104.return_value = mock_g3104

        mock_api = MagicMock()
        mock_api.market.return_value = mock_market

        mock_ls = MagicMock()
        mock_ls.overseas_stock.return_value = mock_api

        with patch("programgarden.executor.ensure_ls_login") as mock_login:
            mock_login.return_value = (mock_ls, True, None)

            executor = FundamentalNodeExecutor()
            result = await executor.execute(
                node_id="fund1",
                node_type="OverseasStockFundamentalNode",
                config={
                    "symbols": [
                        {"exchange": "NASDAQ", "symbol": "AAPL"},
                        {"exchange": "NYSE", "symbol": "MSFT"},
                    ],
                    "connection": {"product": "overseas_stock"},
                },
                context=mock_context,
            )

        assert len(result["values"]) == 2

    @pytest.mark.asyncio
    async def test_missing_credential_returns_error(self, mock_context):
        """credential이 없으면 에러 반환"""
        from programgarden.executor import FundamentalNodeExecutor

        mock_context.get_credential.return_value = None

        executor = FundamentalNodeExecutor()
        result = await executor.execute(
            node_id="fund1",
            node_type="OverseasStockFundamentalNode",
            config={
                "symbols": [{"exchange": "NASDAQ", "symbol": "AAPL"}],
                "connection": {"product": "overseas_stock"},
            },
            context=mock_context,
        )
        assert "error" in result


class TestFundamentalNodeResolverValidation:
    """Resolver 검증: StockBroker + FundamentalNode"""

    def test_stock_broker_with_fundamental_valid(self):
        """해외주식 브로커 + FundamentalNode → 검증 통과"""
        resolver = WorkflowResolver()
        workflow = {
            "id": "test-fund-valid",
            "name": "펀더멘털 노드 테스트",
            "nodes": [
                {"id": "start", "type": "StartNode"},
                {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "cred"},
                {"id": "fund", "type": "OverseasStockFundamentalNode",
                 "symbol": {"exchange": "NASDAQ", "symbol": "AAPL"}},
            ],
            "edges": [
                {"from": "start", "to": "broker"},
                {"from": "broker", "to": "fund"},
            ],
            "credentials": [{"credential_id": "cred", "type": "broker_ls_overseas_stock", "data": []}],
        }
        result = resolver.validate(workflow)
        assert result.is_valid, f"검증 실패: {result.errors}"

    def test_missing_broker_for_fundamental_error(self):
        """FundamentalNode 있는데 브로커 없음 → 에러"""
        resolver = WorkflowResolver()
        workflow = {
            "id": "test-fund-no-broker",
            "name": "브로커 누락 테스트",
            "nodes": [
                {"id": "start", "type": "StartNode"},
                {"id": "fund", "type": "OverseasStockFundamentalNode",
                 "symbol": {"exchange": "NASDAQ", "symbol": "AAPL"}},
            ],
            "edges": [
                {"from": "start", "to": "fund"},
            ],
            "credentials": [],
        }
        result = resolver.validate(workflow)
        assert not result.is_valid
        assert any("브로커" in e or "BrokerNode" in e for e in result.errors)

    def test_wrong_broker_for_fundamental_error(self):
        """해외선물 브로커 + FundamentalNode(주식) → 에러"""
        resolver = WorkflowResolver()
        workflow = {
            "id": "test-fund-wrong-broker",
            "name": "잘못된 브로커 테스트",
            "nodes": [
                {"id": "start", "type": "StartNode"},
                {"id": "broker", "type": "OverseasFuturesBrokerNode", "credential_id": "cred"},
                {"id": "fund", "type": "OverseasStockFundamentalNode",
                 "symbol": {"exchange": "NASDAQ", "symbol": "AAPL"}},
            ],
            "edges": [
                {"from": "start", "to": "broker"},
                {"from": "broker", "to": "fund"},
            ],
            "credentials": [{"credential_id": "cred", "type": "broker_ls_overseas_futures", "data": []}],
        }
        result = resolver.validate(workflow)
        assert not result.is_valid
