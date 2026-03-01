import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t8407

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_t8407():
    """t8407 주식멀티현재가조회 테스트"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 삼성전자, SK하이닉스, LG에너지솔루션 3종목 동시 조회
    codes = "005930000660373220"
    m = ls.국내주식().시세().주식멀티현재가조회(
        t8407.T8407InBlock(nrec=3, shcode=codes)
    )

    response = m.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
    logger.info(f"조회 건수: {len(response.block)}건")
    logger.info("=" * 100)
    logger.info(f"{'종목코드':>8} {'종목명':<14} {'현재가':>10} {'등락률':>8} {'거래량':>12} {'체결강도':>8}")
    logger.info("-" * 100)

    for item in response.block:
        sign_str = {
            "1": "▲", "2": "△", "3": "-", "4": "▼", "5": "▽"
        }.get(item.sign, item.sign)

        logger.info(
            f"{item.shcode:>8} {item.hname:<14} {item.price:>10,} {sign_str}{item.diff:>+6.2f}% "
            f"{item.volume:>12,} {item.chdegree:>8.2f}"
        )


if __name__ == "__main__":
    test_req_t8407()
