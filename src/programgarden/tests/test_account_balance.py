"""
AccountNode 잔고 정보 확장 테스트

- 해외주식: COSOQ02701 (외화예수금/주문가능금액) 추가
- 해외선물: CIDBQ03000 → CIDBQ05300 교체 (증거금/마진콜율 추가)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_mock_context():
    """간이 ExecutionContext mock"""
    ctx = MagicMock()
    ctx.log = MagicMock()
    ctx.job_id = "test-job"
    ctx.is_running = True
    return ctx


def _make_executor():
    """AccountNodeExecutor 인스턴스 생성"""
    from programgarden.executor import AccountNodeExecutor
    return AccountNodeExecutor()


# ── 해외주식 테스트 ──


@pytest.mark.asyncio
async def test_stock_balance_includes_orderable():
    """주식 balance에 orderable_amount/foreign_cash/exchange_rate 포함 확인"""
    executor = _make_executor()
    ctx = _make_mock_context()
    ls = MagicMock()

    # COSOQ00201 mock
    mock_block2 = MagicMock()
    mock_block2.ErnRat = 5.5
    mock_block2.WonDpsBalAmt = 10000000
    mock_block2.StkConvEvalAmt = 50000000
    mock_block2.WonEvalSumAmt = 60000000
    mock_block2.ConvEvalPnlAmt = 5000000

    cosoq00201_response = MagicMock()
    cosoq00201_response.error_msg = None
    cosoq00201_response.block2 = mock_block2
    cosoq00201_response.block4 = []

    mock_cosoq00201 = MagicMock()
    mock_cosoq00201.req_async = AsyncMock(return_value=cosoq00201_response)

    # COSOQ02701 mock
    mock_block3_item = MagicMock()
    mock_block3_item.CrcyCode = "USD"
    mock_block3_item.FcurrOrdAbleAmt = 15000.50
    mock_block3_item.FcurrDps = 20000.00
    mock_block3_item.BaseXchrat = 1350.00

    mock_block4 = MagicMock()
    mock_block4.MnyoutAbleAmt = 8000000
    mock_block4.OvrsMgn = 3000000

    cosoq02701_response = MagicMock()
    cosoq02701_response.error_msg = None
    cosoq02701_response.block3 = [mock_block3_item]
    cosoq02701_response.block4 = mock_block4

    mock_cosoq02701 = MagicMock()
    mock_cosoq02701.req_async = AsyncMock(return_value=cosoq02701_response)

    # LS 체인 mock
    mock_accno = MagicMock()
    mock_accno.cosoq00201 = MagicMock(return_value=mock_cosoq00201)
    mock_accno.cosoq02701 = MagicMock(return_value=mock_cosoq02701)
    mock_overseas_stock = MagicMock()
    mock_overseas_stock.accno = MagicMock(return_value=mock_accno)
    ls.overseas_stock = MagicMock(return_value=mock_overseas_stock)

    result = await executor._ls_overseas_stock(ls, "account1", ctx)

    balance = result["balance"]
    # 기존 필드
    assert balance["total_pnl_rate"] == 5.5
    assert balance["cash_krw"] == 10000000
    assert balance["stock_eval_krw"] == 50000000
    assert balance["total_eval_krw"] == 60000000
    assert balance["total_pnl_krw"] == 5000000
    # 신규 필드 (COSOQ02701)
    assert balance["orderable_amount"] == 15000.50
    assert balance["foreign_cash"] == 20000.00
    assert balance["exchange_rate"] == 1350.00
    assert balance["withdrawable_krw"] == 8000000
    assert balance["overseas_margin"] == 3000000


@pytest.mark.asyncio
async def test_stock_balance_cosoq02701_failure_graceful():
    """COSOQ02701 실패 시 기존 데이터 유지 (graceful degradation)"""
    executor = _make_executor()
    ctx = _make_mock_context()
    ls = MagicMock()

    # COSOQ00201 mock (정상)
    mock_block2 = MagicMock()
    mock_block2.ErnRat = 3.0
    mock_block2.WonDpsBalAmt = 5000000
    mock_block2.StkConvEvalAmt = 30000000
    mock_block2.WonEvalSumAmt = 35000000
    mock_block2.ConvEvalPnlAmt = 2000000

    cosoq00201_response = MagicMock()
    cosoq00201_response.error_msg = None
    cosoq00201_response.block2 = mock_block2
    cosoq00201_response.block4 = []

    mock_cosoq00201 = MagicMock()
    mock_cosoq00201.req_async = AsyncMock(return_value=cosoq00201_response)

    # COSOQ02701 mock (실패)
    cosoq02701_response = MagicMock()
    cosoq02701_response.error_msg = "rate limit exceeded"
    cosoq02701_response.block3 = []
    cosoq02701_response.block4 = None

    mock_cosoq02701 = MagicMock()
    mock_cosoq02701.req_async = AsyncMock(return_value=cosoq02701_response)

    # LS 체인 mock
    mock_accno = MagicMock()
    mock_accno.cosoq00201 = MagicMock(return_value=mock_cosoq00201)
    mock_accno.cosoq02701 = MagicMock(return_value=mock_cosoq02701)
    mock_overseas_stock = MagicMock()
    mock_overseas_stock.accno = MagicMock(return_value=mock_accno)
    ls.overseas_stock = MagicMock(return_value=mock_overseas_stock)

    result = await executor._ls_overseas_stock(ls, "account1", ctx)

    balance = result["balance"]
    # 기존 필드는 정상
    assert balance["total_pnl_rate"] == 3.0
    assert balance["cash_krw"] == 5000000
    # 신규 필드는 없음 (graceful degradation)
    assert "orderable_amount" not in balance
    assert "foreign_cash" not in balance
    assert "exchange_rate" not in balance
    # warning 로그 확인
    ctx.log.assert_any_call("warning", "COSOQ02701 조회 실패 (무시): rate limit exceeded", "account1")


# ── 해외선물 테스트 ──


@pytest.mark.asyncio
async def test_futures_balance_includes_margin():
    """선물 balance에 margin/maintenance_margin/margin_call_rate 포함 확인"""
    executor = _make_executor()
    ctx = _make_mock_context()
    ls = MagicMock()

    # CIDBQ01500 mock (빈 포지션)
    cidbq01500_response = MagicMock()
    cidbq01500_response.rsp_cd = "00707"  # 조회할 내역 없음
    cidbq01500_response.rsp_msg = "조회할 내역이 없습니다"
    cidbq01500_response.block2 = []

    mock_cidbq01500 = MagicMock()
    mock_cidbq01500.req_async = AsyncMock(return_value=cidbq01500_response)

    # CIDBQ05300 mock
    mock_b2_item = MagicMock()
    mock_b2_item.CrcyCode = "USD"
    mock_b2_item.OvrsFutsDps = 50000.0
    mock_b2_item.AbrdFutsOrdAbleAmt = 40000.0
    mock_b2_item.AbrdFutsWthdwAbleAmt = 35000.0
    mock_b2_item.AbrdFutsEvalPnlAmt = 1200.0

    mock_b3 = MagicMock()
    mock_b3.AbrdFutsCsgnMgn = 10000.0
    mock_b3.OvrsFutsMaintMgn = 8000.0
    mock_b3.MgnclRat = 125.5
    mock_b3.AbrdFutsEvalDpstgTotAmt = 55000.0
    mock_b3.AbrdFutsLqdtPnlAmt = 3000.0

    cidbq05300_response = MagicMock()
    cidbq05300_response.block2 = [mock_b2_item]
    cidbq05300_response.block3 = mock_b3

    mock_cidbq05300 = MagicMock()
    mock_cidbq05300.req_async = AsyncMock(return_value=cidbq05300_response)

    # LS 체인 mock
    mock_accno = MagicMock()
    mock_accno.CIDBQ01500 = MagicMock(return_value=mock_cidbq01500)
    mock_accno.CIDBQ05300 = MagicMock(return_value=mock_cidbq05300)
    mock_futures = MagicMock()
    mock_futures.accno = MagicMock(return_value=mock_accno)
    ls.overseas_futureoption = MagicMock(return_value=mock_futures)

    result = await executor._ls_overseas_futureoption(ls, "account1", ctx)

    balance = result["balance"]
    # 기존 필드 (하위 호환)
    assert balance["deposit"] == 50000.0
    assert balance["orderable_amount"] == 40000.0
    assert balance["total_orderable"] == 40000.0
    assert "by_currency" in balance
    assert "USD" in balance["by_currency"]
    # 신규 필드 (CIDBQ05300 block3)
    assert balance["margin"] == 10000.0
    assert balance["maintenance_margin"] == 8000.0
    assert balance["margin_call_rate"] == 125.5
    assert balance["total_eval"] == 55000.0
    assert balance["settlement_pnl"] == 3000.0


@pytest.mark.asyncio
async def test_futures_balance_by_currency_compat():
    """by_currency 구조 하위호환 확인 (CIDBQ03000 → CIDBQ05300)"""
    executor = _make_executor()
    ctx = _make_mock_context()
    ls = MagicMock()

    # CIDBQ01500 mock
    cidbq01500_response = MagicMock()
    cidbq01500_response.rsp_cd = "00707"
    cidbq01500_response.rsp_msg = ""
    cidbq01500_response.block2 = []

    mock_cidbq01500 = MagicMock()
    mock_cidbq01500.req_async = AsyncMock(return_value=cidbq01500_response)

    # CIDBQ05300 mock (다중 통화)
    mock_usd = MagicMock()
    mock_usd.CrcyCode = "USD"
    mock_usd.OvrsFutsDps = 30000.0
    mock_usd.AbrdFutsOrdAbleAmt = 25000.0
    mock_usd.AbrdFutsWthdwAbleAmt = 20000.0
    mock_usd.AbrdFutsEvalPnlAmt = 500.0

    mock_eur = MagicMock()
    mock_eur.CrcyCode = "EUR"
    mock_eur.OvrsFutsDps = 10000.0
    mock_eur.AbrdFutsOrdAbleAmt = 8000.0
    mock_eur.AbrdFutsWthdwAbleAmt = 7000.0
    mock_eur.AbrdFutsEvalPnlAmt = 200.0

    mock_b3 = MagicMock()
    mock_b3.AbrdFutsCsgnMgn = 5000.0
    mock_b3.OvrsFutsMaintMgn = 4000.0
    mock_b3.MgnclRat = 110.0
    mock_b3.AbrdFutsEvalDpstgTotAmt = 45000.0
    mock_b3.AbrdFutsLqdtPnlAmt = 700.0

    cidbq05300_response = MagicMock()
    cidbq05300_response.block2 = [mock_usd, mock_eur]
    cidbq05300_response.block3 = mock_b3

    mock_cidbq05300 = MagicMock()
    mock_cidbq05300.req_async = AsyncMock(return_value=cidbq05300_response)

    # LS 체인 mock
    mock_accno = MagicMock()
    mock_accno.CIDBQ01500 = MagicMock(return_value=mock_cidbq01500)
    mock_accno.CIDBQ05300 = MagicMock(return_value=mock_cidbq05300)
    mock_futures = MagicMock()
    mock_futures.accno = MagicMock(return_value=mock_accno)
    ls.overseas_futureoption = MagicMock(return_value=mock_futures)

    result = await executor._ls_overseas_futureoption(ls, "account1", ctx)

    balance = result["balance"]

    # by_currency 구조 확인 (기존 CIDBQ03000과 동일 키)
    assert "USD" in balance["by_currency"]
    assert "EUR" in balance["by_currency"]
    usd = balance["by_currency"]["USD"]
    assert usd["deposit"] == 30000.0
    assert usd["orderable_amount"] == 25000.0
    assert usd["withdrawable_amount"] == 20000.0
    assert usd["eval_pnl"] == 500.0
    # 다중 통화 합산
    assert balance["total_orderable"] == 33000.0  # 25000 + 8000
    assert balance["deposit"] == 40000.0  # 30000 + 10000
    # USD 기준 orderable_amount
    assert balance["orderable_amount"] == 25000.0


@pytest.mark.asyncio
async def test_futures_cidbq05300_replaces_cidbq03000():
    """CIDBQ05300 교체 후 기존 필드 유지 확인 + CIDBQ03000 미호출 검증"""
    executor = _make_executor()
    ctx = _make_mock_context()
    ls = MagicMock()

    # CIDBQ01500 mock
    cidbq01500_response = MagicMock()
    cidbq01500_response.rsp_cd = "00000"
    cidbq01500_response.rsp_msg = ""

    mock_position = MagicMock()
    mock_position.IsuCodeVal = "CLH26"
    mock_position.BnsTpCode = "2"  # long
    mock_position.BalQty = 2
    mock_position.OvrsDrvtNowPrc = 72.50
    mock_position.PchsPrc = 70.00
    mock_position.AbrdFutsEvalPnlAmt = 500.0
    mock_position.CrcyCodeVal = "USD"
    mock_position.IsuNm = "WTI Crude Oil"
    cidbq01500_response.block2 = [mock_position]

    mock_cidbq01500 = MagicMock()
    mock_cidbq01500.req_async = AsyncMock(return_value=cidbq01500_response)

    # CIDBQ05300 mock
    mock_b2 = MagicMock()
    mock_b2.CrcyCode = "USD"
    mock_b2.OvrsFutsDps = 100000.0
    mock_b2.AbrdFutsOrdAbleAmt = 80000.0
    mock_b2.AbrdFutsWthdwAbleAmt = 70000.0
    mock_b2.AbrdFutsEvalPnlAmt = 5000.0

    mock_b3 = MagicMock()
    mock_b3.AbrdFutsCsgnMgn = 20000.0
    mock_b3.OvrsFutsMaintMgn = 15000.0
    mock_b3.MgnclRat = 150.0
    mock_b3.AbrdFutsEvalDpstgTotAmt = 120000.0
    mock_b3.AbrdFutsLqdtPnlAmt = 8000.0

    cidbq05300_response = MagicMock()
    cidbq05300_response.block2 = [mock_b2]
    cidbq05300_response.block3 = mock_b3

    mock_cidbq05300 = MagicMock()
    mock_cidbq05300.req_async = AsyncMock(return_value=cidbq05300_response)

    # LS 체인 mock
    mock_accno = MagicMock()
    mock_accno.CIDBQ01500 = MagicMock(return_value=mock_cidbq01500)
    mock_accno.CIDBQ05300 = MagicMock(return_value=mock_cidbq05300)
    # CIDBQ03000은 호출되면 안됨
    mock_accno.CIDBQ03000 = MagicMock()
    mock_futures = MagicMock()
    mock_futures.accno = MagicMock(return_value=mock_accno)
    ls.overseas_futureoption = MagicMock(return_value=mock_futures)

    result = await executor._ls_overseas_futureoption(ls, "account1", ctx)

    # CIDBQ03000 미호출 검증
    mock_accno.CIDBQ03000.assert_not_called()

    # 포지션 확인
    assert len(result["positions"]) == 1
    pos = result["positions"][0]
    assert pos["symbol"] == "CLH26"
    assert pos["direction"] == "long"
    assert pos["quantity"] == 2

    # balance 기존 필드 + 신규 필드 확인
    balance = result["balance"]
    assert balance["deposit"] == 100000.0
    assert balance["orderable_amount"] == 80000.0
    assert balance["margin"] == 20000.0
    assert balance["maintenance_margin"] == 15000.0
    assert balance["margin_call_rate"] == 150.0
    assert balance["total_eval"] == 120000.0
    assert balance["settlement_pnl"] == 8000.0
