import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t1636

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_t1636():
    """t1636 Korean stock program trading by symbol — manual integration test."""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA"),
    )

    if login_result is False:
        logger.error("Login failed")
        return

    # KOSPI(0) / amount(1) / sort by market-cap weight(0) / Samsung Electronics(005930)
    m = ls.국내주식().프로그램매매().종목별프로그램매매동향(
        t1636.T1636InBlock(
            gubun="0",
            gubun1="1",
            gubun2="0",
            shcode="005930",
            cts_idx=0,
            exchgubun="K",
        )
    )

    response = m.req()

    if response.error_msg:
        logger.error(f"Request failed: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    if response.cont_block:
        logger.info(f"Continuation cts_idx: {response.cont_block.cts_idx}")

    logger.info(f"Result count: {len(response.block)} rows")
    logger.info("=" * 110)
    logger.info(
        f"{'rank':>4} {'name':>10} {'price':>10} {'net_buy_amt':>15} "
        f"{'rate(%)':>10} {'mkcap_cmpr_val(%)':>20}"
    )
    logger.info("-" * 110)

    for item in response.block:
        logger.info(
            f"{item.rank:>4} {item.hname:>10} {item.price:>10,} "
            f"{item.stksvalue:>15,} {item.rate:>10.2f} {item.mkcap_cmpr_val:>20.2f}"
        )


if __name__ == "__main__":
    test_req_t1636()
