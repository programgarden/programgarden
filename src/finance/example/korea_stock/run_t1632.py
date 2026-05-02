"""run_t1632.py — manual integration test for t1632 시간대별프로그램매매추이.

Scenarios:
  1. Single-page first request (date='', time='', gubun='0' = 거래소/KOSPI).
  2. Multi-page auto-paging via occurs_req() (collects all time buckets until
     tr_cont is no longer 'Y').

Requires .env with APPKEY_KOREA / APPSECRET_KOREA.
Run: cd src/finance && poetry run python example/korea_stock/run_t1632.py

NOTE: Row meaning, array ordering, and any arithmetic relationship between
fields (tot1/tot2/tot3, cha1/cha2/cha3, bcha1/bcha2/bcha3) are not
documented in the LS public spec — values are printed as reported by LS.
"""

import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t1632

logger = logging.getLogger(__name__)

load_dotenv()


def _print_cont_block(label: str, cont_block) -> None:
    """Print t1632OutBlock continuation marker fields."""
    if cont_block is None:
        logger.info(f"[{label}] cont_block: None")
        return
    logger.info(
        f"[{label}] cont_block — date={cont_block.date!r}, "
        f"time={cont_block.time!r}, idx={cont_block.idx}, "
        f"ex_gubun={cont_block.ex_gubun!r}"
    )


def _print_block_summary(label: str, block: list) -> None:
    """Print a summary of t1632OutBlock1 rows (first row shown in full)."""
    logger.info(f"[{label}] block — {len(block)} rows")
    if not block:
        return
    row = block[0]
    logger.info(
        f"  row[0]: time={row.time!r}, k200jisu={row.k200jisu}, "
        f"sign={row.sign!r}, change={row.change}, k200basis={row.k200basis}"
    )
    logger.info(
        f"  row[0]: tot1={row.tot1:,}, tot2={row.tot2:,}, tot3={row.tot3:,}"
    )
    logger.info(
        f"  row[0]: cha1={row.cha1:,}, cha2={row.cha2:,}, cha3={row.cha3:,}"
    )
    logger.info(
        f"  row[0]: bcha1={row.bcha1:,}, bcha2={row.bcha2:,}, bcha3={row.bcha3:,}"
    )


def _print_response(label: str, response) -> None:
    """Pretty-print a single t1632 response page."""
    logger.info("=" * 110)
    logger.info(f"[{label}] rsp_cd={response.rsp_cd!r}, rsp_msg={response.rsp_msg!r}")

    if response.error_msg:
        logger.error(f"[{label}] Request failed: {response.error_msg}")
        return

    _print_cont_block(label, response.cont_block)
    _print_block_summary(label, response.block)


def test_scenario1_first_request():
    """Scenario 1 — Single-page first request.

    gubun='0' (거래소/KOSPI), gubun1='0' (amount), gubun2='1', gubun3='1',
    date='' (first request), time='' (first request), exchgubun='K'.

    Prints cont_block (continuation cursor) + block row count + first row
    summary. Row ordering and arithmetic identities between fields are not
    asserted — consumed as reported by LS.
    """
    ls = LS()
    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA"),
    )
    if login_result is False:
        logger.error("Login failed")
        return

    tr = ls.국내주식().프로그램매매().시간대별프로그램매매추이(
        t1632.T1632InBlock(
            gubun="0",
            gubun1="0",
            gubun2="1",
            gubun3="1",
            date="",
            time="",
            exchgubun="K",
        )
    )
    response = tr.req()
    _print_response("거래소 first-request", response)


def test_scenario2_occurs_req_autopaging():
    """Scenario 2 — Auto-paging via occurs_req().

    Uses the same InBlock as Scenario 1 (first request, date/time empty).
    occurs_req() automatically advances the date+time CTS cursors from each
    response's cont_block until tr_cont is no longer 'Y'.

    Prints the page count and per-page row count via callback.
    Final totals (pages, rows) are logged after all pages are collected.
    """
    ls = LS()
    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA"),
    )
    if login_result is False:
        logger.error("Login failed")
        return

    tr = ls.국내주식().프로그램매매().시간대별프로그램매매추이(
        t1632.T1632InBlock(
            gubun="0",
            gubun1="0",
            gubun2="1",
            gubun3="1",
            date="",
            time="",
            exchgubun="K",
        )
    )

    page_count = 0
    total_rows = 0

    def _page_callback(page_response, status):
        nonlocal page_count, total_rows
        if page_response is None:
            logger.info(f"[occurs_req] status={status.name}")
            return
        page_count += 1
        rows = len(page_response.block)
        total_rows += rows
        logger.info(
            f"[occurs_req page {page_count}] status={status.name}, "
            f"rsp_cd={page_response.rsp_cd!r}, rows={rows}"
        )
        if page_response.cont_block:
            logger.info(
                f"  cont_block — date={page_response.cont_block.date!r}, "
                f"time={page_response.cont_block.time!r}"
            )

    logger.info("=" * 110)
    logger.info("[거래소 occurs_req auto-paging] starting...")
    pages = tr.occurs_req(callback=_page_callback, delay=1)
    logger.info(
        f"[거래소 occurs_req] finished — pages={len(pages)}, "
        f"total_rows={total_rows}"
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_scenario1_first_request()
    test_scenario2_occurs_req_autopaging()
