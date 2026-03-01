import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t8452

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_t8452():
    """t8452 주식차트(N분) 테스트"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 삼성전자(005930) 5분봉 최근 50건 조회
    m = ls.국내주식().차트().주식차트N분(
        t8452.T8452InBlock(shcode="005930", ncnt=5, qrycnt=50, sdate="20260228", edate="20260228", comp_yn="N")
    )

    response = m.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    if response.cont_block:
        logger.info(f"연속조회키(cts_date): {response.cont_block.cts_date}, cts_time: {response.cont_block.cts_time}")

    logger.info(f"조회 건수: {len(response.block)}건")
    logger.info("=" * 100)
    logger.info(f"{'날짜':>10} {'시간':>8} {'시가':>10} {'고가':>10} {'저가':>10} {'종가':>10} {'거래량':>12}")
    logger.info("-" * 100)

    for item in response.block:
        logger.info(
            f"{item.date:>10} {item.time:>8} {item.open:>10,} {item.high:>10,} "
            f"{item.low:>10,} {item.close:>10,} {item.jdiff_vol:>12,}"
        )


if __name__ == "__main__":
    test_req_t8452()
