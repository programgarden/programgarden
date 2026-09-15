"""Observed non-credit cash and complete pending-order evidence for domestic nodes."""

import asyncio
import re

from ..accno.CSPAQ22200.blocks import CSPAQ22200InBlock1, CSPAQ22200Response
from ..accno.t0425.blocks import T0425InBlock, T0425Response
from .valuation import DomesticPositionEvidenceUnavailable, observed_amount


async def collect_domestic_cash_evidence(accno_client):
    """Use the SDK example's stock-balance scope; no summary fallback or retries."""
    response = await accno_client.cspaq22200(body=CSPAQ22200InBlock1(BalCreTp="0")).req_async()
    if (not isinstance(response, CSPAQ22200Response) or response.status_code != 200
            or response.error_msg or response.rsp_cd not in {"00000", "00136"}
            or response.block1 is None or "BalCreTp" not in response.block1.model_fields_set
            or response.block1.BalCreTp != "0" or response.block2 is None):
        raise DomesticPositionEvidenceUnavailable("incomplete_cash_response")
    cash = observed_amount(response.block2, "RcvblUablOrdAbleAmt")
    if cash is None or cash < 0:
        raise DomesticPositionEvidenceUnavailable("non_credit_cash_unavailable")
    return {
        "orderable_amount": cash,
        "deposit": observed_amount(response.block2, "Dps"),
        "d2_deposit": observed_amount(response.block2, "D2Dps"),
        "margin_cash": observed_amount(response.block2, "MgnMny"),
    }


def _pending_order(row):
    if "ordrem" not in row.model_fields_set or row.ordrem < 0:
        raise DomesticPositionEvidenceUnavailable("missing_or_invalid_remaining_quantity")
    if row.ordrem == 0:
        return None
    required = {"ordno", "expcode", "medosu", "qty", "cheqty", "ordrem"}
    if not required <= row.model_fields_set:
        raise DomesticPositionEvidenceUnavailable("missing_order_fields")
    if (row.ordno <= 0 or not re.fullmatch(r"[0-9]{6}", row.expcode)
            or row.qty <= 0 or not 0 <= row.cheqty <= row.qty
            or not 0 <= row.ordrem <= row.qty):
        raise DomesticPositionEvidenceUnavailable("invalid_order_quantity_or_identity")
    side = {"1": "sell", "2": "buy", "매도": "sell", "매수": "buy"}.get(row.medosu.strip())
    if side is None:
        raise DomesticPositionEvidenceUnavailable("unknown_pending_order_side")
    venue = row.exchname.strip() if "exchname" in row.model_fields_set else None
    return {
        "order_id": str(row.ordno), "symbol": row.expcode, "exchange": "KRX",
        "order_venue": venue if venue in {"KRX", "NXT"} else None,
        "name": "", "side": side, "quantity": row.qty,
        "filled_quantity": row.cheqty, "remaining_quantity": row.ordrem,
        "price": observed_amount(row, "price"),
        "order_type": row.hogagb if "hogagb" in row.model_fields_set else None,
        "order_time": row.ordtime if "ordtime" in row.model_fields_set else None,
    }


async def collect_domestic_open_orders(accno_client):
    """Read all pages of the exact all-orders example, then select observed remainders.

    Instrument identity stays KRX across venues; order_venue is separate evidence.
    A partial list must never permit another buy. Broker rejections are not retried.
    """
    request = T0425InBlock(expcode="", chegb="0", medosu="0", sortgb="1", cts_ordno="")
    tr = accno_client.t0425(body=request)
    pending, cursors, order_ids = [], set(), set()
    for _ in range(100):
        response = await tr.req_async()
        if (not isinstance(response, T0425Response) or response.status_code != 200
                or response.error_msg or response.rsp_cd != "00000"
                or not response._orders_block_present or response.header is None
                or not {"tr_cd", "tr_cont", "tr_cont_key"} <= response.header.model_fields_set
                or response.header.tr_cd != "t0425" or response.cont_block is None
                or "cts_ordno" not in response.cont_block.model_fields_set):
            raise DomesticPositionEvidenceUnavailable("incomplete_orders_response")
        for row in response.block:
            item = _pending_order(row)
            if item is not None:
                if row.ordno in order_ids:
                    raise DomesticPositionEvidenceUnavailable("duplicate_order_observation")
                order_ids.add(row.ordno)
                pending.append(item)
        cursor = response.cont_block.cts_ordno.strip()
        if (not cursor and response.header.tr_cont in {"N", "0"}
                and not response.header.tr_cont_key.strip()):
            return pending
        if (not cursor or cursor in cursors or response.header.tr_cont != "Y"
                or not response.block):
            raise DomesticPositionEvidenceUnavailable("invalid_orders_continuation")
        cursors.add(cursor)
        request.cts_ordno = response.cont_block.cts_ordno
        tr.request_data.header.tr_cont = "Y"
        tr.request_data.header.tr_cont_key = response.header.tr_cont_key
        await asyncio.sleep(1.1)
    raise DomesticPositionEvidenceUnavailable("orders_continuation_limit")
