"""Exact-date COSAQ00102 order totals using the SDK's documented history query."""

import asyncio
from datetime import datetime, timezone

from .broker_evidence import checked_body
from .broker_snapshot import required
from .order_recovery import VerifiedOrderTotal
from .position_reconciliation import ReconciliationUnavailable, quantity


async def read_stock_order_totals(ls, tracker, orders):
    totals, _ = await _read_stock_order_outcomes(ls, tracker, orders, include_cancellations=False)
    return totals


async def read_stock_order_outcomes(ls, tracker, orders):
    """Include positively matched, wholly unfilled cancellations at startup."""
    return await _read_stock_order_outcomes(ls, tracker, orders, include_cancellations=True)


def _unfilled_cancellation(tracker, day, original, rows, observed):
    from .order_cancellation import VerifiedUnfilledCancellation

    number = str(required(original, "OrdNo")).lstrip("0")
    ordered = quantity(required(original, "OrdQty"))
    # This exact zero-fill, full-remaining cancellation was owner-observed.
    # Do not generalize it to partial executions, amendments or code enums.
    if (ordered <= 0 or any(quantity(required(original, field)) != 0
                           for field in ("ExecQty", "AllExecQty", "UnercQty", "OrgOrdNo"))):
        raise ReconciliationUnavailable("unverified_partial_cancellation")
    children = [row for row in rows if str(required(row, "OrgOrdNo")).lstrip("0") == number]
    if len(children) != 1:
        raise ReconciliationUnavailable("ambiguous_cancellation_chain")
    child = children[0]
    symbol = original.ShtnIsuNo.strip() if original.ShtnIsuNo else str(required(original, "IsuNo")).strip()
    child_symbol = child.ShtnIsuNo.strip() if child.ShtnIsuNo else str(required(child, "IsuNo")).strip()
    if (child_symbol != symbol
            or required(child, "BnsTpCode") != required(original, "BnsTpCode")
            or required(child, "OrdMktCode") != required(original, "OrdMktCode")
            or required(child, "MrcTpNm") != "취소"
            or required(child, "OrdTrxPtnNm") != "취소완료"
            or quantity(required(child, "OrdQty")) != ordered
            or quantity(required(child, "CnfQty")) != ordered
            or any(quantity(required(child, field)) != 0
                   for field in ("ExecQty", "AllExecQty", "UnercQty"))):
        raise ReconciliationUnavailable("unverified_cancellation_chain")
    item = VerifiedUnfilledCancellation(
        tracker.execution_key, tracker.product, tracker.provider, tracker.trading_mode,
        day, number, str(required(child, "OrdNo")), symbol,
        {"1": "sell", "2": "buy"}.get(str(required(original, "BnsTpCode"))),
        ordered, {"81": "NYSE", "82": "NASDAQ"}.get(str(required(original, "OrdMktCode"))), observed)
    item.validate(tracker)
    return item


async def _read_stock_order_outcomes(ls, tracker, orders, *, include_cancellations):
    from programgarden_finance import COSAQ00102

    if tracker.product != "overseas_stock" or not tracker.execution_key:
        raise ReconciliationUnavailable("unsupported_order_recovery_scope")
    dates = sorted({order["order_date"] for order in orders})
    if len(dates) > 20 or len(orders) > 500:
        raise ReconciliationUnavailable("order_recovery_window_too_large")
    totals, cancellations = [], []
    for index, day in enumerate(dates):
        if index:
            await asyncio.sleep(2)
        # run_cosaq00102.py's history request, using the already-observed all-
        # market selector from the startup adapter. Historical queries never
        # substitute today's business date or enable the intraday override.
        query = ls.overseas_stock().accno().cosaq00102(COSAQ00102.COSAQ00102InBlock1(
            RecCnt=1, QryTpCode="1", BkseqTpCode="1", OrdMktCode="00", BnsTpCode="0",
            IsuNo="", SrtOrdNo=999999999, OrdDt=day,
            ExecYn="0" if include_cancellations else "1", CrcyCode="000",
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
            if include_cancellations and filled == 0:
                cancellations.append(_unfilled_cancellation(
                    tracker, response.block1.OrdDt, row, response.block3, observed))
                continue
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
    return totals, cancellations
