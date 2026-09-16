"""Exact-date COSAQ00102 order totals using the SDK's documented history query."""

import asyncio
from datetime import datetime, timezone

from .broker_evidence import checked_body
from .broker_snapshot import required
from .order_recovery import VerifiedOrderTotal
from .position_reconciliation import ReconciliationUnavailable, quantity


async def read_stock_order_totals(ls, tracker, orders):
    from programgarden_finance import COSAQ00102

    if tracker.product != "overseas_stock" or not tracker.execution_key:
        raise ReconciliationUnavailable("unsupported_order_recovery_scope")
    dates = sorted({order["order_date"] for order in orders})
    if len(dates) > 20 or len(orders) > 500:
        raise ReconciliationUnavailable("order_recovery_window_too_large")
    totals = []
    for index, day in enumerate(dates):
        if index:
            await asyncio.sleep(2)
        # run_cosaq00102.py's history request, using the already-observed all-
        # market selector from the startup adapter. Historical queries never
        # substitute today's business date or enable the intraday override.
        query = ls.overseas_stock().accno().cosaq00102(COSAQ00102.COSAQ00102InBlock1(
            RecCnt=1, QryTpCode="1", BkseqTpCode="1", OrdMktCode="00", BnsTpCode="0",
            IsuNo="", SrtOrdNo=999999999, OrdDt=day, ExecYn="1", CrcyCode="000",
            ThdayBnsAppYn="0", LoanBalHldYn="0"))
        observed = datetime.now(timezone.utc)
        response = await query.req_async()
        await checked_body(response, "COSAQ00102", query)
        expected = {str(row["order_no"]).lstrip("0") for row in orders if row["order_date"] == day}
        found = set()
        for row in response.block3:
            number = str(required(row, "OrdNo")).lstrip("0")
            if number not in expected:
                continue
            if number in found:
                raise ReconciliationUnavailable("ambiguous_broker_order_total")
            found.add(number)
            symbol = row.ShtnIsuNo.strip() if row.ShtnIsuNo else str(required(row, "IsuNo")).strip()
            side = {"1": "sell", "2": "buy"}.get(str(required(row, "BnsTpCode")))
            filled = quantity(required(row, "ExecQty"))
            if quantity(required(row, "AllExecQty")) != filled:
                raise ReconciliationUnavailable("order_chain_requires_reconciliation")
            original = required(row, "OrgOrdNo")
            if original != 0:
                raise ReconciliationUnavailable("order_chain_requires_reconciliation")
            total = VerifiedOrderTotal(
                tracker.execution_key, tracker.product, tracker.provider, tracker.trading_mode,
                response.block1.OrdDt, number, symbol, side,
                quantity(required(row, "OrdQty")), filled,
                quantity(required(row, "OvrsExecPrc")), quantity(required(row, "UnercQty")),
                str(required(row, "CrcyCode")), str(required(row, "ExecTime")), observed,
                original_order_no=str(original),
            )
            total.validate(tracker)
            totals.append(total)
        if found != expected:
            raise ReconciliationUnavailable("broker_order_total_unavailable")
    return totals
