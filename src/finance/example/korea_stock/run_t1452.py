import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t1452

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_t1452():
    """t1452 거래량상위 조회 테스트"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 코스피(1) 당일(1) 거래량상위 조회
    m_t1452 = ls.국내주식().순위().거래량상위(
        t1452.T1452InBlock(gubun="1", jnilgubun="1")
    )

    response = m_t1452.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    if response.cont_block:
        logger.info(f"연속조회키(idx): {response.cont_block.idx}")

    logger.info(f"조회 건수: {len(response.block)}건")
    logger.info("=" * 100)
    logger.info(f"{'순위':>4} {'종목명':<14} {'현재가':>10} {'등락률':>8} {'누적거래량':>14} {'회전율':>7} {'전일거래량':>14} {'전일비':>8}")
    logger.info("-" * 100)

    for i, item in enumerate(response.block, 1):
        sign_str = {
            "1": "▲", "2": "△", "3": "-", "4": "▼", "5": "▽"
        }.get(item.sign, item.sign)

        logger.info(
            f"{i:>4} {item.hname:<14} {item.price:>10,} {sign_str}{item.diff:>+6.2f}% "
            f"{item.volume:>14,} {item.vol:>6.2f}% {item.jnilvolume:>14,} {item.bef_diff:>7.2f}%"
        )


if __name__ == "__main__":
    test_req_t1452()
