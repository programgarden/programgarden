import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t1466

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_t1466():
    """t1466 전일동시간대비거래급증 테스트"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 전체시장(0) 1주이상(0) 전체급등율(0) 조회
    m = ls.국내주식().순위().전일동시간대비거래급증(
        t1466.T1466InBlock(gubun="0", type1="0", type2="0")
    )

    response = m.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    if response.cont_block:
        logger.info(f"연속조회키(idx): {response.cont_block.idx}")

    logger.info(f"조회 건수: {len(response.block)}건")
    logger.info("=" * 100)
    logger.info(f"{'종목코드':>8} {'종목명':<14} {'현재가':>10} {'등락률':>8} {'거래급등율':>10} {'거래량':>12}")
    logger.info("-" * 100)

    for item in response.block:
        sign_str = {
            "1": "▲", "2": "△", "3": "-", "4": "▼", "5": "▽"
        }.get(item.sign, item.sign)

        logger.info(
            f"{item.shcode:>8} {item.hname:<14} {item.price:>10,} {sign_str}{item.diff:>+6.2f}% "
            f"{item.voldiff:>10.2f} {item.volume:>12,}"
        )


if __name__ == "__main__":
    test_req_t1466()
