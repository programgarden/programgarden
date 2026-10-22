import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t1631

logger = logging.getLogger(__name__)

load_dotenv()


def _print_response(label: str, response):
    """Pretty-print a t1631 response — summary_block + block rows.

    Row meaning and array ordering of ``response.block`` are not
    documented in the LS public spec; values are printed as reported.
    """
    logger.info("=" * 110)
    logger.info(f"[{label}] rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    if response.error_msg:
        logger.error(f"[{label}] Request failed: {response.error_msg}")
        return

    summary = response.summary_block
    if summary:
        logger.info(
            "summary_block (order/remainder aggregates as reported by LS):"
        )
        logger.info(
            f"  sell  arb  unfilled={summary.cdhrem:>10,}  ordered={summary.tcdrem:>10,}"
        )
        logger.info(
            f"  sell  non  unfilled={summary.bdhrem:>10,}  ordered={summary.tbdrem:>10,}"
        )
        logger.info(
            f"  buy   arb  unfilled={summary.cshrem:>10,}  ordered={summary.tcsrem:>10,}"
        )
        logger.info(
            f"  buy   non  unfilled={summary.bshrem:>10,}  ordered={summary.tbsrem:>10,}"
        )

    logger.info(f"block — {len(response.block)} rows (LS-reported order):")
    logger.info(
        f"  {'idx':>3} {'sell_qty':>10} {'sell_amt':>14} "
        f"{'buy_qty':>10} {'buy_amt':>14} {'net_qty':>10} {'net_amt':>14}"
    )
    for idx, row in enumerate(response.block):
        logger.info(
            f"  {idx:>3} {row.offervolume:>10,} {row.offervalue:>14,} "
            f"{row.bidvolume:>10,} {row.bidvalue:>14,} "
            f"{row.volume:>10,} {row.value:>14,}"
        )


def test_req_t1631_today():
    """t1631 same-day query — gubun='1' (거래소), dgubun='1'."""
    ls = LS()
    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA"),
    )
    if login_result is False:
        logger.error("Login failed")
        return

    # gubun='1' (거래소) / dgubun='1' (당일조회) / sdate=edate empty / exchgubun='K' (KRX)
    m = ls.국내주식().프로그램매매().프로그램매매종합조회(
        t1631.T1631InBlock(
            gubun="1",
            dgubun="1",
            sdate="",
            edate="",
            exchgubun="K",
        )
    )
    response = m.req()
    _print_response("거래소 same-day", response)


def test_req_t1631_period():
    """t1631 period query — gubun='2' (코스닥), dgubun='2'."""
    ls = LS()
    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA"),
    )
    if login_result is False:
        logger.error("Login failed")
        return

    # gubun='2' (코스닥) / dgubun='2' (기간조회) / exchgubun='K' (KRX)
    m = ls.국내주식().프로그램매매().프로그램매매종합조회(
        t1631.T1631InBlock(
            gubun="2",
            dgubun="2",
            sdate="20260415",
            edate="20260502",
            exchgubun="K",
        )
    )
    response = m.req()
    _print_response("코스닥 period 20260415~20260502", response)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_req_t1631_today()
    test_req_t1631_period()
