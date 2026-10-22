import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t1441

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_t1441():
    """t1441 등락율상위 조회 테스트"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 코스피(0:전체) 상승률(0) 당일(0) 등락율상위 조회
    m_t1441 = ls.국내주식().순위().등락율상위(
        t1441.T1441InBlock(gubun1="0", gubun2="0", gubun3="0")
    )

    response = m_t1441.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    if response.cont_block:
        logger.info(f"연속조회키(idx): {response.cont_block.idx}")

    logger.info(f"조회 건수: {len(response.block)}건")
    logger.info("=" * 100)
    logger.info(f"{'순위':>4} {'종목명':<14} {'현재가':>10} {'등락률':>8} {'거래량':>12} {'시가총액':>12}")
    logger.info("-" * 100)

    for i, item in enumerate(response.block, 1):
        sign_str = {
            "1": "▲", "2": "△", "3": "-", "4": "▼", "5": "▽"
        }.get(item.sign, item.sign)

        logger.info(
            f"{i:>4} {item.hname:<14} {item.price:>10,} {sign_str}{item.diff:>+6.2f}% "
            f"{item.volume:>12,} {item.total:>12,}"
        )


if __name__ == "__main__":
    test_req_t1441()
