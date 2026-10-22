import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t1471

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_t1471():
    """t1471 시간대별호가잔량추이 테스트"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 삼성전자(005930) 1분(01) 단위 호가잔량추이
    m = ls.국내주식().시세().시간대별호가잔량추이(
        t1471.T1471InBlock(shcode="005930", gubun="01")
    )

    response = m.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    if response.cont_block:
        logger.info(f"연속조회키(time): {response.cont_block.time}")

    logger.info(f"조회 건수: {len(response.block)}건")
    logger.info("=" * 100)
    logger.info(f"{'시간':>10} {'매도잔량':>12} {'매수잔량':>12} {'매수비율':>8} {'순매수':>12}")
    logger.info("-" * 100)

    for item in response.block:
        logger.info(
            f"{item.time:>10} {item.offerrem1:>12,} {item.bidrem1:>12,} "
            f"{item.msrate:>7.2f}% {item.totsun:>12,}"
        )


if __name__ == "__main__":
    test_req_t1471()
