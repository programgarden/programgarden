"""
KoreaStock Executor 단위 테스트

국내주식 13개 노드의 executor 분기 테스트.
LS 로그인 및 외부 API 호출은 mock 처리.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── 공통 헬퍼 ──


def _make_mock_context(credential=None):
    """간이 ExecutionContext mock"""
    ctx = MagicMock()
    ctx.log = MagicMock()
    ctx.job_id = "test-job"
    ctx.is_running = True
    ctx.get_credential = MagicMock(
        return_value=credential or {"appkey": "k", "appsecret": "s"}
    )
    return ctx


# ── 1. _executors 매핑 확인 ──


class TestKoreaStockExecutorMapping:
    """_executors 딕셔너리에 KoreaStock 13개 노드 등록 확인"""

    EXPECTED_TYPES = [
        "KoreaStockBrokerNode",
        "KoreaStockAccountNode",
        "KoreaStockOpenOrdersNode",
        "KoreaStockMarketDataNode",
        "KoreaStockFundamentalNode",
        "KoreaStockHistoricalDataNode",
        "KoreaStockSymbolQueryNode",
        "KoreaStockNewOrderNode",
        "KoreaStockModifyOrderNode",
        "KoreaStockCancelOrderNode",
        "KoreaStockRealMarketDataNode",
        "KoreaStockRealAccountNode",
        "KoreaStockRealOrderEventNode",
    ]

    def test_all_korea_stock_nodes_in_executors(self):
        from programgarden.executor import WorkflowExecutor

        executor = WorkflowExecutor()
        for node_type in self.EXPECTED_TYPES:
            assert node_type in executor._executors, f"{node_type} not in _executors"

    def test_executor_count(self):
        """최소 13개 KoreaStock 노드가 등록되어 있어야 함"""
        from programgarden.executor import WorkflowExecutor

        executor = WorkflowExecutor()
        korea_stock_keys = [
            k for k in executor._executors if k.startswith("KoreaStock")
        ]
        assert len(korea_stock_keys) == 13


# Domestic account/open-order response contracts are exercised with actual SDK
# models in test_domestic_node_evidence.py. The former MagicMock responses here
# invented unavailable CSPAQ12300 summary fields and hid unsettled holdings.


# ── 4. MarketDataNodeExecutor._fetch_korea_stock ──


class TestKoreaStockMarketDataExecutor:
    """국내주식 현재가 조회 (t1102)"""

    def _make_executor(self):
        from programgarden.executor import MarketDataNodeExecutor
        return MarketDataNodeExecutor()

    @pytest.mark.asyncio
    @patch("programgarden.executor.ensure_ls_login")
    async def test_market_data_normal(self, mock_login):
        """정상 현재가 조회"""
        executor = self._make_executor()
        ctx = _make_mock_context()

        mock_ls = MagicMock()
        mock_login.return_value = (mock_ls, True, None)

        blk = MagicMock()
        blk.hname = "삼성전자"
        blk.price = 65000
        blk.change = 500
        blk.sign = "2"  # 상승
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

        symbols = [{"symbol": "005930"}]
        result = await executor._fetch_korea_stock(symbols, ctx, "md1")

        assert len(result["values"]) == 1
        v = result["values"][0]
        assert v["symbol"] == "005930"
        assert v["exchange"] == "KRX"
        assert v["price"] == 65000
        assert v["change"] == 500  # sign=2 → 양수

    @pytest.mark.asyncio
    @patch("programgarden.executor.ensure_ls_login")
    async def test_market_data_sign_negative(self, mock_login):
        """sign=5(하락) → change 음수 변환"""
        executor = self._make_executor()
        ctx = _make_mock_context()

        mock_ls = MagicMock()
        mock_login.return_value = (mock_ls, True, None)

        blk = MagicMock()
        blk.hname = "LG화학"
        blk.price = 300000
        blk.change = 5000
        blk.sign = "5"  # 하락
        blk.diff = -1.64
        blk.volume = 500000
        blk.open = 305000
        blk.high = 306000
        blk.low = 299000
        blk.per = 20.0
        blk.pbrx = 0.9

        resp = MagicMock()
        resp.block = blk

        mock_t1102 = MagicMock()
        mock_t1102.req = MagicMock(return_value=resp)

        mock_market = MagicMock()
        mock_market.t1102 = MagicMock(return_value=mock_t1102)
        mock_ks = MagicMock()
        mock_ks.market = MagicMock(return_value=mock_market)
        mock_ls.korea_stock = MagicMock(return_value=mock_ks)

        symbols = [{"symbol": "051910"}]
        result = await executor._fetch_korea_stock(symbols, ctx, "md1")

        assert result["values"][0]["change"] == -5000

    @pytest.mark.asyncio
    @patch("programgarden.executor.ensure_ls_login")
    async def test_market_data_login_failure(self, mock_login):
        """LS 로그인 실패 시 에러 결과"""
        executor = self._make_executor()
        ctx = _make_mock_context()
        mock_login.return_value = (None, False, "Login failed")

        result = await executor._fetch_korea_stock([{"symbol": "005930"}], ctx, "md1")
        assert "error" in result


# ── 5. FundamentalNodeExecutor._fetch_korea_stock ──


class TestKoreaStockFundamentalExecutor:
    """국내주식 펀더멘털 조회 (t1102)"""

    def _make_executor(self):
        from programgarden.executor import FundamentalNodeExecutor
        return FundamentalNodeExecutor()

    @pytest.mark.asyncio
    @patch("programgarden.executor.ensure_ls_login")
    async def test_fundamental_normal(self, mock_login):
        """PER, PBR, 시가총액 등 펀더멘털 데이터 조회"""
        executor = self._make_executor()
        ctx = _make_mock_context()

        mock_ls = MagicMock()
        mock_login.return_value = (mock_ls, True, None)

        blk = MagicMock()
        blk.hname = "삼성전자"
        blk.price = 65000
        blk.volume = 15000000
        blk.diff = 0.77
        blk.per = 12.5
        blk.pbrx = 1.2
        blk.total = 388000  # 시가총액 (억원)
        blk.listing = 5969783  # 상장주식수 (천)
        blk.high52w = 78000
        blk.low52w = 52000
        blk.bfeps = 5200.0

        resp = MagicMock()
        resp.block = blk

        mock_t1102 = MagicMock()
        mock_t1102.req = MagicMock(return_value=resp)

        mock_market = MagicMock()
        mock_market.t1102 = MagicMock(return_value=mock_t1102)
        mock_ks = MagicMock()
        mock_ks.market = MagicMock(return_value=mock_market)
        mock_ls.korea_stock = MagicMock(return_value=mock_ks)

        symbols = [{"symbol": "005930"}]
        credential = {"appkey": "k", "appsecret": "s"}
        result = await executor._fetch_korea_stock(symbols, credential, ctx, "fd1")

        assert len(result["values"]) == 1
        v = result["values"][0]
        assert v["per"] == 12.5
        assert v["pbr"] == 1.2
        assert v["market_cap"] == 388000
        assert v["high_52w"] == 78000


# ── 6. HistoricalDataNodeExecutor._fetch_korea_stock ──


class TestKoreaStockHistoricalExecutor:
    """국내주식 차트 데이터 조회 (t8451)"""

    def _make_executor(self):
        from programgarden.executor import HistoricalDataNodeExecutor
        return HistoricalDataNodeExecutor()

    @pytest.mark.asyncio
    @patch("programgarden.executor.ensure_ls_login")
    async def test_historical_ohlcv(self, mock_login):
        """일봉 OHLCV 데이터 조회"""
        executor = self._make_executor()
        ctx = _make_mock_context()

        mock_ls = MagicMock()
        mock_login.return_value = (mock_ls, True, None)

        bar1 = MagicMock()
        bar1.date = "20260301"
        bar1.open = 64000
        bar1.high = 65500
        bar1.low = 63500
        bar1.close = 65000
        bar1.jdiff_vol = 15000000

        bar2 = MagicMock()
        bar2.date = "20260302"
        bar2.open = 65000
        bar2.high = 66000
        bar2.low = 64500
        bar2.close = 65500
        bar2.jdiff_vol = 12000000

        resp = MagicMock()
        resp.block1 = [bar2, bar1]  # 역순으로 넣어 정렬 테스트

        mock_t8451 = MagicMock()
        mock_t8451.req = MagicMock(return_value=resp)

        mock_chart = MagicMock()
        mock_chart.t8451 = MagicMock(return_value=mock_t8451)
        mock_ks = MagicMock()
        mock_ks.chart = MagicMock(return_value=mock_chart)
        mock_ls.korea_stock = MagicMock(return_value=mock_ks)

        result = await executor._fetch_korea_stock(
            symbols=["005930"],
            start_date="20260301",
            end_date="20260302",
            interval="1d",
            context=ctx,
            node_id="hist1",
        )

        assert len(result) == 1
        entry = result[0]
        assert entry["symbol"] == "005930"
        assert entry["exchange"] == "KRX"
        # 시간순 정렬 확인 (오래된 것부터)
        assert entry["time_series"][0]["date"] == "20260301"
        assert entry["time_series"][1]["date"] == "20260302"
        assert entry["time_series"][0]["close"] == 65000

    @pytest.mark.asyncio
    @patch("programgarden.executor.ensure_ls_login")
    async def test_historical_no_credential(self, mock_login):
        """credential 없으면 에러"""
        executor = self._make_executor()
        ctx = _make_mock_context(credential=None)
        ctx.get_credential = MagicMock(return_value=None)

        result = await executor._fetch_korea_stock(
            symbols=["005930"],
            start_date="20260301",
            end_date="20260302",
            interval="1d",
            context=ctx,
            node_id="hist1",
        )

        # 빈 결과 반환
        assert len(result) == 1
        assert result[0]["time_series"] == []


# ── 7. SymbolQueryNodeExecutor._execute_korea_stock_master ──


class TestKoreaStockSymbolQueryExecutor:
    """국내주식 종목마스터 조회 (t9945)"""

    def _make_executor(self):
        from programgarden.executor import SymbolQueryNodeExecutor
        return SymbolQueryNodeExecutor()

    @pytest.mark.asyncio
    @patch("programgarden.executor.ensure_ls_login")
    async def test_symbol_query_all(self, mock_login):
        """KOSPI + KOSDAQ 전체 조회"""
        executor = self._make_executor()
        ctx = _make_mock_context()

        mock_ls = MagicMock()
        mock_login.return_value = (mock_ls, True, None)

        # KOSPI 종목
        kospi_item = MagicMock()
        kospi_item.shcode = "005930"
        kospi_item.hname = "삼성전자"
        kospi_item.etfchk = "0"

        kospi_resp = MagicMock()
        kospi_resp.block = [kospi_item]

        # KOSDAQ 종목
        kosdaq_item = MagicMock()
        kosdaq_item.shcode = "035720"
        kosdaq_item.hname = "카카오"
        kosdaq_item.etfchk = "0"

        kosdaq_resp = MagicMock()
        kosdaq_resp.block = [kosdaq_item]

        # t9945 호출 시 gubun에 따라 다른 응답
        call_count = [0]
        responses = [kospi_resp, kosdaq_resp]

        def mock_t9945_call(**kwargs):
            mock_api = MagicMock()
            mock_api.req = MagicMock(return_value=responses[call_count[0]])
            call_count[0] += 1
            return mock_api

        mock_market = MagicMock()
        mock_market.t9945 = mock_t9945_call
        mock_ks = MagicMock()
        mock_ks.market = MagicMock(return_value=mock_market)
        mock_ls.korea_stock = MagicMock(return_value=mock_ks)

        result = await executor._execute_korea_stock_master(
            node_id="sq1",
            config={"stock_exchange": ""},
            context=ctx,
            appkey="k",
            appsecret="s",
            max_results=1000,
        )

        assert result["count"] == 2
        assert result["product"] == "korea_stock"
        symbols = result["symbols"]
        assert symbols[0]["market"] == "KOSPI"
        assert symbols[1]["market"] == "KOSDAQ"

    @pytest.mark.asyncio
    @patch("programgarden.executor.ensure_ls_login")
    async def test_symbol_query_kospi_only(self, mock_login):
        """KOSPI만 필터링"""
        executor = self._make_executor()
        ctx = _make_mock_context()

        mock_ls = MagicMock()
        mock_login.return_value = (mock_ls, True, None)

        kospi_item = MagicMock()
        kospi_item.shcode = "005930"
        kospi_item.hname = "삼성전자"
        kospi_item.etfchk = "0"

        kospi_resp = MagicMock()
        kospi_resp.block = [kospi_item]

        mock_api = MagicMock()
        mock_api.req = MagicMock(return_value=kospi_resp)

        mock_market = MagicMock()
        mock_market.t9945 = MagicMock(return_value=mock_api)
        mock_ks = MagicMock()
        mock_ks.market = MagicMock(return_value=mock_market)
        mock_ls.korea_stock = MagicMock(return_value=mock_ks)

        result = await executor._execute_korea_stock_master(
            node_id="sq1",
            config={"stock_exchange": "KOSPI"},
            context=ctx,
            appkey="k",
            appsecret="s",
            max_results=1000,
        )

        # KOSPI만 호출되어야 함 (1번)
        assert result["count"] == 1
        assert result["symbols"][0]["market"] == "KOSPI"


# ── 8. NewOrderNodeExecutor._execute_korea_stock ──


class TestKoreaStockNewOrderExecutor:
    """국내주식 신규주문 (CSPAT00601)"""

    def _make_executor(self):
        from programgarden.executor import NewOrderNodeExecutor
        return NewOrderNodeExecutor()

    @pytest.mark.asyncio
    async def test_new_order_buy_limit(self):
        """지정가 매수 주문"""
        executor = self._make_executor()
        ctx = _make_mock_context()
        ls = MagicMock()

        resp = MagicMock()
        resp.error_msg = None
        resp.block2 = MagicMock()
        resp.block2.OrdNo = 99001

        mock_order_api = MagicMock()
        mock_order_api.req_async = AsyncMock(return_value=resp)

        mock_order = MagicMock()
        mock_order.cspat00601 = MagicMock(return_value=mock_order_api)
        mock_ks = MagicMock()
        mock_ks.order = MagicMock(return_value=mock_order)
        ls.korea_stock = MagicMock(return_value=mock_ks)

        order = {"symbol": "005930", "quantity": 10, "price": 65000}
        result = await executor._execute_korea_stock(
            ls, order, "buy", "limit", {}, ctx, "ord1"
        )

        assert result["order_result"]["success"] is True
        assert result["order_result"]["order_id"] == "99001"
        assert result["order_result"]["product"] == "korea_stock"

    @pytest.mark.asyncio
    async def test_new_order_sell_market(self):
        """시장가 매도 주문 → 가격 0"""
        executor = self._make_executor()
        ctx = _make_mock_context()
        ls = MagicMock()

        resp = MagicMock()
        resp.error_msg = None
        resp.block2 = MagicMock()
        resp.block2.OrdNo = 99002

        mock_order_api = MagicMock()
        mock_order_api.req_async = AsyncMock(return_value=resp)

        mock_order = MagicMock()
        mock_order.cspat00601 = MagicMock(return_value=mock_order_api)
        mock_ks = MagicMock()
        mock_ks.order = MagicMock(return_value=mock_order)
        ls.korea_stock = MagicMock(return_value=mock_ks)

        order = {"symbol": "005930", "quantity": 10, "price": 65000}
        result = await executor._execute_korea_stock(
            ls, order, "sell", "market", {}, ctx, "ord1"
        )

        assert result["order_result"]["success"] is True

    @pytest.mark.asyncio
    async def test_new_order_records_workflow_order_ledger(self):
        """신규주문 성공 시 원장(record_workflow_order)에 기록되어야 한다.

        이 호출이 빠져 있으면 SC1 체결이 `_check_workflow_order` 에서 항상 False 가
        되고, 남는 판단 기준이 매체코드뿐이라 'workflow' 분류가 한 건도 생기지
        않는다 — personal_metrics 승률·손익비에서 국내주식 체결이 전량 누락된다.
        주문일자는 브로커 날짜가 아니라 **로컬 날짜**여야 한다(체결 대조가
        (order_no, order_date) 로 이뤄지고 SC1 프레임에는 주문일자가 없다).
        """
        from datetime import datetime

        executor = self._make_executor()
        ctx = _make_mock_context()
        ls = MagicMock()

        resp = MagicMock()
        resp.error_msg = None
        resp.block2 = MagicMock()
        resp.block2.OrdNo = 99003

        mock_order_api = MagicMock()
        mock_order_api.req_async = AsyncMock(return_value=resp)

        mock_order = MagicMock()
        mock_order.cspat00601 = MagicMock(return_value=mock_order_api)
        mock_ks = MagicMock()
        mock_ks.order = MagicMock(return_value=mock_order)
        ls.korea_stock = MagicMock(return_value=mock_ks)

        order = {"symbol": "005930", "quantity": 10, "price": 65000}
        result = await executor._execute_korea_stock(
            ls, order, "buy", "limit", {}, ctx, "ord-ledger"
        )

        assert result["order_result"]["success"] is True
        ctx.record_workflow_order.assert_called_once()
        kwargs = ctx.record_workflow_order.call_args.kwargs
        assert kwargs["order_no"] == "99003"
        assert kwargs["order_date"] == datetime.now().strftime("%Y%m%d")
        assert kwargs["symbol"] == "005930"
        assert kwargs["exchange"] == "KRX"
        assert kwargs["side"] == "buy"
        assert kwargs["quantity"] == 10
        assert kwargs["price"] == 65000.0
        assert kwargs["node_id"] == "ord-ledger"

    @pytest.mark.asyncio
    async def test_new_order_market_records_zero_price_not_requested_price(self):
        """시장가는 브로커에 보낸 값(0.0)을 기록한다 — 체결 시 실체결가로 갱신된다."""
        executor = self._make_executor()
        ctx = _make_mock_context()
        ls = MagicMock()

        resp = MagicMock()
        resp.error_msg = None
        resp.block2 = MagicMock()
        resp.block2.OrdNo = 99004

        mock_order_api = MagicMock()
        mock_order_api.req_async = AsyncMock(return_value=resp)

        mock_order = MagicMock()
        mock_order.cspat00601 = MagicMock(return_value=mock_order_api)
        mock_ks = MagicMock()
        mock_ks.order = MagicMock(return_value=mock_order)
        ls.korea_stock = MagicMock(return_value=mock_ks)

        order = {"symbol": "005930", "quantity": 10, "price": 65000}
        await executor._execute_korea_stock(
            ls, order, "sell", "market", {}, ctx, "ord-market"
        )

        assert ctx.record_workflow_order.call_args.kwargs["price"] == 0.0

    @pytest.mark.asyncio
    async def test_new_order_failure_does_not_record_ledger(self):
        """거부/빈 주문번호는 원장에 남기지 않는다(존재하지 않는 주문의 유령 행 금지)."""
        executor = self._make_executor()
        ctx = _make_mock_context()
        ls = MagicMock()

        resp = MagicMock()
        resp.error_msg = None
        resp.rsp_cd = "40300"
        resp.rsp_msg = "주문가능금액 부족"
        resp.block2 = None

        mock_order_api = MagicMock()
        mock_order_api.req_async = AsyncMock(return_value=resp)

        mock_order = MagicMock()
        mock_order.cspat00601 = MagicMock(return_value=mock_order_api)
        mock_ks = MagicMock()
        mock_ks.order = MagicMock(return_value=mock_order)
        ls.korea_stock = MagicMock(return_value=mock_ks)

        order = {"symbol": "005930", "quantity": 10, "price": 65000}
        result = await executor._execute_korea_stock(
            ls, order, "buy", "limit", {}, ctx, "ord-reject"
        )

        assert result["order_result"]["success"] is False
        ctx.record_workflow_order.assert_not_called()

    @pytest.mark.asyncio
    async def test_ledger_write_failure_cannot_revoke_accepted_order(self):
        """원장 기록이 실패해도 이미 접수된 주문을 실패로 뒤집지 않는다.

        Legacy stores remain best effort; their failure cannot revoke ACK —
        해외선물 신규주문 경로가 쓰는 규약과 같다. 이 호출이 메서드 전체 try 안에
        벌거벗고 있으면 예외가 올라가 `_order_result(False, ...)` 가 되고,
        브로커에는 실제로 들어간 주문이 워크플로우에는 '실패' 로 보인다.
        """
        executor = self._make_executor()
        ctx = _make_mock_context()
        ctx.record_workflow_order = MagicMock(side_effect=RuntimeError("ledger down"))
        ls = MagicMock()

        resp = MagicMock()
        resp.error_msg = None
        resp.block2 = MagicMock()
        resp.block2.OrdNo = 99005

        mock_order_api = MagicMock()
        mock_order_api.req_async = AsyncMock(return_value=resp)

        mock_order = MagicMock()
        mock_order.cspat00601 = MagicMock(return_value=mock_order_api)
        mock_ks = MagicMock()
        mock_ks.order = MagicMock(return_value=mock_order)
        ls.korea_stock = MagicMock(return_value=mock_ks)

        order = {"symbol": "005930", "quantity": 10, "price": 65000}
        result = await executor._execute_korea_stock(
            ls, order, "buy", "limit", {}, ctx, "ord-ledger-fail"
        )

        assert result["order_result"]["success"] is True
        assert result["order_result"]["order_id"] == "99005"

    @pytest.mark.asyncio
    async def test_new_order_api_error(self):
        """주문 API 에러 시 success=False"""
        executor = self._make_executor()
        ctx = _make_mock_context()
        ls = MagicMock()

        resp = MagicMock()
        resp.error_msg = "주문 실패"

        mock_order_api = MagicMock()
        mock_order_api.req_async = AsyncMock(return_value=resp)

        mock_order = MagicMock()
        mock_order.cspat00601 = MagicMock(return_value=mock_order_api)
        mock_ks = MagicMock()
        mock_ks.order = MagicMock(return_value=mock_order)
        ls.korea_stock = MagicMock(return_value=mock_ks)

        order = {"symbol": "005930", "quantity": 10, "price": 65000}
        result = await executor._execute_korea_stock(
            ls, order, "buy", "limit", {}, ctx, "ord1"
        )

        assert result["order_result"]["success"] is False


# ── 9. ModifyOrderNodeExecutor._modify_korea_stock ──


class TestKoreaStockModifyOrderExecutor:
    """국내주식 정정주문 (CSPAT00701)"""

    def _make_executor(self):
        from programgarden.executor import ModifyOrderNodeExecutor
        return ModifyOrderNodeExecutor()

    @pytest.mark.asyncio
    async def test_modify_order_normal(self):
        """정상 정정주문"""
        executor = self._make_executor()
        ctx = _make_mock_context()
        ls = MagicMock()

        resp = MagicMock()
        resp.error_msg = None
        resp.block2 = MagicMock()
        resp.block2.OrdNo = 99010

        mock_order_api = MagicMock()
        mock_order_api.req_async = AsyncMock(return_value=resp)

        mock_order = MagicMock()
        mock_order.cspat00701 = MagicMock(return_value=mock_order_api)
        mock_ks = MagicMock()
        mock_ks.order = MagicMock(return_value=mock_order)
        ls.korea_stock = MagicMock(return_value=mock_ks)

        result = await executor._modify_korea_stock(
            ls, "99001", "005930", 5, 66000.0, {}, ctx, "mod1"
        )

        assert result["modify_result"]["success"] is True
        assert result["modify_result"]["new_order_id"] == "99010"
        assert result["modify_result"]["product"] == "korea_stock"
        assert result["modified_order"]["status"] == "modified"

    @pytest.mark.asyncio
    async def test_modify_order_error(self):
        """정정주문 API 에러"""
        executor = self._make_executor()
        ctx = _make_mock_context()
        ls = MagicMock()

        resp = MagicMock()
        resp.error_msg = "정정 실패"

        mock_order_api = MagicMock()
        mock_order_api.req_async = AsyncMock(return_value=resp)

        mock_order = MagicMock()
        mock_order.cspat00701 = MagicMock(return_value=mock_order_api)
        mock_ks = MagicMock()
        mock_ks.order = MagicMock(return_value=mock_order)
        ls.korea_stock = MagicMock(return_value=mock_ks)

        result = await executor._modify_korea_stock(
            ls, "99001", "005930", 5, 66000.0, {}, ctx, "mod1"
        )

        assert result["modify_result"]["success"] is False
        assert result["modified_order"] is None


# ── 10. CancelOrderNodeExecutor._cancel_korea_stock ──


class TestKoreaStockCancelOrderExecutor:
    """국내주식 취소주문 (CSPAT00801)"""

    def _make_executor(self):
        from programgarden.executor import CancelOrderNodeExecutor
        return CancelOrderNodeExecutor()

    @pytest.mark.asyncio
    async def test_cancel_order_normal(self):
        """정상 취소주문"""
        executor = self._make_executor()
        ctx = _make_mock_context()
        ls = MagicMock()

        resp = MagicMock()
        resp.error_msg = None
        resp.block2.OrdNo = 99002

        mock_order_api = MagicMock()
        mock_order_api.req_async = AsyncMock(return_value=resp)

        mock_order = MagicMock()
        mock_order.cspat00801 = MagicMock(return_value=mock_order_api)
        mock_ks = MagicMock()
        mock_ks.order = MagicMock(return_value=mock_order)
        ls.korea_stock = MagicMock(return_value=mock_ks)

        result = await executor._cancel_korea_stock(
            ls, "99001", "005930", {"quantity": 10}, ctx, "can1"
        )

        assert result["cancel_result"]["success"] is True
        assert result["cancel_result"]["product"] == "korea_stock"
        assert result["cancelled_order"]["status"] == "cancel_requested"
        assert result["cancel_result"]["confirmation_pending"] is True

    @pytest.mark.asyncio
    async def test_cancel_order_api_error(self):
        """취소주문 API 에러"""
        executor = self._make_executor()
        ctx = _make_mock_context()
        ls = MagicMock()

        resp = MagicMock()
        resp.error_msg = "취소 실패"

        mock_order_api = MagicMock()
        mock_order_api.req_async = AsyncMock(return_value=resp)

        mock_order = MagicMock()
        mock_order.cspat00801 = MagicMock(return_value=mock_order_api)
        mock_ks = MagicMock()
        mock_ks.order = MagicMock(return_value=mock_order)
        ls.korea_stock = MagicMock(return_value=mock_ks)

        result = await executor._cancel_korea_stock(
            ls, "99001", "005930", {}, ctx, "can1"
        )

        assert result["cancel_result"]["success"] is False
        assert result["cancelled_order"] is None
