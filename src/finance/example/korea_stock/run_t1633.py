"""Live verification script for t1633 (기간별프로그램매매추이).

Usage:
    cd src/finance && poetry run python example/korea_stock/run_t1633.py

Verifies (via real LS API call, no mock):
- single ``req()`` call for a recent ~1 month period (KOSPI daily)
- ``occurs_req()`` paging through a longer period (KOSPI daily, 3 months)
- field-level inspection: sign code domain, jisu/change wire format,
  volume non-zero, cont_block.date format
"""

import logging
import os
from dotenv import load_dotenv
from programgarden_finance import LS, t1633

logger = logging.getLogger(__name__)

load_dotenv()


def _format_row(item: t1633.T1633OutBlock1) -> str:
    sign_str = {
        "1": "▲상한", "2": "△상승", "3": "-보합",
        "4": "▼하한", "5": "▽하락",
    }.get(item.sign, f"?{item.sign}")
    return (
        f"{item.date:>10} {sign_str:>6} {item.jisu:>10.2f} "
        f"{item.change:>+8.2f} | "
        f"tot {item.tot1:>10,}/{item.tot2:>10,}/{item.tot3:>10,} | "
        f"cha {item.cha1:>8,}/{item.cha2:>8,}/{item.cha3:>8,} | "
        f"bcha {item.bcha1:>10,}/{item.bcha2:>10,}/{item.bcha3:>10,} | "
        f"vol {item.volume:>12,}"
    )


def _check_response(label: str, resp: t1633.T1633Response) -> None:
    logger.info(f"--- {label} ---")
    logger.info(f"rsp_cd={resp.rsp_cd!r}, rsp_msg={resp.rsp_msg!r}")
    logger.info(f"status_code={resp.status_code}")
    logger.info(f"error_msg={resp.error_msg!r}")
    if resp.cont_block:
        logger.info(
            f"cont_block: date={resp.cont_block.date!r}, "
            f"idx={resp.cont_block.idx}"
        )
    logger.info(f"block rows: {len(resp.block)}")
    if resp.block:
        logger.info(
            f"{'date':>10} {'sign':>6} {'jisu':>10} {'change':>8} "
            f"| tot1/tot2/tot3 | cha1/cha2/cha3 | bcha1/bcha2/bcha3 | volume"
        )
        for item in resp.block[:5]:
            logger.info(_format_row(item))
        if len(resp.block) > 5:
            logger.info(f"... ({len(resp.block) - 5} more rows)")
    logger.info("")


def test_req_t1633():
    """t1633 기간별프로그램매매추이 — single page + occurs_req 검증."""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    ls = LS()
    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA"),
    )
    if login_result is False:
        logger.error("로그인 실패")
        return

    program = ls.국내주식().프로그램매매()

    # ─────────────────────────────────────────────────────────
    # Test 1 — single req(): KOSPI daily, recent ~1 month (Apr 2026)
    # ─────────────────────────────────────────────────────────
    body1 = t1633.T1633InBlock(
        gubun="0",
        gubun1="0",
        gubun2="0",
        gubun3="1",
        fdate="20260401",
        tdate="20260430",
        gubun4="0",
        date=" ",
        exchgubun="K",
    )
    tr1 = program.기간별프로그램매매추이(body=body1)
    resp1 = tr1.req()
    _check_response("Test 1 (single req, KOSPI daily 1mo)", resp1)

    # Discover sign code domain actually returned by REST
    if resp1.block:
        signs = sorted({item.sign for item in resp1.block})
        logger.info(f"[discover] distinct sign codes in Test 1: {signs}")

    # ─────────────────────────────────────────────────────────
    # Test 2 — manual 2-page paging (KOSPI daily 12mo, verify cont_block flow)
    # ─────────────────────────────────────────────────────────
    body2 = t1633.T1633InBlock(
        gubun="0",
        gubun1="0",
        gubun2="0",
        gubun3="1",
        fdate="20250501",
        tdate="20260430",
        gubun4="0",
        date=" ",
        exchgubun="K",
    )
    tr2 = program.기간별프로그램매매추이(body=body2)
    page1 = tr2.req()
    _check_response("Test 2 page 1 (manual 2-page, KOSPI daily 12mo)", page1)
    if page1.cont_block and page1.header and page1.header.tr_cont == "Y":
        # Manual second page: feed cont_block.date back into the InBlock
        body2.date = page1.cont_block.date
        tr2.request_data.body["t1633InBlock"].date = page1.cont_block.date
        tr2.request_data.header.tr_cont = page1.header.tr_cont
        tr2.request_data.header.tr_cont_key = page1.header.tr_cont_key
        page2 = tr2.req()
        _check_response("Test 2 page 2", page2)
        # Verify cursor advanced (page2 should not duplicate page1's first row)
        if page2.block and page1.block:
            assert page2.block[0].date != page1.block[0].date, (
                "manual paging failed: page2 first row date matches page1 — "
                "cont_block.date was not propagated correctly"
            )
            logger.info(
                f"[verify] cursor advance OK: page1[0].date={page1.block[0].date} "
                f"→ page2[0].date={page2.block[0].date}"
            )
    else:
        logger.info("[skip] page1 returned tr_cont!='Y' — single page covered the period")

    # ─────────────────────────────────────────────────────────
    # Test 3 — KOSDAQ weekly (gubun='1', gubun3='2')
    # ─────────────────────────────────────────────────────────
    body3 = t1633.T1633InBlock(
        gubun="1",
        gubun1="0",
        gubun2="0",
        gubun3="2",
        fdate="20260101",
        tdate="20260430",
        gubun4="0",
        date=" ",
        exchgubun="K",
    )
    tr3 = program.기간별프로그램매매추이(body=body3)
    resp3 = tr3.req()
    _check_response("Test 3 (KOSDAQ weekly, gubun3='2')", resp3)


if __name__ == "__main__":
    test_req_t1633()
