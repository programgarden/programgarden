import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t1444

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_t1444():
    """t1444 시가총액상위 조회 테스트"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 코스피(001) 시가총액상위 조회
    m_t1444 = ls.국내주식().순위().시가총액상위(
        t1444.T1444InBlock(upcode="001", idx=0)
    )

    response = m_t1444.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    if response.cont_block:
        logger.info(f"연속조회키(idx): {response.cont_block.idx}")

    logger.info(f"조회 건수: {len(response.block)}건")
    logger.info("=" * 90)
    logger.info(f"{'순위':>4} {'종목명':<12} {'현재가':>10} {'등락률':>8} {'거래량':>14} {'시가총액(억)':>14} {'비중':>7} {'외인비중':>8}")
    logger.info("-" * 90)

    for i, item in enumerate(response.block, 1):
        sign_str = {
            "1": "▲", "2": "△", "3": "-", "4": "▼", "5": "▽"
        }.get(item.sign, item.sign)

        logger.info(
            f"{i:>4} {item.hname:<12} {item.price:>10,} {sign_str}{item.diff:>+6.2f}% "
            f"{item.volume:>14,} {item.total:>14,} {item.rate:>6.2f}% {item.for_rate:>7.2f}%"
        )


if __name__ == "__main__":
    test_req_t1444()
