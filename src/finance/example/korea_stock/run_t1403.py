import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t1403

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_t1403():
    """t1403 신규상장종목조회 테스트"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 코스피(1) 2025년 신규상장종목 조회
    m_t1403 = ls.국내주식().기타().신규상장종목조회(
        t1403.T1403InBlock(gubun="1", styymm="202501", enyymm="202512")
    )

    response = m_t1403.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    if response.cont_block:
        logger.info(f"연속조회키(idx): {response.cont_block.idx}")

    logger.info(f"조회 건수: {len(response.block)}건")
    logger.info("=" * 120)
    logger.info(f"{'종목명':<14} {'현재가':>10} {'등락률':>8} {'공모가':>10} {'상장일':>10} {'기준가등락률':>10} {'등록일종가':>10} {'등록일등락률':>10} {'종목코드':>8}")
    logger.info("-" * 120)

    for item in response.block:
        sign_str = {
            "1": "▲", "2": "△", "3": "-", "4": "▼", "5": "▽"
        }.get(item.sign, item.sign)

        logger.info(
            f"{item.hname:<14} {item.price:>10,} {sign_str}{item.diff:>+6.2f}% "
            f"{item.kmprice:>10,} {item.date:>10} {item.kmdiff:>+9.2f}% "
            f"{item.close:>10,} {item.recdiff:>+9.2f}% {item.shcode:>8}"
        )


if __name__ == "__main__":
    test_req_t1403()
