import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t1903

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_t1903():
    """t1903 ETF일별추이 테스트"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # KODEX 200 (069500) ETF 일별추이
    m = ls.국내주식().ETF().ETF일별추이(
        t1903.T1903InBlock(shcode="069500")
    )

    response = m.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    if response.cont_block:
        logger.info(f"연속조회키(date): {response.cont_block.date}")

    logger.info(f"조회 건수: {len(response.block)}건")
    logger.info("=" * 100)
    logger.info(f"{'일자':>10} {'현재가':>10} {'거래량':>12} {'NAV':>12} {'괴리율':>8} {'추적오차':>8}")
    logger.info("-" * 100)

    for item in response.block:
        logger.info(
            f"{item.date:>10} {item.price:>10,} {item.volume:>12,} "
            f"{item.nav:>12,.2f} {item.crate:>7.2f}% {item.grate:>7.2f}%"
        )


if __name__ == "__main__":
    test_req_t1903()
