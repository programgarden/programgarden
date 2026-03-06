"""
국내주식 WorkflowPnL 추적 테스트

테스트 대상:
- BrokerNodeExecutor._start_korea_stock_tracker: 국내주식 계좌 추적기 시작, PnL 이벤트 발행
- BrokerNodeExecutor._subscribe_korea_stock_fill_events: SC1 체결 이벤트 구독, FIFO 포지션 추적

실행:
    cd src/programgarden && poetry run pytest tests/test_korea_stock_pnl_tracking.py -v
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest


# ---------------------------------------------------------------------------
# 공통 헬퍼
# ---------------------------------------------------------------------------


def _make_mock_context(is_shutdown: bool = False):
    """ExecutionContext mock 생성 헬퍼"""
    ctx = MagicMock()
    ctx.is_shutdown = is_shutdown
    ctx.job_id = "test-job-001"
    ctx.log = MagicMock()
    ctx.notify_workflow_pnl = AsyncMock()
    ctx.record_workflow_fill = AsyncMock(return_value="workflow")
    ctx.modify_workflow_order = AsyncMock(return_value=True)
    ctx.cancel_workflow_order = AsyncMock(return_value=True)
    return ctx


def _make_mock_ls(tracker=None, positions=None):
    """LS API 계층 mock 생성 헬퍼

    ls.korea_stock().accno().account_tracker() 체인을 모두 mocking한다.
    """
    mock_ls = MagicMock()
    mock_accno = MagicMock()
    mock_real = MagicMock()
    mock_tracker = tracker or MagicMock()

    mock_real.connect = AsyncMock()
    mock_real.is_connected = AsyncMock(return_value=True)

    # SC1 구독 체인: real.SC1().on_sc1_message(cb)
    mock_sc1 = MagicMock()
    mock_real.SC1 = MagicMock(return_value=mock_sc1)

    mock_tracker.start = AsyncMock()
    mock_tracker.refresh_now = AsyncMock()
    mock_tracker.get_positions = MagicMock(return_value=positions or {})
    # on_account_pnl_change 는 callback을 캡처하기 위해 side_effect로 처리
    mock_tracker.on_account_pnl_change = MagicMock()

    mock_accno.account_tracker = MagicMock(return_value=mock_tracker)

    # korea_stock().accno() / korea_stock().real() 반환
    mock_korea_stock = MagicMock()
    mock_korea_stock.accno = MagicMock(return_value=mock_accno)
    mock_korea_stock.real = MagicMock(return_value=mock_real)
    mock_ls.korea_stock = MagicMock(return_value=mock_korea_stock)

    return mock_ls, mock_tracker, mock_real, mock_sc1


def _make_sc1_body(**kwargs):
    """SC1RealResponseBody mock 생성 헬퍼 (기본값: 체결 이벤트)"""
    defaults = {
        "ordxctptncode": "11",
        "ordno": "0001234567",
        "shtnIsuno": "A005930",
        "bnstp": "2",       # 매수
        "execprc": "55000",
        "execqty": "10",
        "exectime": "093012000",
        "mdfycnfqty": "0",
        "mdfycnfprc": "0",
        "orgordno": "",
    }
    defaults.update(kwargs)
    body = MagicMock()
    for k, v in defaults.items():
        setattr(body, k, v)
    return body


def _get_executor():
    """BrokerNodeExecutor 인스턴스 반환 (클래스 변수 초기화 포함)"""
    from programgarden.executor import BrokerNodeExecutor
    executor = BrokerNodeExecutor()
    # 클래스 변수를 인스턴스 변수로 shadow하여 테스트 간 격리
    executor._active_trackers = {}
    return executor


# ---------------------------------------------------------------------------
# _start_korea_stock_tracker 테스트
# ---------------------------------------------------------------------------


class TestStartKoreaStockTracker:
    """_start_korea_stock_tracker 메서드 테스트"""

    @pytest.mark.asyncio
    async def test_tracker_start_called(self):
        """tracker.start()가 호출되는지 확인"""
        executor = _get_executor()
        context = _make_mock_context()
        mock_ls, mock_tracker, mock_real, _ = _make_mock_ls()

        await executor._start_korea_stock_tracker(
            ls=mock_ls,
            node_id="broker-1",
            product="korea_stock",
            provider="ls-sec.co.kr",
            context=context,
        )

        mock_tracker.start.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_real_connect_called(self):
        """real.connect()가 호출되는지 확인"""
        executor = _get_executor()
        context = _make_mock_context()
        mock_ls, mock_tracker, mock_real, _ = _make_mock_ls()

        await executor._start_korea_stock_tracker(
            ls=mock_ls,
            node_id="broker-1",
            product="korea_stock",
            provider="ls-sec.co.kr",
            context=context,
        )

        mock_real.connect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_tracker_stored_in_active_trackers(self):
        """_active_trackers에 tracker_key로 저장되는지 확인"""
        executor = _get_executor()
        context = _make_mock_context()
        mock_ls, mock_tracker, _, _ = _make_mock_ls()

        await executor._start_korea_stock_tracker(
            ls=mock_ls,
            node_id="broker-1",
            product="korea_stock",
            provider="ls-sec.co.kr",
            context=context,
        )

        expected_key = "test-job-001_broker-1"
        assert expected_key in executor._active_trackers
        info = executor._active_trackers[expected_key]
        assert info["tracker"] is mock_tracker

    @pytest.mark.asyncio
    async def test_on_account_pnl_change_registered(self):
        """tracker.on_account_pnl_change(callback)이 호출되는지 확인"""
        executor = _get_executor()
        context = _make_mock_context()
        mock_ls, mock_tracker, _, _ = _make_mock_ls()

        await executor._start_korea_stock_tracker(
            ls=mock_ls,
            node_id="broker-1",
            product="korea_stock",
            provider="ls-sec.co.kr",
            context=context,
        )

        mock_tracker.on_account_pnl_change.assert_called_once()
        # 등록된 콜백이 callable인지 확인
        registered_cb = mock_tracker.on_account_pnl_change.call_args[0][0]
        assert callable(registered_cb)

    @pytest.mark.asyncio
    async def test_pnl_callback_invokes_notify_workflow_pnl(self):
        """on_account_pnl_change 콜백 호출 시 notify_workflow_pnl이 호출되는지 확인"""
        executor = _get_executor()
        context = _make_mock_context()
        mock_ls, mock_tracker, _, _ = _make_mock_ls()

        await executor._start_korea_stock_tracker(
            ls=mock_ls,
            node_id="broker-1",
            product="korea_stock",
            provider="ls-sec.co.kr",
            context=context,
        )

        # 등록된 콜백 추출
        registered_cb = mock_tracker.on_account_pnl_change.call_args[0][0]

        # asyncio.create_task를 patch하여 코루틴을 직접 실행
        with patch("asyncio.create_task") as mock_create_task:
            captured_coros = []

            def capture_coro(coro):
                captured_coros.append(coro)
                return MagicMock()

            mock_create_task.side_effect = capture_coro

            # PnL 콜백 발화
            mock_pnl_info = MagicMock()
            registered_cb(mock_pnl_info)

            assert len(captured_coros) == 1

            # 캡처된 코루틴 실행 (실제 notify_workflow_pnl 호출 확인)
            await captured_coros[0]

        context.notify_workflow_pnl.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_pnl_callback_passes_krw_currency(self):
        """on_pnl_change 콜백에서 currency='KRW'로 notify_workflow_pnl을 호출하는지 확인"""
        executor = _get_executor()
        context = _make_mock_context()
        mock_ls, mock_tracker, _, _ = _make_mock_ls()

        await executor._start_korea_stock_tracker(
            ls=mock_ls,
            node_id="broker-1",
            product="korea_stock",
            provider="ls-sec.co.kr",
            context=context,
        )

        registered_cb = mock_tracker.on_account_pnl_change.call_args[0][0]

        with patch("asyncio.create_task") as mock_create_task:
            captured_coros = []
            mock_create_task.side_effect = lambda c: captured_coros.append(c) or MagicMock()
            registered_cb(MagicMock())
            await captured_coros[0]

        call_kwargs = context.notify_workflow_pnl.call_args.kwargs
        assert call_kwargs.get("currency") == "KRW"

    @pytest.mark.asyncio
    async def test_pnl_callback_position_field_mapping_int_to_float(self):
        """KrStockPositionItem의 int 필드(buy_price, current_price)가 float으로 변환되는지 확인"""
        executor = _get_executor()
        context = _make_mock_context()

        # KrStockPositionItem mock (int 타입 필드)
        mock_pos = MagicMock()
        mock_pos.current_price = 55000   # int (원)
        mock_pos.buy_price = 50000       # int (원)
        mock_pos.quantity = 10
        mock_pos.pnl_rate = 10.0

        positions = {"005930": mock_pos}
        mock_ls, mock_tracker, _, _ = _make_mock_ls(positions=positions)

        await executor._start_korea_stock_tracker(
            ls=mock_ls,
            node_id="broker-1",
            product="korea_stock",
            provider="ls-sec.co.kr",
            context=context,
        )

        registered_cb = mock_tracker.on_account_pnl_change.call_args[0][0]

        with patch("asyncio.create_task") as mock_create_task:
            captured_coros = []
            mock_create_task.side_effect = lambda c: captured_coros.append(c) or MagicMock()
            registered_cb(MagicMock())
            await captured_coros[0]

        call_kwargs = context.notify_workflow_pnl.call_args.kwargs
        account_positions = call_kwargs.get("account_positions")
        assert account_positions is not None
        pos = account_positions["005930"]
        # int → float 변환 확인
        assert isinstance(pos["buy_price"], float), "buy_price는 float이어야 함"
        assert isinstance(pos["current_price"], float), "current_price는 float이어야 함"
        assert pos["buy_price"] == 50000.0
        assert pos["current_price"] == 55000.0

    @pytest.mark.asyncio
    async def test_pnl_callback_current_prices_populated(self):
        """current_prices 딕셔너리에 symbol: float(current_price) 형태로 채워지는지 확인"""
        executor = _get_executor()
        context = _make_mock_context()

        mock_pos = MagicMock()
        mock_pos.current_price = 77000
        mock_pos.buy_price = 70000
        mock_pos.quantity = 5
        mock_pos.pnl_rate = 10.0

        positions = {"035720": mock_pos}
        mock_ls, mock_tracker, _, _ = _make_mock_ls(positions=positions)

        await executor._start_korea_stock_tracker(
            ls=mock_ls,
            node_id="broker-1",
            product="korea_stock",
            provider="ls-sec.co.kr",
            context=context,
        )

        registered_cb = mock_tracker.on_account_pnl_change.call_args[0][0]

        with patch("asyncio.create_task") as mock_create_task:
            captured_coros = []
            mock_create_task.side_effect = lambda c: captured_coros.append(c) or MagicMock()
            registered_cb(MagicMock())
            await captured_coros[0]

        call_kwargs = context.notify_workflow_pnl.call_args.kwargs
        current_prices = call_kwargs.get("current_prices")
        assert "035720" in current_prices
        assert current_prices["035720"] == 77000.0

    @pytest.mark.asyncio
    async def test_empty_positions_passes_none_to_account_positions(self):
        """포지션이 없을 때 account_positions=None으로 호출되는지 확인"""
        executor = _get_executor()
        context = _make_mock_context()
        mock_ls, mock_tracker, _, _ = _make_mock_ls(positions={})

        await executor._start_korea_stock_tracker(
            ls=mock_ls,
            node_id="broker-1",
            product="korea_stock",
            provider="ls-sec.co.kr",
            context=context,
        )

        registered_cb = mock_tracker.on_account_pnl_change.call_args[0][0]

        with patch("asyncio.create_task") as mock_create_task:
            captured_coros = []
            mock_create_task.side_effect = lambda c: captured_coros.append(c) or MagicMock()
            registered_cb(MagicMock())
            await captured_coros[0]

        call_kwargs = context.notify_workflow_pnl.call_args.kwargs
        assert call_kwargs.get("account_positions") is None

    @pytest.mark.asyncio
    async def test_tracker_key_format(self):
        """_active_trackers의 키가 '{job_id}_{node_id}' 형식인지 확인"""
        executor = _get_executor()
        context = _make_mock_context()
        context.job_id = "job-abc"
        mock_ls, _, _, _ = _make_mock_ls()

        await executor._start_korea_stock_tracker(
            ls=mock_ls,
            node_id="broker-kr",
            product="korea_stock",
            provider="ls-sec.co.kr",
            context=context,
        )

        assert "job-abc_broker-kr" in executor._active_trackers


# ---------------------------------------------------------------------------
# _subscribe_korea_stock_fill_events 테스트
# ---------------------------------------------------------------------------


class TestSubscribeKoreaStockFillEvents:
    """_subscribe_korea_stock_fill_events 메서드 테스트"""

    async def _setup_and_get_sc1_callback(self, executor, context, mock_ls, mock_sc1):
        """_subscribe_korea_stock_fill_events를 실행하고 on_sc1_event 콜백을 반환한다."""
        await executor._subscribe_korea_stock_fill_events(
            ls=mock_ls,
            node_id="broker-1",
            context=context,
        )
        # on_sc1_message에 전달된 콜백 추출
        mock_sc1.on_sc1_message.assert_called_once()
        return mock_sc1.on_sc1_message.call_args[0][0]

    @pytest.mark.asyncio
    async def test_sc1_subscription_registered(self):
        """real.SC1().on_sc1_message()가 호출되는지 확인"""
        executor = _get_executor()
        context = _make_mock_context()
        mock_ls, _, _, mock_sc1 = _make_mock_ls()

        await executor._subscribe_korea_stock_fill_events(
            ls=mock_ls,
            node_id="broker-1",
            context=context,
        )

        mock_sc1.on_sc1_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_fill_event_calls_record_workflow_fill(self):
        """체결(ordxctptncode='11') 이벤트 수신 시 record_workflow_fill이 호출되는지 확인"""
        executor = _get_executor()
        context = _make_mock_context()
        mock_ls, _, _, mock_sc1 = _make_mock_ls()

        on_sc1 = await self._setup_and_get_sc1_callback(executor, context, mock_ls, mock_sc1)

        body = _make_sc1_body(ordxctptncode="11", execqty="10", execprc="55000")
        resp = MagicMock()
        resp.body = body

        loop = asyncio.get_event_loop()
        with patch("asyncio.run_coroutine_threadsafe") as mock_run:
            futures = []

            def capture_coro(coro, lp):
                futures.append(coro)
                return MagicMock()

            mock_run.side_effect = capture_coro
            on_sc1(resp)

        assert len(futures) == 1, "record_and_refresh 코루틴이 1회 스케줄되어야 함"
        # 실제 코루틴 실행
        await futures[0]
        context.record_workflow_fill.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_fill_event_record_parameters(self):
        """체결 이벤트에서 record_workflow_fill의 파라미터가 올바른지 확인"""
        executor = _get_executor()
        context = _make_mock_context()
        mock_ls, _, _, mock_sc1 = _make_mock_ls()

        on_sc1 = await self._setup_and_get_sc1_callback(executor, context, mock_ls, mock_sc1)

        body = _make_sc1_body(
            ordxctptncode="11",
            ordno="0009876543",
            shtnIsuno="A005380",
            bnstp="2",         # 매수
            execprc="88000",
            execqty="5",
            exectime="141530000",
        )
        resp = MagicMock()
        resp.body = body

        with patch("asyncio.run_coroutine_threadsafe") as mock_run:
            futures = []
            mock_run.side_effect = lambda c, l: futures.append(c) or MagicMock()
            on_sc1(resp)

        await futures[0]

        call_kwargs = context.record_workflow_fill.call_args.kwargs
        assert call_kwargs["order_no"] == "0009876543"
        assert call_kwargs["symbol"] == "005380", "A 접두사가 제거된 종목코드여야 함"
        assert call_kwargs["exchange"] == "KRX"
        assert call_kwargs["side"] == "buy"
        assert call_kwargs["quantity"] == 5
        assert call_kwargs["price"] == 88000.0
        assert call_kwargs["fill_time"] == "141530000"

    @pytest.mark.asyncio
    async def test_symbol_a_prefix_stripped(self):
        """shtnIsuno 'A005930' → symbol '005930' (A 접두사 제거) 확인"""
        executor = _get_executor()
        context = _make_mock_context()
        mock_ls, _, _, mock_sc1 = _make_mock_ls()

        on_sc1 = await self._setup_and_get_sc1_callback(executor, context, mock_ls, mock_sc1)

        body = _make_sc1_body(shtnIsuno="A005930")
        resp = MagicMock()
        resp.body = body

        with patch("asyncio.run_coroutine_threadsafe") as mock_run:
            futures = []
            mock_run.side_effect = lambda c, l: futures.append(c) or MagicMock()
            on_sc1(resp)

        await futures[0]
        call_kwargs = context.record_workflow_fill.call_args.kwargs
        assert call_kwargs["symbol"] == "005930"

    @pytest.mark.asyncio
    async def test_exchange_is_krx(self):
        """exchange 파라미터가 항상 'KRX'인지 확인"""
        executor = _get_executor()
        context = _make_mock_context()
        mock_ls, _, _, mock_sc1 = _make_mock_ls()

        on_sc1 = await self._setup_and_get_sc1_callback(executor, context, mock_ls, mock_sc1)

        body = _make_sc1_body(ordxctptncode="11")
        resp = MagicMock()
        resp.body = body

        with patch("asyncio.run_coroutine_threadsafe") as mock_run:
            futures = []
            mock_run.side_effect = lambda c, l: futures.append(c) or MagicMock()
            on_sc1(resp)

        await futures[0]
        assert context.record_workflow_fill.call_args.kwargs["exchange"] == "KRX"

    @pytest.mark.asyncio
    async def test_bnstp_1_sell(self):
        """bnstp='1'(매도)이면 side='sell'로 변환되는지 확인"""
        executor = _get_executor()
        context = _make_mock_context()
        mock_ls, _, _, mock_sc1 = _make_mock_ls()

        on_sc1 = await self._setup_and_get_sc1_callback(executor, context, mock_ls, mock_sc1)

        body = _make_sc1_body(bnstp="1")  # 매도
        resp = MagicMock()
        resp.body = body

        with patch("asyncio.run_coroutine_threadsafe") as mock_run:
            futures = []
            mock_run.side_effect = lambda c, l: futures.append(c) or MagicMock()
            on_sc1(resp)

        await futures[0]
        assert context.record_workflow_fill.call_args.kwargs["side"] == "sell"

    @pytest.mark.asyncio
    async def test_bnstp_2_buy(self):
        """bnstp='2'(매수)이면 side='buy'로 변환되는지 확인"""
        executor = _get_executor()
        context = _make_mock_context()
        mock_ls, _, _, mock_sc1 = _make_mock_ls()

        on_sc1 = await self._setup_and_get_sc1_callback(executor, context, mock_ls, mock_sc1)

        body = _make_sc1_body(bnstp="2")  # 매수
        resp = MagicMock()
        resp.body = body

        with patch("asyncio.run_coroutine_threadsafe") as mock_run:
            futures = []
            mock_run.side_effect = lambda c, l: futures.append(c) or MagicMock()
            on_sc1(resp)

        await futures[0]
        assert context.record_workflow_fill.call_args.kwargs["side"] == "buy"

    @pytest.mark.asyncio
    async def test_str_to_int_float_conversion(self):
        """execprc, execqty가 str 타입으로 오더라도 int/float으로 안전 변환되는지 확인"""
        executor = _get_executor()
        context = _make_mock_context()
        mock_ls, _, _, mock_sc1 = _make_mock_ls()

        on_sc1 = await self._setup_and_get_sc1_callback(executor, context, mock_ls, mock_sc1)

        # 모든 필드가 str 타입
        body = _make_sc1_body(execqty="7", execprc="123456")
        resp = MagicMock()
        resp.body = body

        with patch("asyncio.run_coroutine_threadsafe") as mock_run:
            futures = []
            mock_run.side_effect = lambda c, l: futures.append(c) or MagicMock()
            on_sc1(resp)

        await futures[0]
        call_kwargs = context.record_workflow_fill.call_args.kwargs
        assert call_kwargs["quantity"] == 7, "execqty가 int로 변환되어야 함"
        assert call_kwargs["price"] == 123456.0, "execprc가 float으로 변환되어야 함"
        assert isinstance(call_kwargs["quantity"], int)
        assert isinstance(call_kwargs["price"], float)

    @pytest.mark.asyncio
    async def test_fill_event_triggers_tracker_refresh(self):
        """체결 후 tracker.refresh_now()가 호출되는지 확인"""
        executor = _get_executor()
        context = _make_mock_context()
        mock_ls, mock_tracker, _, mock_sc1 = _make_mock_ls()

        # tracker를 _active_trackers에 사전 등록 (실제 실행 순서 반영)
        tracker_key = f"{context.job_id}_broker-1"
        executor._active_trackers[tracker_key] = {"tracker": mock_tracker}

        on_sc1 = await self._setup_and_get_sc1_callback(executor, context, mock_ls, mock_sc1)

        body = _make_sc1_body(ordxctptncode="11")
        resp = MagicMock()
        resp.body = body

        with patch("asyncio.run_coroutine_threadsafe") as mock_run:
            futures = []
            mock_run.side_effect = lambda c, l: futures.append(c) or MagicMock()
            on_sc1(resp)

        await futures[0]
        mock_tracker.refresh_now.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_modify_event_calls_modify_workflow_order(self):
        """정정확인(ordxctptncode='12') 이벤트 수신 시 modify_workflow_order가 호출되는지 확인"""
        executor = _get_executor()
        context = _make_mock_context()
        mock_ls, _, _, mock_sc1 = _make_mock_ls()

        on_sc1 = await self._setup_and_get_sc1_callback(executor, context, mock_ls, mock_sc1)

        body = _make_sc1_body(
            ordxctptncode="12",
            ordno="0001111111",
            mdfycnfqty="5",
            mdfycnfprc="60000",
        )
        resp = MagicMock()
        resp.body = body

        with patch("asyncio.run_coroutine_threadsafe") as mock_run:
            futures_or_mock = []
            # run_coroutine_threadsafe는 코루틴을 직접 받으므로 캡처
            mock_run.side_effect = lambda c, l: futures_or_mock.append(c) or MagicMock()
            on_sc1(resp)

        assert len(futures_or_mock) == 1, "modify_workflow_order 코루틴이 1회 스케줄되어야 함"
        await futures_or_mock[0]
        context.modify_workflow_order.assert_awaited_once()
        call_kwargs = context.modify_workflow_order.call_args.kwargs
        assert call_kwargs["order_no"] == "0001111111"
        assert call_kwargs["new_quantity"] == 5
        assert call_kwargs["new_price"] == 60000.0

    @pytest.mark.asyncio
    async def test_cancel_event_calls_cancel_workflow_order(self):
        """취소확인(ordxctptncode='13') 이벤트 수신 시 cancel_workflow_order가 호출되는지 확인"""
        executor = _get_executor()
        context = _make_mock_context()
        mock_ls, _, _, mock_sc1 = _make_mock_ls()

        on_sc1 = await self._setup_and_get_sc1_callback(executor, context, mock_ls, mock_sc1)

        body = _make_sc1_body(
            ordxctptncode="13",
            ordno="0002222222",
        )
        resp = MagicMock()
        resp.body = body

        with patch("asyncio.run_coroutine_threadsafe") as mock_run:
            futures = []
            mock_run.side_effect = lambda c, l: futures.append(c) or MagicMock()
            on_sc1(resp)

        assert len(futures) == 1
        await futures[0]
        context.cancel_workflow_order.assert_awaited_once()
        call_kwargs = context.cancel_workflow_order.call_args.kwargs
        assert call_kwargs["order_no"] == "0002222222"

    @pytest.mark.asyncio
    async def test_reject_event_ignored(self):
        """거부(ordxctptncode='14') 이벤트는 무시되는지 확인 (어떤 메서드도 호출되지 않음)"""
        executor = _get_executor()
        context = _make_mock_context()
        mock_ls, _, _, mock_sc1 = _make_mock_ls()

        on_sc1 = await self._setup_and_get_sc1_callback(executor, context, mock_ls, mock_sc1)

        body = _make_sc1_body(ordxctptncode="14")
        resp = MagicMock()
        resp.body = body

        with patch("asyncio.run_coroutine_threadsafe") as mock_run:
            on_sc1(resp)
            mock_run.assert_not_called()

        context.record_workflow_fill.assert_not_called()
        context.modify_workflow_order.assert_not_called()
        context.cancel_workflow_order.assert_not_called()

    @pytest.mark.asyncio
    async def test_order_receipt_event_ignored(self):
        """주문접수(ordxctptncode='01') 이벤트는 무시되는지 확인"""
        executor = _get_executor()
        context = _make_mock_context()
        mock_ls, _, _, mock_sc1 = _make_mock_ls()

        on_sc1 = await self._setup_and_get_sc1_callback(executor, context, mock_ls, mock_sc1)

        body = _make_sc1_body(ordxctptncode="01")
        resp = MagicMock()
        resp.body = body

        with patch("asyncio.run_coroutine_threadsafe") as mock_run:
            on_sc1(resp)
            mock_run.assert_not_called()

    @pytest.mark.asyncio
    async def test_is_shutdown_guard_blocks_callback(self):
        """context.is_shutdown=True 상태에서 SC1 콜백이 즉시 반환되는지 확인"""
        executor = _get_executor()
        context = _make_mock_context(is_shutdown=True)
        mock_ls, _, _, mock_sc1 = _make_mock_ls()

        on_sc1 = await self._setup_and_get_sc1_callback(executor, context, mock_ls, mock_sc1)

        body = _make_sc1_body(ordxctptncode="11")
        resp = MagicMock()
        resp.body = body

        with patch("asyncio.run_coroutine_threadsafe") as mock_run:
            on_sc1(resp)
            mock_run.assert_not_called(), "shutdown 상태에서는 코루틴이 스케줄되지 않아야 함"

    @pytest.mark.asyncio
    async def test_fill_subscription_stored_in_active_trackers(self):
        """fill_subscription이 _active_trackers에 저장되는지 확인"""
        executor = _get_executor()
        context = _make_mock_context()
        mock_ls, _, _, _ = _make_mock_ls()

        await executor._subscribe_korea_stock_fill_events(
            ls=mock_ls,
            node_id="broker-1",
            context=context,
        )

        sub_key = "test-job-001_broker-1_fill_sub"
        assert sub_key in executor._active_trackers
        info = executor._active_trackers[sub_key]
        assert info.get("type") == "fill_subscription"

    @pytest.mark.asyncio
    async def test_zero_qty_fill_ignored(self):
        """체결수량이 0인 경우 record_workflow_fill이 호출되지 않는지 확인"""
        executor = _get_executor()
        context = _make_mock_context()
        mock_ls, _, _, mock_sc1 = _make_mock_ls()

        on_sc1 = await self._setup_and_get_sc1_callback(executor, context, mock_ls, mock_sc1)

        body = _make_sc1_body(ordxctptncode="11", execqty="0", execprc="55000")
        resp = MagicMock()
        resp.body = body

        with patch("asyncio.run_coroutine_threadsafe") as mock_run:
            on_sc1(resp)
            mock_run.assert_not_called(), "수량 0 체결은 무시되어야 함"

    @pytest.mark.asyncio
    async def test_zero_price_fill_ignored(self):
        """체결가격이 0인 경우 record_workflow_fill이 호출되지 않는지 확인"""
        executor = _get_executor()
        context = _make_mock_context()
        mock_ls, _, _, mock_sc1 = _make_mock_ls()

        on_sc1 = await self._setup_and_get_sc1_callback(executor, context, mock_ls, mock_sc1)

        body = _make_sc1_body(ordxctptncode="11", execqty="10", execprc="0")
        resp = MagicMock()
        resp.body = body

        with patch("asyncio.run_coroutine_threadsafe") as mock_run:
            on_sc1(resp)
            mock_run.assert_not_called(), "가격 0 체결은 무시되어야 함"


# ---------------------------------------------------------------------------
# context.py record_workflow_fill PnL refresh 테스트
# ---------------------------------------------------------------------------


class TestRecordWorkflowFillPnLRefresh:
    """record_workflow_fill 후 PnL refresh 시 korea_stock이면 currency='KRW' 전달 확인"""

    @pytest.mark.asyncio
    async def test_korea_stock_fill_uses_krw_currency(self):
        """_workflow_product='korea_stock'일 때 notify_workflow_pnl에 currency='KRW' 전달 확인"""
        from programgarden.context import ExecutionContext

        ctx = ExecutionContext(
            job_id="test-job-001",
            workflow_id="wf-001",
        )

        # 내부 상태 직접 설정 (broker 연결 없이 테스트)
        ctx._workflow_product = "korea_stock"
        ctx._workflow_broker_node_id = "broker-kr"

        # position tracker mock
        mock_tracker = MagicMock()
        mock_tracker.record_fill = AsyncMock(return_value="workflow")
        ctx._workflow_position_tracker = mock_tracker

        # notify_workflow_pnl mock
        ctx.notify_workflow_pnl = AsyncMock()

        await ctx.record_workflow_fill(
            order_no="0001234567",
            order_date="20260306",
            symbol="005930",
            exchange="KRX",
            side="buy",
            quantity=10,
            price=55000.0,
            fill_time="093000000",
        )

        ctx.notify_workflow_pnl.assert_awaited_once()
        call_kwargs = ctx.notify_workflow_pnl.call_args.kwargs
        assert call_kwargs.get("currency") == "KRW", (
            "korea_stock product에서 PnL refresh 시 currency는 'KRW'이어야 함"
        )

    @pytest.mark.asyncio
    async def test_overseas_stock_fill_uses_usd_currency(self):
        """_workflow_product='overseas_stock'일 때 notify_workflow_pnl에 currency='USD' 전달 확인"""
        from programgarden.context import ExecutionContext

        ctx = ExecutionContext(
            job_id="test-job-002",
            workflow_id="wf-002",
        )

        ctx._workflow_product = "overseas_stock"
        ctx._workflow_broker_node_id = "broker-us"

        mock_tracker = MagicMock()
        mock_tracker.record_fill = AsyncMock(return_value="workflow")
        ctx._workflow_position_tracker = mock_tracker

        ctx.notify_workflow_pnl = AsyncMock()

        await ctx.record_workflow_fill(
            order_no="0001111111",
            order_date="20260306",
            symbol="AAPL",
            exchange="NASDAQ",
            side="buy",
            quantity=5,
            price=180.0,
            fill_time="093000000",
        )

        ctx.notify_workflow_pnl.assert_awaited_once()
        call_kwargs = ctx.notify_workflow_pnl.call_args.kwargs
        assert call_kwargs.get("currency") == "USD", (
            "overseas_stock product에서 PnL refresh 시 currency는 'USD'이어야 함"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
