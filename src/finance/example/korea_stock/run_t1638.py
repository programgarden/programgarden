import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t1638

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_t1638():
    """t1638 종목별잔량/사전공시 테스트"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 코스피(1) 시가총액비중순(1) 조회
    m = ls.국내주식().기타().종목별잔량사전공시(
        t1638.T1638InBlock(gubun1="1", gubun2="1")
    )

    response = m.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
    logger.info(f"조회 건수: {len(response.block)}건")
    logger.info("=" * 120)
    logger.info(f"{'순위':>4} {'종목명':<14} {'현재가':>10} {'시총비중':>8} {'매수잔량':>12} {'매도잔량':>12}")
    logger.info("-" * 120)

    for item in response.block:
        logger.info(
            f"{item.rank:>4} {item.hname:<14} {item.price:>10,} {item.sigatotrt:>7.2f}% "
            f"{item.buyrem:>12,} {item.sellrem:>12,}"
        )


if __name__ == "__main__":
    test_req_t1638()
