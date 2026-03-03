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


# ── 2. AccountNodeExecutor._ls_korea_stock ──


class TestKoreaStockAccountExecutor:
    """국내주식 잔고 조회 (CSPAQ12300 + CSPAQ22200)"""

    def _make_executor(self):
        from programgarden.executor import AccountNodeExecutor
        return AccountNodeExecutor()

    def _build_ls_mock(self, cspaq12300_resp, cspaq22200_resp):
        """LS API 체인 mock 구성"""
        ls = MagicMock()

        mock_12300 = MagicMock()
        mock_12300.req_async = AsyncMock(return_value=cspaq12300_resp)

        mock_22200 = MagicMock()
        mock_22200.req_async = AsyncMock(return_value=cspaq22200_resp)

        mock_accno = MagicMock()
        mock_accno.cspaq12300 = MagicMock(return_value=mock_12300)
        mock_accno.cspaq22200 = MagicMock(return_value=mock_22200)

        mock_korea_stock = MagicMock()
        mock_korea_stock.accno = MagicMock(return_value=mock_accno)
        ls.korea_stock = MagicMock(return_value=mock_korea_stock)

        return ls

    @pytest.mark.asyncio
    async def test_positions_and_balance(self):
        """정상 잔고 조회: positions + balance 확인"""
        executor = self._make_executor()
        ctx = _make_mock_context()

        # CSPAQ12300 mock
        b2 = MagicMock()
        b2.MnyOrdAbleAmt = 5000000
        b2.BalEvalAmt = 20000000
        b2.PchsAmt = 18000000
        b2.EvalPnl = 2000000
        b2.PnlRat = 11.1
        b2.Dps = 6000000

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

        resp_12300 = MagicMock()
        resp_12300.error_msg = None
        resp_12300.block2 = b2
        resp_12300.block3 = [pos_item]

        # CSPAQ22200 mock
        b2_cash = MagicMock()
        b2_cash.MnyOrdAbleAmt = 5500000
        b2_cash.Dps = 6100000
        b2_cash.D2Dps = 5800000
        b2_cash.MgnMny = 100000

        resp_22200 = MagicMock()
        resp_22200.error_msg = None
        resp_22200.block2 = b2_cash

        ls = self._build_ls_mock(resp_12300, resp_22200)
        result = await executor._ls_korea_stock(ls, "acct1", ctx)

        # positions 검증
        assert len(result["positions"]) == 1
        pos = result["positions"][0]
        assert pos["symbol"] == "005930"  # A 접두사 제거
        assert pos["exchange"] == "KRX"
        assert pos["quantity"] == 100
        assert pos["product"] == "korea_stock"

        # balance 검증
        bal = result["balance"]
        assert bal["orderable_amount"] == 5500000  # CSPAQ22200 우선
        assert bal["deposit"] == 6100000
        assert bal["d2_deposit"] == 5800000

    @pytest.mark.asyncio
    async def test_cspaq12300_error(self):
        """CSPAQ12300 에러 시 빈 positions + warning"""
        executor = self._make_executor()
        ctx = _make_mock_context()

        resp_12300 = MagicMock()
        resp_12300.error_msg = "CSPAQ12300 조회 실패"
        resp_12300.block2 = None
        resp_12300.block3 = []

        resp_22200 = MagicMock()
        resp_22200.error_msg = None
        resp_22200.block2 = None

        ls = self._build_ls_mock(resp_12300, resp_22200)
        result = await executor._ls_korea_stock(ls, "acct1", ctx)

        assert result["positions"] == []
        ctx.log.assert_any_call("warning", "CSPAQ12300 조회 실패: CSPAQ12300 조회 실패", "acct1")

    @pytest.mark.asyncio
    async def test_zero_balance_position_skipped(self):
        """잔량 0인 포지션은 결과에서 제외"""
        executor = self._make_executor()
        ctx = _make_mock_context()

        pos_item = MagicMock()
        pos_item.IsuNo = "A005930"
        pos_item.IsuNm = "삼성전자"
        pos_item.BalQty = 0  # 잔량 0
        pos_item.NowPrc = 65000
        pos_item.AvrUprc = 60000
        pos_item.EvalPnl = 0
        pos_item.PnlRat = 0
        pos_item.SellAbleQty = 0
        pos_item.BalEvalAmt = 0

        resp_12300 = MagicMock()
        resp_12300.error_msg = None
        resp_12300.block2 = MagicMock(MnyOrdAbleAmt=0, BalEvalAmt=0, PchsAmt=0, EvalPnl=0, PnlRat=0, Dps=0)
        resp_12300.block3 = [pos_item]

        resp_22200 = MagicMock()
        resp_22200.error_msg = None
        resp_22200.block2 = None

        ls = self._build_ls_mock(resp_12300, resp_22200)
        result = await executor._ls_korea_stock(ls, "acct1", ctx)

        assert len(result["positions"]) == 0


# ── 3. OpenOrdersNodeExecutor._ls_korea_stock ──


class TestKoreaStockOpenOrdersExecutor:
    """국내주식 미체결 조회 (t0425)"""

    def _make_executor(self):
        from programgarden.executor import OpenOrdersNodeExecutor
        return OpenOrdersNodeExecutor()

    @pytest.mark.asyncio
    async def test_open_orders_normal(self):
        """정상 미체결 조회"""
        executor = self._make_executor()
        ctx = _make_mock_context()
        ls = MagicMock()

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
        ls.korea_stock = MagicMock(return_value=mock_ks)

        result = await executor._ls_korea_stock(ls, "oo1", ctx)

        assert result["count"] == 1
        order = result["open_orders"][0]
        assert order["order_id"] == "12345"
        assert order["side"] == "buy"
        assert order["remaining_quantity"] == 50

    @pytest.mark.asyncio
    async def test_open_orders_error(self):
        """t0425 에러 시 빈 결과"""
        executor = self._make_executor()
        ctx = _make_mock_context()
        ls = MagicMock()

        resp = MagicMock()
        resp.error_msg = "t0425 error"

        mock_t0425 = MagicMock()
        mock_t0425.req_async = AsyncMock(return_value=resp)

        mock_accno = MagicMock()
        mock_accno.t0425 = MagicMock(return_value=mock_t0425)
        mock_ks = MagicMock()
        mock_ks.accno = MagicMock(return_value=mock_accno)
        ls.korea_stock = MagicMock(return_value=mock_ks)

        result = await executor._ls_korea_stock(ls, "oo1", ctx)

        assert result["open_orders"] == []
        assert result["count"] == 0


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
        assert result["cancelled_order"]["status"] == "cancelled"

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
