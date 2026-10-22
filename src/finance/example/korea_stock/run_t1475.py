import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t1475

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_t1475():
    """t1475 체결강도추이 테스트"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 삼성전자(005930) 시간별(0) 체결강도추이
    m = ls.국내주식().시세().체결강도추이(
        t1475.T1475InBlock(shcode="005930", vptype="0")
    )

    response = m.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    if response.cont_block:
        logger.info(f"연속조회키(date): {response.cont_block.date}, time: {response.cont_block.time}")

    logger.info(f"조회 건수: {len(response.block)}건")
    logger.info("=" * 80)
    logger.info(f"{'일시':>14} {'거래량':>12} {'당일VP':>8} {'5일MAVP':>8}")
    logger.info("-" * 80)

    for item in response.block:
        logger.info(
            f"{item.datetime:>14} {item.volume:>12,} {item.todayvp:>8.2f} {item.ma5vp:>8.2f}"
        )


if __name__ == "__main__":
    test_req_t1475()
