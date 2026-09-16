"""Read scoped startup evidence using existing SDK example query parameters."""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from .broker_evidence import checked_body, StartupQueryDateMismatch
from .position_reconciliation import (
    ReconciliationUnavailable, VerifiedPositionSnapshot, normalized_symbol, quantity,
)


@dataclass(frozen=True)
class BrokerStartupSnapshot:
    positions: VerifiedPositionSnapshot
    pending_orders: tuple[dict, ...]


def required(row, field):
    if field not in row.model_fields_set or getattr(row, field) in (None, ""):
        raise ReconciliationUnavailable(f"missing_broker_field:{field}")
    return getattr(row, field)


def pending_row(row, product, *, day=None):
    """Keep broker dates and explicit sides; never infer cancellation identity."""
    if product == "overseas_stock":
        symbol = row.ShtnIsuNo.strip() if row.ShtnIsuNo else str(required(row, "IsuNo")).strip()
        order_no = str(required(row, "OrdNo"))
        # COSAQ00102 detail rows do not expose OrdDt. Use only the validated
        # exact-date query echo, never an invented detail field or wall clock.
        order_day = day
        side = {"01": "sell", "02": "buy"}.get(str(required(row, "BnsTpCode")))
        market = str(required(row, "OrdMktCode"))
    else:
        symbol = str(required(row, "IsuCodeVal")).strip()
        order_no = str(required(row, "OvrsFutsOrdNo"))
        order_day = str(required(row, "OrdDt"))
        side = {"1": "sell", "2": "buy"}.get(str(required(row, "BnsTpCode")))
        market = None  # Futures cancellation needs the contract, not a guessed venue.
    remainder = quantity(required(row, "UnercQty"))
    if remainder == 0:
        return None
    if not side or not symbol or not order_no.isdigit() or int(order_no) <= 0:
        raise ReconciliationUnavailable("invalid_pending_order_identity")
    try:
        datetime.strptime(order_day, "%Y%m%d")
    except (TypeError, ValueError):
        raise ReconciliationUnavailable("missing_broker_order_date") from None
    return {"order_id": order_no, "order_date": order_day, "symbol": symbol,
            "side": side, "remaining_quantity": remainder, "market_code": market}


async def read_broker_snapshot(ls, *, execution_key, product, provider, trading_mode):
    """One positions/pending pair, spaced for the shared app key; no order calls."""
    observed_at = datetime.now(timezone.utc)
    day = observed_at.astimezone(timezone(timedelta(hours=9))).strftime("%Y%m%d")
    positions, pending = {}, []
    if product == "korea_stock":
        from programgarden_finance.ls.korea_stock.extension.valuation import collect_domestic_trading_positions
        from programgarden_finance.ls.korea_stock.extension.account_queries import collect_domestic_open_orders

        _, rows = await collect_domestic_trading_positions(ls.korea_stock().accno())
        for row in rows:
            symbol = normalized_symbol(str(required(row, "IsuNo")), product)
            if symbol in positions:
                raise ReconciliationUnavailable("ambiguous_position_rows")
            positions[symbol] = quantity(required(row, "BnsBaseBalQty"))
        await asyncio.sleep(2)
        pending = await collect_domestic_open_orders(ls.korea_stock().accno())
        # t0425 is the documented current-day inquiry. Retain that observation
        # date for exact ledger matching; never widen it to yesterday's order.
        for row in pending:
            row["order_date"] = day
        source = "CSPAQ12300+t0425"
    elif product == "overseas_stock":
        from programgarden_finance import COSOQ00201, COSAQ00102

        accno = ls.overseas_stock().accno()
        query = accno.cosoq00201(COSOQ00201.COSOQ00201InBlock1(
            RecCnt=1, BaseDt=day, CrcyCode="ALL", AstkBalTpCode="00"))
        response = await query.req_async()
        await checked_body(response, "COSOQ00201", query)
        for row in response.block4:
            symbol = row.ShtnIsuNo.strip() if row.ShtnIsuNo else str(required(row, "IsuNo")).strip()
            symbol = normalized_symbol(symbol, product)
            if symbol in positions:
                # Multiple custody/fractional rows need separate evidence before
                # aggregation; a duplicate must not silently overwrite a holding.
                raise ReconciliationUnavailable("ambiguous_position_rows")
            positions[symbol] = quantity(required(row, "AstkBalQty"))
        await asyncio.sleep(2)
        for attempt in range(2):
            query = accno.cosaq00102(COSAQ00102.COSAQ00102InBlock1(
                RecCnt=1, QryTpCode="1", BkseqTpCode="1", OrdMktCode="00", BnsTpCode="0",
                IsuNo="", SrtOrdNo=999999999, OrdDt=day, ExecYn="2", CrcyCode="000",
                ThdayBnsAppYn="1", LoanBalHldYn="0"))
            response = await query.req_async()
            try:
                await checked_body(response, "COSAQ00102", query)
            except StartupQueryDateMismatch as exc:
                if attempt:
                    raise
                day = exc.business_day
                await asyncio.sleep(2)
                continue
            pending = [value for row in response.block3 if (value := pending_row(row, product, day=response.block1.OrdDt)) is not None]
            break
        source = "COSOQ00201+COSAQ00102"
    elif product == "overseas_futures":
        from programgarden_finance import CIDBQ01500, CIDBQ02400

        accno = ls.overseas_futureoption().accno()
        query = accno.CIDBQ01500(body=CIDBQ01500.CIDBQ01500InBlock1(
            RecCnt=1, AcntTpCode="1", FcmAcntNo="", QryDt="", BalTpCode="2"))
        response = await query.req_async()
        await checked_body(response, "CIDBQ01500", query)
        for row in response.block2:
            symbol = normalized_symbol(str(required(row, "IsuCodeVal")), product)
            side = str(required(row, "BnsTpCode"))
            amount = quantity(required(row, "BalQty"))
            if side not in {"1", "2"}:
                raise ReconciliationUnavailable("unknown_position_side")
            # The current FIFO lot store represents buy lots. Never net a short
            # position into long availability or import it as strategy ownership.
            if side == "2":
                positions[symbol] = positions.get(symbol, Decimal(0)) + amount
        await asyncio.sleep(2)
        query = accno.CIDBQ02400(body=CIDBQ02400.CIDBQ02400InBlock1(
            RecCnt=1, IsuCodeVal="", QrySrtDt="", QryEndDt="", ThdayTpCode="1",
            OrdStatCode="2", BnsTpCode="0", QryTpCode="2", OrdPtnCode="00", OvrsDrvtFnoTpCode="A"))
        response = await query.req_async()
        await checked_body(response, "CIDBQ02400", query)
        pending = [value for row in response.block2 if (value := pending_row(row, product)) is not None]
        source = "CIDBQ01500+CIDBQ02400"
    else:
        raise ReconciliationUnavailable("unsupported_startup_product")
    keys = [(row["order_date"], str(row["order_id"]).lstrip("0")) for row in pending]
    if len(keys) != len(set(keys)):
        raise ReconciliationUnavailable("ambiguous_pending_orders")
    return BrokerStartupSnapshot(
        VerifiedPositionSnapshot(execution_key, product, provider, trading_mode, observed_at,
                                 positions, source, True, True, tuple(pending)), tuple(pending))
