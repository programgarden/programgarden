"""Complete domestic position observations on an explicit average-cost basis."""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import re

from ..accno.CSPAQ12300.blocks import CSPAQ12300InBlock1, CSPAQ12300Response
from ..accno.t0424.blocks import T0424InBlock, T0424Response


class DomesticPositionEvidenceUnavailable(ValueError):
    """A partial or ambiguous response cannot become a current account snapshot."""


def observed_amount(row, field):
    if field not in row.model_fields_set:
        return None
    value = getattr(row, field)
    if value is None or isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value))
        return number if number.is_finite() else None
    except (InvalidOperation, ValueError):
        return None


def position_evidence(rows, observed_at):
    """Whitelisted rows; missing costs do not erase an observed holding quantity."""
    positions = {}
    earned, lost = Decimal(0), Decimal(0)
    amounts_complete = True
    seen = set()
    for row in rows:
        if "IsuNo" not in row.model_fields_set:
            raise DomesticPositionEvidenceUnavailable("missing_symbol")
        symbol = row.IsuNo.removeprefix("A")
        quantity = observed_amount(row, "BnsBaseBalQty")
        if not re.fullmatch(r"[0-9]{6}", symbol) or symbol in seen:
            raise DomesticPositionEvidenceUnavailable("ambiguous_symbol_rows")
        seen.add(symbol)
        if quantity is None or quantity < 0 or quantity != quantity.to_integral_value():
            raise DomesticPositionEvidenceUnavailable("missing_trade_basis_quantity")
        pnl = observed_amount(row, "EvalPnl")
        if quantity == 0:
            amounts_complete &= pnl == 0
            continue
        average = observed_amount(row, "AvrUprc")
        purchase = observed_amount(row, "PchsAmt")
        price = observed_amount(row, "NowPrc")
        evaluation = observed_amount(row, "BalEvalAmt")
        average = average if average is not None and average > 0 else None
        purchase = purchase if purchase is not None and purchase > 0 else None
        price = price if price is not None and price > 0 else None
        evaluation = evaluation if evaluation is not None and evaluation >= 0 else None
        positions[symbol] = {
            "symbol": symbol, "quantity": int(quantity), "product": "korea_stock",
            "symbol_name": row.IsuNm if "IsuNm" in row.model_fields_set else "",
            "currency": "KRW", "buy_price": average, "average_price": average,
            "acquisition_amount": purchase, "current_price": price,
            "eval_amount": evaluation, "pnl_amount": pnl,
            "pnl_status": "available" if pnl is not None else "unavailable",
            "pnl_unavailable_reason": None if pnl is not None else "broker_field_not_observed",
            "cost_basis": "broker_average_commission_excluded",
            "cost_status": "available" if average is not None and purchase is not None else "unavailable",
            "cost_unavailable_reason": None if average is not None and purchase is not None else "broker_field_not_observed",
            "observed_at": observed_at.isoformat(),
        }
        if pnl is None:
            amounts_complete = False
        else:
            earned += max(pnl, Decimal(0))
            lost += max(-pnl, Decimal(0))
    valuation = None
    if amounts_complete:
        valuation = {
            "version": 1, "product": "korea_stock", "source": "CSPAQ12300",
            "basis": "broker_open_positions", "commission_basis": "excluded",
            "observed_at": observed_at.isoformat(),
            "groups": [{"currency": "KRW", "earned": earned, "lost": lost, "net": earned - lost}],
        }
    return {"positions": positions, "account_valuation": valuation,
            "observed_at": observed_at.isoformat(), "source": "CSPAQ12300"}


async def collect_domestic_position_evidence(accno_client):
    """Use the exact owner example, bounded pagination and no rejection retries.

    OutBlock2 is entirely unavailable and never supplies any value here.
    Header continuation is copied onto the same authenticated request instance.
    """
    request = CSPAQ12300InBlock1(RecCnt=1, BalCreTp="0", CmsnAppTpCode="0",
                               D2balBaseQryTp="0", UprcTpCode="0")
    tr = accno_client.cspaq12300(body=request)
    rows, cursors = [], set()
    for _ in range(100):
        response = await tr.req_async()
        if (not isinstance(response, CSPAQ12300Response) or response.status_code != 200
                or response.error_msg or response.rsp_cd not in {"00000", "00136"}
                or not response._positions_blocks_present or response.header is None
                or not {"tr_cd", "tr_cont", "tr_cont_key"} <= response.header.model_fields_set
                or response.header.tr_cd not in {"CSPAQ12300", "CSPAQ"}):
            raise DomesticPositionEvidenceUnavailable("incomplete_broker_response")
        echo = response.block1
        fields = {"RecCnt", "BalCreTp", "CmsnAppTpCode", "D2balBaseQryTp", "UprcTpCode"}
        if echo is None or not fields <= echo.model_fields_set or any(
                getattr(echo, name) != getattr(request, name) for name in fields):
            raise DomesticPositionEvidenceUnavailable("request_basis_mismatch")
        rows.extend(response.block3)
        flag, cursor = response.header.tr_cont, response.header.tr_cont_key.strip()
        if flag == "N" and not cursor:
            return position_evidence(rows, datetime.now(timezone.utc))
        if flag != "Y" or not cursor or cursor in cursors or not response.block3:
            raise DomesticPositionEvidenceUnavailable("invalid_continuation")
        cursors.add(cursor)
        tr.request_data.header.tr_cont = "Y"
        tr.request_data.header.tr_cont_key = response.header.tr_cont_key
        await asyncio.sleep(1.1)
    raise DomesticPositionEvidenceUnavailable("continuation_limit")


async def collect_domestic_trading_positions(accno_client):
    """Preserve the existing t0424 BEP/fill/cost request, reading every page."""
    request = T0424InBlock(prcgb="2", chegb="2", dangb="0", charge="1")
    tr = accno_client.t0424(body=request)
    rows, cursors, symbols = [], set(), set()
    first = None
    for _ in range(100):
        response = await tr.req_async()
        if (not isinstance(response, T0424Response) or response.status_code != 200
                or response.error_msg or response.rsp_cd != "00000"
                or not response._positions_blocks_present or response.header is None
                or not {"tr_cd", "tr_cont", "tr_cont_key"} <= response.header.model_fields_set
                or response.header.tr_cd != "t0424" or response.cont_block is None
                or "cts_expcode" not in response.cont_block.model_fields_set):
            raise DomesticPositionEvidenceUnavailable("incomplete_trading_positions")
        if first is None:
            first = response
        for row in response.block:
            if (not {"expcode", "janqty", "pamt", "price", "mamt", "appamt", "dtsunik", "sunikrt"}
                    <= row.model_fields_set or not re.fullmatch(r"[0-9]{6}", row.expcode)
                    or row.expcode in symbols or row.janqty < 0):
                raise DomesticPositionEvidenceUnavailable("ambiguous_trading_positions")
            symbols.add(row.expcode)
            rows.append(row)
        cursor = response.cont_block.cts_expcode.strip()
        flag = response.header.tr_cont
        if not cursor and flag in {"N", "0"} and not response.header.tr_cont_key.strip():
            return first, rows
        if not cursor or cursor in cursors or flag != "Y" or not response.block:
            raise DomesticPositionEvidenceUnavailable("invalid_trading_continuation")
        cursors.add(cursor)
        request.cts_expcode = response.cont_block.cts_expcode
        tr.request_data.header.tr_cont = "Y"
        tr.request_data.header.tr_cont_key = response.header.tr_cont_key
        await asyncio.sleep(1.1)
    raise DomesticPositionEvidenceUnavailable("trading_continuation_limit")
