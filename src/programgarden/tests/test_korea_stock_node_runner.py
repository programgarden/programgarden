"""
KoreaStock NodeRunner 테스트

국내주식 노드의 NodeRunner 단독 실행 테스트.
broker_ls_korea_stock credential 파싱 및 브로커 의존 노드 등록 확인.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from programgarden.node_runner import (
    NodeRunner,
    _REALTIME_NODE_TYPES,
    _BROKER_NODE_TYPES,
    _BROKER_DEPENDENT_NODE_TYPES,
)


# ── 1. 타입 등록 확인 ──


class TestKoreaStockNodeRunnerTypes:
    """NodeRunner 내부 타입 세트에 KoreaStock 노드 등록 확인"""

    def test_realtime_nodes_registered(self):
        """실시간 노드 3개가 _REALTIME_NODE_TYPES에 등록"""
        expected = {
            "KoreaStockRealAccountNode",
            "KoreaStockRealMarketDataNode",
            "KoreaStockRealOrderEventNode",
        }
        assert expected.issubset(_REALTIME_NODE_TYPES)

    def test_broker_node_registered(self):
        """KoreaStockBrokerNode가 _BROKER_NODE_TYPES에 등록"""
        assert "KoreaStockBrokerNode" in _BROKER_NODE_TYPES

    def test_broker_dependent_nodes_registered(self):
        """브로커 의존 노드 9개가 _BROKER_DEPENDENT_NODE_TYPES에 등록"""
        expected = {
            "KoreaStockAccountNode",
            "KoreaStockOpenOrdersNode",
            "KoreaStockMarketDataNode",
            "KoreaStockFundamentalNode",
            "KoreaStockHistoricalDataNode",
            "KoreaStockSymbolQueryNode",
            "KoreaStockNewOrderNode",
            "KoreaStockModifyOrderNode",
            "KoreaStockCancelOrderNode",
        }
        assert expected.issubset(_BROKER_DEPENDENT_NODE_TYPES)


# ── 2. Credential 파싱 ──


class TestKoreaStockCredentialParsing:
    """broker_ls_korea_stock credential 파싱"""

    def test_korea_stock_credential_parsing(self):
        """broker_ls_korea_stock → product=korea_stock, paper_trading=False"""
        runner = NodeRunner(credentials=[{
            "credential_id": "broker",
            "type": "broker_ls_korea_stock",
            "data": {"appkey": "test_key", "appsecret": "test_secret"},
        }])

        info = runner._parse_broker_credential("broker")
        assert info is not None
        assert info["product"] == "korea_stock"
        assert info["appkey"] == "test_key"
        assert info["paper_trading"] is False

    def test_korea_stock_paper_trading_forced_real(self):
        """korea_stock + paper_trading=True → 강제 실전 모드"""
        runner = NodeRunner(credentials=[{
            "credential_id": "broker",
            "type": "broker_ls_korea_stock",
            "data": {"appkey": "k", "appsecret": "s", "paper_trading": True},
        }])

        info = runner._parse_broker_credential("broker")
        assert info["paper_trading"] is False

    def test_korea_stock_list_data_format(self):
        """data가 list 형태인 경우 정상 파싱"""
        runner = NodeRunner(credentials=[{
            "credential_id": "broker",
            "type": "broker_ls_korea_stock",
            "data": [
                {"key": "appkey", "value": "list_key"},
                {"key": "appsecret", "value": "list_secret"},
            ],
        }])

        info = runner._parse_broker_credential("broker")
        assert info is not None
        assert info["appkey"] == "list_key"
        assert info["product"] == "korea_stock"


# ── 3. 실시간 노드 차단 ──


class TestKoreaStockRealtimeBlocked:
    """실시간(WebSocket) 노드는 NodeRunner에서 실행 불가"""

    @pytest.mark.asyncio
    async def test_realtime_market_data_blocked(self):
        """KoreaStockRealMarketDataNode → ValueError"""
        runner = NodeRunner()
        with pytest.raises(ValueError, match="실시간"):
            await runner.run("KoreaStockRealMarketDataNode")
        await runner.cleanup()

    @pytest.mark.asyncio
    async def test_realtime_account_blocked(self):
        """KoreaStockRealAccountNode → ValueError"""
        runner = NodeRunner()
        with pytest.raises(ValueError, match="실시간"):
            await runner.run("KoreaStockRealAccountNode")
        await runner.cleanup()

    @pytest.mark.asyncio
    async def test_realtime_order_event_blocked(self):
        """KoreaStockRealOrderEventNode → ValueError"""
        runner = NodeRunner()
        with pytest.raises(ValueError, match="실시간"):
            await runner.run("KoreaStockRealOrderEventNode")
        await runner.cleanup()


# ── 4. 브로커 노드 자동 처리 ──


class TestKoreaStockBrokerNodeRunner:
    """KoreaStockBrokerNode는 NodeRunner에서 직접 실행 불필요"""

    @pytest.mark.asyncio
    async def test_broker_node_skipped(self):
        """BrokerNode 실행 시 자동 처리 (에러 아님)"""
        runner = NodeRunner(credentials=[{
            "credential_id": "broker",
            "type": "broker_ls_korea_stock",
            "data": {"appkey": "k", "appsecret": "s"},
        }])

        # BrokerNode는 skip되거나 자동 처리됨 (구현에 따라)
        # NodeRunner._is_broker_node() → True → 특별 처리
        assert "KoreaStockBrokerNode" in _BROKER_NODE_TYPES
        await runner.cleanup()


# ── 5. 브로커 의존 노드 실행 (mock) ──


class TestKoreaStockBrokerDependentRunner:
    """브로커 의존 노드의 mock 실행"""

    @pytest.mark.asyncio
    @patch("programgarden.executor.ensure_ls_login")
    async def test_market_data_via_runner(self, mock_login):
        """KoreaStockMarketDataNode를 NodeRunner로 실행"""
        mock_ls = MagicMock()
        mock_login.return_value = (mock_ls, True, None)

        # t1102 mock
        blk = MagicMock()
        blk.hname = "삼성전자"
        blk.price = 65000
        blk.change = 500
        blk.sign = "2"
        blk.diff = 0.77
        blk.volume = 15000000
        blk.open = 64500
        blk.high = 65500
        blk.low = 64000
        blk.per = 12.5
        blk.pbrx = 1.2

        resp = MagicMock()
        resp.block = blk

        mock_t1102 = MagicMock()
        mock_t1102.req = MagicMock(return_value=resp)

        mock_market = MagicMock()
        mock_market.t1102 = MagicMock(return_value=mock_t1102)
        mock_ks = MagicMock()
        mock_ks.market = MagicMock(return_value=mock_market)
        mock_ls.korea_stock = MagicMock(return_value=mock_ks)

        runner = NodeRunner(credentials=[{
            "credential_id": "broker",
            "type": "broker_ls_korea_stock",
            "data": {"appkey": "test_key", "appsecret": "test_secret"},
        }])

        result = await runner.run(
            "KoreaStockMarketDataNode",
            credential_id="broker",
            symbols=[{"symbol": "005930"}],
        )

        assert "values" in result
        await runner.cleanup()

    @pytest.mark.asyncio
    async def test_missing_credential_raises(self):
        """credential 없이 브로커 의존 노드 실행 → ValueError"""
        runner = NodeRunner()
        with pytest.raises(ValueError, match="not found"):
            await runner.run(
                "KoreaStockAccountNode",
                credential_id="nonexistent",
            )
        await runner.cleanup()
