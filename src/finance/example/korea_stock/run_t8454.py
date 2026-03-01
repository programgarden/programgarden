import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t8454

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_t8454():
    """t8454 주식시간대별체결조회2 테스트"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 삼성전자(005930) 시간대별체결조회2
    m = ls.국내주식().시세().주식시간대별체결조회2(
        t8454.T8454InBlock(shcode="005930")
    )

    response = m.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    if response.cont_block:
        logger.info(f"연속조회키(cts_time): {response.cont_block.cts_time}")

    logger.info(f"조회 건수: {len(response.block)}건")
    logger.info("=" * 100)
    logger.info(f"{'시간':>10} {'현재가':>10} {'체결수량':>10} {'순체결량':>10} {'체결강도':>8}")
    logger.info("-" * 100)

    for item in response.block:
        sign_str = {
            "1": "▲", "2": "△", "3": "-", "4": "▼", "5": "▽"
        }.get(item.sign, item.sign)

        logger.info(
            f"{item.chetime:>10} {item.price:>10,} {item.cvolume:>10,} "
            f"{item.revolume:>10,} {item.chdegree:>8.2f}"
        )


if __name__ == "__main__":
    test_req_t8454()
