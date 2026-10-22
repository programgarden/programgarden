import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t1941

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_t1941():
    """t1941 종목별대차거래일간추이 테스트"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 삼성전자(005930) 최근 1개월 대차거래 추이
    m = ls.국내주식().기타().종목별대차거래일간추이(
        t1941.T1941InBlock(shcode="005930", sdate="20260201", edate="20260228")
    )

    response = m.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
    logger.info(f"조회 건수: {len(response.block)}건")
    logger.info("=" * 110)
    logger.info(f"{'일자':>10} {'현재가':>10} {'거래량':>12} {'대차체결':>12} {'대차상환':>12} {'잔고':>12}")
    logger.info("-" * 110)

    for item in response.block:
        logger.info(
            f"{item.date:>10} {item.price:>10,} {item.volume:>12,} "
            f"{item.upvolume:>12,} {item.dnvolume:>12,} {item.tovolume:>12,}"
        )


if __name__ == "__main__":
    test_req_t1941()
