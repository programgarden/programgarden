import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t1901

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_t1901():
    """t1901 ETF현재가(시세)조회 테스트"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # KODEX 200 (069500) ETF 현재가 조회
    m = ls.국내주식().ETF().ETF현재가조회(
        t1901.T1901InBlock(shcode="069500")
    )

    response = m.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    item = response.block
    sign_str = {
        "1": "▲", "2": "△", "3": "-", "4": "▼", "5": "▽"
    }.get(item.sign, item.sign)

    logger.info("=" * 60)
    logger.info(f"ETF명: {item.hname}")
    logger.info(f"현재가: {item.price:,} ({sign_str}{item.change:+,}, {item.diff:+.2f}%)")
    logger.info(f"거래량: {item.volume:,}")
    logger.info(f"NAV: {item.nav:,.2f}")
    logger.info(f"PER: {item.per:.2f}")
    logger.info(f"순자산총액: {item.etftotcap:,}")
    logger.info("=" * 60)


if __name__ == "__main__":
    test_req_t1901()
