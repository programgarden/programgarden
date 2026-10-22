import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t1532

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_t1532():
    """t1532 종목별테마 테스트"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 삼성전자(005930)가 속한 테마 조회
    m = ls.국내주식().업종테마().종목별테마(
        t1532.T1532InBlock(shcode="005930")
    )

    response = m.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
    logger.info(f"조회 건수: {len(response.block)}건")
    logger.info("=" * 80)
    logger.info(f"{'테마명':<20} {'평균등락률':>10} {'테마코드':>10}")
    logger.info("-" * 80)

    for item in response.block:
        logger.info(
            f"{item.tmname:<20} {item.avgdiff:>+9.2f}% {item.tmcode:>10}"
        )


if __name__ == "__main__":
    test_req_t1532()
