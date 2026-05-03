import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t1637

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_t1637():
    """t1637 per-symbol program-trading time series — manual integration test.

    Default mode: time-bucketed (gubun2='0') for Samsung Electronics(005930)
    in amount mode (gubun1='1') on KRX. The LS official example uses these
    same parameters.
    """

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA"),
    )

    if login_result is False:
        logger.error("Login failed")
        return

    # Samsung Electronics(005930), amount mode (gubun1='1'),
    # time-bucketed (gubun2='0'), KRX, chart marker (cts_idx=9999, default).
    m = ls.국내주식().프로그램매매().종목별프로그램매매추이(
        t1637.T1637InBlock(
            gubun1="1",
            gubun2="0",
            shcode="005930",
            date="",
            time="",
            cts_idx=9999,
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
        logger.info(f"OutBlock cts_idx echo: {response.cont_block.cts_idx}")

    logger.info(f"Result count: {len(response.block)} rows")
    logger.info("=" * 110)
    logger.info(
        f"{'date':>10} {'time':>8} {'price':>10} {'net_buy_amt':>15} "
        f"{'buy_amt':>15} {'sell_amt':>15}"
    )
    logger.info("-" * 110)

    for item in response.block:
        logger.info(
            f"{item.date:>10} {item.time:>8} {item.price:>10,} "
            f"{item.svalue:>15,} {item.stksvalue:>15,} {item.offervalue:>15,}"
        )


if __name__ == "__main__":
    test_req_t1637()
