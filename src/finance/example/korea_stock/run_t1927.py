import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t1927

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_t1927():
    """t1927 공매도일별추이 테스트"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 삼성전자(005930) 최근 1개월 공매도 추이
    m = ls.국내주식().기타().공매도일별추이(
        t1927.T1927InBlock(shcode="005930", sdate="20260201", edate="20260228")
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
    logger.info(f"{'일자':>10} {'현재가':>10} {'거래량':>12} {'공매도량':>12} {'공매도금액':>14} {'공매도비중':>8}")
    logger.info("-" * 100)

    for item in response.block:
        logger.info(
            f"{item.date:>10} {item.price:>10,} {item.volume:>12,} "
            f"{item.gm_vo:>12,} {item.gm_va:>14,} {item.gm_per:>7.2f}%"
        )


if __name__ == "__main__":
    test_req_t1927()
