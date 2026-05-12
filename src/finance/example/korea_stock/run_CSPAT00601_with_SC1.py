"""CSPAT00601 (현물주문) + SC1 (주식주문체결) OrdNo matching example.

EN:
    Production template for placing a Korean stock order via CSPAT00601 and
    awaiting the fill via the SC1 WebSocket execution event, matched by order
    number. Handles partial fills (multiple SC1 events with ordxctptncode='11')
    and rejection (SC4 path via ordxctptncode='14').

    Pattern:
        1. Subscribe SC1 (registers all SC0~SC4 order events on the account).
        2. Place an order with CSPAT00601 → returns block2.OrdNo (int).
        3. Cast OrdNo to str to match SC1.body.ordno (str).
        4. await an asyncio.Future resolved when unercqty == '0' (full fill).

    Note: SC0~SC4 share a single account registration. Subscribing only SC1
    is sufficient; SC4 (rejection) events also arrive on the same channel and
    can be inspected via ordxctptncode='14'. For independent handlers, use
    on_sc4_message() in addition.

KO:
    현물주문(CSPAT00601) 접수 후 SC1 체결 이벤트로 OrdNo 매칭하여 체결을
    기다리는 실전 템플릿. 부분체결 (체결 이벤트 여러 회) 및 거부 처리
    포함. SC0~SC4는 계좌 단위로 등록을 공유하므로 SC1 등록만으로 모든
    주문 이벤트가 활성화됩니다.

장 마감 시간대에는 모의/실전 모두 SC1 이벤트가 도달하지 않습니다. 파서/
매칭 로직 검증은 tests/test_cspat00601_sc1_mock.py 참조.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Dict

from dotenv import load_dotenv

from programgarden_finance import LS, CSPAT00601
from programgarden_finance.ls.korea_stock.real.SC1.blocks import SC1RealResponse

logger = logging.getLogger(__name__)
load_dotenv()


ORD_FILL_CODE = "11"
ORD_REJECT_CODE = "14"


async def place_order_and_await_fill(
    ls: LS,
    *,
    isu_no: str,
    qty: int,
    price: int,
    is_buy: bool,
    timeout_sec: float = 30.0,
) -> Dict[str, object]:
    """Place a CSPAT00601 order and await fill via SC1 OrdNo matching.

    Returns a dict with keys: ord_no, total_filled_qty, fills (list of dicts),
    rejected (bool).
    """
    pending: Dict[str, asyncio.Future] = {}
    fills: Dict[str, list] = {}

    real_client = ls.korea_stock().real()
    await real_client.connect()
    sc1 = real_client.SC1()

    def on_sc1(resp: SC1RealResponse):
        if resp.body is None:
            return
        ordno = resp.body.ordno
        if ordno not in pending:
            return
        fut = pending[ordno]
        code = resp.body.ordxctptncode

        if code == ORD_FILL_CODE:
            fills.setdefault(ordno, []).append({
                "execqty": int(resp.body.execqty or "0"),
                "execprc": int(resp.body.execprc or "0"),
                "exectime": resp.body.exectime,
            })
            if resp.body.unercqty == "0" and not fut.done():
                fut.set_result("filled")
        elif code == ORD_REJECT_CODE:
            if not fut.done():
                fut.set_exception(RuntimeError(
                    f"order rejected: rjtqty={resp.body.rjtqty} msgcode={resp.body.msgcode}"
                ))

    sc1.on_sc1_message(on_sc1)

    bns_code = "2" if is_buy else "1"
    expected_rsp = "00040" if is_buy else "00039"
    m_order = ls.국내주식().주문().현물주문(
        CSPAT00601.CSPAT00601InBlock1(
            IsuNo=isu_no,
            OrdQty=qty,
            OrdPrc=price,
            BnsTpCode=bns_code,
            OrdprcPtnCode="00",
            MgntrnCode="000",
            LoanDt="",
            OrdCndiTpCode="0",
        )
    )
    response = await m_order.req_async()

    if response.error_msg is not None:
        raise RuntimeError(f"order transport failed: {response.error_msg}")
    if response.status_code is None or response.status_code >= 400:
        raise RuntimeError(f"order HTTP {response.status_code}: {response.rsp_msg}")
    if response.rsp_cd != expected_rsp:
        raise RuntimeError(f"order rejected at accept: rsp_cd={response.rsp_cd} rsp_msg={response.rsp_msg}")
    if response.block2 is None or response.block2.OrdNo == 0:
        raise RuntimeError("order accepted but OrdNo missing — cannot track fill")

    ord_no = str(response.block2.OrdNo)
    pending[ord_no] = asyncio.get_running_loop().create_future()

    try:
        await asyncio.wait_for(pending[ord_no], timeout=timeout_sec)
    except asyncio.TimeoutError:
        return {
            "ord_no": ord_no,
            "total_filled_qty": sum(f["execqty"] for f in fills.get(ord_no, [])),
            "fills": fills.get(ord_no, []),
            "rejected": False,
            "timed_out": True,
        }

    total = sum(f["execqty"] for f in fills.get(ord_no, []))
    return {
        "ord_no": ord_no,
        "total_filled_qty": total,
        "fills": fills.get(ord_no, []),
        "rejected": False,
        "timed_out": False,
    }


async def main():
    logging.basicConfig(level=logging.INFO)

    ls = LS.get_instance()
    if not ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA"),
    ):
        logger.error("login failed")
        return

    try:
        result = await place_order_and_await_fill(
            ls,
            isu_no="005930",
            qty=1,
            price=100,
            is_buy=True,
            timeout_sec=30.0,
        )
        logger.info(f"result: {result}")
    except RuntimeError as e:
        logger.error(f"order error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
