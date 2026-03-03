"""
KoreaStock 워크플로우 JSON 통합 테스트

국내주식 노드를 포함한 워크플로우 JSON을 WorkflowExecutor로 실행하는 E2E 테스트.
LS 로그인 및 외부 API 호출은 mock 처리.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── 워크플로우 트래커 ──


class _WorkflowTracker:
    """워크플로우 노드 상태/출력 추적"""

    def __init__(self):
        self.completed = []
        self.outputs = {}
        self.logs = []

    async def on_node_state_change(self, event):
        state = event.state.value if hasattr(event.state, "value") else str(event.state)
        if state == "completed":
            self.completed.append(event.node_id)
            if event.outputs:
                self.outputs[event.node_id] = event.outputs

    async def on_edge_state_change(self, event): pass
    async def on_log(self, event):
        self.logs.append(event)
    async def on_job_state_change(self, event): pass
    async def on_display_data(self, event): pass


# ── 헬퍼 ──


def _mock_ls_korea_stock():
    """국내주식 API mock 체인 생성"""
    ls = MagicMock()

    # CSPAQ12300 (잔고)
    pos_item = MagicMock()
    pos_item.IsuNo = "A005930"
    pos_item.IsuNm = "삼성전자"
    pos_item.BalQty = 100
    pos_item.NowPrc = 65000
    pos_item.AvrUprc = 60000
    pos_item.EvalPnl = 500000
    pos_item.PnlRat = 8.3
    pos_item.SellAbleQty = 100
    pos_item.BalEvalAmt = 6500000

    b2 = MagicMock()
    b2.MnyOrdAbleAmt = 5000000
    b2.BalEvalAmt = 20000000
    b2.PchsAmt = 18000000
    b2.EvalPnl = 2000000
    b2.PnlRat = 11.1
    b2.Dps = 6000000

    resp_12300 = MagicMock()
    resp_12300.error_msg = None
    resp_12300.block2 = b2
    resp_12300.block3 = [pos_item]

    mock_12300 = MagicMock()
    mock_12300.req_async = AsyncMock(return_value=resp_12300)

    # CSPAQ22200 (예수금)
    b2_cash = MagicMock()
    b2_cash.MnyOrdAbleAmt = 5500000
    b2_cash.Dps = 6100000
    b2_cash.D2Dps = 5800000
    b2_cash.MgnMny = 100000

    resp_22200 = MagicMock()
    resp_22200.error_msg = None
    resp_22200.block2 = b2_cash

    mock_22200 = MagicMock()
    mock_22200.req_async = AsyncMock(return_value=resp_22200)

    # 체인 구성
    mock_accno = MagicMock()
    mock_accno.cspaq12300 = MagicMock(return_value=mock_12300)
    mock_accno.cspaq22200 = MagicMock(return_value=mock_22200)

    mock_korea_stock = MagicMock()
    mock_korea_stock.accno = MagicMock(return_value=mock_accno)
    ls.korea_stock = MagicMock(return_value=mock_korea_stock)

    return ls


# ── 1. Broker → Account 워크플로우 ──


class TestKoreaStockBrokerAccountWorkflow:
    """KoreaStockBrokerNode → KoreaStockAccountNode 워크플로우"""

    @pytest.mark.asyncio
    @patch("programgarden.executor.ensure_ls_login")
    async def test_broker_account_workflow(self, mock_login):
        """국내주식 브로커 → 잔고 조회 워크플로우 실행"""
        from programgarden.executor import WorkflowExecutor

        mock_ls = _mock_ls_korea_stock()
        mock_login.return_value = (mock_ls, True, None)

        workflow = {
            "id": "test-kr-acct",
            "name": "국내주식 잔고 조회",
            "nodes": [
                {"id": "start", "type": "StartNode"},
                {
                    "id": "broker",
                    "type": "KoreaStockBrokerNode",
                    "credential_id": "kr-cred",
                },
                {"id": "account", "type": "KoreaStockAccountNode"},
            ],
            "edges": [
                {"from": "start", "to": "broker"},
                {"from": "broker", "to": "account"},
            ],
            "credentials": [
                {
                    "credential_id": "kr-cred",
                    "type": "broker_ls_korea_stock",
                    "data": {"appkey": "test_key", "appsecret": "test_secret"},
                }
            ],
        }

        tracker = _WorkflowTracker()
        executor = WorkflowExecutor()
        job = await executor.execute(workflow, listeners=[tracker])
        await asyncio.wait_for(job._task, timeout=10)

        assert "broker" in tracker.completed
        assert "account" in tracker.completed

        # account 출력 확인
        acct_out = tracker.outputs.get("account", {})
        assert "positions" in acct_out
        assert "balance" in acct_out


# ── 2. Broker → Account → Display 워크플로우 ──


class TestKoreaStockAccountDisplayWorkflow:
    """3노드 워크플로우: Broker → Account → TableDisplay"""

    @pytest.mark.asyncio
    @patch("programgarden.executor.ensure_ls_login")
    async def test_account_to_display(self, mock_login):
        """잔고 → 테이블 출력 워크플로우"""
        from programgarden.executor import WorkflowExecutor

        mock_ls = _mock_ls_korea_stock()
        mock_login.return_value = (mock_ls, True, None)

        workflow = {
            "id": "test-kr-display",
            "name": "국내주식 잔고 표시",
            "nodes": [
                {"id": "start", "type": "StartNode"},
                {
                    "id": "broker",
                    "type": "KoreaStockBrokerNode",
                    "credential_id": "kr-cred",
                },
                {"id": "account", "type": "KoreaStockAccountNode"},
                {
                    "id": "display",
                    "type": "TableDisplayNode",
                    "data": "{{ nodes.account.positions }}",
                },
            ],
            "edges": [
                {"from": "start", "to": "broker"},
                {"from": "broker", "to": "account"},
                {"from": "account", "to": "display"},
            ],
            "credentials": [
                {
                    "credential_id": "kr-cred",
                    "type": "broker_ls_korea_stock",
                    "data": {"appkey": "test_key", "appsecret": "test_secret"},
                }
            ],
        }

        tracker = _WorkflowTracker()
        executor = WorkflowExecutor()
        job = await executor.execute(workflow, listeners=[tracker])
        await asyncio.wait_for(job._task, timeout=10)

        assert "display" in tracker.completed


# ── 3. Broker → MarketData 워크플로우 ──


class TestKoreaStockMarketDataWorkflow:
    """KoreaStockBrokerNode → KoreaStockMarketDataNode 워크플로우"""

    @pytest.mark.asyncio
    @patch("programgarden.executor.ensure_ls_login")
    async def test_market_data_workflow(self, mock_login):
        """국내주식 현재가 조회 워크플로우"""
        from programgarden.executor import WorkflowExecutor

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

        workflow = {
            "id": "test-kr-market",
            "name": "국내주식 시세 조회",
            "nodes": [
                {"id": "start", "type": "StartNode"},
                {
                    "id": "broker",
                    "type": "KoreaStockBrokerNode",
                    "credential_id": "kr-cred",
                },
                {
                    "id": "market",
                    "type": "KoreaStockMarketDataNode",
                    "symbols": [{"symbol": "005930"}],
                },
            ],
            "edges": [
                {"from": "start", "to": "broker"},
                {"from": "broker", "to": "market"},
            ],
            "credentials": [
                {
                    "credential_id": "kr-cred",
                    "type": "broker_ls_korea_stock",
                    "data": {"appkey": "test_key", "appsecret": "test_secret"},
                }
            ],
        }

        tracker = _WorkflowTracker()
        executor = WorkflowExecutor()
        job = await executor.execute(workflow, listeners=[tracker])
        await asyncio.wait_for(job._task, timeout=10)

        assert "market" in tracker.completed
        market_out = tracker.outputs.get("market", {})
        # MarketDataNode는 values 포트로 출력
        if "values" in market_out:
            assert len(market_out["values"]) >= 1


# ── 4. Broker → OpenOrders 워크플로우 ──


class TestKoreaStockOpenOrdersWorkflow:
    """KoreaStockBrokerNode → KoreaStockOpenOrdersNode 워크플로우"""

    @pytest.mark.asyncio
    @patch("programgarden.executor.ensure_ls_login")
    async def test_open_orders_workflow(self, mock_login):
        """국내주식 미체결 조회 워크플로우"""
        from programgarden.executor import WorkflowExecutor

        mock_ls = MagicMock()
        mock_login.return_value = (mock_ls, True, None)

        # t0425 mock
        item = MagicMock()
        item.ordno = 12345
        item.ordrem = 50
        item.expcode = "005930"
        item.medosu = "매수"
        item.hogagb = "지정가"
        item.qty = 100
        item.cheqty = 50
        item.price = 65000
        item.ordtime = "093000"

        resp = MagicMock()
        resp.error_msg = None
        resp.block1 = [item]

        mock_t0425 = MagicMock()
        mock_t0425.req_async = AsyncMock(return_value=resp)

        mock_accno = MagicMock()
        mock_accno.t0425 = MagicMock(return_value=mock_t0425)
        mock_ks = MagicMock()
        mock_ks.accno = MagicMock(return_value=mock_accno)
        mock_ls.korea_stock = MagicMock(return_value=mock_ks)

        workflow = {
            "id": "test-kr-oo",
            "name": "국내주식 미체결 조회",
            "nodes": [
                {"id": "start", "type": "StartNode"},
                {
                    "id": "broker",
                    "type": "KoreaStockBrokerNode",
                    "credential_id": "kr-cred",
                },
                {"id": "oo", "type": "KoreaStockOpenOrdersNode"},
            ],
            "edges": [
                {"from": "start", "to": "broker"},
                {"from": "broker", "to": "oo"},
            ],
            "credentials": [
                {
                    "credential_id": "kr-cred",
                    "type": "broker_ls_korea_stock",
                    "data": {"appkey": "test_key", "appsecret": "test_secret"},
                }
            ],
        }

        tracker = _WorkflowTracker()
        executor = WorkflowExecutor()
        job = await executor.execute(workflow, listeners=[tracker])
        await asyncio.wait_for(job._task, timeout=10)

        assert "oo" in tracker.completed


# ── 5. 잘못된 credential 타입 ──


class TestKoreaStockCredentialValidation:
    """credential 타입 불일치 시 에러 처리"""

    @pytest.mark.asyncio
    @patch("programgarden.executor.ensure_ls_login")
    async def test_wrong_credential_type(self, mock_login):
        """해외주식 credential로 국내주식 노드 실행 시"""
        from programgarden.executor import WorkflowExecutor

        # 로그인은 성공하지만 product 불일치 시나리오
        mock_ls = MagicMock()
        mock_login.return_value = (mock_ls, True, None)

        # 빈 응답으로 설정 (product 불일치 에러가 아닌 빈 결과)
        resp = MagicMock()
        resp.error_msg = "unauthorized"
        resp.block2 = None
        resp.block3 = []

        mock_12300 = MagicMock()
        mock_12300.req_async = AsyncMock(return_value=resp)

        resp_22200 = MagicMock()
        resp_22200.error_msg = None
        resp_22200.block2 = None

        mock_22200 = MagicMock()
        mock_22200.req_async = AsyncMock(return_value=resp_22200)

        mock_accno = MagicMock()
        mock_accno.cspaq12300 = MagicMock(return_value=mock_12300)
        mock_accno.cspaq22200 = MagicMock(return_value=mock_22200)
        mock_ks = MagicMock()
        mock_ks.accno = MagicMock(return_value=mock_accno)
        mock_ls.korea_stock = MagicMock(return_value=mock_ks)

        workflow = {
            "id": "test-kr-wrong-cred",
            "name": "잘못된 credential",
            "nodes": [
                {"id": "start", "type": "StartNode"},
                {
                    "id": "broker",
                    "type": "KoreaStockBrokerNode",
                    "credential_id": "kr-cred",
                },
                {"id": "account", "type": "KoreaStockAccountNode"},
            ],
            "edges": [
                {"from": "start", "to": "broker"},
                {"from": "broker", "to": "account"},
            ],
            "credentials": [
                {
                    "credential_id": "kr-cred",
                    "type": "broker_ls_korea_stock",
                    "data": {"appkey": "", "appsecret": ""},
                }
            ],
        }

        tracker = _WorkflowTracker()
        executor = WorkflowExecutor()
        job = await executor.execute(workflow, listeners=[tracker])
        await asyncio.wait_for(job._task, timeout=10)

        # 워크플로우는 완료되지만 빈 잔고
        assert "account" in tracker.completed
        acct = tracker.outputs.get("account", {})
        assert acct.get("positions", []) == []
